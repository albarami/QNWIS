"""Unit tests for incident resolver."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.qnwis.notify.models import Incident, IncidentState, Severity
from src.qnwis.notify.resolver import IncidentResolver
from src.qnwis.utils.clock import Clock


@pytest.fixture
def fixed_clock() -> Clock:
    """Create a fixed clock for deterministic tests."""
    fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    return Clock(now=lambda: fixed_time, perf_counter=lambda: 1000.0)


@pytest.fixture
def temp_ledger(tmp_path: Path) -> Path:
    """Create temporary ledger directory."""
    ledger_dir = tmp_path / "incidents"
    ledger_dir.mkdir()
    return ledger_dir


class TestIncidentResolver:
    """Test IncidentResolver."""

    def test_acknowledge_open_incident(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test acknowledging an open incident."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Create incident
        incident = Incident(
            incident_id="inc_001",
            notification_id="notif_001",
            rule_id="rule_001",
            severity=Severity.WARNING,
            state=IncidentState.OPEN,
            message="Test incident",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-15T11:00:00+00:00",
            updated_at="2024-01-15T11:00:00+00:00",
        )
        resolver._incidents[incident.incident_id] = incident

        # Acknowledge
        updated = resolver.acknowledge("inc_001")

        assert updated is not None
        assert updated.state == IncidentState.ACK
        assert updated.ack_at is not None
        assert updated.updated_at == "2024-01-15T12:00:00+00:00"

    def test_acknowledge_non_open_incident(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test acknowledging a non-open incident has no effect."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Create resolved incident
        incident = Incident(
            incident_id="inc_002",
            notification_id="notif_002",
            rule_id="rule_002",
            severity=Severity.INFO,
            state=IncidentState.RESOLVED,
            message="Test",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-15T11:00:00+00:00",
            updated_at="2024-01-15T11:00:00+00:00",
            resolved_at="2024-01-15T11:30:00+00:00",
        )
        resolver._incidents[incident.incident_id] = incident

        # Try to acknowledge
        updated = resolver.acknowledge("inc_002")

        assert updated is not None
        assert updated.state == IncidentState.RESOLVED  # Unchanged

    def test_acknowledge_nonexistent(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test acknowledging non-existent incident."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)
        result = resolver.acknowledge("nonexistent")
        assert result is None

    def test_silence_incident(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test silencing an incident."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Create open incident
        incident = Incident(
            incident_id="inc_003",
            notification_id="notif_003",
            rule_id="rule_003",
            severity=Severity.ERROR,
            state=IncidentState.OPEN,
            message="Test",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-15T11:00:00+00:00",
            updated_at="2024-01-15T11:00:00+00:00",
        )
        resolver._incidents[incident.incident_id] = incident

        # Silence
        updated = resolver.silence("inc_003")

        assert updated is not None
        assert updated.state == IncidentState.SILENCED
        assert updated.updated_at == "2024-01-15T12:00:00+00:00"

    def test_silence_resolved_incident_fails(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test silencing a resolved incident fails."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Create resolved incident
        incident = Incident(
            incident_id="inc_004",
            notification_id="notif_004",
            rule_id="rule_004",
            severity=Severity.WARNING,
            state=IncidentState.RESOLVED,
            message="Test",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-15T11:00:00+00:00",
            updated_at="2024-01-15T11:30:00+00:00",
            resolved_at="2024-01-15T11:30:00+00:00",
        )
        resolver._incidents[incident.incident_id] = incident

        # Try to silence
        updated = resolver.silence("inc_004")

        assert updated is not None
        assert updated.state == IncidentState.RESOLVED  # Unchanged

    def test_resolve_incident(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test resolving an incident."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Create acknowledged incident
        incident = Incident(
            incident_id="inc_005",
            notification_id="notif_005",
            rule_id="rule_005",
            severity=Severity.CRITICAL,
            state=IncidentState.ACK,
            message="Test",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-15T11:00:00+00:00",
            updated_at="2024-01-15T11:15:00+00:00",
            ack_at="2024-01-15T11:15:00+00:00",
        )
        resolver._incidents[incident.incident_id] = incident

        # Resolve
        updated = resolver.resolve("inc_005")

        assert updated is not None
        assert updated.state == IncidentState.RESOLVED
        assert updated.resolved_at == "2024-01-15T12:00:00+00:00"
        assert updated.updated_at == "2024-01-15T12:00:00+00:00"

    def test_resolve_already_resolved(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test resolving an already resolved incident."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Create resolved incident
        incident = Incident(
            incident_id="inc_006",
            notification_id="notif_006",
            rule_id="rule_006",
            severity=Severity.INFO,
            state=IncidentState.RESOLVED,
            message="Test",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-15T11:00:00+00:00",
            updated_at="2024-01-15T11:30:00+00:00",
            resolved_at="2024-01-15T11:30:00+00:00",
        )
        resolver._incidents[incident.incident_id] = incident

        # Resolve again
        updated = resolver.resolve("inc_006")

        assert updated is not None
        assert updated.state == IncidentState.RESOLVED
        assert updated.resolved_at == "2024-01-15T11:30:00+00:00"  # Original time

    def test_record_green_evaluation(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test recording green evaluation."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger, auto_resolve_threshold=3)

        # Create open incident
        incident = Incident(
            incident_id="inc_007",
            notification_id="notif_007",
            rule_id="rule_green",
            severity=Severity.WARNING,
            state=IncidentState.OPEN,
            message="Test",
            scope={},
            window_start="2024-01-01T00:00:00Z",
            window_end="2024-01-01T23:59:59Z",
            created_at="2024-01-15T11:00:00+00:00",
            updated_at="2024-01-15T11:00:00+00:00",
            consecutive_green_count=0,
        )
        resolver._incidents[incident.incident_id] = incident

        # First green - increments count
        resolved = resolver.record_green_evaluation("rule_green")
        assert len(resolved) == 0
        assert resolver._incidents["inc_007"].consecutive_green_count == 1

        # Second green - increments count
        resolved = resolver.record_green_evaluation("rule_green")
        assert len(resolved) == 0
        assert resolver._incidents["inc_007"].consecutive_green_count == 2

        # Third green - triggers auto-resolve
        resolved = resolver.record_green_evaluation("rule_green")
        assert len(resolved) == 1
        assert resolved[0].state == IncidentState.RESOLVED
        assert resolved[0].consecutive_green_count == 3
        assert resolved[0].metadata.get("auto_resolved") is True

    def test_list_incidents_no_filter(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test listing incidents without filters."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Add incidents
        for i in range(5):
            incident = Incident(
                incident_id=f"inc_{i:03d}",
                notification_id=f"notif_{i:03d}",
                rule_id=f"rule_{i}",
                severity=Severity.INFO,
                state=IncidentState.OPEN,
                message=f"Test {i}",
                scope={},
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-01T23:59:59Z",
                created_at=f"2024-01-15T{11+i:02d}:00:00+00:00",
                updated_at=f"2024-01-15T{11+i:02d}:00:00+00:00",
            )
            resolver._incidents[incident.incident_id] = incident

        incidents = resolver.list_incidents()
        assert len(incidents) == 5

    def test_list_incidents_by_state(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test listing incidents filtered by state."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Add incidents with different states
        for i, state in enumerate([IncidentState.OPEN, IncidentState.ACK, IncidentState.RESOLVED]):
            incident = Incident(
                incident_id=f"inc_{i:03d}",
                notification_id=f"notif_{i:03d}",
                rule_id=f"rule_{i}",
                severity=Severity.INFO,
                state=state,
                message=f"Test {i}",
                scope={},
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-01T23:59:59Z",
                created_at="2024-01-15T11:00:00+00:00",
                updated_at="2024-01-15T11:00:00+00:00",
            )
            resolver._incidents[incident.incident_id] = incident

        # Filter by OPEN
        open_incidents = resolver.list_incidents(state=IncidentState.OPEN)
        assert len(open_incidents) == 1
        assert open_incidents[0].state == IncidentState.OPEN

        # Filter by RESOLVED
        resolved_incidents = resolver.list_incidents(state=IncidentState.RESOLVED)
        assert len(resolved_incidents) == 1
        assert resolved_incidents[0].state == IncidentState.RESOLVED

    def test_list_incidents_by_rule(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test listing incidents filtered by rule ID."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Add incidents with different rules
        for i in range(3):
            incident = Incident(
                incident_id=f"inc_{i:03d}",
                notification_id=f"notif_{i:03d}",
                rule_id="rule_target" if i < 2 else "rule_other",
                severity=Severity.INFO,
                state=IncidentState.OPEN,
                message=f"Test {i}",
                scope={},
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-01T23:59:59Z",
                created_at="2024-01-15T11:00:00+00:00",
                updated_at="2024-01-15T11:00:00+00:00",
            )
            resolver._incidents[incident.incident_id] = incident

        # Filter by rule
        incidents = resolver.list_incidents(rule_id="rule_target")
        assert len(incidents) == 2
        assert all(i.rule_id == "rule_target" for i in incidents)

    def test_get_stats(self, fixed_clock: Clock, temp_ledger: Path) -> None:
        """Test getting incident statistics."""
        resolver = IncidentResolver(clock=fixed_clock, ledger_dir=temp_ledger)

        # Add diverse incidents
        incidents_data = [
            ("inc_001", "rule_a", Severity.WARNING, IncidentState.OPEN),
            ("inc_002", "rule_a", Severity.ERROR, IncidentState.ACK),
            ("inc_003", "rule_b", Severity.CRITICAL, IncidentState.RESOLVED),
            ("inc_004", "rule_c", Severity.INFO, IncidentState.OPEN),
        ]

        for inc_id, rule_id, severity, state in incidents_data:
            incident = Incident(
                incident_id=inc_id,
                notification_id=inc_id.replace("inc", "notif"),
                rule_id=rule_id,
                severity=severity,
                state=state,
                message="Test",
                scope={},
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-01T23:59:59Z",
                created_at="2024-01-15T11:00:00+00:00",
                updated_at="2024-01-15T11:00:00+00:00",
            )
            resolver._incidents[incident.incident_id] = incident

        stats = resolver.get_stats()

        assert stats["total"] == 4
        assert stats["by_state"]["open"] == 2
        assert stats["by_state"]["ack"] == 1
        assert stats["by_state"]["resolved"] == 1
        assert stats["by_severity"]["warning"] == 1
        assert stats["by_severity"]["error"] == 1
        assert stats["by_severity"]["critical"] == 1
        assert stats["by_severity"]["info"] == 1
        assert stats["by_rule"]["rule_a"] == 2
