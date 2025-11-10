# Step 18 Review — Verification Hardening

## Overview
- Layer 2–4 verification now runs deterministically off the prefetched `QueryResult` cache, so no DB/HTTP or `DataClient` calls occur past the prefetch node.
- Metric aliasing, segment normalization, and expanded privacy regexes close correctness gaps observed in prior dry runs.
- Verification output is surfaced in two ways: a Markdown summary section and explicit redaction reason codes appended at the end of every report that required masking.

## Controls & Enhancements
- **Cross-source matching**
  - Segment keys are trimmed, upper-cased, and defaulted to `ALL`, which prevents false negatives caused by casing or whitespace drift.
  - A canonical alias map (e.g., `qatarization` → `qatarization_rate`) allows heterogeneous datasets to participate in the same tolerance rule.
- **Layer 3 privacy**
  - Regex coverage now spans: RFC-style emails, ≥10 digit IDs, and multi-token names with optional Gulf connectors (`bin/bint/al/al-`).
  - RBAC: only roles listed in `privacy.allow_names_when_role` (default `["allow_names"]`) bypass name redaction; emails/IDs are always masked.
  - Every PII match emits a `PII_*` reason code that is bubbled up to the final report’s “Redaction Reasons” section.
- **Layer 4 sanity**
  - Rate metrics can be flagged per rule for `[0,1]` bounds; all core count metrics have `must_be_non_negative=True`.
  - Freshness parsing continues to warn on stale data, while numeric validation marks non-numeric rows as errors.
- **Verify node integration**
  - Structural validation still runs first; only after it passes do we call the verification engine.
  - The engine summary (`summary_md`) is appended as a dedicated “Verification Summary” section in the formatted report without altering upstream sections.
  - Prefetch cache contents are re-used to reconstruct QueryResults; missing evidence simply logs a debug line while keeping the workflow deterministic.

## Rule Tables

### Cross-Source Tolerances
| Check ID | Metric | Tolerance (%) | Aliases |
| --- | --- | --- | --- |
| retention_rate_consistency | `retention_rate` | 2.0 | n/a |
| qatarization_consistency | `qatarization_rate` | 3.0 | `qatarization`, `qatarization_percent`, `qatarization_pct` |

### Sanity Bounds
| Metric | Constraint | Notes |
| --- | --- | --- |
| `retention_rate`, `qatarization_rate` | `rate_0_1` | Asserts values stay inside `[0,1]`. |
| `headcount`, `employees`, `salary` | `must_be_non_negative` | Salary also sets `min_value=0`. |
| All freshness metadata | `freshness_max_hours=72` | Warns when cache is stale. |

### Privacy Patterns
| Pattern | Regex | Reason Code |
| --- | --- | --- |
| Email | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | `PII_EMAIL` |
| Numeric IDs | `\b\d{10,}\b` (configurable digit floor) | `PII_ID` |
| Names | Capitalized names with optional `bin/bint/al/al-` connectors | `PII_NAME` |

## Integration Diagram
```mermaid
flowchart LR
    Prefetch[Prefetch Cache] --> VerifyL2L4[Verify Node (Layers 2-4)]
    Agent[Agent Report] --> VerifyL2L4
    VerifyL2L4 -->|Summary + Redactions| FormatNode[Format Node]
    FormatNode --> Report[Final Report]
```

## Testing & Benchmark
- **Unit tests** cover cross-check tolerance edge cases, regex coverage, RBAC bypass rules, sanity bounds, verify-node metadata wiring, and formatting changes:
  - `tests/unit/verification/test_layer2_crosschecks.py`
  - `tests/unit/verification/test_layer3_privacy.py`
  - `tests/unit/verification/test_layer4_sanity.py`
  - `tests/unit/verification/test_engine_integration.py`
  - `tests/unit/orchestration/test_verify_node_integration.py`
  - `tests/unit/orchestration/test_format.py`
- **Performance guard**: `test_cross_check_benchmark_under_20ms` asserts the Layer 2 comparison loop completes within 20 ms on 20 segments (measured with `perf_counter`).
- **Reason code propagation** verified via formatting tests that check the new “Redaction Reasons” section and summary section insertion ordering.
