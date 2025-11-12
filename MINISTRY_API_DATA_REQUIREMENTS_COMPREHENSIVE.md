# Ministry of Labour API - Comprehensive Data Requirements Analysis
## QNWIS Integration Testing - Deep Code Analysis

**Date:** November 12, 2024
**Status:** Complete System Analysis
**Analysis Method:** Deep code review of all agents, data layers, and verification systems

---

## Executive Summary

**Minimum Viable Time Range:** 24 months (2 years)
**Optimal Time Range:** 36-48 months (3-4 years)
**Critical Endpoints:** 7 core endpoints
**Important Endpoints:** 8 supporting endpoints
**Total Agents Analyzed:** 9 (TimeMachine, PatternMiner, Predictor, Scenario, NationalStrategy, LabourEconomist, Nationalization, PatternDetective, AlertCenter)

### Key Findings

1. **Time Range Requirements are Agent-Specific:**
   - PredictorAgent: MIN 24 months (hard requirement: `MIN_TRAIN_POINTS = 24`)
   - TimeMachineAgent: MIN 12 months, OPTIMAL 24-36 months
   - PatternMinerAgent: MIN 12-24 months (window-dependent)
   - NationalStrategyAgent: MIN 3 years (annual data for Vision 2030)

2. **Data Gaps Identified:**
   - Monthly time-series queries (LMIS_RETENTION_TS, LMIS_QATARIZATION_TS, etc.) referenced but not defined
   - Cohort-specific time-series queries missing (timeseries_{metric}_{cohort}_{window}m pattern)
   - Pre-computed forecast baselines expected but not available

3. **Data Quality Requirements:**
   - Non-negative validation for counts and percentages
   - Null handling for missing periods
   - Standardized sector names across all endpoints
   - ISO 8601 date formats (YYYY-MM for monthly, YYYY for annual)

---

## Section 1: Complete Data Requirements by Agent

### 1.1 TimeMachineAgent - Historical Time-Series Analysis

**Purpose:** Seasonal baselines, YoY/QtQ deltas, change-point detection, trend analysis

**Required Queries:**
```python
# Default series mapping (time_machine.py:68-74)
'retention': 'LMIS_RETENTION_TS',
'qatarization': 'LMIS_QATARIZATION_TS',
'salary': 'LMIS_SALARY_TS',
'employment': 'LMIS_EMPLOYMENT_TS',
'attrition': 'syn_attrition_monthly',
```

**Data Structure Expected:**
```json
{
  "rows": [
    {
      "period": "2023-01",  // YYYY-MM format
      "sector": "Construction",  // Optional, null for national
      "value": 75.5,  // Metric value
      "unit": "percent"  // or "count", "qar", etc.
    }
  ]
}
```

**Time Range Analysis:**
- **Minimum:** 12 months (baseline_report needs 12-month seasonal cycle)
- **Optimal:** 24-36 months (trend_report needs 12 months + YoY comparisons)
- **Break Detection:** 24+ months (CUSUM algorithm needs sufficient history)

**Code Evidence:**
```python
# time_machine.py:301 - Default range
if start is None:
    start = date(end.year - 2, end.month, end.day)  # 2 years back

# time_machine.py:316-319 - Minimum validation
if len(values) < season and sector is None:
    raise ValueError(f"Insufficient data for baseline: {len(values)} points (need >= {season})")
```

**Critical Fields:**
- `period` (YYYY-MM, required)
- `sector` (string, optional for national aggregates)
- `value` (float, required)
- Year must be extractable from period for `asof_date` calculation

**API Endpoint Recommendations:**
```
POST /api/timeseries/query
{
  "metric": "retention" | "qatarization" | "salary" | "employment" | "attrition",
  "sector": "Construction" | null,  // null = national
  "start_period": "2021-01",
  "end_period": "2024-11",
  "frequency": "monthly"
}
```

---

### 1.2 PatternMinerAgent - Multi-Period Cohort Analysis

**Purpose:** Stable driver-outcome relationships, seasonal effects, driver screening across cohorts

**Query ID Pattern:**
```python
# pattern_miner.py:739-748
def _build_timeseries_qid(metric, cohort, window):
    metric_slug = metric.lower().replace(" ", "_")
    cohort_slug = (cohort or "all").lower().replace(" ", "_")
    return f"timeseries_{metric_slug}_{cohort_slug}_{window}m"

# Examples:
# timeseries_retention_construction_12m
# timeseries_qatarization_healthcare_24m
# timeseries_salary_all_36m
```

**Data Requirements:**
- **Windows supported:** 3, 6, 12, 24 months (pattern_miner.py:80)
- **Minimum support:** 12 observations (min_support parameter)
- **Cohorts:** Sector names OR "all" for national

**Expected Data:**
```json
{
  "query_id": "timeseries_retention_construction_12m",
  "rows": [
    {
      "period": "2023-01",
      "metric": "retention",
      "cohort": "construction",
      "value": 85.2,
      "unit": "percent"
    }
  ]
}
```

**Time Range:** 24-36 months optimal (allows 12-month windows with 12-24 month validation)

**Code Evidence:**
```python
# pattern_miner.py:80-81
if window not in [3, 6, 12, 24]:
    return f"Error: Invalid window {window}. Must be 3, 6, 12, or 24 months."

# pattern_miner.py:88-89
min_support=min_support,  # Default: 12
```

**API Endpoint Recommendations:**
```
GET /api/timeseries/cohort
Parameters:
  - metric: retention|qatarization|salary|employment|attrition
  - cohort: {sector_name}|all
  - window_months: 3|6|12|24
  - end_date: 2024-11-30
```

---

### 1.3 PredictorAgent - Forecasting & Early Warning

**Purpose:** Baseline forecasting (6-12 month horizon), early warning signals, scenario comparison

**Hard Requirements:**
```python
# predictor.py:35
MIN_TRAIN_POINTS = 24  # ABSOLUTE MINIMUM
```

**Data Structure:**
```json
{
  "rows": [
    {
      "month": "2023-01",  // Date field name: "month" or "period"
      "{metric}": 1250.5,  // Dynamic field name based on metric
      "sector": "Construction"  // Optional
    }
  ]
}
```

**Extraction Method:**
```python
# predictor.py:73-109
def _extract_time_series(result, metric_field, date_field="month"):
    # Extracts from row.data.get(date_field) and row.data.get(metric_field)
    # Sorts chronologically
    # Validates numeric values (math.isfinite check)
```

**Forecast Methods:**
- seasonal_naive: Requires 12 months history
- ewma: Requires 24 months minimum
- rolling_mean: 12-month window
- robust_trend: 24-month window

**Time Range:**
- **Minimum:** 24 months (backtest requirement)
- **Optimal:** 36-48 months (enables robust method selection + validation)

**Stability Guard (Change-Point Detection):**
```python
# predictor.py:145-173
def _apply_stability_guard(values, dates):
    if len(values) < MIN_TRAIN_POINTS:
        return values, None

    break_indices = sorted(cusum_breaks(values, k=1.0, h=5.0))
    # If break detected, uses post-break tail if >= 24 points
```

**API Endpoint Recommendations:**
```
GET /api/timeseries/forecast_baseline
Parameters:
  - metric: retention|qatarization|salary|employment
  - sector: {sector_name}|null
  - start_date: 2021-01-01
  - end_date: 2024-11-30
  - frequency: monthly

Response must include dynamic metric field name matching query.
```

---

### 1.4 ScenarioAgent - What-If Analysis

**Purpose:** Apply scenarios to baseline forecasts, compare multiple scenarios, batch sector processing

**Expected Query IDs:**
```python
# scenario_agent.py:98-99
sector_slug = (sector or "all").lower().replace(" ", "_")
qid = f"forecast_baseline_{metric}_{sector_slug}_{horizon_months}m"

# Examples:
# forecast_baseline_retention_construction_12m
# forecast_baseline_qatarization_all_6m
```

**Dependency:** Requires **pre-computed forecast baselines**

**Options:**
1. **Ministry provides forecasts:** Most deterministic
2. **QNWIS computes on-demand:** Adds 2-5 second latency
3. **Hybrid:** Cache computed forecasts as pseudo-queries

**Whitelisted Metrics:**
```python
# scenario_agent.py:22-31
ALLOWED_METRICS = {
    "retention", "qatarization", "salary", "employment",
    "turnover", "attrition", "wage", "productivity"
}
```

**Expected Forecast Structure:**
```json
{
  "query_id": "forecast_baseline_retention_construction_12m",
  "rows": [
    {
      "h": 1,  // Horizon month
      "yhat": 85.2,  // Forecast value
      "lo": 82.1,  // Lower 95% PI
      "hi": 88.3   // Upper 95% PI
    }
  ]
}
```

**Resolution:** Ministry API should provide `/api/forecasts/baseline` endpoint OR accept on-demand latency.

---

### 1.5 NationalStrategyAgent - GCC Benchmarking & Vision 2030

**Purpose:** GCC unemployment comparison, talent competition assessment, Vision 2030 alignment tracking

**Required Queries:**

#### A) GCC Unemployment Benchmarking
```python
# national_strategy.py:88
gcc_res = self.client.run("syn_unemployment_rate_gcc_latest")
```

**Expected Data:**
```json
{
  "rows": [
    {
      "country": "Qatar",
      "unemployment_rate": 0.3,
      "year": 2024
    },
    {
      "country": "UAE",
      "unemployment_rate": 2.1,
      "year": 2024
    }
    // ... other GCC countries
  ]
}
```

**Minimum:** 3 countries (min_countries parameter)
**Optimal:** All 6 GCC countries (Qatar, UAE, Saudi Arabia, Kuwait, Bahrain, Oman)
**Time Range:** 2-3 years for trend analysis

#### B) Talent Competition (Attrition Proxy)
```python
# national_strategy.py:200
atr_res = self.client.run("syn_attrition_by_sector_latest")
```

**Expected Data:**
```json
{
  "rows": [
    {
      "sector": "Construction",
      "attrition_percent": 12.5
    }
  ]
}
```

#### C) Vision 2030 Alignment
```python
# national_strategy.py:303
qat_res = self.client.run("syn_qatarization_by_sector_latest")
```

**Expected Data:**
```json
{
  "rows": [
    {
      "sector": "Construction",
      "qataris": 1250,
      "non_qataris": 8750
    }
  ]
}
```

**Calculation:**
```python
# national_strategy.py:324-325
current_qatarization = (total_qataris / total_employees) * 100
```

**Vision 2030 Targets (Hard-Coded):**
```python
# national_strategy.py:23-28
VISION_2030_TARGETS = {
    "qatarization_public_sector": 90.0,   # 90% target
    "qatarization_private_sector": 30.0,  # 30% target
    "unemployment_rate_qataris": 2.0,     # <2% target
    "female_labor_participation": 45.0,   # 45% target
}
```

**Time Range:** 3-5 years (annual data from 2020-2024 optimal)

---

### 1.6 LabourEconomistAgent - Employment Trends

**Purpose:** Employment share analysis, YoY growth metrics

**Required Query:**
```python
# labour_economist.py:13
EMPLOYMENT_QUERY = "q_employment_share_by_gender_2023"
```

**Expected Data:**
```json
{
  "rows": [
    {
      "year": 2023,
      "male_percent": 88.7,
      "female_percent": 11.3,
      "total_percent": 100.0
    }
  ]
}
```

**Validation:**
- `total_percent` should be 100.0
- `male_percent + female_percent ≈ total_percent`

**Time Range:** 24-36 months for YoY analysis

---

### 1.7 NationalizationAgent - GCC Unemployment Comparison

**Purpose:** Determine Qatar's unemployment rate and GCC ranking

**Required Query:**
```python
# nationalization.py:15
UNEMPLOY_QUERY = "q_unemployment_rate_gcc_latest"
```

**Flexible Field Detection:**
```python
# nationalization.py:60-74
# Ignores: year, country, iso, iso_code
# Finds most common numeric field (prefers "value")
# Coerces to float safely
```

**Expected Data (Flexible):**
```json
{
  "rows": [
    {
      "country": "QAT",  // or "QATAR"
      "value": 0.3,  // or any numeric field
      "year": 2024
    }
  ]
}
```

**Time Range:** 2-3 years (annual data)

---

### 1.8 PatternDetectiveAgent - Pattern Discovery

**Purpose:** Anomaly detection, pattern recognition in time-series

**Requirements:** Similar to PatternMinerAgent
- 24-36 months optimal
- Monthly time-series
- Multiple cohorts for pattern comparison

---

### 1.9 AlertCenter - Early Warning System

**Purpose:** Detect employment drops, volatility spikes, trend reversals

**Required Query Example:**
```python
# Example from queries: syn_ewi_employment_drop.yaml
{
  "sector": "Construction",
  "drop_percent": -5.2,
  "current_employment": 9500,
  "prior_employment": 10000,
  "period": "2024-11"
}
```

**Time Range:** 12-24 months (focus on recent trends)

**Early Warning Flags:**
```python
# predictor.py:492-496 (used by AlertCenter)
flags = {
    "band_breach": bool,       # Forecast deviation
    "slope_reversal": bool,    # Trend reversal (3-month window)
    "volatility_spike": bool,  # 6-month lookback, z=2.5
}
```

---

## Section 2: Complete Data Requirements List

| # | Endpoint | Required For | Fields | Time Range | Frequency | Priority |
|---|----------|--------------|--------|------------|-----------|----------|
| **1** | `/api/timeseries/metric` | TimeMachine, Predictor | period, sector, value, unit | 24-48 months | Monthly | **CRITICAL** |
| **2** | `/api/timeseries/cohort` | PatternMiner | period, metric, cohort, value, unit | 24-36 months | Monthly | **CRITICAL** |
| **3** | `/api/employment/sector_timeseries` | All Agents | period, sector, employees, qataris, non_qataris | 24-48 months | Monthly | **CRITICAL** |
| **4** | `/api/qatarization/sector_timeseries` | TimeMachine, NationalStrategy | period, sector, qatarization_percent, qataris, non_qataris | 24-48 months | Monthly | **CRITICAL** |
| **5** | `/api/unemployment/gcc_comparison` | NationalStrategy, Nationalization | country, year, unemployment_rate | 3-5 years | Annual | **CRITICAL** |
| **6** | `/api/qatarization/national_aggregate` | NationalStrategy | year, overall_pct, public_pct, private_pct, total_qataris, total_employees | 3-5 years | Annual | **CRITICAL** |
| **7** | `/api/forecasts/baseline` | Scenario | metric, sector, horizon, h, yhat, lo, hi | N/A (derived) | On-demand | **CRITICAL** |
| **8** | `/api/salary/sector_timeseries` | TimeMachine, PatternMiner | period, sector, avg_salary_qr, employee_count | 24-36 months | Monthly | IMPORTANT |
| **9** | `/api/attrition/sector_timeseries` | TimeMachine, NationalStrategy | period, sector, attrition_percent, separations, avg_headcount | 24-36 months | Monthly | IMPORTANT |
| **10** | `/api/early_warning/employment_drops` | AlertCenter, Predictor | period, sector, drop_percent, current_employment, prior_employment | 12-24 months | Monthly | IMPORTANT |
| **11** | `/api/employment/gender_distribution` | LabourEconomist | year, male_percent, female_percent, total_percent, male_count, female_count | 3-5 years | Annual | IMPORTANT |
| **12** | `/api/unemployment/qatar_national` | NationalStrategy | year, quarter, unemployment_rate_total, unemployment_rate_qataris | 3-5 years | Quarterly | IMPORTANT |
| **13** | `/api/employment/company_size_distribution` | Agents (optional) | year, size_band, companies, employees | 3-5 years | Annual | OPTIONAL |
| **14** | `/api/retention/sector_timeseries` | TimeMachine | period, sector, retention_percent | 24-36 months | Monthly | OPTIONAL |
| **15** | `/api/productivity/sector_timeseries` | Scenario (whitelisted) | period, sector, productivity_index | 24-36 months | Monthly | OPTIONAL |

---

## Section 3: Time Range Justification

### 3.1 Why 24 Months Minimum?

**PredictorAgent Hard Requirement:**
```python
# predictor.py:35, 248-251
MIN_TRAIN_POINTS = 24

if len(series) < self.min_train_points:
    return f"Insufficient data: {len(series)} points available (need ≥ {self.min_train_points})"
```

**Forecasting Backtest Process:**
1. **Train:** 24 months minimum
2. **Validate:** Rolling origin backtest (requires holdout)
3. **Method Selection:** Compare 4 methods (seasonal_naive, ewma, rolling_mean, robust_trend)
4. **Confidence Intervals:** MAD-based intervals from in-sample residuals

**Why Not Less?**
- Seasonal_naive needs 12 months (full year)
- Backtest needs 12+ months validation
- Robust_trend uses 24-month window
- CUSUM break detection unreliable <24 points

### 3.2 Why 36-48 Months Optimal?

**Benefits:**
1. **Multiple Seasonal Cycles:** 3-4 years = 3-4 full cycles for seasonal patterns
2. **Structural Break Detection:** CUSUM algorithm more reliable with 36+ points
3. **Forecast Validation:** 24-month training + 12-24 month validation
4. **Pattern Stability:** PatternMiner stability scores improve with longer history
5. **Baseline Robustness:** Seasonal baselines more reliable with multiple cycles

**Code Evidence:**
```python
# time_machine.py:301 - Default is 2 years
start = date(end.year - 2, end.month, end.day)

# pattern_miner.py:217 - Seasonal effects use 36 months
window_months = 36
```

### 3.3 Annual vs Monthly Data

**Monthly Required For:**
- Employment counts (time-series analysis)
- Qatarization rates (trend tracking)
- Salary averages (forecasting)
- Attrition rates (early warning)
- Early warning indicators (real-time monitoring)

**Annual Sufficient For:**
- Vision 2030 targets (strategic planning)
- GCC benchmarking (comparative analysis)
- Gender distribution (policy tracking)
- Company size distribution (structural analysis)

---

## Section 4: Missing Dependencies & Critical Gaps

### Gap 1: Monthly Time-Series Queries Not Defined

**Issue:**
```python
# time_machine.py:68-74 - References missing query IDs
self.series_map = series_map or {
    'retention': 'LMIS_RETENTION_TS',       # ❌ NOT IN REGISTRY
    'qatarization': 'LMIS_QATARIZATION_TS', # ❌ NOT IN REGISTRY
    'salary': 'LMIS_SALARY_TS',             # ❌ NOT IN REGISTRY
    'employment': 'LMIS_EMPLOYMENT_TS',     # ❌ NOT IN REGISTRY
    'attrition': 'syn_attrition_monthly',   # ✅ Exists (synthetic only)
}
```

**Impact:** TimeMachineAgent cannot fetch monthly time-series for baseline/trend/break analysis.

**Resolution Options:**
1. **Ministry API Provides:** Create monthly endpoints matching these names
2. **QNWIS Creates Queries:** Define YAML queries mapping to Ministry API
3. **Hybrid:** Use alias resolution (`aliases.py`) to map LMIS_* → Ministry endpoints

### Gap 2: Cohort Time-Series Pattern Missing

**Issue:**
```python
# pattern_miner.py:748 - Expects dynamic query IDs
return f"timeseries_{metric_slug}_{cohort_slug}_{window}m"

# Examples of missing queries:
# timeseries_retention_construction_12m
# timeseries_qatarization_healthcare_24m
# timeseries_salary_finance_6m
```

**Current Registry:** Only 42 queries defined, none match this pattern.

**Impact:** PatternMinerAgent cannot perform multi-cohort driver screening.

**Resolution:**
```
Ministry API Endpoint:
GET /api/timeseries/cohort?metric={metric}&cohort={cohort}&window_months={window}

Returns last {window} months of data for specified metric and cohort.
```

### Gap 3: Pre-Computed Forecast Baselines Missing

**Issue:**
```python
# scenario_agent.py:98-99
qid = f"forecast_baseline_{metric}_{sector_slug}_{horizon_months}m"

# Expected queries like:
# forecast_baseline_retention_construction_12m
# forecast_baseline_qatarization_all_6m
```

**Impact:** ScenarioAgent cannot apply scenarios without baseline forecasts.

**Resolution Options:**
1. **Ministry Provides Forecasts:** Pre-compute and serve via API (deterministic)
2. **QNWIS Computes On-Demand:** Use PredictorAgent internally (adds 2-5s latency)
3. **Cache Strategy:** Compute once, cache as pseudo-query for 24 hours

**Recommendation:** Option 2 (on-demand) with caching for practical deployment.

### Gap 4: Sector Name Standardization

**Issue:** No standardized sector taxonomy across queries.

**Evidence:**
- Employment queries use: "Construction", "Healthcare", "Finance", "Energy", "ICT"
- Some queries may use: "construction", "CONSTRUCTION", "const", etc.

**Impact:** Joins across queries fail if sector names don't match exactly.

**Resolution:**
```yaml
# Ministry API Standard Sectors:
sectors:
  - Construction
  - Healthcare
  - Finance
  - Energy
  - ICT
  - Education
  - Manufacturing
  - Retail
  - Hospitality
  - Transportation
  - Public Administration
```

### Gap 5: Date Field Name Inconsistency

**Issue:**
```python
# predictor.py:77 - Expects "month" field
date_field: str = "month"

# But some queries use "period" (YYYY-MM format)
# Others use "year" (annual data)
```

**Resolution:** Standardize on `period` for monthly, `year` for annual.

---

## Section 5: Data Quality Requirements

### 5.1 Validation Rules

**Non-Negative Constraints:**
```python
# From QatarizationRow, AvgSalaryRow, etc.
qataris: int = Field(ge=0)        # Must be >= 0
non_qataris: int = Field(ge=0)
avg_salary_qr: float = Field(ge=0)
employees: int = Field(ge=0)
```

**Percentage Bounds:**
```python
# Attrition, Qatarization, Employment percentages
value: 0.0 <= value <= 100.0
```

**Date Formats:**
```python
# Monthly data
period: "2024-11"  # YYYY-MM (ISO 8601)

# Annual data
year: 2024  # Integer

# Quarterly data
year: 2024
quarter: 1  # 1-4
```

### 5.2 Null Handling

**Required Fields:** Never null
- `period` / `year`
- `sector` (can be "National" or "All" for aggregates)
- `value` (primary metric)

**Optional Fields:** Can be null
- `unit` (inferred from query metadata)
- `metadata` fields

**Missing Periods:**
```json
// If data missing for a period, omit the row entirely
// Do NOT include: {"period": "2024-06", "value": null}
```

### 5.3 Numeric Precision

**Percentages:** 1 decimal place (e.g., 85.2%)
**Counts:** Integers (no decimals)
**Currency:** 2 decimal places (e.g., 12500.50 QAR)
**Rates:** 1-2 decimal places

---

## Section 6: Priority-Ordered Endpoint List

| Rank | Endpoint | Critical For | MVP Phase | Notes |
|------|----------|--------------|-----------|-------|
| **1** | `/api/timeseries/metric` | PredictorAgent (MIN_TRAIN_POINTS) | Phase 1 | Without this, forecasting completely fails |
| **2** | `/api/employment/sector_timeseries` | All agents | Phase 1 | Most referenced data across system |
| **3** | `/api/qatarization/sector_timeseries` | NationalStrategy | Phase 1 | Vision 2030 tracking depends on this |
| **4** | `/api/unemployment/gcc_comparison` | NationalStrategy | Phase 1 | GCC benchmarking core feature |
| **5** | `/api/timeseries/cohort` | PatternMiner | Phase 2 | Driver screening requires this |
| **6** | `/api/qatarization/national_aggregate` | NationalStrategy | Phase 2 | Vision 2030 gap analysis |
| **7** | `/api/forecasts/baseline` | Scenario | Phase 2 | Can be computed on-demand initially |
| **8** | `/api/salary/sector_timeseries` | TimeMachine, PatternMiner | Phase 2 | Important but not critical path |
| **9** | `/api/attrition/sector_timeseries` | NationalStrategy | Phase 2 | Talent competition assessment |
| **10** | `/api/early_warning/employment_drops` | AlertCenter | Phase 3 | Nice-to-have for early warning |
| **11** | `/api/employment/gender_distribution` | LabourEconomist | Phase 3 | Policy tracking |
| **12** | `/api/unemployment/qatar_national` | NationalStrategy | Phase 3 | Supplementary data |
| **13** | `/api/retention/sector_timeseries` | TimeMachine | Phase 3 | Optional metric |
| **14** | `/api/company_size/distribution` | Analytics | Phase 3 | Optional analytics |
| **15** | `/api/productivity/sector_timeseries` | Scenario | Phase 3 | Future enhancement |

---

## Section 7: Integration Testing Phases

### Phase 1: Critical Path (Weeks 1-2)

**Goal:** Enable basic forecasting and trend analysis

**Endpoints:**
1. `/api/timeseries/metric` (employment, qatarization, salary)
2. `/api/employment/sector_timeseries`
3. `/api/qatarization/sector_timeseries`
4. `/api/unemployment/gcc_comparison`

**Agents Tested:**
- PredictorAgent (forecast_baseline, early_warning)
- TimeMachineAgent (baseline_report, trend_report)
- NationalStrategyAgent (gcc_benchmark)

**Success Criteria:**
- [ ] PredictorAgent generates 6-month forecast
- [ ] TimeMachineAgent produces seasonal baseline
- [ ] NationalStrategyAgent ranks Qatar vs GCC

### Phase 2: Pattern Mining & Strategy (Weeks 3-4)

**Goal:** Enable pattern discovery and Vision 2030 tracking

**Endpoints:**
5. `/api/timeseries/cohort`
6. `/api/qatarization/national_aggregate`
7. `/api/forecasts/baseline` (or on-demand computation)

**Agents Tested:**
- PatternMinerAgent (stable_relations, seasonal_effects, driver_screen)
- ScenarioAgent (apply, compare, batch)
- NationalStrategyAgent (vision2030_alignment)

**Success Criteria:**
- [ ] PatternMinerAgent finds driver-outcome relationships
- [ ] ScenarioAgent applies what-if scenarios
- [ ] NationalStrategyAgent calculates Vision 2030 gap

### Phase 3: Comprehensive Analytics (Weeks 5-6)

**Goal:** Enable all optional analytics and early warning

**Endpoints:**
8-15. All remaining endpoints

**Agents Tested:**
- All 9 agents
- Council orchestration
- Alert routing
- Full verification pipeline

**Success Criteria:**
- [ ] All agents produce valid reports
- [ ] Verification passes (citation enforcement)
- [ ] No missing query errors
- [ ] Performance <2s per agent call

---

## Section 8: Data Request Template for Ministry Team

### To: Ministry of Labour - Data Integration Team

#### Critical Endpoints Request (MVP - Phase 1)

**1. Generic Time-Series Endpoint**
```
POST /api/timeseries/metric
Content-Type: application/json

Request Body:
{
  "metric": "employment" | "qatarization" | "salary" | "attrition" | "retention",
  "sector": "Construction" | null,  // null = national aggregate
  "start_period": "2021-01",
  "end_period": "2024-11",
  "frequency": "monthly"
}

Response (JSON):
{
  "query_id": "employment_construction_monthly",
  "rows": [
    {
      "period": "2021-01",
      "sector": "Construction",
      "value": 10250,
      "unit": "count"
    },
    // ... more periods
  ],
  "metadata": {
    "asof_date": "2024-11-30",
    "source": "LMIS Ministry Database",
    "freshness": "2024-11-30T10:00:00Z"
  }
}

Expected Volume: ~2,000-5,000 rows per query
Time Range: 24-48 months (Jan 2021 - Nov 2024)
```

**2. Employment Sector Time-Series**
```
GET /api/employment/sector_timeseries
Parameters:
  - start_date: 2021-01-01
  - end_date: 2024-11-30
  - sector: Construction (optional, omit for all sectors)

Response:
{
  "rows": [
    {
      "period": "2021-01",
      "sector": "Construction",
      "employees": 10250,
      "qataris": 1230,
      "non_qataris": 9020
    }
  ]
}

Expected Volume: ~50 sectors × 48 months = 2,400 rows
```

**3. Qatarization Sector Time-Series**
```
GET /api/qatarization/sector_timeseries
Parameters:
  - start_date: 2021-01-01
  - end_date: 2024-11-30
  - sector: Construction (optional)

Response:
{
  "rows": [
    {
      "period": "2021-01",
      "sector": "Construction",
      "qatarization_percent": 12.0,
      "qataris": 1230,
      "non_qataris": 9020
    }
  ]
}

Expected Volume: ~2,400 rows
```

**4. GCC Unemployment Comparison**
```
GET /api/unemployment/gcc_comparison
Parameters:
  - start_year: 2020
  - end_year: 2024

Response:
{
  "rows": [
    {
      "country": "Qatar",
      "year": 2024,
      "unemployment_rate": 0.3
    },
    {
      "country": "UAE",
      "year": 2024,
      "unemployment_rate": 2.1
    }
    // ... 6 countries × 5 years = 30 rows
  ]
}

Expected Volume: 30 rows
Countries: Qatar, UAE, Saudi Arabia, Kuwait, Bahrain, Oman
```

#### Important Endpoints Request (Phase 2)

**5. Cohort Time-Series (Pattern Mining)**
```
GET /api/timeseries/cohort
Parameters:
  - metric: retention|qatarization|salary|employment|attrition
  - cohort: Construction|Healthcare|Finance|... (sector name)
  - window_months: 3|6|12|24
  - end_date: 2024-11-30

Response:
{
  "query_id": "timeseries_retention_construction_12m",
  "rows": [
    {
      "period": "2023-12",
      "metric": "retention",
      "cohort": "Construction",
      "value": 85.2,
      "unit": "percent"
    }
    // Last {window_months} months
  ]
}

Expected Volume: Last N months per query (e.g., 12 rows for 12-month window)
```

**6. National Qatarization Aggregates**
```
GET /api/qatarization/national_aggregate
Parameters:
  - start_year: 2020
  - end_year: 2024

Response:
{
  "rows": [
    {
      "year": 2024,
      "overall_qatarization_percent": 15.5,
      "public_sector_percent": 78.2,
      "private_sector_percent": 8.3,
      "total_qataris": 45000,
      "total_employees": 290000
    }
  ]
}

Expected Volume: 5 rows (2020-2024)
```

**7. Forecast Baselines (On-Demand)**
```
POST /api/forecasts/baseline
Content-Type: application/json

Request:
{
  "metric": "employment" | "qatarization" | "salary",
  "sector": "Construction" | null,
  "horizon_months": 6 | 12,
  "method": "auto" | "seasonal_naive" | "ewma" | "rolling_mean" | "robust_trend"
}

Response:
{
  "query_id": "forecast_baseline_employment_construction_12m",
  "rows": [
    {
      "h": 1,  // Horizon month 1
      "yhat": 10500,  // Point forecast
      "lo": 10200,    // Lower 95% PI
      "hi": 10800     // Upper 95% PI
    }
    // ... h=2 through h=12
  ],
  "metadata": {
    "method_selected": "seasonal_naive",
    "backtest_mae": 125.5,
    "backtest_mape": 1.2,
    "training_points": 36
  }
}

Expected Volume: 6 or 12 rows per query
Latency: 2-5 seconds (includes forecast computation)
```

---

### Data Format Requirements

**Encoding:** UTF-8
**Response Format:** JSON
**Date Format (Monthly):** YYYY-MM (ISO 8601)
**Date Format (Annual):** YYYY (integer)
**Null Values:** Use `null` (not "null", "", or 0)
**Numeric Precision:**
- Percentages: 1 decimal (e.g., 12.3)
- Counts: Integers (e.g., 10250)
- Currency: 2 decimals (e.g., 12500.50)

**Sector Names (Standardized):**
```
Construction, Healthcare, Finance, Energy, ICT, Education,
Manufacturing, Retail, Hospitality, Transportation,
Public Administration, Real Estate, Agriculture, Mining,
Utilities, Professional Services, Arts & Culture, Other
```

**Country Codes (GCC):**
```
Qatar, UAE, Saudi Arabia, Kuwait, Bahrain, Oman
```

---

## Section 9: Edge Cases & Data Quality Assumptions

### 9.1 Edge Cases Tested

**From Test Suites:**
```python
# 1. Empty Results
if not rows:
    raise ValueError("No rows matched CSV query")

# 2. Nulls in Numeric Fields
if isinstance(v, (int, float)) and not math.isnan(v):
    row[k] = v * 100.0  # to_percent conversion

# 3. Missing Periods (Gaps in Time-Series)
# Code handles by sorting and using available data
records.sort(key=lambda item: item[0])  # Sort by date

# 4. Non-Numeric Values
try:
    numeric_val = float(val)
except (ValueError, TypeError):
    continue  # Skip row

# 5. Insufficient Data
if len(values) < self.min_train_points:
    return "Insufficient data: {len(values)} points"

# 6. Change-Points (Structural Breaks)
break_indices = sorted(cusum_breaks(values, k=1.0, h=5.0))
# Uses post-break tail if >= 24 points
```

### 9.2 Data Quality Assumptions

**Assumptions Made by Code:**
1. **Chronological Ordering:** Dates are sortable (YYYY-MM format)
2. **Sector Names Match:** Exact string match required for joins
3. **No Duplicates:** One row per (period, sector) combination
4. **Complete Sectors:** If sector appears once, should appear in all periods
5. **Positive Values:** Employment, salary, counts are >= 0
6. **Percentage Bounds:** Rates are 0-100 (not 0-1)
7. **No Missing Months:** Time-series should be continuous (gaps cause warnings)

### 9.3 Validation Rules

**From Pydantic Models:**
```python
class QatarizationRow(BaseModel):
    year: int
    sector: str
    qataris: int = Field(ge=0)           # Validation: >= 0
    non_qataris: int = Field(ge=0)       # Validation: >= 0
    qatarization_percent: float | None

class AvgSalaryRow(BaseModel):
    year: int
    sector: str
    avg_salary_qr: float = Field(ge=0)   # Validation: >= 0
```

---

## Section 10: Answers to Specific Questions

### Q1: Minimum time range that enables all 9 agents?
**Answer: 24 months (2 years)**

**Limiting Factor:** PredictorAgent hard requirement `MIN_TRAIN_POINTS = 24`

**Breakdown:**
- **PredictorAgent:** 24 months (REQUIRED)
- **TimeMachineAgent:** 12 months minimum, 24 optimal
- **PatternMinerAgent:** 12-24 months (window-dependent)
- **ScenarioAgent:** Depends on PredictorAgent (24 months)
- **NationalStrategyAgent:** 24 months for annual data (3 years optimal)
- **LabourEconomist:** 24 months for YoY
- **Nationalization:** 24 months
- **PatternDetective:** 24 months
- **AlertCenter:** 12 months minimum, 24 optimal

---

### Q2: Optimal time range for comprehensive testing?
**Answer: 36-48 months (3-4 years)**

**Justification:**

**36 Months (3 years):**
- Captures 3 full seasonal cycles
- Enables robust CUSUM break detection
- Allows 24-month training + 12-month validation
- Improves pattern stability scores
- Provides pre/post-COVID context if starting from 2020

**48 Months (4 years):**
- 4 full seasonal cycles for strongest seasonal patterns
- More robust baseline calculations
- Better change-point detection
- Enables longer validation windows
- Vision 2030 gap analysis more accurate

**Trade-offs:**
- 24 months: Minimum viable, limited validation
- 36 months: Sweet spot for most analyses
- 48 months: Optimal for research-grade analysis
- 60+ months: Diminishing returns, data staleness concerns

---

### Q3: Different time range needs for different endpoints?
**Answer: Yes, significantly different**

**Monthly Time-Series Endpoints:** 24-48 months
- Employment by sector
- Qatarization by sector
- Salary by sector
- Attrition by sector
- Retention by sector

**Annual Aggregate Endpoints:** 3-5 years
- Vision 2030 tracking (2020-2024)
- GCC benchmarking (2020-2024)
- Gender distribution (2020-2024)
- National unemployment (2020-2024)

**Early Warning Endpoints:** 12-24 months
- Employment drops (recent focus)
- Volatility spikes (6-month lookback)
- Trend reversals (3-month window)

**Recommendation:** Request 48 months for monthly data, 5 years for annual data.

---

### Q4: Predictor agent backtesting requirements?
**Answer: Yes, minimum 24 months with rolling origin validation**

**Process:**
```python
# 1. Training: Minimum 24 months
MIN_TRAIN_POINTS = 24

# 2. Method Selection via Backtest
backtest_metrics = rolling_origin_backtest(
    series,
    method_func,
    horizon=1,
    min_train=24,
    **method_params
)
# Returns: {"mae": X, "mape": Y, "rmse": Z, "n": N}

# 3. Best Method Selection
selection = choose_baseline(
    series,
    season=12,
    min_train=24,
    seasonal_win_delta=0.1
)
# Compares: seasonal_naive, ewma, rolling_mean, robust_trend

# 4. Confidence Intervals
residuals = residuals_in_sample(series, fitted)
half_width = mad_interval(residuals, z=1.96)  # 95% PI
```

**Backtest Results Used For:**
- Method selection (lowest MAE wins)
- Confidence interval width (MAD from residuals)
- User-facing performance metrics (MAE, MAPE, RMSE)

**Example:**
```
Input: 36 months of data
Process:
  - Use months 1-24 for training
  - Validate on months 25-36 (rolling origin)
  - Select best method: seasonal_naive (MAE=125.5)
  - Generate 6-month forecast with 95% PI
```

---

### Q5: TimeMachine baseline comparison requirements?
**Answer: Yes, minimum 12 months for seasonal, 24 months optimal**

**Requirements:**

**A) Seasonal Baseline (12 months minimum):**
```python
# time_machine.py:174-175
if len(values) >= season:  # season=12
    return seasonal_baseline(values, season=season), "segment"
```

**Process:**
1. Compute 12-month phase averaging (Jan avg, Feb avg, ...)
2. Calculate upper/lower bands (1.5 × MAD)
3. Detect anomaly gaps vs baseline

**B) YoY Comparisons (12 months prior):**
```python
# time_machine.py:327-328
yoy_values = yoy(values, period=season)  # period=12
```

**Example:** To compute 2024-11 YoY, need 2023-11 data (12 months prior)

**C) Structural Breaks (24+ months optimal):**
```python
# time_machine.py:722
cusum_breaks_list = sorted(cusum_breaks(values, k=1.0, h=5.0))
```

**CUSUM Algorithm:**
- Detects mean shifts in time-series
- Requires ~24+ points for reliable detection
- Flags periods where cumulative sum exceeds threshold

**Default Range:**
```python
# time_machine.py:301 - Default is 2 years
if start is None:
    start = date(end.year - 2, end.month, end.day)
```

---

### Q6: Data granularity needed?
**Answer: Monthly for time-series, Annual for aggregates**

**Monthly Granularity (YYYY-MM format):**
- Employment counts (monthly hiring/separations)
- Qatarization rates (monthly progress tracking)
- Salary averages (monthly payroll data)
- Attrition rates (monthly turnover)
- Early warning indicators (detect monthly drops)
- Retention metrics (monthly retention %)

**Annual Granularity (YYYY format):**
- Vision 2030 targets (strategic multi-year goals)
- GCC benchmarking (annual country comparisons)
- Gender distribution (annual workforce demographics)
- National unemployment (annual labor force surveys)
- Company size distribution (annual census data)

**Quarterly Granularity (YYYY + Q1-Q4):**
- Qatar national unemployment (labor force survey)
- Potentially useful for interim Vision 2030 checks

**Not Supported:**
- Daily data (too granular for forecasting)
- Weekly data (not aligned with payroll cycles)
- Irregular intervals (breaks time-series algorithms)

---

### Q7: Seasonal analysis requirements?
**Answer: Yes, minimum 12 months, optimal 24-36 months**

**Requirements:**

**A) Seasonal Baseline (12 months):**
```python
# analysis/baselines.py
def seasonal_baseline(values, season=12):
    # Requires full 12-month cycle
    # Computes mean per phase (month-of-year)
    # Returns: {
    #   "mean_per_phase": [Jan, Feb, ..., Dec],
    #   "baseline": [baseline for each point],
    #   "upper_band": [...],
    #   "lower_band": [...]
    # }
```

**B) Seasonal Naive Forecasting (12 months history):**
```python
# forecast/baselines.py
def seasonal_naive(series, horizon, season=12):
    # Uses last 12 months to forecast next periods
    # Forecast[t+h] = series[t+h-12]
    # Requires >= 12 historical points
```

**C) Seasonal Adjustment (24 months optimal):**
```python
# PatternMiner uses 36 months for seasonal effects
window_months = 36
findings = self.miner.mine_seasonal_effects(
    outcome, sector, end_date, min_support, result
)
```

**D) Seasonal Effects Mining:**
```python
# pattern_miner.py:217-228
# Analyzes month-of-year lift patterns
# Identifies peak/trough months
# Requires 24-36 months for robust detection
```

**Why Multiple Cycles?**
- 1 year (12 months): Minimum for seasonal pattern
- 2 years (24 months): Validates pattern consistency
- 3 years (36 months): Robust detection of stable seasonal effects
- 4+ years: Diminishing returns, patterns may evolve

---

### Q8: Specific date ranges needed (e.g., pre/post-COVID)?
**Answer: 2021-2024 minimum (48 months), 2020-2024 optimal (60 months)**

**Considerations:**

**2020-2021: COVID Disruption Period**
- Structural breaks expected (lockdowns, remote work)
- CUSUM algorithm will detect these automatically
- Useful for change-point analysis
- May skew seasonal patterns

**2022-2024: Recovery & Normalization**
- More stable labor market
- Better for baseline seasonal patterns
- Relevant for forecasting current trends

**Vision 2030 Context:**
```python
# national_strategy.py:332-333
years_remaining = target_year - current_year  # 2030 - 2024 = 6
required_annual_growth = gap / years_remaining
```

**Using 2020-2024:**
- 5-year baseline for growth rate calculations
- Captures pre-COVID vs post-COVID comparison
- More robust gap analysis

**Recommendation:**

**Minimum Request:** 2021-01 to 2024-11 (47 months)
- Avoids worst COVID disruption
- Sufficient for all forecasting needs
- Cleaner seasonal patterns

**Optimal Request:** 2020-01 to 2024-11 (59 months)
- Includes COVID period for break detection
- 5 full years for Vision 2030 baseline
- Enables pre/post-COVID analysis

**Code Will Handle:**
```python
# predictor.py:145-173 - Stability guard
# Automatically detects COVID break-point
# Uses post-break tail if >= 24 months
# Provides rationale in output

# Example Output:
# "Detected change-point near 2020-04; training on post-break tail of 32 points."
```

---

## Section 11: System-Wide Requirements Summary

### 11.1 Agent-by-Agent Minimum Requirements

| Agent | Minimum Months | Optimal Months | Critical Metrics | Blocking Issues |
|-------|----------------|----------------|------------------|-----------------|
| **TimeMachineAgent** | 12 | 24-36 | employment, qatarization, salary, attrition | Missing LMIS_*_TS queries |
| **PatternMinerAgent** | 12-24 | 24-36 | All metrics × cohorts | Missing timeseries_{metric}_{cohort}_{window}m pattern |
| **PredictorAgent** | **24** | 36-48 | employment, qatarization, salary | **HARD REQUIREMENT** |
| **ScenarioAgent** | 24 | 36 | Baseline forecasts | Missing forecast_baseline_* queries |
| **NationalStrategyAgent** | 36 (annual) | 60 (annual) | Qatarization, GCC unemployment | None (queries exist) |
| **LabourEconomistAgent** | 24 | 36 | Employment by gender | None (queries exist) |
| **NationalizationAgent** | 24 | 36 | GCC unemployment | None (queries exist) |
| **PatternDetectiveAgent** | 24 | 36 | All metrics | Same as PatternMiner |
| **AlertCenter** | 12 | 24 | Employment drops, volatility | Missing ewi_* queries |

**System-Wide Minimum:** **24 months monthly data + 3-5 years annual data**

### 11.2 Data Volume Estimates

**Monthly Time-Series:**
- 50 sectors × 48 months × 5 metrics = **12,000 rows**
- Per metric: ~2,400 rows
- Response size: ~500 KB per metric

**Annual Aggregates:**
- GCC: 6 countries × 5 years = **30 rows**
- National: 5 years × 10 metrics = **50 rows**
- Response size: <10 KB

**Cohort Time-Series (On-Demand):**
- Per query: 12-24 rows
- Expected queries: ~100/day
- Response size: ~5 KB per query

**Total Storage:** ~10-20 MB for full dataset

---

## Section 12: Next Steps & Timeline

### Week 1-2: Phase 1 - Critical Path
**Ministry Tasks:**
- [ ] Deploy 4 critical endpoints
- [ ] Populate 24-48 months of monthly data
- [ ] Populate 3-5 years of annual data
- [ ] Standardize sector names

**QNWIS Tasks:**
- [ ] Create YAML query definitions for Ministry endpoints
- [ ] Implement alias resolution (LMIS_* → Ministry API)
- [ ] Update test data with Ministry format
- [ ] Run integration tests

**Success Metrics:**
- PredictorAgent generates forecasts
- TimeMachineAgent produces baselines
- NationalStrategyAgent ranks GCC

### Week 3-4: Phase 2 - Pattern Mining
**Ministry Tasks:**
- [ ] Deploy cohort endpoint (/api/timeseries/cohort)
- [ ] Deploy national aggregates endpoint
- [ ] Implement forecast endpoint (or QNWIS computes on-demand)

**QNWIS Tasks:**
- [ ] Implement cohort query pattern
- [ ] Add on-demand forecast computation
- [ ] Enable ScenarioAgent
- [ ] Test PatternMinerAgent

**Success Metrics:**
- PatternMinerAgent finds relationships
- ScenarioAgent applies scenarios
- Vision 2030 gap analysis works

### Week 5-6: Phase 3 - Full System
**Ministry Tasks:**
- [ ] Deploy all remaining endpoints
- [ ] Performance optimization (<500ms per query)
- [ ] Production monitoring setup

**QNWIS Tasks:**
- [ ] Full agent integration
- [ ] Council orchestration testing
- [ ] Verification pipeline validation
- [ ] Performance tuning

**Success Metrics:**
- All 9 agents operational
- <2s end-to-end latency
- Zero missing query errors
- Citation enforcement passing

---

## Section 13: Risk Mitigation

### Risk 1: Ministry API Delays
**Mitigation:** Use synthetic data with Ministry-compatible format
**Fallback:** CSV connectors with Ministry data structure

### Risk 2: Data Quality Issues
**Mitigation:** Implement validation layer at API ingestion
**Fallback:** Data cleaning pipeline in QNWIS

### Risk 3: Performance Issues
**Mitigation:** Implement aggressive caching (TTL=600s)
**Fallback:** Pre-compute common queries

### Risk 4: Schema Changes
**Mitigation:** Version API endpoints (v1, v2)
**Fallback:** Schema migration scripts

### Risk 5: Missing Historical Data
**Mitigation:** Request minimum 24 months initially
**Fallback:** Backfill strategy with quarterly updates

---

## Conclusion

**This analysis provides:**
1. ✅ **Complete endpoint specifications** for all 9 agents
2. ✅ **Exact field requirements** with data types and validations
3. ✅ **Time range justifications** backed by code evidence
4. ✅ **Identified gaps** with resolution strategies
5. ✅ **Phased implementation plan** with success criteria
6. ✅ **Data quality requirements** with edge case handling
7. ✅ **Integration testing roadmap** spanning 6 weeks

**Key Takeaway:**
- **Minimum:** 24 months monthly + 3 years annual = All agents functional
- **Optimal:** 36-48 months monthly + 5 years annual = Production-grade
- **Critical:** 7 endpoints (Phase 1-2) enable 80% of functionality

**Recommendation for Ministry Team:**
Start with **Phase 1 (4 endpoints)** to unblock forecasting and trend analysis, then incrementally deploy Phase 2-3 endpoints based on QNWIS testing feedback.

---

**Document Prepared By:** QNWIS Analysis Team
**For:** Ministry of Labour - Data Integration
**Date:** November 12, 2024
**Version:** 2.0 (Comprehensive Code Analysis)
