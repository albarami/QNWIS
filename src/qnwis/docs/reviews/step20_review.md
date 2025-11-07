# Step-20 Result Verification Review (Hardened)

## Highlights
- ✅ **Docstrings + hints**: All public verification entry points retain full docstrings and now emit actionable retry hints on every failure code.
- ✅ **Extraction coverage**: Regex + unit classifiers validated on 1,234 / 87.5% / +2.3 pp / QAR 18,500 combinations (see `tests/unit/verification/test_result_verifier.py::TestNumericClaimExtraction`).
- ✅ **Segment-aware binding**: Claim sentences mentioning a sector/company now restrict lookups to matching rows (default `segment_fields`: sector, industry, company, employer, segment, country).
- ✅ **Ambiguity handling**: When multiple QueryResults match and no QID is cited we emit `AMBIGUOUS_SOURCE` (warning) plus a “add query_id” hint; QIDs continue to bypass ambiguity checks.
- ✅ **Derived consistency**: Derived `QueryResult` percent/share columns are recomputed on the fly from stored row components; any mismatch remains matched (for traceability) but surfaces as `ROUNDING_MISMATCH` (error) with the recomputed value.

## Tolerances & Policies
- **Counts / currency**: `abs_epsilon` still 0.5 (counts) / 50 (currency). Relative tolerance remains 1%.
- **Percent claims**: All comparisons convert to `[0, 1]` internally; tolerance expressed in percentage points (default 0.5 pp) converts to ratio space automatically.
- **Rounding mismatches**: Only triggered when the difference exceeds the acceptance window but is within `2 × abs_epsilon`. Larger gaps fall back to `CLAIM_NOT_FOUND` so we no longer mislabel large errors as rounding issues.
- **Derived checks**: Enabled by default via `derived_share_check_enabled`; requires at least two non-percent numeric columns (`derived_share_min_components`, default 2). Uses same percent tolerance (0.5 pp).
- **Runtime budget**: `report.runtime_ms` recorded for every run; enforcement optional but telemetry is now attached to verification metadata.

## Edge-Case Coverage
- **Numbers w/ formatting**: Regex accepts thousand separators, leading `+/-`, “pp/bps” suffixes, and currency codes preceding numbers. Added regression test `test_extract_handles_commas_signs_and_currency`.
- **Segment binding**: Demonstrated in `test_segment_aware_binding_prefers_matching_row`, ensuring identical values across rows bind to the row whose label appears in the claim sentence.
- **Ambiguous sources**: `test_ambiguous_sources_without_query_id` covers multi-source hits → warning, while `verify_numbers` test ensures the issue surfaces in reports.
- **Rounding hints**: `test_verify_rounding_mismatch_hint_included` ensures hints look like “Replace 1,000 with 1,000.8 (QID: ...)”.
- **Derived mismatch**: `test_derived_share_recomputation_flags_inconsistency` + `test_verify_derived_share_inconsistency` cover share-of-total recomputations and error propagation.

## Math & Tables
- **Bullet groups**: Existing percentage-sum detector retained; math checks now return both booleans and structured metadata (stored under `math_check_details`). Failures emit `MATH_INCONSISTENT` (error) with hints (“Adjust values to reach 100.0 (current 99.0)”).
- **Markdown tables**: New parser scans pipe tables and compares summed columns against a `Total` row, tolerant to currency/percent formatting. Example failure scenario: Energy 1000 + Finance 2000 vs Total 3500 → emitted `table_total_L5_C2`.

## Severity & Retry UX
- `CLAIM_NOT_FOUND`, `UNIT_MISMATCH`, and `MATH_INCONSISTENT` are always `error`, matching verify-node expectations.
- Each issue carries a `hint`, e.g., `CLAIM_NOT_FOUND` now suggests the closest value/QID when available.
- `AMBIGUOUS_SOURCE` remains warning (per requirements) but includes candidate QIDs to speed agent retries.

## Performance Measurements
- Stress test (≈400 repeated findings, ~14 k chars) executed in **~438 ms** on the dev workstation (`report.runtime_ms = 437.66`), well under the 5 s budget.
- Unit suite (`tests/unit/verification/test_result_verifier.py`, 30 tests) completes in ~2.3 s locally, covering extraction, binding, math tables, derived recomputations, and runtime guard.

## Next Steps / Observations
- Consider extending derived recomputation beyond share-of-total (e.g., rank ordering heuristics) if new derived operations appear.
- Runtime telemetry now available; wiring a hard budget gate in orchestration would be trivial if desired.
