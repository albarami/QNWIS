# Step 25: Predictor Agent - Baseline Forecasting & Early Warning System

**Status**: ✅ Implementation Complete  
**Version**: 1.0  
**Last Updated**: 2024-11-08

## Overview

The **PredictorAgent** provides deterministic baseline forecasting and early-warning risk scoring for LMIS labour market time-series. All methods are interpretable, citation-ready, and designed for production use by Qatar's Ministry of Labour.

### Capabilities

1. **Baseline Forecasting** (`forecast_baseline`)
   - Automatic method selection via backtesting
   - 95% prediction intervals using MAD scaling
   - Horizon up to 12 months

2. **Early Warning System** (`early_warning`)
   - Risk scoring (0-100) based on three flags
   - Band breach detection (forecast deviation)
   - Slope reversal detection (trend change)
   - Volatility spike detection (abnormal variability)

3. **Scenario Comparison** (`scenario_compare`)
   - Compare multiple forecasting methods
   - Backtest performance metrics
   - Forecast delta analysis

---

## Architecture

### Core Modules

#### `src/qnwis/forecast/baselines.py`
Implements four deterministic forecasting methods:

- **Seasonal Naive**: Repeats value from t-season periods ago
- **EWMA**: Exponentially weighted moving average (recursive smoothing)
- **Rolling Mean**: Simple moving average over last N points
- **Robust Trend**: Theil-Sen linear extrapolation (median of pairwise slopes)

**Key Functions**:
```python
def seasonal_naive(series: List[float], season: int = 12, horizon: int = 6) -> List[Optional[float]]
def ewma_forecast(series: List[float], alpha: float = 0.3, horizon: int = 6) -> List[float]
def rolling_mean_forecast(series: List[float], window: int = 12, horizon: int = 6) -> List[Optional[float]]
def robust_trend_forecast(series: List[float], window: int = 24, horizon: int = 6) -> List[float]
```

**Prediction Intervals**:
```python
def mad_interval(residuals: List[float], z: float = 1.96) -> float
```
Uses MAD (Median Absolute Deviation) scaled to σ ≈ 1.4826 × MAD for robust interval estimation.

#### `src/qnwis/forecast/backtest.py`
Rolling-origin (walk-forward) backtesting framework:

```python
def rolling_origin_backtest(
    series: List[float],
    method: ForecastFn,
    horizon: int = 1,
    min_train: int = 24,
    **method_kwargs
) -> Dict[str, float]:
    """Returns: {'mae': ..., 'mape': ..., 'rmse': ..., 'n': ...}"""
```

**Method Selection**:
```python
def choose_baseline(series: List[float], season: int = 12) -> str:
    """Heuristic selection: backtest all methods, return lowest MAE."""
```

#### `src/qnwis/forecast/early_warning.py`
Risk detection rules:

```python
def band_breach(actual: float, yhat: float, half_width: float) -> bool
def slope_reversal(recent: List[float], window: int = 3) -> bool
def volatility_spike(recent: List[float], lookback: int = 6, z: float = 2.5) -> bool
def risk_score(flags: Dict[str, bool], weights: Dict[str, float]) -> float
```

**Default Risk Weights**:
- Band breach: 50%
- Slope reversal: 30%
- Volatility spike: 20%

---

## Usage

### 1. Baseline Forecasting

```python
from datetime import date
from src.qnwis.agents.base import DataClient
from src.qnwis.agents.predictor import PredictorAgent

client = DataClient()
agent = PredictorAgent(client)

narrative = agent.forecast_baseline(
    metric="retention",
    sector="Construction",
    start=date(2019, 1, 1),
    end=date(2025, 6, 1),
    horizon_months=6,
    season=12
)

print(narrative)
```

**Output Format**:
```markdown
## Executive Summary
- **Metric**: retention
- **Sector**: Construction
- **Horizon**: 6 months
- **Method selected**: robust_trend (lowest MAE=0.0234) [QID: derived_backtest_...]

## Forecast with 95% Prediction Intervals
| h | yhat | lo | hi |
|---|------|----|----|
| 1 | 82.45 | 79.12 | 85.78 |
| 2 | 82.67 | 79.34 | 85.99 |
...
[QID: derived_forecast_...]

## Backtest Performance
- **MAE**: 0.0234 [QID: ...]
- **MAPE**: 2.85% [QID: ...]
- **RMSE**: 0.0312 [QID: ...]

## Freshness
- **Data as of**: 2025-06-01

## Reproducibility
```python
DataClient.run("ts_retention_by_sector")
PredictorAgent.forecast_baseline(metric="retention", sector="Construction", horizon_months=6)
```
```

### 2. Early Warning Analysis

```python
narrative = agent.early_warning(
    metric="qatarization",
    sector="Healthcare",
    end=date(2025, 6, 1),
    horizon_months=3
)

print(narrative)
```

**Output Format**:
```markdown
## Risk Assessment
- **Risk Score**: 65.0/100 [QID: derived_early_warning_...]
- **Active Flags**: band_breach, volatility_spike
- **Metric**: qatarization
- **Sector**: Healthcare
- **Evaluation date**: 2025-06-01

## Flag Details
- **Band Breach**: Yes - Actual 23.45 vs forecast 26.78 ± 1.89 [QID: ...]
- **Slope Reversal**: No [QID: ...]
- **Volatility Spike**: Yes [QID: ...]

## Recommended Actions
1. Investigate qatarization deviation in Healthcare: review recent policy changes...
2. Address qatarization volatility in Healthcare: implement stabilization measures...
3. Monitor qatarization trend reversal in Healthcare: assess if this indicates...
```

### 3. Scenario Comparison

```python
narrative = agent.scenario_compare(
    metric="salary",
    sector="Finance",
    start=date(2019, 1, 1),
    end=date(2025, 6, 1),
    horizon_months=6,
    methods=["seasonal_naive", "ewma", "robust_trend"]
)

print(narrative)
```

**Output Format**:
```markdown
## Method Comparison

### Backtest Performance
| Method | MAE | MAPE | RMSE |
|--------|-----|------|------|
| seasonal_naive | 0.0245 | 2.95% | 0.0328 |
| ewma | 0.0221 | 2.67% | 0.0295 |
| robust_trend | 0.0198 | 2.39% | 0.0265 |

### Forecast Comparison
| h | seasonal_naive | ewma | robust_trend |
|---|----------------|------|--------------|
| 1 | 12450.00 | 12523.45 | 12589.23 |
| 2 | 12450.00 | 12523.45 | 12612.67 |
...
```

---

## CLI Usage

### Installation
```bash
# No additional dependencies required
cd /d/lmis_int
```

### Commands

**Forecast**:
```bash
python -m src.qnwis.cli.qnwis_predict forecast \
  --metric retention \
  --sector Construction \
  --start 2019-01-01 \
  --end 2025-06-01 \
  --horizon 6 \
  --season 12
```

**Early Warning**:
```bash
python -m src.qnwis.cli.qnwis_predict warn \
  --metric qatarization \
  --sector Healthcare \
  --end 2025-06-01 \
  --horizon 3
```

**Scenario Comparison**:
```bash
python -m src.qnwis.cli.qnwis_predict compare \
  --metric avg_salary \
  --sector All \
  --start 2019-01-01 \
  --end 2025-06-01 \
  --horizon 6 \
  --methods seasonal_naive,ewma,robust_trend
```

---

## Mathematical Details

### 1. Seasonal Naive
For seasonal period `s` and horizon `h`:
```
yhat_{t+h} = y_{t - s + (h mod s)}
```

**Use Case**: Strong seasonal patterns (e.g., monthly hiring cycles)

### 2. EWMA (Exponential Smoothing)
Recursive formula:
```
S_t = α × y_t + (1 - α) × S_{t-1}
yhat_{t+h} = S_t  (flat forecast)
```

**Parameters**:
- α = 0.3 (default): balances responsiveness vs. smoothness
- Higher α → more reactive to recent changes
- Lower α → smoother, less sensitive to noise

**Use Case**: Trend-stationary series without strong seasonality

### 3. Rolling Mean
Simple moving average:
```
yhat_{t+h} = (1/w) × Σ_{i=t-w+1}^{t} y_i
```

**Parameters**:
- w = 12 (default window)

**Use Case**: Stable metrics with low volatility

### 4. Robust Trend (Theil-Sen)
Median of all pairwise slopes:
```
slope = median{ (y_j - y_i) / (j - i) | j > i }
yhat_{t+h} = y_t + slope × h
```

**Advantages**:
- Robust to outliers (50% breakdown point)
- Deterministic (no iterative optimization)
- O(n²) complexity, practical for n ≤ 50

**Use Case**: Trending series with occasional outliers

### 5. Prediction Intervals (MAD-based)
```
MAD = median{ |r_i| }
σ̂ = 1.4826 × MAD
CI = [yhat - 1.96σ̂, yhat + 1.96σ̂]  (95% coverage)
```

**Why MAD?**
- Robust to outliers (50% breakdown point)
- No assumptions about residual distribution
- More stable than standard deviation for real-world data

---

## Orchestration Integration

### Intent Catalog (`intent_catalog.yml`)

Three new intents added:

1. **`predict.forecast`**
   - Keywords: forecast, predict, project, future, outlook
   - Prefetch: 36 months of time-series history

2. **`predict.early_warning`**
   - Keywords: warning, alert, risk, red flag, concern
   - Prefetch: 24 months of recent history

3. **`predict.scenario_compare`**
   - Keywords: compare forecast, method comparison, scenario
   - Prefetch: 36 months for method comparison

### Agent Registry

Registered in `orchestration/registry.py`:
```python
predictor_agent = PredictorAgent(client)
registry.register("predict.forecast", predictor_agent, "forecast_baseline")
registry.register("predict.early_warning", predictor_agent, "early_warning")
registry.register("predict.scenario_compare", predictor_agent, "scenario_compare")
```

### Natural Language Examples

**Forecast**:
- "Forecast retention for next 6 months in Construction"
- "What is the expected salary trend for Healthcare?"
- "Project qatarization rates for Q1 2026"

**Early Warning**:
- "Are there warning signs in retention?"
- "Risk assessment for Construction turnover"
- "What are the red flags for Healthcare qatarization?"

**Scenario Comparison**:
- "Compare forecasting methods for retention"
- "Which forecast method is most accurate for salary?"
- "Contrast seasonal vs trend forecasts"

---

## Performance Characteristics

### Computational Complexity

| Method | Training | Forecast | Notes |
|--------|----------|----------|-------|
| Seasonal Naive | O(1) | O(h) | Lookback only |
| EWMA | O(n) | O(h) | Recursive smoothing |
| Rolling Mean | O(w) | O(h) | Window average |
| Robust Trend | O(n²) | O(h) | Theil-Sen slope |
| Backtest | O(n × T) | - | T = training iterations |

**Practical Limits**:
- Series length: n ≤ 500 (typical: 24-60 months)
- Horizon: h ≤ 12 months
- Backtest folds: (n - min_train) iterations

### Memory Footprint

- In-memory series: ~8 KB per 100 points (float64)
- Forecast table: ~200 bytes per horizon step
- Total agent memory: < 1 MB for typical use cases

### Latency Targets

- `forecast_baseline`: < 100 ms (including method selection)
- `early_warning`: < 50 ms (single forecast + flags)
- `scenario_compare`: < 300 ms (4 methods × backtest)

---

## Data Requirements

### Input Format

Time-series data from `DataClient.run(query_id)`:
```python
QueryResult(
    query_id="ts_retention_by_sector",
    rows=[
        Row(data={"month": "2024-01-01", "retention": 82.5, "sector": "Construction"}),
        Row(data={"month": "2024-02-01", "retention": 83.1, "sector": "Construction"}),
        ...
    ],
    unit="percent",
    ...
)
```

**Requirements**:
- Minimum 24 points for baseline forecasts
- Minimum 12 points for early warning
- Chronologically ordered (sorted by date field)
- No missing values in forecast window

### Query ID Mapping (Placeholder)

Current implementation uses placeholder query IDs:
```python
query_id = f"ts_{metric}_by_sector"  # Placeholder
```

**Integration Follow-ups**:
- Map metrics to actual registry query IDs
- Add sector filtering to queries
- Implement date range filtering

---

## Safety & Constraints

### Input Validation

1. **Horizon Bounds**: `1 ≤ horizon_months ≤ 12`
2. **History Requirements**:
   - Baseline forecast: ≥ 24 points
   - Early warning: ≥ 12 points
   - Scenario compare: ≥ 24 points
3. **Non-negative Clamping**: Forecasts for rate/percentage metrics clamped to [0, ∞)

### Error Handling

- **Insufficient Data**: Returns descriptive error message (no fallback to mock data)
- **Query Not Found**: Logs error and returns user-friendly message
- **Method Failure**: Backtesting silently skips failed methods; defaults to EWMA

### PII Safety

- **Aggregate Data Only**: No person-level identifiers in time-series
- **Sector Aggregation**: Minimum 10 entities per sector (enforced upstream)

---

## Testing Strategy

### Unit Tests (`tests/unit/forecast/`)

1. **`test_baselines.py`**:
   - Seasonal naive with insufficient history → returns None
   - EWMA with α ∈ (0, 1] → valid forecasts
   - Rolling mean with window > len(series) → returns None
   - Robust trend with n < 2 → returns last value

2. **`test_backtest.py`**:
   - Rolling-origin with min_train > len(series) → returns NaN
   - Method selection with all failures → defaults to "ewma"
   - MAPE with zero actuals → safe handling

3. **`test_early_warning.py`**:
   - Band breach with half_width = 0 → always False
   - Slope reversal with insufficient data → returns False
   - Volatility spike with lookback > len(series) → returns False
   - Risk score with empty flags → returns 0.0

### Integration Tests (`tests/integration/agents/`)

1. **`test_predictor_forecast.py`**:
   - End-to-end forecast with synthetic time-series
   - QID citations present in narrative
   - Backtest metrics match expected values

2. **`test_predictor_early_warning.py`**:
   - Risk score computation with known flags
   - Recommendation generation based on active flags

3. **`test_predictor_scenario.py`**:
   - Method comparison with 3+ methods
   - Backtest table formatting

### Coverage Target

- **Baseline modules**: >95%
- **PredictorAgent**: >90%
- **CLI**: >80% (manual CLI tests in addition)

---

## Known Limitations

1. **Univariate Only**: No multivariate forecasting (e.g., VAR models)
2. **Linear Trends**: Robust trend assumes linear extrapolation
3. **Fixed Seasonality**: Seasonal naive requires constant seasonal period
4. **No Uncertainty Quantification**: Intervals assume normal residuals (MAD scaling)
5. **Placeholder Query IDs**: Requires integration with actual query registry

---

## Future Enhancements

### Phase 2 (Post-Launch)

1. **Adaptive Seasonality**: Detect and adjust seasonal period dynamically
2. **Ensemble Methods**: Combine multiple baselines with weighted averaging
3. **Anomaly Correction**: Pre-process outliers before forecasting
4. **Exogenous Variables**: Add policy indicators as covariates
5. **Probabilistic Forecasts**: Full posterior distributions via bootstrapping

### Phase 3 (Advanced)

1. **State-Space Models**: Structural time-series (level + trend + seasonal)
2. **Prophet Integration**: Facebook Prophet for automatic seasonality detection
3. **Neural Forecasting**: Transformer-based models for long-horizon forecasts
4. **Causal Inference**: Synthetic control for policy impact estimation

---

## Runbook

### Deployment Checklist

- [ ] Update query ID mappings in `predictor.py`
- [ ] Verify sector filtering in upstream queries
- [ ] Add horizon bounds to API validation
- [ ] Configure risk weight defaults in environment
- [ ] Enable audit logging for forecast requests
- [ ] Set up monitoring for latency SLAs

### Troubleshooting

**Issue**: "Insufficient data" errors
- **Cause**: Series length < 24 points
- **Solution**: Verify query date range; extend history if needed

**Issue**: All backtest methods fail
- **Cause**: Series contains NaN or Inf values
- **Solution**: Check upstream data quality; add pre-processing step

**Issue**: Risk score always 0
- **Cause**: All flags False or empty weights
- **Solution**: Verify flag computation logic; check weight normalization

---

## References

### Academic Sources

1. **Theil-Sen Estimator**: Sen, P. K. (1968). "Estimates of the regression coefficient based on Kendall's tau". *Journal of the American Statistical Association*, 63(324), 1379-1389.

2. **MAD Scaling**: Rousseeuw, P. J., & Croux, C. (1993). "Alternatives to the median absolute deviation". *Journal of the American Statistical Association*, 88(424), 1273-1283.

3. **Walk-Forward Validation**: Tashman, L. J. (2000). "Out-of-sample tests of forecasting accuracy: an analysis and review". *International Journal of Forecasting*, 16(4), 437-450.

### Internal Documentation

- [Step 23: Time Machine](./step23_time_machine.md) - Baseline computation
- [Step 22: Confidence Scoring](../../STEP22_CONFIDENCE_SCORING_IMPLEMENTATION.md) - Verification patterns
- [Complete API Catalog](../../metadata/complete_api_catalog.md) - API contracts

---

## Changelog

### v1.0 (2024-11-08)
- ✅ Implemented four baseline forecasters
- ✅ Rolling-origin backtesting framework
- ✅ Early-warning engine with risk scoring
- ✅ PredictorAgent with three entrypoints
- ✅ CLI tool for offline forecasts
- ✅ Orchestration integration (3 new intents)
- ✅ Comprehensive documentation

---

**Author**: QNWIS Development Team  
**Reviewed By**: Ministry of Labour Technical Advisory  
**Classification**: Internal Use - Qatar Government
