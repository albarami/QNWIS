# ADR 0001: Deterministic Data Layer

**Status:** Accepted (2025-01-12)  
**Owners:** Data Platform & Agents teams  
**Related Steps:** 16–17 (Deterministic LMIS data), 34 (Security), 35 (Performance), 37 (Documentation hardening)

## Context

QNWIS must answer ministerial questions using only audited LMIS sources. Prior steps uncovered two recurring risks:

1. Generative agents are prone to hallucinating SQL or using stale, ad-hoc CSVs.  
2. Regulatory reviewers require a single place to trace every number back to a table, row, and timestamp.

To satisfy those constraints we need a deterministic layer that converts every question into curated query templates, executes them against managed data services, and captures provenance for auditing, caching, and verification.

## Decision

- All agents interact with data through the deterministic Data API and catalog. **Agents NEVER write SQL; they call the Data API only.**  
- Query templates live in `src/qnwis/data/queries/*.yaml` and are executed by deterministic services that enforce schema, filters, and freshness gates.  
- Verification services (triangulation, audit logs, number verifier) receive the same normalized payload to avoid divergence between UI, API, and briefing agents.  
- The deterministic layer emits structured telemetry (query_id, dataset_id, checksum) that downstream verification and synthesis components consume without re-querying the database.

## Options Considered

| Option | Summary | Outcome |
|--------|---------|---------|
| Allow agents to write parameterized SQL directly | Fast to prototype but difficult to audit; high risk of schema drift or injection | **Rejected** — violates regulatory requirement for deterministic queries |
| Mirror LMIS tables into vector store / embeddings | Simplifies semantic search but breaks determinism and requires sensitive data duplication | **Rejected** — unacceptable data residency footprint |
| Deterministic layer + Data API (selected) | Centralizes query logic, enforces provenance, keeps agents simple | **Accepted** |

## Consequences

**Positive**
- Full traceability per Step 17 audit rules and Step 34 security controls (RBAC, rate limiting, CSRF, CSP/HSTS).  
- Cache warmers, verification workers, and ministerial briefings reuse the same deterministic payloads, which improves performance tuning (Step 35) and reduces drift.  
- Simplifies coordination between teams—changes land in query YAMLs or deterministic services, and everyone reuses them after they `git push after every step`.

**Negative / Mitigations**
- More upfront work to add a new metric (needs query YAML, tests, catalog entry). *Mitigation:* templates + scripts in `src/qnwis/data/deterministic`.  
- Agents cannot satisfy ad-hoc SQL asks. *Mitigation:* provide curated API endpoints and educate users via USER_GUIDE.md.  
- Requires disciplined release practice. *Mitigation:* automated gates (placeholder scan, doc_checks, deterministic tests) enforced in CI.

## References

- [DETERMINISTIC_DATA_LAYER_SPECIFICATION.md](../DETERMINISTIC_DATA_LAYER_SPECIFICATION.md)  
- [ARCHITECTURE.md](../ARCHITECTURE.md) — diagrams and system context  
- [USER_GUIDE.md](../USER_GUIDE.md) — user-facing guarantee and examples  
- [API_REFERENCE.md](../API_REFERENCE.md) — deterministic API endpoints  
- [PERFORMANCE.md](../PERFORMANCE.md) — cache/DB tuning (Step 35)  
- [SECURITY.md](../SECURITY.md) — Step 34 protections that rely on deterministic calls
