# Transforms Catalog

**Post-processing transforms for deterministic data layer queries.**

All transforms are **pure functions** that operate on `List[Dict[str, Any]]` and return modified copies. No side effects, no I/O, deterministic behavior only.

Transforms can be chained in YAML query definitions via the `postprocess` field.

---

## Composing Transforms

These end-to-end examples show how to combine multiple steps inside a query definition.

### Example 1 — Sector Leaderboard

```yaml
postprocess:
  - name: filter_equals
    params:
      where:
        year: 2024
  - name: top_n
    params:
      sort_key: employees
      n: 3
  - name: select
    params:
      columns: ["sector", "employees"]
```

**Expected rows schema**
- `sector`: str — sector identifier
- `employees`: float — headcount after filtering and sorting

### Example 2 — Market Share Snapshot

```yaml
postprocess:
  - name: share_of_total
    params:
      group_keys: ["year"]
      value_key: "employment"
      out_key: "employment_share_pct"
  - name: select
    params:
      columns: ["year", "sector", "employment_share_pct"]
```

**Expected rows schema**
- `year`: int — reporting year
- `sector`: str — sector label
- `employment_share_pct`: float — percent share of employment within the year group

### Example 3 — Rolling Trend With YoY

```yaml
postprocess:
  - name: rolling_avg
    params:
      key: "value"
      sort_keys: ["year"]
      window: 4
      out_key: "rolling_avg_value"
  - name: yoy
    params:
      key: "value"
      sort_keys: ["year"]
      out_key: "value_yoy_pct"
```

**Expected rows schema**
- `year`: int — sorted chronological key
- `value`: float — original metric
- `rolling_avg_value`: float | null — trailing 4-period mean
- `value_yoy_pct`: float | null — year-over-year percent change

## Available Transforms

### 1. `select`

**Select a subset of columns from each row.**

**Parameters:**
- `columns` (list[str]): Column names to keep

**Behavior:**
- Returns rows with only specified columns
- Missing columns become `None`
- Order of columns in output follows `columns` parameter

**Example:**

```yaml
postprocess:
  - name: select
    params:
      columns: ["year", "sector", "employees"]
```

**Input:**
```python
[
  {"year": 2024, "sector": "Energy", "employees": 100, "extra": "x"},
  {"year": 2024, "sector": "Finance", "employees": 200, "extra": "y"}
]
```

**Output:**
```python
[
  {"year": 2024, "sector": "Energy", "employees": 100},
  {"year": 2024, "sector": "Finance", "employees": 200}
]
```

---

### 2. `filter_equals`

**Filter rows where all specified columns equal given values.**

**Parameters:**
- `where` (dict): Dictionary of `column_name: expected_value` conditions

**Behavior:**
- Returns only rows matching ALL conditions
- Uses equality comparison (`==`)
- Empty `where` dict returns all rows

**Example:**

```yaml
postprocess:
  - name: filter_equals
    params:
      where:
        sector: "Energy"
        year: 2024
```

**Input:**
```python
[
  {"year": 2023, "sector": "Energy", "value": 100},
  {"year": 2024, "sector": "Energy", "value": 110},
  {"year": 2024, "sector": "Finance", "value": 200}
]
```

**Output:**
```python
[
  {"year": 2024, "sector": "Energy", "value": 110}
]
```

---

### 3. `rename_columns`

**Rename columns according to mapping.**

**Parameters:**
- `mapping` (dict[str, str]): Dictionary of `old_name: new_name`

**Behavior:**
- Renames columns specified in mapping
- Unmapped columns keep original names
- If multiple old names map to same new name, last wins

**Example:**

```yaml
postprocess:
  - name: rename_columns
    params:
      mapping:
        employees: "total_employees"
        avg_salary: "mean_salary_qar"
```

**Input:**
```python
[
  {"sector": "Energy", "employees": 100, "avg_salary": 15000}
]
```

**Output:**
```python
[
  {"sector": "Energy", "total_employees": 100, "mean_salary_qar": 15000}
]
```

---

### 4. `to_percent`

**Convert numeric columns to percentages by multiplying by scale.**

**Parameters:**
- `columns` (list[str]): Column names to convert
- `scale` (float, default=100.0): Multiplier to apply

**Behavior:**
- Multiplies numeric values by `scale`
- Non-numeric values unchanged
- Missing columns ignored

**Example:**

```yaml
postprocess:
  - name: to_percent
    params:
      columns: ["ratio"]
      scale: 100.0
```

**Input:**
```python
[
  {"sector": "Energy", "ratio": 0.15, "count": 100},
  {"sector": "Finance", "ratio": 0.85, "count": 200}
]
```

**Output:**
```python
[
  {"sector": "Energy", "ratio": 15.0, "count": 100},
  {"sector": "Finance", "ratio": 85.0, "count": 200}
]
```

---

### 5. `top_n`

**Return top N rows sorted by specified key.**

**Parameters:**
- `sort_key` (str): Column name to sort by
- `n` (int): Number of rows to return
- `descending` (bool, default=True): Sort order

**Behavior:**
- Sorts rows by `sort_key`
- Returns first `n` rows after sorting
- Missing `sort_key` treated as `0`
- Negative `n` returns empty list

**Example:**

```yaml
postprocess:
  - name: top_n
    params:
      sort_key: "employees"
      n: 5
      descending: true
```

**Input:**
```python
[
  {"sector": "Energy", "employees": 100},
  {"sector": "Finance", "employees": 300},
  {"sector": "ICT", "employees": 200}
]
```

**Output:**
```python
[
  {"sector": "Finance", "employees": 300},
  {"sector": "ICT", "employees": 200},
  {"sector": "Energy", "employees": 100}
]
```

---

### 6. `share_of_total`

**Compute share of total within groups as percentage.**

**Parameters:**
- `group_keys` (list[str]): Columns defining groups (empty list = single group)
- `value_key` (str): Numeric column to compute share of
- `out_key` (str, default="share_percent"): Output column name

**Behavior:**
- Groups rows by `group_keys`
- Computes `100 * value / sum(value in group)` for each row
- Adds `out_key` column with percentage
- Division by zero yields `0.0`

**Example:**

```yaml
postprocess:
  - name: share_of_total
    params:
      group_keys: ["year"]
      value_key: "employees"
      out_key: "share_percent"
```

**Input:**
```python
[
  {"year": 2024, "sector": "Energy", "employees": 100},
  {"year": 2024, "sector": "Finance", "employees": 300}
]
```

**Output:**
```python
[
  {"year": 2024, "sector": "Energy", "employees": 100, "share_percent": 25.0},
  {"year": 2024, "sector": "Finance", "employees": 300, "share_percent": 75.0}
]
```

---

### 7. `yoy`

**Compute year-over-year percentage change.**

**Parameters:**
- `key` (str): Numeric column to compute YoY for
- `sort_keys` (list[str]): Columns to sort by (typically `["year"]`)
- `out_key` (str, default="yoy_percent"): Output column name

**Behavior:**
- Sorts rows by `sort_keys`
- Computes `(current - previous) / previous * 100`
- First row gets `None`
- Missing/non-numeric values yield `None`
- Division by zero yields `None`
- Rounds to 2 decimal places

**Example:**

```yaml
postprocess:
  - name: yoy
    params:
      key: "employees"
      sort_keys: ["year"]
      out_key: "yoy_percent"
```

**Input:**
```python
[
  {"year": 2022, "employees": 100},
  {"year": 2023, "employees": 110},
  {"year": 2024, "employees": 121}
]
```

**Output:**
```python
[
  {"year": 2022, "employees": 100, "yoy_percent": None},
  {"year": 2023, "employees": 110, "yoy_percent": 10.0},
  {"year": 2024, "employees": 121, "yoy_percent": 10.0}
]
```

---

### 8. `rolling_avg`

**Compute rolling average over specified window.**

**Parameters:**
- `key` (str): Numeric column to average
- `sort_keys` (list[str]): Columns to sort by
- `window` (int, default=3): Window size
- `out_key` (str, default="rolling_avg"): Output column name

**Behavior:**
- Sorts rows by `sort_keys`
- Computes mean of last N values (where N = `window`)
- Returns `None` until window is filled
- Non-numeric values skipped
- Rounds to 2 decimal places

**Example:**

```yaml
postprocess:
  - name: rolling_avg
    params:
      key: "employees"
      sort_keys: ["year"]
      window: 3
      out_key: "rolling_avg"
```

**Input:**
```python
[
  {"year": 2020, "employees": 100},
  {"year": 2021, "employees": 110},
  {"year": 2022, "employees": 120},
  {"year": 2023, "employees": 130}
]
```

**Output:**
```python
[
  {"year": 2020, "employees": 100, "rolling_avg": None},
  {"year": 2021, "employees": 110, "rolling_avg": None},
  {"year": 2022, "employees": 120, "rolling_avg": 110.0},  # mean(100,110,120)
  {"year": 2023, "employees": 130, "rolling_avg": 120.0}   # mean(110,120,130)
]
```

---

## Pipeline Composition

Transforms can be chained in YAML query definitions. They execute **in order**, with each transform receiving the output of the previous one.

### Example: Multi-step Pipeline

```yaml
id: example_pipeline
title: Energy sector YoY growth with top 3 years
source: csv
params:
  pattern: "aggregates/sector_employment_by_year.csv"
postprocess:
  # Step 1: Filter to Energy sector only
  - name: filter_equals
    params:
      where:
        sector: "Energy"
  
  # Step 2: Compute year-over-year growth
  - name: yoy
    params:
      key: "employees"
      sort_keys: ["year"]
      out_key: "yoy_percent"
  
  # Step 3: Select relevant columns
  - name: select
    params:
      columns: ["year", "employees", "yoy_percent"]
  
  # Step 4: Get top 3 years by YoY growth
  - name: top_n
    params:
      sort_key: "yoy_percent"
      n: 3
      descending: true
```

### Execution Order

Transforms execute **left-to-right** (top-to-bottom in YAML):

1. `filter_equals` reduces rows to Energy sector
2. `yoy` adds `yoy_percent` column to remaining rows
3. `select` removes unwanted columns
4. `top_n` returns 3 rows with highest YoY growth

**Critical:** Later transforms operate on the output of earlier transforms. Order matters!

---

## Design Principles

### 1. Purity
- No side effects
- Same input → same output
- No I/O, no network, no database

### 2. Immutability
- Transforms return **new** lists/dicts
- Original data never modified
- Safe for caching and parallelization

### 3. Composability
- Transforms can be chained freely
- Output of one is input to next
- Small, focused functions

### 4. Determinism
- No randomness
- No timestamps
- Reproducible results

### 5. Type Safety
- All transforms type-hinted
- Pydantic validation for parameters
- Graceful handling of missing/invalid data

---

## Usage in Queries

### YAML Structure

```yaml
id: query_id
title: Query Title
source: csv
params:
  # ... connector params ...
postprocess:
  - name: transform_name
    params:
      param1: value1
      param2: value2
  - name: another_transform
    params:
      param3: value3
```

### API Override

You can override postprocess at runtime via `spec_override`:

```python
from src.qnwis.data.deterministic.models import QuerySpec, TransformStep

spec = registry.get("base_query_id")
spec_override = spec.model_copy(deep=True)
spec_override.postprocess = [
    TransformStep(name="filter_equals", params={"where": {"year": 2024}}),
    TransformStep(name="top_n", params={"sort_key": "value", "n": 10}),
]

result = execute_cached("base_query_id", registry, spec_override=spec_override)
```

**Note:** Different `postprocess` steps generate different cache keys, so each pipeline variant is cached separately.

---

## Performance Considerations

### Memory
- Transforms operate on full result set in memory
- Large datasets (>100K rows) may be slow
- Consider filtering early in pipeline

### Caching
- Postprocess included in cache key
- Each pipeline variant cached separately
- Cache hit requires exact match of all steps + params

### Optimization Tips

1. **Filter first:** Use `filter_equals` early to reduce row count
2. **Select late:** Use `select` near end to keep needed columns during intermediate steps
3. **Avoid redundant sorts:** `top_n`, `yoy`, `rolling_avg` all sort internally
4. **Group efficiently:** Minimize cardinality of `group_keys` in `share_of_total`

---

## Error Handling

### Unknown Transform
```python
KeyError: "Unknown transform: invalid_name"
```

### Invalid Parameters
```python
TypeError: missing required parameter 'sort_key'
ValidationError: 'n' must be integer
```

### Data Errors
- Missing columns: treated as `None` or `0`
- Non-numeric values: skipped in numeric transforms
- Division by zero: returns `None` or `0.0`

---

## Testing

All transforms have comprehensive unit tests in `tests/unit/test_transforms_base.py`.

Integration tests in `tests/integration/test_queries_with_transforms.py` verify end-to-end execution with synthetic data.

Run tests:
```bash
pytest tests/unit/test_transforms_base.py -v
pytest tests/unit/test_postprocess_pipeline.py -v
pytest tests/integration/test_queries_with_transforms.py -v
```

### Trace Instrumentation

Set `QNWIS_TRANSFORM_TRACE=1` before executing a query to append `transform:<step-name>` entries to the `QueryResult.warnings` list. This is useful when debugging complex pipelines; row data is left untouched.

---

## Extension

To add a new transform:

1. **Define function** in `src/qnwis/data/transforms/base.py`
2. **Register** in `src/qnwis/data/transforms/catalog.py`
3. **Add tests** in `tests/unit/test_transforms_base.py`
4. **Document** in this file

Example:

```python
# base.py
def filter_gt(rows: List[Dict[str, Any]], column: str, threshold: float) -> List[Dict[str, Any]]:
    """Filter rows where column > threshold."""
    return [r for r in rows if r.get(column, 0) > threshold]

# catalog.py
CATALOG = {
    # ... existing ...
    "filter_gt": base.filter_gt,
}
```

---

## See Also

- [Data API v2 Documentation](./data_api_v2.md) — API endpoints using transforms
- [Implementation Roadmap](./IMPLEMENTATION_ROADMAP.md) — DDL architecture
- [Query Registry](../src/qnwis/data/deterministic/registry.py) — Query loading
- [Postprocess Pipeline](../src/qnwis/data/deterministic/postprocess.py) — Execution logic
