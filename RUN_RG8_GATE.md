# RG-8 Continuity Gate — Quick Reference

**Purpose**: Validate Business Continuity & Failover Orchestration system compliance
**Checks**: 5 automated checks for presence, integrity, validity, audit, and performance
**Status**: ✅ PASS (5/5 checks)

## Overview

The RG-8 Continuity Gate validates the Business Continuity & Failover Orchestration system with 5 deterministic checks covering presence, integrity, validity, audit, and performance.

## Prerequisites

```bash
# Ensure you're in the project root
cd /path/to/lmis_int

# Activate virtual environment (if using)
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

## Run Gate

### Full Gate Execution

```bash
python src/qnwis/scripts/qa/rg8_continuity_gate.py
```

### Expected Output

```
RG-8.1: Continuity Presence Check
  [PASS] All continuity modules and interfaces present

RG-8.2: Continuity Plan Integrity Check
  [PASS] Plan round-trip integrity verified

RG-8.3: Continuity Failover Validity Check
  [PASS] Failover simulation passed all checks

RG-8.4: Continuity Audit Integrity Check
  [PASS] Audit pack integrity verified

RG-8.5: Continuity Performance Check
  [PASS] p95 latency 38ms < 100ms

Generating artifacts...
  Report: docs/audit/rg8/rg8_report.json
  Summary: docs/audit/rg8/CONTINUITY_SUMMARY.md
  Badge: docs/audit/badges/rg8_pass.svg
  Badge: src/qnwis/docs/audit/badges/rg8_pass.svg

============================================================
RG-8 CONTINUITY GATE: PASS ✓
All 5 checks passed
```

## Gate Checks

### Check 1: Continuity Presence ✅

**What it validates**:
- All continuity modules import successfully
- CLI commands are discoverable
- API routes are registered

**Modules checked**:
- `qnwis.continuity.models`
- `qnwis.continuity.heartbeat`
- `qnwis.continuity.planner`
- `qnwis.continuity.executor`
- `qnwis.continuity.verifier`
- `qnwis.continuity.simulate`
- `qnwis.continuity.audit`

### Check 2: Plan Integrity ✅

**What it validates**:
- Continuity plans round-trip deterministically
- YAML → dict → YAML produces identical results
- No data loss in serialization

**Test**:
1. Generate plan from test cluster + policy
2. Convert to YAML
3. Parse back to dict
4. Verify identical to original

### Check 3: Failover Validity ✅

**What it validates**:
- Simulated failover passes all checks
- Quorum is maintained
- Policy adherence is verified
- Verification report shows PASS

**Test**:
1. Simulate primary node failure
2. Execute failover plan
3. Verify quorum status
4. Check policy compliance

### Check 4: Audit Integrity ✅

**What it validates**:
- Audit pack structure is complete
- SHA-256 manifest hash is correct
- All required fields present
- Confidence scoring works

**Test**:
1. Generate audit pack
2. Calculate manifest hash
3. Verify hash matches
4. Check all required fields

### Check 5: Performance ✅

**What it validates**:
- p95 failover simulation < 100ms
- Deterministic performance
- No performance regressions

**Test**:
1. Run 20 simulations with different seeds
2. Calculate p95 latency
3. Verify < 100ms threshold

## Artifacts Generated

After successful gate execution, the following artifacts are created:

### 1. Gate Report
**Path**: `docs/audit/rg8/rg8_report.json`

```json
{
  "checks": {
    "continuity_presence": {
      "status": "PASS",
      "modules": ["models", "heartbeat", "planner", ...],
      "cli_commands": ["plan", "simulate", "execute", ...],
      "api_routes": ["plan", "execute", "status", "simulate"]
    },
    "continuity_plan_integrity": {
      "status": "PASS",
      "plan_id": "...",
      "action_count": 5,
      "estimated_total_ms": 40000,
      "round_trip": "identical"
    },
    ...
  },
  "metrics": {
    "checks_passed": 5,
    "checks_total": 5,
    "pass_rate": 100.0
  }
}
```

### 2. Summary Document
**Path**: `docs/audit/rg8/CONTINUITY_SUMMARY.md`

Markdown summary with:
- Gate status (PASS/FAIL)
- Check results
- Artifact list

### 3. Sample Plan
**Path**: `docs/audit/rg8/sample_plan.yaml`

Example continuity plan showing:
- Cluster configuration
- Policy settings
- Failover actions
- Estimated timings

### 4. Badge
**Paths**:
- `docs/audit/badges/rg8_pass.svg`
- `src/qnwis/docs/audit/badges/rg8_pass.svg`

SVG badge showing gate status.

## Troubleshooting

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'qnwis'`

**Solution**:
```bash
# Ensure you're in project root
cd /path/to/lmis_int

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/Mac
# or
set PYTHONPATH=%PYTHONPATH%;%CD%  # Windows
```

### Check Failures

**Symptom**: One or more checks show `[FAIL]`

**Solution**:
1. Review error message in output
2. Check `docs/audit/rg8/rg8_report.json` for details
3. Run specific test:
   ```bash
   pytest tests/unit/continuity/ -v
   pytest tests/integration/continuity/ -v
   ```

### Performance Check Fails

**Symptom**: `p95 latency exceeds 100ms threshold`

**Solution**:
1. Check system load
2. Close resource-intensive applications
3. Run gate again
4. If persistent, review code for performance issues

## Manual Verification

### Verify Module Imports

```python
python -c "
from qnwis.continuity.models import Node, Cluster
from qnwis.continuity.heartbeat import HeartbeatMonitor
from qnwis.continuity.planner import ContinuityPlanner
from qnwis.continuity.executor import FailoverExecutor
from qnwis.continuity.verifier import FailoverVerifier
from qnwis.continuity.simulate import FailoverSimulator
from qnwis.continuity.audit import ContinuityAuditor
print('All imports successful')
"
```

### Verify CLI

```bash
python -m qnwis.cli.qnwis_continuity --help
```

### Verify API

```python
python -c "
from qnwis.api.routers.continuity import router
print(f'Router prefix: {router.prefix}')
print(f'Routes: {[r.path for r in router.routes]}')
"
```

## Integration with CI/CD

### GitHub Actions

```yaml
name: RG-8 Continuity Gate

on: [push, pull_request]

jobs:
  rg8-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run RG-8 Gate
        run: |
          python src/qnwis/scripts/qa/rg8_continuity_gate.py
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: rg8-artifacts
          path: docs/audit/rg8/
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
python src/qnwis/scripts/qa/rg8_continuity_gate.py
if [ $? -ne 0 ]; then
    echo "RG-8 gate failed. Commit aborted."
    exit 1
fi
```

## Related Commands

### Run Unit Tests

```bash
pytest tests/unit/continuity/ -v --cov=qnwis.continuity
```

### Run Integration Tests

```bash
pytest tests/integration/continuity/ -v
```

### Generate Coverage Report

```bash
pytest tests/unit/continuity/ tests/integration/continuity/ \
  --cov=qnwis.continuity \
  --cov-report=html \
  --cov-report=term-missing
```

### View Coverage

```bash
# Open in browser
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Success Criteria

✅ All 5 checks PASS  
✅ Artifacts generated in `docs/audit/rg8/`  
✅ Badge shows "PASS" status  
✅ Exit code 0

## Failure Handling

If gate fails:

1. **Review output** for specific check failures
2. **Check report** at `docs/audit/rg8/rg8_report.json`
3. **Run tests** to identify root cause
4. **Fix issues** and re-run gate
5. **Verify** all checks pass before proceeding

## Support

For issues or questions:
- Review documentation: `docs/ops/step33_continuity_failover.md`
- Check implementation summary: `STEP33_CONTINUITY_IMPLEMENTATION_COMPLETE.md`
- Run tests: `pytest tests/unit/continuity/ tests/integration/continuity/ -v`

---

**Gate Version**: 1.0
**Last Updated**: 2025-01-11
**Status**: Production-Ready ✓
