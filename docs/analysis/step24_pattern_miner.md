# Step 24: Pattern Miner Implementation

**Status:** ✅ Complete  
**Date:** 2025-11-08  
**Agent:** PatternMinerAgent  
**Module:** `src/qnwis/patterns/`

## Overview

The Pattern Miner system discovers stable driver-outcome relationships across historical windows (3/6/12/24 months) and cohorts (sector, nationality, company size, wage band) using deterministic statistical methods. All results are wrapped as QueryResults with full provenance for verification and audit trails.

## Architecture

### Components

```
src/qnwis/patterns/
├── __init__.py           # Package initialization
├── metrics.py            # Pure Python statistical functions
└── miner.py              # Core pattern mining engine

src/qnwis/agents/
├── pattern_miner.py      # Agent with 3 entrypoints
└── prompts/
    └── pattern_miner_prompts.py  # Narrative templates

src/qnwis/orchestration/
├── intent_catalog.yml    # New intents: pattern.{stable_relations, seasonal_effects, driver_screen}
└── registry.py           # Intent → agent mapping
```

### Design Principles

1. **Deterministic Only**: Uses registered Query IDs via DataClient; no SQL/HTTP generation
2. **Derived Everywhere**: Every computed metric wrapped as Derived QueryResult
3. **Citations & Verification**: Complies with Steps 18–21 verification framework
4. **Bounded Compute**: Windows in {3,6,12,24}; cohort loops capped at 30
5. **Security**: Aggregates only; enforces min_support; never emits PII
6. **Performance**: O(n) per series per window; target <200ms end-to-end

## Statistical Metrics

### `src/qnwis/patterns/metrics.py`

Pure Python implementations (no numpy/scipy) for reproducibility:

#### Correlation Measures

**Pearson Correlation**
```python
def pearson(xs: List[float], ys: List[float]) -> float
```
- Linear correlation coefficient: ρ ∈ [-1, 1]
- Formula: cov(x,y) / (σ_x × σ_y)
- Use case: Linear relationships with normal distributions

**Spearman Rank Correlation**
```python
def spearman(xs: List[float], ys: List[float]) -> float
```
- Non-parametric rank correlation: ρ_s ∈ [-1, 1]
- Robust to outliers and non-linear monotonic relationships
- **Default method** for pattern mining

#### Trend Analysis

**OLS Slope**
```python
def slope(xs: List[float], ys: List[float]) -> float
```
- Ordinary Least Squares regression slope
- x typically = time indices [0, 1, 2, ...]
- Returns: units of y per time step

**Lift Percentage**
```python
def lift(a: List[float], b: List[float]) -> float
```
- Percentage lift: (mean(a) - mean(b)) / |mean(b)| × 100
- Safe for zero baselines (returns 0.0)
- Use case: Seasonal analysis, A/B comparisons

#### Quality Metrics

**Stability Score**
```python
def stability(values: List[float], windows: Tuple[int,...] = (3,6,12)) -> float
```
- Returns: stability ∈ [0, 1] where 1 = very stable
- Method: exp(-CV) where CV = coefficient of variation of windowed slopes
- Interpretation:
  - CV=0 → stability=1.0 (perfectly consistent trend)
  - CV=1 → stability=0.37 (moderate volatility)
  - CV=2 → stability=0.14 (high volatility)

**Support Score**
```python
def support(n_points: int, min_required: int) -> float
```
- Returns: support ∈ [0, 1] where 1 = sufficient data
- Linear scaling: min(n / min_required, 1.0)
- Flags low-confidence results when support < 0.7

## Core Mining Engine

### `src/qnwis/patterns/miner.py`

#### PatternSpec

Configuration for mining operations:

```python
@dataclass
class PatternSpec:
    outcome: Outcome                              # retention_rate | qatarization_rate
    drivers: List[Driver]                         # variables to test
    sector: Optional[str] = None                  # cohort filter
    window: Window = 12                           # lookback: 3|6|12|24 months
    min_support: int = 12                         # minimum observations
    method: Literal["pearson","spearman"] = "spearman"
```

#### PatternFinding

Result structure for discovered patterns:

```python
@dataclass
class PatternFinding:
    driver: Driver                                # variable name
    effect: float                                 # correlation or lift %
    support: float                                # 0..1 data sufficiency
    stability: float                              # 0..1 trend consistency
    direction: Literal["pos","neg","nonlinear","flat"]
    cohort: str                                   # sector/band label
    n: int                                        # observation count
```

#### Direction Classification

Deterministic rules (configured thresholds):

```python
|effect| < 0.15             → "flat"      # negligible
effect ≥ 0.15 and effect > 0 → "pos"       # positive association
effect ≥ 0.15 and effect < 0 → "neg"       # negative association
```

#### Composite Scoring

Rankings use: **|effect| × support × stability**

- Penalizes low data quality (support < 0.7)
- Penalizes volatile patterns (stability < 0.6)
- Rewards strong, consistent, well-supported relationships

## Agent Interface

### `src/qnwis/agents/pattern_miner.py`

#### 1. Stable Relations

**Intent:** `pattern.stable_relations`

```python
def stable_relations(
    outcome: str,
    drivers: List[str],
    sector: Optional[str] = None,
    window: int = 12,
    end_date: Optional[date] = None,
    min_support: int = 12,
    method: str = "spearman",
) -> str
```

**Purpose:** Rank drivers by effect size/stability/support over a lookback window.

**Example Query:**
```
"What factors show stable relationships with retention over 12 months?"
```

**Output Structure:**
```markdown
# Executive Summary
Top 3 drivers with exact effect sizes

# Detailed Findings
| Driver | Effect | Support | Stability | Direction | N | Composite |
|--------|--------|---------|-----------|-----------|---|-----------|
[Ranked table]

# Data Context
- Analysis window, cohort, method, thresholds

# Limitations
- Causal disclaimers, data quality notes

# Reproducibility
- Query IDs, freshness, analysis timestamp
```

**Query IDs Used:**
- `timeseries_{outcome}_{sector}_{window}m`
- `timeseries_{driver}_{sector}_{window}m` (per driver)

#### 2. Seasonal Effects

**Intent:** `pattern.seasonal_effects`

```python
def seasonal_effects(
    outcome: str,
    sector: Optional[str] = None,
    end_date: Optional[date] = None,
    min_support: int = 24,
) -> str
```

**Purpose:** Surface seasonal lift patterns by month-of-year or quarter.

**Example Query:**
```
"Are there seasonal patterns in qatarization rates?"
```

**Method:**
1. Extract multi-year time series (≥24 months)
2. Group by month-of-year (1–12)
3. Compute baseline = overall mean
4. Calculate lift % per month vs baseline
5. Rank by |lift| × support

**Output Structure:**
```markdown
# Monthly Lift Analysis
| Month | Lift (%) | Support | N | Interpretation |
|-------|----------|---------|---|----------------|
[Top 6 months]

# Insights
- Peak months: [with lift %]
- Trough months: [with lift %]
- Confidence: [based on support]

# Reproducibility
[Query IDs and freshness]
```

**Query IDs Used:**
- `timeseries_{outcome}_{sector}_36m` (multi-year for seasonality)

#### 3. Driver Screen

**Intent:** `pattern.driver_screen`

```python
def driver_screen(
    driver: str,
    outcome: str,
    cohorts: List[str],
    windows: List[int],
    sector: Optional[str] = None,
    end_date: Optional[date] = None,
    min_support: int = 12,
) -> str
```

**Purpose:** Screen a single driver across multiple cohorts and windows to find where the relationship is strongest.

**Example Query:**
```
"Screen salary as a driver of retention across sectors and time windows"
```

**Method:**
1. Loop over cohorts (capped at 30)
2. For each cohort, loop over windows [3, 6, 12, 24]
3. Compute Spearman correlation (robust to outliers)
4. Rank by composite score
5. Flag low-quality findings (support < 0.7, stability < 0.6)

**Output Structure:**
```markdown
# Top Cohort-Window Combinations
| Cohort | Window | Effect | Support | Stability | N | Composite | Notes |
|--------|--------|--------|---------|-----------|---|-----------|-------|
[Top 8 findings]

# Insights
- Strongest relationships
- Cross-window consistency
- Data quality flags

# Reproducibility
[Query IDs and freshness]
```

**Query IDs Used:**
- `timeseries_{outcome}_{cohort}_{window}m` (per cohort-window pair)
- `timeseries_{driver}_{cohort}_{window}m` (per cohort-window pair)

## Intent Routing

### Intent Catalog Additions

**`src/qnwis/orchestration/intent_catalog.yml`**

```yaml
pattern.stable_relations:
  description: "Discover stable driver-outcome relationships over historical windows"
  keywords: ["stable", "consistent", "relationship", "driver", "persistent", ...]
  
pattern.seasonal_effects:
  description: "Detect seasonal lift patterns by month or quarter"
  keywords: ["seasonal", "monthly", "quarter", "cyclical", "peak month", ...]
  
pattern.driver_screen:
  description: "Screen a driver variable across cohorts and windows"
  keywords: ["screen", "compare cohorts", "across sectors", "varies by", ...]
```

### Registry Wiring

**`src/qnwis/orchestration/registry.py`**

```python
pattern_miner_agent = PatternMinerAgent(client)

registry.register("pattern.stable_relations", pattern_miner_agent, "stable_relations")
registry.register("pattern.seasonal_effects", pattern_miner_agent, "seasonal_effects")
registry.register("pattern.driver_screen", pattern_miner_agent, "driver_screen")
```

## Performance Characteristics

### Computational Complexity

| Operation | Time Complexity | Space Complexity |
|-----------|-----------------|------------------|
| Pearson/Spearman | O(n) | O(1) |
| Slope (OLS) | O(n) | O(1) |
| Stability | O(n × w) where w = window sizes | O(w) |
| Stable Relations | O(d × n) where d = drivers | O(d × n) |
| Seasonal Effects | O(n) | O(12) months |
| Driver Screen | O(c × w × n) where c = cohorts, w = windows | O(c × w × n) |

### Target Performance

- **Single pattern analysis:** <50ms
- **Multi-driver stable relations:** <100ms (5 drivers)
- **Seasonal analysis:** <60ms (36-month series)
- **Cross-cohort screen:** <200ms (10 cohorts × 4 windows)

### Bounded Execution

Safety limits:
- **Max cohorts:** 30 (hardcoded in PatternMiner)
- **Valid windows:** {3, 6, 12, 24} months only
- **Min support:** Configurable, default 12 observations
- **Max series length:** No hard limit, but typical <200 points

## Data Requirements

### Query Registry Needs

Pattern Miner expects these Query IDs to be registered:

#### Time Series Queries

```yaml
timeseries_retention_rate_{sector}_{window}m:
  description: "Monthly retention rate time series"
  fields: [date, sector, retention_rate, n_employees]
  
timeseries_qatarization_rate_{sector}_{window}m:
  description: "Monthly qatarization rate time series"
  fields: [date, sector, qatarization_rate, n_qatari, n_total]
  
timeseries_avg_salary_{sector}_{window}m:
  description: "Monthly average salary time series"
  fields: [date, sector, avg_salary, n_employees]
  
timeseries_wage_spread_{sector}_{window}m:
  description: "Monthly wage spread (P90/P10) time series"
  fields: [date, sector, wage_spread]
  
timeseries_promotion_rate_{sector}_{window}m:
  description: "Monthly promotion rate time series"
  fields: [date, sector, promotion_rate, n_promotions, n_eligible]
```

### Field Conventions

Time series QueryResults must include:
- **Date field:** `date` or `month` (ISO format: YYYY-MM-DD)
- **Value field:** `value`, `rate`, metric-specific name (e.g., `retention_rate`)
- **Cohort field:** `sector`, `nationality`, `wage_band` (optional, for filtering)
- **Count field:** `n`, `n_employees`, `n_observations` (for support calculation)

## Verification & Audit

### Derived Result Wrapping

All computed patterns wrapped via `make_derived_query_result()`:

```python
derived_result = make_derived_query_result(
    operation="stable_relations",
    params={
        "outcome": outcome,
        "drivers": drivers,
        "sector": sector,
        "window": window,
        "method": method,
    },
    rows=findings_rows,
    sources=source_qids,  # List of input Query IDs
    unit="correlation",
)
```

**Generated Query ID Format:**
```
derived_stable_relations_a3f8b9c2
derived_seasonal_effects_7d2e4f1a
derived_driver_screen_9c1a3e5b
```

### Citation Format

All narratives include:
```
(QID=derived_stable_relations_a3f8b9c2)
```

After every numeric claim, enabling downstream verification.

### Audit Trail

Logged events:
- `INFO: Would fetch Query ID: timeseries_retention_rate_Construction_12m`
- `INFO: Pattern mining complete: 5 findings, 3 drivers, 12-month window`
- `ERROR: Invalid window 18. Must be 3, 6, 12, or 24 months.`

## Security & Privacy

### Aggregation Enforcement

- **No row-level data:** All time series are pre-aggregated
- **Min support threshold:** Enforced in `PatternSpec` (default: 12 observations)
- **Cohort minimum:** If cohort has <min_support points, excluded from results

### No Causal Language

Prompts explicitly forbid:
- ❌ "salary causes retention to increase"
- ✅ "salary is positively associated with retention (ρ=0.65)"

### No Derived Variables

Agent does not infer sector, nationality, or wage band. These must be provided as input parameters or present in QueryResult rows.

## Testing Strategy

### Unit Tests

**`tests/unit/patterns/test_metrics.py`**
- Pearson correlation: perfect linear, inverse, zero variance cases
- Spearman: outlier robustness, rank ties
- Slope: positive/negative/flat trends
- Lift: zero baseline handling, percentage accuracy
- Stability: perfect linear vs volatile series
- Support: boundary conditions (0, min_required, 2×min_required)

**`tests/unit/patterns/test_miner.py`**
- Direction classification: flat/pos/neg thresholds
- Series extraction: date parsing, sector filtering
- Series alignment: mismatched lengths
- Composite scoring: effect × support × stability ordering

**`tests/unit/agents/test_pattern_miner.py`**
- Stable relations: narrative formatting, citation inclusion
- Seasonal effects: month grouping, lift calculation
- Driver screen: cohort looping, window validation
- Error handling: invalid windows, missing data

### Integration Tests

**`tests/integration/agents/test_pattern_miner_integration.py`**
- End-to-end stable relations with mock time series
- Seasonal analysis with multi-year data
- Driver screening across 3 cohorts × 4 windows
- Derived result verification (query_id stability, provenance)

### Expected Coverage

Target: **>90%** for new modules
- `metrics.py`: 95% (pure functions, easy to test)
- `miner.py`: 90% (core engine)
- `pattern_miner.py`: 90% (agent methods)

## Example Usage

### Programmatic

```python
from src.qnwis.agents.base import DataClient
from src.qnwis.agents.pattern_miner import PatternMinerAgent
from datetime import date

# Initialize
client = DataClient(queries_dir="data/queries")
agent = PatternMinerAgent(client)

# Stable relations analysis
narrative = agent.stable_relations(
    outcome="retention_rate",
    drivers=["avg_salary", "promotion_rate", "wage_spread"],
    sector="Construction",
    window=12,
    end_date=date(2024, 12, 31),
    min_support=12,
    method="spearman",
)
print(narrative)

# Seasonal effects
seasonal_narrative = agent.seasonal_effects(
    outcome="qatarization_rate",
    sector="Finance",
    end_date=date(2024, 12, 31),
    min_support=24,
)
print(seasonal_narrative)

# Driver screening
screen_narrative = agent.driver_screen(
    driver="avg_salary",
    outcome="retention_rate",
    cohorts=["Construction", "Finance", "Healthcare"],
    windows=[6, 12, 24],
    min_support=12,
)
print(screen_narrative)
```

### Natural Language Queries

Through orchestration router:

```
User: "What factors show stable relationships with retention in Construction?"
→ Intent: pattern.stable_relations
→ Agent: PatternMinerAgent.stable_relations(...)

User: "Are there seasonal patterns in hiring?"
→ Intent: pattern.seasonal_effects
→ Agent: PatternMinerAgent.seasonal_effects(...)

User: "Screen salary as a driver across sectors"
→ Intent: pattern.driver_screen
→ Agent: PatternMinerAgent.driver_screen(...)
```

## Formulas Reference

### Pearson Correlation

$$
\rho = \frac{\sum_{i=1}^n (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum_{i=1}^n (x_i - \bar{x})^2} \sqrt{\sum_{i=1}^n (y_i - \bar{y})^2}}
$$

### Spearman Rank Correlation

$$
\rho_s = \rho(\text{rank}(x), \text{rank}(y))
$$

Apply Pearson to rank-transformed data.

### OLS Slope

$$
\beta = \frac{\sum_{i=1}^n (x_i - \bar{x})(y_i - \bar{y})}{\sum_{i=1}^n (x_i - \bar{x})^2}
$$

Where x = time indices [0, 1, ..., n-1]

### Lift Percentage

$$
\text{lift} = \frac{\bar{a} - \bar{b}}{|\bar{b}|} \times 100
$$

### Stability Score

$$
\text{stability} = e^{-CV}
$$

Where CV = coefficient of variation of windowed slopes:

$$
CV = \frac{\sigma_{\text{slopes}}}{\mu_{\text{slopes}}}
$$

### Composite Score

$$
\text{composite} = |\text{effect}| \times \text{support} \times \text{stability}
$$

## Future Enhancements

### Phase 2 Candidates

1. **Non-linear pattern detection:**
   - Polynomial regression (degree 2-3)
   - Change-point detection within relationships
   
2. **Multi-driver interactions:**
   - Two-way interaction terms
   - Conditional correlations (e.g., salary effect varies by size)
   
3. **Lag analysis:**
   - Test lagged correlations (e.g., salary at t-1 vs retention at t)
   - Cross-correlation function (CCF)
   
4. **Confidence intervals:**
   - Bootstrap CI for correlation estimates
   - Permutation tests for significance
   
5. **Cohort discovery:**
   - Automatic segmentation (k-means on driver space)
   - Hierarchical cohort analysis

### Known Limitations

- **Assumes stationarity:** Does not detect regime changes within window
- **Linear/monotonic only:** Misses U-shaped or threshold relationships
- **No confounders:** Observed correlations may be spurious
- **Fixed windows:** Cannot adaptively select optimal lookback period
- **No missing data handling:** Assumes complete time series

## Runbook

### Deployment Checklist

- [ ] Query registry includes all `timeseries_*` query definitions
- [ ] Time series queries return date + value + cohort fields
- [ ] Min support thresholds configured per use case
- [ ] Intent catalog keywords aligned with user vocabulary
- [ ] Registry wiring tested in integration tests
- [ ] Performance benchmarks met (<200ms typical)
- [ ] Documentation reviewed by domain experts

### Troubleshooting

**Symptom:** "No stable relationships found"
- **Check:** min_support too high? Try lowering to 6-8 observations
- **Check:** Window too short? Increase to 12 or 24 months
- **Check:** Relationships genuinely flat? Review scatter plots

**Symptom:** Low support scores (<0.7)
- **Cause:** Insufficient data in time series
- **Fix:** Aggregate to quarterly instead of monthly, or extend window

**Symptom:** Low stability scores (<0.6)
- **Cause:** Volatile time series with inconsistent trends
- **Fix:** Apply smoothing (moving average) before analysis, or flag as "unstable relationship"

**Symptom:** "Invalid window" error
- **Cause:** Window not in {3, 6, 12, 24}
- **Fix:** Round to nearest valid window or reject request

## References

- Steps 18–21: Verification & Audit framework
- Step 19–20: Numeric and result verification
- Time Machine Agent: Historical time series handling
- Pattern Detective Agent: Anomaly and correlation detection (complementary)

---

**Implementation Date:** 2025-11-08  
**Next Review:** After production deployment with real query registry  
**Owner:** QNWIS Analytics Team
