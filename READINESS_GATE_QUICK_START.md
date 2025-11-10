# Readiness Gate - Quick Start Guide

## One-Line Execution

```powershell
# Run the complete readiness validation
python src\qnwis\scripts\qa\readiness_gate.py
```

## What It Does

Validates **ALL of Steps 1-25** in one comprehensive pass:

1. ✅ No placeholders (TODO/FIXME/pass/NotImplemented)
2. ✅ Clean linting (ruff, flake8, mypy --strict)
3. ✅ Deterministic access (no direct SQL/HTTP in agents)
4. ✅ Full test suite with coverage thresholds
5. ✅ Cache infrastructure (Redis, MVs, warmup)
6. ✅ Verification layers (Steps 18-22)
7. ✅ Citation enforcement (Step 19)
8. ✅ Result verification (Step 20)
9. ✅ Orchestration (Steps 14-16)
10. ✅ All agents (Steps 9-13, 23-25)
11. ✅ Performance checks

## Quick Commands

```powershell
# Full readiness gate
python src\qnwis\scripts\qa\readiness_gate.py

# Run system tests
pytest tests\system\test_readiness_gate.py -v

# Run specific test class
pytest tests\system\test_readiness_gate.py::TestCoverageGate -v

# Quick smoke check
pytest tests\system\test_readiness_gate.py::TestReadinessGateExecution::test_gate_script_exists -v
```

## Output Files

After execution, check:

```
src/qnwis/docs/audit/
├── readiness_report.json         # Machine-readable results
├── READINESS_REPORT_1_25.md      # Human-readable summary
└── READINESS_ARTIFACTS.md        # Artifact index

# Root directory (test artifacts)
coverage.xml                       # Coverage report (XML)
htmlcov/index.html                # Coverage report (HTML)
junit.xml                         # Test results
```

## Understanding Results

### ✅ SUCCESS
```
FINAL STATUS: ✅ PASS
```
- All gates passed
- All deliverables verified
- Ready for production

### ❌ FAILURE
```
Running gate: no_placeholders... ❌ FAIL (3747ms)

❌ FATAL: Gate 'no_placeholders' failed with ERROR severity
Details: {
  "matches_found": 25,
  "sample_matches": [...]
}

FAIL-FAST: Stopping execution
```

**What to do:**
1. Check the details in the error message
2. Fix the identified issues
3. Re-run the gate
4. Repeat until all gates pass

## Common Issues & Fixes

### Gate Fails: no_placeholders
**Issue:** TODO/FIXME/pass/NotImplemented found in code

**Fix:**
```powershell
# Find all instances
Get-ChildItem -Path "src\qnwis" -Recurse -Include *.py | Select-String -Pattern "\bTODO\b|\bFIXME\b"

# Replace empty pass statements with actual implementations
# Remove or complete TODO comments
```

### Gate Fails: linters_and_types
**Issue:** Code style or type errors

**Fix:**
```powershell
# Auto-fix what's possible
python -m ruff check --fix src/

# Check mypy errors
python -m mypy src/qnwis/ --strict

# Fix manually reported issues
```

### Gate Fails: deterministic_access
**Issue:** Direct SQL/HTTP in agents

**Fix:**
```python
# WRONG: Direct SQL in agent
def get_data(self):
    result = connection.execute("SELECT * FROM table")
    
# RIGHT: Use DataClient
def get_data(self):
    result = self.data_client.query("workforce_headcount", sector="All")
```

### Gate Fails: unit_and_integration_tests
**Issue:** Test failures or low coverage

**Fix:**
```powershell
# Run tests to see failures
pytest tests/ -v --tb=short

# Check coverage
pytest tests/ --cov=src/qnwis --cov-report=term-missing

# Add tests for uncovered code
```

## File Locations

```
src/qnwis/scripts/qa/
├── readiness_gate.py             # Main orchestrator
├── grep_rules.yml                # Pattern enforcement rules
└── smoke_matrix.yml              # Smoke test scenarios

src/qnwis/docs/audit/
├── README.md                     # Full documentation
├── READINESS_ARTIFACTS.md        # Artifact index
├── readiness_report.json         # Latest JSON report
├── READINESS_REPORT_1_25.md      # Latest MD report
└── checklists/
    └── stepwise_matrix.csv       # Deliverables checklist

tests/system/
└── test_readiness_gate.py        # System tests

.github/workflows/
└── ci_readiness.yml              # CI/CD integration
```

## CI/CD Integration

The gate runs automatically on:
- ✅ Push to `main` or `develop`
- ✅ Pull requests to `main` or `develop`
- ✅ Manual workflow dispatch

Results appear as:
- ✅ PR comments with gate summary
- ✅ Check status on commits
- ✅ Downloadable artifacts

## Performance Targets

| Component | Target | Checked By |
|-----------|--------|------------|
| Time Machine window ops | <50ms | gate_performance_smoke |
| Pattern Miner scan | <200ms | gate_performance_smoke |
| Predictor baseline+bands | <100ms | gate_performance_smoke |
| Overall coverage | ≥80% | gate_unit_and_integration_tests |
| New module coverage | ≥90% | gate_unit_and_integration_tests |
| Critical module coverage | ≥95% | gate_unit_and_integration_tests |

## Validation Scope

### Steps 1-8: Foundation
- Config management with environment validation
- Docker setup
- Structured logging
- Query registry
- DataClient abstraction
- Safe connectors
- No hardcoded secrets
- Cache middleware & TTL policies
- MV registry & refresh jobs

### Steps 9-13: Core Agents
- Pattern Detective
- National Strategy
- Skills Analyzer (if applicable)
- Nationalization Agent
- Labour Economist

### Steps 14-16: Orchestration
- Intent router/classifier
- Registry whitelisting
- LangGraph DAG execution
- Parallel/sequential coordination
- PII redaction
- Retry policies

### Step 17: Cache & Materialization
- Redis cache hit/miss
- Negative caching
- Warmup packs
- MV refresh (dry-run OK)
- TTL policy validation

### Steps 18-22: Verification Suite
- Layer 2: Cross-checks
- Layer 3: Privacy/RBAC
- Layer 4: Sanity/freshness
- Step 19: Citation enforcement
- Step 20: Result verification
- Step 21: Audit trail
- Step 22: Confidence scoring

### Step 23: Time Machine
- Baselines, breaks, trend reports
- Derived QueryResults with QIDs
- Performance <50ms for window ops

### Step 24: Pattern Miner
- Effect/support/stability ranking
- Seasonally adjusted effects
- Citations present
- Performance <200ms for scan

### Step 25: Predictor
- Baselines + bands + backtests + what-if
- Elasticities for what-if scenarios
- Deterministic & cited
- Performance <100ms for baseline+bands

## Getting Help

**Full Documentation:**
```powershell
# Open the comprehensive guide
code src\qnwis\docs\audit\README.md
```

**Check Latest Results:**
```powershell
# View JSON report
code src\qnwis\docs\audit\readiness_report.json

# View Markdown report
code src\qnwis\docs\audit\READINESS_REPORT_1_25.md
```

**Run Specific Tests:**
```powershell
# Test that gate can execute
pytest tests\system\test_readiness_gate.py::TestReadinessGateExecution -v

# Test coverage gate
pytest tests\system\test_readiness_gate.py::TestCoverageGate -v

# Test determinism gate
pytest tests\system\test_readiness_gate.py::TestDeterminismGate -v
```

## Current Status

**First Execution Results:**
- Status: ❌ FAIL (expected - validation working)
- Issue: 25 placeholder instances found
- Files affected:
  - `src/qnwis/agents/utils/derived_results.py` - Empty pass statements
  - `src/qnwis/data/deterministic/cache_access.py` - Empty pass
  - `src/qnwis/data/cache/backends.py` - NotImplementedError

**Next Action:**
Fix the identified placeholders and re-run the gate.

---

**For detailed information, see:**
- `src/qnwis/docs/audit/README.md` - Complete guide
- `READINESS_GATE_IMPLEMENTATION_COMPLETE.md` - Implementation details
- `src/qnwis/scripts/qa/grep_rules.yml` - Pattern rules
- `src/qnwis/scripts/qa/smoke_matrix.yml` - Smoke scenarios
