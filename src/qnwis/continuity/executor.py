"""
Failover executor.

Executes failover actions deterministically without external subprocess calls.
Simulates DNS flips, service promotion/demotion, and audit logging.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from qnwis.continuity.models import (
    ActionType,
    FailoverResult,
)
from qnwis.utils.clock import Clock

if TYPE_CHECKING:
    from qnwis.continuity.models import ContinuityPlan, FailoverAction


class FailoverExecutor:
    """
    Executes failover plans deterministically.

    Simulates all actions without external dependencies for testing.
    In production, would integrate with actual infrastructure APIs.
    """

    def __init__(self, clock: Clock | None = None, dry_run: bool = False) -> None:
        """
        Initialize failover executor.

        Args:
            clock: Clock instance for deterministic time (default: system clock)
            dry_run: If True, simulate without making changes
        """
        self._clock = clock or Clock()
        self._dry_run = dry_run
        self._execution_log: list[dict[str, str]] = []

    def execute_plan(self, plan: ContinuityPlan) -> FailoverResult:
        """
        Execute a continuity plan.

        Args:
            plan: Continuity plan to execute

        Returns:
            Failover execution result
        """
        execution_id = str(uuid.uuid4())
        started_at = self._clock.utcnow()
        start_time = self._clock.time()

        actions_executed = 0
        actions_failed = 0
        errors: list[str] = []

        self._execution_log.clear()

        # Execute actions in sequence
        for action in sorted(plan.actions, key=lambda a: a.sequence):
            try:
                self._execute_action(action, plan)
                actions_executed += 1
            except Exception as e:
                actions_failed += 1
                errors.append(f"Action {action.action_id} failed: {e!s}")
                # Continue with remaining actions for resilience

        # Calculate actual duration
        end_time = self._clock.time()
        total_duration_ms = int((end_time - start_time) * 1000)

        completed_at = self._clock.utcnow()
        success = actions_failed == 0

        return FailoverResult(
            execution_id=execution_id,
            plan_id=plan.plan_id,
            started_at=started_at,
            completed_at=completed_at,
            success=success,
            actions_executed=actions_executed,
            actions_failed=actions_failed,
            total_duration_ms=total_duration_ms,
            errors=errors,
            metadata={
                "dry_run": self._dry_run,
                "cluster_id": plan.cluster_id,
                "policy_id": plan.policy_id,
            },
        )

    def _execute_action(self, action: FailoverAction, plan: ContinuityPlan) -> None:
        """
        Execute a single failover action.

        Args:
            action: Action to execute
            plan: Parent continuity plan

        Raises:
            ValueError: If action type is unknown
        """
        if action.action_type == ActionType.DEMOTE:
            self._execute_demote(action)
        elif action.action_type == ActionType.PROMOTE:
            self._execute_promote(action)
        elif action.action_type == ActionType.DNS_FLIP:
            self._execute_dns_flip(action)
        elif action.action_type == ActionType.NOTIFY:
            self._execute_notify(action)
        elif action.action_type == ActionType.VERIFY:
            self._execute_verify(action)
        elif action.action_type == ActionType.RESTART:
            self._execute_restart(action)
        else:
            raise ValueError(f"Unknown action type: {action.action_type}")

        # Log action execution
        self._execution_log.append(
            {
                "action_id": action.action_id,
                "action_type": action.action_type.value,
                "target_node_id": action.target_node_id,
                "timestamp": self._clock.utcnow(),
            }
        )

    def _execute_demote(self, action: FailoverAction) -> None:
        """
        Execute demote action.

        Simulates demoting a primary node to secondary.

        Args:
            action: Demote action
        """
        if self._dry_run:
            return

        # Simulate demote operation
        # In production: call infrastructure API to demote node
        # Simulated operation - no actual changes
        pass

    def _execute_promote(self, action: FailoverAction) -> None:
        """
        Execute promote action.

        Simulates promoting a secondary node to primary.

        Args:
            action: Promote action
        """
        if self._dry_run:
            return

        # Simulate promote operation
        # In production: call infrastructure API to promote node
        # Simulated operation - no actual changes
        pass

    def _execute_dns_flip(self, action: FailoverAction) -> None:
        """
        Execute DNS flip action.

        Simulates updating DNS records to point to new primary.

        Args:
            action: DNS flip action
        """
        if self._dry_run:
            return

        # Simulate DNS update
        # In production: call DNS API to update records
        # Simulated operation - no actual changes
        pass

    def _execute_notify(self, action: FailoverAction) -> None:
        """
        Execute notify action.

        Simulates sending notifications to operators.

        Args:
            action: Notify action
        """
        if self._dry_run:
            return

        # Simulate notification
        # In production: call notification service
        # Simulated operation - no actual changes
        pass

    def _execute_verify(self, action: FailoverAction) -> None:
        """
        Execute verify action.

        Simulates post-action verification checks.

        Args:
            action: Verify action
        """
        # Verification is always performed, even in dry-run
        # Simulated verification - always passes in simulation
        pass

    def _execute_restart(self, action: FailoverAction) -> None:
        """
        Execute restart action.

        Simulates restarting a service on a node.

        Args:
            action: Restart action
        """
        if self._dry_run:
            return

        # Simulate service restart
        # In production: call service management API
        # Simulated operation - no actual changes
        pass

    def get_execution_log(self) -> list[dict[str, str]]:
        """
        Get execution log.

        Returns:
            List of executed actions with timestamps
        """
        return list(self._execution_log)


__all__ = ["FailoverExecutor"]
