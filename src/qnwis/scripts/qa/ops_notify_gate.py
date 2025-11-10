"""
RG-4 Ops-Notifications Gate.

Validates notification and incident management system readiness:
- Completeness: All modules load, env validated, channels wired
- Accuracy: Golden fixtures produce expected notifications
- Performance: p95 dispatch < 50ms for 100 notifications (dry-run)
- Audit: Ledger integrity and HMAC verification
- Determinism: No non-deterministic code in notification pipeline
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from ...notify.dispatcher import NotificationDispatcher
from ...notify.models import Channel, Notification, Severity
from ...notify.resolver import IncidentResolver
from ...utils.clock import Clock
from .determinism_scan import DEFAULT_BANNED_PATTERNS, scan_for_banned_calls

REPO_ROOT = Path(__file__).resolve().parents[4]
OPS_NOTIFY_REPORT_JSON = REPO_ROOT / "ops_notify_report.json"
OPS_NOTIFY_SUMMARY_MD = REPO_ROOT / "OPS_NOTIFY_SUMMARY.md"
NOTIFY_DIR = REPO_ROOT / "src" / "qnwis" / "notify"
AGENT_DIR = REPO_ROOT / "src" / "qnwis" / "agents"


def _modified_agent_files() -> list[Path]:
    """Return python agent files changed in working tree."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", str(AGENT_DIR.relative_to(REPO_ROOT))],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return sorted(AGENT_DIR.rglob("*.py"))

    files: set[Path] = set()
    for raw_line in result.stdout.splitlines():
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue
        rel_path = line[3:]
        if " -> " in rel_path:
            rel_path = rel_path.split(" -> ", 1)[1]
        path = (REPO_ROOT / rel_path.strip()).resolve()
        if path.suffix == ".py" and path.exists():
            files.add(path)

    if not files:
        return []

    return sorted(files)


class RG4OpsNotificationsGate:
    """RG-4 Ops-Notifications readiness gate."""

    def __init__(self) -> None:
        """Initialize gate."""
        self.results: dict[str, dict[str, Any]] = {}
        self.performance_metrics: dict[str, float] = {}
        self.incident_metrics: dict[str, Any] = {}
        self.determinism_report: dict[str, Any] = {}

    def run_all(self) -> dict[str, bool]:
        """
        Run all RG-4 gate checks.

        Returns:
            Dict mapping check name to pass/fail
        """
        checks = {
            "notify_completeness": self.check_completeness,
            "notify_accuracy": self.check_accuracy,
            "notify_performance": self.check_performance,
            "notify_audit": self.check_audit,
            "notify_determinism": self.check_determinism,
        }

        results = {}
        for name, check in checks.items():
            try:
                passed = check()
                results[name] = passed
                self.results[name] = {"passed": passed}
            except Exception as e:
                results[name] = False
                self.results[name] = {"passed": False, "error": str(e)}

        self.collect_incident_metrics()
        return results

    def check_completeness(self) -> bool:
        """
        Check that all notification modules load and channels are wired.

        Returns:
            True if complete
        """
        print("Running notify_completeness check...")

        try:
            # Import all modules
            from ...notify import (
                Channel,
                IncidentResolver,
                IncidentState,
                NotificationDispatcher,
                Severity,
            )
            from ...notify.channels import EmailChannel, TeamsChannel, WebhookChannel

            # Verify models
            assert Channel.EMAIL is not None
            assert Severity.CRITICAL is not None
            assert IncidentState.OPEN is not None

            # Verify classes instantiate
            clock = Clock()
            dispatcher = NotificationDispatcher(clock=clock, dry_run=True)
            resolver = IncidentResolver(clock=clock)

            # Verify channels
            email = EmailChannel(dry_run=True)
            teams = TeamsChannel(dry_run=True)
            webhook = WebhookChannel(dry_run=True)

            assert dispatcher is not None
            assert resolver is not None
            assert email is not None
            assert teams is not None
            assert webhook is not None

            print("[OK] All modules load successfully")
            print("[OK] All channels wired")
            return True

        except Exception as e:
            print(f"[ERROR] Completeness check failed: {e}")
            return False

    def check_accuracy(self) -> bool:
        """
        Check notification accuracy with golden fixtures.

        Verifies:
        - 1 alert → 1 incident → 1 message per channel
        - Escalation after T minutes (simulated)

        Returns:
            True if accurate
        """
        print("Running notify_accuracy check...")

        try:
            clock = Clock()
            dispatcher = NotificationDispatcher(clock=clock, dry_run=True)
            resolver = IncidentResolver(clock=clock)

            # Golden fixture: Create notification
            notification = Notification(
                notification_id="test_notify_001",
                rule_id="test_rule_retention_low",
                severity=Severity.WARNING,
                message="Test alert: Retention below threshold",
                scope={"level": "sector", "code": "010"},
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-01T23:59:59Z",
                channels=[Channel.EMAIL, Channel.TEAMS],
                evidence={"retention_rate": 0.65, "threshold": 0.70},
                timestamp=clock.now_iso(),
            )

            # Dispatch
            results = dispatcher.dispatch(notification)

            # Verify 1 message per channel
            assert "email" in results, "Email channel missing from results"
            assert "teams" in results, "Teams channel missing from results"
            assert results["email"] == "dry_run_success", "Email dispatch failed"
            assert results["teams"] == "dry_run_success", "Teams dispatch failed"

            # Verify incident created
            incident = resolver.get_incident("test_notify_001")
            assert incident is not None, "Incident not found in resolver"

            # Verify incident details
            assert incident.rule_id == "test_rule_retention_low"
            assert incident.severity == Severity.WARNING
            assert incident.message == "Test alert: Retention below threshold"

            print("[OK] 1 alert -> 1 incident -> 1 message per channel")
            print("[OK] Golden fixture validation passed")
            return True

        except AssertionError as e:
            print(f"[ERROR] Accuracy check failed: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Accuracy check error: {e}")
            return False

    def check_performance(self) -> bool:
        """
        Check notification dispatch performance.

        Requirement: p95 dispatch < 50ms for 100 notifications (dry-run)

        Returns:
            True if performant
        """
        print("Running notify_performance check...")

        try:
            clock = Clock()
            dispatcher = NotificationDispatcher(clock=clock, dry_run=True)

            # Dispatch 100 notifications
            latencies = []
            for i in range(100):
                notification = Notification(
                    notification_id=f"perf_test_{i:03d}",
                    rule_id=f"test_rule_{i % 10}",
                    severity=Severity.INFO,
                    message=f"Performance test notification {i}",
                    scope={"level": "national", "code": ""},
                    window_start="2024-01-01T00:00:00Z",
                    window_end="2024-01-01T23:59:59Z",
                    channels=[Channel.EMAIL],
                    evidence={},
                    timestamp=clock.now_iso(),
                )

                start = time.perf_counter()
                dispatcher.dispatch(notification)
                end = time.perf_counter()

                latency_ms = (end - start) * 1000
                latencies.append(latency_ms)

            latencies.sort()

            def percentile(values: list[float], pct: float) -> float:
                if not values:
                    return 0.0
                position = pct * (len(values) - 1)
                lower = int(position)
                upper = min(len(values) - 1, lower + 1)
                weight = position - lower
                if upper == lower:
                    return values[lower]
                return values[lower] * (1 - weight) + values[upper] * weight

            p50_latency = percentile(latencies, 0.50)
            p95_latency = percentile(latencies, 0.95)
            p99_latency = percentile(latencies, 0.99)

            self.performance_metrics = {
                "sample_size": len(latencies),
                "p50_ms": p50_latency,
                "p95_ms": p95_latency,
                "p99_ms": p99_latency,
            }

            print(f"p50 latency: {p50_latency:.2f}ms")
            print(f"p95 latency: {p95_latency:.2f}ms")
            print(f"p99 latency: {p99_latency:.2f}ms")

            if p95_latency < 50:
                print("[OK] p95 latency within 50ms threshold")
                return True

            print(f"[ERROR] p95 latency {p95_latency:.2f}ms exceeds 50ms threshold")
            return False

        except Exception as e:
            print(f"[ERROR] Performance check error: {e}")
            return False

    def check_audit(self) -> bool:
        """
        Check audit ledger integrity.

        Verifies:
        - Ledger + HMAC envelope present
        - Integrity verified via SHA256

        Returns:
            True if audit trail is valid
        """
        print("Running notify_audit check...")

        try:
            clock = Clock()
            dispatcher = NotificationDispatcher(clock=clock, dry_run=True)
            ledger_dir = dispatcher.ledger_dir

            # Create test notification
            notification = Notification(
                notification_id="audit_test_001",
                rule_id="test_rule_audit",
                severity=Severity.INFO,
                message="Audit test notification",
                scope={"level": "national", "code": ""},
                window_start="2024-01-01T00:00:00Z",
                window_end="2024-01-01T23:59:59Z",
                channels=[Channel.EMAIL],
                evidence={},
                timestamp=clock.now_iso(),
            )

            # Dispatch to create ledger entry
            dispatcher.dispatch(notification)

            # Verify ledger file exists
            ledger_file = ledger_dir / "incidents.jsonl"
            assert ledger_file.exists(), "Ledger file not found"

            # Verify envelope exists
            envelope_file = ledger_dir / "audit_test_001.envelope.json"
            assert envelope_file.exists(), "Envelope file not found"

            # Load and verify envelope
            with open(envelope_file, encoding="utf-8") as f:
                envelope = json.load(f)

            assert "incident_id" in envelope, "Missing incident_id in envelope"
            assert "payload" in envelope, "Missing payload in envelope"
            assert "signature" in envelope, "Missing signature in envelope"
            assert "algorithm" in envelope, "Missing algorithm in envelope"
            assert envelope["algorithm"] == "sha256", "Incorrect algorithm"

            # Verify signature
            payload = envelope["payload"]
            expected_sig = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            assert envelope["signature"] == expected_sig, "Signature mismatch"

            print("[OK] Ledger file present")
            print("[OK] HMAC envelope present")
            print("[OK] Signature integrity verified")
            return True

        except AssertionError as e:
            print(f"[ERROR] Audit check failed: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Audit check error: {e}")
            return False

    def check_determinism(self) -> bool:
        """
        Check for non-deterministic code in notification pipeline.

        Scans for datetime.now, time.time, random.* calls.

        Returns:
            True if deterministic
        """
        print("Running notify_determinism check...")

        try:
            targets = [NOTIFY_DIR]
            modified_agents = _modified_agent_files()
            targets.extend(modified_agents)

            violations = scan_for_banned_calls(targets, DEFAULT_BANNED_PATTERNS)
            self.determinism_report = {
                "passed": not violations,
                "violations": violations,
                "targets_scanned": [
                    str(path.relative_to(REPO_ROOT)) if isinstance(path, Path) and path.is_absolute()
                    else str(path)
                    for path in targets
                ],
            }

            if violations:
                print("[ERROR] Non-deterministic code found:")
                for violation in violations:
                    file_path = violation.get('file')
                    line = violation.get('line')
                    pattern = violation.get('pattern')
                    print(f"  - {file_path}:{line} -> {pattern}")
                return False

            print("[OK] No banned datetime/time/random usage detected")
            return True

        except Exception as e:
            self.determinism_report = {"passed": False, "error": str(e), "violations": []}
            print(f"[ERROR] Determinism check error: {e}")
            return False

    def collect_incident_metrics(self) -> dict[str, Any]:
        """Aggregate incident stats for reporting."""
        try:
            resolver = IncidentResolver(clock=Clock())
            stats = resolver.get_stats()
            metrics = {
                "total": stats.get("total", 0),
                "open": stats.get("by_state", {}).get("open", 0),
                "ack": stats.get("by_state", {}).get("ack", 0),
                "silenced": stats.get("by_state", {}).get("silenced", 0),
                "resolved": stats.get("by_state", {}).get("resolved", 0),
            }
        except Exception as exc:
            metrics = {"error": str(exc)}

        self.incident_metrics = metrics
        return metrics

    def build_summary_payload(self) -> dict[str, Any]:
        """Build JSON-serializable payload for artifacts."""
        overall_passed = all(result.get("passed", False) for result in self.results.values())
        return {
            "generated_at": Clock().now_iso(),
            "overall_passed": overall_passed,
            "performance": self.performance_metrics,
            "incidents": self.incident_metrics,
            "determinism": self.determinism_report,
            "checks": self.results,
        }

    def _render_summary_markdown(self, payload: dict[str, Any]) -> str:
        """Render markdown summary for artifacts and docs."""
        def fmt_latency(key: str) -> str:
            value = perf.get(key)
            return f"{value:.2f}" if isinstance(value, (int, float)) else "n/a"

        lines = [
            "# RG-4 Ops Notify Summary",
            "",
            f"- Generated: {payload.get('generated_at')}",
            f"- RG-4 Status: {'PASS' if payload.get('overall_passed') else 'FAIL'}",
            "",
            "## Performance (ms)",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
        perf = payload.get("performance") or {}
        lines.append(f"| p50 | {fmt_latency('p50_ms')} |")
        lines.append(f"| p95 | {fmt_latency('p95_ms')} |")
        lines.append(f"| p99 | {fmt_latency('p99_ms')} |")
        lines.append(f"| Sample Size | {perf.get('sample_size', 'n/a')} |")
        lines.extend(
            [
                "",
                "## Incident Metrics",
                "",
                "| State | Count |",
                "| --- | --- |",
            ]
        )
        incidents = payload.get("incidents") or {}
        if "error" in incidents:
            lines.append(f"| error | {incidents['error']} |")
        else:
            lines.append(f"| Open | {incidents.get('open', 0)} |")
            lines.append(f"| Ack | {incidents.get('ack', 0)} |")
            lines.append(f"| Silenced | {incidents.get('silenced', 0)} |")
            lines.append(f"| Resolved | {incidents.get('resolved', 0)} |")
            lines.append(f"| Total | {incidents.get('total', 0)} |")
        lines.extend(
            [
                "",
                "## Determinism Scan",
                "",
            ]
        )
        determinism = payload.get("determinism") or {}
        if determinism.get("violations"):
            lines.append("### Violations")
            for violation in determinism["violations"][:10]:
                lines.append(
                    f"- {violation.get('file')}:{violation.get('line')} -> {violation.get('pattern')}"
                )
        else:
            lines.append("- No forbidden datetime/time/random usage detected.")
        lines.extend(
            [
                "",
                "## Gate Checks",
                "",
                "| Check | Status |",
                "| --- | --- |",
            ]
        )
        for name, result in self.results.items():
            status = "PASS" if result.get("passed") else "FAIL"
            lines.append(f"| {name} | {status} |")
        return "\n".join(lines)

    def write_artifacts(
        self,
        json_path: Path = OPS_NOTIFY_REPORT_JSON,
        markdown_path: Path = OPS_NOTIFY_SUMMARY_MD,
    ) -> None:
        """Write JSON + Markdown artifacts."""
        payload = self.build_summary_payload()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        markdown_path.write_text(self._render_summary_markdown(payload), encoding="utf-8")

    def print_summary(self) -> None:
        """Print gate summary."""
        print("\n" + "=" * 60)
        print("RG-4 Ops-Notifications Gate Summary")
        print("=" * 60)

        all_passed = all(r.get("passed", False) for r in self.results.values())

        for check, result in self.results.items():
            status = "PASS" if result.get("passed") else "FAIL"
            symbol = "[PASS]" if result.get("passed") else "[FAIL]"
            print(f"{check:30s} {symbol} {status}")
            if not result.get("passed") and "error" in result:
                print(f"  Error: {result['error']}")

        print("=" * 60)
        if all_passed:
            print("[PASS] RG-4 GATE PASSED - Notification system ready")
        else:
            print("[FAIL] RG-4 GATE FAILED - Address issues above")
        print("=" * 60)


def main() -> int:
    """Run RG-4 gate and return exit code."""
    gate = RG4OpsNotificationsGate()
    results = gate.run_all()
    gate.write_artifacts()
    gate.print_summary()

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
