## Step 39 Review – Enterprise Chainlit UI Hardening

**Date**: 12 November 2025  
**Reviewer**: Codex (GPT‑5)  
**Objective**: Assess and harden the enterprise Chainlit UI (Step 39) against the readiness checklist, add the Stage timeline widget, surface raw deterministic evidence, and provide verification artifacts.

---

### Checklist Status

- [x] **All functions typed & complete** – No placeholders in `src/qnwis/ui/chainlit_app.py`, `src/qnwis/orchestration/workflow_adapter.py`, `src/qnwis/verification/ui_bridge.py`, or `src/qnwis/config/model_select.py`.
- [x] **Streaming path verified** – Timeline message renders before graph execution (<1s), StageEvents stream sequentially, and timeline updates reuse a single sticky widget to avoid memory growth (`render_timeline_widget` + `sanitize_markdown`).
- [x] **Sanitization parity (Step‑34)** – Every Chainlit emission (timeline, stage cards, verification, raw evidence, fallback notice) now funnels through `sanitize_markdown`.
- [x] **Deterministic contract honored** – Raw evidence previews re-run registered deterministic queries via `DataClient` (no SQL or ad-hoc stats) and cap output at top‑N rows.
- [x] **RAG carries sources + freshness** – `retrieve_external_context` already enforced citations/freshness; `run_workflow_stream` now passes that blob through to final synthesis without mutation.
- [x] **Audit panel completeness** – `workflow_adapter` aggregates query IDs, sources, cache stats, timestamps, and latency, and `render_audit_panel` surfaces the same.
- [x] **Model fallback tested** – `call_with_model_fallback` handles Anthropic 404s → OpenAI fallback and is covered by unit tests (see transcript below).
- [x] **Latency envelopes** – Timeline widget sends immediately, each StageEvent captures `latency_ms`, and council execution stays within Step‑35 targets on sampled traces.
- [x] **Tests updated** – `python -m pytest tests/ui/test_chainlit_orchestration.py` (unit) and `python -m pytest tests/integration/test_e2e_chainlit_workflow.py` (E2E) both pass.

---

### Implementation Highlights

- **Sticky Stage Timeline** (`src/qnwis/ui/components.py`)  
  A CSS-styled, sanitized widget now anchors to the top-right of the chat, showing completion/active/pending states with badges and detail text. Timeline updates reuse a persisted message to avoid extra frames and reduce load on the Chainlit front end.

- **Raw Evidence Preview Button** (`src/qnwis/ui/chainlit_app.py`, `src/qnwis/verification/ui_bridge.py`)  
  Each agent finding stores a keyed payload in the user session. The new **View raw evidence** action replays the deterministic QueryResult via `DataClient`, sanitizes the rows, and renders a markdown table so analysts can expand beyond the top‑3 evidence summary without leaving the UI.

- **Audit Trail Enrichment** (`src/qnwis/orchestration/workflow_adapter.py:310`)  
  Stage `done` now emits cache hit/miss/invalidations from the deterministic cache layer alongside the existing query IDs, sources, timestamps, and total latency—matching the “audit panel” requirement.

- **Model Fallback Helper** (`src/qnwis/config/model_select.py`)  
  The UI synthesizer wraps its formatting function in `call_with_model_fallback`, logging 404s and switching to the OpenAI model transparently. Fallback state is reflected back to the user with a note if the backup path was exercised.

- **Streaming & Sanitization Hardening** (`src/qnwis/ui/chainlit_app.py`)  
  The initial timeline message is sent (and sanitized) before `run_workflow_stream` yields, guaranteeing sub-second feedback. Every update, including the sticky widget, verification panel, audit trail, and fallback notice, now passes through `sanitize_markdown`.

- **Classifier Compatibility Fixes** (`src/qnwis/orchestration/workflow_adapter.py`)  
  The workflow adapter now calls `classify_text`, handles multiple intents, and treats `Complexity` as the literal string exposed by the schema—restoring classifier functionality for both unit and integration suites.

---

### Stage Panel Snapshots

```text
## dYZ_ Intent Classification

**Intent**: `pattern.anomalies`
**Complexity**: Medium
**Confidence**: 86%
**Sectors**: Energy, Finance
**Metrics**: attrition
**Time Horizon**: 24 months
*Completed in 123ms*

## dY"S Data Prefetch

**RAG Context**: 3 snippets retrieved
**External Sources**: World Bank API, Qatar Open Data
*Completed in 123ms*

## dY- PatternDetective

**Findings**: 2
**Status**: �o. Completed
*Execution time: 123ms*

## dY� Verification

�o. **Citations**: All valid
�o. **Numeric Checks**: All valid
dY"S **Avg Confidence**: 82%
*Completed in 123ms*

## dY� Synthesis

**Agents Consulted**: 2
**Total Findings**: 4
*Completed in 123ms*

## �o. Analysis Complete

**Queries Executed**: 1
**Data Sources**: 1
**Total Time**: 123ms (0.12s)
```

---

### Raw Evidence Preview (per-agent button output)

```text
## Raw Evidence — PatternDetective
**Finding**: Attrition anomaly

### `syn_attrition_by_sector_latest`
- Dataset: `aggregates/attrition_by_sector.csv`
- Freshness: 2025-11-08

| attrition_percent | sector |
| --- | --- |
| 3.1 | Energy |
| 4.4 | Finance |

*Preview limited to top rows per deterministic query.*
```

---

### Verification / Audit Panel Example

```text
## dY"< Audit Trail

**Request ID**: `req_demo`

**Queries Executed**: 2
   - `syn_attrition`
   - `syn_employment`

**Data Sources**: 2
   - aggregates/attrition.csv
   - aggregates/employment.csv

**Cache Performance**:
   - Hits: 7 / Misses: 1
   - Hit Rate: 87.5%

**Total Latency**: 6.12s (6123ms)

**Timestamps**:
   - Started: 2025-11-12T10:00:00Z
   - Completed: 2025-11-12T10:00:06Z
```

---

### Model Fallback Transcript

```text
2025-11-12 12:18:38,799 WARNING Primary model returned 404. Falling back to backup provider.
```

The fallback path is also covered by `TestModelSelector.test_call_with_model_fallback_on_http_404`.

---

### Tests Executed

```bash
python -m pytest tests/ui/test_chainlit_orchestration.py
python -m pytest tests/integration/test_e2e_chainlit_workflow.py
```

Both suites passed, exercising the classifier fixes, the UI components (timeline, raw evidence), RAG propagation, audit trail data, and the Anthropic→OpenAI fallback path end-to-end.

---

**Next Steps**:  
- Optional: Capture a short screencast of the Chainlit session to accompany the text snapshots when presenting Step 39.  
- Monitor fallback counters in production to ensure Anthropic outages are visible in ops dashboards.
