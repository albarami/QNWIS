# Ministry of Labour API - Complete Data Requirements Analysis
## QNWIS Integration Testing Requirements

**Date:** November 12, 2024  
**Status:** Comprehensive Analysis Complete

---

## Executive Summary

**Minimum Viable Time Range:** 24 months (2 years)  
**Optimal Time Range:** 36-48 months (3-4 years)  
**Critical Endpoints:** 5 core endpoints  
**Important Endpoints:** 5 supporting endpoints  
**Optional Endpoints:** 5+ enhancement endpoints

---

## Section 1: Complete Data Requirements

### 1.1 CRITICAL ENDPOINTS (Tier 1)

#### 1. Employment Time-Series by Sector
**Endpoint:** `/api/employment/sector_timeseries`  
**Required For:** TimeMachineAgent, PatternMinerAgent, PredictorAgent  
**Fields:**
- `period` (YYYY-MM format, monthly)
- `sector` (string)
- `employees` (integer)
- `qataris` (integer)
- `non_qataris` (integer)

**Time Range:** 24-48 months | **Frequency:** Monthly | **Priority:** CRITICAL

---

#### 2. Qatarization Time-Series by Sector
**Endpoint:** `/api/qatarization/sector_timeseries`  
**Required For:** TimeMachineAgent, PatternMinerAgent, NationalStrategyAgent  
**Fields:**
- `period` (YYYY-MM)
- `sector` (string)
- `qatarization_percent` (float: 0-100)
- `qataris` (integer)
- `non_qataris` (integer)

**Time Range:** 24-48 months | **Frequency:** Monthly | **Priority:** CRITICAL

---

#### 3. Generic Time-Series for Pattern Mining
**Endpoint:** `/api/timeseries/metric_by_cohort`  
**Required For:** PatternMinerAgent  
**Parameters:** `metric`, `cohort`, `start_date`, `end_date`  
**Fields:**
- `period` (YYYY-MM)
- `metric` (string: retention, qatarization, salary, employment, attrition)
- `cohort` (string: sector name or "all")
- `value` (float)
- `unit` (string)

**Time Range:** 24-36 months | **Frequency:** Monthly | **Priority:** CRITICAL

---

#### 4. National Qatarization Aggregates
**Endpoint:** `/api/qatarization/national_aggregate`  
**Required For:** NationalStrategyAgent (Vision 2030 tracking)  
**Fields:**
- `year` (integer)
- `overall_qatarization_percent` (float)
- `public_sector_percent` (float)
- `private_sector_percent` (float)
- `total_qataris` (integer)
- `total_employees` (integer)

**Time Range:** 3-5 years | **Frequency:** Annual | **Priority:** CRITICAL

---

#### 5. GCC Unemployment Comparison
**Endpoint:** `/api/unemployment/gcc_comparison`  
**Required For:** NationalStrategyAgent  
**Fields:**
- `country` (string: Qatar, UAE, Saudi Arabia, Kuwait, Bahrain, Oman)
- `year` (integer)
- `unemployment_rate` (float: 0-100)

**Time Range:** 2-3 years | **Frequency:** Annual | **Priority:** CRITICAL

---

### 1.2 IMPORTANT ENDPOINTS (Tier 2)

#### 6. Salary Time-Series by Sector
**Endpoint:** `/api/salary/sector_timeseries`  
**Fields:** period, sector, avg_salary_qr, employee_count  
**Time Range:** 24-36 months | **Frequency:** Monthly/Quarterly | **Priority:** IMPORTANT

#### 7. Attrition Time-Series by Sector
**Endpoint:** `/api/attrition/sector_timeseries`  
**Fields:** period, sector, attrition_percent, separations, avg_headcount  
**Time Range:** 24-36 months | **Frequency:** Monthly | **Priority:** IMPORTANT

#### 8. Qatar National Unemployment
**Endpoint:** `/api/unemployment/qatar_national`  
**Fields:** year, quarter, unemployment_rate_total, unemployment_rate_qataris  
**Time Range:** 3-5 years | **Frequency:** Annual/Quarterly | **Priority:** IMPORTANT

#### 9. Early Warning - Employment Drops
**Endpoint:** `/api/early_warning/employment_drops`  
**Fields:** period, sector, drop_percent, current_employment, prior_employment  
**Time Range:** 12-24 months | **Frequency:** Monthly | **Priority:** IMPORTANT

#### 10. Employment Gender Distribution
**Endpoint:** `/api/employment/gender_distribution`  
**Fields:** year, male_percent, female_percent, male_count, female_count  
**Time Range:** 3-5 years | **Frequency:** Annual | **Priority:** IMPORTANT

---

## Section 2: Time Range Justification

### 2.1 Forecasting (PredictorAgent)
**Minimum:** 24 months  
**Reason:** Forecast backtesting requires 24 points minimum. Seasonal naive needs 12 months history + 12 months for validation.

**Optimal:** 36-48 months  
**Reason:** Captures multiple seasonal cycles, enables CUSUM break detection, provides robust confidence intervals.

**Code Evidence:** `MIN_TRAIN_POINTS = 24` (predictor.py line 35)

---

### 2.2 Trend Analysis (TimeMachineAgent)
**Minimum:** 24 months  
**Reason:** YoY comparisons need 12 months prior + seasonal baseline needs 12-month cycle.

**Optimal:** 36 months  
**Reason:** Structural break detection (CUSUM) needs 24+ points, baseline stability improves with 2-3 years.

**Code Evidence:** Default range is 2 years (time_machine.py line 301)

---

### 2.3 Pattern Mining (PatternMinerAgent)
**Minimum:** 12-24 months (depends on window parameter)  
**Reason:** Supports windows of 3, 6, 12, 24 months. Minimum support = 12 observations.

**Optimal:** 24-36 months  
**Reason:** Allows 12-month pattern analysis with 12-month validation. Seasonal adjustment needs 24 months.

**Code Evidence:** `if window not in [3, 6, 12, 24]` (pattern_miner.py line 80)

---

### 2.4 Vision 2030 Tracking (NationalStrategyAgent)
**Minimum:** 3 years (2022-2024)  
**Reason:** Calculate required annual growth from current to 2030 target (6 years remaining).

**Optimal:** 5 years (2020-2024)  
**Reason:** Captures pre/post-COVID patterns for robust baseline.

**Code Evidence:** `years_remaining = target_year - current_year` (national_strategy.py line 332)

---

## Section 3: Missing Dependencies & Gaps

### Gap 1: Monthly Time-Series Query IDs
**Issue:** Code references `LMIS_RETENTION_TS`, `LMIS_QATARIZATION_TS`, `LMIS_SALARY_TS`, `LMIS_EMPLOYMENT_TS` which don't exist in query registry.

**Impact:** TimeMachineAgent cannot fetch monthly data.

**Resolution:** Ministry API must provide monthly endpoints OR QNWIS creates query definitions.

---

### Gap 2: Sector-Specific Forecasts
**Issue:** ScenarioAgent expects pre-computed forecasts like `forecast_baseline_retention_construction_12m`.

**Impact:** Scenario planning requires baseline forecasts to exist.

**Resolution:** Either Ministry provides forecasts OR QNWIS generates on-demand (adds latency).

---

### Gap 3: Cohort Time-Series
**Issue:** PatternMinerAgent builds query IDs like `timeseries_retention_construction_12m` which don't exist.

**Impact:** Cannot perform multi-cohort driver screening.

**Resolution:** Ministry API must support: `/api/timeseries?metric=retention&cohort=construction&window=12`

---

## Section 4: Priority-Ordered Endpoints

| Rank | Endpoint | Required For | Time Range | Priority |
|------|----------|--------------|------------|----------|
| 1 | `/api/employment/sector_timeseries` | TimeMachine, PatternMiner, Predictor | 24-48 months | **CRITICAL** |
| 2 | `/api/qatarization/sector_timeseries` | TimeMachine, PatternMiner, NationalStrategy | 24-48 months | **CRITICAL** |
| 3 | `/api/timeseries/metric_by_cohort` | PatternMiner | 24-36 months | **CRITICAL** |
| 4 | `/api/qatarization/national_aggregate` | NationalStrategy | 3-5 years | **CRITICAL** |
| 5 | `/api/unemployment/gcc_comparison` | NationalStrategy | 2-3 years | **CRITICAL** |
| 6 | `/api/salary/sector_timeseries` | TimeMachine, PatternMiner | 24-36 months | IMPORTANT |
| 7 | `/api/attrition/sector_timeseries` | TimeMachine, NationalStrategy | 24-36 months | IMPORTANT |
| 8 | `/api/unemployment/qatar_national` | NationalStrategy | 3-5 years | IMPORTANT |
| 9 | `/api/early_warning/employment_drops` | Predictor, AlertCenter | 12-24 months | IMPORTANT |
| 10 | `/api/employment/gender_distribution` | NationalStrategy | 3-5 years | IMPORTANT |

---

## Section 5: Data Request Template

### To: Ministry of Labour - Data Integration Team

#### Critical Endpoints Request (MVP)

**1. Employment Time-Series**
```
Endpoint: /api/employment/sector_timeseries
Parameters: start_date=2021-01-01, end_date=2024-12-31, frequency=monthly
Expected Volume: ~2,000 records (48 months × 40 sectors)
```

**2. Qatarization Time-Series**
```
Endpoint: /api/qatarization/sector_timeseries
Parameters: start_date=2021-01-01, end_date=2024-12-31, frequency=monthly
Expected Volume: ~2,000 records
```

**3. Generic Time-Series (Pattern Mining)**
```
Endpoint: /api/timeseries/metric_by_cohort
Parameters: metric={retention|qatarization|salary|employment|attrition}, cohort={sector|all}
Time Range: 2021-01-01 to 2024-12-31
```

**4. National Qatarization**
```
Endpoint: /api/qatarization/national_aggregate
Parameters: start_year=2020, end_year=2024
Expected Volume: 5 records
```

**5. GCC Unemployment**
```
Endpoint: /api/unemployment/gcc_comparison
Parameters: start_year=2022, end_year=2024
Expected Volume: 18 records (6 countries × 3 years)
```

### Data Format Requirements
- **Date Format:** ISO 8601 (YYYY-MM-DD, YYYY-MM for periods)
- **Encoding:** UTF-8
- **Response Format:** JSON
- **Null Handling:** Use `null` for missing values
- **Sector Names:** Standardized (Construction, Healthcare, Finance, Energy, ICT, etc.)

---

## Section 6: Answers to Specific Questions

### Q1: Minimum time range that enables all 9 agents?
**Answer: 24 months (2 years)**

**Limiting Factor:** PredictorAgent requires 24 months for forecast backtesting.

---

### Q2: Optimal time range for comprehensive testing?
**Answer: 36-48 months (3-4 years)**

**Justification:**
- Forecasting: 36 months = 24-month training + 12-month validation
- Seasonal Patterns: 3 years captures multiple cycles
- Structural Breaks: 36+ months enables CUSUM detection
- Vision 2030: 4-5 years provides better baseline

---

### Q3: Different time range needs for different endpoints?
**Answer: Yes**

- **Monthly Time-Series:** 24-48 months (employment, qatarization, salary, attrition)
- **Annual Aggregates:** 3-5 years (Vision 2030, GCC benchmarking)
- **Early Warning:** 12-24 months (recent trends)

---

### Q4: Predictor agent backtesting requirements?
**Answer: Yes, minimum 2 years (24 months)**

**Process:**
- Training: 24 months minimum
- Validation: Rolling origin backtest with horizon=1
- Method Selection: Compares seasonal_naive, ewma, rolling_mean, robust_trend
- Confidence Intervals: MAD-based intervals from in-sample residuals

---

### Q5: TimeMachine baseline comparison requirements?
**Answer: Yes, minimum 2 years**

**Requirements:**
- Seasonal Baseline: 12-month phase averaging (needs full annual cycle)
- YoY Comparisons: Requires 12 months prior (e.g., 2024-11 vs 2023-11)
- Structural Breaks: CUSUM needs 24+ points for reliable detection
- Default Range: 2 years (code default: `date(end.year - 2, end.month, end.day)`)

---

### Q6: Data granularity needed?
**Answer: Monthly for time-series, Annual for aggregates**

**Monthly:**
- Employment counts
- Qatarization rates
- Salary averages
- Attrition rates
- Early warning indicators

**Annual/Quarterly:**
- Vision 2030 targets
- GCC benchmarking
- Gender distribution
- National unemployment

---

### Q7: Seasonal analysis requirements?
**Answer: Yes, minimum 12 months, optimal 24-36 months**

**Requirements:**
- Seasonal Baseline: 12-month phase averaging
- Seasonal Naive Forecasting: Requires 12 months history
- Seasonal Adjustment: Pattern mining uses 24 months for detrending
- Seasonal Effects Mining: 36 months optimal (3 full cycles)

---

### Q8: Specific date ranges needed (e.g., pre/post-COVID)?
**Answer: Not explicitly required, but 2020-2024 range captures COVID impact**

**Considerations:**
- **2020-2021:** COVID disruption period
- **2022-2024:** Recovery and normalization
- **Structural Breaks:** CUSUM algorithm will automatically detect COVID-related regime changes
- **Vision 2030:** 5-year baseline (2020-2024) provides pre/post-COVID context

**Recommendation:** Request 2021-2024 minimum (48 months), 2020-2024 optimal (60 months)

---

## Summary Table: Time Range by Agent

| Agent | Minimum | Optimal | Critical Metrics |
|-------|---------|---------|------------------|
| **TimeMachineAgent** | 24 months | 36 months | Employment, Qatarization, Salary, Attrition |
| **PatternMinerAgent** | 24 months | 36 months | All metrics × cohorts |
| **PredictorAgent** | 24 months | 36-48 months | Employment, Qatarization, Salary |
| **ScenarioAgent** | Depends on Predictor | 36 months | Baseline forecasts |
| **NationalStrategyAgent** | 3 years | 5 years | Qatarization, Unemployment, GCC data |
| **LabourEconomist** | 24 months | 36 months | Employment, Salary |
| **Nationalization** | 24 months | 36 months | Qatarization time-series |
| **PatternDetective** | 24 months | 36 months | Pattern discovery |
| **AlertCenter** | 12 months | 24 months | Early warning indicators |

**System-Wide Minimum:** 24 months  
**System-Wide Optimal:** 36-48 months

---

## Next Steps

1. **Ministry Team:** Review and confirm endpoint availability
2. **QNWIS Team:** Create query definitions mapping to Ministry API
3. **Testing:** Phase 1 (Critical endpoints) → Phase 2 (Important) → Phase 3 (Optional)
4. **Timeline:** 4 weeks for full integration testing

