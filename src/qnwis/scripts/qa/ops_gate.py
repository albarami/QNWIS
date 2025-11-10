"""
RG-3 Operations Gate for Alert Center.

Validates alert system completeness, accuracy, performance, audit, and determinism.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.qnwis.alerts.engine import AlertEngine
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
from src.qnwis.scripts.qa.determinism_scan import (
    DEFAULT_BANNED_PATTERNS,
    scan_for_banned_calls,
)

OPS_GATE_SUMMARY_JSON = project_root / "OPS_GATE_SUMMARY.json"
OPS_GATE_SUMMARY_MD = project_root / "OPS_GATE_SUMMARY.md"
ALERT_STACK_TARGETS = [
    project_root / "src" / "qnwis" / "alerts",
    project_root / "src" / "qnwis" / "monitoring",
    project_root / "src" / "qnwis" / "agents" / "alert_center.py",
    project_root / "src" / "qnwis" / "scripts" / "qa" / "ops_gate.py",
    project_root / "src" / "qnwis" / "scripts" / "qa" / "determinism_scan.py",
]


class OpsGateResult:
    """Result of an ops gate check."""

    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.details = {}

    def pass_gate(self, message: str, details: dict | None = None):
        """Mark gate as passed."""
        self.passed = True
        self.message = message
        self.details = details or {}

    def fail_gate(self, message: str, details: dict | None = None):
        """Mark gate as failed."""
        self.passed = False
        self.message = message
        self.details = details or {}


class RG3OpsGate:
    """RG-3 Operations Gate validator."""

    def __init__(self):
        self.results = []
        self.performance_profile: dict[str, float | int] | None = None

    def run_all_gates(self) -> bool:
        """
        Run all RG-3 gate checks.

        Returns:
            True if all gates pass
        """
        print("=" * 70)
        print("RG-3 OPERATIONS GATE - Alert Center Validation")
        print("=" * 70)
        print()

        gates = [
            ("alerts_completeness", self.gate_completeness),
            ("alerts_accuracy", self.gate_accuracy),
            ("alerts_performance", self.gate_performance),
            ("alerts_determinism", self.gate_determinism),
            ("alerts_audit", self.gate_audit),
        ]

        for gate_name, gate_func in gates:
            print(f"Running gate: {gate_name}...")
            result = gate_func()
            self.results.append(result)

            status_label = "[PASS]" if result.passed else "[FAIL]"
            print(f"  {status_label} {result.message}")

            if result.details:
                for key, value in result.details.items():
                    print(f"     {key}: {value}")
            print()

        all_passed = all(r.passed for r in self.results)

        print("=" * 70)
        status_msg = "RG-3 OPERATIONS GATE: PASSED" if all_passed else "RG-3 OPERATIONS GATE: FAILED"
        print(status_msg)
        print("=" * 70)

        return all_passed

    def gate_completeness(self) -> OpsGateResult:
        """
        Gate 1: Completeness - All rules load and validate.

        Checks:
        - Registry can load sample rules
        - All modules import successfully
        - No missing dependencies
        """
        result = OpsGateResult("alerts_completeness")

        try:
            # Test module imports
            from src.qnwis.alerts import (
                AlertRegistry,
                AlertRule,
            )

            # Create and validate sample rules
            registry = AlertRegistry()

            sample_rules = [
                AlertRule(
                    rule_id=f"test_rule_{i}",
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
                    description=f"Test rule {i}",
                )
                for i in range(10)
            ]

            for rule in sample_rules:
                registry.add_rule(rule)

            is_valid, errors = registry.validate_all()

            if not is_valid:
                result.fail_gate(
                    "Rule validation failed",
                    {"error_count": len(errors), "errors": errors[:3]},
                )
                return result

            result.pass_gate(
                "All modules loaded and rules validated",
                {"rules_loaded": len(registry), "validation_errors": 0},
            )

        except Exception as e:
            result.fail_gate(f"Import or validation error: {e}")

        return result

    def gate_accuracy(self) -> OpsGateResult:
        """
        Gate 2: Accuracy - Sample evaluations return expected decisions.

        Checks:
        - Threshold triggers work correctly
        - YoY delta triggers work correctly
        - Slope triggers work correctly
        - Break detection works correctly
        """
        result = OpsGateResult("alerts_accuracy")

        try:
            engine = AlertEngine()
            test_cases = []

            # Test 1: Threshold trigger (should fire)
            rule1 = AlertRule(
                rule_id="threshold_test",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.THRESHOLD,
                    op=TriggerOperator.LT,
                    value=0.5,
                ),
                horizon=12,
                severity=Severity.LOW,
            )
            decision1 = engine.evaluate(rule1, [0.6, 0.5, 0.4], [])
            test_cases.append(("threshold_trigger", decision1.triggered is True))

            # Test 2: YoY delta trigger (should fire)
            rule2 = AlertRule(
                rule_id="yoy_test",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=6),
                trigger=TriggerConfig(
                    type=TriggerType.YOY_DELTA_PCT,
                    op=TriggerOperator.LTE,
                    value=-5.0,
                ),
                horizon=12,
                severity=Severity.HIGH,
            )
            # 10% drop: 0.5 -> 0.45
            series2 = [0.5] * 12 + [0.45]
            decision2 = engine.evaluate(rule2, series2, [])
            test_cases.append(("yoy_delta_trigger", decision2.triggered is True))

            # Test 3: Slope trigger (should fire)
            rule3 = AlertRule(
                rule_id="slope_test",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=3),
                trigger=TriggerConfig(
                    type=TriggerType.SLOPE_WINDOW,
                    op=TriggerOperator.LT,
                    value=-0.01,
                ),
                horizon=12,
                severity=Severity.MEDIUM,
            )
            series3 = [0.5, 0.48, 0.46, 0.44, 0.42, 0.40]
            decision3 = engine.evaluate(rule3, series3, [])
            test_cases.append(("slope_trigger", decision3.triggered is True))

            # Test 4: Break detection (should fire on level shift)
            rule4 = AlertRule(
                rule_id="break_test",
                metric="retention",
                scope=ScopeConfig(level="sector"),
                window=WindowConfig(months=12),
                trigger=TriggerConfig(
                    type=TriggerType.BREAK_EVENT,
                    value=3.0,
                ),
                horizon=12,
                severity=Severity.CRITICAL,
            )
            series4 = [0.5] * 6 + [0.7] * 6
            decision4 = engine.evaluate(rule4, series4, [])
            test_cases.append(("break_detection", decision4.triggered is True))

            # Check all test cases
            failed_cases = [name for name, passed in test_cases if not passed]

            if failed_cases:
                result.fail_gate(
                    "Some accuracy tests failed",
                    {
                        "total_tests": len(test_cases),
                        "failed_tests": len(failed_cases),
                        "failures": failed_cases,
                    },
                )
            else:
                result.pass_gate(
                    "All accuracy tests passed",
                    {"tests_passed": len(test_cases)},
                )

        except Exception as e:
            result.fail_gate(f"Accuracy test error: {e}")

        return result

    def gate_performance(self) -> OpsGateResult:
        """
        Gate 3: Performance - p95 < 150ms for 200 rules.

        Checks:
        - Batch evaluation of 200 rules
        - p95 latency under threshold
        """
        result = OpsGateResult("alerts_performance")

        try:
            engine = AlertEngine()

            # Generate 200 test rules
            rules = []
            for i in range(200):
                rule = AlertRule(
                    rule_id=f"perf_rule_{i:04d}",
                    metric="retention",
                    scope=ScopeConfig(level="sector"),
                    window=WindowConfig(months=3 + (i % 9)),
                    trigger=TriggerConfig(
                        type=TriggerType.THRESHOLD,
                        op=TriggerOperator.LT,
                        value=0.5,
                    ),
                    horizon=12,
                    severity=Severity.LOW,
                )
                rules.append(rule)

            def data_provider(rule):
                return [0.6, 0.5, 0.4], []

            # Warm-up
            engine.batch_evaluate(rules, data_provider)

            # Benchmark
            latencies = []
            for _ in range(10):
                start = time.perf_counter()
                _ = engine.batch_evaluate(rules, data_provider)
                elapsed = time.perf_counter() - start
                latencies.append(elapsed * 1000)

            # Compute p95
            latencies.sort()
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[int(len(latencies) * 0.95)]
            self.performance_profile = {
                "p50_ms": round(p50, 3),
                "p95_ms": round(p95, 3),
                "samples": len(latencies),
                "rules_per_sample": len(rules),
            }

            if p95 >= 150.0:
                result.fail_gate(
                    f"p95 latency {p95:.2f}ms exceeds 150ms threshold",
                    {
                        "p50_ms": round(p50, 2),
                        "p95_ms": round(p95, 2),
                        "samples": len(latencies),
                        "rules_per_sample": len(rules),
                    },
                )
            else:
                result.pass_gate(
                    f"Performance target met: p95={p95:.2f}ms",
                    {
                        "p50_ms": round(p50, 2),
                        "p95_ms": round(p95, 2),
                        "samples": len(latencies),
                        "rules_per_sample": len(rules),
                    },
                )

        except Exception as e:
            result.fail_gate(f"Performance test error: {e}")

        return result

    def gate_determinism(self) -> OpsGateResult:
        """
        Gate 4: Determinism - forbid datetime.now/time.time/random.* in alert stack.
        """

        result = OpsGateResult("alerts_determinism")
        try:
            violations = scan_for_banned_calls(ALERT_STACK_TARGETS, DEFAULT_BANNED_PATTERNS)
            if violations:
                result.fail_gate(
                    "Forbidden datetime/time/random usage detected",
                    {"violations": violations},
                )
            else:
                result.pass_gate("Alert stack determinism guard passed")
        except Exception as exc:  # pragma: no cover
            result.fail_gate(f"Determinism scan error: {exc}")
        return result

    def gate_audit(self) -> OpsGateResult:
        """
        Gate 4: Audit - Audit pack generation with citations & hashes.

        Checks:
        - Report renderer generates audit artifacts
        - Markdown and JSON reports created
        - Hash manifest generated
        - Citations present
        """
        result = OpsGateResult("alerts_audit")

        try:
            import tempfile

            renderer = AlertReportRenderer()

            # Create sample decisions and rules
            from src.qnwis.alerts.engine import AlertDecision

            decisions = [
                AlertDecision(
                    rule_id="audit_test",
                    triggered=True,
                    evidence={"test_value": 0.5},
                    message="Test alert triggered",
                )
            ]

            rules = {
                "audit_test": AlertRule(
                    rule_id="audit_test",
                    metric="retention",
                    scope=ScopeConfig(level="sector"),
                    window=WindowConfig(months=3),
                    trigger=TriggerConfig(
                        type=TriggerType.THRESHOLD,
                        op=TriggerOperator.LT,
                        value=0.5,
                    ),
                    horizon=12,
                    severity=Severity.HIGH,
                )
            }

            with tempfile.TemporaryDirectory() as tmpdir:
                artifacts = renderer.generate_audit_pack(decisions, rules, tmpdir)

                # Verify artifacts exist
                required_keys = ["markdown", "json", "manifest"]
                missing_keys = [k for k in required_keys if k not in artifacts]

                if missing_keys:
                    result.fail_gate(
                        "Missing audit artifacts",
                        {"missing": missing_keys},
                    )
                    return result

                # Verify files exist
                for key, path in artifacts.items():
                    if not Path(path).exists():
                        result.fail_gate(
                            f"Artifact file not found: {key}",
                            {"path": path},
                        )
                        return result

                # Verify markdown contains citations
                md_path = Path(artifacts["markdown"])
                md_content = md_path.read_text(encoding="utf-8")

                required_citations = ["L19", "L20", "L21", "L22"]
                missing_citations = [c for c in required_citations if c not in md_content]

                if missing_citations:
                    result.fail_gate(
                        "Missing citations in markdown",
                        {"missing": missing_citations},
                    )
                    return result

                # Verify manifest has hashes
                manifest_path = Path(artifacts["manifest"])
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)

                if "files" not in manifest:
                    result.fail_gate("Manifest missing 'files' key")
                    return result

                # Verify hash format
                for file_key in ["markdown", "json"]:
                    if file_key not in manifest["files"]:
                        result.fail_gate(f"Manifest missing {file_key} file entry")
                        return result

                    file_entry = manifest["files"][file_key]
                    if "sha256" not in file_entry:
                        result.fail_gate(f"Manifest missing sha256 for {file_key}")
                        return result

                    sha_hash = file_entry["sha256"]
                    if len(sha_hash) != 64:
                        result.fail_gate(
                            f"Invalid sha256 hash length for {file_key}",
                            {"length": len(sha_hash)},
                        )
                        return result

                result.pass_gate(
                    "Audit pack generation successful",
                    {
                        "artifacts_count": len(artifacts),
                        "citations_present": True,
                        "hashes_valid": True,
                    },
                )

        except Exception as e:
            result.fail_gate(f"Audit pack generation error: {e}")

        return result

    def export_results(self, output_path: str):
        """Export gate results to JSON."""
        results_data = {
            "rg3_ops_gate": "alert_center",
            "passed": all(r.passed for r in self.results),
            "gates": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2)

        print(f"\nResults exported to: {output_path}")

    def build_summary_payload(self) -> dict[str, Any]:
        """Build structured summary payload for downstream readiness gate."""
        determinism_gate = next((r for r in self.results if r.name == "alerts_determinism"), None)
        determinism_payload = {
            "passed": determinism_gate.passed if determinism_gate else True,
            "violations": (determinism_gate.details.get("violations", []) if determinism_gate else []),
        }
        payload: dict[str, object] = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "overall_passed": all(r.passed for r in self.results),
            "performance": self.performance_profile or {},
            "determinism": determinism_payload,
            "gates": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.results
            ],
        }
        return payload

    @staticmethod
    def _render_summary_markdown(payload: dict[str, Any]) -> str:
        lines = [
            "# Ops Gate Summary",
            "",
            f"- Generated: {payload.get('generated_at', 'n/a')}",
            f"- Overall Status: {'PASS' if payload.get('overall_passed') else 'FAIL'}",
            "",
            "## Performance Benchmarks",
            "",
        ]
        performance = payload.get("performance") or {}
        if performance:
            lines.append(f"- p50 latency: {performance.get('p50_ms', 'n/a')} ms")
            lines.append(f"- p95 latency: {performance.get('p95_ms', 'n/a')} ms")
            samples = performance.get("samples")
            rules_per_sample = performance.get("rules_per_sample")
            if samples is not None:
                sample_line = f"- Samples: {samples} runs"
                if rules_per_sample is not None:
                    sample_line = f"{sample_line} / {rules_per_sample} rules"
                lines.append(sample_line)
        else:
            lines.append("- Not available (benchmark step did not complete)")

        determinism = payload.get("determinism") or {}
        lines.extend(
            [
                "",
                "## Determinism Scan",
                "",
                f"- Status: {'PASS' if determinism.get('passed') else 'FAIL'}",
            ]
        )
        violations = determinism.get("violations") or []
        if violations:
            for violation in violations[:10]:
                lines.append(
                    f"  - {violation.get('file')}:{violation.get('line')} -> {violation.get('pattern')}"
                )
            if len(violations) > 10:
                lines.append(f"  - ... ({len(violations) - 10} more)")
        else:
            lines.append("- No forbidden datetime.now/time.time/random.* usage detected.")

        lines.extend(["", "## Gate Status", "", "| Gate | Status | Message |", "| --- | --- | --- |"])
        for gate in payload.get("gates", []):
            name = gate.get("name", "unknown")
            status = "PASS" if gate.get("passed") else "FAIL"
            msg = gate.get("message", "")
            lines.append(f"| {name} | {status} | {msg} |")

        return "\n".join(lines)

    def write_summary(
        self,
        json_path: Path = OPS_GATE_SUMMARY_JSON,
        markdown_path: Path = OPS_GATE_SUMMARY_MD,
    ) -> None:
        """Write Ops Gate summary in JSON and Markdown formats."""
        payload = self.build_summary_payload()
        json_path = Path(json_path)
        markdown_path = Path(markdown_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        markdown_path.write_text(self._render_summary_markdown(payload), encoding="utf-8")
        print(f"Ops Gate summary written to {json_path} and {markdown_path}")


def main():
    """Main entry point."""
    gate = RG3OpsGate()
    passed = gate.run_all_gates()

    # Export results
    output_path = "docs/audit/alerts/rg3_ops_gate_results.json"
    gate.export_results(output_path)
    gate.write_summary()

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
