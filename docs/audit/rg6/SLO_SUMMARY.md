# RG-6 Resilience Gate Report

- **slo_presence**: PASS (count=3)
- **sli_accuracy**: PASS
- **budget_correctness**: PASS (samples=3)
- **burnrate_alerts**: PASS
- **resilience_perf**: PASS (p95_ms=0.011)

## SLOs
- `api_availability`: availability_pct objective=99.9 window_days=14
- `api_error_rate`: error_rate_pct objective=1.0 window_days=14
- `api_latency_p95`: latency_ms_p95 objective=200.0 window_days=7

## Budget Snapshot

- Samples: 3 (source=synthetic_zero_load)
- Avg Remaining %: 100.0 / Min Remaining %: 100.0
- Avg Minutes Left: 241.92 / Min Minutes Left: 20.16
- Burn p95 (fast/slow): 0.0 / 0.0
- Burn max (fast/slow): 0.0 / 0.0

| SLO | Remaining % | Minutes Left | Burn Rate (fast/slow) |
| --- | --- | --- | --- |
| api_availability | 100.000 | 20.160 | 0.000 / 0.000 |
| api_error_rate | 100.000 | 201.600 | 0.000 / 0.000 |
| api_latency_p95 | 100.000 | 504.000 | 0.000 / 0.000 |
