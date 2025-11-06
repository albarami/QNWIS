# QNWIS UI Dashboard Bundle

## Overview

The QNWIS UI Dashboard Bundle provides a production-ready, deterministic dashboard and export system that runs entirely on synthetic CSV data. No network, SQL, or LLM dependencies.

**Features:**
- Minimal HTML dashboard served at `/dash`
- CSV export endpoints for all UI data
- SVG export endpoints for charts (dependency-free)
- Optional PNG export (graceful fallback when Pillow unavailable)
- Deterministic outputs for all operations
- Full test coverage

## Quick Start

### 1. Generate Synthetic Data

```bash
python scripts/seed_synthetic_lmis.py
```

This creates synthetic LMIS data in `qatar_data/synthetic/`.

### 2. Start the Server

```bash
uvicorn src.qnwis.app:app --reload
```

### 3. Access the Dashboard

Open your browser to: **http://localhost:8000/dash**

The dashboard displays:
- Top sectors by employment (KPI cards)
- Sector employment bar chart
- Salary year-over-year line chart

## API Endpoints

### CSV Export

**Endpoint:** `GET /v1/ui/export/csv`

Export UI data as CSV files. Supports multiple resources:

#### Top Sectors
```bash
curl "http://localhost:8000/v1/ui/export/csv?resource=top-sectors&n=5" -o top-sectors.csv
```

Parameters:
- `resource=top-sectors` (required)
- `n` - Number of top sectors (default: 5, range: 1-20)
- `year` - Target year (default: latest available)

#### Early Warning Indicators
```bash
curl "http://localhost:8000/v1/ui/export/csv?resource=ewi&threshold=3.0&n=5" -o ewi.csv
```

Parameters:
- `resource=ewi` (required)
- `threshold` - Percent drop threshold (default: 3.0)
- `n` - Number of sectors (default: 5, range: 1-20)
- `year` - Target year (default: latest available)

#### Sector Employment
```bash
curl "http://localhost:8000/v1/ui/export/csv?resource=sector-employment&year=2024" -o sector-employment.csv
```

Parameters:
- `resource=sector-employment` (required)
- `year` - Target year (default: latest available)

#### Salary Year-over-Year
```bash
curl "http://localhost:8000/v1/ui/export/csv?resource=salary-yoy&sector=Energy" -o salary-yoy.csv
```

Parameters:
- `resource=salary-yoy` (required)
- `sector` - Sector name (default: "Energy")

#### Employment Share
```bash
curl "http://localhost:8000/v1/ui/export/csv?resource=employment-share&year=2024" -o employment-share.csv
```

Parameters:
- `resource=employment-share` (required)
- `year` - Target year (default: latest available)

### SVG Export

**Endpoint:** `GET /v1/ui/export/svg`

Export charts as dependency-free SVG images.

#### Sector Employment Bar Chart
```bash
curl "http://localhost:8000/v1/ui/export/svg?chart=sector-employment&year=2024" -o chart.svg
```

Parameters:
- `chart=sector-employment` (required)
- `year` - Target year (default: latest available)

#### Salary YoY Line Chart
```bash
curl "http://localhost:8000/v1/ui/export/svg?chart=salary-yoy&sector=Energy" -o chart.svg
```

Parameters:
- `chart=salary-yoy` (required)
- `sector` - Sector name (default: "Energy")

### PNG Export (Optional)

**Endpoint:** `GET /v1/ui/export/png`

Optional PNG export. Requires Pillow and environment variable.

**Enable PNG Export:**
```bash
export QNWIS_ENABLE_PNG_EXPORT=1
pip install pillow
```

**Usage:**
```bash
curl "http://localhost:8000/v1/ui/export/png?chart=sector-employment&year=2024" -o chart.png
```

**Graceful Fallback:**
- If `QNWIS_ENABLE_PNG_EXPORT != '1'`: Returns HTTP 406 with suggestion to use SVG
- If Pillow not installed: Returns HTTP 406 with installation instructions

## Architecture

### Components

```
src/qnwis/
├── ui/
│   ├── svg.py          # Dependency-free SVG renderers
│   ├── cards.py        # KPI card data builders
│   └── charts.py       # Chart data builders
├── api/routers/
│   ├── export.py       # CSV/SVG/PNG export endpoints
│   └── ui.py           # JSON API endpoints for dashboard
└── app.py              # FastAPI app with static mount

apps/dashboard/static/
├── index.html          # Dashboard HTML
├── styles.css          # Dashboard styles
└── app.js              # Dashboard JavaScript
```

### Data Flow

1. **Dashboard loads** → Fetches JSON from `/v1/ui/cards/*` and `/v1/ui/charts/*`
2. **User clicks export** → Downloads CSV/SVG from `/v1/ui/export/*`
3. **All data** → Sourced from `DataAPI` → Queries synthetic CSVs
4. **Deterministic** → Same inputs always produce same outputs

## Testing

### Run All Tests

```bash
pytest tests/unit/test_svg_renderer.py -v
pytest tests/integration/test_api_ui_export.py -v
pytest tests/integration/test_dashboard_static.py -v
```

### Unit Tests

- `test_svg_renderer.py` - SVG generation, escaping, determinism

### Integration Tests

- `test_api_ui_export.py` - CSV/SVG/PNG endpoints with synthetic data
- `test_dashboard_static.py` - Static file serving, HTML structure

## Configuration

### Environment Variables

- `QNWIS_ENABLE_PNG_EXPORT` - Set to `1` to enable PNG export (requires Pillow)
- `QNWIS_RATE_LIMIT_RPS` - Rate limiting (optional)

### Cache Headers

All export endpoints return:
- `ETag` - MD5 hash of response payload (for caching)
- `Cache-Control: public, max-age=60` - Browser caching

## Deterministic Behavior

All components guarantee deterministic outputs:

1. **SVG Renderer** - Same title/data → Same SVG markup
2. **CSV Export** - Same resource/params → Same CSV content
3. **DataAPI** - Same query/year → Same results (from synthetic CSVs)
4. **TTL Clamping** - Input TTL clamped to 60-86400 seconds

## Windows Compatibility

✅ No shell commands
✅ Uses `pathlib` for cross-platform paths
✅ No POSIX-specific dependencies
✅ All tests pass on Windows

## Production Deployment

### Step 1: Generate Synthetic Data
```bash
python scripts/seed_synthetic_lmis.py
```

### Step 2: Configure Environment
```bash
# Optional: Enable PNG export
export QNWIS_ENABLE_PNG_EXPORT=1

# Optional: Set rate limiting
export QNWIS_RATE_LIMIT_RPS=10
```

### Step 3: Run Server
```bash
uvicorn src.qnwis.app:app --host 0.0.0.0 --port 8000
```

### Step 4: Verify
```bash
# Check dashboard
curl http://localhost:8000/dash

# Check health
curl http://localhost:8000/health

# Test CSV export
curl "http://localhost:8000/v1/ui/export/csv?resource=top-sectors&n=5"

# Test SVG export
curl "http://localhost:8000/v1/ui/export/svg?chart=sector-employment&year=2024"
```

## Examples

### Dashboard Screenshot Workflow

1. Open dashboard: `http://localhost:8000/dash`
2. Click "Download SVG" to get vector chart
3. Open SVG in browser or Inkscape
4. Take screenshot or convert to PNG as needed

### Data Analysis Workflow

1. Export CSV: `curl "http://localhost:8000/v1/ui/export/csv?resource=sector-employment&year=2024" -o data.csv`
2. Load in Excel/Python/R for analysis
3. All data is deterministic and reproducible

### Custom Dashboard

Modify `apps/dashboard/static/index.html` to:
- Add new sections
- Change chart parameters
- Integrate with your own CSS framework
- Add interactivity with JavaScript

## Troubleshooting

### Dashboard Shows Empty
- **Cause:** Synthetic data not generated
- **Fix:** Run `python scripts/seed_synthetic_lmis.py`

### Export Returns Empty CSV
- **Cause:** No data for requested year/sector
- **Fix:** Check available years with `/v1/ui/cards/top-sectors` first

### PNG Export Returns 406
- **Expected:** PNG is optional and disabled by default
- **Fix:** Set `QNWIS_ENABLE_PNG_EXPORT=1` and install Pillow
- **Alternative:** Use SVG export instead

### Rate Limit Errors
- **Cause:** Too many requests
- **Fix:** Increase `QNWIS_RATE_LIMIT_RPS` or disable rate limiting

## Next Steps

- **Extend Charts:** Add more chart types in `src/qnwis/ui/svg.py`
- **Custom Exports:** Add new resources in `src/qnwis/api/routers/export.py`
- **Dashboard UI:** Enhance `apps/dashboard/static/` with your framework
- **Real Data:** Replace synthetic CSVs with production data sources

## Support

For issues or questions:
1. Check test files for usage examples
2. Review API documentation at `http://localhost:8000/docs`
3. Verify deterministic behavior with provided tests
