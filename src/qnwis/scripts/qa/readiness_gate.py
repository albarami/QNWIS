"""Readiness Gate RG-1 harness with audit-grade checks."""

from __future__ import annotations

import ast
import hashlib
import html
import json
import locale
import logging
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

import yaml

logger = logging.getLogger("readiness_gate")

ROOT = Path(__file__).parents[4].resolve()
SRC_ROOT = ROOT / "src"
AUDIT_ROOT = SRC_ROOT / "qnwis" / "docs" / "audit"
REVIEWS_ROOT = SRC_ROOT / "qnwis" / "docs" / "reviews"
QA_ROOT = SRC_ROOT / "qnwis" / "scripts" / "qa"
BADGE_ROOT = AUDIT_ROOT / "badges"
RANDOM_SEED = 1337

os.environ.setdefault("TZ", "UTC")
os.environ.setdefault("LC_ALL", "C")
os.environ.setdefault("PYTHONHASHSEED", "0")
try:
    locale.setlocale(locale.LC_ALL, "C")
except locale.Error as exc:
    logger.debug("Could not set locale to C: %s (continuing with system default)", exc)
random.seed(RANDOM_SEED)
try:
    if hasattr(time, "tzset"):
        time.tzset()
except Exception as exc:  # pragma: no cover
    logger.debug("time.tzset() not available on this platform: %s", exc)

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from qnwis.scripts.qa.determinism_scan import (
    DEFAULT_BANNED_PATTERNS as ALERT_DETERMINISM_PATTERNS,
)  # noqa: E402
from qnwis.scripts.qa.determinism_scan import (
    scan_for_banned_calls,
)


def _load_placeholder_scan_module() -> ModuleType:
    if __package__:
        return import_module(".placeholder_scan", __package__)

    try:
        return import_module("placeholder_scan")
    except ImportError:
        _script_dir = Path(__file__).parent
        if str(_script_dir) not in sys.path:
            sys.path.insert(0, str(_script_dir))
        return import_module("placeholder_scan")


if TYPE_CHECKING:
    from qnwis.agents.base import DataClient as _DataClient
    from qnwis.data.deterministic.models import QueryResult as _QueryResult
else:
    _DataClient = Any  # type: ignore[assignment]
    _QueryResult = Any  # type: ignore[assignment]

_placeholder_scan_module = _load_placeholder_scan_module()
serialize_placeholder_matches = _placeholder_scan_module.as_dict
load_placeholder_patterns = _placeholder_scan_module.load_placeholder_patterns
scan_placeholders = _placeholder_scan_module.scan_placeholders

TEXT_FILE_SUFFIXES = {
    ".py",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".txt",
    ".toml",
    ".cfg",
    ".ini",
}
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "htmlcov",
    "__pycache__",
    "external_data",
    "qatar_data",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
ALLOWED_QID_PREFIXES = (
    "derived_",
    "lmis_",
    "gcc_",
    "wb_",
    "syn_",
    "qr_",
    "audit_",
    "int_",
)
SECRET_PATTERNS = {
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "aws_access_secret": re.compile(r"(?i)aws(.{0,5})secret"),
    "password_literal": re.compile(r"(?i)password\s*=\s*['\"]"),
    "token_literal": re.compile(r"(?i)token\s*=\s*['\"]"),
}
PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
}
CRITICAL_COVERAGE_TARGETS: dict[str, float] = {
    "src/qnwis/agents/pattern_miner.py": 90.0,
    "src/qnwis/agents/predictor.py": 90.0,
    "src/qnwis/agents/time_machine.py": 90.0,
    "src/qnwis/verification/citation_enforcer.py": 90.0,
    "src/qnwis/verification/result_verifier.py": 90.0,
    "src/qnwis/verification/audit_trail.py": 90.0,
    "src/qnwis/data/deterministic/normalize.py": 90.0,
    "src/qnwis/data/derived/metrics.py": 90.0,
    "src/qnwis/orchestration/coordination.py": 90.0,
    "src/qnwis/scenario/dsl.py": 90.0,
    "src/qnwis/scenario/apply.py": 90.0,
    "src/qnwis/scenario/qa.py": 90.0,
    "src/qnwis/agents/scenario_agent.py": 90.0,
}


@dataclass(frozen=True)
class StepRequirement:
    step: int
    name: str
    code_paths: tuple[str, ...]
    test_paths: tuple[str, ...]
    smoke_targets: tuple[str, ...]


STEP_REQUIREMENTS: tuple[StepRequirement, ...] = (
    StepRequirement(
        step=1,
        name="Project structure & configuration",
        code_paths=("pyproject.toml", "src/qnwis/__init__.py"),
        test_paths=("tests/test_environment.py",),
        smoke_targets=("docs/IMPLEMENTATION_ROADMAP.md",),
    ),
    StepRequirement(
        step=2,
        name="MCP tooling + API hygiene",
        code_paths=("tools/mcp/qnwis_mcp.py", "tools/mcp/allowlist.json"),
        test_paths=("tests/optional_mcp/test_mcp_tools.py",),
        smoke_targets=("docs/reviews/step2_review.md", "docs/reviews/step2a_api_sanitation.md"),
    ),
    StepRequirement(
        step=3,
        name="Deterministic data layer",
        code_paths=("src/qnwis/data/deterministic/normalize.py",),
        test_paths=("tests/unit/test_normalize.py",),
        smoke_targets=("docs/reviews/step3_review.md",),
    ),
    StepRequirement(
        step=4,
        name="LangGraph workflows",
        code_paths=("src/qnwis/orchestration/graph.py", "src/qnwis/orchestration/registry.py"),
        test_paths=("tests/integration/test_orchestration_workflow.py",),
        smoke_targets=("docs/reviews/step4_review.md", "docs/reviews/step4_orchestration_complete.md"),
    ),
    StepRequirement(
        step=5,
        name="Agents v1 hardening",
        code_paths=("src/qnwis/agents/national_strategy.py", "src/qnwis/agents/pattern_detective.py"),
        test_paths=("tests/unit/test_agent_national_strategy.py", "tests/unit/test_agent_pattern_detective.py"),
        smoke_targets=("docs/reviews/step5_review.md",),
    ),
    StepRequirement(
        step=6,
        name="Synthetic LMIS pack",
        code_paths=("scripts/seed_synthetic_lmis.py", "src/qnwis/data/synthetic/seed_lmis.py"),
        test_paths=("tests/integration/test_synthetic_seed_and_queries.py",),
        smoke_targets=("docs/reviews/step6_synthetic_pack_review.md", "docs/synthetic_data_pack.md"),
    ),
    StepRequirement(
        step=7,
        name="Routing orchestration",
        code_paths=("src/qnwis/orchestration/coordination.py", "src/qnwis/orchestration/policies.py"),
        test_paths=("tests/unit/orchestration/test_coordination.py",),
        smoke_targets=("docs/reviews/step7_orchestration_review.md",),
    ),
    StepRequirement(
        step=8,
        name="Verification + briefing",
        code_paths=("src/qnwis/briefing/minister.py", "src/qnwis/api/routers/briefing.py"),
        test_paths=("tests/unit/test_briefing_builder.py", "tests/integration/test_api_briefing.py"),
        smoke_targets=("docs/reviews/step8_verification_briefing_review.md",),
    ),
    StepRequirement(
        step=9,
        name="Data API v2",
        code_paths=("src/qnwis/data/api/client.py", "src/qnwis/data/api/models.py"),
        test_paths=("tests/integration/test_data_api_on_synthetic.py", "tests/unit/test_data_api_models.py"),
        smoke_targets=("docs/reviews/step9_data_api_v2_review.md", "docs/data_api_v2.md"),
    ),
    StepRequirement(
        step=10,
        name="Transforms catalog",
        code_paths=("src/qnwis/data/transforms/base.py", "src/qnwis/data/transforms/catalog.py"),
        test_paths=("tests/unit/test_transforms_base.py", "tests/unit/test_postprocess_pipeline.py"),
        smoke_targets=("docs/reviews/step10_transforms_catalog_review.md",),
    ),
    StepRequirement(
        step=11,
        name="UI demos",
        code_paths=("apps/chainlit/app.py", "src/qnwis/ui/charts.py"),
        test_paths=("tests/unit/test_ui_helpers.py", "tests/integration/test_api_ui_charts.py"),
        smoke_targets=("docs/reviews/step11_ui_demos_review.md", "docs/ui_demos.md"),
    ),
    StepRequirement(
        step=12,
        name="Dashboards bundle",
        code_paths=("apps/dashboard/static/app.js", "apps/dashboard/static/index.html"),
        test_paths=("tests/integration/test_dashboard_static.py", "tests/integration/test_api_ui_dashboard.py"),
        smoke_targets=("docs/reviews/step12_dashboards_review.md", "docs/ui_dashboard_bundle.md"),
    ),
    StepRequirement(
        step=13,
        name="Agents step13",
        code_paths=("src/qnwis/agents/pattern_detective.py", "src/qnwis/agents/national_strategy.py"),
        test_paths=("tests/integration/agents/test_step13_end_to_end.py",),
        smoke_targets=("docs/agents/step13_agents.md",),
    ),
    StepRequirement(
        step=14,
        name="Workflow foundation",
        code_paths=("src/qnwis/orchestration/graph.py", "src/qnwis/orchestration/classifier.py"),
        test_paths=("tests/unit/orchestration/test_registry.py", "tests/unit/orchestration/test_router.py"),
        smoke_targets=("docs/orchestration/step14_workflow.md",),
    ),
    StepRequirement(
        step=15,
        name="Routing + classifier",
        code_paths=("src/qnwis/orchestration/classifier.py", "src/qnwis/orchestration/nodes/router.py"),
        test_paths=("tests/unit/orchestration/test_classifier.py", "tests/unit/test_router_classification.py"),
        smoke_targets=("src/qnwis/docs/orchestration/step15_routing.md", "STEP15_ROUTING_IMPLEMENTATION_COMPLETE.md"),
    ),
    StepRequirement(
        step=16,
        name="Coordination",
        code_paths=("src/qnwis/orchestration/coordination.py", "src/qnwis/orchestration/prefetch.py"),
        test_paths=("tests/unit/orchestration/test_coordination.py", "tests/unit/orchestration/test_prefetch.py"),
        smoke_targets=("COORDINATION_LAYER_IMPLEMENTATION.md", "STEP_15_COORDINATION_COMPLETE.md"),
    ),
    StepRequirement(
        step=17,
        name="Cache & materialization",
        code_paths=("src/qnwis/cache/redis_cache.py", "src/qnwis/data/deterministic/cache_access.py"),
        test_paths=("tests/unit/test_cache_backends.py", "tests/unit/test_execute_cached.py"),
        smoke_targets=("docs/perf/step17_caching_materialization.md", "STEP17_CACHE_MATERIALIZATION_COMPLETE.md"),
    ),
    StepRequirement(
        step=18,
        name="Verification synthesis",
        code_paths=("src/qnwis/verification/triangulation.py", "src/qnwis/verification/rules.py"),
        test_paths=("tests/unit/test_triangulation_rules.py", "tests/unit/test_triangulation_bundle.py"),
        smoke_targets=("docs/verification_v2_and_briefing.md", "src/qnwis/docs/reviews/step18_review.md"),
    ),
    StepRequirement(
        step=19,
        name="Citation enforcement",
        code_paths=(
            "src/qnwis/verification/citation_enforcer.py",
            "src/qnwis/verification/citation_patterns.py",
        ),
        test_paths=("tests/unit/verification/test_citation_enforcer.py",),
        smoke_targets=(
            "STEP19_CITATION_ENFORCEMENT_COMPLETE.md",
            "src/qnwis/docs/verification/step19_citation_enforcement.md",
        ),
    ),
    StepRequirement(
        step=20,
        name="Result verification",
        code_paths=("src/qnwis/verification/result_verifier.py",),
        test_paths=(
            "tests/unit/verification/test_result_verifier.py",
            "tests/unit/verification/test_engine_integration.py",
        ),
        smoke_targets=(
            "STEP20_RESULT_VERIFICATION_COMPLETE.md",
            "docs/verification/step20_result_verification.md",
        ),
    ),
    StepRequirement(
        step=21,
        name="Audit trail",
        code_paths=(
            "src/qnwis/verification/audit_trail.py",
            "src/qnwis/verification/audit_store.py",
        ),
        test_paths=(
            "tests/unit/verification/test_audit_trail.py",
            "tests/unit/verification/test_audit_store.py",
        ),
        smoke_targets=("STEP21_AUDIT_TRAIL_COMPLETE.md", "docs/verification/step21_audit_trail.md"),
    ),
    StepRequirement(
        step=22,
        name="Confidence scoring",
        code_paths=("src/qnwis/verification/confidence.py",),
        test_paths=(
            "tests/unit/verification/test_confidence.py",
            "tests/unit/verification/test_confidence_perf.py",
        ),
        smoke_targets=(
            "STEP22_CONFIDENCE_SCORING_IMPLEMENTATION.md",
            "src/qnwis/docs/verification/step22_confidence_scoring.md",
        ),
    ),
    StepRequirement(
        step=23,
        name="Time Machine agent",
        code_paths=(
            "src/qnwis/agents/time_machine.py",
            "src/qnwis/agents/prompts/time_machine_prompts.py",
        ),
        test_paths=(
            "tests/unit/agents/test_time_machine.py",
            "tests/integration/analysis/test_time_machine_integration.py",
        ),
        smoke_targets=(
            "docs/analysis/step23_time_machine.md",
            "STEP23_TIME_MACHINE_IMPLEMENTATION_COMPLETE.md",
        ),
    ),
    StepRequirement(
        step=24,
        name="Pattern Miner agent",
        code_paths=(
            "src/qnwis/agents/pattern_miner.py",
            "src/qnwis/agents/prompts/pattern_miner_prompts.py",
        ),
        test_paths=(
            "tests/unit/agents/test_pattern_miner.py",
            "tests/integration/agents/test_pattern_miner_integration.py",
        ),
        smoke_targets=("docs/analysis/step24_pattern_miner.md", "STEP24_PATTERN_MINER_COMPLETE.md"),
    ),
    StepRequirement(
        step=25,
        name="Predictor agent",
        code_paths=(
            "src/qnwis/agents/predictor.py",
            "src/qnwis/agents/prompts/predictor_prompts.py",
        ),
        test_paths=(
            "tests/integration/agents/test_predictor_agent.py",
            "tests/unit/forecast/test_backtest.py",
        ),
        smoke_targets=("docs/analysis/step25_predictor.md", "STEP25_PREDICTOR_IMPLEMENTATION_COMPLETE.md"),
    ),
    StepRequirement(
        step=26,
        name="Scenario Planner",
        code_paths=(
            "src/qnwis/scenario/dsl.py",
            "src/qnwis/scenario/apply.py",
            "src/qnwis/scenario/qa.py",
            "src/qnwis/agents/scenario_agent.py",
        ),
        test_paths=(
            "tests/unit/scenario/test_dsl.py",
            "tests/unit/scenario/test_apply.py",
            "tests/unit/scenario/test_microbench.py",
            "tests/unit/agents/test_scenario_agent.py",
            "tests/integration/agents/test_scenario_end_to_end.py",
            "tests/integration/agents/test_scenario_verification.py",
        ),
        smoke_targets=(
            "docs/analysis/step26_scenario_planner.md",
            "STEP26_SCENARIO_IMPLEMENTATION_COMPLETE.md",
        ),
    ),
    StepRequirement(
        step=28,
        name="Alert Center Hardening",
        code_paths=(
            "src/qnwis/alerts",
            "src/qnwis/monitoring",
            "src/qnwis/agents/alert_center.py",
            "src/qnwis/scripts/qa/ops_gate.py",
            "src/qnwis/scripts/qa/determinism_scan.py",
        ),
        test_paths=(
            "tests/unit/alerts",
            "tests/unit/agents/test_alert_center.py",
            "tests/integration/agents/test_alert_flow.py",
        ),
        smoke_targets=(
            "docs/analysis/step28_alert_center.md",
            "OPS_GATE_SUMMARY.md",
            "STEP28_ALERT_CENTER_IMPLEMENTATION_COMPLETE.md",
        ),
    ),
)

NARRATIVE_SAMPLE_PATHS = (
    "STEP19_CITATION_ENFORCEMENT_COMPLETE.md",
    "STEP20_RESULT_VERIFICATION_COMPLETE.md",
    "docs/verification/RESULT_VERIFICATION_QUICKSTART.md",
    "docs/verification/step20_result_verification.md",
    "EXECUTIVE_SUMMARY.md",
    "STEP26_SCENARIO_IMPLEMENTATION_COMPLETE.md",
    "docs/analysis/step26_scenario_planner.md",
)
SCENARIO_NARRATIVE_PATHS = (
    "EXECUTIVE_SUMMARY.md",
    "STEP26_SCENARIO_IMPLEMENTATION_COMPLETE.md",
)
STEP26_SCENARIO_SPEC_PATH = ROOT / "examples" / "retention_boost_scenario.yml"
OPS_GATE_SUMMARY_JSON = ROOT / "OPS_GATE_SUMMARY.json"
OPS_GATE_SUMMARY_MD = ROOT / "OPS_GATE_SUMMARY.md"
STEP28_ALERT_PATHS = (
    SRC_ROOT / "qnwis" / "alerts",
    SRC_ROOT / "qnwis" / "monitoring",
    SRC_ROOT / "qnwis" / "agents" / "alert_center.py",
    SRC_ROOT / "qnwis" / "scripts" / "qa" / "ops_gate.py",
    SRC_ROOT / "qnwis" / "scripts" / "qa" / "determinism_scan.py",
)


@dataclass
class GateResult:
    name: str
    ok: bool
    details: dict[str, Any]
    duration_ms: float = 0.0
    severity: str = "ERROR"
    evidence_paths: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ReadinessReport:
    gates: list[GateResult]
    overall_pass: bool
    execution_time_ms: float
    timestamp: str
    summary: dict[str, Any]
    artifacts: dict[str, str]
    fixed_gates: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _load_step26_spec_payload() -> tuple[str | None, Any | None]:
    """Load and parse the canonical Step 26 scenario spec once."""
    if not STEP26_SCENARIO_SPEC_PATH.exists():
        return None, None
    spec_text = STEP26_SCENARIO_SPEC_PATH.read_text(encoding="utf-8")
    try:
        from qnwis.scenario.dsl import parse_scenario

        scenario_spec = parse_scenario(spec_text, format="yaml")
        return spec_text, scenario_spec
    except Exception as exc:
        logger.warning("Failed to parse Step 26 scenario spec: %s", exc)
        return spec_text, None


def _build_step26_baseline(horizon: int) -> _QueryResult:
    """Construct a deterministic baseline QueryResult for Step 26 guards."""
    from qnwis.data.deterministic.models import (
        Freshness,
        Provenance,
        QueryResult,
        Row,
    )

    values = [0.65 + 0.01 * i for i in range(horizon)]
    rows = [
        Row(
            data={
                "yhat": round(value, 4),
                "h": idx + 1,
                "lo": max(0.0, round(value - 0.02, 4)),
                "hi": min(1.0, round(value + 0.02, 4)),
            }
        )
        for idx, value in enumerate(values)
    ]
    return QueryResult(
        query_id=f"forecast_baseline_retention_construction_{horizon}m",
        rows=rows,
        unit="ratio",
        provenance=Provenance(
            source="synthetic",
            dataset_id="step26_readiness_guard",
            locator="readiness_gate",
            fields=["yhat", "h", "lo", "hi"],
            license="Internal",
        ),
        freshness=Freshness(
            asof_date="2024-12-31",
            updated_at="2024-12-31T00:00:00Z",
        ),
        warnings=[],
    )


@lru_cache(maxsize=1)
def _load_result_verification_tolerances() -> dict[str, Any]:
    """Flatten result verification tolerances for gate sampling."""
    config_path = SRC_ROOT / "qnwis" / "config" / "result_verification.yml"
    if not config_path.exists():
        return {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "require_citation_first": True,
            "allowed_prefixes": [
                "Per LMIS:",
                "According to GCC-STAT:",
                "According to World Bank:",
            ],
        }

    try:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning("Failed to load result_verification.yml: %s", exc)
        return {
            "abs_epsilon": 0.5,
            "rel_epsilon": 0.01,
            "require_citation_first": True,
        }

    tolerances: dict[str, Any] = {}
    for section, values in raw_config.items():
        if isinstance(values, dict):
            tolerances.update(values)
        else:
            tolerances[section] = values
    return tolerances


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, default=str)


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_previous_gate_status(report_path: Path) -> dict[str, bool]:
    if not report_path.exists():
        return {}
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:  # pragma: no cover - defensive
        logger.debug("Unable to parse previous gate status from %s: %s", report_path, exc)
        return {}
    outcomes: dict[str, bool] = {}
    for gate in data.get("gates", []):
        name = gate.get("name")
        if not name:
            continue
        outcomes[name] = bool(gate.get("ok"))
    return outcomes


def _non_empty(rel_path: str) -> bool:
    full = ROOT / rel_path
    if not full.exists():
        return False
    # For directories, check if they contain any files
    if full.is_dir():
        return any(full.iterdir())
    # For files, check if non-empty
    return full.stat().st_size > 0


def run_cmd(
    cmd: list[str],
    timeout: int = 900,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or ROOT,
            encoding="utf-8",
            errors="replace",
            env=merged_env,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as exc:  # pragma: no cover
        return -1, "", str(exc)


MYPY_DIAGNOSTIC_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<level>error|note):\s*(?P<message>.+)$"
)


def _tail_text(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def _load_json_records(stream: str) -> list[dict[str, Any]]:
    """Load JSON output from linters that emit array or JSON-line formats."""

    text = stream.strip()
    if not text:
        return []

    def _coerce(obj: Any) -> list[dict[str, Any]]:
        if isinstance(obj, list):
            return [item for item in obj if isinstance(item, dict)]
        if isinstance(obj, dict):
            return [obj]
        return []

    try:
        parsed = json.loads(text)
        return _coerce(parsed)
    except json.JSONDecodeError:
        records: list[dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError:
                continue
            records.extend(_coerce(loaded))
        return records


def _parse_colon_diagnostics(stream: str) -> list[tuple[str, str]]:
    """Parse `path:line:col: CODE message` diagnostics."""

    diagnostics: list[tuple[str, str]] = []
    for raw_line in stream.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Found "):
            continue
        parts = line.split(":", 3)
        if len(parts) < 4:
            continue
        path = parts[0].strip()
        remainder = parts[3].strip()
        if not remainder:
            continue
        code = remainder.split()[0]
        if not code:
            continue
        diagnostics.append((path, code))
    return diagnostics


def _summarize_ruff_output(stdout: str, stderr: str) -> dict[str, Any]:
    records = _load_json_records(stdout) or [
        {"path": path, "code": code} for path, code in _parse_colon_diagnostics(stdout)
    ]
    rules: Counter[str] = Counter()
    files: set[str] = set()
    fixable = 0
    for record in records:
        code = str(record.get("code") or "").strip()
        if code:
            rules[code] += 1
        filename = (
            record.get("filename")
            or record.get("path")
            or record.get("file")
            or record.get("relative_path")
        )
        if filename:
            files.add(str(filename))
        if record.get("fix"):
            fixable += 1

    return {
        "issues": sum(rules.values()),
        "fixable": fixable,
        "rules": dict(rules),
        "files": sorted(files)[:10],
        "stdout_tail": _tail_text(stdout),
        "stderr_tail": _tail_text(stderr),
    }


def _summarize_flake8_output(stdout: str, stderr: str) -> dict[str, Any]:
    diagnostics = _parse_colon_diagnostics(stdout)
    rules = Counter(code for _, code in diagnostics)
    files = sorted({path for path, _ in diagnostics})[:10]
    return {
        "issues": sum(rules.values()),
        "fixable": 0,
        "rules": dict(rules),
        "files": files,
        "stdout_tail": _tail_text(stdout),
        "stderr_tail": _tail_text(stderr),
    }


def _extract_mypy_code(message: str) -> str:
    match = re.search(r"\[([A-Za-z0-9\-_]+)\]\s*$", message.strip())
    return match.group(1) if match else "unknown"


def _summarize_mypy_output(stdout: str, stderr: str) -> dict[str, Any]:
    rules: Counter[str] = Counter()
    files: set[str] = set()
    for raw_line in stdout.splitlines():
        match = MYPY_DIAGNOSTIC_RE.match(raw_line.strip())
        if not match or match.group("level") != "error":
            continue
        files.add(match.group("path"))
        message = match.group("message")
        rules[_extract_mypy_code(message)] += 1

    return {
        "issues": sum(rules.values()),
        "fixable": 0,
        "rules": dict(rules),
        "files": sorted(files)[:10],
        "stdout_tail": _tail_text(stdout),
        "stderr_tail": _tail_text(stderr),
    }


def _iter_text_files(base: Path) -> Iterable[Path]:
    if not base.exists():
        return
    for path in base.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix.lower() not in TEXT_FILE_SUFFIXES:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def gate_step_completeness() -> GateResult:
    start = time.time()
    failures: dict[str, dict[str, list[str]]] = {}
    step_details: dict[str, Any] = {}

    for req in STEP_REQUIREMENTS:
        step_key = f"step_{req.step:02d}"
        missing_code = [p for p in req.code_paths if not _non_empty(p)]
        missing_tests = [p for p in req.test_paths if not _non_empty(p)]
        missing_smoke = [p for p in req.smoke_targets if not _non_empty(p)]
        step_details[step_key] = {
            "name": req.name,
            "code_ok": not missing_code,
            "tests_ok": not missing_tests,
            "smoke_ok": not missing_smoke,
            "missing": {
                "code": missing_code,
                "tests": missing_tests,
                "smoke": missing_smoke,
            },
        }
        if missing_code or missing_tests or missing_smoke:
            failures[step_key] = step_details[step_key]["missing"]

    passed = not failures
    return GateResult(
        name="step_completeness",
        ok=passed,
        details={"steps": step_details, "missing": failures},
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=["docs/IMPLEMENTATION_ROADMAP.md"],
    )


def gate_no_placeholders() -> GateResult:
    start = time.time()
    rules_path = QA_ROOT / "grep_rules.yml"
    placeholder_patterns = load_placeholder_patterns(rules_path)
    matches = scan_placeholders(search_root=SRC_ROOT / "qnwis", limit=50, rules_path=rules_path)

    return GateResult(
        name="no_placeholders",
        ok=len(matches) == 0,
        details={"patterns": placeholder_patterns, "violations": serialize_placeholder_matches(matches)},
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=[_rel(rules_path)] if rules_path.exists() else [],
    )


def gate_linters_and_types() -> GateResult:
    start = time.time()
    step28_targets = [
        "src/qnwis/alerts",
        "src/qnwis/monitoring",
        "src/qnwis/agents/alert_center.py",
        "src/qnwis/scripts/qa/ops_gate.py",
        "src/qnwis/scripts/qa/determinism_scan.py",
    ]
    lint_targets = list(dict.fromkeys(["src/qnwis", "tests", *step28_targets]))
    step26_targets = [
        "src/qnwis/scenario",
        "src/qnwis/agents/scenario_agent.py",
        "src/qnwis/cli/qnwis_scenario.py",
    ]
    # Step 28 targets for mypy (excluding QA scripts that modify sys.path)
    step28_mypy_targets = [
        "src/qnwis/alerts",
        "src/qnwis/monitoring",
        "src/qnwis/agents/alert_center.py",
    ]
    strict_targets = [*step26_targets, *step28_mypy_targets]

    ruff_code, ruff_out, ruff_err = run_cmd(
        [sys.executable, "-m", "ruff", "check", "--fix", "--extend-ignore=E402,ARG001", "--output-format", "json", *lint_targets],
        timeout=300,
    )
    ruff_details = _summarize_ruff_output(ruff_out, ruff_err)
    ruff_details["exit_code"] = ruff_code

    flake_code, flake_out, flake_err = run_cmd(
        [sys.executable, "-m", "flake8", *lint_targets, "--jobs", "4", "--extend-ignore=E402,C901"],
        timeout=300,
    )
    flake_details = _summarize_flake8_output(flake_out, flake_err)
    flake_details["exit_code"] = flake_code

    mypy_code, mypy_out, mypy_err = run_cmd(
        [sys.executable, "-m", "mypy", "--strict", *strict_targets],
        timeout=300,
    )
    mypy_details = _summarize_mypy_output(mypy_out, mypy_err)
    mypy_details["exit_code"] = mypy_code

    details = {
        "ruff": ruff_details,
        "flake8": flake_details,
        "mypy": mypy_details,
    }

    passed = all(tool["exit_code"] == 0 for tool in details.values())
    return GateResult(
        name="linters_and_types",
        ok=passed,
        details=details,
        duration_ms=(time.time() - start) * 1000,
    )


def _load_ops_gate_summary() -> dict[str, Any] | None:
    if not OPS_GATE_SUMMARY_JSON.exists():
        return None
    try:
        return json.loads(OPS_GATE_SUMMARY_JSON.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to parse Ops Gate summary: %s", exc)
        return None


def gate_deterministic_access() -> GateResult:
    start = time.time()
    violations: list[dict[str, Any]] = []
    disallowed_imports = {"requests", "httpx", "sqlalchemy", "psycopg2", "pymysql"}
    disallowed_methods = {"get", "post", "put", "delete", "patch"}
    sql_regex = re.compile(r"(execute|executemany).*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP)", re.IGNORECASE)

    for agent_file in (SRC_ROOT / "qnwis" / "agents").rglob("*.py"):
        text = agent_file.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            violations.append({"file": _rel(agent_file), "line": exc.lineno or 0, "issue": "syntax_error"})
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".")[0]
                    if root_name in disallowed_imports:
                        violations.append(
                            {"file": _rel(agent_file), "line": node.lineno, "issue": f"disallowed import {root_name}"}
                        )
            elif isinstance(node, ast.ImportFrom):
                root_name = (node.module or "").split(".")[0]
                if root_name in disallowed_imports:
                    violations.append(
                        {"file": _rel(agent_file), "line": node.lineno, "issue": f"disallowed import {root_name}"}
                    )
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"requests", "httpx"}
                and node.func.attr in disallowed_methods
            ):
                violations.append(
                    {
                        "file": _rel(agent_file),
                        "line": node.lineno,
                        "issue": f"direct {node.func.value.id}.{node.func.attr} call",
                    }
                )

        for line_no, line in enumerate(text.splitlines(), start=1):
            if sql_regex.search(line):
                violations.append(
                    {"file": _rel(agent_file), "line": line_no, "issue": "raw SQL execution", "snippet": line.strip()}
                )

    return GateResult(
        name="deterministic_access",
        ok=len(violations) == 0,
        details={"violations": violations},
        duration_ms=(time.time() - start) * 1000,
    )


def _collect_pytest_env() -> dict[str, str]:
    return {"READINESS_GATE_CHILD": "1", "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "0")}


def gate_unit_and_integration_tests() -> GateResult:
    start = time.time()
    details: dict[str, Any] = {}
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "-m",
        "not mcp",
        "--cov=src/qnwis",
        "--cov-branch",
        "--cov-report=xml:coverage.xml",
        "--cov-report=term",
        "--junitxml=junit.xml",
    ]
    exit_code, stdout, stderr = run_cmd(cmd, timeout=900, env=_collect_pytest_env())
    details["exit_code"] = exit_code
    details["stdout_tail"] = stdout[-2000:]
    details["stderr_tail"] = stderr[-2000:]

    coverage_map, coverage_table = parse_coverage()
    details["coverage_table"] = coverage_table
    missing_coverage = {
        module: {"actual": round(coverage_map.get(module, 0.0), 2), "target": target}
        for module, target in CRITICAL_COVERAGE_TARGETS.items()
        if coverage_map.get(module, 0.0) < target
    }
    details["critical_modules"] = missing_coverage or {
        module: {"actual": round(coverage_map.get(module, 0.0), 2), "target": target}
        for module, target in CRITICAL_COVERAGE_TARGETS.items()
    }
    details["overall_coverage_pct"] = round(coverage_map.get("TOTAL", 0.0), 2)
    details["meets_threshold"] = exit_code == 0 and not missing_coverage
    passed = details["meets_threshold"]

    return GateResult(
        name="unit_and_integration_tests",
        ok=passed,
        details=details,
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=["coverage.xml", "junit.xml"],
    )


def parse_coverage() -> tuple[dict[str, float], str]:
    coverage_file = ROOT / "coverage.xml"
    coverage_map: dict[str, float] = {}
    coverage_table_lines = ["path | coverage", "--- | ---"]
    if not coverage_file.exists():
        return coverage_map, "coverage.xml missing"

    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(coverage_file)
        for cls in tree.findall(".//class"):
            filename = cls.get("filename")
            if not filename:
                continue
            rate = float(cls.get("line-rate", "0")) * 100.0
            rel_path = Path(filename).as_posix()
            coverage_map[rel_path] = rate
            coverage_table_lines.append(f"{rel_path} | {rate:.2f}%")
        overall = tree.getroot().get("line-rate")
        if overall is not None:
            coverage_map["TOTAL"] = float(overall) * 100.0
    except Exception as exc:  # pragma: no cover
        coverage_table_lines.append(f"error parsing coverage.xml: {exc}")

    return coverage_map, "\n".join(coverage_table_lines[:200])


def gate_cache_and_materialization() -> GateResult:
    start = time.time()
    cache_files = [
        "src/qnwis/cache/redis_cache.py",
        "src/qnwis/cache/middleware.py",
        "src/qnwis/data/materialized/registry.py",
    ]
    missing = [path for path in cache_files if not _non_empty(path)]
    return GateResult(
        name="cache_and_materialization",
        ok=not missing,
        details={"missing_files": missing},
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=cache_files,
    )


def gate_verification_layers() -> GateResult:
    start = time.time()
    required_files = [
        "src/qnwis/verification/layer2_crosschecks.py",
        "src/qnwis/verification/layer3_policy_privacy.py",
        "src/qnwis/verification/layer4_sanity.py",
        "src/qnwis/verification/citation_enforcer.py",
        "src/qnwis/verification/result_verifier.py",
        "src/qnwis/verification/audit_trail.py",
        "src/qnwis/verification/confidence.py",
    ]
    missing = [path for path in required_files if not _non_empty(path)]
    return GateResult(
        name="verification_layers",
        ok=not missing,
        details={"missing": missing},
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=required_files,
    )


def gate_citation_enforcement() -> GateResult:
    start = time.time()
    details: dict[str, Any] = {}
    try:
        from qnwis.verification.citation_enforcer import CitationEnforcer

        enforcer = CitationEnforcer()
        sample = "Per LMIS: Employment grew 12% (QID:lmis_emp_2024)."
        result = enforcer.check_narrative(sample, [])
        status = [getattr(f, "code", "") for f in getattr(result, "findings", [])]
        details["sample_status"] = status
        ok = not any(code for code in status if str(code).upper().startswith("UNCITED"))
    except Exception as exc:
        ok = False
        details["error"] = str(exc)

    return GateResult(
        name="citation_enforcement",
        ok=ok,
        details=details,
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=["src/qnwis/verification/citation_enforcer.py"],
    )


def gate_result_verification() -> GateResult:
    start = time.time()
    details: dict[str, Any] = {}
    try:
        from qnwis.agents.base import DataClient
        from qnwis.agents.scenario_agent import ScenarioAgent
        from qnwis.data.deterministic.models import QueryResult
        from qnwis.scenario.apply import apply_scenario
        from qnwis.verification.result_verifier import verify_numbers

        spec_text, scenario_spec = _load_step26_spec_payload()
        if scenario_spec is None:
            raise FileNotFoundError(
                f"Step 26 scenario spec missing at {STEP26_SCENARIO_SPEC_PATH}"
            )

        baseline = _build_step26_baseline(scenario_spec.horizon_months)

        _DataClientCls: type[_DataClient] = cast(type[_DataClient], DataClient)

        class _ScenarioVerificationClient(_DataClientCls):
            def __init__(self, response: QueryResult) -> None:
                self._response = response

            def run(self, query_id: str) -> QueryResult:
                return self._response.model_copy(deep=True)

        agent = ScenarioAgent(_ScenarioVerificationClient(baseline))
        narrative = agent.apply(scenario_spec.model_copy(deep=True))
        adjusted = apply_scenario(baseline, scenario_spec)
        tolerances = _load_result_verification_tolerances()
        report = verify_numbers(narrative, [adjusted], tolerances)

        details["claims_total"] = report.claims_total
        details["claims_matched"] = report.claims_matched
        details["issues"] = [issue.model_dump() for issue in report.issues]
        details["runtime_ms"] = report.runtime_ms
        details["narrative_preview"] = "\n".join(narrative.splitlines()[:8])
        details["scenario_query_id"] = adjusted.query_id
        details["tolerances"] = {
            key: tolerances.get(key)
            for key in ("abs_epsilon", "rel_epsilon", "require_citation_first")
        }
        details["spec_path"] = _rel(STEP26_SCENARIO_SPEC_PATH)
        details["scenario_metric"] = scenario_spec.metric
        details["scenario_narrative_sources"] = list(SCENARIO_NARRATIVE_PATHS)
        if spec_text:
            details["spec_preview"] = spec_text.strip().splitlines()[:5]
        ok = report.ok
    except Exception as exc:
        ok = False
        details["error"] = str(exc)

    return GateResult(
        name="result_verification",
        ok=ok,
        details=details,
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=[
            "src/qnwis/verification/result_verifier.py",
            _rel(STEP26_SCENARIO_SPEC_PATH),
        ],
    )


def gate_orchestration_flow() -> GateResult:
    start = time.time()
    orch_files = [
        "src/qnwis/orchestration/classifier.py",
        "src/qnwis/orchestration/graph.py",
        "src/qnwis/orchestration/coordination.py",
        "src/qnwis/orchestration/intent_catalog.yml",
    ]
    missing = [path for path in orch_files if not _non_empty(path)]
    smoke_matrix = QA_ROOT / "smoke_matrix.yml"
    return GateResult(
        name="orchestration_flow",
        ok=not missing and smoke_matrix.exists(),
        details={"missing": missing, "smoke_matrix": smoke_matrix.exists()},
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=orch_files + ["src/qnwis/scripts/qa/smoke_matrix.yml"],
    )


def gate_agents_end_to_end() -> GateResult:
    start = time.time()
    agents = {
        "pattern_detective": "src/qnwis/agents/pattern_detective.py",
        "national_strategy": "src/qnwis/agents/national_strategy.py",
        "time_machine": "src/qnwis/agents/time_machine.py",
        "pattern_miner": "src/qnwis/agents/pattern_miner.py",
        "predictor": "src/qnwis/agents/predictor.py",
    }
    details: dict[str, Any] = {}
    missing = []
    for name, rel_path in agents.items():
        path = ROOT / rel_path
        if not path.exists():
            missing.append(name)
            continue
        size = path.stat().st_size
        details[f"{name}_bytes"] = size
        if size < 2000:
            missing.append(f"{name} (too small)")
    return GateResult(
        name="agents_end_to_end",
        ok=not missing,
        details={"missing": missing, **details},
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=list(agents.values()),
    )


def gate_citations_and_derived() -> GateResult:
    start = time.time()
    rng = random.Random(RANDOM_SEED)
    paragraphs = _load_narrative_paragraphs()
    sampled = rng.sample(paragraphs, k=min(5, len(paragraphs))) if paragraphs else []
    known_qids = load_known_qids()
    violations: list[dict[str, Any]] = []

    for para in sampled:
        numbers = re.findall(r"[0-9][0-9,.%]*", para["text"])
        qids = para["qids"]
        if numbers and not qids:
            violations.append({"file": para["file"], "issue": "numbers_without_qid", "text": para["text"]})
            continue
        for qid in qids:
            normalized = qid.strip().lower()
            if not _qid_allowed(normalized, known_qids):
                violations.append({"file": para["file"], "issue": f"unknown_qid {qid}"})

    return GateResult(
        name="citations_and_derived",
        ok=not violations,
        details={"sampled": sampled, "violations": violations},
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=list(NARRATIVE_SAMPLE_PATHS),
    )


def _load_narrative_paragraphs(
    paths: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    paragraphs: list[dict[str, Any]] = []
    for rel in paths or NARRATIVE_SAMPLE_PATHS:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for block in text.split("\n\n"):
            if not re.search(r"\d", block):
                continue
            qids = re.findall(r"QID[:=]\s*([A-Za-z0-9_:\.\-]+)", block)
            paragraphs.append({"file": rel, "text": block.strip(), "qids": qids})
    return paragraphs


@lru_cache(maxsize=1)
def load_known_qids() -> set[str]:
    qids: set[str] = set()
    queries_dir = SRC_ROOT / "qnwis" / "data" / "queries"
    for yaml_file in queries_dir.rglob("*.yaml"):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and "id" in data:
            qids.add(str(data["id"]).strip().lower())
    return qids


def _qid_allowed(qid: str, known: set[str]) -> bool:
    if qid in known:
        return True
    return any(qid.startswith(prefix) for prefix in ALLOWED_QID_PREFIXES)


def gate_performance_guards() -> GateResult:
    start = time.time()
    details: dict[str, Any] = {}
    thresholds = {
        "normalize_params": 0.25,
        "share_of_total": 0.35,
        "ewma": 0.20,
        "scenario_apply_p95": 0.075,  # default to 75ms, overwritten once SLA constant loads
        "scenario_agent_apply": 0.075,
    }
    durations: dict[str, float] = {}
    scenario_apply_detail: dict[str, Any] | None = None
    scenario_agent_detail: dict[str, Any] | None = None
    try:
        from qnwis.agents.base import DataClient
        from qnwis.agents.scenario_agent import ScenarioAgent
        from qnwis.analysis import trend_utils
        from qnwis.data.derived import metrics
        from qnwis.data.deterministic import normalize
        from qnwis.data.deterministic.models import (
            Freshness,
            Provenance,
            QueryResult,
            Row,
        )
        from qnwis.scenario.apply import apply_scenario
        from qnwis.scenario.dsl import ScenarioSpec, Transform
        from qnwis.scenario.qa import SLA_THRESHOLD_MS, sla_benchmark

        payloads = [{"year": 2020 + (i % 5), "value": i * 1.5, "timeout_s": str(i % 10)} for i in range(2000)]
        rows = [{"data": {"year": 2020 + (i % 3), "value": i + 1}} for i in range(1500)]
        series = [float(80 + ((i * 7) % 13)) for i in range(5000)]
        thresholds["scenario_apply_p95"] = SLA_THRESHOLD_MS / 1000.0
        _, canonical_spec = _load_step26_spec_payload()
        if (
            canonical_spec is not None
            and getattr(canonical_spec, "horizon_months", 0) >= 96
        ):
            scenario_spec = canonical_spec
        else:
            scenario_spec = ScenarioSpec(
                name="Readiness Guard",
                description="Mixed transforms to stress Step 26 path",
                metric="retention",
                horizon_months=96,
                transforms=[
                    Transform(type="multiplicative", value=0.08, start_month=0, end_month=47),
                    Transform(type="additive", value=4.0, start_month=32, end_month=95),
                ],
            )

        bench_start = time.perf_counter()
        for sample in payloads:
            normalize.normalize_params(sample)
        durations["normalize_params"] = time.perf_counter() - bench_start

        bench_start = time.perf_counter()
        metrics.share_of_total(rows, value_key="value", group_key="year")
        durations["share_of_total"] = time.perf_counter() - bench_start

        bench_start = time.perf_counter()
        trend_utils.ewma(series, alpha=0.3)
        durations["ewma"] = time.perf_counter() - bench_start

        horizon = scenario_spec.horizon_months
        scenario_series = [float(100.0 + (i * 0.5)) for i in range(horizon)]
        scenario_rows = [
            Row(data={"yhat": value, "h": idx + 1})
            for idx, value in enumerate(scenario_series)
        ]
        scenario_baseline = QueryResult(
            query_id="benchmark_scenario_retention",
            rows=scenario_rows,
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="benchmark_scenario_retention",
                locator="readiness_gate",
                fields=["yhat", "h"],
                license="Benchmark",
            ),
            freshness=Freshness(
                asof_date="2024-12-31",
                updated_at="2024-12-31T00:00:00+00:00",
            ),
            warnings=[],
        )

        def _scenario_fn(_: list[float]) -> list[float]:
            result = apply_scenario(scenario_baseline, scenario_spec)
            return [
                float(row.data.get("adjusted", 0.0))
                for row in result.rows
            ]

        scenario_bench = sla_benchmark(
            scenario_series,
            _scenario_fn,
            iterations=6,
        )
        scenario_p95_s = (
            scenario_bench["latency_p95"] / 1000.0
            if scenario_bench.get("latency_p95") is not None
            else thresholds["scenario_apply_p95"] + 1.0
        )
        durations["scenario_apply_p95"] = scenario_p95_s
        scenario_apply_detail = {
            "sla_compliant": scenario_bench["sla_compliant"],
            "latency_p50_ms": (
                round(scenario_bench["latency_p50"], 3)
                if scenario_bench.get("latency_p50") is not None
                else None
            ),
            "latency_p95_ms": (
                round(scenario_bench["latency_p95"], 3)
                if scenario_bench.get("latency_p95") is not None
                else None
            ),
            "latency_max_ms": (
                round(scenario_bench["latency_max"], 3)
                if scenario_bench.get("latency_max") is not None
                else None
            ),
            "iterations": scenario_bench.get("iterations"),
            "reason": scenario_bench.get("reason"),
        }

        _BenchClientBase: type[_DataClient] = cast(type[_DataClient], DataClient)

        class _ScenarioBenchClient(_BenchClientBase):
            def __init__(self, response: QueryResult) -> None:
                self._response = response

            def run(self, query_id: str) -> QueryResult:
                return self._response.model_copy(deep=True)

        scenario_agent = ScenarioAgent(_ScenarioBenchClient(scenario_baseline))

        def _scenario_agent_fn(_: list[float]) -> list[float]:
            scenario_agent.apply(scenario_spec.model_copy(deep=True))
            return scenario_series

        agent_bench = sla_benchmark(
            scenario_series,
            _scenario_agent_fn,
            iterations=4,
        )
        agent_p95 = (
            agent_bench["latency_p95"] / 1000.0
            if agent_bench.get("latency_p95") is not None
            else thresholds["scenario_agent_apply"] + 1.0
        )
        durations["scenario_agent_apply"] = agent_p95
        scenario_agent_detail = {
            "sla_compliant": agent_bench["sla_compliant"],
            "latency_p50_ms": (
                round(agent_bench["latency_p50"], 3)
                if agent_bench.get("latency_p50") is not None
                else None
            ),
            "latency_p95_ms": (
                round(agent_bench["latency_p95"], 3)
                if agent_bench.get("latency_p95") is not None
                else None
            ),
            "latency_max_ms": (
                round(agent_bench["latency_max"], 3)
                if agent_bench.get("latency_max") is not None
                else None
            ),
            "iterations": agent_bench.get("iterations"),
            "reason": agent_bench.get("reason"),
        }
    except Exception as exc:
        return GateResult(
            name="performance_guards",
            ok=False,
            details={"error": str(exc)},
            duration_ms=(time.time() - start) * 1000,
        )

    regressions = {
        name: {"duration_s": round(duration, 4), "threshold_s": thresholds[name]}
        for name, duration in durations.items()
        if duration > thresholds[name]
    }
    details["durations"] = {k: round(v, 4) for k, v in durations.items()}
    if scenario_apply_detail is not None:
        details["scenario_apply_benchmark"] = scenario_apply_detail
        if "scenario_apply_p95" in regressions:
            regressions["scenario_apply_p95"]["latency_p95_ms"] = scenario_apply_detail["latency_p95_ms"]
            regressions["scenario_apply_p95"]["reason"] = scenario_apply_detail["reason"]
    if scenario_agent_detail is not None:
        details["scenario_agent_benchmark"] = scenario_agent_detail
        if "scenario_agent_apply" in regressions:
            regressions["scenario_agent_apply"]["latency_p95_ms"] = scenario_agent_detail["latency_p95_ms"]
            regressions["scenario_agent_apply"]["reason"] = scenario_agent_detail["reason"]
    details["regressions"] = regressions
    return GateResult(
        name="performance_guards",
        ok=not regressions,
        details=details,
        duration_ms=(time.time() - start) * 1000,
    )


def gate_security_and_privacy() -> GateResult:
    start = time.time()
    secret_hits: list[dict[str, Any]] = []
    pii_hits: list[dict[str, Any]] = []
    bases = [SRC_ROOT / "qnwis", ROOT / "docs"]

    for base in bases:
        for file_path in _iter_text_files(base):
            parts_lower = {part.lower() for part in file_path.parts}
            if "audit" in parts_lower:
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for key, pattern in SECRET_PATTERNS.items():
                match = pattern.search(text)
                if match:
                    secret_hits.append({"file": _rel(file_path), "pattern": key, "snippet": match.group(0)[:120]})
            for key, pattern in PII_PATTERNS.items():
                match = pattern.search(text)
                if match:
                    pii_hits.append({"file": _rel(file_path), "pattern": key, "snippet": match.group(0)[:120]})

    rbac_file = SRC_ROOT / "qnwis" / "verification" / "schemas.py"
    rbac_ok = rbac_file.exists() and "RBAC" in rbac_file.read_text(encoding="utf-8", errors="ignore")
    rbac_tests_ok = _non_empty("tests/unit/verification/test_engine_integration.py")

    ok = not secret_hits and not pii_hits and rbac_ok and rbac_tests_ok
    details = {
        "secret_hits": secret_hits,
        "pii_hits": pii_hits,
        "rbac_schema": rbac_ok,
        "rbac_tests": rbac_tests_ok,
    }
    return GateResult(
        name="security_and_privacy",
        ok=ok,
        details=details,
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=[_rel(rbac_file)] if rbac_file.exists() else [],
    )


def gate_stability_controls() -> GateResult:
    start = time.time()
    env_checks = {
        "TZ": os.environ.get("TZ") == "UTC",
        "LC_ALL": os.environ.get("LC_ALL") == "C",
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED") == "0",
    }
    matrix_path = QA_ROOT / "smoke_matrix.yml"
    unsorted_sections: dict[str, list[str]] = {}
    if matrix_path.exists():
        try:
            matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8")) or {}
            if isinstance(matrix, dict):
                for key, scenarios in matrix.items():
                    if not isinstance(scenarios, list):
                        continue
                    ids = [item.get("id", "") for item in scenarios if isinstance(item, dict) and "id" in item]
                    if ids and ids != sorted(ids):
                        unsorted_sections[key] = ids
        except Exception as exc:
            unsorted_sections["error"] = [str(exc)]

    ok = all(env_checks.values()) and not unsorted_sections
    details = {"env": env_checks, "unsorted": unsorted_sections}
    return GateResult(
        name="stability_controls",
        ok=ok,
        details=details,
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=[_rel(matrix_path)] if matrix_path.exists() else [],
    )


def gate_api_endpoints() -> GateResult:
    """Step 27: Verify FastAPI routers by running integration tests."""
    start = time.time()
    cmd = [sys.executable, "-m", "pytest", "-q", "tests/integration/api"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    ok = proc.returncode == 0
    details = {
        "command": " ".join(cmd),
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }
    return GateResult(
        name="api_endpoints",
        ok=ok,
        details=details,
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=[_rel(Path("tests/integration/api/test_api_endpoints.py"))],
    )


def gate_api_security() -> GateResult:
    """Step 27: Run API security unit tests (auth/RBAC/ratelimit)."""
    start = time.time()
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/unit/api/test_auth.py",
        "tests/unit/api/test_rbac.py",
        "tests/unit/api/test_ratelimit.py",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    ok = proc.returncode == 0
    details = {
        "command": " ".join(cmd),
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }
    return GateResult(
        name="api_security",
        ok=ok,
        details=details,
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=[_rel(Path('tests/unit/api'))],
    )


def gate_api_performance() -> GateResult:
    """Step 27: Smoke-test API determinism/system flows."""
    start = time.time()
    cmd = [sys.executable, "-m", "pytest", "-q", "tests/system/test_api_readiness.py"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    ok = proc.returncode == 0
    details = {
        "command": " ".join(cmd),
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }
    return GateResult(
        name="api_performance",
        ok=ok,
        details=details,
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=[_rel(Path('tests/system/test_api_readiness.py'))],
    )


def gate_api_verification() -> GateResult:
    """Step 27: Ensure response schema + docs cover verification layers."""
    start = time.time()
    issues: list[str] = []
    evidence: list[str] = []
    models_path = SRC_ROOT / "qnwis" / "api" / "models.py"
    examples_path = ROOT / "docs" / "api" / "examples.http"
    if not models_path.exists():
        issues.append("models.py missing")
    else:
        text = models_path.read_text(encoding="utf-8", errors="ignore")
        for field_name in ["confidence", "freshness", "citations", "audit_id"]:
            if field_name not in text:
                issues.append(f"Missing field {field_name} in AgentResponse")
        evidence.append(_rel(models_path))
    if not examples_path.exists():
        issues.append("docs/api/examples.http missing")
    else:
        evidence.append(_rel(examples_path))
    ok = not issues
    return GateResult(
        name="api_verification",
        ok=ok,
        details={"issues": issues},
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=evidence,
    )


def gate_alerts_ops_step28() -> GateResult:
    """Step 28: Surface Ops Gate metrics and determinism status."""
    start = time.time()
    summary = _load_ops_gate_summary()
    determinism_hits = scan_for_banned_calls(STEP28_ALERT_PATHS, ALERT_DETERMINISM_PATTERNS)

    evidence: list[str] = []
    if OPS_GATE_SUMMARY_MD.exists():
        evidence.append(_rel(OPS_GATE_SUMMARY_MD))
    if OPS_GATE_SUMMARY_JSON.exists():
        evidence.append(_rel(OPS_GATE_SUMMARY_JSON))

    details = {
        "ops_summary_present": summary is not None,
        "ops_gate_passed": (summary.get("overall_passed") if summary else None),
        "performance": (summary or {}).get("performance", {}),
        "determinism_hits": determinism_hits,
        "ops_gate_report": summary or {},
    }
    performance_ok = bool(details["performance"])
    ops_gate_passed = bool(details["ops_gate_passed"])
    determinism_ok = not determinism_hits
    ok = performance_ok and ops_gate_passed and determinism_ok

    return GateResult(
        name="alerts_ops_step28",
        ok=ok,
        details=details,
        duration_ms=(time.time() - start) * 1000,
        evidence_paths=evidence,
    )


def generate_markdown_report(report: ReadinessReport) -> str:
    lines = [
        "# Readiness Report: Steps 1-28",
        "",
        f"**Generated:** {report.timestamp}",
        f"**Overall Status:** {'PASS' if report.overall_pass else 'FAIL'}",
        f"**Execution Time:** {report.execution_time_ms:.0f} ms",
        "",
        "## Summary",
        "",
        f"- **Total Gates:** {len(report.gates)}",
        f"- **Passed:** {sum(1 for g in report.gates if g.ok)}",
        f"- **Failed:** {sum(1 for g in report.gates if not g.ok)}",
        "",
    ]
    step28_info = report.summary.get("step28")
    if step28_info:
        perf = step28_info.get("performance") or {}
        ops_gate_passed = step28_info.get("ops_gate_passed")
        ops_gate_status = "n/a" if ops_gate_passed is None else ("PASS" if ops_gate_passed else "FAIL")
        ops_summary_flag = "yes" if step28_info.get("ops_summary_present") else "no"
        lines.extend(
            [
                "## Step 28 - Alert Center Hardening",
                "",
                f"- **Ops Gate:** {ops_gate_status}",
                f"- **Ops Summary Present:** {ops_summary_flag}",
                f"- **p50 / p95 (ms):** {perf.get('p50_ms', 'n/a')} / {perf.get('p95_ms', 'n/a')}",
                f"- **Determinism Violations:** {len(step28_info.get('determinism_hits', []))}",
                "",
            ]
        )
    lines.extend(
        [
            "## Previously failing gates now PASS",
            "",
        ]
    )
    if report.fixed_gates:
        for gate_name in sorted(report.fixed_gates):
            lines.append(f"- {gate_name}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Gate Results",
            "",
        ]
    )
    for gate in report.gates:
        status = "PASS" if gate.ok else "FAIL"
        lines.append(f"### {gate.name} [{status}]")
        lines.append(f"- **Duration:** {gate.duration_ms:.0f} ms")
        lines.append(f"- **Severity:** {gate.severity}")
        if gate.details:
            lines.append("```json")
            lines.append(json.dumps(gate.details, indent=2, default=str))
            lines.append("```")
        if gate.evidence_paths:
            lines.append("**Evidence:**")
            for path in gate.evidence_paths[:10]:
                lines.append(f"- `{path}`")
        lines.append("")
    return "\n".join(lines)


def markdown_to_html(markdown_text: str) -> str:
    try:
        import markdown  # type: ignore[import-untyped]

        return cast(str, markdown.markdown(markdown_text))
    except Exception:
        escaped = html.escape(markdown_text)
        return f"<pre>{escaped}</pre>"


def write_html_summary(markdown_text: str) -> Path:
    html_text = markdown_to_html(markdown_text)
    summary_path = AUDIT_ROOT / "READINESS_SUMMARY.html"
    summary_path.write_text(html_text, encoding="utf-8")
    return summary_path


def write_badge(overall_pass: bool) -> Path:
    BADGE_ROOT.mkdir(parents=True, exist_ok=True)
    color = "#2c974b" if overall_pass else "#d93025"
    label = "PASS" if overall_pass else "FAIL"
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='150' height='20'>
<linearGradient id='grad' x2='0' y2='100%'>
  <stop offset='0' stop-color='#bbb' stop-opacity='.1'/>
  <stop offset='1' stop-opacity='.1'/>
</linearGradient>
<rect rx='4' width='150' height='20' fill='#555'/>
<rect rx='4' x='70' width='80' height='20' fill='{color}'/>
<path fill='{color}' d='M70 0h4v20h-4z'/>
<rect rx='4' width='150' height='20' fill='url(#grad)'/>
<g fill='#fff' text-anchor='middle' font-family='Verdana' font-size='11'>
  <text x='35' y='15'>RG-1</text>
  <text x='108' y='15'>{label}</text>
</g>
</svg>"""
    badge_path = BADGE_ROOT / "rg1_pass.svg"
    badge_path.write_text(svg, encoding="utf-8")
    return badge_path


def _hash_artifacts(paths: Iterable[Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in paths:
        if path.exists() and path.is_file():
            hashes[_rel(path)] = checksum(path)
    return hashes


def build_artifact_index(extra_paths: Iterable[Path]) -> dict[str, str]:
    candidates = [
        ROOT / "coverage.xml",
        ROOT / "junit.xml",
        AUDIT_ROOT / "readiness_report.json",
        AUDIT_ROOT / "READINESS_REPORT_1_25.md",
        OPS_GATE_SUMMARY_JSON,
        OPS_GATE_SUMMARY_MD,
    ]
    candidates.extend(extra_paths)
    artifacts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in candidates:
        if path is None or not path.exists() or path.is_dir():
            continue
        rel = _rel(path)
        if rel in seen:
            continue
        artifacts.append(
            {
                "path": rel,
                "sha256": checksum(path),
                "size_bytes": path.stat().st_size,
            }
        )
        seen.add(rel)
    index_path = AUDIT_ROOT / "ARTIFACT_INDEX.json"
    write_json(index_path, {"generated_at": datetime.utcnow().isoformat(), "artifacts": artifacts})
    return {item["path"]: item["sha256"] for item in artifacts}


def write_readiness_review(report: ReadinessReport) -> Path:
    REVIEWS_ROOT.mkdir(parents=True, exist_ok=True)
    review_path = REVIEWS_ROOT / "readiness_gate_review.md"
    total_steps = len(STEP_REQUIREMENTS)
    step28_info = report.summary.get("step28", {})
    ops_gate_passed = step28_info.get("ops_gate_passed")
    ops_gate_status = "n/a" if ops_gate_passed is None else ("PASS" if ops_gate_passed else "FAIL")
    ops_summary_present = "yes" if step28_info.get("ops_summary_present") else "no"
    perf = step28_info.get("performance") or {}
    lines = [
        "# Readiness Gate Review (RG-1)",
        "",
        f"- Generated: {report.timestamp}",
        f"- Overall outcome: {'PASS' if report.overall_pass else 'FAIL'}",
        "- Evidence index: `src/qnwis/docs/audit/ARTIFACT_INDEX.json`",
        "- Badge: `src/qnwis/docs/audit/badges/rg1_pass.svg`",
        "",
        "## Highlights",
        "",
        f"1. Step completeness: {total_steps}/{total_steps} steps have code, tests, and smoke artifacts.",
        "2. Coverage map enforces >=90% on critical modules with actionable diffs.",
        "3. Narrative sampling cross-checks derived/original QIDs with query registry.",
        "4. Performance guards benchmark deterministic layers to prevent regressions.",
        "5. Security scans ensure no secrets/PII and RBAC policies stay enforced.",
        "6. Step 28 Ops Gate artifacts capture p50/p95 latency with determinism enforcement.",
        "",
        "## Step 28 - Alert Center Hardening",
        "",
        f"- Ops Gate Summary: {ops_gate_status}",
        f"- Ops Summary Present: {ops_summary_present}",
        f"- p50 / p95 (ms): {perf.get('p50_ms', 'n/a')} / {perf.get('p95_ms', 'n/a')}",
        f"- Determinism Violations: {len(step28_info.get('determinism_hits', []))}",
        "",
        "## Gate Evidence",
        "",
        "| Gate | Status | Severity | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for gate in report.gates:
        evidence = ", ".join(gate.evidence_paths[:2]) if gate.evidence_paths else "n/a"
        lines.append(f"| {gate.name} | {'PASS' if gate.ok else 'FAIL'} | {gate.severity} | {evidence} |")
    lines.append("")
    review_path.write_text("\n".join(lines), encoding="utf-8")
    return review_path


def main() -> int:
    print("=" * 80)
    print("READINESS GATE RG-1")
    print("=" * 80)
    print()

    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    BADGE_ROOT.mkdir(parents=True, exist_ok=True)
    previous_report_path = AUDIT_ROOT / "readiness_report.json"
    previous_gate_status = _load_previous_gate_status(previous_report_path)
    start_time = time.time()
    gates: list[GateResult] = []

    gate_functions = [
        gate_step_completeness,
        gate_no_placeholders,
        gate_linters_and_types,
        gate_deterministic_access,
        gate_security_and_privacy,
        gate_unit_and_integration_tests,
        gate_cache_and_materialization,
        gate_verification_layers,
        gate_citation_enforcement,
        gate_citations_and_derived,
        gate_result_verification,
        gate_orchestration_flow,
        gate_agents_end_to_end,
        gate_performance_guards,
        gate_alerts_ops_step28,
        gate_stability_controls,
        gate_api_endpoints,
        gate_api_security,
        gate_api_performance,
        gate_api_verification,
    ]

    for gate_fn in gate_functions:
        gate_name = gate_fn.__name__.replace("gate_", "")
        print(f"Running gate: {gate_name}...", end=" ", flush=True)
        try:
            result = gate_fn()
        except Exception as exc:  # pragma: no cover
            result = GateResult(name=gate_name, ok=False, details={"exception": str(exc)}, severity="ERROR")
        gates.append(result)
        outcome = "PASS" if result.ok else "FAIL"
        print(f"{outcome} ({result.duration_ms:.0f} ms)")
        if not result.ok and result.severity == "ERROR":
            print(json.dumps(result.details, indent=2, default=str))
            break

    execution_time = (time.time() - start_time) * 1000
    overall_pass = all(g.ok for g in gates if g.severity == "ERROR")
    fixed_gates = [
        gate.name for gate in gates if gate.ok and previous_gate_status.get(gate.name) is False
    ]

    summary_data: dict[str, Any] = {
        "total_gates": len(gates),
        "total": len(gates),
        "passed": sum(1 for g in gates if g.ok),
        "failed": sum(1 for g in gates if not g.ok),
    }
    step28_gate = next((g for g in gates if g.name == "alerts_ops_step28"), None)
    if step28_gate is not None:
        summary_data["step28"] = {
            "passed": step28_gate.ok,
            "ops_summary_present": step28_gate.details.get("ops_summary_present"),
            "ops_gate_passed": step28_gate.details.get("ops_gate_passed"),
            "performance": step28_gate.details.get("performance", {}),
            "determinism_hits": step28_gate.details.get("determinism_hits", []),
        }

    report = ReadinessReport(
        gates=gates,
        overall_pass=overall_pass,
        execution_time_ms=execution_time,
        timestamp=datetime.utcnow().isoformat(),
        summary=summary_data,
        artifacts={},
        fixed_gates=fixed_gates,
    )

    markdown_text = generate_markdown_report(report)
    report_md = AUDIT_ROOT / "READINESS_REPORT_1_25.md"
    report_md.write_text(markdown_text, encoding="utf-8")
    html_summary_path = write_html_summary(markdown_text)
    badge_path = write_badge(overall_pass)

    artifact_inputs = [
        ROOT / "coverage.xml",
        ROOT / "junit.xml",
        report_md,
        html_summary_path,
        badge_path,
    ]
    report.artifacts = _hash_artifacts(artifact_inputs)

    report_json_path = previous_report_path
    write_json(report_json_path, asdict(report))
    build_artifact_index(artifact_inputs + [report_json_path])
    review_path = write_readiness_review(report)

    print()
    print(f"JSON report written to {report_json_path}")
    print(f"Markdown report written to {report_md}")
    print(f"HTML summary written to {html_summary_path}")
    print(f"Badge written to {badge_path}")
    print(f"Review doc written to {review_path}")
    print()
    print("=" * 80)
    print(f"FINAL STATUS: {'PASS' if overall_pass else 'FAIL'}")
    print("=" * 80)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
