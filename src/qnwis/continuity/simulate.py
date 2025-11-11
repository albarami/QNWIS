"""
Deterministic failover simulator.

What-if simulator with seeded random fault injection for testing
failover scenarios.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from qnwis.continuity.executor import FailoverExecutor
from qnwis.continuity.heartbeat import HeartbeatMonitor
from qnwis.continuity.models import (
    Cluster,
    Node,
    NodeRole,
    NodeStatus,
)
from qnwis.continuity.planner import ContinuityPlanner
from qnwis.continuity.verifier import FailoverVerifier
from qnwis.utils.clock import ManualClock

if TYPE_CHECKING:
    from qnwis.continuity.models import (
        ContinuityPlan,
        FailoverPolicy,
        FailoverResult,
        VerificationReport,
    )


class SimulationResult:
    """
    Complete simulation result.

    Attributes:
        scenario: Scenario description
        cluster: Cluster state after simulation
        failover_result: Failover execution result
        verification_report: Post-failover verification
        success: Overall simulation success
    """

    def __init__(
        self,
        scenario: str,
        cluster: Cluster,
        failover_result: FailoverResult,
        verification_report: VerificationReport,
    ) -> None:
        """Initialize simulation result."""
        self.scenario = scenario
        self.cluster = cluster
        self.failover_result = failover_result
        self.verification_report = verification_report
        self.success = failover_result.success and verification_report.passed


class FailoverSimulator:
    """
    Deterministic failover simulator.

    Simulates various failure scenarios with seeded random number
    generation for reproducibility.
    """

    def __init__(self, seed: int = 42) -> None:
        """
        Initialize failover simulator.

        Args:
            seed: Random seed for deterministic simulation
        """
        self._seed = seed
        self._rng = random.Random(seed)
        self._clock = ManualClock()

    def simulate_primary_failure(
        self,
        cluster: Cluster,
        policy: FailoverPolicy,
    ) -> SimulationResult:
        """
        Simulate primary node failure scenario.

        Args:
            cluster: Cluster configuration
            policy: Failover policy

        Returns:
            Simulation result
        """
        # Mark primary as failed
        modified_nodes = []
        for node in cluster.nodes:
            if node.role.value == "primary":
                # Create new node with failed status
                modified_node = Node(
                    node_id=node.node_id,
                    hostname=node.hostname,
                    role=node.role,
                    region=node.region,
                    site=node.site,
                    status=NodeStatus.FAILED,
                    priority=node.priority,
                    capacity=node.capacity,
                    metadata=node.metadata,
                )
                modified_nodes.append(modified_node)
            else:
                modified_nodes.append(node)

        modified_cluster = Cluster(
            cluster_id=cluster.cluster_id,
            name=cluster.name,
            nodes=modified_nodes,
            quorum_size=cluster.quorum_size,
            regions=cluster.regions,
            metadata=cluster.metadata,
        )

        return self._run_simulation(
            scenario="primary_failure",
            cluster=modified_cluster,
            policy=policy,
        )

    def simulate_random_failures(
        self,
        cluster: Cluster,
        policy: FailoverPolicy,
        failure_count: int = 1,
    ) -> SimulationResult:
        """
        Simulate random node failures.

        Args:
            cluster: Cluster configuration
            policy: Failover policy
            failure_count: Number of nodes to fail

        Returns:
            Simulation result
        """
        # Select random nodes to fail (excluding primary)
        non_primary_nodes = [
            node for node in cluster.nodes if node.role.value != "primary"
        ]

        if failure_count > len(non_primary_nodes):
            failure_count = len(non_primary_nodes)

        failed_nodes = self._rng.sample(non_primary_nodes, failure_count)
        failed_ids = {node.node_id for node in failed_nodes}

        # Create modified cluster
        modified_nodes = []
        for node in cluster.nodes:
            if node.node_id in failed_ids:
                modified_node = Node(
                    node_id=node.node_id,
                    hostname=node.hostname,
                    role=node.role,
                    region=node.region,
                    site=node.site,
                    status=NodeStatus.FAILED,
                    priority=node.priority,
                    capacity=node.capacity,
                    metadata=node.metadata,
                )
                modified_nodes.append(modified_node)
            else:
                modified_nodes.append(node)

        modified_cluster = Cluster(
            cluster_id=cluster.cluster_id,
            name=cluster.name,
            nodes=modified_nodes,
            quorum_size=cluster.quorum_size,
            regions=cluster.regions,
            metadata=cluster.metadata,
        )

        return self._run_simulation(
            scenario=f"random_failures_{failure_count}",
            cluster=modified_cluster,
            policy=policy,
        )

    def simulate_region_failure(
        self,
        cluster: Cluster,
        policy: FailoverPolicy,
        region: str,
    ) -> SimulationResult:
        """
        Simulate entire region failure.

        Args:
            cluster: Cluster configuration
            policy: Failover policy
            region: Region to fail

        Returns:
            Simulation result
        """
        # Mark all nodes in region as failed
        modified_nodes = []
        for node in cluster.nodes:
            if node.region == region:
                modified_node = Node(
                    node_id=node.node_id,
                    hostname=node.hostname,
                    role=node.role,
                    region=node.region,
                    site=node.site,
                    status=NodeStatus.FAILED,
                    priority=node.priority,
                    capacity=node.capacity,
                    metadata=node.metadata,
                )
                modified_nodes.append(modified_node)
            else:
                modified_nodes.append(node)

        modified_cluster = Cluster(
            cluster_id=cluster.cluster_id,
            name=cluster.name,
            nodes=modified_nodes,
            quorum_size=cluster.quorum_size,
            regions=cluster.regions,
            metadata=cluster.metadata,
        )

        return self._run_simulation(
            scenario=f"region_failure_{region}",
            cluster=modified_cluster,
            policy=policy,
        )

    def _run_simulation(
        self,
        scenario: str,
        cluster: Cluster,
        policy: FailoverPolicy,
    ) -> SimulationResult:
        """
        Run complete failover simulation.

        Args:
            scenario: Scenario description
            cluster: Cluster configuration (with failures injected)
            policy: Failover policy

        Returns:
            Simulation result
        """
        # Initialize components with shared clock
        heartbeat_monitor = HeartbeatMonitor(clock=self._clock)
        planner = ContinuityPlanner(clock=self._clock)
        executor = FailoverExecutor(clock=self._clock, dry_run=True)
        verifier = FailoverVerifier(
            clock=self._clock,
            heartbeat_monitor=heartbeat_monitor,
        )

        # Simulate heartbeats
        heartbeat_monitor.simulate_heartbeats(cluster.nodes)

        # Build plan
        try:
            plan = planner.build_plan(cluster, policy, trigger_reason=scenario)
        except ValueError as e:
            # Plan generation failed - create dummy result
            from qnwis.continuity.models import FailoverResult

            failover_result = FailoverResult(
                execution_id="sim-failed",
                plan_id="none",
                started_at=self._clock.utcnow(),
                completed_at=self._clock.utcnow(),
                success=False,
                actions_executed=0,
                actions_failed=0,
                total_duration_ms=0,
                errors=[f"Plan generation failed: {e!s}"],
            )

            from qnwis.continuity.models import VerificationReport

            verification_report = VerificationReport(
                report_id="sim-failed",
                execution_id="sim-failed",
                verified_at=self._clock.utcnow(),
                consistency_ok=False,
                policy_ok=False,
                quorum_ok=False,
                freshness_ok=False,
                errors=[f"Simulation failed: {e!s}"],
                warnings=[],
            )

            return SimulationResult(
                scenario=scenario,
                cluster=cluster,
                failover_result=failover_result,
                verification_report=verification_report,
            )

        # Execute plan
        self._clock.advance(0.1)  # Advance time slightly
        failover_result = executor.execute_plan(plan)

        post_failover_cluster = self._project_failover_state(cluster, plan)

        # Verify result
        self._clock.advance(0.1)
        verification_report = verifier.verify_failover(
            failover_result, post_failover_cluster, policy
        )

        return SimulationResult(
            scenario=scenario,
            cluster=post_failover_cluster,
            failover_result=failover_result,
            verification_report=verification_report,
        )

    def reset_seed(self, seed: int | None = None) -> None:
        """
        Reset random seed for new simulation.

        Args:
            seed: New seed (default: use original seed)
        """
        if seed is not None:
            self._seed = seed
        self._rng = random.Random(self._seed)
        self._clock = ManualClock()

    def _project_failover_state(self, cluster: Cluster, plan: ContinuityPlan) -> Cluster:
        """
        Project post-failover cluster state based on the executed plan.
        """
        if not plan.failover_target_id:
            return cluster

        updated_nodes: list[Node] = []
        for node in cluster.nodes:
            if node.node_id == plan.failover_target_id:
                updated_nodes.append(
                    node.model_copy(
                        update={
                            "role": NodeRole.PRIMARY,
                            "status": NodeStatus.HEALTHY,
                        }
                    )
                )
            elif node.node_id == plan.primary_node_id:
                demoted_status = (
                    NodeStatus.DEGRADED if node.status == NodeStatus.FAILED else node.status
                )
                updated_nodes.append(
                    node.model_copy(
                        update={
                            "role": NodeRole.SECONDARY,
                            "status": demoted_status,
                        }
                    )
                )
            else:
                updated_nodes.append(node)
        return cluster.model_copy(update={"nodes": updated_nodes})


__all__ = [
    "FailoverSimulator",
    "SimulationResult",
]
