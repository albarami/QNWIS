# Step 2 (C1 API) Review

## Issues addressed
- **Validation hardening** – `CouncilRequest` now normalizes and bounds `question`, `provider`, and `model`, preventing unsanitized provider/model strings from reaching the LLM client.
- **Typed contracts** – Added `CouncilRunLLMResponse`, `CouncilMetadata`, and `CouncilErrorResponse` so OpenAPI advertises stable schemas and the run endpoint can be used declaratively.
- **Error handling & observability** – Both endpoints emit deterministic 500 payloads with `request_id`, suppress user-provided text in logs, and attach `X-Request-ID` headers for correlation.
- **Streaming robustness** – SSE now serializes agent reports via `jsonable_encoder`, adds an explicit heartbeat event, disables reverse-proxy buffering, and performs cooperative `asyncio.sleep(0)` yielding.
- **Legacy compatibility** – `/v1/council/run` catches orchestration failures and still returns the deprecation payload so clients always receive HTTP 200 + warning.
- **Test coverage** – Added `tests/integration/api/test_council_llm_invalid.py` to assert 422s for short questions, invalid providers, and oversized prompts; existing streaming/non-stream/deprecation tests still pass.

## Endpoint contract
- **POST `/api/v1/council/stream`**  
  Request body:
  ```json
  {
    "question": "How is attrition trending in healthcare?",
    "provider": "stub",
    "model": "claude-3-haiku"   // optional
  }
  ```
  Response: `text/event-stream` with heartbeat plus workflow events. Example event payload:
  ```json
  {
    "stage": "agent:LabourEconomist",
    "status": "complete",
    "payload": {"report": { ... }, "full_response": "..."},
    "latency_ms": 418.4,
    "timestamp": "2025-11-13T00:32:41.259302+00:00"
  }
  ```

- **POST `/api/v1/council/run-llm`**  
  Request body identical to streaming endpoint.  
  Response (200):
  ```json
  {
    "synthesis": "Consolidated narrative...",
    "classification": {"intent": "attrition_monitoring", "...": "..."},
    "agent_reports": [{"agent": "LabourEconomist", "findings": [...], ...}],
    "verification": {"warnings": []},
    "metadata": {
      "question": "How is attrition trending in healthcare?",
      "provider": "stub",
      "model": "stub-mock",
      "stages": {
        "classify": {"latency_ms": 21.1, "timestamp": "2025-11-13T00:32:41.033Z"},
        "synthesize": {"latency_ms": 712.5, "timestamp": "2025-11-13T00:32:43.884Z"}
      }
    }
  }
  ```

- **Error schema (500)** for both endpoints:
  ```json
  {
    "error": "council_workflow_failed",
    "message": "LLM council execution failed. Retry later or contact operations.",
    "request_id": "2c1d5b4fe3ed4e6db86dee1aab6511ab"
  }
  ```

Docs include cURL samples plus rate-limit guidance within the endpoint docstrings.

## Test matrix
- Positive: `tests/integration/api/test_council_llm.py` (non-stream run, streaming SSE, stage coverage, legacy warning).  
- Negative: `tests/integration/api/test_council_llm_invalid.py` (short question, invalid provider, >5000 char payload) + streaming validation cases inside the main test file.
- Execution:  
  ```powershell
  $env:QNWIS_BYPASS_AUTH='true'
  $env:QNWIS_API_PREFIX='/api'
  python -m pytest tests/integration/api/test_council_llm.py tests/integration/api/test_council_llm_invalid.py -q
  ```
  (Auth is bypassed and the API prefix normalized for local CI parity.)

## OpenAPI & tooling notes
- Routers now declare `response_model=CouncilRunLLMResponse` and shared `CouncilErrorResponse`, so `/openapi.json` advertises the schemas under the `council-llm` tag.
- Streaming endpoint documents SSE semantics via docstring (the OpenAPI entry describes the heartbeat event and rate-limit requirement).
- Response models ensure `pydantic` auto-documents fields without relying on runtime dictionaries; optional extras remain behind `dev`/`production`.

## Operational notes
- SSE responses disable proxy buffering (`X-Accel-Buffering: no`) and surface `X-Request-ID` for tracing; heartbeats keep long-lived connections alive so Traefik/Nginx do not time out.
- Error logging excludes user-supplied questions to avoid leaking secrets; rate limiting is expected at the API gateway/WAF layer per the docstrings.
- Cooperative `await asyncio.sleep(0)` in the stream prevents blocking the event loop during high-volume agent output.
- Legacy deterministic endpoint now fails closed with a deprecation notice instead of raising 500s when LLM-backed agents are missing.
