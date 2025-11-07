# Verification Failure Handling - CRITICAL

## ⚠️ ERROR-SEVERITY ISSUES FAIL THE WORKFLOW

**You were absolutely right** - we cannot ignore verification failures. The system now enforces this:

## Severity Behavior

### ERROR Severity → **WORKFLOW FAILS** ❌
```python
# These issues STOP the orchestration:
- NEGATIVE_VALUE: Metric is negative when must be non-negative
- RATE_OUT_OF_RANGE: Rate not in [0,1] bounds
- K_ANONYMITY_VIOLATION: Group size below k threshold
- NON_NUMERIC_VALUE: Expected numeric, got other type
```

**Result**: `state["error"]` is set, workflow terminates, no report generated.

### WARNING Severity → **WORKFLOW CONTINUES** ⚠️
```python
# These issues are logged but don't stop execution:
- XCHK_TOLERANCE_EXCEEDED: Metric mismatch exceeds tolerance
- PII_EMAIL: Email addresses redacted
- PII_ID: Numeric IDs redacted
- PII_NAME: Names redacted
- STALE_DATA: Data older than freshness limit
- BELOW_MIN/ABOVE_MAX: Value outside suggested bounds
```

**Result**: Report generated with warnings, redactions applied.

### INFO Severity → **INFORMATIONAL ONLY** ℹ️
```python
# These are purely informational
```

**Result**: Logged for audit purposes.

---

## Implementation

### In `verify.py`

```python
# CRITICAL: Fail workflow if verification detects errors
if not verification_summary.ok:
    error_issues = [
        i for i in verification_summary.issues 
        if i.severity == "error"
    ]
    error_codes = [f"{i.layer}/{i.code}" for i in error_issues]
    verification_error = (
        f"Verification failed with {len(error_issues)} error(s): "
        f"{', '.join(error_codes)}"
    )
    logger.error(verification_error)
    for issue in error_issues:
        logger.error(
            "  [%s] %s: %s", 
            issue.layer, issue.code, issue.message
        )

# If verification found errors, fail the workflow
if verification_error:
    return {
        **state,
        "error": verification_error,  # STOPS WORKFLOW
        "logs": [..., f"ERROR: {verification_error}"],
        "metadata": {...}
    }
```

---

## Example Scenarios

### Scenario 1: Rate Out of Range (ERROR)

```yaml
# Config
sanity:
  - metric: "retention_rate"
    rate_0_1: true
```

**Input**: `retention_rate = 1.5` (invalid)

**Output**:
```json
{
  "error": "Verification failed with 1 error(s): L4/RATE_OUT_OF_RANGE",
  "logs": [
    "ERROR: Verification failed with 1 error(s): L4/RATE_OUT_OF_RANGE",
    "ERROR:   [L4] RATE_OUT_OF_RANGE: retention_rate not in [0,1]: 1.5"
  ]
}
```

**Result**: ❌ **Workflow terminated, no report generated**

---

### Scenario 2: Cross-Check Tolerance (WARNING)

```yaml
# Config
crosschecks:
  - metric: "retention_rate"
    tolerance_pct: 2.0
```

**Input**: 
- Primary: `retention_rate = 0.85`
- Reference: `retention_rate = 0.90` (5.88% diff > 2%)

**Output**:
```json
{
  "ok": true,
  "verification": {
    "ok": true,
    "issues_count": 1,
    "stats": {"L2:warning": 1}
  },
  "warnings": [
    "L2/XCHK_TOLERANCE_EXCEEDED: retention_rate mismatch 5.88% for segment ALL"
  ]
}
```

**Result**: ✅ **Workflow continues, report generated with warning**

---

### Scenario 3: Multiple Errors

**Input**:
- Negative headcount: `-10`
- Rate out of range: `1.5`
- Very old data: 3 years stale

**Output**:
```json
{
  "error": "Verification failed with 3 error(s): L4/NEGATIVE_VALUE, L4/RATE_OUT_OF_RANGE, L4/STALE_DATA"
}
```

**Result**: ❌ **Workflow terminated**

---

## Configuration Guidelines

### When to Use ERROR vs WARNING

**Use ERROR severity for**:
- **Data integrity violations**: Negative counts, impossible rates
- **Security violations**: K-anonymity breaches
- **Critical freshness**: Data too old for decision-making
- **Type mismatches**: Expected number, got string

**Use WARNING severity for**:
- **Cross-check mismatches**: Different sources disagree
- **PII redactions**: Informational, not a failure
- **Soft bounds**: Values outside typical range but not impossible
- **Stale data**: Old but still usable

### Configure in `verification.yml`

```yaml
# ERROR-level checks (will fail workflow)
sanity:
  - metric: "retention_rate"
    rate_0_1: true              # ERROR if out of [0,1]
  
  - metric: "headcount"
    must_be_non_negative: true  # ERROR if negative

# WARNING-level checks (won't fail)
crosschecks:
  - metric: "retention_rate"
    tolerance_pct: 2.0          # WARNING if diff > 2%

freshness_max_hours: 72         # WARNING if older
```

---

## Testing Verification Failures

### Test That Errors Fail

```python
def test_verification_errors_fail_workflow():
    # Create data with ERROR-level issue
    primary = QueryResult(
        data=[{"retention_rate": 1.5}]  # Out of [0,1]
    )
    
    state = {...}
    result = verify_structure(state)
    
    # MUST fail
    assert result["error"] is not None
    assert "RATE_OUT_OF_RANGE" in result["error"]
```

### Test That Warnings Pass

```python
def test_warnings_dont_fail():
    # Create data with WARNING-level issue
    primary = QueryResult(
        data=[{"retention_rate": 0.85}]
    )
    reference = QueryResult(
        data=[{"retention_rate": 0.90}]  # 5.88% diff
    )
    
    result = verify_structure(state)
    
    # Should NOT fail
    assert result["error"] is None
    assert len(result["metadata"]["verification_warnings"]) > 0
```

---

## Logging Output

### ERROR Case
```
ERROR    verify:verify.py:284 Verification failed with 1 error(s): L4/RATE_OUT_OF_RANGE
ERROR    verify:verify.py:286   [L4] RATE_OUT_OF_RANGE: retention_rate not in [0,1]: 1.5
ERROR    verify:verify.py:206 Verification failed: Agent report evidence lacks freshness metadata
```

### WARNING Case
```
INFO     verify:verify.py:267 Verification: 1 issues, 2 redactions, ok=True
WARNING  verify:verify.py:216 Structural verification: 1 warnings
```

---

## Metrics Tracking

```python
# When errors occur
metrics.increment("agent.verify.failure", tags={"reason": "verification_errors"})

# When successful
metrics.increment("agent.verify.success", tags={"has_warnings": "true"})
```

---

## Operational Impact

### For Operators

1. **Monitor error rates**: `agent.verify.failure` with `reason=verification_errors`
2. **Review rejected reports**: Check logs for `Verification failed with N error(s)`
3. **Tune thresholds**: Adjust rules if too many false positives

### For Developers

1. **ERROR = Hard Fail**: Use sparingly for truly invalid data
2. **WARNING = Soft Fail**: Use for data quality concerns
3. **Test failure paths**: Ensure errors actually stop the workflow

### For Analysts

1. **Red flag indicators**: ERROR-level issues mean data is unreliable
2. **Yellow flag indicators**: WARNING-level issues need review
3. **Trust the system**: If report generated, data passed all ERROR checks

---

## Critical Principle

> **If the data is so bad that we shouldn't trust the analysis, we MUST fail the workflow.**
> 
> **Warnings inform. Errors protect.**

This is not optional - it's a quality gate for Qatar's Ministry of Labour LMIS system.
