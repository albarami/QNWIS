"""
Unit tests for alert report generation.

Tests markdown/JSON rendering, citations, and freshness integration.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.qnwis.alerts.engine import AlertDecision
from src.qnwis.alerts.report import AlertReportRenderer
from src.qnwis.alerts.rules import (
    AlertRule,
    ScopeConfig,
    Severity,
    TriggerConfig,
    TriggerOperator,
    TriggerType,
    WindowConfig,
)


@pytest.fixture
def renderer():
    """Create AlertReportRenderer instance."""
    return AlertReportRenderer()


@pytest.fixture
def sample_rules():
    """Create sample alert rules for testing."""
    return {
        "retention_drop": AlertRule(
            rule_id="retention_drop",
            metric="retention",
            scope=ScopeConfig(level="sector", code="construction"),
            window=WindowConfig(months=6),
            trigger=TriggerConfig(
                type=TriggerType.YOY_DELTA_PCT,
                op=TriggerOperator.LTE,
                value=-5.0,
            ),
            horizon=12,
            severity=Severity.HIGH,
            description="Alert on 5% YoY retention drop",
        ),
        "salary_low": AlertRule(
            rule_id="salary_low",
            metric="salary",
            scope=ScopeConfig(level="sector"),
            window=WindowConfig(months=3),
            trigger=TriggerConfig(
                type=TriggerType.THRESHOLD,
                op=TriggerOperator.LT,
                value=3000.0,
            ),
            horizon=6,
            severity=Severity.MEDIUM,
        ),
    }


@pytest.fixture
def sample_decisions():
    """Create sample alert decisions for testing."""
    return [
        AlertDecision(
            rule_id="retention_drop",
            triggered=True,
            evidence={
                "yoy_delta_pct": -8.5,
                "threshold": -5.0,
                "operator": "lte",
            },
            message="YoY delta -8.50% lte threshold -5.00%",
            timestamp="2025-01-01T12:00:00Z",
        ),
        AlertDecision(
            rule_id="salary_low",
            triggered=False,
            evidence={
                "current_value": 3500.0,
                "threshold": 3000.0,
                "operator": "lt",
            },
            message="Current value 3500.0000 lt threshold 3000.0000",
            timestamp="2025-01-01T12:00:00Z",
        ),
    ]


class TestMarkdownRendering:
    """Tests for markdown report generation."""

    def test_render_with_triggered_alerts(self, renderer, sample_decisions, sample_rules):
        """Test markdown rendering with triggered alerts."""
        md = renderer.render_markdown(sample_decisions, sample_rules)

        assert "# Alert Center Report" in md
        assert "🚨 Active Alerts" in md
        assert "retention_drop" in md
        assert "🔴 HIGH" in md
        assert "YoY delta -8.50%" in md
        assert "Citations & Freshness" in md
        assert "L19" in md and "L22" in md

    def test_render_no_triggered_alerts(self, renderer, sample_rules):
        """Test markdown rendering with no triggered alerts."""
        decisions = [
            AlertDecision(
                rule_id="test",
                triggered=False,
                message="All good",
            )
        ]

        md = renderer.render_markdown(decisions, sample_rules)

        assert "# Alert Center Report" in md
        assert "✅ No Active Alerts" in md
        assert "🚨 Active Alerts" not in md

    def test_render_with_metadata(self, renderer, sample_decisions, sample_rules):
        """Test markdown rendering with metadata."""
        metadata = {
            "timestamp": "2025-01-01T12:00:00Z",
            "rules_count": 10,
            "alerts_fired": 1,
        }

        md = renderer.render_markdown(sample_decisions, sample_rules, metadata)

        assert "Evaluation Time" in md
        assert "2025-01-01T12:00:00Z" in md
        assert "Rules Evaluated**: 10" in md
        assert "Alerts Fired**: 1" in md

    def test_render_summary_table(self, renderer, sample_decisions, sample_rules):
        """Test evaluation summary table."""
        md = renderer.render_markdown(sample_decisions, sample_rules)

        assert "## Evaluation Summary" in md
        assert "| Rule ID | Status | Message |" in md
        assert "🔴 TRIGGERED" in md
        assert "✅ OK" in md

    def test_severity_emojis(self, renderer):
        """Test severity level emojis in report."""
        decisions = [
            AlertDecision(rule_id="low", triggered=True, message="test"),
            AlertDecision(rule_id="medium", triggered=True, message="test"),
            AlertDecision(rule_id="high", triggered=True, message="test"),
            AlertDecision(rule_id="critical", triggered=True, message="test"),
        ]

        rules = {
            "low": AlertRule(
                rule_id="low",
                metric="test",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=12,
                severity=Severity.LOW,
            ),
            "medium": AlertRule(
                rule_id="medium",
                metric="test",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=12,
                severity=Severity.MEDIUM,
            ),
            "high": AlertRule(
                rule_id="high",
                metric="test",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=12,
                severity=Severity.HIGH,
            ),
            "critical": AlertRule(
                rule_id="critical",
                metric="test",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=12,
                severity=Severity.CRITICAL,
            ),
        }

        md = renderer.render_markdown(decisions, rules)

        assert "🟡" in md  # LOW
        assert "🟠" in md  # MEDIUM
        assert "🔴" in md  # HIGH
        assert "🚨" in md  # CRITICAL


class TestJSONRendering:
    """Tests for JSON report generation."""

    def test_render_json(self, renderer, sample_decisions, sample_rules):
        """Test JSON rendering."""
        json_str = renderer.render_json(sample_decisions, sample_rules)
        data = json.loads(json_str)

        assert "metadata" in data
        assert "alerts" in data
        assert "summary" in data

        assert data["summary"]["total_rules"] == 2
        assert data["summary"]["alerts_fired"] == 1

        assert len(data["alerts"]) == 2
        assert data["alerts"][0]["rule_id"] == "retention_drop"
        assert data["alerts"][0]["triggered"] is True
        assert data["alerts"][0]["severity"] == "high"

    def test_json_with_metadata(self, renderer, sample_decisions, sample_rules):
        """Test JSON rendering with custom metadata."""
        metadata = {"custom_field": "value"}
        json_str = renderer.render_json(sample_decisions, sample_rules, metadata)
        data = json.loads(json_str)

        assert data["metadata"]["custom_field"] == "value"

    def test_json_evidence_included(self, renderer, sample_decisions, sample_rules):
        """Test that evidence is included in JSON."""
        json_str = renderer.render_json(sample_decisions, sample_rules)
        data = json.loads(json_str)

        alert = data["alerts"][0]
        assert "evidence" in alert
        assert alert["evidence"]["yoy_delta_pct"] == -8.5


class TestAuditPackGeneration:
    """Tests for audit pack artifact generation."""

    def test_generate_audit_pack(self, renderer, sample_decisions, sample_rules):
        """Test audit pack generation creates all artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = renderer.generate_audit_pack(
                sample_decisions,
                sample_rules,
                tmpdir,
            )

            assert "markdown" in artifacts
            assert "json" in artifacts
            assert "manifest" in artifacts

            # Verify files exist
            md_path = Path(artifacts["markdown"])
            json_path = Path(artifacts["json"])
            manifest_path = Path(artifacts["manifest"])

            assert md_path.exists()
            assert json_path.exists()
            assert manifest_path.exists()

    def test_audit_pack_markdown_content(self, renderer, sample_decisions, sample_rules):
        """Test audit pack markdown content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = renderer.generate_audit_pack(
                sample_decisions,
                sample_rules,
                tmpdir,
            )

            md_path = Path(artifacts["markdown"])
            content = md_path.read_text(encoding="utf-8")

            assert "# Alert Center Report" in content
            assert "retention_drop" in content

    def test_audit_pack_json_content(self, renderer, sample_decisions, sample_rules):
        """Test audit pack JSON content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = renderer.generate_audit_pack(
                sample_decisions,
                sample_rules,
                tmpdir,
            )

            json_path = Path(artifacts["json"])
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

            assert "alerts" in data
            assert len(data["alerts"]) == 2

    def test_audit_pack_manifest(self, renderer, sample_decisions, sample_rules):
        """Test audit pack manifest with hashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = renderer.generate_audit_pack(
                sample_decisions,
                sample_rules,
                tmpdir,
            )

            manifest_path = Path(artifacts["manifest"])
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)

            assert "timestamp" in manifest
            assert "files" in manifest

            assert "markdown" in manifest["files"]
            assert "json" in manifest["files"]

            # Check hashes exist
            assert "sha256" in manifest["files"]["markdown"]
            assert "sha256" in manifest["files"]["json"]

            # Hash should be 64-char hex
            md_hash = manifest["files"]["markdown"]["sha256"]
            assert len(md_hash) == 64
            assert all(c in "0123456789abcdef" for c in md_hash)

    def test_audit_pack_creates_directory(self, renderer, sample_decisions, sample_rules):
        """Test that audit pack creates output directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "audit"
            artifacts = renderer.generate_audit_pack(
                sample_decisions,
                sample_rules,
                str(nested_dir),
            )

            assert nested_dir.exists()
            assert Path(artifacts["markdown"]).exists()


class TestCitationIntegration:
    """Tests for L19→L22 citation integration."""

    def test_citations_in_markdown(self, renderer, sample_decisions, sample_rules):
        """Test that L19→L22 citations appear in markdown."""
        md = renderer.render_markdown(sample_decisions, sample_rules)

        assert "L19" in md
        assert "L20" in md
        assert "L21" in md
        assert "L22" in md

        assert "Query Definition" in md
        assert "Result Verification" in md
        assert "Audit Trail" in md
        assert "Confidence Scoring" in md
