# Step 22: Confidence Scoring System

## Overview

The Confidence Scoring System is a production-grade component that computes a deterministic confidence score (0-100) for every orchestration result. The score aggregates outputs from verification Layers 2-4, citation enforcement (Step 19), and result verification (Step 20) into a single, actionable metric with GREEN/AMBER/RED banding.

**Key Properties:**
- **Deterministic**: Same inputs always produce the same score
- **Configuration-driven**: All weights, penalties, and thresholds defined in YAML
- **Fail-safe**: Scoring never overrides existing verification failures
- **Audit-ready**: Score computed even on ERROR for audit trail completeness
- **Performance**: <5ms typical execution time

## Architecture

### Components

```
src/qnwis/verification/confidence.py     — Pure Python scoring engine
src/qnwis/config/confidence.yml          — Weights, penalties, thresholds
src/qnwis/orchestration/schemas.py       — ConfidenceBreakdown model
src/qnwis/orchestration/nodes/verify.py  — Integration point (post-verification)
src/qnwis/orchestration/nodes/format.py  — Report rendering
```

### Data Flow

```
Verification Layers (L2-L4)
    ↓
Citation Enforcement (Step 19)
    ↓
Result Verification (Step 20)
    ↓
Audit Trail Generation (Step 21)
    ↓
Confidence Computation (Step 22) ← YOU ARE HERE
    ↓
Format Node (renders section)
    ↓
OrchestrationResult.confidence
```

### UI Hooks

The verify node exposes both the full `ConfidenceBreakdown` and a compact
`confidence_dashboard_payload` containing `{score, band, coverage, freshness}`
so dashboards can subscribe to a stable JSON structure without scraping the
report Markdown.

## Scoring Algorithm

### Component Scores (0-100 each)

All deductions are capped so that no single penalty can shave more than 50% off a
component, and small-sample guards blend low-support metrics back toward the
neutral score until at least three observations are available. This keeps
edge cases (single citation, one-off claim) from driving runaway swings.

1. **Citation Coverage** (weight: 0.25)
   - Base score: `100 * (cited_numbers / total_numbers)`
   - Penalty: -100 if any citation errors exist (malformed, unknown source, missing QID)
   - Handles zero numbers gracefully (returns 100)

2. **Result Verification** (weight: 0.40)
   - Base score: `100 * (claims_matched / claims_total)`
   - Penalty: -15 if any math consistency check fails
   - Largest weight reflects importance of numeric accuracy

3. **Cross-Source Validation** (weight: 0.10)
   - Base score: 100
   - Penalty: -3 per Layer 2 cross-check warning
   - Detects discrepancies between LMIS/GCC-STAT/external sources

4. **Privacy Compliance** (weight: 0.10)
   - Base score: 100
   - Penalty: -1 per PII redaction applied
   - Gentle penalty; redactions are protective, not errors

5. **Data Freshness** (weight: 0.15)
   - Base score: 100 if within SLA (72h default)
   - Penalty: -2 per 10 hours beyond SLA
   - Ensures timely data for decision-making

### Aggregation

```python
raw_score = (
    w_citation * citation_score +
    w_numbers * numbers_score +
    w_cross * cross_score +
    w_privacy * privacy_score +
    w_freshness * freshness_score
)

final_score = round(clamp(raw_score, 0, 100))
```

### Special Cases

**Insufficient Evidence**: When `total_numbers == 0 AND claims_total == 0`:
- Return configured floor score (default: 60)
- Add reason: "Insufficient evidence: no numeric claims or verifications"

**Reason Hygiene**:
- Reasons are sanitized, deduplicated, and sorted deterministically.
- `guards.max_reason_count` limits the list length; overflow is summarized as
  "`... N additional factor(s)`" to keep UI real estate predictable.

**Streaming Sessions**:
- Supplying `previous_score` activates hysteresis (when enabled) so AMBER/GREEN
  transitions require a meaningful delta (default: 4 points).

### Band Mapping

| Band | Threshold | Interpretation |
|------|-----------|----------------|
| GREEN | ≥90 | High confidence; all verification layers passed |
| AMBER | 75-89 | Medium confidence; some issues detected |
| RED | <75 | Low confidence; significant issues present |

When streaming or iterative sessions feed a `previous_score`, the optional
band hysteresis (enabled by default) keeps the qualitative band locked until
the delta exceeds the configured tolerance (4 points). This prevents noisy
bouncing between AMBER/GREEN when scores fluctuate by just a couple of points.

## Configuration

### `src/qnwis/config/confidence.yml`

```yaml
weights:
  citation: 0.25
  numbers: 0.40
  cross: 0.10
  privacy: 0.10
  freshness: 0.15

penalties:
  math_fail: 15
  l2_per_item: 3
  redaction_per_item: 1
  freshness_per_10h: 2

thresholds:
  GREEN: 90
  AMBER: 75
  RED: 0

guards:
  min_score_on_insufficient: 60
  min_support_numbers: 3
  min_support_claims: 3
  max_reason_count: 8

caps:
  penalty_fraction: 0.5

stability:
  enable_band_hysteresis: true
  hysteresis_tolerance: 4

integration:
  include_in_failures: true
```

**Validation**: Weights must sum to 1.0 (±1e-6). Engine raises `ValueError` if violated.

## Integration Points

### Verify Node

After all verification layers complete (regardless of WARN/ERROR):

```python
from ...verification.confidence import aggregate_confidence, ConfidenceInputs, ConfidenceRules

# Extract inputs from verification summary
inputs = ConfidenceInputs(
    total_numbers=citation_report.total_numbers,
    cited_numbers=citation_report.cited_numbers,
    citation_errors=len(uncited + malformed + missing_qid),
    claims_total=result_report.claims_total,
    claims_matched=result_report.claims_matched,
    math_checks=result_report.math_checks,
    l2_warnings=count_layer2_warnings,
    l3_redactions=verification_summary.applied_redactions,
    l4_errors=count_layer4_errors,
    l4_warnings=count_layer4_warnings,
    max_age_hours=compute_max_age,
    freshness_sla_hours=config.freshness_max_hours,
)

# Compute confidence
result = aggregate_confidence(inputs, rules)

# Attach to metadata
breakdown = ConfidenceBreakdown(
    score=result.score,
    band=result.band,
    components=result.components,
    reasons=result.reasons,
)
```

### Format Node

Renders confidence section in final report:

```python
def _format_confidence_summary(confidence: ConfidenceBreakdown) -> ReportSection:
    # Score + band with emoji
    # Component breakdown table
    # Top 5 reasons affecting score
    # Interpretation guidance
```

Attached to `OrchestrationResult.confidence` field.

## Output Schema

```python
class ConfidenceBreakdown(BaseModel):
    score: int = Field(ge=0, le=100)
    band: Literal["GREEN", "AMBER", "RED"]
    components: Dict[str, float]  # 5 components, each 0-100
    reasons: List[str]  # Sorted, unique, human-readable
```

### Example

```json
{
  "score": 87,
  "band": "AMBER",
  "components": {
    "citation": 100.0,
    "numbers": 85.0,
    "cross": 100.0,
    "privacy": 98.0,
    "freshness": 100.0
  },
  "reasons": [
    "All 12 claims properly cited",
    "Math checks failed: percent_total≈100",
    "No cross-source discrepancies",
    "PII redactions applied: 2",
    "Data age within SLA: 24.0h"
  ]
}
```

## Report Section Example

```markdown
## Confidence Assessment

**Overall Score**: 87/100 — **AMBER** ⚠️

**Component Breakdown:**

| Component | Score | Weight |
|-----------|-------|--------|
| Citation Coverage | 100.0 | — |
| Result Verification | 85.0 | — |
| Cross-Source Checks | 100.0 | — |
| Privacy Compliance | 98.0 | — |
| Data Freshness | 100.0 | — |

**Key Factors:**

1. All 12 claims properly cited
2. Math checks failed: percent_total≈100
3. No cross-source discrepancies
4. PII redactions applied: 2
5. Data age within SLA: 24.0h

**Interpretation:**
- Medium confidence: Some verification issues detected.
- Review key factors above before making critical decisions.
```

## Operational Guide

### When Score is GREEN (≥90)

- **Action**: Approve for decision-making
- **Typical use cases**: Executive briefings, policy recommendations, external reporting
- **Review requirements**: Standard peer review

### When Score is AMBER (75-89)

- **Action**: Review key factors before use
- **Typical issues**: 
  - Math consistency check failures (rounding, totals)
  - Small number of uncited claims
  - Minor cross-source discrepancies
- **Remediation**: Agent re-run with corrected citations or verification config adjustments

### When Score is RED (<75)

- **Action**: Remediate before use
- **Typical issues**:
  - High citation error rate
  - Large number of unmatched claims
  - Significant cross-source discrepancies
  - Stale data (>SLA)
- **Remediation**: 
  - Fix agent citation logic
  - Update stale data sources
  - Investigate L2/L4 violations

## Performance Characteristics

- **Typical runtime**: <5ms
- **Memory**: O(n) where n = number of reasons (typically <20)
- **CPU**: Pure Python arithmetic, no I/O or external calls
- **Determinism**: Guaranteed for same inputs

## Testing Strategy

### Unit Tests

```python
# tests/unit/verification/test_confidence.py

def test_all_perfect():
    # All 100s → score 100, band GREEN
    
def test_insufficient_evidence():
    # No numbers/claims → floor score 60
    
def test_citation_errors():
    # Errors penalize heavily
    
def test_math_check_failure():
    # Penalty applied to numbers component
    
def test_weights_validation():
    # Weights must sum to 1.0
```

### Integration Tests

```python
# tests/integration/orchestration/test_confidence_integration.py

def test_confidence_in_orchestration():
    # End-to-end workflow includes confidence
    
def test_confidence_on_verification_failure():
    # Confidence computed even on ERROR
```

## Monitoring & Metrics

### Metrics Emitted

- `confidence.computed` (counter, tags: band)
- `confidence.score_distribution` (histogram)
- `confidence.component_scores` (gauge per component)

### Alerts

- **Low confidence rate**: >20% RED scores in 1h window
- **Config validation failures**: Any weight sum violations
- **Computation failures**: Exceptions during scoring

## Troubleshooting

### Score unexpectedly low

1. Check `reasons` list in breakdown
2. Inspect component scores to identify weak areas
3. Review verification summary for underlying issues

### Confidence not computed

1. Verify `confidence.yml` exists and is valid
2. Check logs for config loading errors
3. Ensure verification summary is available (not skipped)

### Weight validation error

```
ValueError: Weights must sum to 1.0 (got 0.95)
```

**Fix**: Adjust weights in `confidence.yml` to sum exactly to 1.0

## Future Enhancements

- [ ] Configurable weight profiles (conservative, balanced, aggressive)
- [ ] Temporal trend analysis (score degradation over time)
- [ ] Component-specific remediation suggestions
- [ ] Integration with alerting for critical LOW scores

## References

- Step 19: Citation Enforcement (`step19_citation_enforcement.md`)
- Step 20: Result Verification (`step20_result_verification.md`)
- Step 21: Audit Trail (`docs/verification/audit_trail.md`)
- Verification Engine: `src/qnwis/verification/engine.py`

---

**Status**: ✅ PRODUCTION-READY  
**Version**: 1.0  
**Last Updated**: 2024-11-07
