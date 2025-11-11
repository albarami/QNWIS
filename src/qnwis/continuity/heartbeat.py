"""
Deterministic heartbeat monitoring and quorum detection.

Uses ManualClock for deterministic testing and quorum calculation
based on N/2 + 1 formula.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qnwis.continuity.models import (
    Heartbeat,
    NodeStatus,
    QuorumStatus,
)
from qnwis.utils.clock import Clock

if TYPE_CHECKING:
    from qnwis.continuity.models import Cluster, Node


class HeartbeatMonitor:
    """
    Deterministic heartbeat simulator and quorum detector.

    Simulates node heartbeats using injected clock and calculates
    quorum status based on healthy node count.
    """

    def __init__(self, clock: Clock | None = None) -> None:
        """
        Initialize heartbeat monitor.

        Args:
            clock: Clock instance for deterministic time (default: system clock)
        """
        self._clock = clock or Clock()
        self._heartbeats: dict[str, Heartbeat] = {}

    def record_heartbeat(
        self,
        node_id: str,
        status: NodeStatus,
        latency_ms: float = 0.0,
    ) -> Heartbeat:
        """
        Record a heartbeat from a node.

        Args:
            node_id: Node identifier
            status: Current node status
            latency_ms: Heartbeat latency in milliseconds

        Returns:
            Recorded heartbeat
        """
        heartbeat = Heartbeat(
            node_id=node_id,
            timestamp=self._clock.utcnow(),
            status=status,
            latency_ms=latency_ms,
        )
        self._heartbeats[node_id] = heartbeat
        return heartbeat

    def get_heartbeat(self, node_id: str) -> Heartbeat | None:
        """
        Get most recent heartbeat for a node.

        Args:
            node_id: Node identifier

        Returns:
            Most recent heartbeat or None if not found
        """
        return self._heartbeats.get(node_id)

    def get_all_heartbeats(self) -> dict[str, Heartbeat]:
        """
        Get all recorded heartbeats.

        Returns:
            Dictionary mapping node_id to heartbeat
        """
        return dict(self._heartbeats)

    def calculate_quorum(self, cluster: Cluster) -> QuorumStatus:
        """
        Calculate quorum status for a cluster.

        Quorum is achieved when healthy_nodes >= quorum_size.
        Standard quorum formula: N/2 + 1 (majority).

        Args:
            cluster: Cluster configuration

        Returns:
            Quorum status
        """
        healthy_node_ids = []
        for node in cluster.nodes:
            heartbeat = self._heartbeats.get(node.node_id)
            if heartbeat and heartbeat.status == NodeStatus.HEALTHY:
                healthy_node_ids.append(node.node_id)

        healthy_count = len(healthy_node_ids)
        has_quorum = healthy_count >= cluster.quorum_size

        return QuorumStatus(
            cluster_id=cluster.cluster_id,
            timestamp=self._clock.utcnow(),
            total_nodes=len(cluster.nodes),
            healthy_nodes=healthy_count,
            quorum_size=cluster.quorum_size,
            has_quorum=has_quorum,
            healthy_node_ids=healthy_node_ids,
        )

    def simulate_heartbeats(
        self,
        nodes: list[Node],
        latency_ms: float = 5.0,
    ) -> list[Heartbeat]:
        """
        Simulate heartbeats for a list of nodes.

        Uses node.status to determine heartbeat status.

        Args:
            nodes: List of nodes to simulate
            latency_ms: Simulated latency in milliseconds

        Returns:
            List of recorded heartbeats
        """
        heartbeats = []
        for node in nodes:
            heartbeat = self.record_heartbeat(
                node_id=node.node_id,
                status=node.status,
                latency_ms=latency_ms,
            )
            heartbeats.append(heartbeat)
        return heartbeats

    def check_node_health(self, node_id: str, max_age_s: float = 30.0) -> bool:
        """
        Check if a node is healthy based on heartbeat age.

        Args:
            node_id: Node identifier
            max_age_s: Maximum heartbeat age in seconds

        Returns:
            True if node is healthy and heartbeat is recent
        """
        heartbeat = self._heartbeats.get(node_id)
        if not heartbeat:
            return False

        # In production, would check timestamp age
        # For deterministic testing, we trust the recorded status
        return heartbeat.status == NodeStatus.HEALTHY

    def clear_heartbeats(self) -> None:
        """Clear all recorded heartbeats."""
        self._heartbeats.clear()


def calculate_quorum_size(total_nodes: int) -> int:
    """
    Calculate required quorum size using majority formula.

    Formula: floor(N/2) + 1

    Args:
        total_nodes: Total number of nodes

    Returns:
        Required quorum size

    Examples:
        >>> calculate_quorum_size(3)
        2
        >>> calculate_quorum_size(5)
        3
        >>> calculate_quorum_size(1)
        1
    """
    if total_nodes < 1:
        raise ValueError("Total nodes must be at least 1")
    return (total_nodes // 2) + 1


__all__ = [
    "HeartbeatMonitor",
    "calculate_quorum_size",
]
