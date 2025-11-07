# Step-20: Result Verification (Layer 3 Claim Validation)

## Overview

The Result Verification system provides deterministic validation of numeric claims in agent narratives against QueryResult data. This Layer-3 verification catches fabrications, rounding errors, and math inconsistencies **before** responses reach users.

## Architecture

### Component Structure

```
src/qnwis/verification/
├── result_verifier.py         # Core verification engine
├── number_extractors.py        # Unit-aware numeric parsing
├── schemas.py                  # NumericClaim, ClaimBinding, ResultVerificationReport
└── engine.py                   # Integration with Layers 2-4

src/qnwis/config/
└── result_verification.yml     # Tolerances and rules

src/qnwis/orchestration/nodes/
├── verify.py                   # Loads config, runs verification, fails on ERROR
└── format.py                   # Formats verification summary section
```

### Verification Flow

```
1. Agent generates narrative → Prefetch node loads QueryResults
2. Verify node:
   a. Extract NumericClaims (number_extractors.py)
   b. Bind claims to QueryResults (result_verifier.py)
   c. Check rounding/unit tolerances
   d. Run math consistency checks (% sums, table totals)
   e. Aggregate issues → ResultVerificationReport
3. If report.ok == False: FAIL workflow (like Step-18)
4. Format node: Append "Result Verification Summary" section
```

## Core Models

### NumericClaim

```python
class NumericClaim(BaseModel):
    value_text: str           # "1,234.5"
    value: float              # 1234.5
    unit: Unit                # "count" | "percent" | "currency"
    span: Tuple[int, int]     # Character position
    sentence: str             # Containing sentence
    citation_prefix: Optional[str]   # "Per LMIS:"
    query_id: Optional[str]          # "lmis_salary_q1_2024"
    source_family: Optional[str]     # "LMIS" | "GCC-STAT" | "WorldBank"
```

### ClaimBinding

```python
class ClaimBinding(BaseModel):
    claim: NumericClaim
    matched: bool
    matched_source_qid: Optional[str]    # Which QueryResult matched
    matched_location: Optional[str]      # "data[5].salary" | "row_count"
```

### ResultVerificationReport

```python
class ResultVerificationReport(BaseModel):
    ok: bool                          # Pass/fail
    claims_total: int
    claims_matched: int
    issues: List[VerificationIssue]   # Errors/warnings
    bindings: List[ClaimBinding]
    math_checks: Dict[str, bool]      # {"percent_sum_L42": True}
```

## Verification Logic

### 1. Numeric Claim Extraction

**Module**: `number_extractors.py`

Scans Markdown narrative for numeric patterns:

```python
# Matches: 1,234.5%, 50 QAR, +2.3, 15 percent
NUM_TOKEN = r"(?<![\w/])([+-]?\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(\s?(%|percent|pp|bps|QAR|USD))?(?![\w/])"
```

**Unit Classification**:
- `%`, `percent`, `pp`, `bps` → `"percent"`
- `QAR`, `USD` → `"currency"`
- No unit or integer → `"count"`

**Context Extraction**:
- Finds sentence boundaries around claim
- Detects citation prefix (`Per LMIS:`, `According to GCC-STAT:`)
- Extracts query_id if present (reuses Step-19 QID detection)

**Filters**:
- Years (2023, 2024) skipped if `ignore_years: true`
- Small numbers (<1.0) skipped if `ignore_numbers_below: 1.0`

### 2. Claim Binding Strategy

**Module**: `result_verifier.py::bind_claim_to_sources()`

**Selection Priority**:
1. **Exact query_id match** (if `prefer_query_id: true`)
2. **Source family preference** (LMIS, GCC-STAT, WorldBank)
3. **All sources** (fallback)

**Value Matching**:

```python
# Row count check (for integer counts)
if claim.unit == "count" and abs(claim.value - len(qr.rows)) <= abs_epsilon:
    return matched

# Data row search (for all units)
for row in qr.rows:
    for field, candidate in row.data.items():
        # Unit-aware comparison
        if unit == "percent":
            # Try both [0,1] and [0,100] representations
            if 0 <= target <= 1 and candidate > 1:
                candidate = candidate / 100.0
            elif target > 1 and 0 <= candidate <= 1:
                candidate = candidate * 100.0
        
        # Apply tolerances
        diff = abs(target - candidate)
        if diff <= abs_epsilon:  # 0.5 for counts
            return matched
        if abs(target) > 0 and (diff / abs(target)) <= rel_epsilon:  # 1%
            return matched
```

### 3. Tolerances Configuration

**File**: `src/qnwis/config/result_verification.yml`

```yaml
rounding:
  abs_epsilon: 0.5    # ±0.5 for integer counts (handles rounding)
  rel_epsilon: 0.01   # 1% relative tolerance for large values

percent:
  epsilon_pct: 0.5    # ±0.5% for percentage matching
  sum_to_100: true    # Check bullet groups sum to ~100%

currency:
  currencies: [QAR, USD]
  epsilon_amount: 50  # ±QR50 allowed if rounded in narrative

binding:
  prefer_query_id: true           # Use QID before source_family
  require_citation_first: true    # Uncited claims = ERROR
  ignore_numbers_below: 1.0       # Skip small values
```

### 4. Math Consistency Checks

**Module**: `result_verifier.py::check_math_consistency()`

**Heuristics**:

1. **Percentage bullet groups**:
   ```markdown
   - 45% in construction
   - 30% in services
   - 25% in manufacturing
   → Sum = 100% ± epsilon_pct (0.5%)
   ```

2. **Table totals** (future enhancement):
   ```markdown
   | Sector | Count |
   |--------|-------|
   | A      | 100   |
   | B      | 200   |
   | Total  | 300   |
   → Total matches sum of rows
   ```

## Integration Points

### verify.py

```python
# Load config (cached)
result_tolerances = _load_result_verification_tolerances()

# Initialize engine
engine = VerificationEngine(
    config,
    user_roles=user_roles,
    citation_rules=citation_rules,
    result_tolerances=result_tolerances,  # NEW
)

# Run verification
verification_summary = engine.run_with_agent_report(narrative_md, query_results)

# Store in metadata
if verification_summary.result_verification_report:
    metadata["result_verification_report"] = report.model_dump()

# CRITICAL: Fail on errors (same path as Step-18/19)
if not verification_summary.ok:
    error_issues = [i for i in issues if i.severity == "error"]
    return {"error": f"Verification failed: {error_codes}"}
```

### format.py

```python
# Extract report from metadata
result_report = workflow_state.metadata.get("result_verification_report")

# Format summary section
if result_report:
    sections.append(_format_result_verification_summary(result_report))

# Output:
# ## Result Verification Summary
# **Status**: PASS
# **Claims Checked**: 15
# **Claims Matched**: 14 (93.3%)
# **Math Checks**: 2 passed, 0 failed
```

## Issue Codes

| Code | Severity | Trigger | Remediation |
|------|----------|---------|-------------|
| `CLAIM_UNCITED` | error | No citation prefix | Add `Per LMIS:` before claim |
| `CLAIM_NOT_FOUND` | error | Value not in QueryResult | Fix rounding or check source |
| `ROUNDING_MISMATCH` | warning | Outside tolerances | Increase epsilon or verify data |
| `UNIT_MISMATCH` | error | Percent vs count confusion | Check unit classification |
| `MATH_INCONSISTENT` | error | % group != 100 | Fix percentages or add rounding note |
| `AMBIGUOUS_SOURCE` | warning | Multiple QIDs possible | Specify exact query_id |

## Edge Cases Handled

### 1. Percentage Representations

```python
# Narrative: "15% growth"
claim.value = 15.0, claim.unit = "percent"

# QueryResult may have:
data[0].growth_rate = 0.15  # [0, 1] range
# OR
data[0].growth_rate = 15.0  # [0, 100] range

# Verifier tries both:
if 0 <= claim.value <= 1 and candidate > 1:
    candidate = candidate / 100.0  # Scale down
elif claim.value > 1 and 0 <= candidate <= 1:
    candidate = candidate * 100.0  # Scale up
```

### 2. Thousand Separators

```python
# Narrative: "1,234 employees"
value_text = "1,234"
value = 1234.0  # Normalized (commas removed)
```

### 3. Signed Numbers

```python
# Narrative: "+5% increase" or "-2.3% decline"
sign = match.group("sign")  # "+" or "-"
value = float(num_str)
if sign == "-":
    value = -value
```

### 4. Row Count Matches

```python
# Narrative: "Based on 50 records, Per LMIS: QID:lmis_q1"
claim.value = 50.0, claim.unit = "count"

# Check row_count first (fast path)
if abs(50.0 - len(qr.rows)) <= 0.5:
    binding.matched_location = "row_count"
```

### 5. Citation-less Claims

```python
# If require_citation_first: true
if not claim.citation_prefix:
    issues.append(VerificationIssue(
        code="CLAIM_UNCITED",
        severity="error",  # Fails workflow
    ))
    bindings.append(ClaimBinding(claim=claim, matched=False))
    continue  # Skip verification for uncited claims
```

## Performance Characteristics

- **Target**: <5 seconds for large responses (per roadmap)
- **Optimization**: Short-circuit on first match (avoid O(N²))
- **Caching**: Config loaded once per workflow run

```python
# Efficient search (stops at first match)
for qr in candidate_sources:
    loc = _check_row_count_match(claim, qr, abs_epsilon)
    if loc:
        return ClaimBinding(matched=True, ...)  # SHORT-CIRCUIT
    
    loc = _search_value_in_rows(claim.value, qr.rows, ...)
    if loc:
        return ClaimBinding(matched=True, ...)  # SHORT-CIRCUIT
```

## Testing Strategy

### Unit Tests

```python
# tests/unit/verification/test_result_verifier.py

def test_extract_numeric_claims():
    md = "Per LMIS: 1,234 employees (QID:lmis_001)"
    claims = extract_numeric_claims(md)
    assert claims[0].value == 1234.0
    assert claims[0].unit == "count"
    assert claims[0].query_id == "lmis_001"

def test_bind_claim_exact_match():
    claim = NumericClaim(value=1234.0, unit="count", query_id="lmis_001", ...)
    qr = QueryResult(query_id="lmis_001", rows=[...])  # 1234 rows
    binding = bind_claim_to_sources(claim, [qr], tolerances)
    assert binding.matched
    assert binding.matched_location == "row_count"

def test_percentage_normalization():
    claim = NumericClaim(value=15.0, unit="percent", ...)
    qr = QueryResult(rows=[Row(data={"rate": 0.15})])  # [0, 1] format
    binding = bind_claim_to_sources(claim, [qr], tolerances)
    assert binding.matched  # Handles scale conversion

def test_math_consistency_percentages():
    md = "- 45%\n- 30%\n- 24%"  # Sums to 99% (within epsilon)
    checks = check_math_consistency(md, {"epsilon_pct": 0.5, "sum_to_100": True})
    assert checks["percent_sum_L1"]  # Pass
```

### Integration Tests

```python
# tests/integration/verification/test_result_verification_workflow.py

def test_verification_fails_on_unmatched_claim():
    narrative = "Per LMIS: 9999 employees (QID:lmis_001)"  # Wrong value
    qr = QueryResult(query_id="lmis_001", rows=[...])  # 1234 rows
    report = verify_numbers(narrative, [qr], tolerances)
    assert not report.ok
    assert any(i.code == "CLAIM_NOT_FOUND" for i in report.issues)

def test_workflow_fails_on_verification_error():
    state = {...}  # Mock state with mismatched claim
    result = verify_structure(state)
    assert "error" in result  # Workflow failed
    assert "Verification failed" in result["error"]
```

## Runbook

### Scenario 1: Claim Not Found

**Symptom**: `CLAIM_NOT_FOUND` error in verification report

**Diagnosis**:
1. Check narrative for citation: `grep "Per LMIS" narrative.md`
2. Check query_id in QueryResult: `echo $QID`
3. Check actual value in data: `jq '.rows[].data' result.json`

**Resolution**:
```python
# If rounding issue:
# Update config: abs_epsilon: 1.0 (was 0.5)

# If wrong QueryResult cited:
# Fix agent prompt to use correct QID

# If data truly mismatched:
# Investigate upstream data pipeline
```

### Scenario 2: Math Inconsistency

**Symptom**: `MATH_INCONSISTENT` error for percentage group

**Diagnosis**:
```python
# Check bullet group:
# - 45.2%
# - 30.1%
# - 24.5%
# Sum = 99.8% (outside 0.5% epsilon)
```

**Resolution**:
```yaml
# Option A: Increase tolerance
percent:
  epsilon_pct: 1.0  # Was 0.5

# Option B: Add rounding note in narrative
# "Percentages may not sum to exactly 100% due to rounding."
```

### Scenario 3: Performance Degradation

**Symptom**: Verification takes >5 seconds

**Diagnosis**:
```python
# Profile with:
import time
start = time.perf_counter()
report = verify_numbers(narrative, qresults, tolerances)
duration = time.perf_counter() - start
```

**Resolution**:
- Reduce `claims_total` by increasing `ignore_numbers_below`
- Optimize QueryResult indexing (future enhancement)
- Consider async verification for large datasets

## Security Considerations

1. **No New Data Access**: Operates only on prefetched QueryResults
2. **Config Validation**: YAML schema enforced via Pydantic
3. **Injection Prevention**: Regex patterns do not execute code
4. **Deterministic**: Same inputs always produce same outputs

## Future Enhancements

1. **Table Total Validation**: Detect table structures and verify row sums
2. **Cross-Claim Consistency**: Verify related claims (e.g., "20% of 1000 = 200")
3. **Currency Conversion**: Handle QAR ↔ USD conversions
4. **Trend Validation**: Check time-series consistency (YoY growth rates)
5. **Confidence Scoring**: Probabilistic matching for fuzzy claims

## Success Metrics

- ✅ Claims matched: **≥95%** (target)
- ✅ False positives: **<5%** (too strict tolerances)
- ✅ Performance: **<5 seconds** for 50+ claims
- ✅ Workflow failure rate: **<10%** (catches real issues)

## References

- **Step-19**: Citation enforcement (provides query_id detection)
- **Step-18**: Verification failure path (workflow error handling)
- **Layers 2-4**: Cross-checks, privacy, sanity (parallel verification)
- **QueryResult**: Deterministic data model (source of truth)
