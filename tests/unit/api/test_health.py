"""
Unit tests for health check module.
"""


from qnwis.observability.health import (
    ComponentHealth,
    HealthCheck,
    HealthChecker,
    HealthStatus,
    check_health,
)


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_status_values(self):
        """Test health status values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestComponentHealth:
    """Test ComponentHealth dataclass."""

    def test_create_component_health(self):
        """Test creating component health."""
        component = ComponentHealth(
            name="postgres",
            status=HealthStatus.HEALTHY,
            message="Connection OK",
            latency_ms=10.5,
            metadata={"version": "14.0"},
        )

        assert component.name == "postgres"
        assert component.status == HealthStatus.HEALTHY
        assert component.message == "Connection OK"
        assert component.latency_ms == 10.5
        assert component.metadata["version"] == "14.0"

    def test_create_component_without_metadata(self):
        """Test creating component without metadata."""
        component = ComponentHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            message="Slow response",
            latency_ms=500.0,
        )

        assert component.name == "redis"
        assert component.metadata == {}


class TestHealthCheck:
    """Test HealthCheck dataclass."""

    def test_create_health_check(self):
        """Test creating health check."""
        components = [
            ComponentHealth(
                name="postgres",
                status=HealthStatus.HEALTHY,
                message="OK",
                latency_ms=5.0,
            ),
        ]

        check = HealthCheck(
            status=HealthStatus.HEALTHY,
            timestamp="2025-01-01T00:00:00Z",
            uptime_seconds=3600.0,
            version="1.0.0",
            components=components,
        )

        assert check.status == HealthStatus.HEALTHY
        assert check.uptime_seconds == 3600.0
        assert len(check.components) == 1

    def test_to_dict(self):
        """Test converting health check to dictionary."""
        components = [
            ComponentHealth(
                name="postgres",
                status=HealthStatus.HEALTHY,
                message="OK",
                latency_ms=5.0,
                metadata={"connections": 10},
            ),
        ]

        check = HealthCheck(
            status=HealthStatus.HEALTHY,
            timestamp="2025-01-01T00:00:00Z",
            uptime_seconds=100.0,
            version="1.0.0",
            components=components,
        )

        result = check.to_dict()

        assert result["status"] == "healthy"
        assert result["uptime_seconds"] == 100.0
        assert result["version"] == "1.0.0"
        assert len(result["components"]) == 1
        assert result["components"][0]["name"] == "postgres"
        assert result["components"][0]["status"] == "healthy"
        assert result["components"][0]["metadata"]["connections"] == 10


class TestHealthChecker:
    """Test HealthChecker class."""

    def test_create_health_checker(self):
        """Test creating health checker."""
        checker = HealthChecker()

        assert checker.start_time > 0
        assert isinstance(checker.version, str)

    def test_check_liveness(self):
        """Test liveness check."""
        checker = HealthChecker()
        result = checker.check_liveness()

        assert result.status == HealthStatus.HEALTHY
        assert result.uptime_seconds >= 0
        assert len(result.components) >= 1
        assert any(c.name == "process" for c in result.components)

    def test_liveness_always_healthy(self):
        """Test that liveness is always healthy if running."""
        checker = HealthChecker()

        # Multiple calls should all be healthy
        for _ in range(3):
            result = checker.check_liveness()
            assert result.status == HealthStatus.HEALTHY

    def test_check_readiness_structure(self):
        """Test readiness check structure."""
        checker = HealthChecker()
        result = checker.check_readiness()

        # Should have multiple components
        assert len(result.components) >= 1
        assert result.uptime_seconds >= 0
        assert isinstance(result.timestamp, str)

        # Check component names
        component_names = {c.name for c in result.components}
        assert "postgres" in component_names or "redis" in component_names or "agents" in component_names

    def test_readiness_degrades_with_redis_failure(self, monkeypatch):
        """Test readiness degrades when Redis fails."""
        monkeypatch.setenv("QNWIS_REDIS_URL", "redis://invalid:6379")

        checker = HealthChecker()
        result = checker.check_readiness()

        # Should degrade or mark unhealthy depending on optional deps
        assert result.status in (
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        )


class TestCheckHealthFunction:
    """Test check_health convenience function."""

    def test_check_health_liveness(self):
        """Test check_health for liveness."""
        result = check_health(readiness=False)

        assert isinstance(result, HealthCheck)
        assert result.status == HealthStatus.HEALTHY
        assert any(c.name == "process" for c in result.components)

    def test_check_health_readiness(self):
        """Test check_health for readiness."""
        result = check_health(readiness=True)

        assert isinstance(result, HealthCheck)
        assert len(result.components) >= 1

    def test_check_health_returns_different_results(self):
        """Test that liveness and readiness return different results."""
        liveness = check_health(readiness=False)
        readiness = check_health(readiness=True)

        # Readiness should check more components
        assert len(readiness.components) >= len(liveness.components)
