# QNWIS Dashboards V1 — Matplotlib-Based

## Overview

Production-ready HTML dashboards and PNG/CSV exports powered by matplotlib and the deterministic DataAPI. All content runs on synthetic data with no network, SQL, or LLM dependencies.

**Features:**
- Self-contained HTML dashboard with embedded base64 PNG charts
- Matplotlib-based PNG chart exports (headless Agg backend)
- CSV table exports for all data
- ETag and Cache-Control headers on all endpoints
- Deterministic output (same inputs → same outputs)
- Windows-compatible (no shell dependencies)

## Quick Start

### 1. Install Dependencies

```bash
# Install matplotlib if not already present
pip install matplotlib>=3.8,<3.9
```

### 2. Generate Synthetic Data

```bash
python scripts/seed_synthetic_lmis.py
```

### 3. Start Server

```bash
uvicorn src.qnwis.app:app --reload
```

### 4. Access Dashboard

Open browser to: **http://localhost:8000/v1/ui/dashboard/summary**

## API Endpoints

### HTML Dashboard

**Endpoint:** `GET /v1/ui/dashboard/summary`

Self-contained HTML page with embedded PNG charts and KPI cards.

**Parameters:**
- `year` (optional): Target year, defaults to latest available
- `sector` (optional): Sector for salary YoY chart, default "Energy"
- `queries_dir` (optional): Custom queries directory path
- `ttl_s` (optional): Cache TTL in seconds (60-86400), default 300

**Example:**
```bash
curl "http://localhost:8000/v1/ui/dashboard/summary?year=2024&sector=Energy" > dashboard.html
```

**Features:**
- Two embedded PNG charts (salary YoY, sector employment)
- 4 top sector KPI cards
- 4 early warning indicator cards
- Responsive grid layout
- No external dependencies (CSS inline, images base64)

---

### PNG Exports

#### Salary Year-over-Year Line Chart

**Endpoint:** `GET /v1/ui/export/salary-yoy.png`

**Parameters:**
- `sector` (required): Sector name, min 2 characters
- `queries_dir` (optional): Custom queries directory path
- `ttl_s` (optional): Cache TTL, default 300

**Example:**
```bash
curl "http://localhost:8000/v1/ui/export/salary-yoy.png?sector=Energy" -o salary-yoy.png
```

#### Sector Employment Bar Chart

**Endpoint:** `GET /v1/ui/export/sector-employment.png`

**Parameters:**
- `year` (required): Target year (2000-2100)
- `queries_dir` (optional): Custom queries directory path
- `ttl_s` (optional): Cache TTL, default 300

**Example:**
```bash
curl "http://localhost:8000/v1/ui/export/sector-employment.png?year=2024" -o employment.png
```

---

### CSV Exports

#### Sector Employment Table

**Endpoint:** `GET /v1/ui/export/sector-employment.csv`

**Parameters:**
- `year` (required): Target year (2000-2100)
- `queries_dir` (optional): Custom queries directory path
- `ttl_s` (optional): Cache TTL, default 300

**Columns:** `year, sector, employees`

**Example:**
```bash
curl "http://localhost:8000/v1/ui/export/sector-employment.csv?year=2024" -o employment.csv
```

#### Top Sectors Table

**Endpoint:** `GET /v1/ui/export/top-sectors.csv`

**Parameters:**
- `year` (optional): Target year, defaults to latest
- `n` (optional): Number of sectors (1-20), default 5
- `queries_dir` (optional): Custom queries directory path
- `ttl_s` (optional): Cache TTL, default 300

**Columns:** `year, sector, employees`

**Example:**
```bash
curl "http://localhost:8000/v1/ui/export/top-sectors.csv?year=2024&n=10" -o top-sectors.csv
```

---

## Architecture

### Components

```
src/qnwis/
├── ui/
│   ├── export.py       # PNG (matplotlib) + CSV exports
│   ├── html.py         # HTML dashboard renderer
│   ├── svg.py          # SVG renderer (lightweight alternative)
│   ├── cards.py        # KPI card builders
│   └── charts.py       # Chart data builders
├── api/routers/
│   ├── ui_dashboard.py # PNG/CSV/HTML endpoints (matplotlib-based)
│   ├── export.py       # SVG/CSV endpoints (dependency-free)
│   └── ui.py           # JSON API endpoints
└── app.py              # FastAPI app with all routers
```

### Data Flow

1. **HTTP Request** → FastAPI router
2. **Router** → DataAPI queries synthetic CSVs
3. **DataAPI** → Returns structured data
4. **Renderer** → Generates PNG (matplotlib) or CSV
5. **Response** → Binary data with ETag/Cache-Control headers

### Matplotlib Configuration

```python
import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
```

**Why Agg?**
- No GUI dependencies
- Deterministic rendering
- Windows-compatible
- Thread-safe

---

## Caching

All endpoints return cache headers:

```http
ETag: "sha256_hash_of_payload"
Cache-Control: public, max-age=60
```

**Client-side caching:**
- Browsers automatically cache responses
- CDNs can cache based on ETag
- Clients can validate with If-None-Match header

**Deterministic ETags:**
- Same parameters always produce same ETag
- Different parameters always produce different ETags
- SHA256 hash of response payload

---

## Configuration

### Environment Variables

None required. All endpoints work with defaults.

**Optional:**
- `QNWIS_RATE_LIMIT_RPS` - Rate limiting (requests per second)
- `QNWIS_QUERIES_DIR` - Custom queries directory path

### Parameter Validation

All endpoints validate inputs:
- `year`: Must be 2000-2100
- `sector`: Min 2 characters, max 80
- `n`: Must be 1-20
- `ttl_s`: Clamped to 60-86400 seconds

---

## Testing

### Run All Tests

```bash
# Unit tests
python -m pytest tests/unit/test_ui_exports.py -v
python -m pytest tests/unit/test_ui_html.py -v

# Integration tests
python -m pytest tests/integration/test_api_ui_dashboard.py -v
```

### Test Coverage

**Unit Tests:**
- `test_ui_exports.py` - PNG/CSV generation, determinism, ETags
- `test_ui_html.py` - HTML rendering, structure, embedded images

**Integration Tests:**
- `test_api_ui_dashboard.py` - HTTP endpoints, validation, caching

---

## Examples

### Example 1: Dashboard with Custom Sector

```bash
curl "http://localhost:8000/v1/ui/dashboard/summary?year=2024&sector=Technology" > tech-dashboard.html
```

Open `tech-dashboard.html` in browser to view dashboard with Technology sector salary trends.

### Example 2: Export All Data for Year

```bash
# Get employment data
curl "http://localhost:8000/v1/ui/export/sector-employment.csv?year=2024" -o data.csv

# Get employment chart
curl "http://localhost:8000/v1/ui/export/sector-employment.png?year=2024" -o chart.png
```

### Example 3: Compare Sectors

```bash
# Export PNGs for multiple sectors
for sector in Energy Technology Healthcare Manufacturing; do
  curl "http://localhost:8000/v1/ui/export/salary-yoy.png?sector=$sector" -o "${sector}.png"
done
```

### Example 4: Automated Reporting

```python
import requests

# Generate dashboard
r = requests.get("http://localhost:8000/v1/ui/dashboard/summary", params={
    "year": 2024,
    "sector": "Energy"
})

with open("report.html", "w") as f:
    f.write(r.text)

# Download charts
charts = [
    ("salary-yoy.png", {"sector": "Energy"}),
    ("sector-employment.png", {"year": 2024}),
]

for filename, params in charts:
    r = requests.get(f"http://localhost:8000/v1/ui/export/{filename}", params=params)
    with open(filename, "wb") as f:
        f.write(r.content)
```

---

## Comparison: Matplotlib vs SVG

| Feature | Matplotlib (ui_dashboard.py) | SVG (export.py) |
|---------|------------------------------|-----------------|
| Dependencies | matplotlib>=3.8 | None |
| Output Format | PNG (raster) | SVG (vector) |
| File Size | ~50-100KB | ~5-10KB |
| Scalability | Fixed resolution | Infinite |
| Browser Support | All | All modern |
| Print Quality | DPI-dependent | Perfect |
| Deterministic | ✅ Yes | ✅ Yes |
| Use Case | Reports, exports | Web dashboards |

**Recommendation:**
- Use **PNG/matplotlib** for: Email reports, PDFs, fixed-resolution exports
- Use **SVG** for: Interactive dashboards, scalable web content

Both systems coexist in the codebase. Choose based on your use case.

---

## Troubleshooting

### Dashboard Shows No Images

**Cause:** Synthetic data not generated or matplotlib not installed

**Fix:**
```bash
python scripts/seed_synthetic_lmis.py
pip install matplotlib>=3.8,<3.9
```

### PNG Export Returns Empty/Corrupt Image

**Cause:** Matplotlib Agg backend not configured

**Fix:** Ensure `matplotlib.use("Agg")` is called before importing pyplot

### CSV Export Returns Empty

**Cause:** No data for requested year

**Fix:** Check available years:
```bash
curl "http://localhost:8000/v1/ui/cards/top-sectors" | jq
```

### Matplotlib Import Error on Windows

**Cause:** Missing Visual C++ redistributables

**Fix:** Install from https://aka.ms/vs/17/release/vc_redist.x64.exe

---

## Performance

### Benchmark Results (Synthetic Data)

- HTML Dashboard: ~200-300ms (includes 2 PNG renders)
- PNG Export: ~100-150ms per chart
- CSV Export: ~20-30ms
- Served from cache (ETag match): <5ms

### Optimization Tips

1. **Enable client caching:** Check ETag before re-downloading
2. **CDN distribution:** Place CDN in front of export endpoints
3. **Pre-generate:** Generate common dashboards on schedule
4. **Increase TTL:** Use longer cache TTL for historical data

---

## Production Deployment

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
pip install matplotlib>=3.8,<3.9
```

### Step 2: Generate Data

```bash
python scripts/seed_synthetic_lmis.py
```

### Step 3: Configure Server

```bash
export QNWIS_RATE_LIMIT_RPS=10  # Optional rate limiting
```

### Step 4: Run with Gunicorn

```bash
gunicorn src.qnwis.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Step 5: Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/ui/dashboard/summary
```

---

## Security Considerations

- ✅ No user-uploaded content (all synthetic data)
- ✅ Input validation on all parameters
- ✅ No shell execution
- ✅ No SQL injection (reads CSVs only)
- ✅ Rate limiting available
- ✅ CORS configurable

---

## Next Steps

- **Custom Charts:** Add new chart types in `src/qnwis/ui/export.py`
- **Dashboard Layout:** Modify `src/qnwis/ui/html.py` for custom layouts
- **Real Data:** Replace synthetic CSVs with production data
- **Branding:** Update CSS in `html.py` with your theme

---

## Support

For issues or questions:
1. Check test files for usage examples
2. Review API docs at `http://localhost:8000/docs`
3. Verify matplotlib Agg backend is configured
4. Ensure synthetic data is generated

---

## Changelog

### V1 (Current)
- HTML dashboard with embedded PNG charts
- Matplotlib-based PNG exports (headless Agg)
- CSV table exports
- ETag caching support
- Full test coverage
