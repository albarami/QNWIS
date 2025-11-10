# Step 14 Orchestration Hardening Review

## Summary of Changes
- Enforced registry safety: duplicate registrations rejected (unit-tested) and router now surfaces helpful errors while keeping parameter logs redacted.
- Hardened invoke node with signature-aware argument filtering, config-driven transient retry (one safe retry by default), and observability counters/timers.
- Strengthened verification gate to require findings, evidence with query IDs, freshness metadata, and reproducibility context before formatting.
- Updated formatter to apply documented PII redaction rules, deterministic ordering/truncation, freshness derivation, and sensitive-param redaction.
- Added lightweight metrics observer plumbed through graph, nodes, and error handler; default implementation is a no-op for local runs.
- Tightened orchestration schemas using Pydantic cross-field validators (year ranges, top_n bounds, month windows).

## Deterministic Graph Overview
```
┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
│ Router │─▶│ Invoke │─▶│ Verify │─▶│ Format │
└────────┘   └────────┘   └────────┘   └────────┘
     │                          │            │
     └──────────────────────────┴────────────┘
                          ▼
                      ┌────────┐
                      │ Error  │
                      └────────┘
```
Metrics emit at each transition (`workflow.run.start/success/failure`, `agent.invoke.*`, `agent.verify.*`, `agent.format.*`, `agent.error.handled`).

## Verification & Formatting Rationale
- **Executive Summary Guarantee**: Verification confirms each finding has a title/summary so the formatter can synthesize an executive summary paragraph without fallback text.
- **Evidence & Citations**: Findings must include evidence objects with query IDs and dataset IDs. Formatter deduplicates, sorts `(dataset_id, query_id, locator)`, and truncates to configured top-N for deterministic output.
- **Freshness Channel**: Evidence now carries deterministic freshness timestamps sourced from deterministic queries; formatter converts them into `Freshness` objects (with age-days when parseable). Verification enforces that at least one evidence item supplies freshness metadata.
- **Reproducibility Metadata**: Invoke node persists agent/method names and sanitized parameter keys. Verification ensures these are present before formatting, and formatter redacts sensitive values via `filter_sensitive_params`.
- **PII Redaction Rule**: Formatter swaps capitalised first+last names, email addresses, and 10+ digit identifiers with `[REDACTED_*]` tokens before rendering Markdown sections.

## Intent → Agent Mapping
| Intent | Agent | Method |
| --- | --- | --- |
| pattern.anomalies | PatternDetectiveAgent | detect_anomalous_retention |
| pattern.correlation | PatternDetectiveAgent | find_correlations |
| pattern.root_causes | PatternDetectiveAgent | identify_root_causes |
| pattern.best_practices | PatternDetectiveAgent | best_practices |
| strategy.gcc_benchmark | NationalStrategyAgent | gcc_benchmark |
| strategy.talent_competition | NationalStrategyAgent | talent_competition_assessment |
| strategy.vision2030 | NationalStrategyAgent | vision2030_alignment |

## Test Coverage
- New unit suites guard signature enforcement, retry flow, freshness/PII formatting, and schema cross-field validators.
- Integration workflow test updated to use real intents while ensuring unknown-but-valid intents produce structured errors.
