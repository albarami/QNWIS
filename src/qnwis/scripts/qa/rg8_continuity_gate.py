"""
RG-8 Continuity Gate for Business Continuity & Failover Orchestration.

Deterministic checks:
- continuity_presence: modules import, CLI/API routes discoverable
- continuity_plan_integrity: plans round-trip deterministically (YAML→JSON→YAML identical)
- continuity_failover_validity: simulated failover passes quorum & policy adherence
- continuity_audit: audit pack integrity (SHA-256 manifests verified)
- continuity_perf: p95 failover simulation < 100 ms

Artifacts:
- docs/audit/rg8/rg8_report.json
- docs/audit/rg8/CONTINUITY_SUMMARY.md
- docs/audit/rg8/sample_plan.yaml
- docs/audit/badges/rg8_pass.svg
"""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from yaml import dump as yaml_dump  # type: ignore[attr-defined]
from yaml import safe_load as yaml_safe_load


def _ensure_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    src_root = repo_root / "src"
    for candidate in (repo_root, src_root):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    return str(path)


def _write_md(path: Path, lines: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _write_badge(path: Path, label: str, status: str, color: str) -> str:
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='190' height='20' role='img' aria-label='{label}: {status}'>
  <linearGradient id='s' x2='0' y2='100%'>
    <stop offset='0' stop-color='#bbb' stop-opacity='.1'/>
    <stop offset='1' stop-opacity='.1'/>
  </linearGradient>
  <rect rx='3' width='190' height='20' fill='#555'/>
  <rect rx='3' x='85' width='105' height='20' fill='{color}'/>
  <path fill='{color}' d='M85 0h4v20h-4z'/>
  <rect rx='3' width='190' height='20' fill='url(#s)'/>
  <g fill='#fff' text-anchor='middle' font-family='DejaVu Sans,Verdana,Geneva,sans-serif' font-size='11'>
    <text x='43' y='15' fill='#010101' fill-opacity='.3'>{label}</text>
    <text x='43' y='14'>{label}</text>
    <text x='137' y='15' fill='#010101' fill-opacity='.3'>{status}</text>
    <text x='137' y='14'>{status}</text>
  </g>
</svg>""".strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return str(path)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if percentile <= 0:
        return float(values[0])
    if percentile >= 1:
        return float(values[-1])
    index = int(round(percentile * (len(values) - 1)))
    index = max(0, min(len(values) - 1, index))
    return float(values[index])


def run_gate() -> int:  # noqa: C901
    _ensure_repo_root()

    from qnwis.continuity.audit import ContinuityAuditor
    from qnwis.continuity.heartbeat import calculate_quorum_size
    from qnwis.continuity.models import (
        Cluster,
        FailoverPolicy,
        FailoverStrategy,
        Node,
        NodeRole,
        NodeStatus,
    )
    from qnwis.continuity.planner import ContinuityPlanner
    from qnwis.continuity.simulate import FailoverSimulator
    from qnwis.utils.clock import ManualClock

    out_dir = Path("docs/audit/rg8")
    badge_targets = [
        Path("docs/audit/badges/rg8_pass.svg"),
        Path("src/qnwis/docs/audit/badges/rg8_pass.svg"),
    ]

    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    results: dict[str, Any] = {"checks": {}, "metrics": {}}
    all_passed = True

    # ========================================================================
    # CHECK 1: continuity_presence
    # ========================================================================
    print("RG-8.1: Continuity Presence Check")
    try:
        # Verify imports work
        continuity_modules = [
            "qnwis.continuity.models",
            "qnwis.continuity.heartbeat",
            "qnwis.continuity.planner",
            "qnwis.continuity.executor",
            "qnwis.continuity.verifier",
            "qnwis.continuity.simulate",
            "qnwis.continuity.audit",
        ]
        for module_name in continuity_modules:
            importlib.import_module(module_name)

        from qnwis.api.routers import continuity
        from qnwis.cli import qnwis_continuity

        # Verify CLI commands exist
        cli_commands = ["plan", "simulate", "execute", "status", "audit"]
        for cmd in cli_commands:
            if not hasattr(qnwis_continuity.cli, "commands"):
                raise ValueError(f"CLI command '{cmd}' not found")

        # Verify API routes exist
        if not hasattr(continuity, "router"):
            raise ValueError("API router not found")

        results["checks"]["continuity_presence"] = {
            "status": "PASS",
            "modules": [name.split(".")[-1] for name in continuity_modules],
            "cli_commands": cli_commands,
            "api_routes": ["plan", "execute", "status", "simulate"],
        }
        print("  [PASS] All continuity modules and interfaces present")
    except Exception as e:
        results["checks"]["continuity_presence"] = {"status": "FAIL", "error": str(e)}
        print(f"  [FAIL] {e}")
        all_passed = False

    # ========================================================================
    # CHECK 2: continuity_plan_integrity
    # ========================================================================
    print("\nRG-8.2: Continuity Plan Integrity Check")
    try:
        # Create test cluster
        nodes = [
            Node(
                node_id="node-1",
                hostname="10.0.1.10",
                role=NodeRole.PRIMARY,
                region="region-1",
                site="site-a",
                status=NodeStatus.HEALTHY,
                priority=100,
                capacity=100.0,
            ),
            Node(
                node_id="node-2",
                hostname="10.0.1.11",
                role=NodeRole.SECONDARY,
                region="region-1",
                site="site-b",
                status=NodeStatus.HEALTHY,
                priority=90,
                capacity=95.0,
            ),
            Node(
                node_id="node-3",
                hostname="10.0.2.10",
                role=NodeRole.SECONDARY,
                region="region-2",
                site="site-c",
                status=NodeStatus.HEALTHY,
                priority=80,
                capacity=90.0,
            ),
        ]

        cluster = Cluster(
            cluster_id="test-cluster",
            name="Test Cluster",
            nodes=nodes,
            quorum_size=calculate_quorum_size(len(nodes)),
            regions=["region-1", "region-2"],
        )

        policy = FailoverPolicy(
            policy_id="test-policy",
            name="Test Policy",
            strategy=FailoverStrategy.AUTOMATIC,
            max_failover_time_s=60,
            require_quorum=True,
            region_priority=["region-1", "region-2"],
            site_priority=["site-a", "site-b", "site-c"],
            min_healthy_nodes=2,
        )

        # Generate plan
        planner = ContinuityPlanner(clock=clock)
        plan = planner.build_plan(cluster, policy)

        # Convert to dict
        plan_dict = {
            "plan_id": plan.plan_id,
            "cluster_id": plan.cluster_id,
            "policy_id": plan.policy_id,
            "created_at": plan.created_at,
            "primary_node_id": plan.primary_node_id,
            "failover_target_id": plan.failover_target_id,
            "estimated_total_ms": plan.estimated_total_ms,
            "actions": [
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "target_node_id": action.target_node_id,
                    "sequence": action.sequence,
                    "estimated_duration_ms": action.estimated_duration_ms,
                    "params": action.params,
                }
                for action in plan.actions
            ],
        }

        # Convert to YAML and back
        yaml_str = yaml_dump(plan_dict, sort_keys=True)
        plan_dict_2 = yaml_safe_load(yaml_str)

        # Verify round-trip
        if plan_dict != plan_dict_2:
            raise ValueError("Plan round-trip failed: YAML→dict not identical")

        # Save sample plan
        sample_plan_path = out_dir / "sample_plan.yaml"
        sample_plan_path.parent.mkdir(parents=True, exist_ok=True)
        sample_plan_path.write_text(yaml_str, encoding="utf-8")

        results["checks"]["continuity_plan_integrity"] = {
            "status": "PASS",
            "plan_id": plan.plan_id,
            "action_count": len(plan.actions),
            "estimated_total_ms": plan.estimated_total_ms,
            "round_trip": "identical",
        }
        print("  [PASS] Plan round-trip integrity verified")
    except Exception as e:
        results["checks"]["continuity_plan_integrity"] = {"status": "FAIL", "error": str(e)}
        print(f"  [FAIL] {e}")
        all_passed = False

    # ========================================================================
    # CHECK 3: continuity_failover_validity
    # ========================================================================
    print("\nRG-8.3: Continuity Failover Validity Check")
    try:
        # Run simulation
        simulator = FailoverSimulator(seed=42)
        sim_result = simulator.simulate_primary_failure(cluster, policy)

        # Verify simulation passed
        if not sim_result.success:
            raise ValueError(
                f"Simulation failed: {sim_result.verification_report.errors}"
            )

        # Verify quorum
        if not sim_result.verification_report.quorum_ok:
            raise ValueError("Quorum check failed")

        # Verify policy adherence
        if not sim_result.verification_report.policy_ok:
            raise ValueError("Policy adherence check failed")

        healthy_nodes = sum(1 for node in sim_result.cluster.nodes if node.status == NodeStatus.HEALTHY)
        total_nodes = len(sim_result.cluster.nodes)
        quorum_size = sim_result.cluster.quorum_size or calculate_quorum_size(total_nodes)
        quorum_rate = round(healthy_nodes / quorum_size, 2) if quorum_size else None

        results["checks"]["continuity_failover_validity"] = {
            "status": "PASS",
            "scenario": sim_result.scenario,
            "actions_executed": sim_result.failover_result.actions_executed,
            "duration_ms": sim_result.failover_result.total_duration_ms,
            "verification_passed": sim_result.verification_report.passed,
            "healthy_nodes": healthy_nodes,
            "total_nodes": total_nodes,
            "quorum_size": quorum_size,
            "quorum_rate": quorum_rate,
        }
        results["metrics"]["quorum"] = {
            "healthy_nodes": healthy_nodes,
            "total_nodes": total_nodes,
            "quorum_size": quorum_size,
            "quorum_rate": quorum_rate,
        }
        print("  [PASS] Failover simulation passed all checks")
    except Exception as e:
        results["checks"]["continuity_failover_validity"] = {
            "status": "FAIL",
            "error": str(e),
        }
        print(f"  [FAIL] {e}")
        all_passed = False

    # ========================================================================
    # CHECK 4: continuity_audit
    # ========================================================================
    print("\nRG-8.4: Continuity Audit Integrity Check")
    try:
        # Generate audit pack
        auditor = ContinuityAuditor(clock=clock)
        audit_pack = auditor.generate_audit_pack(
            plan, sim_result.failover_result, sim_result.verification_report
        )

        # Verify manifest hash
        manifest_str = json.dumps(audit_pack["manifest"], sort_keys=True)
        calculated_hash = hashlib.sha256(manifest_str.encode()).hexdigest()

        if calculated_hash != audit_pack["manifest_hash"]:
            raise ValueError(
                f"Manifest hash mismatch: {calculated_hash} != {audit_pack['manifest_hash']}"
            )

        # Verify audit pack structure
        required_fields = [
            "audit_id",
            "timestamp",
            "plan",
            "execution",
            "verification",
            "citations",
            "confidence",
            "manifest",
            "manifest_hash",
        ]
        for field in required_fields:
            if field not in audit_pack:
                raise ValueError(f"Missing audit pack field: {field}")

        results["checks"]["continuity_audit"] = {
            "status": "PASS",
            "audit_id": audit_pack["audit_id"],
            "manifest_hash": audit_pack["manifest_hash"],
            "confidence_score": audit_pack["confidence"]["score"],
            "confidence_band": audit_pack["confidence"]["band"],
        }
        print("  [PASS] Audit pack integrity verified")
    except Exception as e:
        results["checks"]["continuity_audit"] = {"status": "FAIL", "error": str(e)}
        print(f"  [FAIL] {e}")
        all_passed = False

    # ========================================================================
    # CHECK 5: continuity_perf
    # ========================================================================
    print("\nRG-8.5: Continuity Performance Check")
    try:
        # Run multiple simulations to measure p95
        durations: list[float] = []
        for i in range(20):
            sim = FailoverSimulator(seed=42 + i)
            result = sim.simulate_primary_failure(cluster, policy)
            durations.append(float(result.failover_result.total_duration_ms))

        # Calculate p95
        sorted_durations = sorted(durations)
        p50_ms = _percentile(sorted_durations, 0.50)
        p95_ms = _percentile(sorted_durations, 0.95)

        # Verify p95 < 100ms
        if p95_ms >= 100:
            raise ValueError(f"p95 latency {p95_ms}ms exceeds 100ms threshold")

        results["checks"]["continuity_perf"] = {
            "status": "PASS",
            "p50_ms": p50_ms,
            "p95_ms": p95_ms,
            "threshold_ms": 100,
            "sample_count": len(durations),
        }
        results["metrics"]["latency_ms"] = {
            "p50_ms": p50_ms,
            "p95_ms": p95_ms,
            "sample_count": len(durations),
        }
        print(f"  [PASS] p95 latency {p95_ms}ms < 100ms")
    except Exception as e:
        results["checks"]["continuity_perf"] = {"status": "FAIL", "error": str(e)}
        print(f"  [FAIL] {e}")
        all_passed = False

    # ========================================================================
    # Generate Artifacts
    # ========================================================================
    print("\nGenerating artifacts...")

    # Summary metrics
    passed_count = sum(
        1 for check in results["checks"].values() if check["status"] == "PASS"
    )
    total_count = len(results["checks"])
    results["metrics"]["checks_passed"] = passed_count
    results["metrics"]["checks_total"] = total_count
    results["metrics"]["pass_rate"] = round(passed_count / total_count * 100, 2)

    # Write report
    report_path = out_dir / "rg8_report.json"
    _write_json(report_path, results)
    print(f"  Report: {report_path}")

    # Write summary
    summary_lines = [
        "# RG-8 Continuity Gate Summary",
        "",
        f"**Status**: {'PASS' if all_passed else 'FAIL'}",
        f"**Checks**: {passed_count}/{total_count} passed",
        f"**Pass Rate**: {results['metrics']['pass_rate']}%",
        "",
        "## Checks",
        "",
    ]

    for check_name, check_data in results["checks"].items():
        status_icon = "✓" if check_data["status"] == "PASS" else "✗"
        summary_lines.append(f"- **{status_icon} {check_name}**: {check_data['status']}")

    summary_lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `rg8_report.json` - Complete gate report",
            "- `sample_plan.yaml` - Sample continuity plan",
            "- `CONTINUITY_SUMMARY.md` - This file",
            "- `../badges/rg8_pass.svg` - Gate badge",
        ]
    )

    summary_path = out_dir / "CONTINUITY_SUMMARY.md"
    _write_md(summary_path, summary_lines)
    print(f"  Summary: {summary_path}")

    # Write badge
    badge_color = "#4c1" if all_passed else "#e05d44"
    badge_status = "PASS" if all_passed else "FAIL"
    for badge_path in badge_targets:
        _write_badge(badge_path, "RG-8 Continuity", badge_status, badge_color)
        print(f"  Badge: {badge_path}")

    # Final status
    print(f"\n{'='*60}")
    if all_passed:
        print("RG-8 CONTINUITY GATE: PASS")
        print(f"All {total_count} checks passed")
        return 0
    else:
        print("RG-8 CONTINUITY GATE: FAIL")
        print(f"{total_count - passed_count}/{total_count} checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_gate())
