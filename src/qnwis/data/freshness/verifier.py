"""Freshness verification and as-of date detection for query results."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..deterministic.models import QueryResult, QuerySpec

_ISO_DATE_FMT = "%Y-%m-%d"
_AUTO_SENTINELS = {"auto", "api"}


def _normalize_numeric_year(value: float | int) -> str | None:
    """Convert numeric year into canonical YYYY-MM-DD string."""
    year = int(value)
    if 1000 <= year <= 9999:
        return f"{year}-12-31"
    return None


def _strip_time_suffix(value: str) -> str:
    """Remove time components and trailing Z from a timestamp string."""
    candidate = value.replace("Z", "")
    if "T" in candidate:
        candidate = candidate.split("T", 1)[0]
    if " " in candidate:
        candidate = candidate.split(" ", 1)[0]
    return candidate


def _normalize_four_digit_year(candidate: str) -> str | None:
    """Return year-end ISO string for four-digit year candidates."""
    return f"{candidate}-12-31" if len(candidate) == 4 and candidate.isdigit() else None


def _normalize_numeric_string(candidate: str) -> str | None:
    """Attempt to treat string candidate as numeric year."""
    try:
        numeric_candidate = float(candidate)
    except ValueError:
        return None
    return _normalize_numeric_year(numeric_candidate)


def _parse_iso_section(candidate: str) -> str | None:
    """Parse ISO formatted date strings."""
    token = candidate[:10] if len(candidate) >= 10 else candidate
    try:
        return datetime.strptime(token, _ISO_DATE_FMT).strftime(_ISO_DATE_FMT)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(token)
            return parsed.date().isoformat()
        except ValueError:
            return None


def _normalize_string_candidate(value: str) -> str | None:
    """Normalize string representations of dates or years."""
    trimmed = value.strip()
    if not trimmed:
        return None
    if trimmed.lower() in _AUTO_SENTINELS:
        return None
    candidate = _strip_time_suffix(trimmed)
    normalized_year = _normalize_four_digit_year(candidate) or _normalize_numeric_string(candidate)
    if normalized_year:
        return normalized_year
    return _parse_iso_section(candidate)


def _normalize_date_candidate(value: Any) -> str | None:
    """Normalize candidate value into YYYY-MM-DD if possible."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return _normalize_numeric_year(value)
    if isinstance(value, str):
        return _normalize_string_candidate(value)
    return None


def _extract_year(value: Any) -> int | None:
    """Extract four-digit year from various numeric representations."""
    if value is None:
        return None
    candidate: int | None
    if isinstance(value, (int, float)):
        candidate = int(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            candidate = int(float(stripped))
        except ValueError:
            return None
    else:
        return None
    if 1000 <= candidate <= 9999:
        return candidate
    return None


def _extract_explicit_asof(res: QueryResult) -> tuple[str | None, bool]:
    """Attempt to normalize explicit freshness.asof_date value."""
    raw = res.freshness.asof_date
    if raw is None:
        return None, False
    normalized = _normalize_date_candidate(raw)
    if normalized:
        return normalized, False
    if isinstance(raw, str) and raw.strip().lower() in _AUTO_SENTINELS:
        return None, False
    return None, True


def _guess_asof_date(res: QueryResult) -> tuple[str | None, bool]:
    """
    Derive as-of date from result data.

    Prefers explicit res.freshness.asof_date if not 'auto'/'api',
    otherwise attempts to derive from 'date' or 'year' columns.
    """
    explicit, explicit_error = _extract_explicit_asof(res)
    if explicit or explicit_error:
        return explicit, explicit_error

    for row in res.rows:
        normalized_row_date = _normalize_date_candidate(row.data.get("date"))
        if normalized_row_date:
            return normalized_row_date, False

    years: list[int] = []
    for row in res.rows:
        year_candidate = _extract_year(row.data.get("year"))
        if year_candidate is not None:
            years.append(year_candidate)

    if years:
        return f"{max(years)}-12-31", False

    return None, False


def _coerce_sla_days(raw_value: Any) -> int | None:
    """Validate freshness SLA days constraint as non-negative integer."""
    if raw_value is None:
        return None
    try:
        coerced = int(raw_value)
    except (TypeError, ValueError):
        return None
    if coerced < 0:
        return None
    return coerced


def verify_freshness(
    spec: QuerySpec, res: QueryResult, now: datetime | None = None
) -> list[str]:
    """
    Verify result freshness against SLA days constraint.

    Returns list of warning strings if data is stale or freshness is unknown.
    """
    warnings: list[str] = []
    raw_sla = spec.constraints.get("freshness_sla_days")
    if raw_sla is None:
        return warnings

    sla_days = _coerce_sla_days(raw_sla)
    if sla_days is None:
        warnings.append("freshness_invalid_sla")
        return warnings

    now = now or datetime.utcnow()
    asof, parse_error = _guess_asof_date(res)
    if parse_error:
        warnings.append("freshness_parse_error")
        return warnings
    if not asof:
        warnings.append("freshness_unknown")
        return warnings

    try:
        asof_dt = datetime.strptime(asof, _ISO_DATE_FMT)
    except ValueError:
        warnings.append("freshness_parse_error")
        return warnings

    age = (now - asof_dt).days
    if age > sla_days:
        warnings.append(f"stale_data:{age}>{sla_days}")

    return warnings
