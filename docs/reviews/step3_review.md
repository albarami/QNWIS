# Step 3: Cache & Freshness Hardening Review

**Date**: 2025-11-04  
**Objective**: Harden deterministic query caching, freshness validation, and catalog/connectors prior to Step 3 rollout.

## ✅ Checklist Status
- ✅ Deterministic cache keys use stable hashing over `spec.id` + canonicalised params (`src/qnwis/data/deterministic/cache_access.py:33`).
- ✅ TTL enforcement caps at 24h, treats `<=0` as uncached, validates `None` as no-expiry (`src/qnwis/data/deterministic/cache_access.py:75`).
- ✅ Cache payloads serialise via `model_dump(mode="json")` and hydrate with `model_validate`, with zlib compression ≥8KB and envelope metadata (`src/qnwis/data/deterministic/cache_access.py:96`).
- ✅ Freshness parsing normalises ISO dates, trims time suffixes, and falls back to year-end derived from year columns (`src/qnwis/data/freshness/verifier.py:20`).
- ✅ SLA warnings triggered only when `freshness_sla_days` is valid; invalid/parse errors surfaced explicitly (`src/qnwis/data/freshness/verifier.py:105`).
- ✅ Catalog lookups tolerate missing/invalid files and never raise (`src/qnwis/data/catalog/registry.py:14`).
- ✅ Connectors enforce `max_rows`, handle thousands separators, and accept `to_percent` lists (`src/qnwis/data/connectors/csv_catalog.py:109`).
- ✅ Type hints & docstrings added; `mypy --strict` passes (`pyproject.toml` / command run).
- ✅ Enhancements delivered: cache compression metadata, `invalidate_query` helper, cache hit/miss counters.

## Highlights

### Cache Layer
- Canonical parameter hashing prevents drift across differing dict orderings.
- Normalised TTL logic deletes stale entries when caching disabled and caps long-lived entries.
- Cache envelope adds `_meta` section with `content_encoding` hints; ≥8KB payloads compressed transparently.
- `COUNTERS` exposes hit/miss metrics, and `invalidate_query` simplifies explicit invalidation paths.

### Freshness & SLA Handling
- `_normalize_date_candidate` delegates to smaller helpers, supporting ISO timestamps with `Z`/`T`, numeric strings, and bare years.
- `_extract_explicit_asof` now distinguishes parse failures from missing data to emit `freshness_parse_error`.
- Invalid SLA inputs raise `freshness_invalid_sla`, guarding against silent misconfiguration.

### Catalog & Connector Safety
- `DatasetCatalog` gracefully handles absent files and YAML parse errors, returning empty matches.
- CSV connector validates iterables, enforces `max_rows`, converts thousands separators, and applies `to_percent` lists.
- Added unit coverage for thousands separators, invalid `max_rows`, TTL edge cases, compression envelope, and invalid SLA flows.

## Test & Tooling Gate

| Tool | Command | Result |
|------|---------|--------|
| Pytest | `.venv\Scripts\python.exe -m pytest` | ✅ 82 passed / 59 deselected |
| Ruff | `.venv\Scripts\python.exe -m ruff check` | ✅ |
| Flake8 | `.venv\Scripts\python.exe -m flake8` | ✅ |
| Mypy | `.venv\Scripts\python.exe -m mypy --strict src` | ✅ |
| Secret Scan | `powershell -File scripts\secret_scan.ps1` | ⚠️ Flagged sample key at `scripts/purge_secrets_from_history.ps1:23` (needs redaction/replacement) |

> **Action**: Remove or sanitise the demonstrative key in `scripts/purge_secrets_from_history.ps1` so the security gate passes.

