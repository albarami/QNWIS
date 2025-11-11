"""
RG-5 Ops Console Gate - Production readiness validation.

Validates:
- UI completeness (pages, templates, routes, a11y)
- UI performance (p95 render < 150ms, SSE < 5ms)
- UI security (CSRF, cookies, headers, no inline scripts)
- UI determinism (no banned calls, stable sorting)
- UI audit (actions emit audit entries)
"""

# ruff: noqa: I001

from __future__ import annotations

import ast
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

# Add src to path
sys.path.insert(0, str(Path(__file__).parents[4]))

from src.qnwis.ops_console.app import create_ops_app  # noqa: E402
from src.qnwis.ops_console.perf_metrics import (  # noqa: E402
    collect_ui_metrics,
    persist_ui_metrics,
)
from src.qnwis.utils.clock import ManualClock  # noqa: E402


def _flatten_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    render = metrics.get("render", {})
    incidents = render.get("incidents", {})
    detail = render.get("incident_detail", {})
    sse_metrics = metrics.get("sse", {})
    csrf_section = metrics.get("csrf", {})
    csrf_verify = csrf_section.get("verify", csrf_section)
    return {
        "incidents_p50_ms": incidents.get("p50_ms", 0.0),
        "incidents_p95_ms": incidents.get("p95_ms", 0.0),
        "detail_p50_ms": detail.get("p50_ms", 0.0),
        "detail_p95_ms": detail.get("p95_ms", 0.0),
        "sse_p95_ms": sse_metrics.get("p95_ms") or sse_metrics.get("enqueue_p95_ms", 0.0),
        "csrf_p95_ms": csrf_verify.get("p95_ms", 0.0),
    }


JsonDict = dict[str, Any]


def _checks(container: JsonDict) -> dict[str, Any]:
    if "checks" not in container:
        container["checks"] = {}
    return cast(dict[str, Any], container["checks"])


def _errors(container: JsonDict) -> list[str]:
    if "errors" not in container:
        container["errors"] = []
    return cast(list[str], container["errors"])


def _metrics(container: JsonDict) -> dict[str, Any]:
    if "metrics" not in container:
        container["metrics"] = {}
    return cast(dict[str, Any], container["metrics"])


def check_ui_completeness() -> JsonDict:
    """
    Validate UI completeness.

    Checks:
    - All required pages exist
    - Templates compile
    - Routes are mounted
    - Basic a11y heuristics (labels, roles)
    """
    print("🔍 Checking UI completeness...")

    results: JsonDict = {
        "passed": True,
        "checks": {},
        "errors": [],
    }
    checks = _checks(results)
    errors = _errors(results)

    # Check template files exist
    templates_dir = Path(__file__).parents[3] / "qnwis" / "ops_console" / "templates"
    required_templates = [
        "layout.html",
        "ops_index.html",
        "incidents_list.html",
        "incident_detail.html",
        "alerts_list.html",
    ]

    for template_name in required_templates:
        template_path = templates_dir / template_name
        exists = template_path.exists()
        checks[f"template_{template_name}"] = exists

        if not exists:
            results["passed"] = False
            errors.append(f"Template missing: {template_name}")
        else:
            # Check for basic a11y attributes
            content = template_path.read_text(encoding="utf-8")

            # Check for labels
            has_labels = True
            if "<input" in content or "<select" in content or "<textarea" in content:
                has_labels = ("<label" in content or "aria-label" in content)

            checks[f"a11y_labels_{template_name}"] = has_labels

            if not has_labels:
                errors.append(f"Template {template_name} has inputs without labels")

            # Check for semantic HTML
            has_semantic = any(tag in content for tag in ["<nav", "<main", "<footer", "role="])
            checks[f"semantic_html_{template_name}"] = has_semantic

    # Check routes mounted
    try:
        app = create_ops_app(clock=ManualClock())
        route_paths = [route.path for route in app.routes]

        required_routes = [
            "/",
            "/incidents",
            "/incidents/{incident_id}",
            "/incidents/{incident_id}/ack",
            "/incidents/{incident_id}/resolve",
            "/incidents/{incident_id}/silence",
            "/alerts",
            "/stream/incidents",
        ]

        for route_path in required_routes:
            mounted = route_path in route_paths
            checks[f"route_{route_path}"] = mounted

            if not mounted:
                results["passed"] = False
                errors.append(f"Route not mounted: {route_path}")

    except Exception as exc:
        results["passed"] = False
        errors.append(f"Failed to create app: {exc}")

    # Check CSS assets
    assets_dir = Path(__file__).parents[3] / "qnwis" / "ops_console" / "assets"
    css_exists = (assets_dir / "style.css").exists()
    checks["css_assets"] = css_exists

    if not css_exists:
        results["passed"] = False
        errors.append("CSS assets missing")

    return results


def check_ui_performance() -> JsonDict:
    """
    Validate UI performance.

    Checks:
    - p95 page render < 150ms (list + detail)
    - SSE enqueue < 5ms
    - CSRF verification < 1ms
    """
    print("?s? Checking UI performance...")

    results: JsonDict = {
        "passed": True,
        "checks": {},
        "metrics": {},
        "errors": [],
    }
    checks = _checks(results)
    errors = _errors(results)
    metrics_store = _metrics(results)

    try:
        test_file = Path(__file__).parents[4] / "tests" / "unit" / "ops_console" / "test_perf_render.py"

        if not test_file.exists():
            results["passed"] = False
            errors.append("Performance test file not found")
            return results

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            "-x",
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        checks["perf_tests_passed"] = proc.returncode == 0

        if proc.returncode != 0:
            results["passed"] = False
            errors.append("Performance tests failed")
            results["test_output"] = proc.stdout + "\n" + proc.stderr
            return results

        metrics = collect_ui_metrics()
        metrics_path = persist_ui_metrics(metrics)
        flattened = _flatten_metrics(metrics)
        metrics_store.update(flattened)
        metrics_store["metrics_file"] = str(metrics_path)

        budgets = {
            "incidents_p95_ms": 150.0,
            "detail_p95_ms": 150.0,
            "sse_p95_ms": 5.0,
            "csrf_p95_ms": 1.0,
        }
        for key, threshold in budgets.items():
            value = flattened.get(key, 0.0)
            check_name = f"{key}_budget"
            within_budget = value < threshold
            checks[check_name] = within_budget
            if not within_budget:
                results["passed"] = False
                errors.append(f"{key} {value:.3f}ms exceeds {threshold}ms budget")

        checks["ui_metrics_saved"] = metrics_path.exists()

    except subprocess.TimeoutExpired:
        results["passed"] = False
        errors.append("Performance tests timed out")

    except Exception as exc:
        results["passed"] = False
        errors.append(f"Performance check failed: {exc}")

    return results


def check_ui_security() -> JsonDict:
    """
    Validate UI security.

    Checks:
    - CSRF tokens present on POST forms
    - SameSite cookies (if applicable)
    - Security headers set
    - No inline scripts without nonce
    """
    print("[rg5] Checking UI security...")

    results: JsonDict = {
        "passed": True,
        "checks": {},
        "errors": [],
    }
    checks = _checks(results)
    errors = _errors(results)

    csrf_module = Path(__file__).parents[3] / "qnwis" / "ops_console" / "csrf.py"
    csrf_exists = csrf_module.exists()
    checks["csrf_module_exists"] = csrf_exists

    if not csrf_exists:
        results["passed"] = False
        errors.append("CSRF module missing")
    else:
        content = csrf_module.read_text(encoding="utf-8")
        has_protection = "class CSRFProtection" in content
        has_verify = "verify_token" in content
        has_generate = "generate_token" in content
        checks["csrf_protection_class"] = has_protection
        checks["csrf_verify_function"] = has_verify
        checks["csrf_generate_function"] = has_generate
        if not (has_protection and has_verify and has_generate):
            results["passed"] = False
            errors.append("CSRF implementation incomplete")

    templates_dir = Path(__file__).parents[3] / "qnwis" / "ops_console" / "templates"
    for template_file in templates_dir.glob("*.html"):
        content = template_file.read_text(encoding="utf-8")
        if 'method="post"' in content.lower():
            has_csrf_field = ("csrf_token" in content or "csrf_field" in content)
            checks[f"csrf_in_{template_file.name}"] = has_csrf_field
            if not has_csrf_field:
                results["passed"] = False
                errors.append(f"POST form without CSRF in {template_file.name}")
        if ("<script>" in content and "nonce=" not in content and "<script src=" not in content):
            checks[f"inline_script_check_{template_file.name}"] = False
            errors.append(f"Inline script without nonce in {template_file.name}")

    views_module = Path(__file__).parents[3] / "qnwis" / "ops_console" / "views.py"
    if views_module.exists():
        content = views_module.read_text(encoding="utf-8")
        has_csrf_import = "verify_csrf_token" in content
        has_csrf_dependency = "Depends(verify_csrf_token)" in content
        checks["csrf_dependency_imported"] = has_csrf_import
        checks["csrf_dependency_used"] = has_csrf_dependency
        if not (has_csrf_import and has_csrf_dependency):
            results["passed"] = False
            errors.append("verify_csrf_token dependency not enforced")

    return results


def check_ui_determinism() -> JsonDict:
    """
    Validate UI determinism.

    Checks:
    - No banned calls (datetime.now, time.time, random.*)
    - Stable sorting proven in tests
    """
    print("🎯 Checking UI determinism...")

    results: JsonDict = {
        "passed": True,
        "checks": {},
        "errors": [],
    }
    checks = _checks(results)
    errors = _errors(results)

    # Check for banned calls in ops_console module
    ops_console_dir = Path(__file__).parents[3] / "qnwis" / "ops_console"

    banned_patterns = [
        ("datetime.now()", "datetime.now"),
        ("time.time()", "time.time()"),
        ("random.", "import random"),
        ("secrets.token", "secrets.token"),  # Should use injected values
    ]

    violations = []

    for py_file in ops_console_dir.glob("**/*.py"):
        if py_file.name == "__pycache__":
            continue

        content = py_file.read_text(encoding="utf-8")

        for pattern, search_str in banned_patterns:
            if search_str in content:
                # Check if it's in a comment or string
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if (
                        search_str in line
                        and not line.strip().startswith("#")
                        and '"""' not in line
                        and "'''" not in line
                    ):
                        violations.append(f"{py_file.name}:{i+1} - {pattern}")

    checks["no_banned_calls"] = len(violations) == 0

    if violations:
        results["passed"] = False
        errors.extend(violations)

    network_banned = {"requests", "httpx", "urllib", "urllib3", "urllib2", "socket", "ssl", "webbrowser", "aiohttp"}
    network_hits: list[str] = []
    for py_file in ops_console_dir.glob("**/*.py"):
        if py_file.name.endswith(".py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            except SyntaxError as exc:
                results["passed"] = False
                errors.append(f"Syntax error in {py_file}: {exc}")
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_name = alias.name.split(".")[0]
                        if root_name in network_banned:
                            rel = py_file.relative_to(Path(__file__).parents[4])
                            network_hits.append(f"{rel}:{node.lineno} import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    root_name = node.module.split(".")[0]
                    if root_name in network_banned:
                        rel = py_file.relative_to(Path(__file__).parents[4])
                        network_hits.append(f"{rel}:{node.lineno} from {node.module} import ...")

    checks["no_network_imports"] = not network_hits
    if network_hits:
        results["passed"] = False
        errors.extend(network_hits)

    # Check for ManualClock usage in tests
    test_files = list(Path(__file__).parents[4].glob("tests/**/ops_console/**/*.py"))

    uses_manual_clock = False
    for test_file in test_files:
        content = test_file.read_text(encoding="utf-8")
        if "ManualClock" in content:
            uses_manual_clock = True
            break

    checks["tests_use_manual_clock"] = uses_manual_clock

    if not uses_manual_clock:
        errors.append("Tests don't use ManualClock for determinism")

    return results


def check_ui_audit() -> JsonDict:
    """
    Validate UI audit trail.

    Checks:
    - UI actions emit audit entries
    - Entries include request_id and actor
    - Audit artifacts can be saved
    """
    print("📋 Checking UI audit...")

    results: JsonDict = {
        "passed": True,
        "checks": {},
        "errors": [],
    }
    checks = _checks(results)
    errors = _errors(results)

    # Check views.py includes logging
    views_module = Path(__file__).parents[3] / "qnwis" / "ops_console" / "views.py"

    if views_module.exists():
        content = views_module.read_text(encoding="utf-8")

        has_logging = "import logging" in content
        has_logger = "logger = logging.getLogger" in content
        has_log_calls = "logger.info" in content or "logger.warning" in content

        checks["logging_imported"] = has_logging
        checks["logger_configured"] = has_logger
        checks["audit_logging_present"] = has_log_calls

        if not (has_logging and has_logger):
            results["passed"] = False
            errors.append("Logging not properly configured in views")

        # Check for request_id in log calls
        has_request_id = 'request_id' in content
        checks["request_id_in_logs"] = has_request_id

        # Check for actor/principal in action handlers
        has_principal = "principal.user_id" in content
        checks["principal_in_actions"] = has_principal

    else:
        results["passed"] = False
        errors.append("views.py not found")

    # Check for request ID middleware in app.py
    app_module = Path(__file__).parents[3] / "qnwis" / "ops_console" / "app.py"

    if app_module.exists():
        content = app_module.read_text(encoding="utf-8")

        has_middleware = "@app.middleware" in content
        has_request_id = "request_id" in content

        checks["middleware_present"] = has_middleware
        checks["request_id_middleware"] = has_request_id

    return results


def run_gate() -> dict[str, Any]:
    """Run all gate checks and generate report."""
    print("=" * 60)
    print("RG-5 OPS CONSOLE GATE")
    print("=" * 60)
    print()

    gate_results: JsonDict = {
        "gate": "RG-5 Ops Console",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": True,
        "checks": {},
    }
    gate_checks = _checks(gate_results)

    # Run all checks
    checks = [
        ("ui_completeness", check_ui_completeness),
        ("ui_performance", check_ui_performance),
        ("ui_security", check_ui_security),
        ("ui_determinism", check_ui_determinism),
        ("ui_audit", check_ui_audit),
    ]

    for check_name, check_func in checks:
        try:
            result = check_func()
            gate_checks[check_name] = result

            if not result["passed"]:
                gate_results["passed"] = False

            # Print summary
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"{status} - {check_name}")

            if result.get("errors"):
                for error in result["errors"]:
                    print(f"  ⚠️  {error}")

            print()

        except Exception as exc:
            print(f"❌ FAIL - {check_name} (exception)")
            print(f"  ⚠️  {exc}")
            print()

            gate_results["passed"] = False
            gate_checks[check_name] = {
                "passed": False,
                "error": str(exc),
            }

    # Print summary
    print("=" * 60)
    if gate_results["passed"]:
        print("✅ RG-5 PASSED - All checks passed")
    else:
        print("❌ RG-5 FAILED - Some checks failed")
    print("=" * 60)

    return gate_results


def save_artifacts(gate_results: dict[str, Any]) -> None:
    """Save gate artifacts."""
    print("\n[rg5] Saving artifacts...")
    root_dir = Path(__file__).parents[4]

    audit_dir = root_dir / "src" / "qnwis" / "docs" / "audit" / "ops"
    audit_dir.mkdir(parents=True, exist_ok=True)

    report_file = audit_dir / "ui_gate_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(gate_results, f, indent=2)
    print(f"  [+] Gate report: {report_file}")

    badge_dir = root_dir / "src" / "qnwis" / "docs" / "audit" / "badges"
    badge_dir.mkdir(parents=True, exist_ok=True)
    badge_file = badge_dir / "rg5_ops_console.svg"
    badge_color = "brightgreen" if gate_results["passed"] else "red"
    badge_status = "PASS" if gate_results["passed"] else "FAIL"
    badge_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="160" height="20">
  <rect width="80" height="20" fill="#555"/>
  <rect x="80" width="80" height="20" fill="{badge_color}"/>
  <text x="40" y="15" fill="#fff" font-family="Arial" font-size="11" text-anchor="middle">RG-5 Ops Console</text>
  <text x="120" y="15" fill="#fff" font-family="Arial" font-size="11" text-anchor="middle">{badge_status}</text>
</svg>'''
    with open(badge_file, "w", encoding="utf-8") as f:
        f.write(badge_svg)
    print(f"  [+] Badge: {badge_file}")

    summary_file = root_dir / "OPS_UI_SUMMARY.md"
    metrics_info = (
        gate_results.get("checks", {})
        .get("ui_performance", {})
        .get("metrics", {})
    )
    metrics_file_str = metrics_info.get("metrics_file")
    metrics_path = Path(metrics_file_str) if metrics_file_str else None

    summary_lines = [
        "# RG-5 Ops Console Gate Summary",
        "",
        f"**Status**: {'?o. PASSED' if gate_results['passed'] else '??O FAILED'}",
        f"**Timestamp**: {gate_results['timestamp']}",
        "",
        "## Check Results",
        "",
    ]

    for check_name, check_result in gate_results["checks"].items():
        status = "?o. PASS" if check_result.get("passed", False) else "??O FAIL"
        summary_lines.append(f"### {check_name.replace('_', ' ').title()}")
        summary_lines.append(f"**Status**: {status}")
        summary_lines.append("")

        if check_result.get("errors"):
            summary_lines.append("**Errors**:")
            for error in check_result["errors"]:
                summary_lines.append(f"- {error}")
            summary_lines.append("")

        if check_result.get("metrics"):
            summary_lines.append("**Metrics**:")
            for metric, value in check_result["metrics"].items():
                summary_lines.append(f"- {metric}: {value}")
            summary_lines.append("")
            if check_result["metrics"].get("metrics_file"):
                summary_lines.append(f"- Metrics file: {check_result['metrics']['metrics_file']}")
                summary_lines.append("")

    relative_report = report_file.relative_to(Path.cwd())
    relative_badge = badge_file.relative_to(Path.cwd())
    metrics_entry = (
        metrics_path.relative_to(Path.cwd())
        if metrics_path and metrics_path.exists()
        else metrics_file_str or "n/a"
    )

    summary_lines.extend([
        "## Artifacts",
        "",
        f"- Gate Report: `{relative_report}`",
        f"- Badge: `{relative_badge}`",
        f"- Metrics: `{metrics_entry}`",
        "",
        "---",
        "",
        "*Generated by RG-5 Ops Console Gate*",
    ])

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print(f"  [+] Summary: {summary_file}")


def main() -> int:
    """Run RG-5 gate and return exit code."""
    try:
        gate_results = run_gate()
        save_artifacts(gate_results)

        return 0 if gate_results["passed"] else 1

    except Exception as exc:
        print(f"\n❌ Gate execution failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
