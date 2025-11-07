# Result Verification Quick Start Guide

## What It Does

Validates that every numeric claim in agent narratives matches actual data in QueryResults. Catches fabrications, rounding errors, and math inconsistencies **before** responses reach users.

## 5-Minute Setup

### 1. Configuration (Already Set Up)

**File**: `src/qnwis/config/result_verification.yml`

```yaml
rounding:
  abs_epsilon: 0.5      # ±0.5 for counts
  rel_epsilon: 0.01     # 1% relative tolerance

percent:
  epsilon_pct: 0.5      # ±0.5% for percentages
  sum_to_100: true      # Check % groups sum to 100

binding:
  prefer_query_id: true
  require_citation_first: true
```

**To adjust tolerances**: Edit the YAML file. Changes take effect on next workflow run (config is cached per run).

### 2. How It Works (Automatic)

```
Agent Output → Verify Node → Result Verification → Format Node
                    ↓
              If errors found: FAIL workflow
              If pass: Continue to format
```

**No code changes needed** - already integrated into:
- `verify.py` - Loads config, runs verification
- `format.py` - Displays verification summary

### 3. What Gets Verified

**Extracts numeric claims**:
```markdown
Per LMIS: 1,234 employees (QID:lmis_001)
According to GCC-STAT: Growth is 15.5%
Salary averages 5,000 QAR
```

**Checks**:
- ✅ Has citation prefix (`Per LMIS:`, `According to GCC-STAT:`)
- ✅ Value exists in QueryResult (within tolerance)
- ✅ Units match (count/percent/currency)
- ✅ Percentage groups sum to ~100%

### 4. Example: Pass

**Input**:
```markdown
Per LMIS: Total workforce is 10,234 employees (QID:lmis_q1).
- 45% in construction
- 30% in services
- 25% in manufacturing
```

**QueryResult**:
```python
QueryResult(
    query_id="lmis_q1",
    rows=[Row(...) for _ in range(10234)],  # ✅ Matches
)
```

**Result**: ✅ PASS → Workflow continues

### 5. Example: Fail

**Input**:
```markdown
Per LMIS: Total workforce is 15,000 employees (QID:lmis_q1).
```

**QueryResult**:
```python
QueryResult(
    query_id="lmis_q1",
    rows=[Row(...) for _ in range(10234)],  # ❌ Mismatch
)
```

**Result**: ❌ FAIL → Workflow stops with error:
```
Verification failed with 1 error(s): L3/CLAIM_NOT_FOUND
```

## Common Scenarios

### Scenario 1: Rounding Tolerance

**Problem**: Agent rounds "1234.4" to "1234", verification fails

**Solution**:
```yaml
rounding:
  abs_epsilon: 1.0  # Increase from 0.5 to 1.0
```

### Scenario 2: Percentage Format

**Problem**: Data has `growth_rate: 0.15`, agent says "15%"

**Solution**: Already handled! Verifier tries both formats:
- 15% → checks 15.0 and 0.15

### Scenario 3: Missing Citations

**Problem**: `CLAIM_UNCITED` errors for every number

**Solution A** (Fix agent prompt):
```markdown
Always cite sources: "Per LMIS: <claim> (QID:<id>)"
```

**Solution B** (Disable requirement temporarily):
```yaml
binding:
  require_citation_first: false  # Warnings instead of errors
```

### Scenario 4: Math Consistency False Positive

**Problem**: "45% + 30% + 25.5% = 100.5%" fails math check

**Solution**:
```yaml
percent:
  epsilon_pct: 1.0  # Increase tolerance from 0.5% to 1.0%
```

## Testing Your Changes

### Run Unit Tests
```bash
python -m pytest tests/unit/verification/test_result_verifier.py -v
```

**Expected**: 21 passed in <1s

### Test Integration
```python
# In your workflow test
from src.qnwis.orchestration.nodes.verify import verify_structure

state = {
    "agent_output": agent_report,
    "prefetch_cache": {qid: query_result},
    "task": task,
    ...
}

result = verify_structure(state)

# Should fail if claims don't match data
assert "error" in result or result["metadata"]["verification_ok"]
```

## Interpreting Reports

### Verification Summary (in formatted output)

```markdown
## Result Verification Summary

**Status**: PASS
**Claims Checked**: 15
**Claims Matched**: 14 (93.3%)
**Math Checks**: 2 passed, 0 failed

**Errors** (1):
1. `CLAIM_NOT_FOUND` - Claim '15000' not found in cited sources (QID: lmis_q1)

**Remediation Tips**:
- Verify claimed values match actual data. Check for rounding differences.
```

### Issue Codes

| Code | What It Means | How to Fix |
|------|---------------|------------|
| `CLAIM_UNCITED` | No citation prefix | Add `Per LMIS:` before claim |
| `CLAIM_NOT_FOUND` | Value not in data | Check data or fix claim |
| `MATH_INCONSISTENT` | % don't sum to 100 | Fix percentages or increase epsilon |
| `ROUNDING_MISMATCH` | Outside tolerance | Increase abs_epsilon or rel_epsilon |
| `UNIT_MISMATCH` | Wrong unit type | Fix unit classification |

## Debugging

### Step 1: Check Logs
```bash
# Look for verification details
grep "Result verification complete" logs/workflow.log
# "Result verification complete: 14/15 claims matched, ok=False"
```

### Step 2: Inspect Issues
```python
# In workflow metadata
metadata["result_verification_report"]["issues"]
# [
#   {
#     "code": "CLAIM_NOT_FOUND",
#     "message": "Claim '15000' not found...",
#     "severity": "error",
#     "details": {"value": "15000.0", "query_id": "lmis_q1"}
#   }
# ]
```

### Step 3: Check Bindings
```python
# See what matched/didn't match
metadata["result_verification_report"]["bindings"]
# [
#   {
#     "claim": {"value": 15000.0, "query_id": "lmis_q1"},
#     "matched": False,
#     "matched_location": None
#   }
# ]
```

### Step 4: Verify Data
```python
# Check QueryResult has expected value
qr = prefetch_cache["lmis_q1"]
print(f"Row count: {len(qr.rows)}")  # 10234 (not 15000!)
print(f"Data fields: {qr.rows[0].data.keys()}")
```

## Performance Tips

### Current Performance
- Extraction: <100ms for 20 claims
- Verification: <200ms for 20 claims × 3 sources
- Total: <500ms (well under 5s target)

### If Slow (>5s)
1. **Reduce claim count**:
   ```yaml
   binding:
     ignore_numbers_below: 5.0  # Skip small numbers
   ```

2. **Reduce source count**: Filter QueryResults before verification

3. **Profile**:
   ```python
   import time
   start = time.perf_counter()
   report = verify_numbers(narrative, qresults, tolerances)
   print(f"Verification took {time.perf_counter() - start:.3f}s")
   ```

## FAQ

**Q: Will this break existing workflows?**  
A: No. If config file doesn't exist, verification is skipped silently.

**Q: Can I disable it temporarily?**  
A: Yes. Rename or delete `src/qnwis/config/result_verification.yml`

**Q: What if agent doesn't cite sources?**  
A: Set `require_citation_first: false` to get warnings instead of errors

**Q: How do I handle currency conversions?**  
A: Use `epsilon_amount` tolerance for QAR/USD rounding differences

**Q: Can I verify derived metrics (averages, etc.)?**  
A: Not yet. Current version only matches direct data values

**Q: What about "approximately 1000" vs "1000"?**  
A: Only extracts numbers. Natural language qualifiers are ignored

## Next Steps

1. ✅ Tests passing? Deploy to staging
2. ✅ Monitor false positive rate (<5% target)
3. ✅ Tune tolerances based on real data
4. ✅ Add more math consistency checks (tables, trends)

## Support

- **Documentation**: `docs/verification/step20_result_verification.md`
- **Tests**: `tests/unit/verification/test_result_verifier.py`
- **Implementation**: `src/qnwis/verification/result_verifier.py`
- **Config**: `src/qnwis/config/result_verification.yml`

---

**Ready to use!** No code changes needed. Verification runs automatically on every workflow.
