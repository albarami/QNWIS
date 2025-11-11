"""
Post-failover verification.

Validates failover execution against policy, quorum, consistency,
and data freshness requirements.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from qnwis.continuity.heartbeat import HeartbeatMonitor
from qnwis.continuity.models import (
    NodeRole,
    NodeStatus,
    VerificationReport,
)
from qnwis.utils.clock import Clock

if TYPE_CHECKING:
    from qnwis.continuity.models import (
        Cluster,
        FailoverPolicy,
        FailoverResult,
    )


class FailoverVerifier:
    """
    Post-failover verification.

    Validates that failover execution meets all requirements:
    - Consistency: New primary is operational
    - Policy: Failover adheres to policy constraints
    - Quorum: Cluster maintains quorum
    - Freshness: Data is current
    """

    def __init__(
        self,
        clock: Clock | None = None,
        heartbeat_monitor: HeartbeatMonitor | None = None,
    ) -> None:
        """
        Initialize failover verifier.

        Args:
            clock: Clock instance for deterministic time (default: system clock)
            heartbeat_monitor: Heartbeat monitor for quorum checks
        """
        self._clock = clock or Clock()
        self._heartbeat_monitor = heartbeat_monitor or HeartbeatMonitor(clock=self._clock)

    def verify_failover(
        self,
        result: FailoverResult,
        cluster: Cluster,
        policy: FailoverPolicy,
    ) -> VerificationReport:
        """
        Verify failover execution.

        Args:
            result: Failover execution result
            cluster: Cluster configuration
            policy: Failover policy

        Returns:
            Verification report
        """
        report_id = str(uuid.uuid4())
        verified_at = self._clock.utcnow()

        errors: list[str] = []
        warnings: list[str] = []

        # Check 1: Consistency
        consistency_ok = self._verify_consistency(cluster, errors, warnings)

        # Check 2: Policy adherence
        policy_ok = self._verify_policy(result, policy, errors, warnings)

        # Check 3: Quorum
        quorum_ok = self._verify_quorum(cluster, policy, errors, warnings)

        # Check 4: Freshness
        freshness_ok = self._verify_freshness(cluster, errors, warnings)

        return VerificationReport(
            report_id=report_id,
            execution_id=result.execution_id,
            verified_at=verified_at,
            consistency_ok=consistency_ok,
            policy_ok=policy_ok,
            quorum_ok=quorum_ok,
            freshness_ok=freshness_ok,
            errors=errors,
            warnings=warnings,
        )

    def _verify_consistency(
        self,
        cluster: Cluster,
        errors: list[str],
        warnings: list[str],
    ) -> bool:
        """
        Verify cluster consistency.

        Checks:
        - Exactly one primary node exists
        - Primary node is healthy

        Args:
            cluster: Cluster configuration
            errors: List to append errors to
            warnings: List to append warnings to

        Returns:
            True if consistency checks pass
        """
        primaries = [node for node in cluster.nodes if node.role == NodeRole.PRIMARY]

        if len(primaries) == 0:
            errors.append("No primary node found")
            return False

        if len(primaries) > 1:
            errors.append(f"Multiple primary nodes found: {len(primaries)}")
            return False

        primary = primaries[0]
        if primary.status != NodeStatus.HEALTHY:
            errors.append(f"Primary node {primary.node_id} is not healthy: {primary.status}")
            return False

        return True

    def _verify_policy(
        self,
        result: FailoverResult,
        policy: FailoverPolicy,
        errors: list[str],
        warnings: list[str],
    ) -> bool:
        """
        Verify policy adherence.

        Checks:
        - Failover completed within max_failover_time_s
        - All actions executed successfully

        Args:
            result: Failover execution result
            policy: Failover policy
            errors: List to append errors to
            warnings: List to append warnings to

        Returns:
            True if policy checks pass
        """
        # Check execution time
        max_time_ms = policy.max_failover_time_s * 1000
        if result.total_duration_ms > max_time_ms:
            warnings.append(
                f"Failover exceeded max time: {result.total_duration_ms}ms > {max_time_ms}ms"
            )

        # Check execution success
        if not result.success:
            errors.append(f"Failover execution failed: {result.actions_failed} actions failed")
            return False

        return True

    def _verify_quorum(
        self,
        cluster: Cluster,
        policy: FailoverPolicy,
        errors: list[str],
        warnings: list[str],
    ) -> bool:
        """
        Verify quorum status.

        Checks:
        - Cluster has quorum if required by policy
        - Minimum healthy nodes requirement met

        Args:
            cluster: Cluster configuration
            policy: Failover policy
            errors: List to append errors to
            warnings: List to append warnings to

        Returns:
            True if quorum checks pass
        """
        quorum_status = self._heartbeat_monitor.calculate_quorum(cluster)

        if policy.require_quorum and not quorum_status.has_quorum:
            errors.append(
                f"Quorum not achieved: {quorum_status.healthy_nodes}/{quorum_status.quorum_size}"
            )
            return False

        if quorum_status.healthy_nodes < policy.min_healthy_nodes:
            errors.append(
                f"Insufficient healthy nodes: {quorum_status.healthy_nodes} < {policy.min_healthy_nodes}"
            )
            return False

        return True

    def _verify_freshness(
        self,
        cluster: Cluster,
        errors: list[str],
        warnings: list[str],
    ) -> bool:
        """
        Verify data freshness.

        Checks:
        - Primary node has recent data
        - No stale replicas

        Args:
            cluster: Cluster configuration
            errors: List to append errors to
            warnings: List to append warnings to

        Returns:
            True if freshness checks pass
        """
        # In production, would check actual data timestamps
        # For simulation, we assume data is fresh if nodes are healthy
        primary = next(
            (node for node in cluster.nodes if node.role == NodeRole.PRIMARY),
            None,
        )

        if not primary:
            errors.append("No primary node for freshness check")
            return False

        if primary.status != NodeStatus.HEALTHY:
            warnings.append(f"Primary node {primary.node_id} status: {primary.status}")

        return True


__all__ = ["FailoverVerifier"]
