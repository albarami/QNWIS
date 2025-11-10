# Step 23: Time Machine Module - Historical Time-Series Analysis

**Status**: ✅ Implementation Complete  
**Version**: 1.0  
**Date**: 2025-11-08  
**Objective**: Production-grade time-series analytics with seasonal baselines, trend detection, and structural break identification

---

## Overview

The Time Machine module provides deterministic historical analytics for Qatar's Labour Market Intelligence System. It analyzes monthly time-series data to:
- Compute seasonal baselines and detect anomalies
- Calculate YoY/QtQ growth rates and momentum indicators
- Identify structural breaks and change points
- Generate citation-ready narratives with reproducibility snippets

All analysis uses approved time-series accessed via `DataClient` with query IDs. No direct SQL or HTTP access.

---

## Architecture

### Module Structure

```
src/qnwis/analysis/
├── trend_utils.py         # Math utilities (YoY, QtQ, EWMA, index-100, slopes)
├── change_points.py       # CUSUM & z-score break detection
└── baselines.py           # Seasonal baseline & anomaly bands

src/qnwis/agents/
├── time_machine.py        # TimeMachineAgent with 3 report methods
└── prompts/
    └── time_machine_prompts.py  # LLM prompts with strict citation rules

src/qnwis/cli/
└── qnwis_time.py         # CLI for offline report generation

src/qnwis/orchestration/
├── intent_catalog.yml    # Added time.baseline, time.trend, time.breaks
└── registry.py           # Registered TimeMachineAgent methods
```

### Data Flow

```
User Query → Router → TimeMachineAgent
                ↓
        DataClient.run(query_id)
                ↓
        Trend/Baseline/Break Analysis
                ↓
        make_derived_query_result()
                ↓
        Narrative + Citations + Derived QIDs
```

---

## Core Components

### 1. Trend Utilities (`trend_utils.py`)

Pure-Python implementations guarding against edge cases:

#### Functions

```python
pct_change(curr, prev) → Optional[float]
```
- Safe percentage change calculation
- Returns `None` if prev is 0

```python
yoy(series, period=12) → List[Optional[float]]
```
- Year-over-year percentage changes
- Pads first `period` values with `None`

```python
qtq(series, period=3) → List[Optional[float]]
```
- Quarter-over-quarter percentage changes
- Pads first `period` values with `None`

```python
ewma(series, alpha=0.25) → List[float]
```
- Exponentially weighted moving average
- Alpha ∈ (0, 1]: lower = more smoothing

```python
index_100(series, base_idx) → List[Optional[float]]
```
- Normalize to index 100 at base period
- Returns `None` where base value is 0

```python
window_slopes(series, windows=(3,6,12)) → List[Tuple[int, Optional[float]]]
```
- Linear slopes over trailing windows using least squares
- Indicates momentum/acceleration

#### Example Usage

```python
from src.qnwis.analysis.trend_utils import yoy, ewma, window_slopes

# Compute YoY growth
monthly_values = [100, 102, 105, 108, 110, 112, ...]
yoy_pct = yoy(monthly_values, period=12)

# Smooth with EWMA
smoothed = ewma(monthly_values, alpha=0.25)

# Check momentum
slopes = window_slopes(monthly_values, windows=(3, 6, 12))
# Returns: [(3, 2.1), (6, 1.8), (12, 1.5)]
```

---

### 2. Change-Point Detection (`change_points.py`)

Detects structural breaks and outliers using statistical methods:

#### Functions

```python
cusum_breaks(series, k=1.0, h=5.0) → List[int]
```
- CUSUM (Cumulative Sum) two-sided break detection
- `k`: drift parameter (0.5-2.0)
- `h`: threshold (4.0-6.0)
- Returns indices of detected breaks

```python
zscore_outliers(series, z=2.5) → List[int]
```
- Z-score outlier detection
- `z`: threshold (typical 2.0-3.0)
- Returns indices where |z-score| ≥ threshold

```python
summarize_breaks(series) → Dict[str, Optional[float]]
```
- Aggregate break summary
- Returns: first_break_idx, n_breaks, max_jump_abs, max_jump_pct

#### Math Notes

**CUSUM Algorithm**:
1. Normalize series: `z_i = (x_i - μ) / σ`
2. Update statistics:
   - `S_high = max(0, S_high + z_i - k)`
   - `S_low = max(0, S_low - z_i - k)`
3. Detect when `S_high > h` or `S_low > h`

**Z-score Method**:
1. Compute mean `μ` and std `σ`
2. For each point: `z_i = (x_i - μ) / σ`
3. Flag if `|z_i| ≥ threshold`

#### Example Usage

```python
from src.qnwis.analysis.change_points import cusum_breaks, zscore_outliers

# Detect structural breaks
breaks = cusum_breaks(series, k=1.0, h=5.0)
# Returns: [23, 47, 89]  # Indices of breaks

# Find outliers
outliers = zscore_outliers(series, z=2.5)
# Returns: [12, 56]  # Indices of outliers
```

---

### 3. Seasonal Baselines (`baselines.py`)

Computes seasonal patterns and anomaly bands:

#### Functions

```python
seasonal_baseline(series, season=12) → Dict[str, List[float]]
```
- Returns:
  - `mean_per_phase`: Average for each phase (Jan, Feb, ...)
  - `baseline`: Repeated seasonal pattern
  - `upper_band`: baseline + 1.5×MAD
  - `lower_band`: baseline - 1.5×MAD

```python
anomaly_gaps(series, baseline) → List[Optional[float]]
```
- Percentage gaps: `(actual - baseline) / baseline × 100`
- Returns `None` where baseline is 0

```python
detect_seasonal_anomalies(series, season=12, threshold_mad=2.0) → List[int]
```
- Points beyond `threshold_mad` MADs from baseline
- Returns indices of anomalies

#### Example Usage

```python
from src.qnwis.analysis.baselines import seasonal_baseline, anomaly_gaps

# Compute baseline
result = seasonal_baseline(monthly_data, season=12)

baseline = result['baseline']
upper_band = result['upper_band']
lower_band = result['lower_band']

# Find gaps
gaps = anomaly_gaps(monthly_data, baseline)
# Returns: [2.5, -1.3, 0.8, ...]  # % deviations
```

---

### 4. TimeMachineAgent (`time_machine.py`)

Main agent with three report methods:

#### Initialization

```python
from src.qnwis.agents.base import DataClient
from src.qnwis.agents.time_machine import TimeMachineAgent

client = DataClient(queries_dir='data/queries')
agent = TimeMachineAgent(
    data_client=client,
    series_map={
        'retention': 'LMIS_RETENTION_TS',
        'qatarization': 'LMIS_QATARIZATION_TS',
        'salary': 'LMIS_SALARY_TS',
    }
)
```

#### Methods

##### `baseline_report(metric, sector, start, end, base_at)`

Computes seasonal baseline and index-100.

**Returns**:
- Executive summary
- Baseline table (last 12 months)
- Index-100 snapshot
- Citations (original + derived QIDs)

**Example**:
```python
report = agent.baseline_report(
    metric='retention',
    sector='Construction',
    start=date(2020, 1, 1),
    end=date(2024, 12, 31),
    base_at=None  # Defaults to 12 months ago
)
```

##### `trend_report(metric, sector, start, end)`

Computes YoY/QtQ, EWMA, and multi-window slopes.

**Returns**:
- Trend summary (direction, acceleration)
- Growth rates table
- Slope analysis
- Reproducibility snippet

**Example**:
```python
report = agent.trend_report(
    metric='qatarization',
    sector='Finance',
    start=date(2022, 1, 1),
    end=date(2024, 12, 31)
)
```

##### `breaks_report(metric, sector, start, end, z_threshold, cusum_h)`

Detects structural breaks and outliers.

**Returns**:
- Break summary
- Break points table (CUSUM)
- Outliers table (Z-score)
- Context vs baseline
- Recommended actions
- Audit trail

**Example**:
```python
report = agent.breaks_report(
    metric='salary',
    sector=None,  # All sectors
    start=date(2018, 1, 1),
    end=date(2024, 12, 31),
    z_threshold=2.5,
    cusum_h=5.0
)
```

---

## CLI Interface

### Installation

No additional installation required (uses project dependencies).

### Usage

```bash
# Baseline report
python -m src.qnwis.cli.qnwis_time \
  --intent time.baseline \
  --metric retention \
  --start 2020-01-01 \
  --end 2024-12-31

# Trend report with sector filter
python -m src.qnwis.cli.qnwis_time \
  --intent time.trend \
  --metric qatarization \
  --sector Construction

# Break detection with custom thresholds
python -m src.qnwis.cli.qnwis_time \
  --intent time.breaks \
  --metric salary \
  --z-threshold 3.0 \
  --cusum-h 6.0

# Save to file
python -m src.qnwis.cli.qnwis_time \
  --intent time.baseline \
  --metric retention \
  --output reports/retention_baseline.md
```

### CLI Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--intent` | ✅ | - | time.baseline, time.trend, or time.breaks |
| `--metric` | ✅ | - | Metric name (retention, qatarization, salary, etc.) |
| `--sector` | ❌ | None | Sector filter (Construction, Finance, etc.) |
| `--start` | ❌ | 2 years ago | Start date (YYYY-MM-DD) |
| `--end` | ❌ | Today | End date (YYYY-MM-DD) |
| `--base-at` | ❌ | 12 months ago | Index base period (baseline only) |
| `--z-threshold` | ❌ | 2.5 | Z-score threshold (breaks only) |
| `--cusum-h` | ❌ | 5.0 | CUSUM threshold (breaks only) |
| `--queries-dir` | ❌ | data/queries | Query definitions directory |
| `--output` | ❌ | stdout | Output file path |
| `--verbose` | ❌ | False | Enable verbose logging |

---

## Orchestration Integration

### Intent Registration

Three new intents added to `intent_catalog.yml`:

#### `time.baseline`
**Keywords**: baseline, seasonal, average, normal, expected, typical, index, normalize, band  
**Examples**:
- "What is the seasonal baseline for retention?"
- "Show me the normal pattern for qatarization"
- "Compute index-100 for salary trends"

#### `time.trend`
**Keywords**: trend, trending, direction, momentum, yoy, qtq, growth rate, slope, velocity  
**Examples**:
- "What is the trend for retention?"
- "Show YoY growth for qatarization"
- "Is employment accelerating or slowing?"

#### `time.breaks`
**Keywords**: break, structural break, change point, regime change, shift, disruption, cusum  
**Examples**:
- "Detect structural breaks in retention"
- "When did qatarization rates shift?"
- "Identify disruptions in employment patterns"

### Registry Mapping

```python
# In src/qnwis/orchestration/registry.py
time_machine_agent = TimeMachineAgent(client)

registry.register("time.baseline", time_machine_agent, "baseline_report")
registry.register("time.trend", time_machine_agent, "trend_report")
registry.register("time.breaks", time_machine_agent, "breaks_report")
```

### Routing

Automatic routing via `QNWISGraph`:
1. User query classified by `QueryClassifier`
2. Matched to time.* intent
3. Routed to TimeMachineAgent method
4. Report returned with citations and derived QIDs

---

## Testing Strategy

### Unit Tests

Create comprehensive tests for all modules (target >90% coverage):

#### `tests/unit/analysis/test_trend_utils.py`
```python
def test_yoy_basic():
    """Test YoY calculation with 12-month lag."""
    series = [100, 110, 120, 105]
    result = yoy(series, period=2)
    assert result[2] == 20.0  # (120-100)/100 * 100

def test_yoy_zero_handling():
    """Test YoY with zero previous value."""
    series = [0, 100, 110]
    result = yoy(series, period=1)
    assert result[1] is None  # Division by zero

def test_ewma_stability():
    """Test EWMA converges for constant series."""
    series = [100] * 10
    result = ewma(series, alpha=0.25)
    assert all(abs(x - 100) < 0.01 for x in result)
```

#### `tests/unit/analysis/test_change_points.py`
```python
def test_cusum_detects_shift():
    """Test CUSUM detects mean shift."""
    series = [100]*10 + [150]*10
    breaks = cusum_breaks(series, k=1.0, h=3.0)
    assert 10 in breaks

def test_zscore_detects_outlier():
    """Test z-score flags outlier."""
    series = [100, 102, 101, 200, 99]
    outliers = zscore_outliers(series, z=2.0)
    assert 3 in outliers
```

#### `tests/unit/analysis/test_baselines.py`
```python
def test_seasonal_baseline_12_month():
    """Test seasonal baseline with 12-month period."""
    # Create series with seasonal pattern
    series = [100, 110, 105] * 4  # 12 months
    result = seasonal_baseline(series, season=3)
    assert len(result['baseline']) == 12
    assert result['mean_per_phase'][0] == 100
```

#### `tests/unit/agents/test_time_machine.py`
```python
def test_baseline_report_returns_narrative():
    """Test baseline_report returns formatted string."""
    client = MockDataClient()
    agent = TimeMachineAgent(client)
    report = agent.baseline_report('retention', None, start, end)
    assert isinstance(report, str)
    assert "Executive Summary" in report
    assert "QID=" in report

def test_trend_report_includes_yoy():
    """Test trend_report includes YoY values."""
    client = MockDataClient()
    agent = TimeMachineAgent(client)
    report = agent.trend_report('retention', None, start, end)
    assert "YoY %" in report
```

### Integration Tests

#### `tests/integration/agents/test_time_machine_integration.py`
```python
def test_end_to_end_baseline_with_real_data():
    """Test baseline report with synthetic LMIS data."""
    client = DataClient('data/queries')
    agent = TimeMachineAgent(client)
    
    report = agent.baseline_report(
        metric='retention',
        sector='Construction',
        start=date(2020, 1, 1),
        end=date(2024, 12, 31)
    )
    
    assert "QID=" in report
    assert "Freshness:" in report
    assert len(report) > 100
```

### Test Execution

```bash
# Run all Time Machine tests
pytest tests/unit/analysis/ -v
pytest tests/unit/agents/test_time_machine.py -v
pytest tests/integration/agents/test_time_machine_integration.py -v

# Coverage report
pytest tests/ --cov=src.qnwis.analysis --cov=src.qnwis.agents.time_machine --cov-report=html
```

---

## Performance Considerations

### Complexity

All algorithms are **O(n)** for n-length time-series:
- YoY/QtQ: Single pass
- EWMA: Single pass
- CUSUM: Single pass with running statistics
- Seasonal baseline: O(n) grouping + O(season) averaging
- Window slopes: O(window) least squares per window

### Memory

- In-place computation where possible
- Lists used instead of NumPy for simplicity
- Peak memory: ~3× series length (original + derived + intermediate)

### Latency Targets

For typical monthly series (24-60 points):
- Baseline computation: <10ms
- Trend analysis: <15ms
- Break detection: <20ms
- Total agent report: <50ms

### Optimization Notes

- Guard clauses prevent unnecessary computation
- Early returns for insufficient data
- No external dependencies (pure Python)
- Suitable for real-time API responses

---

## Security & Data Quality

### PII Safety

✅ **All analysis is on aggregate time-series only**
- No person-level data
- No company names in formulas
- Sector aggregations only
- Automatic redaction in agent base

### Input Validation

```python
# Required validations (implemented in agent):
- Minimum 3 points for any analysis
- Minimum 12 points for baseline (seasonal)
- Date range validation (start < end)
- Query ID whitelisting via series_map
- Sector filter sanitization
```

### Error Handling

```python
# Graceful degradation:
- Zero values: Return None (not error)
- Constant series: Return zeros/None (not error)
- Insufficient data: Raise ValueError with clear message
- Missing query ID: Raise ValueError listing available metrics
```

---

## Known Limitations

1. **Monthly Data Only**: Assumes monthly periodicity (season=12)
2. **No Missing Values**: Does not interpolate gaps (raises error)
3. **Single Metric**: Analyzes one metric at a time (no multivariate)
4. **No Forecasting**: Historical analysis only (no predictions)
5. **Pure Python**: No NumPy/Pandas (by design for simplicity)

---

## Future Enhancements

### Phase 2 (Q1 2025)
- [ ] Multi-metric correlation in time domain
- [ ] Seasonal decomposition (trend + seasonal + residual)
- [ ] Autocorrelation analysis (ACF/PACF)
- [ ] Rolling window statistics

### Phase 3 (Q2 2025)
- [ ] Quarterly and annual aggregations
- [ ] Custom seasonality detection
- [ ] Advanced smoothing (Holt-Winters, STL)
- [ ] Comparative time-series (benchmark multiple series)

---

## Runbook

### Common Tasks

#### Add New Time-Series Metric

1. Define query in `data/queries/*.yaml`
2. Add to `series_map` in agent initialization:
   ```python
   agent = TimeMachineAgent(
       client,
       series_map={'new_metric': 'LMIS_NEW_METRIC_TS'}
   )
   ```
3. Update intent_catalog keywords if needed
4. Test with CLI

#### Adjust Break Detection Sensitivity

**More sensitive** (detect smaller breaks):
```python
agent.breaks_report(
    metric='retention',
    z_threshold=2.0,  # Lower = more sensitive
    cusum_h=4.0       # Lower = more sensitive
)
```

**Less sensitive** (only major breaks):
```python
agent.breaks_report(
    metric='retention',
    z_threshold=3.0,  # Higher = less sensitive
    cusum_h=6.0       # Higher = less sensitive
)
```

#### Troubleshoot "Insufficient Data" Error

```python
# Check available data
result = client.run('LMIS_RETENTION_TS')
print(f"Available points: {len(result.rows)}")
print(f"Date range: {result.rows[0].data['period']} to {result.rows[-1].data['period']}")

# Adjust date range
agent.baseline_report(
    metric='retention',
    start=date(2022, 1, 1),  # Wider range
    end=date(2024, 12, 31)
)
```

---

## Success Criteria

✅ **Implementation Complete**:
- [x] Math utilities (trend_utils.py)
- [x] Change-point detection (change_points.py)
- [x] Seasonal baselines (baselines.py)
- [x] TimeMachineAgent with 3 methods
- [x] LLM prompts with citation discipline
- [x] CLI interface (qnwis_time.py)
- [x] Orchestration integration (intents + registry)
- [x] Documentation (this file)

✅ **Quality Gates**:
- All functions guard against edge cases (zeros, NaNs, small samples)
- Pure Python (no NumPy/Pandas dependencies)
- O(n) complexity for all algorithms
- Citations include original + derived Query IDs
- Derived QueryResults wrapped for verification
- Input validation prevents security issues

🔲 **Pending**:
- [ ] Unit tests (>90% coverage)
- [ ] Integration tests with synthetic LMIS data
- [ ] Performance benchmarks (<50ms target)
- [ ] User acceptance testing

---

## References

### Academic Sources
- Page, E. S. (1954). "Continuous Inspection Schemes". *Biometrika*.
- Basseville, M., & Nikiforov, I. V. (1993). *Detection of Abrupt Changes*. Prentice Hall.

### Internal Documents
- `Complete_Implementation_Plan_And_Development_Roadmap.md`
- `Complete_API_Specification.md`
- `Complete_Testing_Strategy_and_Validation.md`

### Code References
- `src/qnwis/agents/pattern_detective.py` (anomaly detection patterns)
- `src/qnwis/data/derived/metrics.py` (yoy_growth reference)
- `src/qnwis/agents/utils/derived_results.py` (derived QueryResult creation)

---

## Contact & Support

**Module Owner**: QNWIS Development Team  
**Reviewers**: Data Science Team, Ministry of Labour  
**Last Updated**: 2025-11-08  
**Next Review**: 2025-12-01

For issues or questions, refer to:
- `README.md` (project setup)
- `AGENTS_QUICK_START.md` (agent development)
- `ORCHESTRATION_QUICK_START.md` (routing & intents)
