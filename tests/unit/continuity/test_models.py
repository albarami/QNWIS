"""Unit tests for continuity models."""

from __future__ import annotations

import math

import pytest

from qnwis.continuity.models import (
    ActionType,
    Cluster,
    FailoverAction,
    FailoverPolicy,
    FailoverStrategy,
    Heartbeat,
    Node,
    NodeRole,
    NodeStatus,
    QuorumStatus,
)


def test_node_creation():
    """Test Node model creation."""
    node = Node(
        node_id="node-1",
        hostname="10.0.1.10",
        role=NodeRole.PRIMARY,
        region="region-1",
        site="site-a",
        status=NodeStatus.HEALTHY,
        priority=100,
        capacity=95.5,
    )

    assert node.node_id == "node-1"
    assert node.hostname == "10.0.1.10"
    assert node.role == NodeRole.PRIMARY
    assert node.status == NodeStatus.HEALTHY
    assert node.priority == 100
    assert node.capacity == 95.5


def test_node_validation_priority():
    """Test Node priority validation."""
    with pytest.raises(ValueError, match="Priority must be between 0 and 1000"):
        Node(
            node_id="node-1",
            hostname="10.0.1.10",
            role=NodeRole.PRIMARY,
            region="region-1",
            site="site-a",
            priority=1001,
        )


def test_node_validation_capacity_nan():
    """Test Node capacity NaN validation."""
    with pytest.raises(ValueError, match="Capacity cannot be NaN or Inf"):
        Node(
            node_id="node-1",
            hostname="10.0.1.10",
            role=NodeRole.PRIMARY,
            region="region-1",
            site="site-a",
            capacity=math.nan,
        )


def test_node_validation_capacity_inf():
    """Test Node capacity Inf validation."""
    with pytest.raises(ValueError, match="Capacity cannot be NaN or Inf"):
        Node(
            node_id="node-1",
            hostname="10.0.1.10",
            role=NodeRole.PRIMARY,
            region="region-1",
            site="site-a",
            capacity=math.inf,
        )


def test_node_frozen():
    """Test Node is frozen."""
    node = Node(
        node_id="node-1",
        hostname="10.0.1.10",
        role=NodeRole.PRIMARY,
        region="region-1",
        site="site-a",
    )

    with pytest.raises(Exception):  # Pydantic raises ValidationError
        node.priority = 200  # type: ignore


def test_cluster_creation():
    """Test Cluster model creation."""
    nodes = [
        Node(
            node_id="node-1",
            hostname="10.0.1.10",
            role=NodeRole.PRIMARY,
            region="region-1",
            site="site-a",
        ),
        Node(
            node_id="node-2",
            hostname="10.0.1.11",
            role=NodeRole.SECONDARY,
            region="region-1",
            site="site-b",
        ),
    ]

    cluster = Cluster(
        cluster_id="cluster-1",
        name="Test Cluster",
        nodes=nodes,
        quorum_size=2,
        regions=["region-1"],
    )

    assert cluster.cluster_id == "cluster-1"
    assert len(cluster.nodes) == 2
    assert cluster.quorum_size == 2


def test_failover_policy_creation():
    """Test FailoverPolicy model creation."""
    policy = FailoverPolicy(
        policy_id="policy-1",
        name="Test Policy",
        strategy=FailoverStrategy.AUTOMATIC,
        max_failover_time_s=60,
        require_quorum=True,
        region_priority=["region-1", "region-2"],
        min_healthy_nodes=2,
    )

    assert policy.policy_id == "policy-1"
    assert policy.strategy == FailoverStrategy.AUTOMATIC
    assert policy.max_failover_time_s == 60
    assert policy.require_quorum is True


def test_heartbeat_creation():
    """Test Heartbeat model creation."""
    heartbeat = Heartbeat(
        node_id="node-1",
        timestamp="2024-01-01T00:00:00Z",
        status=NodeStatus.HEALTHY,
        latency_ms=5.5,
    )

    assert heartbeat.node_id == "node-1"
    assert heartbeat.status == NodeStatus.HEALTHY
    assert heartbeat.latency_ms == 5.5


def test_heartbeat_validation_latency_negative():
    """Test Heartbeat latency negative validation."""
    with pytest.raises(ValueError, match="Latency cannot be negative"):
        Heartbeat(
            node_id="node-1",
            timestamp="2024-01-01T00:00:00Z",
            status=NodeStatus.HEALTHY,
            latency_ms=-1.0,
        )


def test_quorum_status_creation():
    """Test QuorumStatus model creation."""
    status = QuorumStatus(
        cluster_id="cluster-1",
        timestamp="2024-01-01T00:00:00Z",
        total_nodes=3,
        healthy_nodes=2,
        quorum_size=2,
        has_quorum=True,
        healthy_node_ids=["node-1", "node-2"],
    )

    assert status.cluster_id == "cluster-1"
    assert status.total_nodes == 3
    assert status.healthy_nodes == 2
    assert status.has_quorum is True


def test_failover_action_creation():
    """Test FailoverAction model creation."""
    action = FailoverAction(
        action_id="action-1",
        action_type=ActionType.PROMOTE,
        target_node_id="node-2",
        params={"role": "primary"},
        sequence=0,
        estimated_duration_ms=10000,
    )

    assert action.action_id == "action-1"
    assert action.action_type == ActionType.PROMOTE
    assert action.target_node_id == "node-2"
    assert action.sequence == 0
