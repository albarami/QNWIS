## Step 12 Dashboards Bundle – Review & Hardening

### Overview
Step 12 focused on hardening the dashboard exports, tightening input validation, and polishing the static demo. The key changes include:

- Enforced parameter validation across UI and export endpoints (`ttl_s`, `n`, year bounds, sector length).  
- Cache-aware helpers now respect `If-None-Match` and return `304 Not Modified` when hashes match.  
- Added export documentation models (`ExportCSVMeta`, `ExportSVGMeta`) and wired descriptive OpenAPI metadata.  
- Refined SVG renderers to be pure, escape labels, and render a graceful empty-state.  
- PNG export honours `QNWIS_ENABLE_PNG_EXPORT`, emits clear guidance when disabled, and succeeds with Pillow enabled.  
- Static dashboard buttons auto-populate download URLs using the resolved year derived from the API.

### Verified diffs
- `src/qnwis/api/routers/ui.py`: shared cache helper with ETag short-circuit, Query validation, sector employment response now includes `year`.  
- `src/qnwis/api/routers/export.py`: validation mirrored for exports, documentation metadata, 304 handling, PNG gating improvements, OpenAPI header docs.  
- `src/qnwis/ui/svg.py`: `_empty_svg` placeholder, strict escaping, sanity for empty series.  
- `apps/dashboard/static/app.js`: client fetches latest year and rewires download links.  
- Tests updated/added under `tests/integration/test_api_ui_charts.py` & `tests/integration/test_api_ui_export.py` to cover validation, 304 flows, PNG toggles.

### Gates run
- `python -m pytest tests/integration/test_api_ui_charts.py --maxfail=1 --disable-warnings -q`  
- `python -m pytest tests/integration/test_api_ui_export.py --maxfail=1 --disable-warnings -q`  
- `.\\.venv\\Scripts\\ruff.exe check`  
- `python -m mypy src`  
- `./scripts/secret_scan.ps1`

All gates completed successfully (pytest invocations required extended `timeout_ms` due to coverage plug‑ins; both suites reported clean passes).

### curl walk-through
```bash
# CSV export with ETag replay
curl -i "http://localhost:8000/v1/ui/export/csv?resource=top-sectors&n=3"
curl -i -H "If-None-Match: \"<etag-from-first-call>\"" \
     "http://localhost:8000/v1/ui/export/csv?resource=top-sectors&n=3"

# SVG export with validation (year resolved server-side)
curl -i "http://localhost:8000/v1/ui/export/svg?chart=sector-employment&year=2024"

# PNG fallback guidance (default disabled)
curl -i "http://localhost:8000/v1/ui/export/png?chart=salary-yoy&sector=Energy"
```
Expected behaviours: 200 + cache headers on first request, `304 Not Modified` on replay, and a `406` JSON body directing users to SVG/enable flag for PNG unless `QNWIS_ENABLE_PNG_EXPORT=1`.

### PNG fallback note
- Disabled state now raises `406` with `detail="PNG export disabled. Use /v1/ui/export/svg or set QNWIS_ENABLE_PNG_EXPORT=1 with Pillow installed."`
- When `QNWIS_ENABLE_PNG_EXPORT=1` and Pillow is present, endpoint returns deterministic placeholder PNG and cache headers (`ETag`, `Cache-Control`).

### Cheat sheet (routes & metadata)
| Route | Method | Content-Type | Key params (validated) | Notes |
| --- | --- | --- | --- | --- |
| `/v1/ui/cards/top-sectors` | GET | `application/json` | `ttl_s:60-86400`, `year:2000-2100`, `n:1-20` | Responses include `ETag`, `Cache-Control` |
| `/v1/ui/cards/ewi` | GET | `application/json` | `threshold:0-100`, `n:1-20`, year bounds | Uses sanitized thresholds |
| `/v1/ui/charts/sector-employment` | GET | `application/json` | `year:2000-2100`, `ttl_s` clamp | Response now carries `year` field |
| `/v1/ui/charts/salary-yoy` | GET | `application/json` | `sector` length 2-80, `ttl_s` bounds | Sector input trimmed & validated |
| `/v1/ui/export/csv` | GET | `text/csv` | `resource` enum, `ttl_s`, `n`, `threshold`, `year`, `sector` | Strong `ETag`, `Cache-Control`, 304 shortcut |
| `/v1/ui/export/svg` | GET | `image/svg+xml` | `chart` enum, `ttl_s`, `year`, `sector` | SVG safe for empty series |
| `/v1/ui/export/png` | GET | `image/png` | `chart` enum, `ttl_s`, `year`, `sector` | 406 unless `QNWIS_ENABLE_PNG_EXPORT=1` & Pillow |
| `/dash` | GET | `text/html` | – | `StaticFiles(..., html=True)` serves SPA index |

### Additional observations
- Tests temporarily mutate `csvcat.BASE` but now wrap in `try/finally` to guarantee restoration.  
- OpenAPI docs describe export headers through `ExportCSVMeta`/`ExportSVGMeta` field metadata.  
- Static dashboard gracefully survives empty data sets (SVG placeholder) and download links remain in sync with backend-selected year.
