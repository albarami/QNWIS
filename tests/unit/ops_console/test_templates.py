"""
Unit tests for ops console templates.

Tests deterministic rendering, accessibility hints, and template structure.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, TemplateNotFound

from src.qnwis.ops_console.app import SafeTemplateLoader, create_ops_app
from src.qnwis.ops_console.csrf import CSRFToken
from src.qnwis.utils.clock import ManualClock

# Template directory
TEMPLATES_DIR = Path(__file__).parents[3] / "src" / "qnwis" / "ops_console" / "templates"


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment for testing."""
    if not TEMPLATES_DIR.exists():
        pytest.skip(f"Templates directory not found: {TEMPLATES_DIR}")

    env = Environment(loader=SafeTemplateLoader([str(TEMPLATES_DIR)]))

    # Add custom filters and globals
    env.globals["csrf_field"] = lambda token: f'<input type="hidden" name="csrf_token" value="{token.token}">'

    return env


class TestLayoutTemplate:
    """Test base layout template."""

    def test_layout_exists(self, jinja_env):
        """Layout template exists."""
        try:
            template = jinja_env.get_template("layout.html")
            assert template is not None
        except TemplateNotFound:
            pytest.fail("layout.html not found")

    def test_layout_renders(self, jinja_env):
        """Layout template renders without errors."""
        template = jinja_env.get_template("layout.html")

        context = {
            "request_id": "test_req_123",
            "principal": type("Principal", (), {
                "user_id": "test@example.com",
                "roles": ["analyst"],
            })(),
            "render_start": "2024-01-01T12:00:00Z",
        }

        output = template.render(**context)

        assert "QNWIS Ops Console" in output
        assert "test_req_123" in output
        assert "test@example.com" in output

    def test_layout_has_semantic_html(self, jinja_env):
        """Layout uses semantic HTML elements."""
        template = jinja_env.get_template("layout.html")

        context = {
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
        }

        output = template.render(**context)

        assert "<nav" in output
        assert "<main" in output
        assert "<footer" in output
        assert 'role="navigation"' in output
        assert 'role="main"' in output
        assert 'role="contentinfo"' in output

    def test_layout_has_aria_labels(self, jinja_env):
        """Layout includes ARIA labels."""
        template = jinja_env.get_template("layout.html")

        context = {
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
        }

        output = template.render(**context)

        assert 'aria-label=' in output


class TestOpsIndexTemplate:
    """Test ops index (dashboard) template."""

    def test_ops_index_exists(self, jinja_env):
        """Ops index template exists."""
        try:
            template = jinja_env.get_template("ops_index.html")
            assert template is not None
        except TemplateNotFound:
            pytest.fail("ops_index.html not found")

    def test_ops_index_renders(self, jinja_env):
        """Ops index template renders."""
        template = jinja_env.get_template("ops_index.html")

        context = {
            "request": type("Request", (), {})(),
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
            "stats": {
                "total": 10,
                "by_state": {"open": 3, "ack": 2, "resolved": 5},
                "by_severity": {"critical": 1, "warning": 4, "info": 5},
            },
            "csrf_token": CSRFToken(token="test_token", timestamp="2024-01-01T12:00:00Z", ttl=900),
        }

        output = template.render(**context)

        assert "Operations Dashboard" in output or "Dashboard" in output
        assert "10" in output  # Total incidents

    def test_ops_index_has_sse_attributes(self, jinja_env):
        """Ops index includes SSE (HTMX) attributes."""
        template = jinja_env.get_template("ops_index.html")

        context = {
            "request": type("Request", (), {})(),
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
            "stats": {"total": 0, "by_state": {}, "by_severity": {}},
            "csrf_token": CSRFToken(token="test", timestamp="2024-01-01T12:00:00Z", ttl=900),
        }

        output = template.render(**context)

        # Check for SSE/HTMX attributes
        assert "hx-ext=" in output or "sse-connect=" in output


class TestIncidentsListTemplate:
    """Test incidents list template."""

    def test_incidents_list_exists(self, jinja_env):
        """Incidents list template exists."""
        try:
            template = jinja_env.get_template("incidents_list.html")
            assert template is not None
        except TemplateNotFound:
            pytest.fail("incidents_list.html not found")

    def test_incidents_list_renders_empty(self, jinja_env):
        """Incidents list renders with no incidents."""
        template = jinja_env.get_template("incidents_list.html")

        context = {
            "request": type("Request", (), {})(),
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
            "incidents": [],
            "filters": {"state": None, "severity": None, "rule_id": None},
            "csrf_token": CSRFToken(token="test", timestamp="2024-01-01T12:00:00Z", ttl=900),
        }

        output = template.render(**context)

        assert "Incidents" in output
        assert "No incidents" in output.lower() or "no results" in output.lower()

    def test_incidents_list_has_filters(self, jinja_env):
        """Incidents list includes filter form."""
        template = jinja_env.get_template("incidents_list.html")

        context = {
            "request": type("Request", (), {})(),
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
            "incidents": [],
            "filters": {"state": None, "severity": None, "rule_id": None},
            "csrf_token": CSRFToken(token="test", timestamp="2024-01-01T12:00:00Z", ttl=900),
        }

        output = template.render(**context)

        assert "<form" in output
        assert 'name="state"' in output
        assert 'name="severity"' in output

    def test_incidents_list_has_table_headers(self, jinja_env):
        """Incidents list table has proper headers."""
        template = jinja_env.get_template("incidents_list.html")

        # Mock incident
        incident = type("Incident", (), {
            "incident_id": "inc_123",
            "rule_id": "rule_1",
            "severity": type("Severity", (), {"value": "critical"})(),
            "state": type("State", (), {"value": "open"})(),
            "message": "Test incident",
            "window_start": "2024-01-01T00:00:00Z",
            "window_end": "2024-01-01T01:00:00Z",
        })()

        context = {
            "request": type("Request", (), {})(),
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
            "incidents": [incident],
            "filters": {},
            "csrf_token": CSRFToken(token="test", timestamp="2024-01-01T12:00:00Z", ttl=900),
        }

        output = template.render(**context)

        assert "<thead>" in output
        assert "<tbody>" in output
        assert "inc_123" in output


class TestIncidentDetailTemplate:
    """Test incident detail template."""

    def test_incident_detail_exists(self, jinja_env):
        """Incident detail template exists."""
        try:
            template = jinja_env.get_template("incident_detail.html")
            assert template is not None
        except TemplateNotFound:
            pytest.fail("incident_detail.html not found")

    def test_incident_detail_renders(self, jinja_env):
        """Incident detail template renders."""
        template = jinja_env.get_template("incident_detail.html")

        incident = type("Incident", (), {
            "incident_id": "inc_123",
            "rule_id": "rule_1",
            "severity": type("Severity", (), {"value": "critical"})(),
            "state": type("State", (), {"value": "open"})(),
            "message": "Critical issue detected",
            "window_start": "2024-01-01T00:00:00Z",
            "window_end": "2024-01-01T01:00:00Z",
            "created_at": "2024-01-01T00:30:00Z",
            "updated_at": "2024-01-01T00:30:00Z",
            "metadata": {},
        })()

        context = {
            "request": type("Request", (), {})(),
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
            "incident": incident,
            "timeline": [{"event": "CREATED", "timestamp": "2024-01-01T00:30:00Z", "actor": "system"}],
            "audit_pack_path": None,
            "csrf_token": CSRFToken(token="test", timestamp="2024-01-01T12:00:00Z", ttl=900),
        }

        output = template.render(**context)

        assert "inc_123" in output
        assert "Critical issue detected" in output

    def test_incident_detail_has_action_forms(self, jinja_env):
        """Incident detail includes action forms."""
        template = jinja_env.get_template("incident_detail.html")

        incident = type("Incident", (), {
            "incident_id": "inc_123",
            "rule_id": "rule_1",
            "severity": type("Severity", (), {"value": "warning"})(),
            "state": type("State", (), {"value": "open"})(),
            "message": "Test",
            "window_start": "2024-01-01T00:00:00Z",
            "window_end": "2024-01-01T01:00:00Z",
            "created_at": "2024-01-01T00:30:00Z",
            "updated_at": "2024-01-01T00:30:00Z",
            "metadata": {},
        })()

        context = {
            "request": type("Request", (), {})(),
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
            "incident": incident,
            "timeline": [],
            "audit_pack_path": None,
            "csrf_token": CSRFToken(token="test", timestamp="2024-01-01T12:00:00Z", ttl=900),
        }

        output = template.render(**context)

        # Should have forms for actions
        assert "<form" in output
        assert 'method="post"' in output


class TestAccessibility:
    """Test accessibility features across templates."""

    @pytest.mark.parametrize(
        "template_name",
        ["layout.html", "ops_index.html", "incidents_list.html", "incident_detail.html"],
    )
    def test_template_has_labels_for_inputs(self, jinja_env, template_name):
        """All input fields have associated labels."""
        try:
            template = jinja_env.get_template(template_name)
        except TemplateNotFound:
            pytest.skip(f"{template_name} not found")

        # Minimal context
        context = {
            "request": type("Request", (), {})(),
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
            "stats": {"total": 0, "by_state": {}, "by_severity": {}},
            "incidents": [],
            "filters": {},
            "incident": type("I", (), {
                "incident_id": "i1",
                "rule_id": "r1",
                "severity": type("S", (), {"value": "info"})(),
                "state": type("St", (), {"value": "open"})(),
                "message": "msg",
                "window_start": "2024-01-01T00:00:00Z",
                "window_end": "2024-01-01T01:00:00Z",
                "created_at": "2024-01-01T00:30:00Z",
                "updated_at": "2024-01-01T00:30:00Z",
                "metadata": {},
            })(),
            "timeline": [],
            "audit_pack_path": None,
            "alerts": [],
            "csrf_token": CSRFToken(token="test", timestamp="2024-01-01T12:00:00Z", ttl=900),
        }

        output = template.render(**context)

        # Check that inputs have labels or aria-label
        # This is a heuristic check
        if "<input" in output or "<select" in output or "<textarea" in output:
            assert ("<label" in output or "aria-label" in output), \
                f"{template_name} has inputs without labels"


class TestDeterminism:
    """Test deterministic rendering."""

    def test_layout_renders_deterministically(self, jinja_env):
        """Layout produces same output for same input."""
        template = jinja_env.get_template("layout.html")

        context = {
            "request_id": "test_123",
            "principal": type("P", (), {"user_id": "user@test.com", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
        }

        output1 = template.render(**context)
        output2 = template.render(**context)

        assert output1 == output2


class TestTemplateLoaderSecurity:
    """Validate SafeTemplateLoader protections."""

    def test_loader_blocks_remote_urls(self):
        loader = SafeTemplateLoader([str(TEMPLATES_DIR)])
        env = Environment(loader=loader)
        with pytest.raises(TemplateNotFound):
            loader.get_source(env, "https://example.com/evil.html")

    def test_loader_blocks_path_traversal(self):
        loader = SafeTemplateLoader([str(TEMPLATES_DIR)])
        env = Environment(loader=loader)
        with pytest.raises(TemplateNotFound):
            loader.get_source(env, "../secrets.html")

    def test_app_uses_safe_loader(self):
        app = create_ops_app(clock=ManualClock())
        templates = app.state.ops_templates
        assert isinstance(templates.env.loader, SafeTemplateLoader)

    def test_ops_index_renders_deterministically(self, jinja_env):
        """Ops index produces same output for same input."""
        template = jinja_env.get_template("ops_index.html")

        context = {
            "request": type("Request", (), {})(),
            "request_id": "test",
            "principal": type("P", (), {"user_id": "u", "roles": ["analyst"]})(),
            "render_start": "2024-01-01T12:00:00Z",
            "stats": {
                "total": 5,
                "by_state": {"open": 2, "resolved": 3},
                "by_severity": {"critical": 1, "info": 4},
            },
            "csrf_token": CSRFToken(token="stable_token", timestamp="2024-01-01T12:00:00Z", ttl=900),
        }

        output1 = template.render(**context)
        output2 = template.render(**context)

        assert output1 == output2
