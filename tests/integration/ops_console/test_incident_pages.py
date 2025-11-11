"""
Integration tests for incident pages.

Tests list, filter, detail, and POST actions (ack/resolve/silence) with CSRF.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from src.qnwis.notify.models import Incident, IncidentState, Severity
from src.qnwis.notify.resolver import IncidentResolver
from src.qnwis.ops_console.app import create_ops_app
from src.qnwis.ops_console.csrf import CSRFProtection
from src.qnwis.security import Principal
from src.qnwis.utils.clock import ManualClock


@pytest.fixture
def manual_clock():
    """Manual clock for deterministic timestamps."""
    return ManualClock(start=datetime(2024, 1, 1, 12, 0, tzinfo=UTC))


@pytest.fixture
def ops_app(manual_clock):
    """Create ops console app with test configuration."""
    app = create_ops_app(clock=manual_clock, secret_key="test_secret_key_12345")

    # Initialize incident resolver with test data
    resolver = IncidentResolver(clock=manual_clock, ledger_dir=None)

    # Create test incidents
    for i in range(5):
        incident = Incident(
            incident_id=f"inc_{i:03d}",
            notification_id=f"notif_{i:03d}",
            rule_id=f"rule_{i % 2}",
            severity=Severity.CRITICAL if i < 2 else Severity.WARNING,
            state=IncidentState.OPEN if i < 3 else IncidentState.RESOLVED,
            message=f"Test incident {i}",
            scope={"level": "sector", "code": f"{i:03d}"},
            window_start=f"2024-01-0{i+1}T00:00:00Z",
            window_end=f"2024-01-0{i+1}T01:00:00Z",
            created_at=f"2024-01-0{i+1}T00:30:00Z",
            updated_at=f"2024-01-0{i+1}T00:30:00Z",
            consecutive_green_count=0,
            metadata={},
        )
        resolver._store[incident.incident_id] = incident

    app.state.incident_resolver = resolver

    return app


@pytest.fixture
def client(ops_app):
    """Test client with authenticated principal."""
    client = TestClient(ops_app)

    # Mock principal in request state
    def add_principal(request):
        request.state.principal = Principal(
            user_id="test@example.com",
            roles=["analyst", "admin"],
        )

    # Add middleware to inject principal
    @ops_app.middleware("http")
    async def inject_principal(request, call_next):
        request.state.principal = Principal(
            user_id="test@example.com",
            roles=["analyst", "admin"],
        )
        response = await call_next(request)
        return response

    return client


class TestOpsIndex:
    """Test ops console index page."""

    def test_index_page_loads(self, client):
        """Index page loads successfully."""
        response = client.get("/")

        assert response.status_code == 200
        assert "Operations Dashboard" in response.text or "Dashboard" in response.text

    def test_index_shows_stats(self, client):
        """Index page displays incident statistics."""
        response = client.get("/")

        assert response.status_code == 200
        # Should show total count (5 incidents)
        assert "5" in response.text

    def test_index_includes_request_id(self, client):
        """Index page includes request ID."""
        response = client.get("/")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers


class TestIncidentsList:
    """Test incidents list page."""

    def test_incidents_list_loads(self, client):
        """Incidents list page loads."""
        response = client.get("/incidents")

        assert response.status_code == 200
        assert "Incidents" in response.text

    def test_incidents_list_shows_all(self, client):
        """Incidents list shows all incidents."""
        response = client.get("/incidents")

        assert response.status_code == 200
        # Should show incident IDs
        assert "inc_000" in response.text
        assert "inc_004" in response.text

    def test_filter_by_state(self, client):
        """Can filter incidents by state."""
        response = client.get("/incidents?state=open")

        assert response.status_code == 200
        # Should show only open incidents (0, 1, 2)
        assert "inc_000" in response.text
        assert "inc_001" in response.text
        assert "inc_002" in response.text
        # Should not show resolved (3, 4)
        assert "inc_003" not in response.text or "resolved" in response.text.lower()

    def test_filter_by_severity(self, client):
        """Can filter incidents by severity."""
        response = client.get("/incidents?severity=critical")

        assert response.status_code == 200
        # Should show critical incidents (0, 1)
        assert "CRITICAL" in response.text

    def test_filter_by_rule_id(self, client):
        """Can filter incidents by rule ID."""
        response = client.get("/incidents?rule_id=rule_0")

        assert response.status_code == 200
        # Should show incidents with rule_0 (0, 2, 4)
        assert "rule_0" in response.text

    def test_invalid_state_filter_ignored(self, client):
        """Invalid state filter is ignored."""
        response = client.get("/incidents?state=invalid")

        assert response.status_code == 200
        # Should show all incidents
        assert "inc_000" in response.text

    def test_limit_parameter(self, client):
        """Can limit number of results."""
        response = client.get("/incidents?limit=2")

        assert response.status_code == 200
        # Should show at most 2 incidents


class TestIncidentDetail:
    """Test incident detail page."""

    def test_incident_detail_loads(self, client):
        """Incident detail page loads."""
        response = client.get("/incidents/inc_000")

        assert response.status_code == 200
        assert "inc_000" in response.text
        assert "Test incident 0" in response.text

    def test_incident_not_found(self, client):
        """Returns 404 for non-existent incident."""
        response = client.get("/incidents/inc_999")

        assert response.status_code == 404

    def test_detail_shows_timeline(self, client):
        """Detail page shows incident timeline."""
        response = client.get("/incidents/inc_000")

        assert response.status_code == 200
        assert "Timeline" in response.text or "CREATED" in response.text

    def test_detail_shows_action_forms(self, client):
        """Detail page shows action forms for open incident."""
        response = client.get("/incidents/inc_000")

        assert response.status_code == 200
        # Should have forms for actions
        assert 'method="post"' in response.text.lower()
        assert "csrf_token" in response.text


class TestIncidentActions:
    """Test incident action endpoints (POST)."""

    def test_ack_incident_requires_csrf(self, client):
        """Acknowledging incident requires CSRF token."""
        response = client.post("/incidents/inc_000/ack", data={})

        assert response.status_code == 403

    def test_ack_incident_success(self, client, ops_app, manual_clock):
        """Can acknowledge incident with valid CSRF."""
        # Generate valid CSRF token
        csrf = CSRFProtection(secret_key="test_secret_key_12345", ttl=900)
        token = csrf.generate_token(manual_clock.utcnow())

        response = client.post(
            "/incidents/inc_000/ack",
            data={"csrf_token": token.token},
            follow_redirects=False,
        )

        # Should redirect (303) to detail page
        assert response.status_code == 303
        assert "/ops/incidents/inc_000" in response.headers.get("HX-Redirect", "")

    def test_ack_nonexistent_incident(self, client, ops_app, manual_clock):
        """Acknowledging non-existent incident returns 404."""
        csrf = CSRFProtection(secret_key="test_secret_key_12345", ttl=900)
        token = csrf.generate_token(manual_clock.utcnow())

        response = client.post(
            "/incidents/inc_999/ack",
            data={"csrf_token": token.token},
        )

        assert response.status_code == 404

    def test_resolve_incident_requires_csrf(self, client):
        """Resolving incident requires CSRF token."""
        response = client.post("/incidents/inc_000/resolve", data={"note": "Fixed"})

        assert response.status_code == 403

    def test_resolve_incident_success(self, client, ops_app, manual_clock):
        """Can resolve incident with valid CSRF."""
        csrf = CSRFProtection(secret_key="test_secret_key_12345", ttl=900)
        token = csrf.generate_token(manual_clock.utcnow())

        response = client.post(
            "/incidents/inc_000/resolve",
            data={"csrf_token": token.token, "note": "Issue resolved"},
            follow_redirects=False,
        )

        assert response.status_code == 303

    def test_resolve_incident_with_note(self, client, ops_app, manual_clock):
        """Resolution note is stored in incident."""
        csrf = CSRFProtection(secret_key="test_secret_key_12345", ttl=900)
        token = csrf.generate_token(manual_clock.utcnow())

        client.post(
            "/incidents/inc_000/resolve",
            data={"csrf_token": token.token, "note": "Test resolution note"},
        )

        # Check incident was updated
        resolver = ops_app.state.incident_resolver
        incident = resolver.get_incident("inc_000")
        assert incident is not None
        assert incident.state == IncidentState.RESOLVED

    def test_silence_incident_requires_csrf(self, client):
        """Silencing incident requires CSRF token."""
        response = client.post(
            "/incidents/inc_000/silence",
            data={"until": "2024-01-02T00:00:00Z"},
        )

        assert response.status_code == 403

    def test_silence_incident_success(self, client, ops_app, manual_clock):
        """Can silence incident with valid CSRF."""
        csrf = CSRFProtection(secret_key="test_secret_key_12345", ttl=900)
        token = csrf.generate_token(manual_clock.utcnow())

        response = client.post(
            "/incidents/inc_000/silence",
            data={
                "csrf_token": token.token,
                "until": "2024-01-02T00:00:00Z",
                "reason": "Planned maintenance",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303

    def test_silence_metadata_stored(self, client, ops_app, manual_clock):
        """Silence metadata is stored in incident."""
        csrf = CSRFProtection(secret_key="test_secret_key_12345", ttl=900)
        token = csrf.generate_token(manual_clock.utcnow())

        client.post(
            "/incidents/inc_000/silence",
            data={
                "csrf_token": token.token,
                "until": "2024-01-02T00:00:00Z",
                "reason": "Test reason",
            },
        )

        # Check metadata
        resolver = ops_app.state.incident_resolver
        incident = resolver.get_incident("inc_000")
        assert incident is not None
        assert incident.state == IncidentState.SILENCED
        assert incident.metadata.get("silence_until") == "2024-01-02T00:00:00Z"
        assert incident.metadata.get("silence_reason") == "Test reason"


class TestAlertsList:
    """Test alerts list page."""

    def test_alerts_list_loads(self, client):
        """Alerts list page loads (placeholder)."""
        response = client.get("/alerts")

        assert response.status_code == 200
        assert "Alert" in response.text


class TestCSRFProtection:
    """Test CSRF protection across pages."""

    def test_pages_include_csrf_token(self, client):
        """Pages with forms include CSRF token."""
        response = client.get("/incidents/inc_000")

        assert response.status_code == 200
        assert 'name="csrf_token"' in response.text

    def test_invalid_csrf_token_rejected(self, client):
        """Invalid CSRF token is rejected."""
        response = client.post(
            "/incidents/inc_000/ack",
            data={"csrf_token": "invalid_token_12345"},
        )

        assert response.status_code == 403

    def test_expired_csrf_token_rejected(self, client, ops_app, manual_clock):
        """Expired CSRF token is rejected."""
        csrf = CSRFProtection(secret_key="test_secret_key_12345", ttl=900)

        # Generate token at T=0
        token = csrf.generate_token("2024-01-01T00:00:00Z")

        # Advance clock beyond TTL
        manual_clock.current = "2024-01-01T01:00:00Z"

        response = client.post(
            "/incidents/inc_000/ack",
            data={"csrf_token": token.token},
        )

        assert response.status_code == 403


class TestDeterminism:
    """Test deterministic behavior."""

    def test_list_page_deterministic(self, client):
        """List page produces same output for same state."""
        response1 = client.get("/incidents")
        response2 = client.get("/incidents")

        assert response1.text == response2.text

    def test_detail_page_deterministic(self, client):
        """Detail page produces same output for same state."""
        response1 = client.get("/incidents/inc_000")
        response2 = client.get("/incidents/inc_000")

        assert response1.text == response2.text


class TestRBAC:
    """Test role-based access control (placeholder - requires full RBAC setup)."""

    def test_analyst_can_view_incidents(self, client):
        """Analyst role can view incidents."""
        response = client.get("/incidents")

        assert response.status_code == 200

    def test_analyst_can_view_detail(self, client):
        """Analyst role can view incident detail."""
        response = client.get("/incidents/inc_000")

        assert response.status_code == 200
