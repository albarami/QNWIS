# Verification V2 and Minister Briefing

## Overview

This document describes the cross-source numeric verification (triangulation) system and Minister Briefing generator implemented for QNWIS. Both systems operate deterministically on synthetic CSV data without LLMs, network calls, or SQL.

## Architecture

### Verification Module

Located in `src/qnwis/verification/`:

- **`rules.py`**: Reusable numeric validation rules
- **`triangulation.py`**: Cross-source checks combining multiple query results

### Briefing Module

Located in `src/qnwis/briefing/`:

- **`minister.py`**: Generates executive briefings from council findings and verification results

### API Endpoint

- **`POST /v1/briefing/minister`**: Returns JSON with embedded Markdown briefing

### Process Flow

```
+---------+      +----------------------+      +------------------+      +--------------------+
| Queries | ---> | Triangulation Checks | ---> | Council Synthesis | ---> | Minister Briefings |
+---------+      +----------------------+      +------------------+      +--------------------+
```

## Validation Rules

### 1. Percent Bounds Check

**Code**: `percent_bounds`

**Purpose**: Ensure percentage metrics fall within [0, 100]

**Parameters**:
- `PCT_MIN = 0.0`
- `PCT_MAX = 100.0`

**Logic**:
```python
if key.endswith("_percent") and (value < 0 or value > 100):
    # Flag as warning
```

### 2. Sum-to-One Check

**Code**: `sum_to_one`

**Purpose**: Validate that component percentages sum to total

**Parameters**:
- `SUM_TOL = 0.5` (percent tolerance)

**Logic**:
```python
if abs((male_percent + female_percent) - total_percent) > SUM_TOL:
    # Flag as warning
```

**Example**:
- Male: 55.0%, Female: 44.0%, Total: 100.0%
- Delta: -1.0% (exceeds tolerance) → Warning

### 3. Year-over-Year Bounds Check

**Code**: `yoy_outlier`

**Purpose**: Detect unrealistic YoY growth rates

**Parameters**:
- `YOY_MIN = -100.0` (percent)
- `YOY_MAX = 200.0` (percent)

**Logic**:
```python
if yoy_percent < -100 or yoy_percent > 200:
    # Flag as warning
```

### 4. Qatarization Formula Check

**Code**: `qatarization_mismatch`

**Purpose**: Validate Qatarization percentage calculation

**Parameters**:
- `SUM_TOL = 0.5` (percent tolerance)

**Formula**:
```
expected_percent = 100 * qataris / (qataris + non_qataris)
```

**Logic**:
```python
if abs(expected_percent - reported_percent) > SUM_TOL:
    # Flag as warning
```

### 5. EWI vs YoY Coherence Check

**Code**: `ewi_incoherence`

**Purpose**: Ensure Employment Warning Indicator aligns with YoY trends

**Threshold**: EWI drop > 3%

**Logic**:
```python
if ewi_drop_percent > 3.0 and yoy_percent > 0.0:
    # Flag as warning (incoherent signals)
```

## Triangulation Checks

The `run_triangulation()` function performs four cross-source checks:

### Check 1: Employment Sum-to-One

**Check ID**: `employment_sum_to_one`

**Queries Used**:
- `q_employment_share_by_gender_2017_2024`

**Process**:
1. Get latest year data
2. Validate `male_percent + female_percent ≈ total_percent`
3. Check all `*_percent` fields are in [0, 100]

### Check 2: Qatarization Formula

**Check ID**: `qatarization_formula`

**Queries Used**:
- `q_qatarization_components`

**Process**:
1. Get component data (qataris, non_qataris, qatarization_percent)
2. Validate formula on first 10 rows
3. Flag mismatches exceeding tolerance

### Check 3: EWI vs YoY Employment

**Check ID**: `ewi_vs_yoy`

**Queries Used**:
- `q_sector_employment_by_year`
- `q_ewi_employment_drop`

**Process**:
1. Compute YoY growth per sector
2. Get latest EWI drop per sector
3. Check for incoherence (high EWI but positive YoY)

### Check 4: Bounds Sanity

**Check ID**: `bounds_sanity`

**Queries Used**:
- `q_employment_share_by_gender_2017_2024`

**Process**:
1. Sample first 2 rows
2. Validate all `*_percent` fields are in [0, 100]

## Briefing Structure

### MinisterBriefing Dataclass

```python
@dataclass
class MinisterBriefing:
    title: str                    # Briefing title
    headline: List[str]           # Top bullet points
    key_metrics: Dict[str, float] # Numeric KPIs
    red_flags: List[str]          # Verification issues (≤8)
    provenance: List[str]         # Data source locators
    markdown: str                 # Full briefing in Markdown
```

### Generation Process

1. **Run Council**: Execute agent council to gather findings and consensus
2. **Run Triangulation**: Perform cross-source checks
3. **Extract Headlines**: Build bullet points from consensus and warnings
4. **Collect Key Metrics**: Take top 5 numeric metrics from consensus
5. **Aggregate Red Flags**: Collect issues from triangulation (limit to 8)
6. **Build Provenance**: Deduplicate evidence locators
7. **Generate Markdown**: Format structured output

### Markdown Format

```markdown
# Minister Briefing (Synthetic Demo)

## Headline
- Employment total = 99.8% (synthetic).
- Verification warnings: employment_sum_to_one:1.

## Key Metrics
- **employment_total_percent**: 99.80
- **male_percent**: 55.00
- **female_percent**: 45.00

## Red Flags
- sum_to_one: male+female=100.000 vs total=99.800 (Δ=0.200)

## Provenance
- csv://aggregates/employment_share_by_gender.csv
- csv://aggregates/qatarization_by_sector.csv
```

## API Usage

### Endpoint

```
POST /v1/briefing/minister
```

### Parameters

- `queries_dir` (optional): Custom queries directory path
- `ttl_s` (default: 300): Cache TTL in seconds

### Request

```bash
curl -X POST http://localhost:8000/v1/briefing/minister?ttl_s=120
```

### Response

```json
{
  "title": "Minister Briefing — Synthetic Demo",
  "headline": [
    "Employment total = 99.8% (synthetic).",
    "Verification warnings: employment_sum_to_one:1."
  ],
  "key_metrics": {
    "employment_total_percent": 99.8,
    "male_percent": 55.0,
    "female_percent": 45.0
  },
  "red_flags": [
    "sum_to_one: male+female=100.000 vs total=99.800 (Δ=0.200)"
  ],
  "provenance": [
    "csv://aggregates/employment_share_by_gender.csv"
  ],
  "markdown": "# Minister Briefing (Synthetic Demo)\n..."
}
```

## Query Specifications

### syn_qatarization_components.yaml

```yaml
id: q_qatarization_components
title: Qatarization components by sector (synthetic)
description: Qataris, non-Qataris, and computed percent by sector/year.
source: csv
expected_unit: count
params:
  pattern: "aggregates/qatarization_by_sector.csv"
  select: ["year","sector","qataris","non_qataris","qatarization_percent"]
  year: 2023
constraints:
  freshness_sla_days: 3650
```

### syn_employment_latest_total.yaml

```yaml
id: q_employment_latest_total
title: Employment total percent (synthetic)
description: Totals used to cross-check sum-to-one.
source: csv
expected_unit: percent
params:
  pattern: "aggregates/employment_share_by_gender.csv"
  select: ["year","total_percent"]
  year: 2023
constraints:
  freshness_sla_days: 3650
```

## Testing

### Unit Tests

**Coverage Target**: ≥90% for verification and briefing modules

#### test_triangulation_rules.py

- Tests all validation rules (bounds, sum-to-one, YoY, Qatarization, EWI)
- Covers both pass and fail cases
- Tests None handling

#### test_triangulation_bundle.py

- Tests full triangulation execution
- Validates result structure
- Checks issue and sample formatting

#### test_briefing_builder.py

- Tests briefing generation
- Validates all fields and types
- Checks Markdown structure
- Verifies limits (red flags ≤8)

### Integration Tests

#### test_api_briefing.py

- Tests POST /v1/briefing/minister endpoint
- Validates response structure
- Tests with custom parameters
- Verifies deterministic behavior (same input = same output)

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_triangulation_rules.py -v

# Run with coverage
pytest tests/ --cov=src/qnwis/verification --cov=src/qnwis/briefing
```

## Implementation Notes

### Design Principles

1. **Deterministic Only**: No LLMs, no network calls, no SQL
2. **Synthetic Data**: All tests use CSV catalog with synthetic LMIS data
3. **Tolerant Thresholds**: ±0.5% for sum checks, [-100%, 200%] for YoY
4. **JSON-Safe**: All outputs serializable to JSON
5. **Windows Compatible**: No shell operations

### Performance

- **Triangulation**: Runs on cached queries (TTL: 300s default)
- **Briefing**: Single-pass generation
- **API**: Synchronous, blocking (suitable for executive reports)

### Error Handling

- Rules return empty lists when inputs are None
- Triangulation continues on individual check failures
- API returns 200 with empty sections if data unavailable

### Extension Points

To add new validation rules:

1. Define rule in `rules.py`:
   ```python
   def check_my_rule(val: float) -> List[RuleIssue]:
       # Implementation
   ```

2. Add to triangulation in `triangulation.py`:
   ```python
   res = TriangulationResult(check_id="my_check")
   res.issues += check_my_rule(data)
   ```

3. Add tests in `tests/unit/test_triangulation_rules.py`

## Success Criteria

✅ All files created as specified
✅ API endpoint functional: POST /v1/briefing/minister
✅ Returns JSON with markdown, headline, key_metrics, red_flags, provenance
✅ Unit tests achieve ≥90% coverage
✅ Integration tests pass with synthetic data
✅ Lint/type/secret-scan gates pass
✅ No LLMs, network, or SQL used
✅ Windows compatible
✅ Deterministic behavior verified
