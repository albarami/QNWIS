from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ....data.apis.world_bank import UDCGlobalDataIntegrator  # type: ignore[import-not-found]
from ..deterministic.models import Freshness, Provenance, QueryResult, QuerySpec, Row

GCC_DEFAULT_COUNTRIES = ["QAT", "SAU", "ARE", "KWT", "BHR", "OMN"]
WORLD_BANK_LICENSE = "World Bank Open Data (CC BY 4.0)"


def _validate_countries(value: Any) -> list[str]:
    """Validate the countries parameter ensuring ISO-3 codes."""
    if value is None:
        return list(GCC_DEFAULT_COUNTRIES)
    if isinstance(value, str) or not isinstance(value, Iterable):
        raise ValueError("'countries' must be an iterable of ISO-3 codes.")
    normalized: list[str] = []
    for code in value:
        if not isinstance(code, str) or len(code.strip()) != 3:
            raise ValueError(f"Invalid ISO-3 code in 'countries': {code!r}")
        normalized.append(code.strip().upper())
    if not normalized:
        raise ValueError("'countries' must contain at least one ISO-3 code.")
    return normalized


def _validate_positive_number(value: Any, name: str) -> float:
    """Validate a positive numeric parameter and return it as float."""
    if isinstance(value, bool):
        raise ValueError(f"'{name}' must be a positive number.")
    if not isinstance(value, (int, float)):
        raise ValueError(f"'{name}' must be a positive number.")
    numeric = float(value)
    if numeric <= 0:
        raise ValueError(f"'{name}' must be a positive number.")
    return numeric


def _validate_positive_int(value: Any, name: str) -> int:
    """Validate a positive integer parameter."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"'{name}' must be a positive integer.")
    if value <= 0:
        raise ValueError(f"'{name}' must be a positive integer.")
    return int(value)


def run_world_bank_query(spec: QuerySpec) -> QueryResult:
    """
    Execute a deterministic World Bank query via the shared API integrator.

    Required params:
        indicator (str): World Bank indicator code.

    Optional params:
        countries (Iterable[str]): ISO-3 country codes (default GCC set).
        year / start_year / end_year: Passed through to the API client.
        timeout_s (float): Maximum seconds per API request (default 30).
        max_rows (int): Maximum rows to include in the result set (default 10000).
    """
    params = spec.params or {}
    indicator = params.get("indicator")
    if not isinstance(indicator, str) or not indicator.strip():
        raise ValueError("World Bank query requires a non-empty 'indicator' parameter.")
    indicator_code = indicator.strip()

    countries = _validate_countries(params.get("countries"))

    # Default timeout_s to 30 if not provided
    timeout_s = 30.0
    if "timeout_s" in params:
        timeout_s = _validate_positive_number(params["timeout_s"], "timeout_s")

    # Default max_rows to 10000 if not provided
    max_rows = 10000
    if "max_rows" in params:
        max_rows = _validate_positive_int(params["max_rows"], "max_rows")

    integ = UDCGlobalDataIntegrator()
    dataframe = integ.get_indicator(
        indicator=indicator_code,
        countries=countries,
        year=params.get("year"),
        start_year=params.get("start_year"),
        end_year=params.get("end_year"),
        timeout_s=timeout_s,
        max_rows=max_rows,
    )

    if dataframe.empty:
        raise ValueError(
            f"World Bank query returned no data for indicator '{indicator_code}' "
            f"with countries {countries}"
        )

    records = dataframe.to_dict(orient="records")
    rows: list[Row] = [Row(data=record) for record in records]

    return QueryResult(
        query_id=spec.id,
        rows=rows,
        unit=spec.expected_unit,
        provenance=Provenance(
            source="world_bank",
            dataset_id=indicator_code,
            locator=f"indicator={indicator_code}",
            fields=list(dataframe.columns),
            license=WORLD_BANK_LICENSE,
        ),
        freshness=Freshness(asof_date="api", updated_at=None),
    )
