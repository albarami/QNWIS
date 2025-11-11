"""
Continuity plan builder.

Generates failover plans from cluster topology and policy configuration.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from qnwis.continuity.models import (
    ActionType,
    ContinuityPlan,
    FailoverAction,
    NodeRole,
    NodeStatus,
)
from qnwis.utils.clock import Clock

if TYPE_CHECKING:
    from qnwis.continuity.models import Cluster, FailoverPolicy, Node


class ContinuityPlanner:
    """
    Builds continuity plans from topology and policy.

    Generates ordered failover actions based on policy priorities
    and cluster configuration.
    """

    def __init__(self, clock: Clock | None = None) -> None:
        """
        Initialize continuity planner.

        Args:
            clock: Clock instance for deterministic time (default: system clock)
        """
        self._clock = clock or Clock()

    def build_plan(
        self,
        cluster: Cluster,
        policy: FailoverPolicy,
        trigger_reason: str = "manual",
    ) -> ContinuityPlan:
        """
        Build a continuity plan for cluster failover.

        Args:
            cluster: Cluster configuration
            policy: Failover policy
            trigger_reason: Reason for failover (for audit trail)

        Returns:
            Complete continuity plan

        Raises:
            ValueError: If no suitable failover target found
        """
        # Find current primary
        primary = self._find_primary(cluster)
        if not primary:
            raise ValueError("No primary node found in cluster")

        # Find failover target
        target = self._select_failover_target(cluster, policy, primary)
        if not target:
            raise ValueError("No suitable failover target found")

        # Generate actions
        actions = self._generate_actions(primary, target, cluster, policy)

        # Calculate total estimated time
        total_ms = sum(action.estimated_duration_ms for action in actions)

        plan_id = str(uuid.uuid4())
        return ContinuityPlan(
            plan_id=plan_id,
            cluster_id=cluster.cluster_id,
            policy_id=policy.policy_id,
            created_at=self._clock.utcnow(),
            actions=actions,
            estimated_total_ms=total_ms,
            primary_node_id=primary.node_id,
            failover_target_id=target.node_id,
            metadata={
                "trigger_reason": trigger_reason,
                "primary_region": primary.region,
                "target_region": target.region,
            },
        )

    def _find_primary(self, cluster: Cluster) -> Node | None:
        """Find current primary node."""
        for node in cluster.nodes:
            if node.role == NodeRole.PRIMARY:
                return node
        return None

    def _select_failover_target(
        self,
        cluster: Cluster,
        policy: FailoverPolicy,
        primary: Node,
    ) -> Node | None:
        """
        Select best failover target based on policy.

        Selection criteria (in order):
        1. Node must be healthy
        2. Node must be secondary (not witness)
        3. Prefer regions in policy.region_priority
        4. Prefer sites in policy.site_priority
        5. Prefer higher priority nodes
        6. Prefer higher capacity nodes

        Args:
            cluster: Cluster configuration
            policy: Failover policy
            primary: Current primary node

        Returns:
            Best failover target or None
        """
        candidates = [
            node
            for node in cluster.nodes
            if node.node_id != primary.node_id
            and node.role == NodeRole.SECONDARY
            and node.status == NodeStatus.HEALTHY
        ]

        if not candidates:
            return None

        # Score candidates
        scored = []
        for node in candidates:
            score = self._score_candidate(node, policy)
            scored.append((score, node))

        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)

        return scored[0][1] if scored else None

    def _score_candidate(self, node: Node, policy: FailoverPolicy) -> float:
        """
        Score a candidate node for failover.

        Higher score = better candidate.

        Args:
            node: Candidate node
            policy: Failover policy

        Returns:
            Candidate score
        """
        score = 0.0

        # Region priority (1000 points per position)
        if policy.region_priority:
            try:
                region_idx = policy.region_priority.index(node.region)
                score += 1000.0 * (len(policy.region_priority) - region_idx)
            except ValueError:
                pass  # Region not in priority list

        # Site priority (500 points per position)
        if policy.site_priority:
            try:
                site_idx = policy.site_priority.index(node.site)
                score += 500.0 * (len(policy.site_priority) - site_idx)
            except ValueError:
                pass  # Site not in priority list

        # Node priority (direct addition)
        score += float(node.priority)

        # Capacity (0-100 points)
        score += node.capacity

        return score

    def _generate_actions(
        self,
        primary: Node,
        target: Node,
        cluster: Cluster,
        policy: FailoverPolicy,
    ) -> list[FailoverAction]:
        """
        Generate ordered failover actions.

        Standard failover sequence:
        1. Demote primary
        2. Promote target
        3. Update DNS
        4. Notify operators
        5. Verify failover

        Args:
            primary: Current primary node
            target: Failover target node
            cluster: Cluster configuration
            policy: Failover policy

        Returns:
            Ordered list of failover actions
        """
        actions = []
        sequence = 0

        # Action 1: Demote primary
        actions.append(
            FailoverAction(
                action_id=str(uuid.uuid4()),
                action_type=ActionType.DEMOTE,
                target_node_id=primary.node_id,
                params={"role": "secondary"},
                sequence=sequence,
                estimated_duration_ms=5000,
            )
        )
        sequence += 1

        # Action 2: Promote target
        actions.append(
            FailoverAction(
                action_id=str(uuid.uuid4()),
                action_type=ActionType.PROMOTE,
                target_node_id=target.node_id,
                params={"role": "primary"},
                sequence=sequence,
                estimated_duration_ms=10000,
            )
        )
        sequence += 1

        # Action 3: DNS flip
        actions.append(
            FailoverAction(
                action_id=str(uuid.uuid4()),
                action_type=ActionType.DNS_FLIP,
                target_node_id=target.node_id,
                params={
                    "old_ip": primary.hostname,
                    "new_ip": target.hostname,
                    "ttl": 60,
                },
                sequence=sequence,
                estimated_duration_ms=15000,
            )
        )
        sequence += 1

        # Action 4: Notify
        actions.append(
            FailoverAction(
                action_id=str(uuid.uuid4()),
                action_type=ActionType.NOTIFY,
                target_node_id=target.node_id,
                params={
                    "message": f"Failover from {primary.node_id} to {target.node_id}",
                    "channels": ["ops", "audit"],
                },
                sequence=sequence,
                estimated_duration_ms=2000,
            )
        )
        sequence += 1

        # Action 5: Verify
        actions.append(
            FailoverAction(
                action_id=str(uuid.uuid4()),
                action_type=ActionType.VERIFY,
                target_node_id=target.node_id,
                params={"checks": ["quorum", "consistency", "policy"]},
                sequence=sequence,
                estimated_duration_ms=8000,
            )
        )

        return actions


__all__ = ["ContinuityPlanner"]
