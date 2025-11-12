# QNWIS Changelog

Chronological record of notable work delivered during the roadmap milestones. Each entry references the relevant implementation step and the operational decision it unlocked.

## Step 36 – Production Deployment (2025-01-12)
- Added blue/green deployment workflow, health-gated cutovers, and explicit rollback scripts documented in [docs/deploy/DEPLOYMENT_RUNBOOK.md](deploy/DEPLOYMENT_RUNBOOK.md).  
- Hardened disaster recovery automation (PostgreSQL promotion scripts, Redis failover, `qnwis_dr.py`) and documented the DR exercise now mirrored in the Operations Runbook.  
- Finalized release etiquette: sign off via `docs/reviews/step36_review.md`, verify `/health/*` and `/metrics`, then **git push after every step** before notifying the ops bridge.

## Step 35 – Performance Optimization (2025-01-05)
- Tuned cache hierarchy (in-memory, Redis, materialized views) and surfaced the tuning levers in [PERFORMANCE.md](PERFORMANCE.md).  
- Landed benchmark suite (`scripts/benchmark_qnwis.py`, `tests/performance`) plus Prometheus SLO alerts integrated with the ops console.  
- Documented DB tuning recipes (VACUUM cadence, query statistics, connection pooling) and tied them to the `/metrics` export contract.

## Step 34 – Security Hardening (2024-12-29)
- Enforced HTTPS only, CSP + HSTS, CSRF protection, RBAC, audit logging, and rate limiting across all routers (see [SECURITY.md](SECURITY.md)).  
- Moved all secrets to environment variables with `.env.example` guidance; prohibited inline secrets in documentation or sample code.  
- Expanded security test suites (rate limit, CSRF, RBAC) and locked down the OpenAPI export so CI fails fast if schema generation breaks.

---

Earlier steps remain catalogued in [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md); this changelog highlights the most recent hardening phases preceding Step 37.
