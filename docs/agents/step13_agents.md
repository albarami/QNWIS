# Step 13: Pattern Detective & National Strategy Agents

**Implementation Date:** November 2025  
**Status:** ✅ Complete  
**Dependencies:** Deterministic Data Layer (Steps 3-5), Agent Base (Step 9)

---

## Overview

This document describes the implementation of two advanced analytical agents:

1. **PatternDetectiveAgent** (Agent 4): Discovers correlations, detects anomalies, investigates root causes, and identifies best practices
2. **NationalStrategyAgent** (Agent 5): Provides GCC benchmarking, talent competition assessment, and Vision 2030 alignment tracking

Both agents strictly adhere to the **Deterministic Data Layer** principles:
- ✅ No direct SQL/database access
- ✅ All data via `DataClient.run(query_id)`
- ✅ All computed results wrapped in `QueryResult` format
- ✅ Full provenance and verification support

---

## Architecture

### Data Flow

```
User Request
    ↓
Agent Method (e.g., detect_anomalous_retention)
    ↓
DataClient.run(query_id) → QueryResult (source data)
    ↓
Pure Python Statistics (pearson, spearman, z_scores, winsorize)
    ↓
make_derived_query_result() → QueryResult (computed data)
    ↓
AgentReport with Evidence + Insights
    ↓
Verification Layer (can trace all numbers back to sources)
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| `PatternDetectiveAgent` | Correlation & anomaly analysis | `/src/qnwis/agents/pattern_detective.py` |
| `NationalStrategyAgent` | Strategic benchmarking | `/src/qnwis/agents/national_strategy.py` |
| `statistics.py` | Pure Python stats functions | `/src/qnwis/agents/utils/statistics.py` |
| `derived_results.py` | QueryResult wrapper | `/src/qnwis/agents/utils/derived_results.py` |
| Prompt templates | LLM guidance (optional) | `/src/qnwis/agents/prompts/*.py` |

---

## Agent 4: PatternDetectiveAgent

### Capabilities

#### 1. `detect_anomalous_retention()`

**Purpose:** Find sectors with statistically unusual attrition rates using z-score analysis.

**Method:**
```python
report = agent.detect_anomalous_retention(
    z_threshold=2.5,      # Anomaly threshold (default 2.5 std devs)
    min_sample_size=3,    # Minimum sectors required
)
```

**Algorithm:**
1. Fetch `syn_attrition_by_sector_latest`
2. Winsorize values (clip top/bottom 5% to handle extremes)
3. Calculate z-scores
4. Flag sectors exceeding threshold

**Output:**
```python
{
    "agent": "PatternDetective",
    "findings": [
        {
            "title": "Attrition anomaly detection (z-score > 2.5)",
            "summary": "Found 2 sectors with anomalous attrition rates out of 10 total.",
            "metrics": {
                "anomaly_count": 2,
                "total_sectors": 10,
                "threshold": 2.5,
                "max_z_score": 3.12
            },
            "evidence": [
                {"query_id": "syn_attrition_by_sector_latest", ...},
                {"query_id": "derived_z_score_anomaly_detection_a3f7c8d2", ...}
            ]
        }
    ]
}
```

**Use Cases:**
- Identify sectors losing talent at abnormal rates
- Target retention interventions
- Early warning for emerging crises

---

#### 2. `find_correlations()`

**Purpose:** Discover relationships between qatarization and attrition rates.

**Method:**
```python
report = agent.find_correlations(
    method="spearman",         # "pearson" or "spearman"
    min_correlation=0.5,       # Significance threshold
    min_sample_size=5,         # Minimum sectors required
)
```

**Algorithm:**
1. Fetch `syn_qatarization_by_sector_latest` and `syn_attrition_by_sector_latest`
2. Match sectors across both datasets
3. Calculate Pearson (linear) or Spearman (rank) correlation
4. Compare to significance threshold

**Statistical Notes:**
- **Pearson:** Assumes linear relationship, sensitive to outliers
- **Spearman:** Robust to non-linearity and outliers (recommended default)
- Returns 0.0 for zero-variance data (no error)

**Output:**
```python
{
    "metrics": {
        "spearman_correlation": 0.68,
        "sample_size": 12
    },
    "summary": "Spearman correlation between qatarization and attrition: 0.680 (n=12). Positive relationship exceeds threshold (0.5)."
}
```

**Interpretation:**
- **r > 0.7:** Strong correlation
- **0.5 < r < 0.7:** Moderate correlation
- **r < 0.5:** Weak/no correlation
- **Correlation ≠ Causation** (always acknowledged in findings)

---

#### 3. `identify_root_causes()`

**Purpose:** Investigate drivers of high attrition by comparing sector characteristics.

**Method:**
```python
report = agent.identify_root_causes(
    top_n=3,  # Number of top/bottom sectors to compare
)
```

**Algorithm:**
1. Fetch attrition and qatarization data
2. Sort sectors by attrition rate
3. Compare top N (highest attrition) vs bottom N (lowest attrition)
4. Calculate average qatarization difference

**Output:**
```python
{
    "metrics": {
        "high_attrition_qat_avg": 15.3,
        "low_attrition_qat_avg": 42.7,
        "qatarization_diff": -27.4
    },
    "summary": "High attrition sectors (top 3) have average qatarization of 15.3%, vs 42.7% for low attrition sectors. Difference: -27.4 percentage points. Note: Correlation does not imply causation."
}
```

**Use Cases:**
- Hypothesis generation for retention interventions
- Identify potential leverage points
- Inform policy experiments

**Limitations:**
- Observational data only (confounding variables possible)
- No causal proof (acknowledges in every report)
- Small sample sizes reduce reliability

---

#### 4. `best_practices()`

**Purpose:** Surface characteristics of top-performing sectors.

**Method:**
```python
report = agent.best_practices(
    metric="qatarization",  # or "retention"
    top_n=5,                # Number of leaders to highlight
)
```

**Algorithm:**
1. Fetch relevant metric data
2. Sort sectors by performance
3. Extract top N performers
4. Calculate performance gap vs overall average

**Output:**
```python
{
    "metrics": {
        "top_5_average": 65.2,
        "overall_average": 42.1,
        "performance_gap": 23.1
    },
    "summary": "Top 5 sectors average 65.2% vs overall 42.1%."
}
```

**Use Cases:**
- Benchmark against high performers
- Identify replicable practices
- Set aspirational targets

---

## Agent 5: NationalStrategyAgent

### Capabilities

#### 1. `gcc_benchmark()`

**Purpose:** Compare Qatar's unemployment rate to GCC peer countries.

**Method:**
```python
report = agent.gcc_benchmark(
    min_countries=3,  # Minimum GCC countries required
)
```

**Algorithm:**
1. Fetch `syn_unemployment_rate_gcc_latest`
2. Extract unemployment rates for all GCC countries
3. Rank countries (low unemployment = better)
4. Calculate Qatar's rank and gap to GCC average

**Output:**
```python
{
    "metrics": {
        "gcc_countries_count": 6,
        "gcc_average": 7.8,
        "qatar_rank": 2,
        "qatar_rate": 6.2,
        "gap_to_average": -1.6
    },
    "summary": "Qatar ranks 2/6 in GCC unemployment rate (6.2%). GCC average: 7.8%. Gap to average: -1.6 percentage points."
}
```

**Use Cases:**
- Regional competitiveness tracking
- Policy benchmarking
- Ministry reporting

---

#### 2. `talent_competition_assessment()`

**Purpose:** Identify sectors under competitive pressure from regional talent markets.

**Method:**
```python
report = agent.talent_competition_assessment(
    focus_metric="attrition_percent",
)
```

**Algorithm:**
1. Fetch attrition data by sector
2. Calculate sector-wide average attrition
3. Classify sectors:
   - **High:** > 1.5x average (intense competition)
   - **Moderate:** > average (some pressure)
   - **Low:** ≤ average (stable)

**Output:**
```python
{
    "metrics": {
        "average_attrition": 12.5,
        "high_competition_sectors": 3,
        "total_sectors": 10,
        "highest_attrition": 22.4,
        "highest_attrition_sector": "Healthcare"
    },
    "summary": "Talent competition assessment across 10 sectors. Average attrition: 12.5%. 3 sectors face high competitive pressure (>1.5x average)."
}
```

**Use Cases:**
- Prioritize retention programs
- Salary competitiveness reviews
- Cross-border talent flow monitoring

---

#### 3. `vision2030_alignment()`

**Purpose:** Track progress toward Qatar Vision 2030 qatarization targets.

**Method:**
```python
report = agent.vision2030_alignment(
    target_year=2030,
    current_year=2024,
)
```

**Algorithm:**
1. Fetch current qatarization rates across all sectors
2. Calculate overall national qatarization rate
3. Compare to Vision 2030 target (30% private sector baseline)
4. Calculate:
   - Gap to target (percentage points)
   - Required annual growth rate
   - Risk level (on_track / moderate / high)

**Vision 2030 Targets (Illustrative):**
```python
VISION_2030_TARGETS = {
    "qatarization_public_sector": 90.0,    # 90% in public sector
    "qatarization_private_sector": 30.0,   # 30% in private sector
    "unemployment_rate_qataris": 2.0,      # <2% Qatari unemployment
    "female_labor_participation": 45.0,    # 45% female participation
}
```

**Output:**
```python
{
    "metrics": {
        "current_qatarization": 18.3,
        "target_qatarization": 30.0,
        "gap_percentage_points": 11.7,
        "required_annual_growth": 1.95,
        "years_remaining": 6
    },
    "summary": "Vision 2030 qatarization alignment: Current 18.3% vs target 30.0%. Gap: 11.7 percentage points (39.0% of target). Requires 1.95 pp annual growth over 6 years. Risk level: high."
}
```

**Risk Levels:**
- **on_track:** Gap ≤ 0 (meeting or exceeding target)
- **moderate:** Gap < 20% of target
- **high:** Gap ≥ 20% of target

**Use Cases:**
- Executive dashboards
- Policy planning
- Progress monitoring for strategic initiatives

---

## Statistical Utilities

### `statistics.py` Functions

All functions are **pure Python** (no external dependencies) and **deterministic**.

#### `pearson(xs, ys) -> float`

Pearson correlation coefficient (linear relationship).

**Formula:** `r = cov(X,Y) / (σ_X * σ_Y)`

**Returns:** Value in [-1.0, 1.0], or 0.0 if zero variance

**Example:**
```python
from src.qnwis.agents.utils.statistics import pearson

x = [1, 2, 3, 4, 5]
y = [2, 4, 6, 8, 10]
r = pearson(x, y)  # → 1.0 (perfect positive correlation)
```

---

#### `spearman(xs, ys) -> float`

Spearman rank correlation (monotonic relationship).

**Method:** Calculates Pearson correlation on ranked values

**Returns:** Value in [-1.0, 1.0], or 0.0 if zero variance

**When to use:** Prefer over Pearson when:
- Non-linear relationships
- Outliers present
- Ordinal data

**Example:**
```python
from src.qnwis.agents.utils.statistics import spearman

x = [1, 2, 3, 4, 100]  # Outlier!
y = [2, 4, 6, 8, 10]
r = spearman(x, y)  # → 0.9 (robust to outlier)
```

---

#### `z_scores(values) -> List[float]`

Standardize values (mean=0, std=1).

**Formula:** `z = (x - μ) / σ`

**Returns:** List of z-scores, or all zeros if std=0

**Example:**
```python
from src.qnwis.agents.utils.statistics import z_scores

values = [10, 12, 14, 16, 18]
z = z_scores(values)  # → [-1.41, -0.71, 0.0, 0.71, 1.41]

# Interpretation:
# |z| > 2.0 → extreme outlier
# |z| > 1.5 → moderate outlier
```

---

#### `winsorize(values, p=0.01) -> List[float]`

Clip extreme values at percentiles (robust outlier handling).

**Method:** Replace values below p-th percentile with p-th percentile value, same for (1-p)-th percentile

**Default:** Clips bottom 1% and top 1%

**Example:**
```python
from src.qnwis.agents.utils.statistics import winsorize

values = [1, 2, 3, 4, 100]  # 100 is extreme
clipped = winsorize(values, p=0.10)  # → [1, 2, 3, 4, 4]
```

**Use case:** Apply before z-score analysis to prevent single outliers from dominating

---

### `derived_results.py`

#### `make_derived_query_result()`

Wraps computed data into verifiable `QueryResult` format.

**Purpose:** Ensure all agent outputs (even calculations) can be traced and verified

**Signature:**
```python
def make_derived_query_result(
    operation: str,                      # e.g., "pearson_correlation"
    params: dict[str, Any],              # Computation parameters
    rows: list[dict[str, Any]],          # Computed results
    sources: list[str],                  # Source query_ids used
    freshness_like: dict[str, datetime] | None = None,
    unit: str = "unknown",
) -> QueryResult:
```

**Example:**
```python
from src.qnwis.agents.utils.derived_results import make_derived_query_result

# After calculating correlation between two datasets
result = make_derived_query_result(
    operation="spearman_correlation",
    params={"variable_x": "qatarization", "variable_y": "attrition"},
    rows=[
        {"sector": "Finance", "qatarization": 45.2, "attrition": 8.3},
        {"sector": "Energy", "qatarization": 67.1, "attrition": 4.2},
    ],
    sources=["syn_qatarization_by_sector_latest", "syn_attrition_by_sector_latest"],
)

# Result has:
# - Stable query_id: "derived_spearman_correlation_a3f7c8d2"
# - Full provenance: source query IDs, computation method
# - Verification-ready: can be passed to verification layer
```

**Query ID Generation:**
- Stable hash of operation + params
- Format: `derived_{operation}_{hash8}`
- Ensures reproducibility

---

## Usage Examples

### Example 1: Detect Attrition Anomalies

```python
from src.qnwis.agents.base import DataClient
from src.qnwis.agents.pattern_detective import PatternDetectiveAgent

# Initialize
client = DataClient(queries_dir="data/queries")
agent = PatternDetectiveAgent(client)

# Run anomaly detection
report = agent.detect_anomalous_retention(z_threshold=2.0)

# Access findings
for finding in report.findings:
    print(f"Title: {finding.title}")
    print(f"Summary: {finding.summary}")
    print(f"Metrics: {finding.metrics}")
    
    # Trace evidence
    for evidence in finding.evidence:
        print(f"  Query ID: {evidence.query_id}")
        print(f"  Dataset: {evidence.dataset_id}")
```

**Output:**
```
Title: Attrition anomaly detection (z-score > 2.0)
Summary: Found 3 sectors with anomalous attrition rates out of 12 total.
Metrics: {'anomaly_count': 3, 'total_sectors': 12, 'threshold': 2.0, 'max_z_score': 2.87}
  Query ID: syn_attrition_by_sector_latest
  Dataset: aggregates/attrition_by_sector.csv
  Query ID: derived_z_score_anomaly_detection_a3f7c8d2
  Dataset: derived_z_score_anomaly_detection
```

---

### Example 2: GCC Benchmarking

```python
from src.qnwis.agents.national_strategy import NationalStrategyAgent

agent = NationalStrategyAgent(client)
report = agent.gcc_benchmark()

finding = report.findings[0]
print(f"{finding.summary}")
print(f"Qatar Rank: {finding.metrics['qatar_rank']}/{ finding.metrics['gcc_countries_count']}")
print(f"Qatar Rate: {finding.metrics['qatar_rate']}%")
print(f"GCC Average: {finding.metrics['gcc_average']}%")
```

**Output:**
```
Qatar ranks 2/6 in GCC unemployment rate (6.2%). GCC average: 7.8%. Gap to average: -1.6 percentage points.
Qatar Rank: 2/6
Qatar Rate: 6.2%
GCC Average: 7.8%
```

---

### Example 3: Vision 2030 Tracking

```python
agent = NationalStrategyAgent(client)
report = agent.vision2030_alignment(target_year=2030, current_year=2024)

finding = report.findings[0]
print(f"Current: {finding.metrics['current_qatarization']}%")
print(f"Target: {finding.metrics['target_qatarization']}%")
print(f"Gap: {finding.metrics['gap_percentage_points']} pp")
print(f"Required Growth: {finding.metrics['required_annual_growth']} pp/year")
```

**Output:**
```
Current: 18.3%
Target: 30.0%
Gap: 11.7 pp
Required Growth: 1.95 pp/year
```

---

## Operational Limits & Guardrails

### Sample Size Requirements

| Method | Minimum Sample | Reason |
|--------|----------------|--------|
| `pearson()` / `spearman()` | n ≥ 2 | Need variance to calculate correlation |
| `z_scores()` | n ≥ 2 | Need std deviation for standardization |
| `detect_anomalous_retention()` | n ≥ 3 | Statistical reliability |
| `find_correlations()` | n ≥ 5 | Correlation significance |
| `identify_root_causes()` | n ≥ 2×top_n | Need comparison groups |

**Behavior when below minimum:**
- Returns empty `AgentReport` with warning
- No partial results (fail-safe)

---

### Zero Variance Handling

**Problem:** Division by zero when calculating correlation/z-scores

**Solutions:**
1. **Pearson/Spearman:** Return 0.0 (no correlation)
2. **Z-scores:** Return all zeros (no standardization possible)
3. **Winsorize:** Return original values unchanged

**Example:**
```python
# All sectors have same attrition rate
values = [10.0, 10.0, 10.0, 10.0]
z = z_scores(values)  # → [0.0, 0.0, 0.0, 0.0] (no error)
```

---

### Privacy Compliance

**Rule:** Never output person_id or individual names

**Enforcement:**
- All queries use aggregated data only
- No row-level employee queries exposed
- Minimum aggregation thresholds in query definitions

**Verification:**
```bash
# Check queries for privacy violations
grep -r "person_id" src/qnwis/data/queries/*.yaml
# Should return: (empty)
```

---

### Performance Considerations

| Operation | Complexity | Typical Runtime |
|-----------|------------|-----------------|
| `detect_anomalous_retention()` | O(n) | <50ms for n=20 sectors |
| `find_correlations()` | O(n) | <100ms for n=20 sectors |
| `identify_root_causes()` | O(n log n) | <150ms (sorting dominates) |
| `gcc_benchmark()` | O(n log n) | <100ms for n=6 countries |
| `vision2030_alignment()` | O(n) | <75ms for n=20 sectors |

**Optimization:**
- Use pre-aggregated `*_latest` queries (cached)
- Avoid in-memory joins (use dict lookups)
- No database roundtrips inside loops

---

## Testing Strategy

### Unit Tests Required

Create tests in `tests/unit/`:

1. **`test_agent_pattern_detective.py`**
   - Test each method with synthetic data
   - Edge cases: zero variance, small samples, missing sectors
   - Verify Evidence chain completeness

2. **`test_agent_national_strategy.py`**
   - Test GCC benchmarking with mock data
   - Vision 2030 gap calculations
   - Risk level classification logic

3. **`test_utils_statistics.py`**
   - Pearson/Spearman correctness
   - Z-score normalization
   - Winsorization boundary conditions
   - Zero variance handling

4. **`test_utils_derived_results.py`**
   - QueryResult wrapper correctness
   - Stable query_id generation
   - Provenance chain integrity

### Example Test

```python
# tests/unit/test_utils_statistics.py
from src.qnwis.agents.utils.statistics import pearson, z_scores

def test_pearson_perfect_correlation():
    x = [1, 2, 3, 4, 5]
    y = [2, 4, 6, 8, 10]
    assert abs(pearson(x, y) - 1.0) < 0.001

def test_z_scores_zero_variance():
    values = [5.0, 5.0, 5.0]
    result = z_scores(values)
    assert result == [0.0, 0.0, 0.0]  # No error, graceful handling
```

### Integration Tests

Create in `tests/integration/`:

```python
# tests/integration/test_step13_agents.py
from src.qnwis.agents.base import DataClient
from src.qnwis.agents.pattern_detective import PatternDetectiveAgent

def test_pattern_detective_end_to_end():
    client = DataClient()
    agent = PatternDetectiveAgent(client)
    
    report = agent.detect_anomalous_retention()
    
    assert report.agent == "PatternDetective"
    assert len(report.findings) > 0
    
    # Verify evidence chain
    for finding in report.findings:
        assert len(finding.evidence) >= 1
        for evidence in finding.evidence:
            assert evidence.query_id.startswith(("syn_", "derived_"))
```

---

## Verification & Reproducibility

Every agent method returns:

1. **Executive Summary:** Natural language findings
2. **Metrics:** Key numbers with citations
3. **Evidence Chain:** All source query IDs
4. **Reproducibility Snippet:** Method + params

**Example Verification:**
```python
# From report
finding = report.findings[0]
evidence = finding.evidence[0]

# Re-run source query
client = DataClient()
original = client.run(evidence.query_id)

# Verify freshness
print(f"Data as of: {original.freshness.asof_date}")
print(f"Source: {original.provenance.locator}")

# Numbers in finding.metrics must exist in original.rows
```

---

## Prompt Templates (Optional)

Located in `src/qnwis/agents/prompts/`:
- `pattern_detective_prompts.py`
- `national_strategy_prompts.py`

**Usage:** If integrating LLM-based interpretation layer

**Key principles enforced:**
- "Use ONLY numbers from QueryResult"
- "Cite query_id for every claim"
- "Never round beyond source precision"
- "Distinguish correlation from causation"

---

## Known Limitations

1. **Observational Data Only**
   - No causal inference (correlation ≠ causation)
   - Confounding variables not controlled
   - Temporal data limited (mostly cross-sectional)

2. **GCC Data Availability**
   - Relies on `syn_unemployment_rate_gcc_latest` query
   - Real World Bank API integration pending (Step 7 follow-up)
   - Limited to unemployment metric currently

3. **Vision 2030 Targets**
   - Hardcoded in `national_strategy.py` (should be externalized to config)
   - Illustrative targets (need official Ministry confirmation)

4. **Sample Sizes**
   - Sector-level aggregation = small n (10-20 typically)
   - Limits statistical power for some analyses
   - Correlation thresholds conservative (0.5 default)

---

## Future Enhancements

### Short-term (Next Sprint)
- [ ] Extend `gcc_benchmark()` to support multiple metrics (not just unemployment)
- [ ] Add time-series trending to `vision2030_alignment()`
- [ ] Externalize Vision 2030 targets to YAML config
- [ ] Add `detect_salary_anomalies()` method

### Medium-term
- [ ] Integrate real World Bank API (replace syn_ queries)
- [ ] Add GCC labor force participation benchmarking
- [ ] Implement sector-specific best practice deep dives
- [ ] Add temporal anomaly detection (detect sudden changes)

### Long-term
- [ ] Causal inference methods (diff-in-diff, RCT analysis if data available)
- [ ] Predictive models (retention risk scoring)
- [ ] Network analysis (sector transition flows)

---

## Success Criteria

✅ **Met if:**
1. All 7 methods execute without errors on synthetic data
2. Every finding includes ≥1 Evidence object with valid query_id
3. Re-running source queries reproduces reported metrics
4. Unit tests achieve >90% code coverage
5. Integration tests pass with real query definitions
6. No SQL/HTTP calls in agent code (verified by code review)
7. Documentation complete with examples

---

## References

- [Deterministic Data Layer Specification](../DETERMINISTIC_DATA_LAYER_SPECIFICATION.md)
- [Implementation Roadmap - Step 13](../IMPLEMENTATION_ROADMAP.md#step-13)
- [Agent Base Classes](../../src/qnwis/agents/base.py)
- [Query Registry](../../src/qnwis/data/deterministic/registry.py)

---

**Document Version:** 1.0  
**Last Updated:** November 2025  
**Maintainer:** LMIS Development Team
