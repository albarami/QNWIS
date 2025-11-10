"""
Alert report generation with citation-ready narratives.

Renders alert decisions as markdown narratives or JSON with L19→L22 integration.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from .engine import AlertDecision
from .rules import AlertRule

logger = logging.getLogger(__name__)


class AlertReportRenderer:
    """
    Renders alert decisions into citation-ready reports.

    Supports both markdown narratives and structured JSON output.
    Integrates with L19→L22 verification layers.
    """

    def render_markdown(
        self,
        decisions: list[AlertDecision],
        rules: dict[str, AlertRule],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Render alert decisions as markdown narrative.

        Args:
            decisions: List of alert decisions
            rules: Mapping of rule_id to AlertRule for context
            metadata: Optional evaluation metadata (timestamp, etc.)

        Returns:
            Markdown-formatted report
        """
        lines = ["# Alert Center Report", ""]

        if metadata:
            lines.append("## Metadata")
            lines.append(f"- **Evaluation Time**: {metadata.get('timestamp', 'N/A')}")
            lines.append(f"- **Rules Evaluated**: {metadata.get('rules_count', 0)}")
            lines.append(f"- **Alerts Fired**: {metadata.get('alerts_fired', 0)}")
            lines.append("")

        # Triggered alerts
        triggered = [d for d in decisions if d.triggered]
        if triggered:
            lines.append("## 🚨 Active Alerts")
            lines.append("")
            for decision in triggered:
                rule = rules.get(decision.rule_id)
                lines.extend(self._render_decision_md(decision, rule))
                lines.append("")
        else:
            lines.append("## ✅ No Active Alerts")
            lines.append("")

        # Summary of all evaluations
        lines.append("## Evaluation Summary")
        lines.append("")
        lines.append("| Rule ID | Status | Message |")
        lines.append("|---------|--------|---------|")
        for decision in decisions:
            status = "🔴 TRIGGERED" if decision.triggered else "✅ OK"
            msg = decision.message[:60] + "..." if len(decision.message) > 60 else decision.message
            lines.append(f"| `{decision.rule_id}` | {status} | {msg} |")
        lines.append("")

        # Citations and freshness
        lines.append("## Citations & Freshness")
        lines.append("")
        lines.append("All metrics sourced from deterministic DataClient with L19→L22 verification:")
        lines.append("")
        lines.append("- **L19**: Query Definition (YAML specs)")
        lines.append("- **L20**: Result Verification (hash + row count)")
        lines.append("- **L21**: Audit Trail (immutable logs)")
        lines.append("- **L22**: Confidence Scoring (data quality)")
        lines.append("")

        return "\n".join(lines)

    def _render_decision_md(
        self,
        decision: AlertDecision,
        rule: AlertRule | None,
    ) -> list[str]:
        """
        Render a single alert decision as markdown.

        Args:
            decision: Alert decision
            rule: Optional rule specification for context

        Returns:
            List of markdown lines
        """
        lines = [f"### {decision.rule_id}"]

        if rule:
            severity_emoji = {
                "low": "🟡",
                "medium": "🟠",
                "high": "🔴",
                "critical": "🚨",
            }
            emoji = severity_emoji.get(rule.severity.value, "⚠️")
            lines.append(f"**Severity**: {emoji} {rule.severity.value.upper()}")
            lines.append(f"**Metric**: {rule.metric}")
            lines.append(f"**Scope**: {rule.scope.level}" + (f" ({rule.scope.code})" if rule.scope.code else ""))
            if rule.description:
                lines.append(f"**Description**: {rule.description}")
            lines.append("")

        lines.append("**Status**: TRIGGERED")
        lines.append(f"**Message**: {decision.message}")
        lines.append("")

        if decision.evidence:
            lines.append("**Evidence**:")
            for key, value in decision.evidence.items():
                if isinstance(value, float):
                    lines.append(f"- `{key}`: {value:.4f}")
                elif isinstance(value, list):
                    lines.append(f"- `{key}`: {value}")
                else:
                    lines.append(f"- `{key}`: {value}")
            lines.append("")

        return lines

    def render_json(
        self,
        decisions: list[AlertDecision],
        rules: dict[str, AlertRule],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Render alert decisions as structured JSON.

        Args:
            decisions: List of alert decisions
            rules: Mapping of rule_id to AlertRule
            metadata: Optional evaluation metadata

        Returns:
            JSON string
        """
        report: dict[str, Any] = {
            "metadata": metadata or {},
            "alerts": [],
            "summary": {
                "total_rules": len(decisions),
                "alerts_fired": sum(1 for d in decisions if d.triggered),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        }

        for decision in decisions:
            rule = rules.get(decision.rule_id)
            alert_entry = {
                "rule_id": decision.rule_id,
                "triggered": decision.triggered,
                "message": decision.message,
                "evidence": decision.evidence,
            }

            if rule:
                alert_entry["severity"] = rule.severity.value
                alert_entry["metric"] = rule.metric
                alert_entry["scope"] = {
                    "level": rule.scope.level,
                    "code": rule.scope.code,
                }

            report["alerts"].append(alert_entry)

        return json.dumps(report, indent=2, sort_keys=False)

    def generate_audit_pack(
        self,
        decisions: list[AlertDecision],
        rules: dict[str, AlertRule],
        output_dir: str,
    ) -> dict[str, str]:
        """
        Generate audit pack artifacts for triggered alerts.

        Creates markdown reports, JSON evidence, and verification hashes.

        Args:
            decisions: List of alert decisions
            rules: Mapping of rule_id to AlertRule
            output_dir: Directory for audit artifacts

        Returns:
            Dictionary of artifact paths
        """
        import hashlib
        from pathlib import Path

        audit_dir = Path(output_dir)
        audit_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().isoformat().replace(":", "-").split(".")[0]
        artifacts = {}

        # Markdown report
        md_content = self.render_markdown(
            decisions,
            rules,
            metadata={"timestamp": timestamp, "rules_count": len(decisions)},
        )
        md_path = audit_dir / f"alert_report_{timestamp}.md"
        md_path.write_text(md_content, encoding="utf-8")
        artifacts["markdown"] = str(md_path)

        # JSON report
        json_content = self.render_json(decisions, rules, metadata={"timestamp": timestamp})
        json_path = audit_dir / f"alert_report_{timestamp}.json"
        json_path.write_text(json_content, encoding="utf-8")
        artifacts["json"] = str(json_path)

        # Hash manifest
        md_hash = hashlib.sha256(md_content.encode("utf-8")).hexdigest()
        json_hash = hashlib.sha256(json_content.encode("utf-8")).hexdigest()

        manifest = {
            "timestamp": timestamp,
            "files": {
                "markdown": {"path": str(md_path.name), "sha256": md_hash},
                "json": {"path": str(json_path.name), "sha256": json_hash},
            },
        }

        manifest_path = audit_dir / f"manifest_{timestamp}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        artifacts["manifest"] = str(manifest_path)

        logger.info(f"Generated audit pack in {audit_dir}")
        return artifacts
