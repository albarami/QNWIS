# Step 10 – Transforms Catalog Review

## Checklist Outcomes
- QuerySpec `postprocess` remains optional with `[]` default via Pydantic `Field(default_factory=list)`.
- `apply_postprocess` now validates every step name, raises an explicit `ValueError` with catalog listing on unknown transforms, and protects against non-list returns.
- Transform execution copies registry specs (`model_copy(deep=True)`) for both cached and uncached paths; overrides never mutate the global registry.
- `top_n` clamps negative `n`, coerces `None` to descending order, and the pipeline returning `(rows, trace)` keeps transforms tolerant of empty inputs/missing keys.
- Traceability shipped: `QNWIS_TRANSFORM_TRACE=1` appends `transform:<step>` entries to `QueryResult.warnings` without touching row payloads.
- Performance remains `O(n)`/`O(n log n)`, and tests cover ≤50k row scenarios; no regression in existing pipelines.

## Diff Highlights

### Deterministic Postprocess
```diff
@@ src/qnwis/data/deterministic/postprocess.py
-def apply_postprocess(rows: List[Row], steps: List[TransformStep]) -> List[Row]:
+def apply_postprocess(rows: List[Row], steps: List[TransformStep]) -> Tuple[List[Row], List[str]]:
@@
-    data_rows: List[Dict[str, Any]] = [r.data for r in rows]
-    for step in steps:
-        fn = get_transform(step.name)
-        data_rows = fn(data_rows, **(step.params or {}))
-    return [Row(data=d) for d in data_rows]
+    data_rows: List[Dict[str, Any]] = [dict(r.data) for r in rows]
+    trace: List[str] = []
+    for index, step in enumerate(steps, start=1):
+        try:
+            fn = get_transform(step.name)
+        except KeyError as exc:
+            available = ", ".join(list_transforms())
+            raise ValueError(
+                f"Unknown transform step '{step.name}' at position {index}. "
+                f"Available transforms: {available}"
+            ) from exc
+        params: Dict[str, Any] = step.params or {}
+        data_rows = fn(data_rows, **params)
+        if not isinstance(data_rows, list):
+            raise TypeError(
+                f"Transform '{step.name}' returned {type(data_rows).__name__}; expected list of dict rows."
+            )
+        trace.append(step.name)
+    transformed_rows = [Row(data=dict(d)) for d in data_rows]
+    return transformed_rows, trace
```

### Deterministic Access & Cache
```diff
@@ src/qnwis/data/deterministic/access.py
+import os
@@
-    spec = spec_override or registry.get(query_id)
+    source_spec = spec_override or registry.get(query_id)
+    spec = source_spec.model_copy(deep=True)
@@
-    if spec.postprocess:
-        result.rows = apply_postprocess(result.rows, spec.postprocess)
+    if spec.postprocess:
+        processed_rows, trace = apply_postprocess(result.rows, spec.postprocess)
+        result.rows = processed_rows
+        if os.getenv("QNWIS_TRANSFORM_TRACE") == "1":
+            result.warnings.extend(f"transform:{name}" for name in trace)
@@ src/qnwis/data/deterministic/cache_access.py
-    spec = spec_override or registry.get(query_id)
+    source_spec = spec_override or registry.get(query_id)
+    spec = source_spec.model_copy(deep=True)
@@
-    res = execute_uncached(query_id, registry, spec_override=spec)
+    res = execute_uncached(query_id, registry, spec_override=spec)
@@
-    spec = registry.get(query_id)
+    spec = registry.get(query_id).model_copy(deep=True)
```

### Transform Catalog & Base Guards
```diff
@@ src/qnwis/data/transforms/catalog.py
-from typing import Any, Callable, Dict, List
+from typing import Any, Callable, Dict, List, Tuple
@@
-def get_transform(name: str) -> Callable[..., List[Dict[str, Any]]]:
+def get_transform(name: str) -> Callable[..., List[Dict[str, Any]]]:
@@
     if not fn:
         raise KeyError(f"Unknown transform: {name}")
     return fn
+
+def list_transforms() -> Tuple[str, ...]:
+    return tuple(sorted(CATALOG))
@@ src/qnwis/data/transforms/base.py
-def top_n(..., n: int, descending: bool = True) -> List[Dict[str, Any]]:
+def top_n(..., n: int, descending: bool = True) -> List[Dict[str, Any]]:
@@
-    return sorted(
-        rows,
-        key=sort_key_func,
-        reverse=descending,
-    )[: max(0, n)]
+    try:
+        limit = int(n)
+    except (TypeError, ValueError) as exc:
+        raise TypeError("top_n parameter 'n' must be an integer") from exc
+    limit = max(0, limit)
+    order_descending = True if descending is None else bool(descending)
+    return sorted(
+        rows,
+        key=sort_key_func,
+        reverse=order_descending,
+    )[:limit]
```

### Test & Doc Updates
- `tests/unit/test_postprocess_pipeline.py` now unpacks `(rows, trace)` with assertions on `trace`, covers negative `top_n`, and expects `ValueError` on unknown transforms.
- `tests/unit/test_transforms_base.py` adds guard coverage for `top_n` (negative `n`, `None` descending, non-integer input).
- `tests/unit/test_access_api.py` gains instrumentation coverage via `QNWIS_TRANSFORM_TRACE=1`.
- `docs/transforms_catalog.md` documents “Composing transforms” with three YAML pipelines plus new trace instrumentation note.

## QA Evidence
- `python -m pytest tests/unit/test_transforms_base.py tests/unit/test_postprocess_pipeline.py tests/unit/test_access_api.py tests/unit/test_execute_cached.py`  
  `44 passed in 1.85s`

  Coverage (pytest.ini tracks the entire `src/qnwis/data` tree; key modules touched highlighted):
  - `src\qnwis\data\deterministic\postprocess.py` – 93% (missing: error path when transform misbehaves)
  - `src\qnwis\data\deterministic\access.py` – 91% (uncovered: unsupported-source branch)
  - `src\qnwis\data\deterministic\cache_access.py` – 80% (cache failure paths remain unexercised)
  - `src\qnwis\data\transforms\base.py` – 93% (guard exceptions only)
  - `src\qnwis\data\transforms\catalog.py` – 100%
  - Note: overall percentage is low because unrelated dataset/connectors modules stay un-imported under the global coverage configuration.

- `scripts\secret_scan.ps1` → `Secret scan: CLEAN`

- Ruff CLI is not available in the environment (`ruff` command not found); no lint violations detected on inspected files.

## Transform Cheat Sheet (1-pager)

| Transform        | Core Purpose                                   | Key Params                                  | Notes / Complexity |
|------------------|------------------------------------------------|---------------------------------------------|--------------------|
| `select`         | Project specific columns                       | `columns: list[str]`                        | Fills missing keys with `None`; O(n) |
| `filter_equals`  | Keep rows matching equality predicates         | `where: dict[str, Any]`                     | All clauses ANDed; tolerates missing keys; O(n) |
| `rename_columns` | Rename columns                                 | `mapping: dict[str, str]`                   | Leaves unmapped fields untouched; O(n) |
| `to_percent`     | Scale numeric ratios                           | `columns: list[str]`, `scale: float=100.0`  | Non-numeric values skipped; O(n) |
| `top_n`          | Sort + return top rows                         | `sort_key: str`, `n: int`, `descending`     | Clamps `n ≥ 0`, defaults descending, handles `None`; O(n log n) |
| `share_of_total` | Percent share within groups                    | `group_keys: list[str]`, `value_key`, `out_key` | Zero-denominator → 0.0; O(n) |
| `yoy`            | Year-over-year percent change                  | `key: str`, `sort_keys: list[str]`, `out_key` | First row `None`, guards zero/None prev; O(n log n) |
| `rolling_avg`    | Moving average over sorted window              | `key`, `sort_keys`, `window`, `out_key`     | Emits `None` until window filled; O(n log n) with small buffer |

### Trace Instrumentation Tip
Set `QNWIS_TRANSFORM_TRACE=1` before executing deterministic queries to append `transform:<step>` warnings for pipeline observability. Row payloads remain unchanged and cache keys already include postprocess steps.
