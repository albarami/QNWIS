"""
Pydantic models for Business Continuity & Failover Orchestration.

All models are frozen and include NaN/Inf guards for numeric fields.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NodeStatus(str, Enum):
    """Node operational status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class NodeRole(str, Enum):
    """Node role in cluster."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    WITNESS = "witness"


class FailoverStrategy(str, Enum):
    """Failover strategy type."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    QUORUM_BASED = "quorum_based"


class ActionType(str, Enum):
    """Failover action type."""

    DNS_FLIP = "dns_flip"
    PROMOTE = "promote"
    DEMOTE = "demote"
    RESTART = "restart"
    NOTIFY = "notify"
    VERIFY = "verify"


class Node(BaseModel):
    """
    Single node in a cluster.

    Attributes:
        node_id: Unique node identifier
        hostname: Node hostname or IP
        role: Node role (primary, secondary, witness)
        region: Geographic region
        site: Site identifier within region
        status: Current operational status
        priority: Failover priority (higher = preferred)
        capacity: Node capacity percentage (0-100)
        metadata: Additional node metadata
    """

    node_id: str = Field(..., description="Unique node identifier")
    hostname: str = Field(..., description="Node hostname or IP")
    role: NodeRole = Field(..., description="Node role")
    region: str = Field(..., description="Geographic region")
    site: str = Field(..., description="Site identifier")
    status: NodeStatus = Field(default=NodeStatus.UNKNOWN, description="Operational status")
    priority: int = Field(default=100, description="Failover priority")
    capacity: float = Field(default=100.0, description="Capacity percentage")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, v: int) -> int:
        if v < 0 or v > 1000:
            raise ValueError("Priority must be between 0 and 1000")
        return v

    @field_validator("capacity")
    @classmethod
    def _validate_capacity(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Capacity cannot be NaN or Inf")
        if v < 0.0 or v > 100.0:
            raise ValueError("Capacity must be between 0 and 100")
        return v

    model_config = ConfigDict(frozen=True)


class Cluster(BaseModel):
    """
    Cluster topology configuration.

    Attributes:
        cluster_id: Unique cluster identifier
        name: Human-readable cluster name
        nodes: List of nodes in cluster
        quorum_size: Minimum nodes for quorum
        regions: List of regions
        metadata: Additional cluster metadata
    """

    cluster_id: str = Field(..., description="Unique cluster identifier")
    name: str = Field(..., description="Cluster name")
    nodes: list[Node] = Field(default_factory=list, description="Cluster nodes")
    quorum_size: int = Field(..., ge=1, description="Minimum nodes for quorum")
    regions: list[str] = Field(default_factory=list, description="Regions")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("quorum_size")
    @classmethod
    def _validate_quorum(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quorum size must be at least 1")
        return v

    model_config = ConfigDict(frozen=True)


class FailoverPolicy(BaseModel):
    """
    Failover policy configuration.

    Attributes:
        policy_id: Unique policy identifier
        name: Human-readable policy name
        strategy: Failover strategy (automatic, manual, quorum_based)
        max_failover_time_s: Maximum allowed failover time in seconds
        require_quorum: Whether quorum is required for failover
        region_priority: Ordered list of preferred regions
        site_priority: Ordered list of preferred sites
        min_healthy_nodes: Minimum healthy nodes required
        metadata: Additional policy metadata
    """

    policy_id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Policy name")
    strategy: FailoverStrategy = Field(..., description="Failover strategy")
    max_failover_time_s: int = Field(default=60, ge=1, description="Max failover time (seconds)")
    require_quorum: bool = Field(default=True, description="Require quorum for failover")
    region_priority: list[str] = Field(default_factory=list, description="Region priority order")
    site_priority: list[str] = Field(default_factory=list, description="Site priority order")
    min_healthy_nodes: int = Field(default=1, ge=1, description="Minimum healthy nodes")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("max_failover_time_s", "min_healthy_nodes")
    @classmethod
    def _validate_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Value must be at least 1")
        return v

    model_config = ConfigDict(frozen=True)


class Heartbeat(BaseModel):
    """
    Node heartbeat record.

    Attributes:
        node_id: Node identifier
        timestamp: Heartbeat timestamp (ISO 8601)
        status: Node status at heartbeat time
        latency_ms: Heartbeat latency in milliseconds
        metadata: Additional heartbeat metadata
    """

    node_id: str = Field(..., description="Node identifier")
    timestamp: str = Field(..., description="Heartbeat timestamp (ISO 8601)")
    status: NodeStatus = Field(..., description="Node status")
    latency_ms: float = Field(..., description="Heartbeat latency (ms)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("latency_ms")
    @classmethod
    def _validate_latency(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Latency cannot be NaN or Inf")
        if v < 0.0:
            raise ValueError("Latency cannot be negative")
        return v

    model_config = ConfigDict(frozen=True)


class QuorumStatus(BaseModel):
    """
    Cluster quorum status.

    Attributes:
        cluster_id: Cluster identifier
        timestamp: Status timestamp (ISO 8601)
        total_nodes: Total nodes in cluster
        healthy_nodes: Number of healthy nodes
        quorum_size: Required quorum size
        has_quorum: Whether quorum is achieved
        healthy_node_ids: List of healthy node IDs
    """

    cluster_id: str = Field(..., description="Cluster identifier")
    timestamp: str = Field(..., description="Status timestamp (ISO 8601)")
    total_nodes: int = Field(..., ge=0, description="Total nodes")
    healthy_nodes: int = Field(..., ge=0, description="Healthy nodes")
    quorum_size: int = Field(..., ge=1, description="Required quorum size")
    has_quorum: bool = Field(..., description="Quorum achieved")
    healthy_node_ids: list[str] = Field(default_factory=list, description="Healthy node IDs")

    @field_validator("total_nodes", "healthy_nodes")
    @classmethod
    def _validate_counts(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Node counts cannot be negative")
        return v

    model_config = ConfigDict(frozen=True)


class FailoverAction(BaseModel):
    """
    Single failover action.

    Attributes:
        action_id: Unique action identifier
        action_type: Type of action (dns_flip, promote, demote, etc.)
        target_node_id: Target node for action
        params: Action-specific parameters
        sequence: Execution sequence number
        estimated_duration_ms: Estimated duration in milliseconds
    """

    action_id: str = Field(..., description="Unique action identifier")
    action_type: ActionType = Field(..., description="Action type")
    target_node_id: str = Field(..., description="Target node ID")
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    sequence: int = Field(..., ge=0, description="Execution sequence")
    estimated_duration_ms: int = Field(..., ge=0, description="Estimated duration (ms)")

    @field_validator("sequence", "estimated_duration_ms")
    @classmethod
    def _validate_nonnegative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Value cannot be negative")
        return v

    model_config = ConfigDict(frozen=True)


class ContinuityPlan(BaseModel):
    """
    Complete continuity plan.

    Attributes:
        plan_id: Unique plan identifier
        cluster_id: Target cluster identifier
        policy_id: Applied policy identifier
        created_at: Plan creation timestamp (ISO 8601)
        actions: Ordered list of failover actions
        estimated_total_ms: Total estimated execution time (ms)
        primary_node_id: Current primary node ID
        failover_target_id: Target node for failover
        metadata: Additional plan metadata
    """

    plan_id: str = Field(..., description="Unique plan identifier")
    cluster_id: str = Field(..., description="Cluster identifier")
    policy_id: str = Field(..., description="Policy identifier")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    actions: list[FailoverAction] = Field(default_factory=list, description="Failover actions")
    estimated_total_ms: int = Field(..., ge=0, description="Total estimated time (ms)")
    primary_node_id: str = Field(..., description="Current primary node ID")
    failover_target_id: str = Field(..., description="Failover target node ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("estimated_total_ms")
    @classmethod
    def _validate_duration(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Duration cannot be negative")
        return v

    model_config = ConfigDict(frozen=True)


class FailoverResult(BaseModel):
    """
    Failover execution result.

    Attributes:
        execution_id: Unique execution identifier
        plan_id: Executed plan identifier
        started_at: Execution start timestamp (ISO 8601)
        completed_at: Execution completion timestamp (ISO 8601)
        success: Whether failover succeeded
        actions_executed: Number of actions executed
        actions_failed: Number of actions failed
        total_duration_ms: Total execution time (ms)
        errors: List of error messages
        metadata: Additional result metadata
    """

    execution_id: str = Field(..., description="Unique execution identifier")
    plan_id: str = Field(..., description="Plan identifier")
    started_at: str = Field(..., description="Start timestamp (ISO 8601)")
    completed_at: str = Field(..., description="Completion timestamp (ISO 8601)")
    success: bool = Field(..., description="Execution success")
    actions_executed: int = Field(..., ge=0, description="Actions executed")
    actions_failed: int = Field(..., ge=0, description="Actions failed")
    total_duration_ms: int = Field(..., ge=0, description="Total duration (ms)")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("actions_executed", "actions_failed", "total_duration_ms")
    @classmethod
    def _validate_nonnegative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Value cannot be negative")
        return v

    model_config = ConfigDict(frozen=True)


class VerificationReport(BaseModel):
    """
    Post-failover verification report.

    Attributes:
        report_id: Unique report identifier
        execution_id: Associated execution identifier
        verified_at: Verification timestamp (ISO 8601)
        consistency_ok: Data consistency check passed
        policy_ok: Policy adherence check passed
        quorum_ok: Quorum check passed
        freshness_ok: Data freshness check passed
        errors: List of verification errors
        warnings: List of verification warnings
    """

    report_id: str = Field(..., description="Unique report identifier")
    execution_id: str = Field(..., description="Execution identifier")
    verified_at: str = Field(..., description="Verification timestamp (ISO 8601)")
    consistency_ok: bool = Field(..., description="Consistency check passed")
    policy_ok: bool = Field(..., description="Policy adherence passed")
    quorum_ok: bool = Field(..., description="Quorum check passed")
    freshness_ok: bool = Field(..., description="Freshness check passed")
    errors: list[str] = Field(default_factory=list, description="Verification errors")
    warnings: list[str] = Field(default_factory=list, description="Verification warnings")

    @property
    def passed(self) -> bool:
        """Check if all verifications passed."""
        return (
            self.consistency_ok
            and self.policy_ok
            and self.quorum_ok
            and self.freshness_ok
            and not self.errors
        )

    model_config = ConfigDict(frozen=True)


__all__ = [
    "NodeStatus",
    "NodeRole",
    "FailoverStrategy",
    "ActionType",
    "Node",
    "Cluster",
    "FailoverPolicy",
    "Heartbeat",
    "QuorumStatus",
    "FailoverAction",
    "ContinuityPlan",
    "FailoverResult",
    "VerificationReport",
]
