"""Unit tests for failover simulator."""

from __future__ import annotations

import pytest

from qnwis.continuity.models import (
    Cluster,
    FailoverPolicy,
    FailoverStrategy,
    Node,
    NodeRole,
    NodeStatus,
)
from qnwis.continuity.simulate import FailoverSimulator


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


def test_simulator_primary_failure(test_cluster, test_policy):
    """Test simulating primary node failure."""
    simulator = FailoverSimulator(seed=42)

    result = simulator.simulate_primary_failure(test_cluster, test_policy)

    assert result.scenario == "primary_failure"
    assert result.success is True
    assert result.failover_result.success is True
    assert result.verification_report.passed is True


def test_simulator_random_failures(test_cluster, test_policy):
    """Test simulating random node failures."""
    simulator = FailoverSimulator(seed=42)

    result = simulator.simulate_random_failures(test_cluster, test_policy, failure_count=1)

    assert result.scenario == "random_failures_1"
    # Result may succeed or fail depending on which node fails
    assert result.failover_result is not None
    assert result.verification_report is not None


def test_simulator_region_failure(test_cluster, test_policy):
    """Test simulating region failure."""
    simulator = FailoverSimulator(seed=42)

    result = simulator.simulate_region_failure(test_cluster, test_policy, region="region-2")

    assert result.scenario == "region_failure_region-2"
    # Should succeed since primary is in region-1
    assert result.success is True


def test_simulator_deterministic(test_cluster, test_policy):
    """Test that simulator produces deterministic results with same seed."""
    sim1 = FailoverSimulator(seed=42)
    sim2 = FailoverSimulator(seed=42)

    result1 = sim1.simulate_primary_failure(test_cluster, test_policy)
    result2 = sim2.simulate_primary_failure(test_cluster, test_policy)

    # Results should be identical
    assert result1.success == result2.success
    assert result1.failover_result.actions_executed == result2.failover_result.actions_executed
    assert result1.verification_report.passed == result2.verification_report.passed


def test_simulator_different_seeds(test_cluster, test_policy):
    """Test that different seeds can produce different results."""
    sim1 = FailoverSimulator(seed=42)
    sim2 = FailoverSimulator(seed=99)

    result1 = sim1.simulate_random_failures(test_cluster, test_policy)
    result2 = sim2.simulate_random_failures(test_cluster, test_policy)

    # Results may differ (different random failures)
    # Just verify both complete
    assert result1.failover_result is not None
    assert result2.failover_result is not None


def test_simulator_reset_seed(test_cluster, test_policy):
    """Test resetting simulator seed."""
    simulator = FailoverSimulator(seed=42)

    result1 = simulator.simulate_primary_failure(test_cluster, test_policy)

    # Reset to same seed
    simulator.reset_seed(42)

    result2 = simulator.simulate_primary_failure(test_cluster, test_policy)

    # Results should be identical
    assert result1.success == result2.success


def test_simulator_all_nodes_failed(test_cluster, test_policy):
    """Test simulation when all nodes are failed."""
    # Create cluster with all failed nodes
    nodes = [
        Node(
            node_id="node-1",
            hostname="10.0.1.10",
            role=NodeRole.PRIMARY,
            region="region-1",
            site="site-a",
            status=NodeStatus.FAILED,
        ),
        Node(
            node_id="node-2",
            hostname="10.0.1.11",
            role=NodeRole.SECONDARY,
            region="region-1",
            site="site-b",
            status=NodeStatus.FAILED,
        ),
    ]

    cluster = Cluster(
        cluster_id="test-cluster",
        name="Test Cluster",
        nodes=nodes,
        quorum_size=2,
        regions=["region-1"],
    )

    simulator = FailoverSimulator(seed=42)
    result = simulator.simulate_primary_failure(cluster, test_policy)

    # Simulation should fail (no healthy target)
    assert result.success is False
    assert len(result.failover_result.errors) > 0


def test_simulator_performance(test_cluster, test_policy):
    """Test that simulation completes quickly."""
    simulator = FailoverSimulator(seed=42)

    import time

    start = time.perf_counter()
    result = simulator.simulate_primary_failure(test_cluster, test_policy)
    duration_ms = (time.perf_counter() - start) * 1000

    # Should complete in under 100ms (typically much faster)
    assert duration_ms < 100
    assert result.failover_result.total_duration_ms < 100
