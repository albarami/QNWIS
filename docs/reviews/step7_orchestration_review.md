# Step 7 Review - Orchestration v1 Deterministic Council

**Review date:** 2024-11-05  
**Reviewer:** Codex (GPT-5) on Windows (Python 3.11.8)

---

## Scope
- Validate the deterministic council orchestrator against the provided checklist.
- Confirm new enhancements: optional LangGraph pipeline, confidence gating, and TTL rate limiting.
- Ensure outputs remain JSON-safe, deterministic, and compatible with Windows environments.

---

## Checklist Verification
- **Pure execution:** `run_council` only depends on `queries_dir`/`ttl_s` inputs and optional env gating. It delegates to pure helpers and avoids hidden side effects; the LangGraph path reuses the same deterministic steps and preserves agent order (`src\qnwis\orchestration\council.py:58`, `src\qnwis\orchestration\council.py:147`, `src\qnwis\orchestration\council.py:229`).
- **Verification coverage:** Percent bounds, YoY sanity, and sum-to-one tolerances remain enforced via `_check_percent_bounds`, `_check_yoy`, and `_check_sum_to_one` (`src\qnwis\orchestration\verification.py:53`, `src\qnwis\orchestration\verification.py:71`, `src\qnwis\orchestration\verification.py:88`). Tolerance stays ±0.5.
- **Consensus rule:** `_compute_consensus` only averages metrics observed by ≥2 agents, matching the synthesis requirement (`src\qnwis\orchestration\synthesis.py:52`).
- **JSON-safe output:** `_assemble_response` flattens dataclasses, injects `min_confidence`, and ensures verification issues are serialized to dicts (`src\qnwis\orchestration\council.py:102`).
- **Deterministic sequencing:** `_run_agents` executes agents sequentially, and the LangGraph DAG mirrors the plan→run→verify→synthesize→report order without reordering (`src\qnwis\orchestration\council.py:82`, `src\qnwis\orchestration\council.py:158-177`).
- **Windows safety:** No shell/network usage inside orchestration. Tests executed on Windows Python 3.11.8 confirmed behaviour and serialization.

---

## Enhancements Applied
- **LangGraph integration:** Added `build_council_graph(make_agents)` which compiles a LangGraph `StateGraph` matching the sequential flow. `run_council` now attempts this path and gracefully falls back on `ImportError`, keeping deterministic behaviour intact (`src\qnwis\orchestration\council.py:147-207`, `src\qnwis\orchestration\council.py:229-253`).
- **Confidence gate:** `council.min_confidence` is the minimum `confidence_score` across findings, defaulting to `1.0` when empty. It is surfaced in the response to help consumers decide on caution levels (`src\qnwis\orchestration\council.py:68-74`, `src\qnwis\orchestration\council.py:115-121`).
- **Rate limiting hook:** `_apply_rate_limit` reads `QNWIS_RATE_LIMIT_RPS`; when present, it enforces a TTL floor of 60 seconds and annotates the response with `rate_limit_applied: true` (`src\qnwis\orchestration\council.py:58-66`, `src\qnwis\orchestration\council.py:115-121`, `src\qnwis\orchestration\council.py:229-253`).

---

## Response Examples
```json
{
  "council": {
    "agents": ["LabourEconomist", "Nationalization", "Skills"],
    "findings": [
      {
        "title": "Employment recovery steady",
        "summary": "Headline employment rose 1.2% YoY.",
        "metrics": {"employment_percent": 61.2, "yoy_percent": 1.2},
        "evidence": [{"query_id": "employment_rate", "dataset_id": "labour", "locator": "employment.csv", "fields": ["employment_percent", "yoy_percent"]}],
        "warnings": [],
        "confidence_score": 1.0
      }
    ],
    "consensus": {"employment_percent": 60.9},
    "warnings": [],
    "min_confidence": 1.0
  },
  "verification": {
    "LabourEconomist": []
  },
  "rate_limit_applied": false
}
```

```json
{
  "council": {
    "agents": ["A", "B"],
    "findings": [
      {"title": "Signal", "summary": "Check", "metrics": {"metric": 1.0}, "evidence": [], "warnings": ["lagging"], "confidence_score": 0.9}
    ],
    "consensus": {"metric": 1.0},
    "warnings": ["lagging"],
    "min_confidence": 0.9
  },
  "verification": {"A": [], "B": []},
  "rate_limit_applied": true
}
```

---

## Tests Executed
- `python -m pytest tests/unit/test_orchestration_council.py`

All targeted tests passed on Windows. Coverage output is provided by pytest-cov; full-suite rerun recommended prior to release.

---

## Residual Notes
- LangGraph remains optional; when absent the sequential fallback continues to satisfy deterministic execution guarantees.
- Consider future integration tests hitting the API surface (`src\qnwis\api\routers\council.py`) once LangGraph is available to exercise both execution paths end-to-end.
