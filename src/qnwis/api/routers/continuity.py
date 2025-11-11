"""
Business Continuity & Failover API endpoints with RBAC.

Routes (RBAC: admin/service):
- GET /api/v1/continuity/plan
- POST /api/v1/continuity/execute
- GET /api/v1/continuity/status
- GET /api/v1/continuity/audit
- POST /api/v1/continuity/simulate
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from qnwis.continuity.audit import ContinuityAuditor
from qnwis.continuity.executor import FailoverExecutor
from qnwis.continuity.heartbeat import HeartbeatMonitor
from qnwis.continuity.models import (
    Cluster,
    FailoverPolicy,
    Node,
    NodeRole,
    NodeStatus,
)
from qnwis.continuity.planner import ContinuityPlanner
from qnwis.continuity.simulate import FailoverSimulator
from qnwis.continuity.verifier import FailoverVerifier
from qnwis.security.rbac import require_roles
from qnwis.utils.clock import Clock

from ._shared import get_clock

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/continuity", tags=["continuity"])


# ============================================================================
# Request/Response Models
# ============================================================================


class PlanRequest(BaseModel):
    """Request to generate continuity plan."""

    cluster: dict[str, Any] = Field(..., description="Cluster configuration")
    policy: dict[str, Any] = Field(..., description="Failover policy")
    trigger_reason: str = Field(default="manual", description="Failover trigger reason")


class PlanResponse(BaseModel):
    """Response for plan generation."""

    request_id: str = Field(..., description="Request identifier")
    plan_id: str = Field(..., description="Generated plan ID")
    cluster_id: str = Field(..., description="Cluster ID")
    policy_id: str = Field(..., description="Policy ID")
    primary_node_id: str = Field(..., description="Current primary node")
    failover_target_id: str = Field(..., description="Failover target node")
    estimated_total_ms: int = Field(..., description="Estimated execution time (ms)")
    action_count: int = Field(..., description="Number of actions")
    timings_ms: dict[str, int] = Field(default_factory=dict, description="Timing breakdown")


class ExecuteRequest(BaseModel):
    """Request to execute failover plan."""

    plan: dict[str, Any] = Field(..., description="Continuity plan")
    dry_run: bool = Field(default=False, description="Dry-run mode")


class ExecuteResponse(BaseModel):
    """Response for failover execution."""

    request_id: str = Field(..., description="Request identifier")
    execution_id: str = Field(..., description="Execution ID")
    plan_id: str = Field(..., description="Plan ID")
    success: bool = Field(..., description="Execution success")
    actions_executed: int = Field(..., description="Actions executed")
    actions_failed: int = Field(..., description="Actions failed")
    total_duration_ms: int = Field(..., description="Total duration (ms)")
    audit_id: str | None = Field(None, description="Audit pack ID")
    confidence: dict[str, Any] = Field(default_factory=dict, description="Confidence scoring")
    timings_ms: dict[str, int] = Field(default_factory=dict, description="Timing breakdown")


class StatusRequest(BaseModel):
    """Request for cluster status."""

    cluster: dict[str, Any] = Field(..., description="Cluster configuration")


class StatusResponse(BaseModel):
    """Response for cluster status."""

    request_id: str = Field(..., description="Request identifier")
    cluster_id: str = Field(..., description="Cluster ID")
    total_nodes: int = Field(..., description="Total nodes")
    healthy_nodes: int = Field(..., description="Healthy nodes")
    quorum_size: int = Field(..., description="Required quorum size")
    has_quorum: bool = Field(..., description="Quorum achieved")
    primary_node_id: str | None = Field(None, description="Current primary node")
    timings_ms: dict[str, int] = Field(default_factory=dict, description="Timing breakdown")


class AuditResponse(BaseModel):
    """Response for audit pack retrieval."""

    request_id: str = Field(..., description="Request identifier")
    audit_id: str = Field(..., description="Audit pack ID")
    timestamp: str = Field(..., description="Audit timestamp")
    execution: dict[str, Any] = Field(default_factory=dict, description="Execution summary")
    verification: dict[str, Any] = Field(default_factory=dict, description="Verification summary")
    confidence: dict[str, Any] = Field(default_factory=dict, description="Confidence scoring")
    timings_ms: dict[str, int] = Field(default_factory=dict, description="Timing breakdown")


class SimulateRequest(BaseModel):
    """Request for failover simulation."""

    cluster: dict[str, Any] = Field(..., description="Cluster configuration")
    policy: dict[str, Any] = Field(..., description="Failover policy")
    scenario: str = Field(default="primary_failure", description="Simulation scenario")
    seed: int = Field(default=42, description="Random seed")


class SimulateResponse(BaseModel):
    """Response for failover simulation."""

    request_id: str = Field(..., description="Request identifier")
    scenario: str = Field(..., description="Simulation scenario")
    success: bool = Field(..., description="Simulation success")
    failover: dict[str, Any] = Field(default_factory=dict, description="Failover results")
    verification: dict[str, Any] = Field(default_factory=dict, description="Verification results")
    timings_ms: dict[str, int] = Field(default_factory=dict, description="Timing breakdown")


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/plan", response_model=PlanResponse, dependencies=[Depends(require_roles(["admin", "service"]))])
async def generate_plan(
    request: PlanRequest,
    clock: Clock = Depends(get_clock),
) -> PlanResponse:
    """
    Generate continuity plan from cluster and policy configuration.

    Requires admin or service role.
    """
    request_id = str(uuid.uuid4())
    start_time = clock.time()

    try:
        # Parse cluster and policy
        cluster = _parse_cluster(request.cluster)
        policy = _parse_policy(request.policy)

        # Generate plan
        planner = ContinuityPlanner(clock=clock)
        plan = planner.build_plan(cluster, policy, trigger_reason=request.trigger_reason)

        # Calculate timings
        end_time = clock.time()
        total_ms = int((end_time - start_time) * 1000)

        return PlanResponse(
            request_id=request_id,
            plan_id=plan.plan_id,
            cluster_id=plan.cluster_id,
            policy_id=plan.policy_id,
            primary_node_id=plan.primary_node_id,
            failover_target_id=plan.failover_target_id,
            estimated_total_ms=plan.estimated_total_ms,
            action_count=len(plan.actions),
            timings_ms={"total": total_ms, "planning": total_ms},
        )

    except ValueError as exc:
        logger.error("Plan generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan generation failed: {exc!s}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in plan generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc


@router.post("/execute", response_model=ExecuteResponse, dependencies=[Depends(require_roles(["admin", "service"]))])
async def execute_plan(
    request: ExecuteRequest,
    clock: Clock = Depends(get_clock),
) -> ExecuteResponse:
    """
    Execute failover plan.

    Requires admin or service role.
    """
    request_id = str(uuid.uuid4())
    start_time = clock.time()

    try:
        # Parse plan
        plan = _parse_plan(request.plan)

        # Execute plan
        executor = FailoverExecutor(clock=clock, dry_run=request.dry_run)
        result = executor.execute_plan(plan)

        # Generate audit pack if successful
        audit_id = None
        confidence = {}
        if result.success:
            # Parse cluster and policy for verification
            cluster = _parse_cluster(request.plan.get("cluster", {}))
            policy = _parse_policy(request.plan.get("policy", {}))

            # Verify execution
            verifier = FailoverVerifier(clock=clock)
            verification = verifier.verify_failover(result, cluster, policy)

            # Generate audit
            auditor = ContinuityAuditor(clock=clock)
            audit_pack = auditor.generate_audit_pack(plan, result, verification)
            audit_id = audit_pack["audit_id"]
            confidence = audit_pack["confidence"]

        # Calculate timings
        end_time = clock.time()
        total_ms = int((end_time - start_time) * 1000)

        return ExecuteResponse(
            request_id=request_id,
            execution_id=result.execution_id,
            plan_id=result.plan_id,
            success=result.success,
            actions_executed=result.actions_executed,
            actions_failed=result.actions_failed,
            total_duration_ms=result.total_duration_ms,
            audit_id=audit_id,
            confidence=confidence,
            timings_ms={"total": total_ms, "execution": result.total_duration_ms},
        )

    except Exception as exc:
        logger.exception("Unexpected error in plan execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc


@router.post("/status", response_model=StatusResponse, dependencies=[Depends(require_roles(["admin", "service"]))])
async def get_status(
    request: StatusRequest,
    clock: Clock = Depends(get_clock),
) -> StatusResponse:
    """
    Get cluster and quorum status.

    Requires admin or service role.
    """
    request_id = str(uuid.uuid4())
    start_time = clock.time()

    try:
        # Parse cluster
        cluster = _parse_cluster(request.cluster)

        # Simulate heartbeats
        monitor = HeartbeatMonitor(clock=clock)
        monitor.simulate_heartbeats(cluster.nodes)

        # Calculate quorum
        quorum_status = monitor.calculate_quorum(cluster)

        # Find primary
        primary_node_id = None
        for node in cluster.nodes:
            if node.role == NodeRole.PRIMARY:
                primary_node_id = node.node_id
                break

        # Calculate timings
        end_time = clock.time()
        total_ms = int((end_time - start_time) * 1000)

        return StatusResponse(
            request_id=request_id,
            cluster_id=cluster.cluster_id,
            total_nodes=quorum_status.total_nodes,
            healthy_nodes=quorum_status.healthy_nodes,
            quorum_size=quorum_status.quorum_size,
            has_quorum=quorum_status.has_quorum,
            primary_node_id=primary_node_id,
            timings_ms={"total": total_ms},
        )

    except Exception as exc:
        logger.exception("Unexpected error in status check")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc


@router.post("/simulate", response_model=SimulateResponse, dependencies=[Depends(require_roles(["admin", "service"]))])
async def simulate_failover(
    request: SimulateRequest,
    clock: Clock = Depends(get_clock),
) -> SimulateResponse:
    """
    Run deterministic failover simulation.

    Requires admin or service role.
    """
    request_id = str(uuid.uuid4())
    start_time = clock.time()

    try:
        # Parse cluster and policy
        cluster = _parse_cluster(request.cluster)
        policy = _parse_policy(request.policy)

        # Run simulation
        simulator = FailoverSimulator(seed=request.seed)

        if request.scenario == "primary_failure":
            result = simulator.simulate_primary_failure(cluster, policy)
        elif request.scenario == "random_failures":
            result = simulator.simulate_random_failures(cluster, policy, failure_count=1)
        else:
            raise ValueError(f"Unknown scenario: {request.scenario}")

        # Calculate timings
        end_time = clock.time()
        total_ms = int((end_time - start_time) * 1000)

        return SimulateResponse(
            request_id=request_id,
            scenario=result.scenario,
            success=result.success,
            failover={
                "execution_id": result.failover_result.execution_id,
                "success": result.failover_result.success,
                "actions_executed": result.failover_result.actions_executed,
                "total_duration_ms": result.failover_result.total_duration_ms,
            },
            verification={
                "report_id": result.verification_report.report_id,
                "passed": result.verification_report.passed,
                "consistency_ok": result.verification_report.consistency_ok,
                "policy_ok": result.verification_report.policy_ok,
                "quorum_ok": result.verification_report.quorum_ok,
            },
            timings_ms={"total": total_ms, "simulation": result.failover_result.total_duration_ms},
        )

    except Exception as exc:
        logger.exception("Unexpected error in simulation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_cluster(data: dict[str, Any]) -> Cluster:
    """Parse cluster from dictionary."""
    nodes = []
    for node_data in data.get("nodes", []):
        nodes.append(
            Node(
                node_id=node_data["node_id"],
                hostname=node_data["hostname"],
                role=NodeRole(node_data["role"]),
                region=node_data["region"],
                site=node_data["site"],
                status=NodeStatus(node_data.get("status", "healthy")),
                priority=node_data.get("priority", 100),
                capacity=node_data.get("capacity", 100.0),
                metadata=node_data.get("metadata", {}),
            )
        )

    return Cluster(
        cluster_id=data["cluster_id"],
        name=data["name"],
        nodes=nodes,
        quorum_size=data.get("quorum_size", (len(nodes) // 2) + 1),
        regions=data.get("regions", []),
        metadata=data.get("metadata", {}),
    )


def _parse_policy(data: dict[str, Any]) -> FailoverPolicy:
    """Parse policy from dictionary."""
    from qnwis.continuity.models import FailoverStrategy

    return FailoverPolicy(
        policy_id=data["policy_id"],
        name=data["name"],
        strategy=FailoverStrategy(data["strategy"]),
        max_failover_time_s=data.get("max_failover_time_s", 60),
        require_quorum=data.get("require_quorum", True),
        region_priority=data.get("region_priority", []),
        site_priority=data.get("site_priority", []),
        min_healthy_nodes=data.get("min_healthy_nodes", 1),
        metadata=data.get("metadata", {}),
    )


def _parse_plan(data: dict[str, Any]) -> Any:
    """Parse plan from dictionary."""
    from qnwis.continuity.models import ActionType, ContinuityPlan, FailoverAction

    actions = []
    for action_data in data.get("actions", []):
        actions.append(
            FailoverAction(
                action_id=action_data["action_id"],
                action_type=ActionType(action_data["action_type"]),
                target_node_id=action_data["target_node_id"],
                params=action_data.get("params", {}),
                sequence=action_data["sequence"],
                estimated_duration_ms=action_data["estimated_duration_ms"],
            )
        )

    return ContinuityPlan(
        plan_id=data["plan_id"],
        cluster_id=data["cluster_id"],
        policy_id=data["policy_id"],
        created_at=data["created_at"],
        actions=actions,
        estimated_total_ms=data["estimated_total_ms"],
        primary_node_id=data["primary_node_id"],
        failover_target_id=data["failover_target_id"],
        metadata=data.get("metadata", {}),
    )


__all__ = ["router"]
