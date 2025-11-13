# Step 3 – UI Streaming & Health Review

## Rationale & Remediations
- **SSE contract guardrails** – `SSEClient` now validates base URLs, question lengths, and LLM providers before opening sockets, and enforces a schema for every SSE payload. Malformed JSON or missing fields surface as client-side warning events instead of tracebacks.
- **Correlation-first logging** – Every streaming request now propagates a caller-provided `request_id`. The client prefixes logs with `rid=<uuid> stage=<stage> status=<status>` and Chainlit summarizes completion messages with the same ID so ops can join UI and API logs.
- **Provider guardrails** – The Chainlit UI only allows `anthropic`, `openai`, or `stub`. Invalid providers are rejected up front with a user-friendly error, preventing accidental calls to unsupported backends.
- **Health/readiness depth** – `/api/health/ready` now returns `version`, `llm_provider`, `llm_model`, and `registry_query_count`, and flips to 503 if deterministic queries are missing. Optional DB checks still avoid blocking the endpoint so responses stay under 200 ms.
- **Security hygiene** – UI logs no longer include user prompts, and SSE warning/error payloads never echo server exceptions. All 500s use the standardized payload introduced in Step 2.

## Testing Matrix
| Scope | Command | Notes |
|-------|---------|-------|
| UI SSE client unit tests | `python -m pytest tests/unit/ui/test_sse_parsing.py -q` | Covers provider/base URL guards, heartbeat parsing, warning propagation, and token streaming. |
| Health endpoints integration | `python -m pytest tests/integration/api/test_health_endpoints.py -q` | Exercises `/health`, `/health/live`, `/health/ready` including new metadata fields and 200/503 behavior. |

> Env setup for the above:  
> `set QNWIS_BYPASS_AUTH=true` and `set QNWIS_API_PREFIX=/api`

## Operational Notes
- **Curling SSE**: `curl -N -H "X-Request-ID:<uuid>" -H "Content-Type: application/json" -d '{"question":"...","provider":"stub"}' http://host:8000/api/v1/council/stream`. The first line will be `event: heartbeat` followed by `data:` envelopes that match the schema enforced in `SSEClient`.
- **Health checks**:  
  - Liveness: `curl http://host:8000/api/v1/health/live` → always 200 with `{status:"alive"}`.  
  - Readiness: `curl http://host:8000/api/v1/health/ready` → 200 or 503 with `version`, `llm_provider`, `llm_model`, `registry_query_count`, and per-subsystem messages. A query count of 0 or DataClient/LLM failures now force 503 for upstream load balancers.
- **Metrics**: Prometheus counters remain namespaced (`qnwis_ui_*`). When `prometheus_client` is missing, the telemetry module falls back to no-ops without raising.

## Residual Risks
- Streaming retries are capped (0.5 s → 1 s → 2 s). Additional resilience (e.g., circuit breakers) should be evaluated once real provider latencies are observed.
- Readiness still loads the deterministic registry synchronously; if the YAML set grows dramatically we may need lightweight caching to keep responses comfortably under 200 ms.
