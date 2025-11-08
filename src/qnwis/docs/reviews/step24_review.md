# Step 24 Review: Pattern Miner Hardening

## Math & Ranking Policy
- **Effect size:** Default `spearman` (monotonic, rank-based) with `pearson` opt-in; correlation outputs are clamped to `[-1, 1]`. Lift deltas are bounded to `±500%` as a guardrail against unstable denominators.
- **Season-adjusted effects:** When both driver/outcome series expose `value_sa` (or `<metric>_sa`) columns, correlations run on the SA pairs, and findings flag `seasonally_adjusted=True` so narratives can call it out.
- **Support:** Computed from the actual overlapping observations that land inside the requested window (`metrics.support(len(aligned_driver), min_support)`); seasonal analysis additionally enforces per-month minimums.
- **Stability:** Determined by the inverse of the summed variance of windowed slopes (`1 / (1 + Σ(slope - mean)^2)`), returning 1.0 for perfectly consistent slopes and trending toward 0 as variance grows. This keeps scores in `[0,1]` while penalizing jittery trends.
- **Ranking key:** Findings are sorted by `(-support, -stability, -|effect|, driver_name)` to favor well-supported, stable signals with deterministic tie-breaking.

## Rigor, Safety & Observability
- **Freshness passthrough:** Every derived QueryResult now passes `freshness_like` (list of upstream `Freshness` objects) into `make_derived_query_result`, ensuring Step 21 freshness metadata reaches narratives and downstream verification.
- **Source tracking:** All narratives list the sorted `source_qids`, and driver/seasonal tables include an `Adj.` column explaining when a seasonally adjusted series powered the effect.
- **Confidence hints:** Public agent entrypoints accept an optional Step-22 payload (e.g., `{"score": 84, "band": "GREEN"}`) and render `> Confidence hint (Step 22): …` at the top of each report without altering failure logic.
- **Warnings:** Missing driver/cohort data now surfaces deterministic limitations (e.g., “Missing drivers: promotion_rate”), satisfying Step 19 auditability requirements.
- **Prompts:** Templates already mandated “cite each number with (QID=…)”; deterministic narratives now reinforce this by tagging tables with derived QIDs.

## Tests Added / Updated
- **Metrics:** `tests/unit/patterns/test_metrics.py` now covers lift clamping, inverse-variance stability behavior, and ensures volatile series score lower than smooth trends.
- **Pattern miner core:** `tests/unit/patterns/test_miner.py` updated for `SeriesPoint` alignment, seasonally adjusted effects, ranking priority, and includes the micro-benchmark (`TestPatternMinerPerformance.test_driver_screen_micro_benchmark_under_budget` verifies 5 cohorts × 4 windows × 4 drivers completes <200 ms).
- **Agents:** `tests/unit/agents/test_pattern_miner.py` injects deterministic timeseries fixtures to exercise the real mining code paths (freshness passthrough, warnings, confidence hints). `tests/integration/agents/test_pattern_miner_integration.py` now runs the agent end-to-end against `MockDataClient`.
- **Regression guard:** `python -m pytest tests/unit/patterns/test_metrics.py tests/unit/patterns/test_miner.py tests/unit/agents/test_pattern_miner.py tests/integration/agents/test_pattern_miner_integration.py`

## Future Tuning Knobs
1. **Stability sensitivity:** adjust or normalize the variance sum (e.g., divide by window count or rescale by absolute mean slope) if certain datasets require softer penalization.
2. **Seasonal thresholds:** expose per-month support minimums (currently `max(3, min_support // 12)`) to configuration for domains with denser sampling.
3. **Ranking weights:** allow an optional weighting vector (e.g., emphasize stability for compliance scenarios) while keeping deterministic tie-breaking.
4. **Confidence mapping:** feed support/stability summaries into the Step-22 payload when the orchestrator does not provide one, giving downstream consumers a fallback hint.
