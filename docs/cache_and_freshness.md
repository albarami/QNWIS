# Cache and Freshness System

## Overview

The QNWIS deterministic data layer includes a comprehensive caching system with freshness SLA verification, provenance enrichment, and automatic as-of date detection.

## Architecture

### Cache Backends

Two cache backends are supported:

1. **MemoryCacheBackend** (default): In-process cache with TTL support
2. **RedisCacheBackend**: Distributed Redis cache for multi-process deployments

Configure via environment variables:
```bash
QNWIS_CACHE_BACKEND=memory  # default
QNWIS_CACHE_BACKEND=redis
REDIS_HOST=localhost  # for Redis
REDIS_PORT=6379       # for Redis
```

### Cache Key Naming

Cache keys are deterministic and generated from:
- Query ID
- Query parameters (JSON-serialized, sorted)
- SHA256 hash (first 16 chars)

Format: `qnwis:ddl:v1:{query_id}:{hash}`

Example: `qnwis:ddl:v1:q_employment_share:a3f5e12b9c4d8e7f`

## Usage

### Basic Cached Execution

```python
from src.qnwis.data.deterministic.cache_access import execute_cached
from src.qnwis.data.deterministic.registry import QueryRegistry

registry = QueryRegistry(root="data/queries")
registry.load_all()

# Execute with 5-minute cache TTL
result = execute_cached("q_employment_share", registry, ttl_s=300)
```

### Cache Invalidation

Force fresh execution bypassing cache:

```python
result = execute_cached("q_employment_share", registry, ttl_s=300, invalidate=True)
```

## Freshness SLA Verification

### Automatic As-Of Date Detection

The system automatically derives as-of dates from:

1. **Explicit `asof_date`**: If provided in `Freshness` model (not "auto"/"api")
2. **Date column**: Prefers ISO date strings in `date` field
3. **Year column**: Falls back to max year value → `{year}-12-31`
4. **API source**: Returns "api" for World Bank queries (derives from row data)

### SLA Configuration

Add `freshness_sla_days` to query constraints:

```yaml
# data/queries/example.yaml
id: q_employment_share_by_gender_2023
title: Employment share by gender
source: csv
expected_unit: percent
params:
  pattern: "employed-persons-15-years-and-above*.csv"
  select: ["year", "male_percent", "female_percent"]
  year: 2023
constraints:
  freshness_sla_days: 730  # Data must be < 730 days old
```

### Freshness Warnings

Results include warnings when SLA is violated:

- `stale_data:{age}>{sla}`: Data exceeds SLA (e.g., "stale_data:800>730")
- `freshness_unknown`: Cannot derive as-of date
- `freshness_parse_error`: Date parsing failed

```python
result = execute_cached("q_employment_share", registry)
if result.warnings:
    for warning in result.warnings:
        if warning.startswith("stale_data"):
            print(f"Warning: {warning}")
```

## Provenance Enrichment

### Dataset Catalog

The system enriches provenance with license information from `data/catalog/datasets.yaml`:

```yaml
datasets:
  - pattern: "*employed-persons-15-years-and-above*.csv"
    license: "Qatar Open Data (see portal terms)"
    notes: "Employment CSV; year and *_percent columns expected"
  - pattern: "indicator=SL.UEM.TOTL.ZS*"
    license: "World Bank CC BY 4.0"
    notes: "Total unemployment rate (% of total labor force)"
```

The catalog uses fnmatch patterns to match query locators and enrich the `provenance.license` field if not already set.

## Query Parameter Extensions

### CSV Queries

Enhanced parameters:

```yaml
params:
  pattern: "employed-persons*.csv"       # Required
  select: ["year", "male", "female"]     # Optional: field projection
  year: 2023                             # Optional: filter by year
  max_rows: 10000                        # Optional: limit rows
  timeout_s: 5.0                         # Optional: timeout in seconds
  to_percent: ["male", "female"]         # Optional: multiply by 100
```

**`to_percent`**: Converts specified numeric fields from decimals (0.6) to percentages (60.0).

### World Bank Queries

Default parameters added:

```yaml
params:
  indicator: "SL.UEM.TOTL.ZS"            # Required
  countries: ["QAT", "SAU", "ARE"]       # Optional: default GCC
  year: 2022                             # Optional
  timeout_s: 15                          # Optional: default 30
  max_rows: 10000                        # Optional: default 10000
```

## Example Queries

### Employment Share Query

```yaml
# File: data/queries/employment_share.yaml
id: q_employment_share_by_gender_2023
title: Employment share by gender (latest Qatar CSV)
description: Share split expected to sum to 100%
source: csv
expected_unit: percent
params:
  pattern: "employed-persons-15-years-and-above*.csv"
  select: ["year", "male_percent", "female_percent", "total_percent"]
  year: 2023
constraints:
  sum_to_one: true
  freshness_sla_days: 730
```

### GCC Unemployment Comparison

```yaml
# File: data/queries/unemployment_rate_gcc.yaml
id: q_unemployment_rate_gcc_latest
title: Unemployment rate GCC comparison
description: Compare Qatar vs GCC unemployment rate (World Bank)
source: world_bank
expected_unit: percent
params:
  indicator: "SL.UEM.TOTL.ZS"
  countries: ["QAT", "SAU", "ARE", "KWT", "BHR", "OMN"]
  timeout_s: 15
  max_rows: 10000
constraints:
  freshness_sla_days: 365
```

## Cache Management

### TTL Selection

Choose TTL based on data volatility:

- **Historical data**: 86400s (24 hours)
- **Recent quarterly data**: 3600s (1 hour)
- **Real-time indicators**: 300s (5 minutes)

### Manual Invalidation

```python
# Invalidate single query
execute_cached("q_id", registry, invalidate=True)

# Clear entire cache (Memory backend)
from src.qnwis.data.cache.backends import get_cache_backend
cache = get_cache_backend()
# No bulk clear API - invalidate per-query as needed
```

### Redis Cache Clearing

For Redis backend:
```bash
redis-cli FLUSHDB  # Clear current database
redis-cli KEYS "qnwis:ddl:*" | xargs redis-cli DEL  # Clear only QNWIS keys
```

## Testing

All tests are non-blocking and use MemoryCacheBackend via monkeypatch:

```python
def test_example(monkeypatch):
    from src.qnwis.data.cache.backends import MemoryCacheBackend
    
    monkeypatch.setattr(
        "src.qnwis.data.deterministic.cache_access.get_cache_backend",
        lambda: MemoryCacheBackend()
    )
    # Test logic...
```

Run tests:
```bash
pytest tests/unit/test_cache_backends.py -v
pytest tests/unit/test_execute_cached.py -v
pytest tests/unit/test_freshness.py -v
pytest tests/unit/test_catalog_registry.py -v
```

## Windows Compatibility

All file paths use `os.path.join()` and `pathlib.Path` for cross-platform compatibility.
Redis client is only imported when `QNWIS_CACHE_BACKEND=redis` is set.

## Performance

- **Memory backend**: ~0.1ms cache hit latency
- **Redis backend**: ~1-2ms cache hit latency (local Redis)
- **Cache miss**: Full query execution time (varies by source)

## Security Considerations

- Cache keys include parameter hashes to prevent poisoning
- No sensitive data should be cached (queries are deterministic)
- Redis should be secured with authentication in production
- TTL ensures stale data is eventually refreshed

## Quality Gates

The QNWIS data layer maintains strict quality standards:

### Test Coverage
- **Target**: ≥90% branch coverage for `src/qnwis/data`
- **Command**: `python -m pytest tests/unit/ -v --cov=src/qnwis/data --cov-branch --cov-report=term-missing`
- **Exclusions**: MCP tests remain quarantined with `-m 'not mcp'`

### Secret Scanning
- **Tool**: `.\scripts\secret_scan.ps1`
- **Allowlist**: `scripts/secret_scan_allowlist.txt` for known safe patterns
- **Status**: Must pass clean (exit code 0)
- **Excludes**: Binary files, external data, reference code

### Linting
- **Tools**: ruff, flake8, mypy (dev dependencies)
- **Standard**: PEP8 with type hints throughout
- **References**: `references/` folder excluded (read-only examples)

### Test Execution
```bash
# Run all non-MCP tests with coverage
python -m pytest tests/unit/ -m 'not mcp' --cov=src/qnwis/data --cov-branch

# Secret scan
.\scripts\secret_scan.ps1

# All gates must pass before merging to main
```

### Cache-Specific Coverage
- TTL expiration and enforcement
- Hit/miss counter accuracy
- Compression for payloads ≥8KB
- Invalidation and zero-TTL bypass
- Decoding error recovery
