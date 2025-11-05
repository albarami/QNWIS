# Step 4 Review - Deterministic Data Layer V2 Hardening

**Review date:** 2024-11-05  
**Reviewer:** Codex (GPT-5) on Windows (Python 3.11.8)

---

## Scope
- Validate Step 4 hardening work for the deterministic query API.
- Confirm checklist items covering typing, normalization, metrics resilience, request handling, TTL, and Windows compatibility.
- Assess enhancements: query spec exposure, request ID propagation, optional rate limiting.
- Document residual risks and recommended follow-ups.

---

## Checklist Verification
- **Type hints & docstrings:** Key modules (e.g., `src/qnwis/api/routers/queries.py`, `src/qnwis/data/deterministic/cache_access.py`, `src/qnwis/data/derived/metrics.py`, `src/qnwis/data/deterministic/normalize.py`) use modern PEP 604 hints and meaningful docstrings throughout.
- **Safe normalization:** `_extract_row_payload` and `normalize_rows` in `src/qnwis/data/deterministic/normalize.py` accept `Row` objects, raw dicts, and malformed inputs without raising; covered by `tests/unit/test_normalize.py` (`test_normalize_rows_row_model`, `test_normalize_rows_non_mapping_input`, `test_normalize_rows_idempotent`).
- **Derived metrics resilience:** `_val` and `_safe_int` safeguards in `src/qnwis/data/derived/metrics.py` handle `None`, strings, zeros, and NaNs. Regression tests in `tests/unit/test_metrics.py` (`test_share_of_total_non_numeric_values`, `test_yoy_growth_non_numeric_values`, `test_yoy_growth_zero_previous`) confirm graceful degradation.
- **run_query error handling:** `src/qnwis/api/routers/queries.py:120-172` now clones registry specs per request, raises `HTTPException(status_code=404, detail="Unknown query_id")`, clamps TTL inputs, and converts unexpected errors into generic 500 responses without leaking stack traces.
- **TTL bounds & override whitelist:** `_coerce_ttl` enforces 60-86400 seconds and ignores booleans/non-numeric inputs. Only `year`, `timeout_s`, `max_rows`, and `to_percent` pass through `normalize_params`; verified by `tests/integration/test_api_queries.py::test_run_query_ttl_bounds` and `::test_run_query_invalid_override_type`.
- **Query spec exposure:** `GET /v1/queries/{id}` returns `spec.model_dump(exclude_none=True)` while per-request overrides operate on a deepcopy, ensuring no mutation of registry defaults; asserted by new `tests/integration/test_api_queries.py::test_run_query_overrides_do_not_mutate_registry`.
- **Request ID echo:** `src/qnwis/utils/request_id.py` middleware ensures an `X-Request-ID` header is present on every response; `run_query` also mirrors the request ID in the JSON payload to support API clients.
- **Optional rate limiting:** `src/qnwis/app.py` enables `RateLimitMiddleware` (`src/qnwis/utils/rate_limit.py`) when `QNWIS_RATE_LIMIT_RPS` is set to a positive float; invalid values log warnings and do not enable throttling.
- **Windows compatibility:** Tests executed on Windows Python 3.11.8 succeed; file paths and environment handling avoid POSIX-only assumptions.

---

## Findings & Fixes
- **Registry mutation bug:** Previously, `run_query` mutated the shared `QuerySpec.params`, causing override leakage. The handler now deep-copies the spec and passes it through `execute_cached(..., spec_override=...)`, preserving registry state (`src/qnwis/api/routers/queries.py:148-158`).
- **Cache execution alignment:** `src/qnwis/data/deterministic/cache_access.py:157-212` accepts an optional `spec_override`, uses it for cache-key generation, and forwards it to `execute` to keep cache determinism aligned with request overrides.
- **Execution pipeline update:** `src/qnwis/data/deterministic/access.py:17-48` now validates override IDs and honours the supplied `QuerySpec`, ensuring connectors receive the merged parameters without relying on mutable registry state.
- **Test coverage:** Updated unit and integration suites reflect the new execution signature and guard against regression (see `tests/unit/test_execute_cached.py`, `tests/unit/test_execute_cached_metrics.py`, and the new integration test mentioned above).

---

## Tests Executed
- `python -m pytest tests/unit/test_execute_cached.py tests/unit/test_execute_cached_metrics.py tests/integration/test_api_queries.py::test_run_query_overrides_do_not_mutate_registry`

All selected tests passed on Windows. Coverage summary is provided by pytest-cov during execution; full-suite coverage still recommended before release.

---

## Residual Risks & Follow-ups
- **Partial test run:** Only cache/queries suites were executed for this review. Run the full battery (unit, integration, optional MCP) and static analyzers (`ruff`, `flake8`, `mypy`) before final deployment.
- **Single-process rate limiting:** `RateLimitMiddleware` uses an in-memory bucket; deploy behind a shared limiter (e.g., API gateway or Redis) when scaling horizontally.
- **CSV freshness heuristics:** CSV connector freshness dates rely on parsed max year; additional validation may be required if data sources change format.

---

## Conclusion
Step 4 hardening meets the checklist requirements. The per-request spec cloning fix eliminates a critical state-leak bug, and supporting tests confirm behaviour on Windows. Pending full-suite validation and production-readiness tasks (authentication, distributed cache/limiters), the deterministic query API is ready for staging rollout.
