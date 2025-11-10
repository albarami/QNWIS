"""
Health check endpoints for Kubernetes liveness and readiness probes.

Provides comprehensive service health validation including:
- Process health (liveness)
- Dependency health (readiness) - database, Redis, etc.
- Degraded state detection
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """
    Health status for a single component.

    Attributes:
        name: Component name (e.g., 'postgres', 'redis', 'agent_pool')
        status: Health status
        message: Human-readable status message
        latency_ms: Check latency in milliseconds
        metadata: Additional component-specific metadata
    """

    name: str
    status: HealthStatus
    message: str
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """
    Aggregate health check result.

    Attributes:
        status: Overall health status
        timestamp: Check timestamp (ISO 8601)
        uptime_seconds: Process uptime
        version: Application version
        components: Per-component health status
    """

    status: HealthStatus
    timestamp: str
    uptime_seconds: float
    version: str
    components: list[ComponentHealth] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "uptime_seconds": self.uptime_seconds,
            "version": self.version,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                    "metadata": c.metadata,
                }
                for c in self.components
            ],
        }


class HealthChecker:
    """
    Health checker with configurable component checks.

    Performs liveness and readiness checks for service and dependencies.
    """

    def __init__(self) -> None:
        """Initialize health checker."""
        self.start_time = time.time()
        self.version = os.getenv("QNWIS_VERSION", "dev")

    def _check_postgres(self) -> ComponentHealth:
        """Check PostgreSQL database connectivity."""
        start = time.time()
        try:
            # Import here to avoid circular dependencies
            from ..data.deterministic.engine import get_engine

            engine = get_engine()
            with engine.connect() as conn:
                result = conn.execute("SELECT 1").scalar()
                if result != 1:
                    raise ValueError("Unexpected query result")

            latency_ms = (time.time() - start) * 1000
            return ComponentHealth(
                name="postgres",
                status=HealthStatus.HEALTHY,
                message="Database connection OK",
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.error(f"PostgreSQL health check failed: {e}")
            return ComponentHealth(
                name="postgres",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                latency_ms=latency_ms,
            )

    def _check_redis(self) -> ComponentHealth:
        """Check Redis connectivity and responsiveness."""
        start = time.time()
        try:
            # Check if Redis is configured
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis not configured (optional)",
                    latency_ms=0,
                    metadata={"configured": False},
                )

            import redis

            client = redis.from_url(redis_url, socket_connect_timeout=2)
            client.ping()

            latency_ms = (time.time() - start) * 1000
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection OK",
                latency_ms=latency_ms,
                metadata={"configured": True},
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.warning(f"Redis health check failed: {e}")
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message=f"Redis unavailable: {str(e)}",
                latency_ms=latency_ms,
                metadata={"configured": True},
            )

    def _check_agents(self) -> ComponentHealth:
        """Check agent infrastructure readiness."""
        start = time.time()
        try:
            # Verify agent modules can be imported
            from ..agents import (
                NationalStrategyAgent,
                PatternMinerAgent,
                PredictorAgent,
                ScenarioAgent,
                TimeMachineAgent,
            )

            # Basic sanity check
            required_agents = [
                TimeMachineAgent,
                PatternMinerAgent,
                PredictorAgent,
                ScenarioAgent,
                NationalStrategyAgent,
            ]
            agent_names = [agent.__name__ for agent in required_agents]

            latency_ms = (time.time() - start) * 1000
            return ComponentHealth(
                name="agents",
                status=HealthStatus.HEALTHY,
                message="All agents available",
                latency_ms=latency_ms,
                metadata={"agents": agent_names},
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.error(f"Agent health check failed: {e}")
            return ComponentHealth(
                name="agents",
                status=HealthStatus.UNHEALTHY,
                message=f"Agent infrastructure error: {str(e)}",
                latency_ms=latency_ms,
            )

    def check_liveness(self) -> HealthCheck:
        """
        Liveness probe - checks if process is alive.

        Returns:
            Health check result (should always be HEALTHY if process is running)
        """
        uptime = time.time() - self.start_time

        return HealthCheck(
            status=HealthStatus.HEALTHY,
            timestamp=datetime.now(UTC).isoformat(),
            uptime_seconds=uptime,
            version=self.version,
            components=[
                ComponentHealth(
                    name="process",
                    status=HealthStatus.HEALTHY,
                    message="Process is alive",
                    latency_ms=0,
                    metadata={"pid": os.getpid()},
                )
            ],
        )

    def check_readiness(self) -> HealthCheck:
        """
        Readiness probe - checks if service can handle requests.

        Verifies:
        - Database connectivity
        - Redis connectivity (degraded if unavailable)
        - Agent infrastructure

        Returns:
            Health check result with component statuses
        """
        uptime = time.time() - self.start_time

        # Check all components
        components = [
            self._check_postgres(),
            self._check_redis(),
            self._check_agents(),
        ]

        # Determine overall status
        unhealthy_count = sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for c in components if c.status == HealthStatus.DEGRADED)

        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return HealthCheck(
            status=overall_status,
            timestamp=datetime.now(UTC).isoformat(),
            uptime_seconds=uptime,
            version=self.version,
            components=components,
        )


# Global health checker instance
_health_checker: HealthChecker | None = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def check_health(readiness: bool = False) -> HealthCheck:
    """
    Perform health check.

    Args:
        readiness: If True, perform readiness check (includes dependencies).
                  If False, perform liveness check (process only).

    Returns:
        Health check result
    """
    checker = get_health_checker()
    if readiness:
        return checker.check_readiness()
    else:
        return checker.check_liveness()
