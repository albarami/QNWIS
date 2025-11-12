## Step 39 Review - Enterprise Chainlit UI Hardening

**Date:** 12 November 2025  
**Reviewer:** Codex (GPT-5)  
**Scope:** Bring Step-39 in line with the hardened checklist (World Bank units, PatternDetective parity, timing discipline, HTML-free Chainlit) and document the deterministic evidence.

---

### Checklist Status

- **World Bank units:** `_normalize_value` already avoided `*100`; `run_world_bank_query` now writes `QueryResult.metadata["units"] = {"SL.UEM.TOTL.ZS": "percent"}` so every agent has an explicit contract (see `tests/unit/test_worldbank_units.py::test_units_metadata_exposed_for_percent_indicators`).
- **PatternDetective parity:** the legacy consistency check reports `(male + female) - total`, and the unit tests assert both the `-1.0` delta and the `sum_mismatch:-1.0` warning entry.
- **Timing helper:** `Stopwatch` combines UTC timestamps with `perf_counter()` for durations; `run_workflow_stream` also captures UTC start/end so no code mixes `time.time()` with `perf_counter()`.
- **Chainlit Markdown purity:** the sticky timeline is now Markdown-only, the raw evidence view remains Markdown tables, and every message passes through `sanitize_markdown` before `cl.Message.send`.
- **Types, errors, deterministic tests:** new helpers include docstrings and type hints, the World Bank metadata test stubs the integrator deterministically, and the regression timeline test suite verifies the Markdown output has no HTML.

---

### Implementation Highlights

1. **Sticky timeline with durations**
   - `render_stage_timeline_md` (Markdown only) replaces the HTML widget.
   - `handle_message` keeps a single timeline message and updates it after every `StageEvent`.
   - Stage durations come straight from `latency_ms`; the agents stage aggregates the per-agent latencies before being marked complete.

   ```
   **Stage Timeline**

   - DONE  Classify - 46 ms
   - RUN   Prefetch - 12 ms elapsed
   - WAIT  Agents
   - WAIT  Verify
   - WAIT  Synthesize
   - WAIT  Done
   ```

2. **Deterministic evidence expansion**
   - Each finding registers its evidence payload in the session.
   - The **View raw evidence** action re-runs the deterministic query via `DataClient`, caps the preview at five rows, and renders a Markdown table with dataset IDs and freshness metadata.

3. **World Bank metadata**
   - `run_world_bank_query` writes the indicator-to-unit map into `QueryResult.metadata["units"]`.
   - The new unit test patches the integrator to a stub DataFrame so it remains deterministic and never leaves the test harness.

4. **PatternDetective consistency**
   - The legacy `run()` now records `(male + female) - total` with tolerance derived from `SUM_PERCENT_TOLERANCE`.
   - Unit tests assert both the metrics payload (`delta_percent == -1.0`) and the warning string so the check is documented and verified.

5. **Timing and audit hygiene**
   - `Stopwatch` drives the final audit timestamps and durations; all per-stage timing uses `perf_counter()` so there is no drift.
   - The audit payload now includes cache hit/miss/invalidations plus those stopwatch timestamps, satisfying deterministic-layer observability.

---

### Stage Panel Snapshots (Markdown excerpts)

```
## Classify
Intent: pattern.anomalies
Complexity: Medium
Confidence: 86 %
Sectors: Energy, Finance
Time Horizon: 24 months
*Completed in 46 ms*

## Prefetch
RAG context: 3 snippets
Sources: World Bank API, Qatar Open Data
*Completed in 12 ms*

## Agents - PatternDetective
Findings: 2
Status: complete
*Execution time: 118 ms*

## Verify
Citations: pass
Numeric checks: pass
Average confidence: 82 %
*Completed in 41 ms*

## Synthesize
Agents consulted: 5
Total findings: 8
*Completed in 64 ms*

## Done
Queries executed: 14
Data sources: 6
Total time: 1 328 ms
```

---

### Raw Evidence & Audit Examples

```
## Raw Evidence (PatternDetective)

1. syn_attrition_by_sector_latest
   - Dataset: aggregates/attrition_by_sector.csv
   - Freshness: 2025-11-08

| attrition_percent | sector |
| ----------------- | ------ |
| 3.1               | Energy |
| 4.4               | Finance |
```

```
## Audit Trail

Request ID: req_demo
Queries executed: 2
Data sources: 2
Cache: hits 7 / misses 1 (87.5 %)
Total latency: 6.12 s (6123 ms)
Timestamps: 2025-11-12T10:00:00Z -> 2025-11-12T10:00:06Z
```

---

### Model Fallback Transcript

```
2025-11-12 12:18:38,799 WARNING Primary model returned 404. Falling back to backup provider.
```

`TestModelSelector.test_call_with_model_fallback_on_http_404` covers the same scenario.

---

### Tests

```
python -m pytest tests/ui/test_chainlit_orchestration.py \
                 tests/unit/test_worldbank_units.py \
                 tests/unit/regression/test_timeline_state.py
python -m pytest tests/integration/test_e2e_chainlit_workflow.py
```

Both suites passed, demonstrating that the Markdown timeline, units metadata, PatternDetective delta math, and fallback logic all behave deterministically while staying inside the deterministic-layer guarantees and roadmap expectations.
