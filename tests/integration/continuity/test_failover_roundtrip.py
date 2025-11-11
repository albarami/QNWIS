"""Integration tests for complete failover round-trip."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qnwis.continuity.audit import ContinuityAuditor
from qnwis.continuity.executor import FailoverExecutor
from qnwis.continuity.heartbeat import HeartbeatMonitor, calculate_quorum_size
from qnwis.continuity.models import (
    Cluster,
    FailoverPolicy,
    FailoverStrategy,
    Node,
    NodeRole,
    NodeStatus,
)
from qnwis.continuity.planner import ContinuityPlanner
from qnwis.continuity.verifier import FailoverVerifier
from qnwis.utils.clock import ManualClock


@pytest.fixture
def test_cluster():
    """Create test cluster."""
    nodes = [
        Node(
            node_id="node-1",
            hostname="10.0.1.10",
            role=NodeRole.PRIMARY,
            region="region-1",
            site="site-a",
            status=NodeStatus.HEALTHY,
            priority=100,
            capacity=100.0,
        ),
        Node(
            node_id="node-2",
            hostname="10.0.1.11",
            role=NodeRole.SECONDARY,
            region="region-1",
            site="site-b",
            status=NodeStatus.HEALTHY,
            priority=90,
            capacity=95.0,
        ),
        Node(
            node_id="node-3",
            hostname="10.0.2.10",
            role=NodeRole.SECONDARY,
            region="region-2",
            site="site-c",
            status=NodeStatus.HEALTHY,
            priority=80,
            capacity=90.0,
        ),
    ]

    return Cluster(
        cluster_id="test-cluster",
        name="Test Cluster",
        nodes=nodes,
        quorum_size=calculate_quorum_size(len(nodes)),
        regions=["region-1", "region-2"],
    )


@pytest.fixture
def test_policy():
    """Create test policy."""
    return FailoverPolicy(
        policy_id="test-policy",
        name="Test Policy",
        strategy=FailoverStrategy.AUTOMATIC,
        max_failover_time_s=60,
        require_quorum=True,
        region_priority=["region-1", "region-2"],
        site_priority=["site-a", "site-b", "site-c"],
        min_healthy_nodes=2,
    )


def test_complete_failover_roundtrip(test_cluster, test_policy):
    """Test complete failover round-trip: plan -> execute -> verify -> audit."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    # Initialize components
    heartbeat_monitor = HeartbeatMonitor(clock=clock)
    planner = ContinuityPlanner(clock=clock)
    executor = FailoverExecutor(clock=clock, dry_run=True)
    verifier = FailoverVerifier(clock=clock, heartbeat_monitor=heartbeat_monitor)
    auditor = ContinuityAuditor(clock=clock)

    # Simulate heartbeats
    heartbeat_monitor.simulate_heartbeats(test_cluster.nodes)

    # Generate plan
    plan = planner.build_plan(test_cluster, test_policy)
    assert plan.plan_id is not None
    assert len(plan.actions) > 0
    assert plan.primary_node_id == "node-1"
    assert plan.failover_target_id == "node-2"

    # Execute plan
    clock.advance(0.1)
    result = executor.execute_plan(plan)
    assert result.execution_id is not None
    assert result.success is True
    assert result.actions_executed == len(plan.actions)
    assert result.actions_failed == 0

    # Verify execution
    clock.advance(0.1)
    verification = verifier.verify_failover(result, test_cluster, test_policy)
    assert verification.report_id is not None
    assert verification.consistency_ok is True
    assert verification.policy_ok is True
    assert verification.quorum_ok is True
    assert verification.passed is True

    # Generate audit
    audit_pack = auditor.generate_audit_pack(plan, result, verification)
    assert audit_pack["audit_id"] is not None
    assert audit_pack["manifest_hash"] is not None
    assert audit_pack["confidence"]["score"] >= 90
    assert audit_pack["confidence"]["band"] in ["high", "very_high"]


def test_failover_with_insufficient_quorum(test_cluster, test_policy):
    """Test failover fails with insufficient quorum."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    # Mark most nodes as failed
    failed_nodes = [
        Node(
            node_id=node.node_id,
            hostname=node.hostname,
            role=node.role,
            region=node.region,
            site=node.site,
            status=NodeStatus.FAILED if node.node_id != "node-1" else NodeStatus.HEALTHY,
            priority=node.priority,
            capacity=node.capacity,
        )
        for node in test_cluster.nodes
    ]

    failed_cluster = Cluster(
        cluster_id=test_cluster.cluster_id,
        name=test_cluster.name,
        nodes=failed_nodes,
        quorum_size=test_cluster.quorum_size,
        regions=test_cluster.regions,
    )

    heartbeat_monitor = HeartbeatMonitor(clock=clock)
    verifier = FailoverVerifier(clock=clock, heartbeat_monitor=heartbeat_monitor)

    # Simulate heartbeats
    heartbeat_monitor.simulate_heartbeats(failed_cluster.nodes)

    # Create dummy result
    from qnwis.continuity.models import FailoverResult

    result = FailoverResult(
        execution_id="test-exec",
        plan_id="test-plan",
        started_at=clock.utcnow(),
        completed_at=clock.utcnow(),
        success=True,
        actions_executed=5,
        actions_failed=0,
        total_duration_ms=100,
    )

    # Verify - should fail quorum check
    verification = verifier.verify_failover(result, failed_cluster, test_policy)
    assert verification.quorum_ok is False
    assert verification.passed is False
    assert len(verification.errors) > 0


def test_failover_determinism(test_cluster, test_policy):
    """Test failover execution is deterministic."""
    clock1 = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    clock2 = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    planner1 = ContinuityPlanner(clock=clock1)
    planner2 = ContinuityPlanner(clock=clock2)

    plan1 = planner1.build_plan(test_cluster, test_policy)
    plan2 = planner2.build_plan(test_cluster, test_policy)

    # Plans should be identical (except UUIDs)
    assert plan1.cluster_id == plan2.cluster_id
    assert plan1.policy_id == plan2.policy_id
    assert plan1.primary_node_id == plan2.primary_node_id
    assert plan1.failover_target_id == plan2.failover_target_id
    assert len(plan1.actions) == len(plan2.actions)

    # Action sequences should match
    for a1, a2 in zip(plan1.actions, plan2.actions):
        assert a1.action_type == a2.action_type
        assert a1.target_node_id == a2.target_node_id
        assert a1.sequence == a2.sequence
