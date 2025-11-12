# QNWIS Validation Plan

**Purpose:** Deterministic, reproducible validation harness for end-to-end system testing  
**Scope:** 20 real Ministry questions across all complexity tiers  
**Status:** Production-ready  
**Phase Alignment:** Step 38 (Phase 2 extension) building on the Step 37 release tag ([docs/reviews/step37_review.md](../reviews/step37_review.md))  
**Data API Guarantee:** All 20 cases invoke Data API endpoints only (no ad-hoc SQL or direct DB access).  
**Reference Guide:** See `docs/validation/READ_ME_FIRST.md` for runbooks and privacy controls.

---

## Overview

This validation harness executes real Ministry of Labour questions against the QNWIS system, measures accuracy proxies and SLAs, and produces audited case studies for executive review.

### Key Features

- **Deterministic:** Reproducible results with consistent metrics
- **Multi-mode:** HTTP (live), in-process (TestClient), echo (CI)
- **Comprehensive:** 20 cases covering all agent types and complexity tiers
- **Audited:** Full citation tracking and verification status
- **Performance:** SLA enforcement with tier-based envelopes

---

## Case Inventory (20 Deterministic Data API Cases)

| # | Case | Endpoint | Tier | Audit ID |
|---|------|----------|------|----------|
| 1 | Employment Trend - Construction | `/api/v1/query` | Medium | `AUD-EMPLOYMENT-TREND-CONSTRUCTION` |
| 2 | Qatarization Rate - Banking | `/api/v1/query` | Medium | `AUD-QATARIZATION-RATE-BANKING` |
| 3 | GCC Unemployment Comparison | `/api/v1/query` | Simple | `AUD-GCC-UNEMPLOYMENT-COMPARISON` |
| 4 | Vision 2030 Progress | `/api/v1/query` | Complex | `AUD-VISION-2030-PROGRESS` |
| 5 | Salary Trends - Healthcare | `/api/v1/query` | Medium | `AUD-SALARY-TRENDS-HEALTHCARE` |
| 6 | Attrition Rate - Retail | `/api/v1/query` | Simple | `AUD-ATTRITION-RATE-RETAIL` |
| 7 | Employment Forecast - Hospitality | `/api/v1/query` | Complex | `AUD-EMPLOYMENT-FORECAST-HOSPITALITY` |
| 8 | Gender Distribution - Public Sector | `/api/v1/query` | Medium | `AUD-GENDER-DISTRIBUTION-PUBLIC` |
| 9 | Early Warning - Manufacturing | `/api/v1/query` | Medium | `AUD-EARLY-WARNING-MANUFACTURING` |
| 10 | Pattern Mining - Retention | `/api/v1/query` | Complex | `AUD-PATTERN-MINING-RETENTION` |
| 11 | Dashboard KPIs | `/api/v1/dashboard/kpis` | Dashboard | `AUD-DASHBOARD-KPIS` |
| 12 | Sector Comparison - Qatarization | `/api/v1/query` | Medium | `AUD-SECTOR-COMPARISON-QATARIZATION` |
| 13 | Seasonal Patterns - Tourism | `/api/v1/query` | Medium | `AUD-SEASONAL-PATTERNS-TOURISM` |
| 14 | Unemployment - Youth | `/api/v1/query` | Simple | `AUD-UNEMPLOYMENT-YOUTH` |
| 15 | Scenario Planning - Energy | `/api/v1/query` | Complex | `AUD-SCENARIO-PLANNING-ENERGY` |
| 16 | Skill Gaps - Technology | `/api/v1/query` | Medium | `AUD-SKILL-GAPS-TECHNOLOGY` |
| 17 | Retention Drivers - Education | `/api/v1/query` | Medium | `AUD-RETENTION-DRIVERS-EDUCATION` |
| 18 | Wage Competitiveness - Finance | `/api/v1/query` | Complex | `AUD-WAGE-COMPETITIVENESS-FINANCE` |
| 19 | Health Check (Data API) | `/api/v1/query` | Dashboard | `AUD-HEALTH-CHECK` |
| 20 | Metrics Envelope (Data API) | `/api/v1/query` | Dashboard | `AUD-METRICS-ENDPOINT` |

All questions rely solely on the Data API contract outlined in `docs/api/step27_service_api.md`. No direct database calls or ad-hoc SQL are allowed.

---

## Validation Cases

### Case Distribution

| Tier | Count | Max Latency | Description |
|------|-------|-------------|-------------|
| **Dashboard** | 2 | 3s | Real-time KPIs and metrics |
| **Simple** | 5 | 10s | Single-source queries |
| **Medium** | 8 | 30s | Multi-source analysis |
| **Complex** | 5 | 90s | Multi-agent orchestration |

### Coverage by Agent

- **TimeMachineAgent:** 4 cases (employment trends, historical analysis)
- **PatternMinerAgent:** 3 cases (pattern detection, driver analysis)
- **PredictorAgent:** 2 cases (forecasting, early warning)
- **NationalStrategyAgent:** 4 cases (Vision 2030, GCC comparison)
- **ScenarioAgent:** 2 cases (scenario planning)
- **System Guardrails:** 2 Data API cases (readiness and KPI envelope)
- **Multi-agent:** 3 cases (complex orchestration)

---

## Acceptance Envelopes

### Latency Limits

```yaml
dashboard: <3,000 ms   # Real-time dashboards
simple:    <10,000 ms  # Single-agent queries
medium:    <30,000 ms  # Multi-source analysis
complex:   <90,000 ms  # Multi-agent orchestration
```

### Quality Gates

All cases must meet:

1. **Verification Pass:** Deterministic layer verification = `passed`
2. **Citation Coverage:** >=60% of numeric claims cited (or 1.0 when no numeric claims exist)
3. **Freshness Present:** Data source age indicators present
4. **HTTP Status:** 200 or 201
5. **Audit ID:** `metadata.audit_id` present and unique per case
6. **Rate/CSRF Evidence:** Result records capture `X-RateLimit-*` headers plus CSRF cookie presence

---

### Performance Verification Workflow

1. Run the harness (see `docs/validation/READ_ME_FIRST.md`). This produces `validation/summary.csv` and `docs/validation/KPI_SUMMARY.md`.
2. Hit the live `/metrics` endpoint immediately afterwards and confirm latency histograms (for example `qnwis_validation_latency_ms`) align with the values recorded in `KPI_SUMMARY.md`.
3. Capture the findings and a transcript excerpt inside `docs/reviews/step38_review.md` for handover.

---

## Sampling Method

### Case Selection Criteria

Cases were selected to represent:

1. **Real Ministry Questions:** Actual queries from MoL stakeholders
2. **Agent Coverage:** All 6 agents exercised
3. **Complexity Distribution:** Balanced across tiers
4. **Data Source Diversity:** LMIS, GCC stats, Vision 2030 targets
5. **Security Scenarios:** PII redaction, sensitive data handling

### Anonymization

- Personal identifiers: `[REDACTED-ID]`
- Employee codes: `[REDACTED-EMP]`
- Salary amounts: `[REDACTED-SALARY]`
- Financial data: `[REDACTED-AMOUNT]`

---

## Execution Modes

### HTTP Mode (Production)

```bash
python scripts/validation/run_validation.py \
  --mode http \
  --base-url http://localhost:8000
```

Tests against live QNWIS service. Requires:
- Running QNWIS instance
- Valid authentication (if enabled)
- Network connectivity

### In-Process Mode (Integration Testing)

```bash
python scripts/validation/run_validation.py \
  --mode inproc
```

Uses FastAPI TestClient. Requires:
- QNWIS source code
- All dependencies installed
- Database connectivity

### Echo Mode (CI/CD)

```bash
python scripts/validation/run_validation.py \
  --mode echo
```

Simulated execution for CI pipelines. Uses:
- Expected responses from YAML
- Minimal latency simulation
- No external dependencies

---

## Reporting Format

### Summary CSV

`validation/summary.csv` contains:

- `case`: Case identifier
- `endpoint`: API endpoint tested
- `tier`: Complexity tier
- `status`: HTTP status code
- `latency_ms`: Response latency
- `citation_coverage`: Citation ratio [0,1]
- `freshness_present`: Boolean
- `verification_passed`: Boolean
- `pass`: Overall pass/fail

### Detailed JSON

`validation/results/{case}.json` contains:

- `spec`: Full case specification
- `result`: Metrics and pass/fail
- `body`: Complete response body with metadata

### Case Studies

`docs/validation/CASE_STUDIES.md` contains:

- Executive summary per case
- Audit trail excerpts
- Performance metrics
- Pass/fail status

---

## Baseline Comparison

Consultant baseline data in `validation/baselines/*.json`:

| Case | Consultant Time | Consultant Cost | QNWIS Target |
|------|----------------|-----------------|--------------|
| Employment Trends | 45s | 2,500 QAR | <30s |
| Qatarization Rate | 15s | 1,200 QAR | <10s |
| GCC Comparison | 120s | 5,000 QAR | <30s |
| Vision 2030 | 180s | 8,000 QAR | <90s |
| Pattern Mining | 240s | 12,000 QAR | <90s |
| Dashboard KPIs | 8s | 500 QAR | <3s |

**Expected Gains:**
- **Throughput:** 3-10x faster
- **Cost:** 95%+ reduction
- **Quality:** 100% verification vs ~50% manual

---

## Integration with CI/CD

### GitHub Actions

```yaml
- name: Run Validation
  run: |
    python scripts/validation/run_validation.py --mode echo
    python scripts/validation/render_case_studies.py
```

### Pre-deployment Gate

```bash
# Must pass before production deployment
python scripts/validation/run_validation.py --mode http --base-url $STAGING_URL
if [ $? -ne 0 ]; then
  echo "Validation failed - blocking deployment"
  exit 1
fi
```

---

## Maintenance

### Adding New Cases

1. Create `validation/cases/{name}.yaml`
2. Define question, endpoint, tier, acceptance
3. Add redaction rules if needed
4. Run validation to verify
5. Update this document

### Updating Envelopes

1. Analyze latency distribution from results
2. Update tier limits in `metrics.py`
3. Re-run validation
4. Document changes in git commit

### Baseline Updates

1. Collect new consultant performance data
2. Update `validation/baselines/{case}.json`
3. Run comparison: `python scripts/validation/compare_baseline.py`
4. Review improvements

---

## Security Considerations

### PII Protection

- All cases use anonymized data
- Redaction rules applied to responses
- No real employee IDs or names
- Salary ranges aggregated

### Rate Limiting

- Validation runner respects rate limits
- Configurable delays between requests
- Exponential backoff on 429 responses

### Authentication

- Supports API key authentication
- Environment variable: `QNWIS_API_KEY`
- Header: `Authorization: Bearer ${token}`

---

## Success Criteria

- [x] **20 cases executed** across all tiers  
- [x] **Summary & case studies** generated  
- [x] **All envelopes met** (latency, verification, citations)  
- [x] **Scripts & tests pass** locally and in CI  
- [x] **No placeholders** in code or docs  
- [x] **Baseline comparison** shows improvements  

---

## References

- **Metrics Implementation:** `src/qnwis/validation/metrics.py`
- **Runner Script:** `scripts/validation/run_validation.py`
- **Case Studies:** `docs/validation/CASE_STUDIES.md`
- **API Specification:** `docs/api/step27_service_api.md`
- **Performance Targets:** `STEP35_PERFORMANCE_OPTIMIZATION_COMPLETE.md`

---

*Last Updated: 2025-11-12*



