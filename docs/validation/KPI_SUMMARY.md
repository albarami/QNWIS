# Validation KPI Summary

- **Pass rate:** 20/20 (100.0%)
- **Verification pass:** 20/20 (100.0%)

| Tier | Envelope (ms) | p50 latency (ms) | p95 latency (ms) |
|------|---------------|------------------|------------------|
| Dashboard | 3000 | 10.12 | 10.53 |
| Simple | 10000 | 10.39 | 10.54 |
| Medium | 30000 | 10.38 | 10.83 |
| Complex | 90000 | 10.51 | 10.89 |

_Compare these latencies with `/metrics` (histograms such as `qnwis_validation_latency_ms`) to confirm production SLO alignment._
