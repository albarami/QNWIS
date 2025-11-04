# Step 2 Review – Deterministic Data Layer Hardening

## Summary
- Hardened the CSV catalog connector with parameter validation, timeout limits, and optional percent scaling while keeping provenance licenses explicit.
- Tightened the World Bank deterministic connector with country validation, optional row/timeout limits, and consistent licensing metadata.
- Added docstrings and stronger typing across deterministic helpers and audit logging to keep `mypy --strict` coverage green.
- Expanded unit coverage for new behaviours (CSV limits, percent conversion, World Bank parameter validation) without unquarantining the MCP suites.

## Key Changes
- **src/qnwis/data/connectors/csv_catalog.py**  
  Rebuilt around structured parameter parsing (`CsvQueryParams`), row transformation helpers, and robust casting handling blanks/thousand separators. Enforces `max_rows`, `timeout_s`, `to_percent`, and raises clear errors for missing files or empty result sets. Added Qatar Open Data license to provenance.
- **src/qnwis/data/connectors/world_bank_det.py**  
  Validates indicator/countries, supports optional `timeout_s`/`max_rows`, and propagates `World Bank Open Data (CC BY 4.0)` licensing. Raises on empty data and keeps helper validation pure-typed.
- **src/data/apis/world_bank.py**  
  Honours per-request timeout overrides and row caps with stricter parameter guards (`client_timeout`, `max_rows`). Minor guard on `_client()` to enforce positive timeouts.
- **Deterministic layer utilities**  
  Added docstrings/typing to `access.execute`, `registry.QueryRegistry`, `number_verifier.verify_result`, and `FileAuditLog`. Registry now uses `Path.glob` with JSON-safe loading and duplicates detection.
- **Tests**  
  New/updated unit coverage in `tests/unit/test_csv_catalog.py`, `test_world_bank_connector.py`, `test_access_api.py`, and `test_registry.py`. Optional MCP suites adjusted for new timeout expectations; core MCP tests remain quarantined (not invoked).

## Validation Commands
- `ruff check` – **pass**
- `flake8` – **pass**
- `mypy src --strict` – **pass**
- `pytest tests/unit -q` – **pass** (MCP suites remain quarantined)

## Notes
- Optional MCP tests (`tests/optional_mcp/...`) were not executed per quarantine requirement but were updated to reflect new git timeout behaviour.
