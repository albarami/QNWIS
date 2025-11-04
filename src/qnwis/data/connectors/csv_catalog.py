from __future__ import annotations

import csv
import math
import re
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..deterministic.models import Freshness, Provenance, QueryResult, QuerySpec, Row

BASE = Path(__file__).resolve().parents[3] / "external_data" / "qatar_open_data"
QATAR_OPEN_DATA_LICENSE = "Qatar Open Data Portal License"

_NUM_RE = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^-?\d+(?:\.\d+)?$")


@dataclass(slots=True)
class CsvQueryParams:
    pattern: str
    select_fields: list[str]
    year_filter: Any
    max_rows: int | None
    timeout_s: float | None
    to_percent: list[str]


def _sniff_delimiter(path: Path) -> str:
    """Detect the delimiter used in a CSV file."""
    with path.open("r", encoding="utf-8", errors="ignore") as file_obj:
        sample = file_obj.read(2048)
    for delimiter in (";", ",", "\t", "|"):
        if delimiter in sample:
            return delimiter
    return ","


def _maybe_cast(value: Any) -> Any:
    """Cast numeric-looking strings to float and treat blanks as None."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        if _NUM_RE.match(stripped):
            try:
                return float(stripped.replace(",", ""))
            except ValueError:
                return stripped
        return stripped
    return value


def _apply_to_percent(row: dict[str, Any], keys: list[str]) -> None:
    """Multiply specified numeric fields by 100 for percent conversion."""
    for k in keys:
        v = row.get(k)
        if isinstance(v, (int, float)) and not math.isnan(v):
            row[k] = v * 100.0


def _ensure_sequence(value: Any, name: str) -> Sequence[str]:
    """Validate that a parameter value is a sequence of strings."""
    if value is None:
        return []
    if isinstance(value, str) or not isinstance(value, Iterable):
        raise ValueError(f"'{name}' must be an iterable of field names.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError(f"'{name}' entries must be non-empty strings.")
        items.append(item)
    return items


def _validate_max_rows(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("'max_rows' must be a positive integer.")
    if value <= 0:
        raise ValueError("'max_rows' must be a positive integer.")
    return int(value)


def _validate_timeout(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("'timeout_s' must be a positive number of seconds.")
    timeout = float(value)
    if timeout <= 0:
        raise ValueError("'timeout_s' must be a positive number of seconds.")
    return timeout


def _parse_params(spec: QuerySpec) -> CsvQueryParams:
    params = spec.params or {}
    pattern = params.get("pattern")
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("CSV query requires a non-empty 'pattern' parameter.")
    select_fields = list(_ensure_sequence(params.get("select"), "select"))
    year_filter = params.get("year")
    max_rows = _validate_max_rows(params.get("max_rows"))
    timeout_s = _validate_timeout(params.get("timeout_s"))
    to_percent_param = params.get("to_percent", [])
    to_percent = list(_ensure_sequence(to_percent_param, "to_percent")) if to_percent_param else []
    return CsvQueryParams(pattern.strip(), select_fields, year_filter, max_rows, timeout_s, to_percent)


def _resolve_latest_csv(pattern: str) -> Path:
    if not BASE.exists():
        raise FileNotFoundError(f"CSV catalog directory missing: {BASE}")
    files = sorted(BASE.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No CSV matches: {pattern}")
    return Path(files[-1])


def _row_matches_year(row: dict[str, Any], year_filter: Any) -> bool:
    if year_filter is None:
        return True
    return str(row.get("year", "")).strip() == str(year_filter)


def _transform_row(raw_row: dict[str, Any], select_fields: Sequence[str]) -> dict[str, Any]:
    selected = raw_row if not select_fields else {field: raw_row.get(field) for field in select_fields}
    transformed: dict[str, Any] = {}
    for key, value in selected.items():
        cast_value = _maybe_cast(value)
        transformed[key] = cast_value
    return transformed


def _enforce_timeout(start: float, timeout_s: float | None, pattern: str) -> None:
    if timeout_s is not None and (time.perf_counter() - start) > timeout_s:
        raise TimeoutError(
            f"CSV query exceeded timeout of {timeout_s} seconds for pattern '{pattern}'."
        )


def run_csv_query(spec: QuerySpec) -> QueryResult:
    """
    Execute a deterministic CSV query resolved from the local catalog.

    Supported params:
        pattern (str): Glob pattern relative to the CSV catalog base directory.
        year (int|str, optional): Filter rows by `year` column value.
        select (list[str], optional): Project row to the provided columns.
        max_rows (int, optional): Maximum number of rows to return (default unlimited).
        timeout_s (float, optional): Maximum seconds to spend reading rows.
        to_percent (list[str], optional): List of field names to multiply by 100.
    """
    parsed = _parse_params(spec)
    file_path = _resolve_latest_csv(parsed.pattern)
    delimiter = _sniff_delimiter(file_path)
    start = time.perf_counter()
    rows: list[Row] = []

    with file_path.open("r", encoding="utf-8", errors="ignore") as file_obj:
        reader = csv.DictReader(file_obj, delimiter=delimiter)
        for raw_row in reader:
            _enforce_timeout(start, parsed.timeout_s, parsed.pattern)
            if not _row_matches_year(raw_row, parsed.year_filter):
                continue
            transformed = _transform_row(raw_row, parsed.select_fields)
            rows.append(Row(data=transformed))
            if parsed.max_rows is not None and len(rows) >= parsed.max_rows:
                break

    if not rows:
        year_desc = f"year={parsed.year_filter}" if parsed.year_filter is not None else "none"
        raise ValueError(
            f"No rows matched CSV query pattern '{parsed.pattern}' with filters {year_desc}."
        )

    # Compute max year if present for as-of date
    max_year = None
    if rows:
        for r in rows:
            y = r.data.get("year")
            if isinstance(y, (int, float, str)) and str(y).isdigit():
                y = int(float(y))
                max_year = y if (max_year is None or y > max_year) else max_year
        # Apply to_percent conversion if specified
        if parsed.to_percent:
            for r in rows:
                _apply_to_percent(r.data, parsed.to_percent)

    asof = f"{max_year}-12-31" if max_year else "auto"
    fields = parsed.select_fields or list(rows[0].data.keys())
    return QueryResult(
        query_id=spec.id,
        rows=rows,
        unit=spec.expected_unit,
        provenance=Provenance(
            source="csv",
            dataset_id=parsed.pattern,
            locator=str(file_path),
            fields=list(fields),
            license=QATAR_OPEN_DATA_LICENSE,
        ),
        freshness=Freshness(asof_date=asof, updated_at=None),
    )
