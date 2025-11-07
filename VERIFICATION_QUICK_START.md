# Verification Layers 2-4 Quick Start

## Overview

The verification engine automatically runs on every orchestration workflow, providing:
- **Layer 2**: Cross-source metric consistency checks
- **Layer 3**: PII redaction (emails, IDs, names)
- **Layer 4**: Sanity checks (freshness, ranges, rates)

## Configuration

Edit `src/qnwis/config/verification.yml`:

```yaml
# Cross-check rules
crosschecks:
  - metric: "retention_rate"
    tolerance_pct: 2.0      # Allow 2% difference
    prefer: "LMIS"          # Prefer LMIS when mismatch

# Privacy rules
privacy:
  k_anonymity: 15
  redact_email: true
  redact_ids_min_digits: 10
  allow_names_when_role: ["allow_names"]

# Sanity rules
sanity:
  - metric: "retention_rate"
    rate_0_1: true          # Must be in [0,1]
  - metric: "headcount"
    must_be_non_negative: true

# Freshness
freshness_max_hours: 72     # Max data age
```

## Automatic Integration

Verification runs automatically in the orchestration workflow:

```python
# No code changes needed! 
# Just run your normal workflow
result = workflow.run(task)

# Results include verification data
print(result.verification)         # {"ok": True, "issues_count": 0}
print(result.redactions_applied)   # 2
print(result.issues_summary)       # {"L3:warning": 2}
```

## Reading Results

```python
from qnwis.orchestration.workflow import run_workflow

result = run_workflow(task)

# Check overall status
if result.verification.get("ok"):
    print("✓ All verification checks passed")
else:
    print(f"⚠ {result.verification['issues_count']} issues found")

# Review redactions
if result.redactions_applied > 0:
    print(f"Applied {result.redactions_applied} PII redactions")

# Examine issues by severity
for layer_severity, count in result.issues_summary.items():
    print(f"{layer_severity}: {count} issues")
```

## CLI Verification

Verify a saved report offline:

```bash
python -m qnwis.cli.qnwis_verify \
  --report-json path/to/report.json \
  --config src/qnwis/config/verification.yml \
  --roles analyst
```

## Issue Codes

### Layer 2 (Cross-Checks)
- `XCHK_TOLERANCE_EXCEEDED` - Metric mismatch exceeds tolerance

### Layer 3 (Privacy)
- `PII_EMAIL` - Email addresses redacted
- `PII_ID` - Numeric IDs redacted
- `PII_NAME` - Names redacted
- `K_ANONYMITY_VIOLATION` - Group size below k threshold

### Layer 4 (Sanity)
- `STALE_DATA` - Data older than freshness limit
- `FRESHNESS_PARSE_ERROR` - Cannot parse timestamp
- `NEGATIVE_VALUE` - Metric is negative when must be non-negative
- `RATE_OUT_OF_RANGE` - Rate not in [0,1] bounds
- `BELOW_MIN` - Value below configured minimum
- `ABOVE_MAX` - Value above configured maximum
- `NON_NUMERIC_VALUE` - Expected numeric, got other type

## Severity Levels

- **info**: Informational, no action needed
- **warning**: Potential issue, review recommended (workflow continues ✓)
- **error**: Critical issue, **WORKFLOW FAILS** (orchestration terminated ❌)

⚠️ **CRITICAL**: ERROR-severity issues stop the workflow and prevent report generation. This is intentional - if data is bad enough to trigger errors, we cannot trust the analysis.

## Adding New Rules

### Cross-Check Rule

```yaml
crosschecks:
  - metric: "qatarization_rate"
    tolerance_pct: 3.0
    prefer: "LMIS"
```

### Sanity Rule

```yaml
sanity:
  - metric: "salary"
    must_be_non_negative: true
    min_value: 0
    max_value: 1000000
```

### Privacy Policy

```yaml
privacy:
  k_anonymity: 20              # Stricter k-anonymity
  redact_email: true
  redact_ids_min_digits: 8     # Redact 8+ digit IDs
  allow_names_when_role:
    - "senior_analyst"
    - "director"
```

## Programmatic Use

```python
from qnwis.verification import VerificationEngine, VerificationConfig
import yaml

# Load config
with open("src/qnwis/config/verification.yml") as f:
    config_data = yaml.safe_load(f)
config = VerificationConfig.model_validate(config_data)

# Create engine
engine = VerificationEngine(
    config,
    user_roles=["analyst"]  # User roles for RBAC
)

# Run verification
summary = engine.run(
    narrative_md=agent_narrative,
    primary=primary_query_result,
    references=[ref1, ref2]
)

# Check results
if not summary.ok:
    for issue in summary.issues:
        print(f"[{issue.severity.upper()}] {issue.layer}/{issue.code}")
        print(f"  {issue.message}")
        print(f"  Details: {issue.details}")
```

## Best Practices

1. **Configure tolerances carefully**: Too strict = false positives, too loose = miss real issues
2. **Review warnings regularly**: They often indicate data quality problems
3. **Update rules as schema evolves**: Add new metrics to sanity checks
4. **Test with real data**: Ensure k-anonymity thresholds match your data
5. **Document RBAC roles**: Clearly define who can see unredacted names

## Performance

- Typical runtime: **<20ms** per verification
- No external data fetches
- Deterministic results
- Safe to run on every request

## Troubleshooting

### Config not loading
- Check path: `src/qnwis/config/verification.yml`
- Verify YAML syntax
- Check logs: `logger.error("Failed to load verification config: ...")`

### No verification results
- Config file must exist
- Check `result.metadata` for `verification_ok` key
- Ensure query results are available

### Too many redactions
- Adjust `allow_names_when_role` for privileged users
- Increase `redact_ids_min_digits` threshold
- Review PII patterns in `layer3_policy_privacy.py`

### False positive cross-checks
- Increase `tolerance_pct` for volatile metrics
- Review segment/sector mapping logic
- Check if reference data is comparable

## Examples

### Minimal Config (Privacy Only)

```yaml
privacy:
  redact_email: true
  redact_ids_min_digits: 10

sanity: []
crosschecks: []
freshness_max_hours: 720  # 30 days
```

### Strict Config (Maximum Validation)

```yaml
crosschecks:
  - metric: "retention_rate"
    tolerance_pct: 1.0
  - metric: "qatarization_rate"
    tolerance_pct: 1.0
  - metric: "headcount"
    tolerance_pct: 0.5

privacy:
  k_anonymity: 25
  redact_email: true
  redact_ids_min_digits: 8

sanity:
  - metric: "retention_rate"
    rate_0_1: true
  - metric: "qatarization_rate"
    rate_0_1: true
  - metric: "headcount"
    must_be_non_negative: true
    min_value: 1
  - metric: "salary"
    must_be_non_negative: true
    min_value: 1000

freshness_max_hours: 24
```

## Support

- Documentation: `VERIFICATION_LAYERS_2_4_IMPLEMENTATION.md`
- Source: `src/qnwis/verification/`
- Config: `src/qnwis/config/verification.yml`
- Tests: `tests/unit/orchestration/test_verify.py`
