# UI Demos: FastAPI Cards & Charts

**Production-ready UI endpoints for QNWIS dashboards — 100% deterministic, synthetic data only.**

## Overview

The UI demo system provides JSON endpoints for frontend components:
- **Cards**: KPI cards (top sectors, early warning indicators, employment gauges)
- **Charts**: Time series and bar charts (salary trends, sector employment)

All endpoints:
- Run on **synthetic CSV data** via `DataAPI`
- **No network, SQL, or LLM** dependencies
- **Deterministic** and **Windows-friendly**
- Include **parameter validation** and **clamping**
- Support **configurable caching** (TTL + HTTP cache hints)

All UI demo endpoints emit `Cache-Control: public, max-age=60` and an `ETag`
derived from the JSON payload. Clients can reuse responses for 60 seconds and
leverage conditional requests for slim refreshes.

## Architecture

```
┌─────────────────┐
│  FastAPI UI     │
│  Endpoints      │ → /v1/ui/cards/* & /v1/ui/charts/*
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  UI Builders    │
│  cards.py       │ → build_top_sectors_cards()
│  charts.py      │ → salary_yoy_series()
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  DataAPI        │ → Cached queries on synthetic CSVs
└─────────────────┘
```

## FastAPI Endpoints

### Cards Endpoints

#### 1. Top Sectors by Employment

**Endpoint**: `GET /v1/ui/cards/top-sectors`

**Query Parameters**:
- `year` (optional): Target year (defaults to `DataAPI.latest_year("sector_employment")`)
- `n` (optional): Number of sectors (1-20, default 5)
- `ttl_s` (optional): Cache TTL in seconds (60-86400, default 300)
- `queries_dir` (optional): Path to queries directory

**Example Request**:
```bash
curl "http://localhost:8000/v1/ui/cards/top-sectors?year=2024&n=5"
```

**Example Response**:
```json
{
  "cards": [
    {
      "title": "Energy",
      "subtitle": "Employment 2024",
      "kpi": 150000,
      "unit": "persons",
      "meta": {"year": 2024}
    },
    {
      "title": "Construction",
      "subtitle": "Employment 2024",
      "kpi": 120000,
      "unit": "persons",
      "meta": {"year": 2024}
    }
  ]
}
```

---

#### 2. Early Warning Indicators (EWI)

**Endpoint**: `GET /v1/ui/cards/ewi`

**Query Parameters**:
- `year` (optional): Target year (defaults to `DataAPI.latest_year("ewi_employment_drop")`)
- `threshold` (optional): Drop percentage threshold (0-100, default 3.0)
- `n` (optional): Number of sectors (1-20, default 5)
- `ttl_s` (optional): Cache TTL in seconds (60-86400, default 300)
- `queries_dir` (optional): Path to queries directory

**Example Request**:
```bash
curl "http://localhost:8000/v1/ui/cards/ewi?threshold=3.5&n=5"
```

**Example Response**:
```json
{
  "cards": [
    {
      "title": "Construction",
      "subtitle": "EWI drop 2024",
      "kpi": 4.5,
      "unit": "percent",
      "meta": {"year": 2024, "threshold": 3.5}
    },
    {
      "title": "Retail",
      "subtitle": "EWI drop 2024",
      "kpi": 3.8,
      "unit": "percent",
      "meta": {"year": 2024, "threshold": 3.5}
    }
  ]
}
```

---

### Charts Endpoints

#### 3. Salary Year-over-Year Growth

**Endpoint**: `GET /v1/ui/charts/salary-yoy`

**Query Parameters**:
- `sector` (required): Sector name (min 2 chars)
- `ttl_s` (optional): Cache TTL in seconds (60-86400, default 300)
- `queries_dir` (optional): Path to queries directory

**Example Request**:
```bash
curl "http://localhost:8000/v1/ui/charts/salary-yoy?sector=Energy"
```

**Example Response**:
```json
{
  "title": "Salary YoY - Energy",
  "series": [
    {"x": 2022, "y": 3.5},
    {"x": 2023, "y": 4.2},
    {"x": 2024, "y": 2.8}
  ]
}
```

---

#### 4. Sector Employment Bar Chart

**Endpoint**: `GET /v1/ui/charts/sector-employment`

**Query Parameters**:
- `year` (optional): Target year (2000-2100, defaults to `DataAPI.latest_year("sector_employment")`)
- `ttl_s` (optional): Cache TTL in seconds (60-86400, default 300)
- `queries_dir` (optional): Path to queries directory

**Example Request**:
```bash
curl "http://localhost:8000/v1/ui/charts/sector-employment?year=2024"
```

**Example Response**:
```json
{
  "title": "Sector Employment - 2024",
  "categories": ["Energy", "Construction", "Finance", "Healthcare", "Retail"],
  "values": [150000, 120000, 95000, 85000, 75000]
}
```

---

#### 5. Employment Share Gauge

**Endpoint**: `GET /v1/ui/charts/employment-share`

**Query Parameters**:
- `year` (optional): Target year (defaults to `DataAPI.latest_year("employment_share_all")`)
- `ttl_s` (optional): Cache TTL in seconds (60-86400, default 300)
- `queries_dir` (optional): Path to queries directory

**Example Request**:
```bash
curl "http://localhost:8000/v1/ui/charts/employment-share?year=2024"
```

**Example Response**:
```json
{
  "year": 2024,
  "male": 75.5,
  "female": 24.5,
  "total": 100.0
}
```

---

## Running with Synthetic Data

### 1. Generate Synthetic Data Pack

```powershell
# Generate synthetic CSV data
python scripts/seed_synthetic_lmis.py

# Or use pytest with tmp_path fixture (automatic)
pytest tests/unit/test_ui_helpers.py -v
```

### 2. Start FastAPI Server

```powershell
# Set queries directory (optional, defaults to src/qnwis/data/queries)
$env:QNWIS_QUERIES_DIR = "src/qnwis/data/queries"

# Start server
uvicorn src.qnwis.app:app --reload --port 8000
```

### 3. Test Endpoints

```powershell
# Test cards endpoints
curl "http://localhost:8000/v1/ui/cards/top-sectors?n=3"
curl "http://localhost:8000/v1/ui/cards/ewi?threshold=3.0"

# Test charts endpoints
curl "http://localhost:8000/v1/ui/charts/salary-yoy?sector=Energy"
curl "http://localhost:8000/v1/ui/charts/sector-employment?year=2024"
curl "http://localhost:8000/v1/ui/charts/employment-share"
```

---

## Optional: Chainlit Interactive Demo

### Installation (Optional)

```powershell
pip install chainlit
```

### Running Chainlit App

```powershell
# Start Chainlit chat interface
chainlit run apps/chainlit/app.py -w

# Open browser to http://localhost:8000
```

### Features

The Chainlit app provides an interactive chat interface with three actions:
1. **Top sectors**: Display top 5 sectors by employment
2. **EWI hotlist**: Show early warning indicators
3. **Salary YoY (Energy)**: Display Energy sector salary trends

**Note**: If Chainlit is not installed, the app module can still be imported safely. The `if cl:` guard ensures handlers are only registered when Chainlit is available.

---

## UI Builder Functions

### Cards Builders (`src/qnwis/ui/cards.py`)

#### `build_top_sectors_cards(api, year, top_n)`

Build KPI cards for top sectors by employment.

**Parameters**:
- `api` (DataAPI): DataAPI instance
- `year` (int, optional): Target year (defaults to latest)
- `top_n` (int): Number of sectors (clamped to 1-20)

**Returns**: List of card dictionaries with keys:
- `title`: Sector name
- `subtitle`: Description with year
- `kpi`: Employment count
- `unit`: "persons"
- `meta`: `{"year": int}`

---

#### `build_ewi_hotlist_cards(api, year, threshold, top_n)`

Build cards for early warning indicators.

**Parameters**:
- `api` (DataAPI): DataAPI instance
- `year` (int, optional): Target year (defaults to latest)
- `threshold` (float): Drop percentage threshold
- `top_n` (int): Number of sectors (clamped to 1-20)

**Returns**: List of card dictionaries with keys:
- `title`: Sector name
- `subtitle`: Description with year
- `kpi`: Employment drop percentage
- `unit`: "percent"
- `meta`: `{"year": int, "threshold": float}`

---

#### `build_employment_share_gauge(api, year)`

Build gauge data for employment share.

**Parameters**:
- `api` (DataAPI): DataAPI instance
- `year` (int, optional): Target year (defaults to latest)

**Returns**: Dictionary with keys:
- `year`: Data year
- `male`: Male employment percentage (or None)
- `female`: Female employment percentage (or None)
- `total`: Total employment percentage (or None)

---

### Charts Builders (`src/qnwis/ui/charts.py`)

#### `salary_yoy_series(api, sector)`

Build time series for salary year-over-year growth.

**Parameters**:
- `api` (DataAPI): DataAPI instance
- `sector` (str): Sector name

**Returns**: Dictionary with keys:
- `title`: Chart title with sector name
- `series`: List of `{"x": year, "y": yoy_percent}` points

---

#### `sector_employment_bar(api, year)`

Build bar chart data for sector employment.

**Parameters**:
- `api` (DataAPI): DataAPI instance
- `year` (int): Target year

**Returns**: Dictionary with keys:
- `title`: Chart title with year
- `categories`: List of sector names
- `values`: List of employment counts (aligned with categories)

---

## Parameter Validation & Clamping

### Automatic Clamping

All endpoints implement safe parameter clamping:

- **`n` (top_n)**: Clamped to 1-20 range
  ```python
  n = max(1, min(20, int(n)))
  ```

- **`ttl_s`**: Clamped to 60-86400 seconds (1 minute to 1 day)
  ```python
  ttl = max(60, min(86400, int(ttl_s)))
  ```

### FastAPI Query Validation

Endpoints use FastAPI `Query` for validation:

```python
@router.get("/v1/ui/cards/top-sectors")
def ui_cards_top_sectors(
    n: int = Query(default=5, ge=1, le=20),  # Min 1, max 20
    year: Optional[int] = Query(default=None)
):
    ...
```

Invalid parameters return **422 Unprocessable Entity**:

```bash
# Invalid: n out of range
curl "http://localhost:8000/v1/ui/cards/top-sectors?n=0"
# Response: {"detail": [{"loc": ["query", "n"], "msg": "ensure this value is greater than or equal to 1", ...}]}
```

---

## Testing

### Running Tests

```powershell
# Run all UI-related tests
pytest tests/unit/test_ui_helpers.py -v
pytest tests/integration/test_api_ui_cards.py -v
pytest tests/integration/test_api_ui_charts.py -v
pytest tests/unit/test_chainlit_import.py -v

# Run with coverage
pytest tests/ -k ui --cov=src/qnwis/ui --cov=src/qnwis/api/routers/ui -v
```

### Test Coverage

**Unit Tests** (`test_ui_helpers.py`):
- Card and chart builder functions
- Parameter clamping (top_n, ttl_s)
- Year defaulting to latest
- Data structure validation

**Integration Tests** (`test_api_ui_cards.py`, `test_api_ui_charts.py`):
- FastAPI endpoint status codes
- Query parameter validation (422 errors)
- Response JSON structure
- Boundary value testing (min/max parameters)

**Import Tests** (`test_chainlit_import.py`):
- Graceful Chainlit import handling
- Module imports without errors
- Conditional handler registration

---

## Response Shapes Reference

### Card Shape

```typescript
interface Card {
  title: string;          // Sector or indicator name
  subtitle: string;       // Description with year
  kpi: number;            // Numeric value (employment count or percentage)
  unit: string;           // "persons" or "percent"
  meta: {
    year: number;
    threshold?: number;   // Only in EWI cards
  };
}
```

### Chart Shapes

#### Time Series (Salary YoY)

```typescript
interface TimeSeriesChart {
  title: string;
  series: Array<{
    x: number;  // Year
    y: number;  // YoY percentage
  }>;
}
```

#### Bar Chart (Sector Employment)

```typescript
interface BarChart {
  title: string;
  categories: string[];  // Sector names
  values: number[];      // Employment counts (aligned with categories)
}
```

#### Gauge (Employment Share)

```typescript
interface Gauge {
  year: number;
  male: number | null;    // Male percentage
  female: number | null;  // Female percentage
  total: number | null;   // Total percentage
}
```

---

## Windows Compatibility

All components are Windows-friendly:
- **Path handling**: Uses `os.path` for cross-platform paths
- **No shell calls**: Pure Python, no subprocess dependencies
- **PowerShell examples**: All command examples use PowerShell syntax
- **File I/O**: Uses UTF-8 encoding with explicit declaration

**Example (PowerShell)**:

```powershell
# Set environment variable
$env:QNWIS_QUERIES_DIR = "src\qnwis\data\queries"

# Run tests
pytest tests\unit\test_ui_helpers.py -v

# Start server
uvicorn src.qnwis.app:app --reload
```

---

## Deterministic Behavior Guarantees

1. **No Network Calls**: All data from local CSV files
2. **No SQL Queries**: Pure Python processing via DataAPI
3. **No LLM Inference**: No AI/ML models involved
4. **Reproducible**: Same input → same output (deterministic synthetic data)
5. **Cache-Safe**: TTL-based caching with explicit invalidation

**Verification**:

```python
# Same query returns identical results
api = DataAPI("src/qnwis/data/queries", ttl_s=300)
result1 = build_top_sectors_cards(api, year=2024, top_n=5)
result2 = build_top_sectors_cards(api, year=2024, top_n=5)
assert result1 == result2  # ✓ Deterministic
```

---

## Success Criteria

✅ **Endpoints Available**: All 5 endpoints return 200 OK  
✅ **Tests Passing**: 8-12 new tests pass (unit + integration)  
✅ **Parameter Validation**: Invalid params return 422 errors  
✅ **Clamping Works**: top_n and ttl_s correctly bounded  
✅ **Documentation Complete**: This file covers all endpoints and usage  
✅ **Chainlit Optional**: App runs with/without Chainlit installed  
✅ **Windows-Friendly**: No shell calls, PowerShell examples  
✅ **Deterministic**: Reproducible results from synthetic data  

---

## Troubleshooting

### Issue: 404 Not Found on UI endpoints

**Solution**: Ensure UI router is registered in `src/qnwis/app.py`:

```python
from .api.routers import ui as ui_router
app.include_router(ui_router.router)
```

---

### Issue: Empty cards/charts

**Solution**: Verify synthetic data exists in CSV catalog:

```powershell
# Check for CSV files
ls data/catalog/*.csv

# Regenerate if missing
python scripts/seed_synthetic_lmis.py
```

---

### Issue: Chainlit not found

**Solution**: This is expected if Chainlit is not installed. The app gracefully handles this:

```python
# apps/chainlit/app.py safely imports
try:
    import chainlit as cl
except Exception:
    cl = None  # Handlers only register if cl is not None
```

Install Chainlit only if you need the interactive demo:

```powershell
pip install chainlit
```

---

## Next Steps

1. **Frontend Integration**: Use these JSON endpoints in React/Vue/Angular dashboards
2. **Custom Cards**: Extend `cards.py` with domain-specific builders
3. **Additional Charts**: Add pie charts, heatmaps, scatter plots in `charts.py`
4. **Real-Time Updates**: Implement WebSocket endpoints for live data
5. **Export Features**: Add CSV/Excel export endpoints for chart data

---

## References

- **DataAPI Documentation**: `docs/DETERMINISTIC_DATA_LAYER_SPECIFICATION.md`
- **Synthetic Data**: `scripts/seed_synthetic_lmis.py`
- **FastAPI Guide**: https://fastapi.tiangolo.com/
- **Chainlit Docs**: https://docs.chainlit.io/

---

**Last Updated**: November 2025  
**Maintainer**: QNWIS Development Team  
**Status**: Production-Ready ✅
