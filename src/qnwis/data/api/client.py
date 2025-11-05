"""
Typed Data API client over the Deterministic Data Layer.

Provides 22+ typed accessor methods with parameter validation, alias resolution,
and derived analytics. All methods are deterministic in-memory transforms with
no network calls or SQL queries.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Any, cast

from ..deterministic.cache_access import execute_cached
from ..deterministic.normalize import normalize_rows
from ..deterministic.registry import QueryRegistry
from .aliases import CANONICAL_TO_IDS
from .models import (
    AttritionRow,
    AvgSalaryRow,
    CompanySizeRow,
    EmploymentShareRow,
    EwiRow,
    QatarizationRow,
    SectorEmploymentRow,
    UnemploymentRow,
)


def _resolve(reg: QueryRegistry, key: str) -> str:
    """
    Resolve canonical key to a registered query ID.

    Args:
        reg: Query registry instance
        key: Canonical query key or partial ID phrase

    Returns:
        Resolved query ID from registry

    Raises:
        KeyError: If no matching query ID is found
    """
    ids = reg.all_ids()
    ids_set = set(ids)

    if key in ids_set:
        return key

    # First try canonical mapping, preferring synthetic datasets for backward compatibility.
    candidates = CANONICAL_TO_IDS.get(key, [])
    if candidates:
        ordered = sorted(candidates, key=lambda cid: (not cid.startswith("syn_"), cid))
        for candidate in ordered:
            if candidate in ids_set:
                return candidate

    # Fallback: match any registered ID containing the key, again preferring syn_* IDs.
    matches = [cid for cid in ids if key in cid]
    if matches:
        ordered = sorted(matches, key=lambda cid: (not cid.startswith("syn_"), cid))
        return ordered[0]

    raise KeyError(f"No query ID found for key={key}")


def _rows(
    reg: QueryRegistry,
    query_id: str,
    ttl_s: int,
    spec_override: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Execute query and return normalized data dictionaries.

    Args:
        reg: Query registry instance
        query_id: Query identifier
        ttl_s: Cache TTL in seconds
        spec_override: Optional parameter overrides as dict

    Returns:
        List of normalized data dictionaries
    """
    # Build QuerySpec with parameter overrides if provided
    spec_obj = None
    if spec_override:
        base_spec = reg.get(query_id)
        merged_params = {**base_spec.params, **spec_override.get("params", {})}
        spec_obj = base_spec.model_copy(update={"params": merged_params}, deep=True)

    res = execute_cached(query_id, reg, ttl_s=ttl_s, spec_override=spec_obj)
    return [r["data"] for r in normalize_rows([{"data": x.data} for x in res.rows])]


class DataAPI:
    """
    Typed accessors over the Deterministic Data Layer.

    All methods are deterministic, in-memory transforms. No network/SQL.
    Supports both synthetic (syn_*) and production (q_*) query IDs via
    alias resolution.

    Args:
        queries_dir: Path to YAML query registry (default: src/qnwis/data/queries)
        ttl_s: Default cache TTL in seconds (default: 300)

    Examples:
        >>> api = DataAPI()
        >>> unemployment = api.unemployment_qatar()
        >>> sectors = api.top_sectors_by_employment(2024, top_n=5)
    """

    def __init__(self, queries_dir: str | None = None, ttl_s: int = 300) -> None:
        """Initialize the DataAPI with a query registry and default cache TTL."""
        self.reg = QueryRegistry(queries_dir or "src/qnwis/data/queries")
        self.reg.load_all()
        self.ttl_s = ttl_s

    def latest_year(
        self,
        key: str,
        *,
        year_field: str = "year",
        spec_override: dict[str, Any] | None = None,
    ) -> int | None:
        """
        Determine the most recent year available for a canonical query or ID.

        Args:
            key: Canonical alias (e.g., "sector_employment") or exact query ID.
            year_field: Field name within each row representing the year (default: "year").
            spec_override: Optional parameter override dict forwarded to the query.

        Returns:
            Most recent year as an integer, or None when no year values are present.

        Raises:
            KeyError: If the key cannot be resolved to a registered query ID.
        """
        ids = self.reg.all_ids()
        qid = key if key in ids else _resolve(self.reg, key)
        rows = _rows(self.reg, qid, self.ttl_s, spec_override=spec_override or {})

        years: list[int] = []
        for row in rows:
            value = row.get(year_field)
            if value is None:
                continue
            try:
                years.append(int(value))
            except (TypeError, ValueError):
                continue
        return max(years) if years else None

    # ---- 1) Employment ----

    def employment_share_all(self) -> list[EmploymentShareRow]:
        """
        Get employment share by gender for all available years.

        Returns:
            List of employment share rows spanning all years
        """
        qid = _resolve(self.reg, "employment_share_all")
        data = _rows(self.reg, qid, self.ttl_s)
        return [EmploymentShareRow(**d) for d in data]

    def employment_share_latest(
        self, year: int | None = None
    ) -> list[EmploymentShareRow]:
        """
        Get employment share by gender for latest or specified year.

        Args:
            year: Optional year filter (defaults to query's default year)

        Returns:
            List of employment share rows for the specified/latest year
        """
        base = _resolve(self.reg, "employment_share_all")
        spec = {"params": {"year": int(year)}} if year else None
        data = _rows(self.reg, base, self.ttl_s, spec_override=spec)
        return [EmploymentShareRow(**d) for d in data if ("year" in d)]

    def employment_male_share(
        self, year: int | None = None
    ) -> list[EmploymentShareRow]:
        """
        Get male employment share, inferring female share as complement.

        Args:
            year: Optional year filter

        Returns:
            List of employment share rows with male/female percentages
        """
        qid = _resolve(self.reg, "employment_male_share")
        spec = {"params": {"year": int(year)}} if year else None
        data = _rows(self.reg, qid, self.ttl_s, spec_override=spec)
        out: list[EmploymentShareRow] = []
        for d in data:
            male_pct = float(d.get("male_percent", 0.0))
            female_pct = (
                float(d.get("female_percent", 0.0))
                if "female_percent" in d
                else 100.0 - male_pct
            )
            out.append(
                EmploymentShareRow(
                    year=int(d["year"]),
                    male_percent=male_pct,
                    female_percent=female_pct,
                    total_percent=float(d.get("total_percent", 100.0)),
                )
            )
        return out

    def employment_female_share(
        self, year: int | None = None
    ) -> list[EmploymentShareRow]:
        """
        Get female employment share, inferring male share as complement.

        Args:
            year: Optional year filter

        Returns:
            List of employment share rows with female/male percentages
        """
        qid = _resolve(self.reg, "employment_female_share")
        spec = {"params": {"year": int(year)}} if year else None
        data = _rows(self.reg, qid, self.ttl_s, spec_override=spec)
        out: list[EmploymentShareRow] = []
        for d in data:
            female_pct = float(d.get("female_percent", 0.0))
            male_pct = 100.0 - female_pct
            out.append(
                EmploymentShareRow(
                    year=int(d["year"]),
                    male_percent=male_pct,
                    female_percent=female_pct,
                    total_percent=float(d.get("total_percent", 100.0)),
                )
            )
        return out

    # ---- 2) Unemployment ----

    def unemployment_gcc_latest(self) -> list[UnemploymentRow]:
        """
        Get latest unemployment rates for all GCC countries.

        Returns:
            List of unemployment rows for GCC countries
        """
        qid = _resolve(self.reg, "unemployment_gcc_latest")
        return [UnemploymentRow(**d) for d in _rows(self.reg, qid, self.ttl_s)]

    def unemployment_qatar(self) -> UnemploymentRow | None:
        """
        Get latest unemployment rate for Qatar specifically.

        Returns:
            Unemployment row for Qatar, or None if not found
        """
        for r in self.unemployment_gcc_latest():
            if r.country.upper() in {"QAT", "QATAR"}:
                return r
        return None

    # ---- 3) Qatarization ----

    def qatarization_by_sector(
        self, year: int | None = None
    ) -> list[QatarizationRow]:
        """
        Get Qatarization metrics by sector.

        Args:
            year: Optional year filter

        Returns:
            List of Qatarization rows by sector
        """
        qid = _resolve(self.reg, "qatarization_by_sector")
        spec = {"params": {"year": int(year)}} if year else None
        return [
            QatarizationRow(**d) for d in _rows(self.reg, qid, self.ttl_s, spec_override=spec)
        ]

    def qatarization_gap_by_sector(
        self, year: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Calculate gap between actual and expected Qatarization percentage.

        Expected is computed as (qataris / total) * 100.

        Args:
            year: Optional year filter

        Returns:
            List of dictionaries with year, sector, and gap_percent
        """
        rows = self.qatarization_by_sector(year)
        out = []
        for r in rows:
            denom = r.qataris + r.non_qataris
            expected = 100.0 * r.qataris / denom if denom > 0 else 0.0
            gap = round(r.qatarization_percent - expected, 2)
            out.append({"year": r.year, "sector": r.sector, "gap_percent": gap})
        return out

    # ---- 4) Salary & Attrition ----

    def avg_salary_by_sector(self, year: int | None = None) -> list[AvgSalaryRow]:
        """
        Get average monthly salary by sector.

        Args:
            year: Optional year filter

        Returns:
            List of average salary rows by sector
        """
        qid = _resolve(self.reg, "avg_salary_by_sector")
        spec = {"params": {"year": int(year)}} if year else None
        return [
            AvgSalaryRow(**d) for d in _rows(self.reg, qid, self.ttl_s, spec_override=spec)
        ]

    def yoy_salary_by_sector(self, sector: str) -> list[dict[str, Any]]:
        """
        Calculate year-over-year salary growth for a specific sector.

        Args:
            sector: Sector name

        Returns:
            List of dictionaries with year, sector, and yoy_percent
        """
        all_rows = self.avg_salary_by_sector(year=None)
        series = [r for r in all_rows if r.sector == sector]
        series = sorted(series, key=lambda r: r.year)
        out: list[dict[str, Any]] = []
        prev = None
        for r in series:
            yoy = (
                None
                if prev is None or prev == 0
                else (r.avg_salary_qr - prev) / prev * 100.0
            )
            out.append(
                {
                    "year": r.year,
                    "sector": sector,
                    "yoy_percent": yoy if yoy is None else round(yoy, 2),
                }
            )
            prev = r.avg_salary_qr
        return out

    def attrition_by_sector(self, year: int | None = None) -> list[AttritionRow]:
        """
        Get employee attrition rates by sector.

        Args:
            year: Optional year filter

        Returns:
            List of attrition rows by sector
        """
        qid = _resolve(self.reg, "attrition_by_sector")
        spec = {"params": {"year": int(year)}} if year else None
        return [
            AttritionRow(**d) for d in _rows(self.reg, qid, self.ttl_s, spec_override=spec)
        ]

    # ---- 5) Company size & Employment ----

    def company_size_distribution(
        self, year: int | None = None
    ) -> list[CompanySizeRow]:
        """
        Get company distribution by size band.

        Args:
            year: Optional year filter

        Returns:
            List of company size distribution rows
        """
        qid = _resolve(self.reg, "company_size_distribution")
        spec = {"params": {"year": int(year)}} if year else None
        return [
            CompanySizeRow(**d)
            for d in _rows(self.reg, qid, self.ttl_s, spec_override=spec)
        ]

    def sector_employment(self, year: int | None = None) -> list[SectorEmploymentRow]:
        """
        Get employment counts by sector.

        Args:
            year: Optional year filter

        Returns:
            List of sector employment rows
        """
        qid = _resolve(self.reg, "sector_employment")
        spec = {"params": {"year": int(year)}} if year else None
        return [
            SectorEmploymentRow(**d)
            for d in _rows(self.reg, qid, self.ttl_s, spec_override=spec)
        ]

    def yoy_employment_growth_by_sector(self, sector: str) -> list[dict[str, Any]]:
        """
        Calculate year-over-year employment growth for a specific sector.

        Args:
            sector: Sector name

        Returns:
            List of dictionaries with year, sector, and yoy_percent
        """
        series = sorted(
            [r for r in self.sector_employment() if r.sector == sector],
            key=lambda r: r.year,
        )
        out: list[dict[str, Any]] = []
        prev = None
        for r in series:
            yoy = (
                None if prev is None or prev == 0 else (r.employees - prev) / prev * 100.0
            )
            out.append(
                {
                    "year": r.year,
                    "sector": sector,
                    "yoy_percent": yoy if yoy is None else round(yoy, 2),
                }
            )
            prev = r.employees
        return out

    # ---- 6) Early warning ----

    def ewi_employment_drop(self, year: int | None = None) -> list[EwiRow]:
        """
        Get early warning indicators for employment drops by sector.

        Args:
            year: Optional year filter

        Returns:
            List of early warning indicator rows
        """
        qid = _resolve(self.reg, "ewi_employment_drop")
        spec = {"params": {"year": int(year)}} if year else None
        return [EwiRow(**d) for d in _rows(self.reg, qid, self.ttl_s, spec_override=spec)]

    def early_warning_hotlist(
        self, year: int | None = None, threshold: float = 3.0, top_n: int = 5
    ) -> list[dict[str, Any]]:
        """
        Identify sectors with significant employment drops above threshold.

        Args:
            year: Optional year filter
            threshold: Minimum drop percentage to include (default: 3.0)
            top_n: Maximum number of sectors to return (default: 5)

        Returns:
            List of dictionaries with year, sector, and drop_percent,
            sorted by drop_percent descending
        """
        rows = self.ewi_employment_drop(year)
        hits = [
            r
            for r in rows
            if r.drop_percent is not None and r.drop_percent >= threshold
        ]
        hits = sorted(hits, key=lambda r: r.drop_percent, reverse=True)[:top_n]
        return [
            {"year": r.year, "sector": r.sector, "drop_percent": r.drop_percent}
            for r in hits
        ]

    # ---- 7) Convenience analytics ----

    def top_sectors_by_employment(
        self, year: int, top_n: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get top N sectors by employment count for a given year.

        Args:
            year: Year to analyze
            top_n: Number of top sectors to return (default: 5)

        Returns:
            List of dictionaries with sector and employees,
            sorted by employees descending
        """
        rows = [r for r in self.sector_employment(year) if isinstance(r.employees, int)]
        rows = sorted(rows, key=lambda r: r.employees, reverse=True)[:top_n]
        return [{"sector": r.sector, "employees": r.employees} for r in rows]

    def top_sectors_by_salary(self, year: int, top_n: int = 5) -> list[dict[str, Any]]:
        """
        Get top N sectors by average salary for a given year.

        Args:
            year: Year to analyze
            top_n: Number of top sectors to return (default: 5)

        Returns:
            List of dictionaries with sector and avg_salary_qr,
            sorted by salary descending
        """
        rows = [
            r for r in self.avg_salary_by_sector(year) if isinstance(r.avg_salary_qr, int)
        ]
        rows = sorted(rows, key=lambda r: r.avg_salary_qr, reverse=True)[:top_n]
        return [{"sector": r.sector, "avg_salary_qr": r.avg_salary_qr} for r in rows]

    def attrition_hotspots(self, year: int, top_n: int = 5) -> list[dict[str, Any]]:
        """
        Identify sectors with highest attrition rates for a given year.

        Args:
            year: Year to analyze
            top_n: Number of sectors to return (default: 5)

        Returns:
            List of dictionaries with sector and attrition_percent,
            sorted by attrition descending
        """
        rows = [
            r
            for r in self.attrition_by_sector(year)
            if isinstance(r.attrition_percent, float)
        ]
        rows = sorted(rows, key=lambda r: r.attrition_percent, reverse=True)[:top_n]
        return [
            {"sector": r.sector, "attrition_percent": r.attrition_percent} for r in rows
        ]

    @staticmethod
    def to_dataframe(rows: Sequence[Any]) -> Any:
        """
        Convert a sequence of row objects into a pandas DataFrame.

        Args:
            rows: Sequence of Pydantic models, dataclasses, or dict-like objects.

        Returns:
            pandas.DataFrame containing the row data.

        Raises:
            ImportError: If pandas is not installed in the current environment.
            TypeError: If rows cannot be converted into dictionaries.
        """
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - guarded optional dependency
            raise ImportError(
                "pandas is required for DataAPI.to_dataframe(); install it with "
                "`pip install pandas` to enable DataFrame exports."
            ) from exc

        if not rows:
            return pd.DataFrame()

        def _to_dict(item: Any) -> dict[str, Any]:
            if hasattr(item, "model_dump"):
                return cast(dict[str, Any], item.model_dump(mode="python"))
            if hasattr(item, "dict"):
                return cast(dict[str, Any], item.dict())
            if dataclasses.is_dataclass(item) and not isinstance(item, type):
                return dataclasses.asdict(item)
            if isinstance(item, Mapping):
                return dict(item)
            raise TypeError(
                "Row objects must be Pydantic models, dataclasses, or dict-like."
            )

        data = [_to_dict(row) for row in rows]
        return pd.DataFrame(data)
