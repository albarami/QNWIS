"""Unit tests for continuity planner."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qnwis.continuity.models import (
    Cluster,
    FailoverPolicy,
    FailoverStrategy,
    Node,
    NodeRole,
    NodeStatus,
)
from qnwis.continuity.planner import ContinuityPlanner
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
        quorum_size=2,
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


def test_planner_build_plan(test_cluster, test_policy):
    """Test building a continuity plan."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    planner = ContinuityPlanner(clock=clock)

    plan = planner.build_plan(test_cluster, test_policy)

    assert plan.plan_id is not None
    assert plan.cluster_id == "test-cluster"
    assert plan.policy_id == "test-policy"
    assert plan.primary_node_id == "node-1"
    assert plan.failover_target_id == "node-2"  # Highest priority secondary
    assert len(plan.actions) > 0
    assert plan.estimated_total_ms > 0


def test_planner_selects_highest_priority_target(test_cluster, test_policy):
    """Test that planner selects highest priority target."""
    planner = ContinuityPlanner()

    plan = planner.build_plan(test_cluster, test_policy)

    # Should select node-2 (priority 90, region-1) over node-3 (priority 80, region-2)
    assert plan.failover_target_id == "node-2"


def test_planner_respects_region_priority(test_cluster, test_policy):
    """Test that planner respects region priority."""
    # Swap node priorities to make node-3 higher
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
            priority=80,  # Lower priority
            capacity=95.0,
        ),
        Node(
            node_id="node-3",
            hostname="10.0.2.10",
            role=NodeRole.SECONDARY,
            region="region-2",
            site="site-c",
            status=NodeStatus.HEALTHY,
            priority=90,  # Higher priority
            capacity=90.0,
        ),
    ]

    cluster = Cluster(
        cluster_id="test-cluster",
        name="Test Cluster",
        nodes=nodes,
        quorum_size=2,
        regions=["region-1", "region-2"],
    )

    planner = ContinuityPlanner()
    plan = planner.build_plan(cluster, test_policy)

    # Should still select node-2 because region-1 has higher priority
    assert plan.failover_target_id == "node-2"


def test_planner_no_primary_error(test_cluster, test_policy):
    """Test error when no primary node exists."""
    # Create cluster with no primary
    nodes = [
        Node(
            node_id="node-1",
            hostname="10.0.1.10",
            role=NodeRole.SECONDARY,  # Changed to secondary
            region="region-1",
            site="site-a",
            status=NodeStatus.HEALTHY,
        ),
    ]

    cluster = Cluster(
        cluster_id="test-cluster",
        name="Test Cluster",
        nodes=nodes,
        quorum_size=1,
        regions=["region-1"],
    )

    planner = ContinuityPlanner()

    with pytest.raises(ValueError, match="No primary node found"):
        planner.build_plan(cluster, test_policy)


def test_planner_no_target_error(test_cluster, test_policy):
    """Test error when no suitable failover target exists."""
    # Create cluster with only primary (no secondaries)
    nodes = [
        Node(
            node_id="node-1",
            hostname="10.0.1.10",
            role=NodeRole.PRIMARY,
            region="region-1",
            site="site-a",
            status=NodeStatus.HEALTHY,
        ),
    ]

    cluster = Cluster(
        cluster_id="test-cluster",
        name="Test Cluster",
        nodes=nodes,
        quorum_size=1,
        regions=["region-1"],
    )

    planner = ContinuityPlanner()

    with pytest.raises(ValueError, match="No suitable failover target found"):
        planner.build_plan(cluster, test_policy)


def test_planner_action_sequence(test_cluster, test_policy):
    """Test that actions are generated in correct sequence."""
    planner = ContinuityPlanner()

    plan = planner.build_plan(test_cluster, test_policy)

    # Verify action sequence
    action_types = [action.action_type.value for action in plan.actions]

    assert action_types[0] == "demote"  # Demote primary
    assert action_types[1] == "promote"  # Promote target
    assert action_types[2] == "dns_flip"  # Update DNS
    assert action_types[3] == "notify"  # Notify operators
    assert action_types[4] == "verify"  # Verify failover


def test_planner_deterministic(test_cluster, test_policy):
    """Test that planner produces deterministic results."""
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


def test_planner_skips_failed_nodes(test_cluster, test_policy):
    """Test that planner skips failed nodes as targets."""
    # Mark node-2 as failed
    nodes = [
        Node(
            node_id="node-1",
            hostname="10.0.1.10",
            role=NodeRole.PRIMARY,
            region="region-1",
            site="site-a",
            status=NodeStatus.HEALTHY,
        ),
        Node(
            node_id="node-2",
            hostname="10.0.1.11",
            role=NodeRole.SECONDARY,
            region="region-1",
            site="site-b",
            status=NodeStatus.FAILED,  # Failed
            priority=90,
        ),
        Node(
            node_id="node-3",
            hostname="10.0.2.10",
            role=NodeRole.SECONDARY,
            region="region-2",
            site="site-c",
            status=NodeStatus.HEALTHY,
            priority=80,
        ),
    ]

    cluster = Cluster(
        cluster_id="test-cluster",
        name="Test Cluster",
        nodes=nodes,
        quorum_size=2,
        regions=["region-1", "region-2"],
    )

    planner = ContinuityPlanner()
    plan = planner.build_plan(cluster, test_policy)

    # Should select node-3 (only healthy secondary)
    assert plan.failover_target_id == "node-3"
