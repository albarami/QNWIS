# Step 17 - Cache & Materialization Hardening Review

## Highlights
- Cache versioning now follows the deterministic query registry checksum (`REGISTRY_VERSION` = first 12 chars of SHA256 across YAML specs). Any change to query definitions automatically bumps cache namespaces.
- CachedDataClient enforces allowlist logging, validates `query_id`, applies a 5 minute negative cache TTL for empty result sets, and swallows cache backend faults without polluting responses.
- Prefetcher, CLI warmup utilities, and Redis backend all share the same version tag and guarantee ISO-preserved timestamps during JSON serialization.
- Materialized view specs are validated (types + index syntax) and the refresh job now uses the QueryRegistry exclusively before rendering SQL. CLI output is structured JSON across all paths.
- Added declarative warmup packs (`src/qnwis/cache/warmup_packs.yml`) for post-deploy cache priming, with loader utilities and tests.

## TTL Policy (Cache Keys)
| Operation | TTL | Notes |
|-----------|-----|-------|
| `get_retention_by_company` | 24h | Daily HR retention rollups |
| `get_salary_statistics` | 24h | Statistical aggregates refreshed nightly |
| `get_employee_transitions` | 12h | Higher churn, refreshed twice daily |
| `get_qatarization_rates` | 7d | Internal quarterly cadence, weekly cache acceptable |
| `get_gcc_indicator` | 30d | GCC macro-economic indicators update monthly |
| `get_world_bank_indicator` | 30d | World Bank API refreshes monthly |
| *Default* | 24h | Applies to new deterministic read APIs |
| *Negative cache* | 5m | Empty result stampede protection (optional) |

## Materialized Views
| MV Name | Query ID | Refresh | Indexes | Rationale |
|---------|----------|---------|---------|-----------|
| `mv_retention_by_company_36m` | `retention_by_company_agg` | `0 */12 * * *` (twice daily) | `idx_mv_ret_comp_sector_company ON mv_retention_by_company_36m(sector, company_id)` | 36-month retention window, sector/company filtered dashboards benefit from B-tree on `(sector, company_id)` |
| `mv_salary_stats_sector` | `salary_statistics_sector` | `0 1 * * *` (daily 01:00) | `idx_mv_sal_sector ON mv_salary_stats_sector(sector)` | Sector-sliced salary reporting; index keeps lookup latency sub-second |

## Operational Runbook
### Cache
1. **Warmup after deploy**: `python -m src.qnwis.cli.qnwis_cache --action show-pack --pack core_kpis | jq '.'` then feed the specs into `warmup(cache, samples, client)` during bootstrap.
2. **Health check**: `python -m src.qnwis.cli.qnwis_cache --action info | jq '.redis.keyspace'`.
3. **Invalidation**: `python -m src.qnwis.cli.qnwis_cache --action invalidate-prefix --prefix "qr:get_retention_by_company"` after upstream data refresh.
4. **Negative cache**: Monitor for empty results; TTL is 300s by default and can be tuned/disabled per CachedDataClient instance.

### Materialized Views
1. **Scheduled refresh**: `python -m src.qnwis.jobs.refresh_materializations --registry src/qnwis/data/materialized/definitions.yml` (pass project DB connection + query registry in bootstrap). Output JSON enumerates refreshed views.
2. **Ad-hoc rebuild**: Delete specific MV via `DROP MATERIALIZED VIEW CONCURRENTLY` followed by running the refresh job.
3. **Validation**: Ensure `render_select` is available on the QueryRegistry adapter; job now asserts this before proceeding.
4. **Index hygiene**: Registry validation rejects malformed definitions; update `definitions.yml` with full `name ON table(columns)` syntax and rerun the job.

### Invalidation Policy
- When deterministic queries change: deploy new YAML, verify `REGISTRY_VERSION` change (e.g. `python -c "from src.qnwis.data.deterministic.registry import REGISTRY_VERSION; print(REGISTRY_VERSION)"`), then purge cache keys with the old version namespace if needed.
- External data sources (GCC / World Bank): rely on 30-day TTL, but proactively invalidate prefixes on upstream revisions to avoid stale analytics.

## Tests & Verification
- `python -m pytest tests/unit/cache`
- `python -m pytest tests/unit/test_registry.py tests/unit/test_queries_yaml_loads.py`

All tests pass; CLI outputs inspected manually for JSON structure. Redis interactions mocked to avoid environment dependencies.
