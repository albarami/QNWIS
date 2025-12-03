from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.data.apis.world_bank import UDCGlobalDataIntegrator  # type: ignore[import-not-found]
else:
    try:
        from src.data.apis.world_bank import UDCGlobalDataIntegrator  # type: ignore[import-not-found]
    except ImportError:
        try:
            # Fallback import path
            from data.apis.world_bank import UDCGlobalDataIntegrator  # type: ignore[import-not-found]
        except ImportError:
            UDCGlobalDataIntegrator = None  # type: ignore[misc,assignment]

from ..deterministic.models import Freshness, Provenance, QueryResult, QuerySpec, Row

GCC_DEFAULT_COUNTRIES = ["QAT", "SAU", "ARE", "KWT", "BHR", "OMN"]
WORLD_BANK_LICENSE = "World Bank Open Data (CC BY 4.0)"

# World Bank indicators with *_ZS suffix are ALREADY in percent units
# Example: SL.UEM.TOTL.ZS = "Unemployment, total (% of labor force)"
# Value of 0.11 means 0.11%, NOT 11%
PERCENT_INDICATORS = {
    "SL.UEM.TOTL.ZS",      # Unemployment, total (% of labor force)
    "SL.UEM.TOTL.MA.ZS",   # Unemployment, male (% of male labor force)
    "SL.UEM.TOTL.FE.ZS",   # Unemployment, female (% of female labor force)
    "SL.EMP.TOTL.SP.ZS",   # Employment to population ratio (%)
    "SL.TLF.CACT.ZS",      # Labor force participation rate (%)
    # Add more *_ZS indicators as needed
}


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


def _normalize_value(indicator_id: str, raw: float | None) -> float | None:
    """
    World Bank values for *_ZS indicators are already percentages.
    Do NOT multiply by 100 again.
    
    Args:
        indicator_id: World Bank indicator code
        raw: Raw value from API
        
    Returns:
        Normalized value (unchanged for percent indicators)
    """
    if raw is None:
        return None
    if indicator_id in PERCENT_INDICATORS:
        return float(raw)  # Already in percent units
    return float(raw)


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

    if UDCGlobalDataIntegrator is None:
        raise ImportError(
            "World Bank connector requires 'data.apis.world_bank' module. "
            "Please install the required external dependency."
        )

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

    # Normalize percent values (do not double-multiply)
    records = dataframe.to_dict(orient="records")
    normalized_records = []
    for record in records:
        normalized = {}
        for key, value in record.items():
            if isinstance(value, (int, float)):
                normalized[key] = _normalize_value(indicator_code, value)
            else:
                normalized[key] = value
        normalized_records.append(normalized)
    
    rows: list[Row] = [Row(data=record) for record in normalized_records]

    unit_label = "percent" if indicator_code in PERCENT_INDICATORS else (
        spec.expected_unit if spec.expected_unit else "unknown"
    )

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
        freshness=Freshness(
            asof_date=datetime.now().date().isoformat(),
            updated_at=datetime.now().isoformat()
        ),
        metadata={
            "units": {
                indicator_code: unit_label
            }
        },
    )
