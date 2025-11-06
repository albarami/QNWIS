## Step 12 Dashboards & Exports – Review

### Checklist verification
- **Matplotlib backend**: `src/qnwis/ui/export.py` now forces `matplotlib.use("Agg")` and sets `plt.rcParams["figure.dpi"] = 150` plus `plt.rcParams["savefig.dpi"] = 150` to lock render determinism.
- **Input validation**: every dashboard/export route enforces bounds (`ttl_s: 60–86400`, `year: 2000–2100`, `sector` min length, `n` range) while `_api` continues to clamp TTL internally.
- **Caching headers**: HTML, CSV, SVG, and PNG responses include `Cache-Control: public, max-age=60` and a quoted ETag; If-None-Match matches return `304 Not Modified`.
- **Static HTML hygiene**: `apps/dashboard/static/index.html` embeds CSS inline and contains no external assets; dashboard HTML renderer (`render_dashboard_html`) emits base64 PNGs only.
- **Tests & fixtures**: Integration/unit suites ensure every test swaps `csvcat.BASE` to a `Path` and restores it in a `finally` block.
- **Tooling gates**: `ruff`, `mypy`, and the PowerShell secret scanner all pass with the updated code.

### Determinism settings
```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 150
```
The PNG helpers close each figure immediately after saving, yielding stable bytes and hash-derived ETags.

### Response headers (examples)
```
HTTP/1.1 200 OK
Content-Type: image/png
Cache-Control: public, max-age=60
ETag: "da6d1c80e9c6435c3bb2b6dc8f86dd8c5b35694efef4324e50a4213db2c2e6ce"

HTTP/1.1 304 Not Modified
Cache-Control: public, max-age=60
ETag: "da6d1c80e9c6435c3bb2b6dc8f86dd8c5b35694efef4324e50a4213db2c2e6ce"
```

### cURL walkthrough
```bash
# HTML dashboard (returns inline CSS + base64 PNGs)
curl -i "http://localhost:8000/v1/ui/dashboard/summary?sector=Energy"

# CSV export with ETag replay protection
curl -i "http://localhost:8000/v1/ui/export/sector-employment.csv?year=2024"
curl -i -H 'If-None-Match: "..."' \
     "http://localhost:8000/v1/ui/export/sector-employment.csv?year=2024"

# Deterministic PNG chart
curl -i "http://localhost:8000/v1/ui/export/sector-employment.png?year=2024"
```

### Test & lint commands
- `python -m pytest tests/unit/test_ui_exports.py tests/unit/test_ui_html.py tests/integration/test_api_ui_dashboard.py tests/integration/test_dashboard_static.py --maxfail=1 --disable-warnings -q`
- `python -m pytest tests/integration/test_api_ui_charts.py --maxfail=1 --disable-warnings -q`
- `.\\.venv\\Scripts\\ruff.exe check`
- `python -m mypy src`
- `./scripts/secret_scan.ps1`

All commands completed successfully. The dashboards bundle respects the Step 12 hardening checklist with deterministic exports, strict validation, strong caching headers, and inline-only HTML.
