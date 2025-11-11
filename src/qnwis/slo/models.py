"""
Pydantic models for SLO core primitives.

Defines SLI kinds, SLO targets, and error budget snapshots.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SLIKind(str, Enum):
    """Supported SLI kinds for SLO evaluations."""

    LATENCY_MS_P95 = "latency_ms_p95"
    AVAILABILITY_PCT = "availability_pct"
    ERROR_RATE_PCT = "error_rate_pct"


class SLOTarget(BaseModel):
    """Service Level Objective target configuration."""

    objective: float = Field(..., description="Target objective value (percent or milliseconds)")
    window_days: int = Field(..., ge=1, description="Rolling evaluation window in days")
    sli: SLIKind = Field(..., description="SLI kind this SLO targets")

    @field_validator("objective")
    @classmethod
    def _reject_nan_inf(cls, v: float) -> float:
        import math

        if math.isnan(v) or math.isinf(v):
            raise ValueError("SLO objective cannot be NaN or Inf")
        return float(v)


class ErrorBudgetSnapshot(BaseModel):
    """Current error budget status for an SLO window."""

    remaining_pct: float = Field(..., ge=0.0, le=100.0, description="Remaining error budget percent (0-100)")
    minutes_left: float = Field(..., ge=0.0, description="Minutes of error budget remaining in current window")
    burn_fast: float = Field(..., ge=0.0, description="Fast-window burn rate (e.g., 5m)")
    burn_slow: float = Field(..., ge=0.0, description="Slow-window burn rate (e.g., 1h)")


__all__ = ["SLIKind", "SLOTarget", "ErrorBudgetSnapshot"]
