# QNWIS API Reference (OpenAPI)

**Version**: dev  
**Title**: QNWIS Agent API  

This document is auto-generated from the FastAPI application.

## Endpoints

### GET `/`

**Summary**: Info

**Responses**: 200: Successful Response

**Tags**: info

---

### POST `/api/v1/agents/pattern/anomalies`

**Summary**: Anomalies

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.pattern

---

### POST `/api/v1/agents/pattern/correlations`

**Summary**: Correlations

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.pattern

---

### POST `/api/v1/agents/predictor/forecast`

**Summary**: Forecast

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.predictor

---

### POST `/api/v1/agents/predictor/warnings`

**Summary**: Warnings

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.predictor

---

### POST `/api/v1/agents/scenario/apply`

**Summary**: Scenario Apply

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.scenario

---

### POST `/api/v1/agents/scenario/compare`

**Summary**: Scenario Compare

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.scenario

---

### POST `/api/v1/agents/strategy/benchmark`

**Summary**: Gcc Benchmark

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.strategy

---

### POST `/api/v1/agents/strategy/vision`

**Summary**: Vision Alignment

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.strategy

---

### POST `/api/v1/agents/time/baseline`

**Summary**: Baseline

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.time

---

### POST `/api/v1/agents/time/breaks`

**Summary**: Breaks

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.time

---

### POST `/api/v1/agents/time/trend`

**Summary**: Trend

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: agents.time

---

### POST `/api/v1/api/v1/continuity/execute`

**Summary**: Execute Plan

Execute failover plan.

Requires admin or service role.

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: continuity

---

### POST `/api/v1/api/v1/continuity/plan`

**Summary**: Generate Plan

Generate continuity plan from cluster and policy configuration.

Requires admin or service role.

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: continuity

---

### POST `/api/v1/api/v1/continuity/simulate`

**Summary**: Simulate Failover

Run deterministic failover simulation.

Requires admin or service role.

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: continuity

---

### POST `/api/v1/api/v1/continuity/status`

**Summary**: Get Status

Get cluster and quorum status.

Requires admin or service role.

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: continuity

---

### POST `/api/v1/api/v1/dr/backup`

**Summary**: Create Backup

Create a backup snapshot.

Requires admin or service role.

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: dr

---

### POST `/api/v1/api/v1/dr/restore`

**Summary**: Restore Snapshot

Restore from a snapshot.

Requires admin or service role.

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: dr

---

### GET `/api/v1/api/v1/dr/snapshots`

**Summary**: List Snapshots

List available snapshots.

Requires admin, service, or analyst role.

**Parameters**:
- `storage_target_id` (string) (required)
- `tag` (string)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: dr

---

### POST `/api/v1/api/v1/dr/verify/{snapshot_id}`

**Summary**: Verify Snapshot

Verify a snapshot.

Requires admin or service role.

**Parameters**:
- `snapshot_id` (string) (required)
- `storage_target_id` (string) (required)
- `key_id` (string)
- `sample_count` (integer)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: dr

---

### GET `/api/v1/api/v1/slo/`

**Summary**: List Slos

**Responses**: 200: Successful Response

**Tags**: slo

---

### GET `/api/v1/api/v1/slo/budget`

**Summary**: Get Budgets

**Responses**: 200: Successful Response

**Tags**: slo

---

### POST `/api/v1/api/v1/slo/simulate`

**Summary**: Simulate

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: slo

---

### GET `/api/v1/incidents`

**Summary**: List Incidents

List incidents with optional filters.

Supports filtering by state, severity, rule_id.

**Parameters**:
- `state` (string)
- `severity` (string)
- `rule_id` (string)
- `limit` (integer)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: notifications

---

### GET `/api/v1/incidents/stats`

**Summary**: Get Incident Stats

Get incident statistics.

**Responses**: 200: Successful Response

**Tags**: notifications

---

### GET `/api/v1/incidents/{incident_id}`

**Summary**: Get Incident

Get incident details by ID.

**Parameters**:
- `incident_id` (string) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: notifications

---

### POST `/api/v1/incidents/{incident_id}/ack`

**Summary**: Acknowledge Incident

Acknowledge an incident (OPEN → ACK).

**Parameters**:
- `incident_id` (string) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: notifications

---

### POST `/api/v1/incidents/{incident_id}/resolve`

**Summary**: Resolve Incident

Resolve an incident (any state → RESOLVED).

**Parameters**:
- `incident_id` (string) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: notifications

---

### POST `/api/v1/incidents/{incident_id}/silence`

**Summary**: Silence Incident

Silence an incident (OPEN|ACK → SILENCED). Admin only.

**Parameters**:
- `incident_id` (string) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: notifications

---

### POST `/api/v1/notify/send`

**Summary**: Send Notification

Send a notification (admin/service only).

Requires admin or service role.

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: notifications

---

### POST `/api/v1/v1/briefing/minister`

**Summary**: Minister Briefing

Generate Minister Briefing combining council findings and verification.

This endpoint:
1. Runs the agent council on synthetic data
2. Performs cross-source triangulation checks
3. Returns a structured briefing with embedded Markdown

Args:
    queries_dir: Optional queries directory path
    ttl_s: Cache TTL in seconds

Returns:
    JSON with briefing structure including:
    - title: Briefing title
    - headline: List of key bullet points
    - key_metrics: Dictionary of numeric metrics
    - red_flags: List of verification issues
    - provenance: List of data source locators
    - markdown: Full briefing in Markdown format

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: briefing

---

### POST `/api/v1/v1/council/run`

**Summary**: Council Run

Execute multi-agent council with deterministic data access.

Runs all 5 agents sequentially, verifies outputs against numeric
invariants, and synthesizes a unified council report with consensus metrics.

Args:
    queries_dir: Optional path to query definitions directory
    ttl_s: Cache TTL in seconds (default: 300)

Returns:
    Dictionary containing:
        - council: CouncilReport with findings, consensus, warnings
        - verification: Agent-level verification results

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: council

---

### GET `/api/v1/v1/queries`

**Summary**: List Queries

List all available deterministic query identifiers.

Returns:
    Dictionary with 'ids' key containing list of query IDs

**Responses**: 200: Successful Response

**Tags**: queries

---

### GET `/api/v1/v1/queries/{query_id}`

**Summary**: Get Query

Retrieve the registered QuerySpec for a given identifier.

Args:
    query_id: Query identifier from registry

Returns:
    Dictionary containing the serialized QuerySpec

Raises:
    HTTPException: 404 if the query is not registered

**Parameters**:
- `query_id` (string) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: queries

---

### POST `/api/v1/v1/queries/{query_id}/cache/invalidate`

**Summary**: Invalidate

Invalidate cached results for a specific query.

Args:
    query_id: Query identifier to invalidate

Returns:
    Status confirmation with invalidated query_id

**Parameters**:
- `query_id` (string) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: queries

---

### POST `/api/v1/v1/queries/{query_id}/run`

**Summary**: Run Query

Execute a deterministic query through cached access.

Allows safe parameter overrides from a whitelist:
- year: int
- timeout_s: int
- max_rows: int
- to_percent: list[str]

Args:
    query_id: Query identifier from registry
    req: FastAPI request object
    ttl_s: Cache TTL override (seconds, bounded to 60-86400)
    body: Request body with override_params and ttl_s

Returns:
    Query result with rows, provenance, freshness, and warnings

Raises:
    HTTPException: 404 if query_id not found

**Parameters**:
- `query_id` (string) (required)
- `ttl_s` (string)
- `page` (integer)
- `page_size` (string)

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: queries

---

### POST `/api/v1/v1/queries/{query_id}/stream`

**Summary**: Stream deterministic query rows as JSON.

Stream deterministic query results as a JSON object with chunked rows.

**Parameters**:
- `query_id` (string) (required)
- `ttl_s` (string)

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: queries

---

### POST `/api/v1/v1/queries:batch`

**Summary**: Run Query Batch

Execute multiple deterministic queries in a single request.

**Request Body**: Required

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: queries

---

### GET `/api/v1/v1/ui/cards/ewi`

**Summary**: Ui Cards Ewi

Get KPI cards for early warning indicators (employment drop hotlist).

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (string)
- `threshold` (number)
- `n` (integer)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: ui

---

### GET `/api/v1/v1/ui/cards/top-sectors`

**Summary**: Ui Cards Top Sectors

Get KPI cards for top sectors by employment.

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (string)
- `n` (integer)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: ui

---

### GET `/api/v1/v1/ui/charts/employment-share`

**Summary**: Ui Chart Employment Share

Get gauge data for employment share (male/female/total percentages).

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (string)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: ui

---

### GET `/api/v1/v1/ui/charts/salary-yoy`

**Summary**: Ui Chart Salary Yoy

Get time series chart data for salary year-over-year growth.

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `sector` (string) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: ui

---

### GET `/api/v1/v1/ui/charts/sector-employment`

**Summary**: Ui Chart Sector Employment

Get bar chart data for sector employment in a given year.

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (string)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: ui

---

### GET `/api/v1/v1/ui/dashboard/summary`

**Summary**: Dashboard Summary Html

Get HTML dashboard with embedded PNG charts and KPI cards.

Args:
    queries_dir: Optional queries directory path
    ttl_s: Cache TTL in seconds (60-86400)
    year: Target year (defaults to latest available)
    sector: Sector name for salary YoY chart

Returns:
    HTML document with embedded base64 PNG images

Example:
    GET /v1/ui/dashboard/summary?year=2024&sector=Energy

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (string)
- `sector` (string)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: dashboard

---

### GET `/api/v1/v1/ui/export/csv`

**Summary**: Export Csv

Export UI data as CSV.

Supported resources:
- top-sectors: Top sectors by employment (params: year, n)
- ewi: Early warning indicators (params: year, threshold, n)
- sector-employment: Sector employment breakdown (params: year)
- salary-yoy: Salary year-over-year by sector (params: sector)
- employment-share: Employment share gauge (params: year)

Args:
    resource: Resource type to export
    queries_dir: Optional queries directory path
    ttl_s: Cache TTL in seconds (60-86400)
    year: Target year (defaults to latest)
    n: Top N results (for top-sectors, ewi)
    sector: Sector name (for salary-yoy)
    threshold: Threshold value (for ewi)

Returns:
    CSV file as text/csv with cache headers

**Parameters**:
- `resource` (string) (required)
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (string)
- `n` (integer)
- `sector` (string)
- `threshold` (number)

**Responses**: 200: Deterministic CSV export. See ExportCSVMeta for caching headers., 304: Not modified when If-None-Match matches resource ETag., 422: Validation Error

**Tags**: ui-export

---

### GET `/api/v1/v1/ui/export/png`

**Summary**: Export Png

Optional PNG export. If Pillow is missing or QNWIS_ENABLE_PNG_EXPORT != '1',
respond 406 with JSON and suggest using /v1/ui/export/svg instead.

Args:
    chart: Chart type to export
    queries_dir: Optional queries directory path
    ttl_s: Cache TTL in seconds (60-86400)
    year: Target year (defaults to latest)
    sector: Sector name (for salary-yoy)

Returns:
    PNG file as image/png with cache headers

Raises:
    HTTPException: 406 if PNG export is disabled or Pillow not installed

**Parameters**:
- `chart` (string) (required)
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (string)
- `sector` (string)

**Responses**: 200: PNG snapshot when enabled (requires Pillow)., 304: Not modified when If-None-Match matches resource ETag., 406: PNG export disabled when QNWIS_ENABLE_PNG_EXPORT != 1 or Pillow missing., 422: Validation Error

**Tags**: ui-export

---

### GET `/api/v1/v1/ui/export/salary-yoy.png`

**Summary**: Export Salary Yoy Png

Export salary year-over-year line chart as PNG.

Args:
    queries_dir: Optional queries directory path
    ttl_s: Cache TTL in seconds (60-86400)
    sector: Sector name (required)

Returns:
    PNG image (matplotlib-generated)

Example:
    GET /v1/ui/export/salary-yoy.png?sector=Energy

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `sector` (string) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: dashboard

---

### GET `/api/v1/v1/ui/export/sector-employment.csv`

**Summary**: Export Sector Employment Csv

Export sector employment data as CSV.

Args:
    queries_dir: Optional queries directory path
    ttl_s: Cache TTL in seconds (60-86400)
    year: Target year (required)

Returns:
    CSV file with columns: year, sector, employees

Example:
    GET /v1/ui/export/sector-employment.csv?year=2024

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (integer) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: dashboard

---

### GET `/api/v1/v1/ui/export/sector-employment.png`

**Summary**: Export Sector Employment Png

Export sector employment bar chart as PNG.

Args:
    queries_dir: Optional queries directory path
    ttl_s: Cache TTL in seconds (60-86400)
    year: Target year (required)

Returns:
    PNG image (matplotlib-generated)

Example:
    GET /v1/ui/export/sector-employment.png?year=2024

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (integer) (required)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: dashboard

---

### GET `/api/v1/v1/ui/export/svg`

**Summary**: Export Svg

Export chart as SVG.

Supported charts:
- sector-employment: Bar chart of sector employment (params: year)
- salary-yoy: Line chart of salary YoY by sector (params: sector)

Args:
    chart: Chart type to export
    queries_dir: Optional queries directory path
    ttl_s: Cache TTL in seconds (60-86400)
    year: Target year (defaults to latest)
    sector: Sector name (for salary-yoy)

Returns:
    SVG file as image/svg+xml with cache headers

**Parameters**:
- `chart` (string) (required)
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (string)
- `sector` (string)

**Responses**: 200: Deterministic SVG export. See ExportSVGMeta for caching headers., 304: Not modified when If-None-Match matches resource ETag., 422: Validation Error

**Tags**: ui-export

---

### GET `/api/v1/v1/ui/export/top-sectors.csv`

**Summary**: Export Top Sectors Csv

Export top N sectors by employment as CSV.

Args:
    queries_dir: Optional queries directory path
    ttl_s: Cache TTL in seconds (60-86400)
    year: Target year (defaults to latest available)
    n: Number of top sectors to return

Returns:
    CSV file with columns: year, sector, employees

Example:
    GET /v1/ui/export/top-sectors.csv?year=2024&n=5

**Parameters**:
- `queries_dir` (string)
- `ttl_s` (integer)
- `year` (string)
- `n` (integer)

**Responses**: 200: Successful Response, 422: Validation Error

**Tags**: dashboard

---

### GET `/health`

**Summary**: Health Alias

**Responses**: 200: Successful Response

**Tags**: observability

---

### GET `/health/live`

**Summary**: Health Live

**Responses**: 200: Successful Response

**Tags**: observability

---

### GET `/health/ready`

**Summary**: Health Ready

**Responses**: 200: Successful Response

**Tags**: observability

---

### GET `/metrics`

**Summary**: Metrics

Prometheus metrics endpoint.

Exposes application metrics in Prometheus text format including:
- HTTP request/response metrics (qnwis_requests_total, qnwis_latency_seconds)
- Database operation metrics (qnwis_db_latency_seconds)
- Cache metrics (qnwis_cache_hits_total, qnwis_cache_misses_total)
- Agent execution metrics (qnwis_agent_latency_seconds)

Additional Prometheus metrics from perf module can be scraped here.

**Responses**: 200: Successful Response

**Tags**: observability

---


## Summary

- **Total Endpoints**: 55
- **Total Paths**: 55
- **Tags**: agents.pattern, agents.predictor, agents.scenario, agents.strategy, agents.time, briefing, continuity, council, dashboard, dr, info, notifications, observability, queries, slo, ui, ui-export

---

**Generated**: auto-generated via scripts/export_openapi.py  
**Source**: FastAPI application at `src/qnwis/api/server.py`
