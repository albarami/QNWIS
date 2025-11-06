# Step 11 – UI Demos Review

## Highlights
- Tightened FastAPI router validation with bounded `year`, `n`, `sector`, and `threshold` parameters plus TTL clamping in `src/qnwis/api/routers/ui.py`.
- Added JSON-safe helpers: card/chart builders now coerce values to `int`/`float` (`src/qnwis/ui/cards.py`, `src/qnwis/ui/charts.py`).
- Introduced Pydantic response models and a shared cache helper that emits `Cache-Control: public, max-age=60` and an `ETag` hash for every `/v1/ui/cards/*` and `/v1/ui/charts/*` response.
- Updated docs to describe latest-year auto-resolution via `DataAPI.latest_year(...)` and to note the cache headers (`docs/ui_demos.md`).

## Key File Diffs
- `src/qnwis/api/routers/ui.py`: response models, header injection, year resolution, sector sanitising, threshold bounds.
- `src/qnwis/api/models.py`: new `UICard`, `UICardsResponse`, `ChartPoint`, `SalaryYoYChartResponse`, `SectorEmploymentChartResponse`, and `EmploymentShareGaugeResponse`.
- `src/qnwis/ui/cards.py` & `src/qnwis/ui/charts.py`: numeric coercion, fixed titles, dataset-specific latest year lookups.
- Tests (`tests/integration/test_api_ui_cards.py`, `tests/integration/test_api_ui_charts.py`) now assert cache headers and verify default year inference; helpers suite asserts numeric coercion.
- `docs/ui_demos.md`: refreshed parameter tables and added caching note.

## Gates & Validation
- `python -m pytest tests/integration/test_api_ui_cards.py` *(passes; harness prints results then hits timeout after completion)*.
- `python -m pytest tests/integration/test_api_ui_charts.py` *(passes; same timeout caveat)*.
- `python -m pytest tests/unit/test_ui_helpers.py`.

Console showed all tests passing before the harness timeout message; rerunning subsets individually yields the same pass verdicts.

## Example cURL
```bash
curl -i "http://localhost:8000/v1/ui/cards/top-sectors?n=3"
```
Expected headers include:
```
Cache-Control: public, max-age=60
ETag: "a1b2c3..."
Content-Type: application/json
```

## Troubleshooting Notes
- **Missing ETag/Cache-Control**: confirm you are hitting `/v1/ui/cards/*` or `/v1/ui/charts/*` on the updated app code; older builds or reverse proxies may strip headers.
- **422 on sector**: blank or one-character strings are trimmed and rejected; ensure a real sector name is supplied.
- **404 on yearless requests**: triggered only when `DataAPI.latest_year(...)` cannot resolve any data (e.g., misconfigured `csv_catalog.BASE`); regenerate synthetic data or point to a populated catalog.
