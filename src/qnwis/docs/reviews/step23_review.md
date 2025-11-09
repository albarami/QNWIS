# Step 23 Review – Time Machine Hardening

## Scope
- Hardened `src/qnwis/agents/time_machine.py` to meet determinism, logging, and narrative requirements for `time.baseline`, `time.trend`, and `time.breaks` intents.
- Upgraded derivation pipeline via `src/qnwis/agents/utils/derived_results.py` and the core models in `src/qnwis/data/deterministic/models.py` to carry metadata and freshness for reviewable outputs.
- Added micro-benchmark coverage (`tests/unit/analysis/test_time_machine_perf.py`) and extended unit suites to exercise fallbacks, confidence hints, and change-point explanations.

## Math & Thresholds
- Seasonal baselines now call `_seasonal_baseline_with_scope` which prefers segment-level phase means when at least 12 monthly observations exist and falls back to economy-wide means scaled to the segment average otherwise. MAD-based bands still use `1.5 * MAD` (see `src/qnwis/analysis/baselines.py` and the new helper in `time_machine.py`).
- Growth math (`yoy`, `qtq`, `pct_change`) continues to guard division by zero. Percent formatting remains in `_build_*_narrative` so derived rows preserve raw floats.
- Break detection keeps the documented defaults (`z=2.5`, `h=5.0`) but remains parameterized per call; tests use `cusum_h=3.0` to demonstrate the new explanations.
- Change-point “why flagged” strings combine three ingredients (all optional): jump vs prior month (`pct_change`), deviation vs seasonal baseline, and months since the previous CUSUM break. See `_annotate_break_rows` in `src/qnwis/agents/time_machine.py`.

## Determinism & Logging
- `_extract_series` now sorts by ISO period before returning values/dates, guaranteeing stable evidence tables even when the deterministic layer emits unsorted rows.
- All agent entry points (`baseline_report`, `trend_report`, `breaks_report`) log the metric, sector, window, and thresholds (`logger.info` near lines 300, 404, 677) with no raw values/PII.
- Evidence tables and derived QueryResults all cap lists at `MAX_EVIDENCE_ROWS = 12`. Break rows are sorted by index/method before truncation, so tests can assert file-stable Markdown.

## Derived Outputs & Verifiability
- `make_derived_query_result` now populates `QueryResult.metadata = {"operation", "params", "sources", "row_count"}` and accepts `Freshness` objects or datetime iterables for freshness passthrough. It keeps the oldest `asof_date` and newest `updated_at` across inputs.
- All Time Machine derived calls pass `freshness_like=[result.freshness]` and use allowed units (`percent`, `index`, `unknown`). See `time_machine.py` around lines 330, 368, 430, and 777.

## Enhancements & Narratives
- Segment-aware fallback is disclosed in the baseline executive summary: “Economy-wide fallback seasonal pattern…” when sector data is short. (`_build_baseline_narrative`)
- Trend reports accept `confidence_hint` (dict with `score` and optional `band`) so Step 22’s confidence can be surfaced without affecting gating. Formatter displays `Confidence hint (Step 22): 82/100 (GREEN).`
- Break reports add a dedicated “## Why Flagged” section when any CUSUM rows exist and describe months since the prior break plus % deltas.

## Orchestration Hooks
- Verified router intent catalog already includes the required entries with prefetch hints (`src/qnwis/orchestration/intent_catalog.yml`: `time.baseline`, `time.trend`, `time.breaks`). Registry wiring remains intact (`src/qnwis/orchestration/registry.py`).

## Testing
- Targeted suite: `python -m pytest tests/unit/agents/test_time_machine.py tests/unit/test_utils_derived_results.py tests/unit/analysis/test_time_machine_perf.py`
  - New tests cover sector fallback, confidence hint rendering, and break explanations.
  - Micro-bench asserts the seasonal baseline + YoY/QtQ + EWMA + CUSUM stack stays under 50 ms for an 8-year monthly series.
