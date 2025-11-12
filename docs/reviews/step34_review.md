# Step 34 Review – Security Hardening Refresh

**Review date:** 2025-11-11  
**Reviewer:** Codex (GPT-5) on Windows (Python 3.11.8)

---

## Scope
- Validate Step 34 checklist items (headers, CSRF, rate limiting, RBAC, sanitization, deterministic-layer guard, Docker, logging).
- Confirm new enhancers: CSP nonce helper, HTTPS enforcement, Range header mitigation, pen-test harness, SARIF-capable security workflow, Bandit/Safety/pip-audit triage.
- Document residual risks and mitigations with references to code and automated evidence.

---

## Checklist Verification
- **Headers & CSP:** `SecurityHeadersMiddleware` now seeds per-request nonces via `ensure_csp_nonce` and appends `'nonce-<value>'` to `script-src` (`src/qnwis/security/headers.py:10-52`, helper in `src/qnwis/security/csp.py:1-31`). Tests assert header layout + helper parity (`tests/integration/test_security_headers.py:25-86`).
- **HTTPS enforcement:** `StrictTransportMiddleware` rejects plain HTTP unless host ∈ localhost allowlist or `require_https=False` (`src/qnwis/security/https.py:13-44`). Covered by `test_https_enforcement_*` (`tests/integration/test_security_headers.py:58-83`).
- **CSRF cookie configurability:** Settings expose `csrf_header_name`, `csrf_secure`, `csrf_samesite`, and overrides for tests (`src/qnwis/security/security_settings.py:27-90`). `tests/integration/test_csrf.py:15-94` verifies cookies set + honored over HTTPS and respects config.
- **Rate limiting:** Redis and in-memory stores now emit `X-RateLimit-Reset` derived from TTL (`src/qnwis/security/rate_limiter.py:98-137`) with regression tests for headers, retry, and per-client behavior (`tests/integration/test_rate_limit.py:8-134`).
- **RBAC case-insensitive any/all:** `require_roles` accepts `mode="any_of"|"all_of"` and enforces multi-role headers (`src/qnwis/security/rbac_helpers.py:8-60`) with tests in `tests/unit/test_rbac.py:1-112`.
- **Sanitization policy:** Allowed-tags list unchanged but high-risk payloads (SVG, javascript:, data URLs) covered by parametric tests (`tests/unit/test_sanitizer.py:5-84`). Sanitizer functions documented and rely on runtime `bleach` dependency in `[project].dependencies` (`pyproject.toml:9-26`).
- **Pen-test harness:** `/form` endpoint receives canonical XSS payloads ensuring HTML/text sanitization remains intact (`tests/integration/test_pen_test_payloads.py:5-33`).
- **Deterministic layer guard:** `python -m pytest tests/unit/test_query_registry_injection_guard.py` passes, confirming no dynamic SQL or unsafe patterns remain.
- **F-string SQL scan:** `rg -n --fixed-strings 'f"SELECT' src/qnwis\data` and equivalent searches for INSERT/UPDATE/DELETE returned no matches (captured via CLI command run during review).
- **Docker hardening:** Production image installs runtime deps only (`Dockerfile:18-35`), switches to non-root UID 1000 (`Dockerfile:11-41`), and exposes health checks without embedding secrets.
- **Logging posture:** Audit middleware hashes user IDs and client addresses before logging (no PII) and propagates rate-limit headers (`src/qnwis/security/audit.py:16-96`).

---

## Enhancements & Fixes
1. **Security middleware orchestration.** `attach_security` now layers `SecurityHeaders -> CSRFMiddleware -> RangeHeaderGuard -> StrictTransport -> RequestAudit`, and `create_app` wires it into the API server (`src/qnwis/api/deps.py:13-31`, `src/qnwis/api/server.py:31-95`). This ensures every request sees strict transport checks, Range header validation, and hashed audit logs without copying the middleware stack per service.
2. **Range header mitigation for GHSA-7f5h-v6xp-fcq8.** `RangeHeaderGuardMiddleware` rejects oversized or multi-range headers before Starlette’s vulnerable parser is invoked (`src/qnwis/security/range_guard.py:1-37`). Integration tests cover both rejection and acceptance paths (`tests/integration/test_security_headers.py:88-114`). This provides a practical mitigation while FastAPI still pins Starlette `<0.48.0`.
3. **Nonce helper for templating.** Pages can pull the nonce via `get_csp_nonce` to annotate inline scripts, with parity verified by `test_csp_nonce_helper_matches_header_value` (`tests/integration/test_security_headers.py:70-86`).
4. **Rate-limit observability.** Headers now include `X-RateLimit-Reset` plus a consistent `Retry-After` contract. `tests/integration/test_rate_limit.py:8-134` ensures TTL math behaves for both happy-path and throttled clients.
5. **CSRF HTTPS behavior.** Tests switched to HTTPS base URLs so “Secure” cookies are exercised, and new assertions ensure cookie attributes reflect `SecuritySettings` overrides (`tests/integration/test_csrf.py:45-102`).
6. **RBAC flexibility.** `require_roles` accepts `mode="all_of"` for scope-style requirements and tests verify multi-role header parsing including case variants (`tests/unit/test_rbac.py:63-112`).
7. **Audit redaction & secure settings overrides.** `_hash_identifier` prevents PII leakage in audit logs, while `override_security_settings/reset_security_settings` lets tests tweak behavior without racing the global singleton (`src/qnwis/security/security_settings.py:27-97`, `src/qnwis/security/audit.py:16-96`).
8. **Workflow + tooling.** `.github/workflows/security.yml` now emits SARIF to code scanning and installs project deps via `pip install .[dev]`. `scripts/run_security_checks.sh` already aligns with local execution. Bandit high/medium issues are resolved (see Tests section).
9. **Dependency hygiene.** Runtime dependencies now include `bleach` and `defusedxml` (`pyproject.toml:9-26`) so sanitizers and XML parsing avoid optional installs. `readiness_gate.py:1202` consumes DefusedXML, and YAML loaders rely on `safe_load` (`src/qnwis/alerts/registry.py:51-62`, `src/qnwis/slo/loader.py:61-86`). Docker installs runtime-only deps (`Dockerfile:26-30`).
10. **CLI + runtime binding defaults.** Local CLI defaults bind to `127.0.0.1` (`src/qnwis/cli/qnwis_api.py:55-73`) and `Settings.api_host` documents the expectation to opt in to `0.0.0.0` explicitly (`src/qnwis/config/settings.py:34-44`).

---

## Tests & Scans
- `python -m pytest tests/unit/test_sanitizer.py tests/unit/test_rbac.py tests/unit/test_query_registry_injection_guard.py tests/integration/test_security_headers.py tests/integration/test_rate_limit.py tests/integration/test_csrf.py tests/integration/test_pen_test_payloads.py`
- `python -m bandit -r src -ll -ii` → no medium/high issues (2025-11-11 16:47).
- `python -m safety check --full-report` (and `--short-report`) → still flags system-wide `pip`/`setuptools` shipped with base Python (C:\Program Files), even though the project installs patched versions via `pip install --user`. Documented residual risk below.
- `python -m pip_audit --format json` (parsed) → remaining findings limited to:
  - `starlette==0.47.3` GHSA-7f5h-v6xp-fcq8 (upgrade blocked by FastAPI `<0.48` constraint; mitigated via Range header guard and tracked for the next FastAPI release).
  - `pdfminer-six==20250506` and `transformers==4.36.0` pulled in by developer-only tooling (Chainlit, LLM experiments). Not part of server runtime or Docker image; mitigation is to keep them out of production images and monitor upstream for `20251107`/`4.53.0` releases.
- `python -m pip install --upgrade pip setuptools wheel` (user scope) to reduce Safety noise; system Python still advertises vulnerable versions, so long-term fix is to use per-project venvs or containerized tooling.

All commands executed on Windows; timings and logs retained in shell history for traceability.

---

## Remaining Risks & Follow-ups
1. **Starlette Range parsing (GHSA-7f5h-v6xp-fcq8).** Direct upgrade is blocked by FastAPI’s `<0.48` pin. Range guard middleware enforces sane limits, but once FastAPI relaxes its requirement we should bump and drop the guard. Track upstream issue [FastAPI#11805] (not yet released).
2. **pdfminer-six / transformers vulnerabilities.** These originate from the shared dev environment (used by demos/agents) and are not bundled into the production Docker image. Still, they should be isolated in virtual environments; recommend splitting ML tooling into a separate optional extras file and upgrading to `pdfminer-six>=20251107` / `transformers>=4.53.0` when available.
3. **Safety scanner noise.** Because Safety scans the entire system site-packages tree, it continues to flag the vendor Python’s `pip/setuptools`. CI should run inside the Docker image (or a virtualenv) to avoid these false positives; documentation updated accordingly.
4. **Container CMD host.** Docker still exposes `--host 0.0.0.0` for actual deployment (`Dockerfile:51`), which is intentional for load-balancers. Combined with StrictTransport and TLS termination, this is acceptable; for local dev use CLI defaults (127.0.0.1).

The checklist is complete with mitigations documented above; remaining items are tracked for upstream releases and environment hygiene.
