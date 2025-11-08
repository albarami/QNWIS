# Readiness Gate - Steps 1-25 Validation

## Overview

The Readiness Gate is a production-grade validation system that proves Steps 1-25 are complete, non-placeholder, deterministic, verified, and performant end-to-end.

## Components

### 1. Orchestrator (`readiness_gate.py`)
Main script that executes all validation gates in sequence with fail-fast behavior.

**Gates:**
- `gate_no_placeholders` - Ensures no TODO/FIXME/pass/NotImplemented
- `gate_linters_and_types` - Runs ruff, flake8, mypy --strict
- `gate_deterministic_access` - Enforces no direct SQL/HTTP in agents
- `gate_unit_and_integration_tests` - Runs full pytest suite with coverage
- `gate_cache_and_materialization` - Validates cache infrastructure
- `gate_verification_layers` - Checks Steps 18-22 verification files
- `gate_citation_enforcement` - Tests Step-19 citation enforcement
- `gate_result_verification` - Tests Step-20 result verifier
- `gate_orchestration_flow` - Validates Steps 14-16 orchestration
- `gate_agents_end_to_end` - Checks all agent implementations
- `gate_performance_smoke` - Performance infrastructure checks

### 2. Configuration Files

**`smoke_matrix.yml`**
- Natural language → intent smoke scenarios
- Covers all agents (Steps 9-13, 23-25)
- Defines expected outputs and performance targets

**`grep_rules.yml`**
- Pattern enforcement rules
- Disallowed patterns (placeholders, direct SQL/HTTP, hardcoded secrets)
- Required patterns (DataClient usage, citations, structured logging)
- File-level requirements

**`stepwise_matrix.csv`**
- Comprehensive deliverables checklist
- Maps each step to required artifacts
- Verification method for each deliverable

### 3. System Tests (`test_readiness_gate.py`)
pytest-based validation that the gate system itself works correctly.

**Test Classes:**
- `TestReadinessGateExecution` - Gate mechanics
- `TestCoverageGate` - Coverage threshold enforcement
- `TestDeterminismGate` - Deterministic access checks
- `TestCitationGate` - Citation enforcement
- `TestVerificationGate` - Verification layers
- `TestAuditGate` - Audit trail requirements
- `TestOrchestrationGate` - Orchestration flow
- `TestAgentsGate` - Agent implementations
- `TestFailFastBehavior` - Error handling
- `TestSmokeMatrix` - Configuration validation
- `TestGrepRules` - Pattern rules validation

### 4. CI Integration (`ci_readiness.yml`)
GitHub Actions workflow for automated validation on push/PR.

**Jobs:**
- `readiness-gate` - Runs full gate with artifact upload
- `system-tests` - Runs system-level validation tests

## Usage

### Local Execution

```powershell
# Run the readiness gate
python src\qnwis\scripts\qa\readiness_gate.py

# Run system tests
pytest tests\system\test_readiness_gate.py -v

# Run specific gate test
pytest tests\system\test_readiness_gate.py::TestCoverageGate -v
```

### Expected Outputs

**Success:**
```
================================================================================
READINESS GATE - Steps 1-25 Validation
================================================================================

Running gate: no_placeholders... ✅ PASS (1234ms)
Running gate: linters_and_types... ✅ PASS (5678ms)
Running gate: deterministic_access... ✅ PASS (890ms)
...

✅ JSON report: src/qnwis/docs/audit/readiness_report.json
✅ Markdown report: src/qnwis/docs/audit/READINESS_REPORT_1_25.md

================================================================================
FINAL STATUS: ✅ PASS
================================================================================
```

**Failure (Fail-Fast):**
```
Running gate: no_placeholders... ❌ FAIL (234ms)

❌ FATAL: Gate 'no_placeholders' failed with ERROR severity
Details: {
  "patterns_searched": ["\\bTODO\\b", "\\bFIXME\\b", ...],
  "matches_found": 5,
  "sample_matches": ["agents/pattern_detective.py:42:  # TODO: implement"]
}

FAIL-FAST: Stopping execution
```

### Artifacts Generated

1. **`readiness_report.json`** - Machine-readable report
   ```json
   {
     "gates": [...],
     "overall_pass": true,
     "execution_time_ms": 45678,
     "timestamp": "2025-11-08T14:32:00Z",
     "summary": {"total": 11, "passed": 11, "failed": 0},
     "artifacts": {"coverage.xml": "abc123..."}
   }
   ```

2. **`READINESS_REPORT_1_25.md`** - Human-readable summary

3. **`coverage.xml`** - Code coverage (XML)

4. **`htmlcov/`** - HTML coverage report

5. **`junit.xml`** - Test results

## Gate Details

### Coverage Thresholds
- **New modules:** ≥90% line coverage
- **Critical modules:** ≥95% line coverage
- **Overall:** ≥80% line coverage
- **Branch coverage:** Required

### Performance Targets
- Time Machine window ops: <50ms
- Pattern Miner scan: <200ms (30 cohorts × 4 windows)
- Predictor baseline+bands: <100ms

### Deterministic Access Rules
- **Agents:** Must use DataClient only, no direct SQL/HTTP
- **Query Registry:** Only place for SQL definitions
- **Connectors:** Only place for HTTP calls

### Citation Requirements
- All numeric claims must have QID citations
- Format: "Per LMIS data (QID_...)..."
- Enforced via CitationEnforcer

### Verification Layers (Steps 18-22)
- Layer 2: Cross-checks
- Layer 3: Privacy/RBAC
- Layer 4: Sanity/freshness
- Citation enforcement (Step 19)
- Result verification (Step 20)
- Audit trail (Step 21)
- Confidence scoring (Step 22)

## Integration with Development Workflow

### Pre-Commit
```bash
# Quick smoke check
pytest tests/system/test_readiness_gate.py::TestReadinessGateExecution -v
```

### Pre-Push
```bash
# Full local gate
python src/qnwis/scripts/qa/readiness_gate.py
```

### CI/CD
- Automatic execution on PR creation
- Blocks merge if gate fails
- Reports posted as PR comments
- Artifacts uploaded for review

## Troubleshooting

### Gate Fails: no_placeholders
**Issue:** TODOs/FIXMEs found in code
**Solution:** Complete or remove all placeholder comments

### Gate Fails: linters_and_types
**Issue:** Code style or type errors
**Solution:** Run `ruff check --fix src/` and fix mypy errors

### Gate Fails: deterministic_access
**Issue:** Direct SQL/HTTP in agents
**Solution:** Refactor to use DataClient abstraction

### Gate Fails: unit_and_integration_tests
**Issue:** Test failures or low coverage
**Solution:** Fix failing tests, add tests for uncovered code

### Gate Fails: citation_enforcement
**Issue:** Citation enforcer not working
**Solution:** Check `src/qnwis/verification/citation_enforcer.py` implementation

## Maintenance

### Adding New Agents (e.g., Step 26)
1. Update `smoke_matrix.yml` with new agent scenarios
2. Add agent check to `gate_agents_end_to_end()`
3. Update `stepwise_matrix.csv` with new deliverables
4. Add system tests to `test_readiness_gate.py`

### Adding New Gates
1. Implement `gate_<name>()` function in `readiness_gate.py`
2. Add to `gate_functions` list in `main()`
3. Add corresponding test class in `test_readiness_gate.py`
4. Document in this README

### Updating Thresholds
- Coverage: Modify threshold checks in `gate_unit_and_integration_tests()`
- Performance: Update targets in `smoke_matrix.yml`
- Rules: Edit `grep_rules.yml` patterns

## References

- **Steps 1-8:** Data Foundation (config, queries, cache)
- **Steps 9-13:** Core Agents (pattern detection, strategy, analysis)
- **Steps 14-16:** Orchestration (router, graph, coordination)
- **Step 17:** Cache & Materialization
- **Steps 18-22:** Verification Suite (cross-checks, privacy, citations, audit)
- **Step 23:** Time Machine (temporal analysis)
- **Step 24:** Pattern Miner (effect ranking)
- **Step 25:** Predictor (forecasting)

---

**Last Updated:** 2025-11-08
**Maintainer:** QNWIS Development Team
