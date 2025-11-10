"""
System tests for Readiness Gate.

Tests that assert gates work correctly with coverage, determinism,
citations, and audit requirements.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2].resolve()
READINESS_GATE = ROOT / "src" / "qnwis" / "scripts" / "qa" / "readiness_gate.py"
AUDIT_ROOT = ROOT / "src" / "qnwis" / "docs" / "audit"

if os.environ.get("READINESS_GATE_CHILD") == "1":
    pytest.skip("Skip readiness gate system tests during nested RG-1 execution", allow_module_level=True)


@pytest.fixture(scope="session")
def run_gate():
    """Run readiness gate once per test session and cache the result."""

    cache: dict[str, subprocess.CompletedProcess[str]] = {}

    def _run():
        if "result" not in cache:
            env = os.environ.copy()
            env.pop("READINESS_GATE_CHILD", None)
            result = subprocess.run(
                [sys.executable, str(READINESS_GATE)],
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=1800,
                env=env,
            )
            if result.returncode != 0:
                pytest.fail(
                    f"Readiness gate failed with exit code {result.returncode}\n"
                    f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )
            cache["result"] = result
        return cache["result"]

    return _run


@pytest.fixture(scope="session")
def readiness_report(run_gate):
    """Return parsed readiness report JSON."""
    run_gate()
    report_path = AUDIT_ROOT / "readiness_report.json"
    assert report_path.exists(), "readiness_report.json not generated"
    with report_path.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def artifact_index(run_gate):
    """Return parsed artifact index."""
    run_gate()
    index_path = AUDIT_ROOT / "ARTIFACT_INDEX.json"
    assert index_path.exists(), "ARTIFACT_INDEX.json missing"
    with index_path.open(encoding="utf-8") as handle:
        return json.load(handle)


class TestReadinessGateExecution:
    """Test gate execution mechanics."""

    def test_gate_script_exists(self):
        """Readiness gate script must exist."""
        assert READINESS_GATE.exists()
        assert READINESS_GATE.is_file()

    def test_gate_is_executable(self):
        """Gate script must be valid Python."""
        # Try to import/parse
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(READINESS_GATE)],
            capture_output=True,
        )
        assert result.returncode == 0, f"Gate script has syntax errors: {result.stderr}"

    def test_gate_produces_json_report(self, readiness_report):
        """Gate must produce machine-readable JSON report."""
        assert "gates" in readiness_report
        assert "overall_pass" in readiness_report
        assert "execution_time_ms" in readiness_report
        assert "timestamp" in readiness_report
        assert isinstance(readiness_report["gates"], list)

    def test_gate_produces_markdown_report(self, run_gate):
        """Gate must produce human-readable Markdown report."""
        run_gate()
        md_report = AUDIT_ROOT / "READINESS_REPORT_1_25.md"
        assert md_report.exists(), "Markdown report not generated"

        content = md_report.read_text()
        assert "Readiness Report" in content
        assert "Gate Results" in content

    def test_html_summary_and_badge_generated(self, run_gate):
        """HTML summary and badge should be emitted."""
        run_gate()
        summary = AUDIT_ROOT / "READINESS_SUMMARY.html"
        badge = AUDIT_ROOT / "badges" / "rg1_pass.svg"
        assert summary.exists()
        summary_text = summary.read_text(encoding="utf-8")
        assert "<html" in summary_text.lower() or "<pre>" in summary_text.lower()
        assert badge.exists()

    def test_artifact_index_hashes_core_files(self, artifact_index):
        """Artifact index must include coverage, junit, markdown, and summary."""
        artifacts = {item["path"]: item for item in artifact_index["artifacts"]}
        expected = {
            "coverage.xml",
            "junit.xml",
            "src/qnwis/docs/audit/READINESS_REPORT_1_25.md",
            "src/qnwis/docs/audit/READINESS_SUMMARY.html",
        }
        assert expected.issubset(set(artifacts.keys()))
        for item in expected:
            assert artifacts[item]["sha256"]
            assert artifacts[item]["size_bytes"] > 0

    def test_review_doc_exists(self, run_gate):
        """The readiness gate review document must be produced."""
        run_gate()
        review_doc = ROOT / "src" / "qnwis" / "docs" / "reviews" / "readiness_gate_review.md"
        assert review_doc.exists()
        content = review_doc.read_text(encoding="utf-8")
        assert "Readiness Gate Review" in content

    def test_wrapper_scripts_exist(self):
        """Run scripts must exist for POSIX and Windows."""
        sh_script = ROOT / "scripts" / "qa" / "run_readiness.sh"
        ps_script = ROOT / "scripts" / "qa" / "run_readiness.ps1"
        assert sh_script.exists()
        assert ps_script.exists()


class TestCoverageGate:
    """Test coverage threshold enforcement."""

    def test_coverage_gate_runs(self, readiness_report):
        """Coverage gate must execute."""
        gates = {g["name"]: g for g in readiness_report["gates"]}
        assert "unit_and_integration_tests" in gates
        details = gates["unit_and_integration_tests"]["details"]
        assert "critical_modules" in details

    def test_coverage_artifacts_generated(self, run_gate):
        """Coverage gate must generate artifacts."""
        run_gate()

        # Check for coverage artifacts
        coverage_xml = ROOT / "coverage.xml"
        htmlcov = ROOT / "htmlcov"

        # At least one should exist if tests ran
        assert coverage_xml.exists() or htmlcov.exists()


class TestDeterminismGate:
    """Test deterministic access enforcement."""

    def test_determinism_gate_runs(self, readiness_report):
        """Determinism gate must execute."""
        gates = {g["name"]: g for g in readiness_report["gates"]}
        assert "deterministic_access" in gates

    def test_no_direct_sql_in_agents(self):
        """Agents must not contain direct SQL."""
        agents_dir = ROOT / "src" / "qnwis" / "agents"
        if not agents_dir.exists():
            pytest.skip("Agents directory not found")

        violations = []
        for agent_file in agents_dir.glob("*.py"):
            if agent_file.name.startswith("_"):
                continue

            content = agent_file.read_text()
            # Check for SQL keywords
            sql_keywords = ["SELECT ", "INSERT INTO", "UPDATE ", "DELETE FROM"]
            for keyword in sql_keywords:
                if keyword in content:
                    # Check if it's in a string/comment context
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        if keyword in line and not line.strip().startswith("#"):
                            violations.append(f"{agent_file.name}:{i} - {keyword}")

        assert len(violations) == 0, f"Direct SQL found in agents: {violations}"


class TestCitationGate:
    """Test citation enforcement."""

    def test_citation_gate_runs(self, readiness_report):
        """Citation gate must execute."""
        gates = {g["name"]: g for g in readiness_report["gates"]}
        assert "citation_enforcement" in gates

    def test_citation_enforcer_exists(self):
        """Citation enforcer module must exist."""
        citation_enforcer = ROOT / "src" / "qnwis" / "verification" / "citation_enforcer.py"
        assert citation_enforcer.exists()


class TestVerificationGate:
    """Test verification layers."""

    def test_verification_gate_runs(self, readiness_report):
        """Verification gate must execute."""
        gates = {g["name"]: g for g in readiness_report["gates"]}
        assert "verification_layers" in gates
        assert "result_verification" in gates

    def test_all_verification_layers_present(self):
        """All verification layer files must exist."""
        verification_dir = ROOT / "src" / "qnwis" / "verification"
        if not verification_dir.exists():
            pytest.skip("Verification directory not found")

        required_files = [
            "layer2_crosschecks.py",
            "layer3_policy_privacy.py",
            "layer4_sanity.py",
            "citation_enforcer.py",
            "result_verifier.py",
            "audit_trail.py",
            "confidence.py",
        ]

        missing = []
        for file in required_files:
            if not (verification_dir / file).exists():
                missing.append(file)

        assert len(missing) == 0, f"Missing verification files: {missing}"


class TestAuditGate:
    """Test audit trail requirements."""

    def test_audit_trail_exists(self):
        """Audit trail module must exist."""
        audit_trail = ROOT / "src" / "qnwis" / "verification" / "audit_trail.py"
        assert audit_trail.exists()

    def test_audit_store_exists(self):
        """Audit store module must exist."""
        audit_store = ROOT / "src" / "qnwis" / "verification" / "audit_store.py"
        assert audit_store.exists()


class TestOrchestrationGate:
    """Test orchestration flow."""

    def test_orchestration_gate_runs(self, run_gate):
        """Orchestration gate must execute."""
        run_gate()
        json_report = AUDIT_ROOT / "readiness_report.json"

        with json_report.open(encoding="utf-8") as f:
            report = json.load(f)

        gates = {g["name"]: g for g in report["gates"]}
        assert "orchestration_flow" in gates

    def test_orchestration_components_exist(self):
        """All orchestration components must exist."""
        orchestration_dir = ROOT / "src" / "qnwis" / "orchestration"
        if not orchestration_dir.exists():
            pytest.skip("Orchestration directory not found")

        required_files = [
            "classifier.py",
            "graph.py",
            "coordination.py",
            "intent_catalog.yml",
        ]

        missing = []
        for file in required_files:
            if not (orchestration_dir / file).exists():
                missing.append(file)

        assert len(missing) == 0, f"Missing orchestration files: {missing}"


class TestAgentsGate:
    """Test agent implementations."""

    def test_agents_gate_runs(self, readiness_report):
        """Agents gate must execute."""
        gates = {g["name"]: g for g in readiness_report["gates"]}
        assert "agents_end_to_end" in gates

    def test_all_required_agents_exist(self):
        """All required agent files must exist."""
        agents_dir = ROOT / "src" / "qnwis" / "agents"
        if not agents_dir.exists():
            pytest.skip("Agents directory not found")

        required_agents = [
            "pattern_detective.py",
            "national_strategy.py",
            "time_machine.py",
            "pattern_miner.py",
            "predictor.py",
        ]

        missing = []
        for agent in required_agents:
            agent_path = agents_dir / agent
            if not agent_path.exists():
                missing.append(agent)
            elif agent_path.stat().st_size < 1000:
                # Agent file is too small to be real implementation
                missing.append(f"{agent} (too small)")

        assert len(missing) == 0, f"Missing/incomplete agents: {missing}"


class TestStepCompleteness:
    """Enforce explicit checks for all 25 steps."""

    def test_all_steps_accounted_for(self, readiness_report):
        gates = {g["name"]: g for g in readiness_report["gates"]}
        assert "step_completeness" in gates
        details = gates["step_completeness"]["details"]
        assert len(details["steps"]) == 25
        assert details["missing"] == {}


class TestCitationsAndDerived:
    """Validate narratives use QIDs."""

    def test_citations_gate_runs(self, readiness_report):
        gates = {g["name"]: g for g in readiness_report["gates"]}
        assert "citations_and_derived" in gates
        assert gates["citations_and_derived"]["details"]["violations"] == []


class TestPerformanceGuards:
    """Ensure micro-benchmarks execute."""

    def test_performance_gate_runs(self, readiness_report):
        gates = {g["name"]: g for g in readiness_report["gates"]}
        perf_gate = gates["performance_guards"]
        assert perf_gate["details"]["durations"]


class TestSecurityAndStability:
    """Security, privacy, and stability guards."""

    def test_security_gate_runs(self, readiness_report):
        gates = {g["name"]: g for g in readiness_report["gates"]}
        sec_gate = gates["security_and_privacy"]
        assert not sec_gate["details"]["secret_hits"]
        assert not sec_gate["details"]["pii_hits"]

    def test_stability_gate_runs(self, readiness_report):
        gates = {g["name"]: g for g in readiness_report["gates"]}
        stability = gates["stability_controls"]
        assert all(stability["details"]["env"].values())


class TestLintersAndTypesGate:
    """Regression tests for lint/type coverage."""

    def test_linters_gate_reports_fixable_counts(self, readiness_report):
        gates = {g["name"]: g for g in readiness_report["gates"]}
        lint_gate = gates["linters_and_types"]
        ruff_details = lint_gate["details"]["ruff"]
        assert "fixable" in ruff_details
        assert isinstance(ruff_details["fixable"], int)
        assert ruff_details["fixable"] >= 0

    def test_no_sim102_regressions(self, readiness_report):
        gates = {g["name"]: g for g in readiness_report["gates"]}
        lint_gate = gates["linters_and_types"]
        ruff_rules = lint_gate["details"]["ruff"]["rules"]
        sim102_hits = ruff_rules.get("SIM102", 0)
        assert sim102_hits == 0, f"SIM102 violations detected: {sim102_hits}"


class TestFailFastBehavior:
    """Test fail-fast behavior on errors."""

    def test_gate_fails_on_critical_errors(self, readiness_report):
        """Gate must fail fast on ERROR severity findings."""
        failed_critical = [g for g in readiness_report["gates"] if not g["ok"] and g["severity"] == "ERROR"]
        if failed_critical:
            assert not readiness_report["overall_pass"], "Should fail on ERROR severity gates"


class TestPlaceholderGate:
    """Validate placeholder scanning results."""

    def test_no_placeholder_hits(self, readiness_report):
        gates = {g["name"]: g for g in readiness_report["gates"]}
        assert gates["no_placeholders"]["details"]["violations"] == []


class TestSmokeMatrix:
    """Test smoke matrix configuration."""

    def test_smoke_matrix_exists(self):
        """Smoke matrix YAML must exist."""
        smoke_matrix = ROOT / "src" / "qnwis" / "scripts" / "qa" / "smoke_matrix.yml"
        assert smoke_matrix.exists()

    def test_smoke_matrix_has_all_agents(self):
        """Smoke matrix must cover all agents."""
        smoke_matrix = ROOT / "src" / "qnwis" / "scripts" / "qa" / "smoke_matrix.yml"
        if not smoke_matrix.exists():
            pytest.skip("Smoke matrix not found")

        import yaml

        with smoke_matrix.open(encoding="utf-8") as f:
            matrix = yaml.safe_load(f)

        required_sections = [
            "pattern_detective",
            "national_strategy",
            "time_machine",
            "pattern_miner",
            "predictor",
            "orchestration",
            "verification",
        ]

        missing = []
        for section in required_sections:
            if section not in matrix:
                missing.append(section)

        assert len(missing) == 0, f"Missing smoke scenarios: {missing}"


class TestGrepRules:
    """Test grep rules configuration."""

    def test_grep_rules_exist(self):
        """Grep rules YAML must exist."""
        grep_rules = ROOT / "src" / "qnwis" / "scripts" / "qa" / "grep_rules.yml"
        assert grep_rules.exists()

    def test_grep_rules_structure(self):
        """Grep rules must have proper structure."""
        grep_rules = ROOT / "src" / "qnwis" / "scripts" / "qa" / "grep_rules.yml"
        if not grep_rules.exists():
            pytest.skip("Grep rules not found")

        import yaml

        with grep_rules.open(encoding="utf-8") as f:
            rules = yaml.safe_load(f)

        assert "disallow" in rules
        assert "require" in rules or "required_files" in rules

    def test_placeholder_patterns_present(self):
        """Placeholder patterns must include TODO/FIXME/pass/NotImplemented."""
        import yaml

        grep_rules = ROOT / "src" / "qnwis" / "scripts" / "qa" / "grep_rules.yml"
        if not grep_rules.exists():
            pytest.skip("Grep rules not found")

        with grep_rules.open(encoding="utf-8") as f:
            rules = yaml.safe_load(f)

        patterns = rules["disallow"]["placeholders"]["patterns"]
        required = [
            r"\bTODO\b",
            r"\bFIXME\b",
            r"\bpass\b(?=\s*$)",
            r"\bNotImplemented\b",
            r"raise\s+NotImplementedError",
        ]
        for pattern in required:
            assert pattern in patterns
