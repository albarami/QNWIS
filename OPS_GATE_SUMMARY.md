# Ops Gate Summary

- Generated: 2025-11-10T09:21:06.331830Z
- Overall Status: PASS

## Performance Benchmarks

- p50 latency: 1.303 ms
- p95 latency: 1.354 ms
- Samples: 10 runs / 200 rules

## Determinism Scan

- Status: PASS
- No forbidden datetime.now/time.time/random.* usage detected.

## Gate Status

| Gate | Status | Message |
| --- | --- | --- |
| alerts_completeness | PASS | All modules loaded and rules validated |
| alerts_accuracy | PASS | All accuracy tests passed |
| alerts_performance | PASS | Performance target met: p95=1.35ms |
| alerts_determinism | PASS | Alert stack determinism guard passed |
| alerts_audit | PASS | Audit pack generation successful |