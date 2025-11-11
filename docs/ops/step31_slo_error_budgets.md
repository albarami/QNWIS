# Step 31: SLO/SLI & Error Budgets (RG-6 Resilience Gate)

## Overview

Production-grade Service Level Objectives (SLO) and error budget tracking for QNWIS API resilience monitoring. Implements deterministic SLI measurement, multi-window burn-rate detection, and automated alerting with notification dispatch integration.

## Architecture

### SLO Core (`src/qnwis/slo/`)

- **models.py**: Pydantic types for `SLIKind`, `SLOTarget`, `ErrorBudgetSnapshot`
- **loader.py**: Deterministic YAML/JSON loader with schema validation and ordering
- **budget.py**: Error budget math (remaining %, minutes left, window calculations)
- **burn.py**: Multi-window burn-rate calculators (fast/slow windows)

### SLI Kinds

1. **latency_ms_p95**: 95th percentile HTTP request latency (milliseconds)
2. **availability_pct**: Percentage of successful requests (1 - 5xx/total)
3. **error_rate_pct**: Percentage of 5xx errors (5xx/total)

### SLO Definitions

SLOs are defined in YAML/JSON under `slo/` directory:

```yaml
slos:
  - id: api_availability
    sli: availability_pct
    objective: 99.9
    window_days: 14
    windows:
      fast_minutes: 5
      slow_minutes: 60
```

**Fields:**
- `id`: Unique SLO identifier
- `sli`: SLI kind (latency_ms_p95, availability_pct, error_rate_pct)
- `objective`: Target value (e.g., 99.9% availability, 200ms latency)
- `window_days`: Rolling evaluation window
- `windows.fast_minutes`: Fast burn-rate window (default: 5)
- `windows.slow_minutes`: Slow burn-rate window (default: 60)

## Error Budget Math

### Allowed Error Fraction

- **Availability SLO**: `(100 - objective) / 100`
  - Example: 99.9% → 0.1% error budget
- **Error Rate SLO**: `objective / 100`
  - Example: 1.0% → 1.0% error budget
- **Latency SLO**: Fixed 5% budget (p95 exceedances)

### Burn Rate

Burn rate = `(actual_error_rate) / (allowed_error_fraction)`

- **Burn rate = 1.0**: Consuming budget at expected rate
- **Burn rate > 1.0**: Consuming budget faster than sustainable
- **Burn rate < 1.0**: Under budget

### Multi-Window Detection

**Fast window (5 minutes)**: Detects acute incidents
**Slow window (60 minutes)**: Confirms sustained degradation

**Alert tiers:**
- **CRITICAL**: fast ≥ 2.0 AND slow ≥ 1.0
- **HIGH**: fast ≥ 1.0 AND slow ≥ 1.0
- **MEDIUM**: fast ≥ 1.0
- **LOW**: slow ≥ 1.0

## CLI Usage

### Validate SLO Definitions

```bash
python -m src.qnwis.cli.qnwis_slo validate --dir slo
```

### Capture SLI Snapshot

```bash
python -m src.qnwis.cli.qnwis_slo snapshot --out docs/audit/rg6/sli_snapshot.json
```

### Compute Error Budgets

```bash
python -m src.qnwis.cli.qnwis_slo budget \
  --dir slo \
  --sli-windows docs/audit/rg6/sli_windows.json \
  --out docs/audit/rg6/budgets.json
```

### Simulate Error Bursts

```bash
python -m src.qnwis.cli.qnwis_slo simulate \
  --fast-bad 10 --fast-total 1000 \
  --slow-bad 100 --slow-total 10000 \
  --window-error-fraction 0.0001 \
  --out docs/audit/rg6/sli_windows.json
```

### Drill Down (Tabular)

```bash
python -m src.qnwis.cli.qnwis_slo drill \
  --dir slo \
  --sli-windows docs/audit/rg6/sli_windows.json
```

## API Endpoints

### List SLOs

```http
GET /api/v1/slo/
```

**Response:**
```json
{
  "slos": [
    {
      "id": "api_availability",
      "sli": "availability_pct",
      "objective": 99.9,
      "window_days": 14,
      "windows": {"fast_minutes": 5, "slow_minutes": 60}
    }
  ]
}
```

### Get Error Budgets

```http
GET /api/v1/slo/budget
```

**Response:**
```json
{
  "budgets": [
    {
      "id": "api_availability",
      "sli": "availability_pct",
      "objective": 99.9,
      "window_days": 14,
      "remaining_pct": 95.5,
      "minutes_left": 19267.2,
      "burn_fast": 0.8,
      "burn_slow": 0.9
    }
  ]
}
```

### Simulate (Admin/Service Only)

```http
POST /api/v1/slo/simulate
Authorization: Bearer <admin-token>

{
  "fast": {"bad": 10, "total": 1000},
  "slow": {"bad": 100, "total": 10000},
  "window_error_fraction": 0.0001
}
```

## Alert Integration

### Burn-Rate Trigger

Alert rules can use `burn_rate` trigger type:

```yaml
rules:
  - rule_id: slo_availability_breach
    metric: availability
    scope:
      level: global
    window:
      months: 3
    trigger:
      type: burn_rate
      fast_threshold: 2.0
      slow_threshold: 1.0
    horizon: 12
    severity: high
```

### Notification Dispatch

Burn-rate alerts automatically map to notification severity:
- **critical** tier → CRITICAL notification
- **high** tier → ERROR notification
- **medium** tier → WARNING notification
- **low** tier → INFO notification

## RG-6 Resilience Gate

### Run Gate

```bash
python -m src.qnwis.scripts.qa.rg6_resilience_gate
```

### Checks

1. **slo_presence**: N SLOs parsed (≥1)
2. **sli_accuracy**: SLI snapshot matches golden (optional)
3. **budget_correctness**: Budget math invariants (0 ≤ remaining_pct ≤ 100, minutes_left ≥ 0)
4. **burnrate_alerts**: Alert engine trips on fast/slow thresholds
5. **resilience_perf**: p95 compute < 50ms for 100 SLOs

### Artifacts

- `docs/audit/rg6/rg6_report.json`: Gate results (JSON)
- `docs/audit/rg6/SLO_SUMMARY.md`: Human-readable summary
- `docs/audit/badges/rg6_pass.svg`: Pass/fail badge

## Performance Targets

- **Budget computation**: p95 < 50ms for 100 SLOs
- **SLI snapshot**: Deterministic (no datetime.now/random)
- **Burn-rate evaluation**: < 5ms per rule

## Determinism

All operations are deterministic:
- Uses `ManualClock` in tests
- No `datetime.now()`, `time.time()`, or `random.*`
- YAML/JSON loading with stable ordering
- Reproducible p95 calculations

## Runbook

### Incident: High Burn Rate

1. Check `/api/v1/slo/budget` for current state
2. Review `docs/audit/rg6/sli_snapshot.json` for SLI trends
3. Inspect alert evidence for tier classification
4. If CRITICAL: page on-call, investigate 5xx spike
5. If HIGH: escalate to team lead
6. If MEDIUM/LOW: monitor and document

### Maintenance: Update SLO Targets

1. Edit `slo/*.yaml` definitions
2. Run `qnwis_slo validate` to verify schema
3. Commit changes
4. Deploy (SLOs hot-reload on next API call)

### Testing: Simulate Error Burst

1. Use `qnwis_slo simulate` to generate windows
2. Run `qnwis_slo budget` to compute impact
3. Verify alert triggers with `AlertEngine.evaluate()`

## References

- [Google SRE Book - SLO Chapter](https://sre.google/sre-book/service-level-objectives/)
- [Multi-Window Burn Rate](https://sre.google/workbook/alerting-on-slos/)
- Step 28: Alert Center (trigger integration)
- Step 29: Notifications (dispatch pipeline)
