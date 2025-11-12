# Validation Harness – READ ME FIRST

**Phase:** Step 38 (Phase 2 extension beyond Step 37 release)  
**Scope:** Deterministic validation of Data API flows with privacy-preserving outputs

---

## Why this guide?

This document explains how to run the validation harness safely and reproducibly, which env vars to set, and how PII is handled before any artefact lands in `/docs/validation/*`. Review this before invoking any of the automation targets.

---

## Quick Start Commands

| Target | Description | Command |
|--------|-------------|---------|
| HTTP validation (staging/prod) | Exercises live Data API with CSRF + rate-limit logging | `make validate-http BASE_URL=https://api.qnwis.gov.qa` |
| In-process validation (hermetic CI) | Uses FastAPI `TestClient`, no network | `make validate-inproc` |
| Render case studies | Converts JSON results to markdown | `make case-studies` |
| Baseline comparison | Compares against consultant benchmarks | `make compare-baseline` |

All targets honor environment variables listed below. To run without GNU Make, call the underlying python scripts shown in the `Makefile`.

---

## Required Environment

| Variable | Purpose |
|----------|---------|
| `QNWIS_BASE_URL` | Base URL for `--mode http` (default `http://localhost:8000`) |
| `QNWIS_API_KEY` | Bearer token automatically injected via case headers (set per environment) |
| `QNWIS_CSRF_TOKEN` | Optional CSRF token header/cookie for protected deployments |
| `QNWIS_VALIDATION_MODE` | Default execution mode (`http`, `inproc`, `echo`) |
| `QNWIS_VALIDATION_MAX_RETRIES` | Override HTTP retry count (default 3) |
| `QNWIS_VALIDATION_RETRY_BASE` | Base delay (seconds) for exponential backoff + jitter |
| `QNWIS_VALIDATION_SEED` | RNG seed for jitter/echo timing (default 1337 for determinism) |

Install dependencies with `pip install -r requirements-dev.txt` (pinned versions) inside the project’s virtual environment.

---

## Running the Harness

1. **Select mode**
   - `http`: against a running deployment (includes CSRF + rate limit evidence in outputs).
   - `inproc`: hermetic, uses TestClient; ideal for CI and air-gapped reviews.
   - `echo`: fixture-driven smoke mode for fast feedback.

2. **Execute**
   ```bash
   python scripts/validation/run_validation.py \
     --mode http \
     --base-url ${QNWIS_BASE_URL:-http://localhost:8000} \
     --redaction-rules validation/redaction_rules.yaml \
     --seed ${QNWIS_VALIDATION_SEED:-1337}
   ```

3. **Review artefacts**
   - `validation/results/*.json`: per-case detail with audit IDs, rate-limit headers, and CSRF cookie presence.
   - `validation/summary.csv`: tabular metrics for all 20 cases.
   - `docs/validation/KPI_SUMMARY.md`: Phase 2 KPI tile (pass %, tier latency percentiles).
   - `docs/validation/CASE_STUDIES.md`: executive narrative linked to the OpenAPI spec.

4. **Cross-check observability**
   - Hit `/metrics` on the target deployment and confirm `qnwis_validation_latency_ms` aligns with the values recorded in `KPI_SUMMARY.md`.

---

## Privacy & Redaction Policy

- The runner loads `validation/redaction_rules.yaml` before writing any JSON/markdown.
- Fields such as `name`, `person_id`, `salary`, and inline patterns are replaced with `[REDACTED-*]`.
- Never commit raw responses generated outside this harness; only sanitized artefacts in `/validation/results` and `/docs/validation/*` are permitted.
- `docs/validation/CASE_STUDIES.md` and `KPI_SUMMARY.md` contain no PII by construction; rerun the harness if rules are changed.

---

## Security & Rate Limits

- HTTP executions automatically retry on `429/503` with exponential backoff + deterministic jitter (`--seed`), and they log `X-RateLimit-*` plus CSRF cookie presence in every result record.
- Respect upstream quotas; adjust `--max-retries`/`--retry-base` instead of hammering endpoints.
- `/docs/validation/*` must remain free of secrets—use the make targets rather than editing markdown manually.

---

## Reproducibility Checklist

- [x] Deterministic jitter via `--seed`
- [x] Hermetic `--mode inproc` for CI
- [x] 20 phase-aligned Data API cases (no ad-hoc SQL)
- [x] KPI tile regenerated on each run
- [x] Step 37 precedent cited in `docs/reviews/step37_review.md`; this guide records the Phase 2 extension (Step 38)

Follow this guide before sharing validation evidence internally or with ministry stakeholders.
