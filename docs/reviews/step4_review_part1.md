# Step 4 Review: Deterministic Data Layer V2 Hardening (Part 1)

**Review Date:** 2024-11-05  
**Reviewer:** Cascade AI (Automated Review + User Enhancements)  
**Status:** ✅ **APPROVED FOR PRODUCTION**

---

## Executive Summary

Step 4 implementation has been comprehensively hardened with improved type safety, robust error handling, enhanced test coverage, and production-ready features. All checklist items have been satisfied, and three enhancements have been successfully integrated.

**Test Results:** 64/64 tests passing (100%)  
**Coverage:** 65% overall, 97% for normalize.py, 83% for metrics.py  
**New Features:** GET query spec endpoint, X-Request-ID echo, optional rate limiting

---

## Checklist Review

### ✅ 1. Type Hints and Docstrings

**Status:** COMPLETE

All public functions now have comprehensive type hints and Google-style docstrings.

**Key Changes:**
- Replaced `Optional` with `| None` syntax (PEP 604)
- Added type hints to all utility functions
- Enhanced docstrings with Args, Returns, Raises sections

**Example:**
```python
def _coerce_ttl(value: Any) -> int | None:
    """
    Coerce a user-provided TTL value into API bounds.
    
    Args:
        value: Raw TTL input (query param or JSON payload)
    
    Returns:
        Integer TTL within [MIN_TTL_S, MAX_TTL_S], or None if invalid/absent.
    """
```

**Files Affected:**
- `src/qnwis/api/models.py`
- `src/qnwis/api/routers/queries.py`
- `src/qnwis/data/deterministic/normalize.py`
- `src/qnwis/data/derived/metrics.py`
- `src/qnwis/utils/*.py`

---

### ✅ 2. normalize_rows Idempotent and Safe

**Status:** COMPLETE

`normalize_rows()` now handles heterogeneous inputs and is fully idempotent.

**Implementation:**
```python
def _extract_row_payload(row: Any) -> Mapping[str, Any] | None:
    """Return the underlying data mapping for a heterogeneous row input."""
    if isinstance(row, Row):
        return row.data
    if isinstance(row, Mapping):
        data = row.get("data")
        if isinstance(data, Mapping):
            return data
        if "data" in row:
            return {}  # Malformed shape; return empty payload instead of raising
        return row
    return None
```

**Supported Inputs:**
- ✅ Row model instances
- ✅ Plain dictionaries
- ✅ Dictionaries with `{"data": {...}}` wrapper
- ✅ Mixed lists of the above
- ✅ Non-mapping inputs (returns empty dict, no crash)

**Tests:**
```python
def test_normalize_rows_idempotent() -> None:
    rows = [{"data": {"Name": "Qatar", "Value": " 10 "}}]
    first = normalize_rows(rows)
    second = normalize_rows(first)
    assert first == second  # ✅ PASSES

def test_normalize_rows_non_mapping_input() -> None:
    out = normalize_rows([{"data": {"Name": "Qatar"}}, 42])
    assert out[0]["data"]["name"] == "Qatar"
    assert out[1]["data"] == {}  # ✅ Graceful
```

---

### ✅ 3. Derived Metrics Handle Missing/Null/NaN

**Status:** COMPLETE

All derived metric functions now gracefully handle edge cases without exceptions.

**Key Helpers:**
```python
def _val(x: Any) -> float | None:
    """Safely extract numeric value from any type."""
    try:
        f = float(x)
        if f != f or isnan(f):  # NaN check
            return None
        return f
    except Exception:
        return None

def _safe_int(value: Any) -> int | None:
    """Safely coerce a value to int, returning None if conversion fails."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(str(value).strip()))
    except Exception:
        return None
```

**Test Coverage:**
```python
def test_share_of_total_non_numeric_values() -> None:
    rows = [
        {"data": {"year": 2023, "v": "n/a"}},
        {"data": {"year": 2023, "v": None}},
        {"data": {"year": 2023, "v": "50"}},
    ]
    out = share_of_total(rows, value_key="v", group_key="year")
    assert out[0]["data"]["share_percent"] is None  # ✅
    assert out[1]["data"]["share_percent"] is None  # ✅
    assert out[2]["data"]["share_percent"] == 100.0  # ✅
```

---

### ✅ 4. TTL Enforcement (60–86400)

**Status:** COMPLETE

**Implementation:**
```python
MIN_TTL_S = 60
MAX_TTL_S = 86400
DEFAULT_TTL_S = 300

def _coerce_ttl(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        ttl = int(float(str(value).strip()))
    except Exception:
        return None
    ttl = max(MIN_TTL_S, ttl)
    ttl = min(MAX_TTL_S, ttl)
    return ttl
```

**Test Verification:**
```python
def test_run_query_ttl_bounds(test_env, monkeypatch):
    captured: list[int] = []
    # ... monkeypatch execute_cached to capture TTL ...
    
    c.post("/v1/queries/q_demo/run", json={"ttl_s": 30})      # → 60
    c.post("/v1/queries/q_demo/run", json={"ttl_s": 100000})  # → 86400
    c.post("/v1/queries/q_demo/run", json={"ttl_s": 300})     # → 300
    
    assert captured == [60, 86400, 300]  # ✅ VERIFIED
```

---

### ✅ 5. Override Whitelist Enforced

**Status:** COMPLETE

```python
allowed = {"year", "timeout_s", "max_rows", "to_percent"}

overrides_raw = payload.get("override_params", {})
if overrides_raw and not isinstance(overrides_raw, dict):
    raise HTTPException(
        status_code=400,
        detail="'override_params' must be an object mapping."
    )

overrides = normalize_params({k: v for k, v in overrides_raw.items() if k in allowed})
```

**Tests:**
```python
def test_run_query_invalid_override_type(test_env):
    r = c.post("/v1/queries/q_demo/run", json={"override_params": ["bad"]})
    assert r.status_code == 400
    assert "must be an object mapping" in r.json()["detail"]

def test_run_query_whitelisted_params(test_env):
    # Whitelisted → accepted
    r = c.post("/v1/queries/q_demo/run", json={
        "override_params": {"year": 2023, "timeout_s": 10}
    })
    assert r.status_code == 200
    
    # Non-whitelisted → silently ignored
    r = c.post("/v1/queries/q_demo/run", json={
        "override_params": {"malicious_param": "value"}
    })
    assert r.status_code == 200  # No error
```

---

### ✅ 6. Endpoints: Clear 404, No Stack Traces

**Status:** COMPLETE

```python
try:
    spec = reg.get(query_id)
except KeyError:
    raise HTTPException(status_code=404, detail="Unknown query_id") from None

try:
    res = execute_cached(query_id, reg, ttl_s=ttl_for_execution)
except TimeoutError as exc:
    log.warning("Query %s timed out: %s", query_id, exc)
    raise HTTPException(status_code=504, detail="Query execution timed out.") from None
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from None
except FileNotFoundError:
    raise HTTPException(status_code=404, detail="Query source data not found.") from None
except Exception:
    log.exception("Unexpected failure executing query %s", query_id)
    raise HTTPException(status_code=500, detail="Query execution failed.") from None
```

**Tests:**
```python
def test_run_query_unknown_id(test_env):
    r = c.post("/v1/queries/nonexistent/run", json={})
    assert r.status_code == 404
    assert "Unknown query_id" in r.json()["detail"]
```

---

### ✅ 7. Test Coverage Enhancements

**Status:** COMPLETE

Test suite expanded from 55 to 64 tests.

**New Tests:**
- `test_normalize_rows_row_model`
- `test_normalize_rows_idempotent`
- `test_normalize_rows_non_mapping_input`
- `test_share_of_total_non_numeric_values`
- `test_yoy_growth_non_numeric_values`
- `test_list_queries_empty`
- `test_run_query_invalid_override_type`
- `test_get_query_spec`
- `test_get_query_spec_unknown`

**Results:**
```
=================== 64 passed in 4.89s ===================
Coverage: normalize.py 97%, metrics.py 83%, overall 65%
```

---

### ✅ 8. FastAPI TestClient Passes on Windows

**Status:** COMPLETE

All tests pass on Windows with proper Path handling:

```python
roots: list[Path] = []
env_root = os.getenv("QNWIS_QUERIES_DIR")
if env_root:
    roots.append(Path(env_root))
roots.extend([
    Path("src") / "qnwis" / "data" / "queries",
    Path("data") / "queries",
])
```

**Verified:** `platform win32 -- Python 3.11.8, pytest-8.4.2`

---

**Continue to Part 2 for Enhancements Review...**
