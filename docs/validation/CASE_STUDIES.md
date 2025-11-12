# QNWIS Real-World Case Studies

**Generated:** Validation Results  
**Purpose:** Executive review of system performance on real Ministry questions  

---

## Attrition Rate Retail

**Case ID:** `attrition_rate_retail`  
**Endpoint:** `/api/v1/query`  
**Tier:** simple  
**Latency:** 10.54 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-ATTRITION-RATE-RETAIL`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "1d"
  },
  "citations": [
    "LMIS Attrition Time-Series"
  ],
  "audit_id": "AUD-ATTRITION-RATE-RETAIL"
}
```

---

## Dashboard Kpis

**Case ID:** `dashboard_kpis`  
**Endpoint:** `/api/v1/dashboard/kpis`  
**Tier:** dashboard  
**Latency:** 10.07 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-DASHBOARD-KPIS`  

**OpenAPI:** [Data API - Dashboard](../api/step27_service_api.md#dashboard-kpis)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "1h"
  },
  "citations": [
    "LMIS Aggregates"
  ],
  "audit_id": "AUD-DASHBOARD-KPIS"
}
```

---

## Early Warning Manufacturing

**Case ID:** `early_warning_manufacturing`  
**Endpoint:** `/api/v1/query`  
**Tier:** medium  
**Latency:** 10.72 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-EARLY-WARNING-MANUFACTURING`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "1d"
  },
  "citations": [
    "Early Warning Employment Drops"
  ],
  "audit_id": "AUD-EARLY-WARNING-MANUFACTURING"
}
```

---

## Employment Forecast Hospitality

**Case ID:** `employment_forecast_hospitality`  
**Endpoint:** `/api/v1/query`  
**Tier:** complex  
**Latency:** 10.12 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-EMPLOYMENT-FORECAST-HOSPITALITY`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "recent"
  },
  "citations": [
    "LMIS Employment Time-Series",
    "Forecast Model"
  ],
  "audit_id": "AUD-EMPLOYMENT-FORECAST-HOSPITALITY"
}
```

---

## Employment Trend Construction

**Case ID:** `employment_trend_construction`  
**Endpoint:** `/api/v1/query`  
**Tier:** medium  
**Latency:** 10.38 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-EMPLOYMENT-TREND-CONSTRUCTION`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "2h"
  },
  "citations": [
    "LMIS Employment Time-Series"
  ],
  "audit_id": "AUD-EMPLOYMENT-TREND-CONSTRUCTION"
}
```

---

## Gcc Unemployment Comparison

**Case ID:** `gcc_unemployment_comparison`  
**Endpoint:** `/api/v1/query`  
**Tier:** medium  
**Latency:** 10.32 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-GCC-UNEMPLOYMENT-COMPARISON`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "1d",
    "GCC_STATS": "recent"
  },
  "citations": [
    "GCC Unemployment Comparison"
  ],
  "audit_id": "AUD-GCC-UNEMPLOYMENT-COMPARISON"
}
```

---

## Gender Distribution Public

**Case ID:** `gender_distribution_public`  
**Endpoint:** `/api/v1/query`  
**Tier:** simple  
**Latency:** 10.52 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-GENDER-DISTRIBUTION-PUBLIC`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "1w"
  },
  "citations": [
    "Employment Gender Distribution"
  ],
  "audit_id": "AUD-GENDER-DISTRIBUTION-PUBLIC"
}
```

---

## Health Check

**Case ID:** `health_check`  
**Endpoint:** `/api/v1/query`  
**Tier:** dashboard  
**Latency:** 10.12 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-HEALTH-CHECK`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "system": "realtime"
  },
  "citations": [
    "Operations Health Feed"
  ],
  "audit_id": "AUD-HEALTH-CHECK"
}
```

### Response Excerpt

> LMIS ingestion is healthy with all freshness targets satisfied.

---

## Metrics Endpoint

**Case ID:** `metrics_endpoint`  
**Endpoint:** `/api/v1/query`  
**Tier:** dashboard  
**Latency:** 10.57 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-METRICS-ENDPOINT`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "metrics": "realtime"
  },
  "citations": [
    "SLO Metrics Feed"
  ],
  "audit_id": "AUD-METRICS-ENDPOINT"
}
```

### Response Excerpt

> All KPI tiers meet the configured latency envelopes.

---

## Pattern Mining Retention

**Case ID:** `pattern_mining_retention`  
**Endpoint:** `/api/v1/query`  
**Tier:** complex  
**Latency:** 10.65 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-PATTERN-MINING-RETENTION`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "2h"
  },
  "citations": [
    "LMIS Retention Time-Series",
    "Pattern Mining Analysis"
  ],
  "audit_id": "AUD-PATTERN-MINING-RETENTION"
}
```

---

## Qatarization Rate Banking

**Case ID:** `qatarization_rate_banking`  
**Endpoint:** `/api/v1/query`  
**Tier:** simple  
**Latency:** 10.26 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-QATARIZATION-RATE-BANKING`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "recent"
  },
  "citations": [
    "LMIS Qatarization Time-Series"
  ],
  "audit_id": "AUD-QATARIZATION-RATE-BANKING"
}
```

---

## Retention Drivers Education

**Case ID:** `retention_drivers_education`  
**Endpoint:** `/api/v1/query`  
**Tier:** complex  
**Latency:** 10.82 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-RETENTION-DRIVERS-EDUCATION`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "2h"
  },
  "citations": [
    "LMIS Retention Time-Series",
    "Driver Analysis"
  ],
  "audit_id": "AUD-RETENTION-DRIVERS-EDUCATION"
}
```

---

## Salary Trends Healthcare

**Case ID:** `salary_trends_healthcare`  
**Endpoint:** `/api/v1/query`  
**Tier:** medium  
**Latency:** 10.53 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-SALARY-TRENDS-HEALTHCARE`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "2h"
  },
  "citations": [
    "LMIS Salary Time-Series"
  ],
  "audit_id": "AUD-SALARY-TRENDS-HEALTHCARE"
}
```

---

## Scenario Planning Energy

**Case ID:** `scenario_planning_energy`  
**Endpoint:** `/api/v1/query`  
**Tier:** complex  
**Latency:** 10.37 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-SCENARIO-PLANNING-ENERGY`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "recent"
  },
  "citations": [
    "LMIS Employment Time-Series",
    "Scenario Models"
  ],
  "audit_id": "AUD-SCENARIO-PLANNING-ENERGY"
}
```

---

## Seasonal Patterns Tourism

**Case ID:** `seasonal_patterns_tourism`  
**Endpoint:** `/api/v1/query`  
**Tier:** complex  
**Latency:** 10.08 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-SEASONAL-PATTERNS-TOURISM`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "2h"
  },
  "citations": [
    "LMIS Employment Time-Series",
    "Seasonal Analysis"
  ],
  "audit_id": "AUD-SEASONAL-PATTERNS-TOURISM"
}
```

---

## Sector Comparison Qatarization

**Case ID:** `sector_comparison_qatarization`  
**Endpoint:** `/api/v1/query`  
**Tier:** medium  
**Latency:** 10.17 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-SECTOR-COMPARISON-QATARIZATION`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "1d"
  },
  "citations": [
    "LMIS Qatarization Time-Series"
  ],
  "audit_id": "AUD-SECTOR-COMPARISON-QATARIZATION"
}
```

---

## Skill Gaps Technology

**Case ID:** `skill_gaps_technology`  
**Endpoint:** `/api/v1/query`  
**Tier:** medium  
**Latency:** 10.88 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-SKILL-GAPS-TECHNOLOGY`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "1w"
  },
  "citations": [
    "Skills Database",
    "Sector Analysis"
  ],
  "audit_id": "AUD-SKILL-GAPS-TECHNOLOGY"
}
```

---

## Unemployment Youth

**Case ID:** `unemployment_youth`  
**Endpoint:** `/api/v1/query`  
**Tier:** simple  
**Latency:** 10.12 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-UNEMPLOYMENT-YOUTH`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "1w"
  },
  "citations": [
    "Qatar National Unemployment"
  ],
  "audit_id": "AUD-UNEMPLOYMENT-YOUTH"
}
```

---

## Vision 2030 Progress

**Case ID:** `vision_2030_progress`  
**Endpoint:** `/api/v1/query`  
**Tier:** complex  
**Latency:** 10.92 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-VISION-2030-PROGRESS`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "recent",
    "VISION_2030": "1w"
  },
  "citations": [
    "National Qatarization Aggregate",
    "Vision 2030 Targets"
  ],
  "audit_id": "AUD-VISION-2030-PROGRESS"
}
```

---

## Wage Competitiveness Finance

**Case ID:** `wage_competitiveness_finance`  
**Endpoint:** `/api/v1/query`  
**Tier:** medium  
**Latency:** 10.37 ms  
**Status:** ✓ PASSED  
**Verified:** Yes  
**Citation Coverage:** 1.00  
**Freshness:** Present  

**Audit ID:** `AUD-WAGE-COMPETITIVENESS-FINANCE`  

**OpenAPI:** [Data API - Query](../api/step27_service_api.md#data-api)  

### Audit Trail

```json
{
  "verification": "passed",
  "freshness": {
    "LMIS": "1w",
    "GCC_STATS": "recent"
  },
  "citations": [
    "LMIS Salary Time-Series",
    "GCC Wage Comparison"
  ],
  "audit_id": "AUD-WAGE-COMPETITIVENESS-FINANCE"
}
```

---

## System Metrics

For detailed system performance metrics, see:

- **Prometheus Metrics:** `/metrics` endpoint
- **Health Status:** `/health/ready` endpoint
- **Operations Console:** See Step 30 documentation

---

*This document is auto-generated from validation results. Do not edit manually.*
