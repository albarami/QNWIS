Step 3 Fix Review
=================

Updates
-------
- Added explicit cache metrics (`hits`, `misses`, `invalidations`) in `src/qnwis/data/deterministic/cache_access.py` with unit coverage for invalidate flag, TTL=0 bypass, and the compression envelope decode paths (`tests/unit/test_execute_cached.py`, `tests/unit/test_execute_cached_metrics.py`, `tests/unit/test_cache_access_errors.py`).
- Hardened catalog registry against missing files, directories, and duplicate IDs (`src/qnwis/data/catalog/registry.py`, `tests/unit/test_catalog_registry.py`, `tests/unit/test_registry.py`).
- Expanded freshness verifier coverage for ISO timestamps, bad dates, string/numeric years, auto/API sentinels, and parse-guard fallbacks (`tests/unit/test_freshness.py`, `tests/unit/test_freshness_edges.py`).
- Reworked `scripts/secret_scan.ps1` to trim allowlists once, ignore blanks/comments, stream diff-style findings, expose exit legend, and verify behaviour with PowerShell integration tests (`tests/unit/test_secret_scan_script.py`); allowlist now captures legacy doc artefacts.
- Exercised Redis backend and deterministic access fallbacks without external services (`tests/unit/test_cache_backends.py`, `tests/unit/test_access_api.py`).

Checklist
---------
- Compression envelope, hit/miss counters, invalidate path, and TTL=0 semantics all covered by new unit tests.
- Catalog gracefully handles missing/invalid YAML and directory collisions without exceptions.
- Freshness verifier now exercises ISO strings, invalid dates, numeric and string year derivations, and sentinel values.
- Secret scanner reads allowlist once, skips comments/blank lines, emits diff previews on failure, and documents exit codes.
- `pytest.ini`/`pyproject.toml` enforce branch coverage targeting `src/qnwis/data`; no tests rely on wall-clock time.

Coverage
--------
Command: `python -m pytest --ignore=tests/optional_mcp`

```
Name                                           Stmts   Miss Branch BrPart  Cover
--------------------------------------------------------------------------------
TOTAL                                            626     43    228     37     90%
```

Secret Scan
-----------
```
Secret scan: CLEAN
```
