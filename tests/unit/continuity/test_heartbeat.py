"""Unit tests for heartbeat monitoring."""

from __future__ import annotations

import pytest

from qnwis.continuity.heartbeat import HeartbeatMonitor, calculate_quorum_size
from qnwis.continuity.models import (
    Cluster,
    Node,
    NodeRole,
    NodeStatus,
)
from qnwis.utils.clock import ManualClock


def test_calculate_quorum_size():
    """Test quorum size calculation."""
    assert calculate_quorum_size(1) == 1
    assert calculate_quorum_size(2) == 2
    assert calculate_quorum_size(3) == 2
    assert calculate_quorum_size(4) == 3
    assert calculate_quorum_size(5) == 3
    assert calculate_quorum_size(6) == 4
    assert calculate_quorum_size(7) == 4


def test_calculate_quorum_size_invalid():
    """Test quorum size calculation with invalid input."""
    with pytest.raises(ValueError, match="Total nodes must be at least 1"):
        calculate_quorum_size(0)


def test_heartbeat_monitor_record():
    """Test recording heartbeats."""
    clock = ManualClock()
    monitor = HeartbeatMonitor(clock=clock)

    heartbeat = monitor.record_heartbeat("node-1", NodeStatus.HEALTHY, latency_ms=5.0)

    assert heartbeat.node_id == "node-1"
    assert heartbeat.status == NodeStatus.HEALTHY
    assert heartbeat.latency_ms == 5.0


def test_heartbeat_monitor_get():
    """Test retrieving heartbeats."""
    clock = ManualClock()
    monitor = HeartbeatMonitor(clock=clock)

    monitor.record_heartbeat("node-1", NodeStatus.HEALTHY)
    heartbeat = monitor.get_heartbeat("node-1")

    assert heartbeat is not None
    assert heartbeat.node_id == "node-1"


def test_heartbeat_monitor_get_missing():
    """Test retrieving missing heartbeat."""
    monitor = HeartbeatMonitor()
    heartbeat = monitor.get_heartbeat("node-999")

    assert heartbeat is None


def test_heartbeat_monitor_calculate_quorum():
    """Test quorum calculation."""
    clock = ManualClock()
    monitor = HeartbeatMonitor(clock=clock)

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
            status=NodeStatus.HEALTHY,
        ),
        Node(
            node_id="node-3",
            hostname="10.0.2.10",
            role=NodeRole.SECONDARY,
            region="region-2",
            site="site-c",
            status=NodeStatus.FAILED,
        ),
    ]

    cluster = Cluster(
        cluster_id="cluster-1",
        name="Test Cluster",
        nodes=nodes,
        quorum_size=2,
        regions=["region-1", "region-2"],
    )

    # Record heartbeats
    for node in nodes:
        monitor.record_heartbeat(node.node_id, node.status)

    # Calculate quorum
    quorum_status = monitor.calculate_quorum(cluster)

    assert quorum_status.total_nodes == 3
    assert quorum_status.healthy_nodes == 2
    assert quorum_status.quorum_size == 2
    assert quorum_status.has_quorum is True
    assert len(quorum_status.healthy_node_ids) == 2


def test_heartbeat_monitor_simulate():
    """Test simulating heartbeats."""
    clock = ManualClock()
    monitor = HeartbeatMonitor(clock=clock)

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
            status=NodeStatus.DEGRADED,
        ),
    ]

    heartbeats = monitor.simulate_heartbeats(nodes, latency_ms=10.0)

    assert len(heartbeats) == 2
    assert heartbeats[0].node_id == "node-1"
    assert heartbeats[0].status == NodeStatus.HEALTHY
    assert heartbeats[1].node_id == "node-2"
    assert heartbeats[1].status == NodeStatus.DEGRADED


def test_heartbeat_monitor_check_health():
    """Test checking node health."""
    clock = ManualClock()
    monitor = HeartbeatMonitor(clock=clock)

    monitor.record_heartbeat("node-1", NodeStatus.HEALTHY)
    monitor.record_heartbeat("node-2", NodeStatus.FAILED)

    assert monitor.check_node_health("node-1") is True
    assert monitor.check_node_health("node-2") is False
    assert monitor.check_node_health("node-999") is False


def test_heartbeat_monitor_clear():
    """Test clearing heartbeats."""
    monitor = HeartbeatMonitor()

    monitor.record_heartbeat("node-1", NodeStatus.HEALTHY)
    monitor.record_heartbeat("node-2", NodeStatus.HEALTHY)

    assert len(monitor.get_all_heartbeats()) == 2

    monitor.clear_heartbeats()

    assert len(monitor.get_all_heartbeats()) == 0
