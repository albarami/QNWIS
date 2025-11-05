# Deterministic Data Layer V2: API Endpoints

## Overview

The Deterministic Data Layer (DDL) V2 provides public FastAPI endpoints for executing deterministic queries with caching, provenance tracking, and freshness validation. These endpoints mirror the internal Python API used by agents, ensuring consistent behavior across HTTP and programmatic access.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  HTTP API   │────▶│  Query Registry  │────▶│  Cache Access Layer │
│  Endpoints  │     │  (YAML Specs)    │     │  (execute_cached)   │
└─────────────┘     └──────────────────┘     └─────────────────────┘
                                                      │
                                                      ▼
                                            ┌──────────────────┐
                                            │ Deterministic    │
                                            │ Connectors       │
                                            │ (CSV, World Bank)│
                                            └──────────────────┘
```

## Endpoints

### 1. List All Queries

**Endpoint:** `GET /v1/queries`

**Description:** Returns all available deterministic query identifiers from the registry.

**Request:**
```bash
curl -X GET http://localhost:8000/v1/queries
```

**Response:**
```json
{
  "ids": ["q_demo", "gdp_growth", "labor_force"]
}
```

### 2. Execute Query

**Endpoint:** `POST /v1/queries/{query_id}/run`

**Description:** Execute a deterministic query with optional parameter overrides and cache TTL.

**Parameters:**
- `query_id` (path): Query identifier from registry
- `ttl_s` (query param, optional): Cache TTL in seconds (60-86400, default 300)
- Request body:
  ```json
  {
    "ttl_s": 120,
    "override_params": {
      "year": 2023,
      "timeout_s": 10,
      "max_rows": 100,
      "to_percent": ["male_percent", "female_percent"]
    }
  }
  ```

**Whitelisted Override Parameters:**
- `year` (int): Filter data by year
- `timeout_s` (int): Query timeout in seconds
- `max_rows` (int): Maximum rows to return
- `to_percent` (list[str]): Columns to convert to percentages

**Request Example (curl):**
```bash
curl -X POST http://localhost:8000/v1/queries/q_demo/run \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: req-12345" \
  -d '{
    "ttl_s": 600,
    "override_params": {
      "year": 2023
    }
  }'
```

**Request Example (Python):**
```python
import requests

response = requests.post(
    "http://localhost:8000/v1/queries/q_demo/run",
    json={
        "ttl_s": 600,
        "override_params": {"year": 2023}
    },
    headers={"X-Request-ID": "req-12345"}
)
data = response.json()
```

**Response:**
```json
{
  "query_id": "q_demo",
  "unit": "percent",
  "rows": [
    {
      "year": 2023,
      "male_percent": 60.0,
      "female_percent": 40.0,
      "total_percent": 100.0
    }
  ],
  "provenance": {
    "source": "csv",
    "dataset_id": "demo_1",
    "locator": "/path/to/demo_1.csv",
    "fields": ["year", "male_percent", "female_percent", "total_percent"],
    "license": "CC BY 4.0"
  },
  "freshness": {
    "asof_date": "2023-12-01",
    "updated_at": "2023-12-01T10:30:00Z"
  },
  "warnings": [],
  "request_id": "req-12345"
}
```

### 3. Invalidate Query Cache

**Endpoint:** `POST /v1/queries/{query_id}/cache/invalidate`

**Description:** Invalidate cached results for a specific query, forcing fresh execution on next request.

**Parameters:**
- `query_id` (path): Query identifier to invalidate

**Request:**
```bash
curl -X POST http://localhost:8000/v1/queries/q_demo/cache/invalidate
```

**Response:**
```json
{
  "status": "ok",
  "invalidated": "q_demo"
}
```

## Safety Guardrails

### 1. No Dynamic Code Execution
- **Zero SQL injection risk**: All queries are predefined YAML specifications
- **No user-defined expressions**: Parameters are validated against whitelist
- **Deterministic connectors only**: CSV and World Bank API with fixed logic

### 2. Parameter Whitelist
Only the following parameters can be overridden via API:
- `year`: Year filter (coerced to int)
- `timeout_s`: Query timeout (coerced to int, bounded)
- `max_rows`: Result limit (coerced to int)
- `to_percent`: Column conversion list (coerced to list[str])

All other parameters in query YAML are immutable via API.

### 3. Cache TTL Bounds
- **Minimum TTL:** 60 seconds (prevents cache thrashing)
- **Maximum TTL:** 86400 seconds (24 hours, ensures freshness)
- **Default TTL:** 300 seconds (5 minutes)

Values outside bounds are automatically clamped:
```python
use_ttl = max(60, min(int(ttl_s), 86400))
```

### 4. Normalization Layer
All parameter and row data passes through deterministic normalization:
- **Parameters:** Type coercion, list conversion, trimming
- **Rows:** Column names to snake_case, string trimming, consistent structure

### 5. Provenance & Freshness
Every response includes:
- **Provenance:** Source type, dataset ID, locator, fields, license
- **Freshness:** As-of date, update timestamp
- **Warnings:** Freshness violations, validation issues

### 6. Request Tracing
- **X-Request-ID middleware:** Automatic request ID generation/forwarding
- **End-to-end tracing:** Request ID included in response for debugging

## Deterministic Guarantees

### Identical Results
For identical query spec and parameters:
```
query_1 = execute_cached("q_demo", registry, ttl_s=300)
query_2 = execute_cached("q_demo", registry, ttl_s=300)

assert query_1.rows == query_2.rows
assert query_1.provenance == query_2.provenance
```

### Cache Key Determinism
Cache keys are SHA-256 hashed from canonicalized inputs:
```python
def _key_for(spec: QuerySpec) -> str:
    normalized_params = _canonicalize_params(spec.params or {})
    payload = json.dumps(
        {"id": spec.id, "source": spec.source, "params": normalized_params},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"qnwis:ddl:v1:{spec.id}:{h}"
```

### No Side Effects
- **Read-only operations:** Queries never mutate data
- **Idempotent cache invalidation:** Multiple invalidations are safe
- **Stateless execution:** No session state, no cross-request dependencies

## Usage Patterns

### 1. Agent Access (Internal)
Agents MUST use the Python API directly, not HTTP endpoints:
```python
from qnwis.data.deterministic.cache_access import execute_cached
from qnwis.data.deterministic.registry import QueryRegistry

registry = QueryRegistry("src/qnwis/data/queries")
registry.load_all()

result = execute_cached("gdp_growth", registry, ttl_s=600)
for row in result.rows:
    process_row(row.data)
```

### 2. External Consumers (HTTP)
External services use HTTP API with same guarantees:
```python
import requests

response = requests.post(
    "http://qnwis-api/v1/queries/gdp_growth/run",
    json={"ttl_s": 600, "override_params": {"year": 2023}}
)
data = response.json()
```

### 3. Cache Management
Invalidate cache when source data updates:
```bash
# After uploading new CSV files
curl -X POST http://qnwis-api/v1/queries/gdp_growth/cache/invalidate
```

## Error Handling

### 404 Not Found
```json
{
  "detail": "Unknown query_id"
}
```
**Cause:** Query ID not in registry

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "ttl_s"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```
**Cause:** Invalid request schema

### 500 Internal Server Error
Cached payload corruption, connector failure, or unexpected errors.

## Configuration

### Environment Variables

```bash
# Required: Query definitions directory
QNWIS_QUERIES_DIR=/path/to/queries

# Optional: Default cache TTL (bounded to 60-86400)
DEFAULT_CACHE_TTL_S=300

# Optional: Redis for distributed cache
REDIS_URL=redis://localhost:6379/0
```

### Query YAML Structure

```yaml
id: gdp_growth
title: GDP Growth Rate
description: Year-over-year GDP growth from World Bank
source: world_bank
expected_unit: percent
params:
  indicator: NY.GDP.MKTP.KD.ZG
  country: QAT
  year: 2023
constraints:
  freshness_sla_days: 365
```

## Derived Metrics

Apply transformations after query execution:

```python
from qnwis.data.derived.metrics import share_of_total, yoy_growth, cagr

# Share of total within groups
rows_with_share = share_of_total(
    result.rows,
    value_key="population",
    group_key="year"
)

# Year-over-year growth
rows_with_growth = yoy_growth(
    result.rows,
    value_key="gdp"
)

# CAGR calculation
growth_rate = cagr(start_value=100, end_value=121, years=2)
# Returns: 10.0 (percent)
```

## Performance

### Latency Targets
- **Cache hit:** <10ms
- **Cache miss (CSV):** <50ms
- **Cache miss (World Bank):** <200ms

### Cache Compression
Payloads >8KB are zlib-compressed for storage efficiency.

### Connection Pooling
- **Redis:** 50 max connections
- **PostgreSQL:** 20 pool size (audit logs)

## Security

### No SQL Injection
Queries are YAML specs, not dynamic SQL. Connectors use parameterized queries internally.

### Rate Limiting
Implement at reverse proxy layer (nginx, Traefik):
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;
```

### Authentication
Add authentication middleware as needed:
```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.middleware("http")
async def verify_token(request: Request, call_next):
    # Verify JWT, API key, etc.
    pass
```

## Testing

Run full test suite:
```bash
# Unit tests
pytest tests/unit/test_normalize.py -v
pytest tests/unit/test_metrics.py -v
pytest tests/unit/test_api_models.py -v

# Integration tests
pytest tests/integration/test_api_queries.py -v
```

## Monitoring

Key metrics to track:
- **Cache hit rate:** `COUNTERS["hits"] / (COUNTERS["hits"] + COUNTERS["misses"])`
- **Query latency:** P50, P95, P99 for cache hits and misses
- **Freshness violations:** Count of queries with `warnings` containing freshness issues
- **Invalidation rate:** `COUNTERS["invalidations"]` per hour

## Summary

The DDL V2 API provides:
✓ **Deterministic execution** with reproducible results  
✓ **Safe parameter overrides** via whitelist  
✓ **Cache management** with TTL bounds (60-86400s)  
✓ **Provenance tracking** for audit and compliance  
✓ **Freshness validation** with SLA warnings  
✓ **Zero SQL injection** risk via predefined specs  
✓ **Request tracing** with X-Request-ID  
✓ **Normalization** for consistent data structure  

Agents continue using Python API; HTTP endpoints are for external consumers with identical guarantees.
