"""Cross-source triangulation checks combining multiple query results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..data.derived.metrics import yoy_growth
from ..data.deterministic.cache_access import execute_cached
from ..data.deterministic.normalize import normalize_rows
from ..data.deterministic.registry import QueryRegistry
from .rules import (
    RuleIssue,
    check_ewi_vs_yoy_sign,
    check_percent_bounds,
    check_qatarization_formula,
    check_sum_to_one,
)


@dataclass
class TriangulationCheck:
    """Metadata for a triangulation check."""

    id: str
    description: str


@dataclass
class TriangulationResult:
    """Result of a single triangulation check."""

    check_id: str
    issues: list[RuleIssue] = field(default_factory=list)
    samples: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TriangulationBundle:
    """Complete bundle of all triangulation results."""

    results: list[TriangulationResult]
    warnings: list[str] = field(default_factory=list)
    licenses: list[str] = field(default_factory=list)


def _sample_rows(
    qid: str,
    reg: QueryRegistry,
    ttl_s: int = 300,
    *,
    max_rows: int | None = 50,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Execute cached query and return normalized sample rows plus license.

    Args:
        qid: Query ID to execute.
        reg: QueryRegistry instance.
        ttl_s: Cache TTL in seconds.
        max_rows: Optional hard cap on rows fetched per query.

    Returns:
        Tuple of (sampled rows, license string if available).
    """
    spec = reg.get(qid)
    spec_override = spec.model_copy(deep=True)
    if max_rows is not None:
        params = dict(spec_override.params or {})
        user_cap = params.get("max_rows")
        if not isinstance(user_cap, int) or user_cap <= 0 or user_cap > max_rows:
            params["max_rows"] = max_rows
        spec_override.params = params
    res = execute_cached(qid, reg, ttl_s=ttl_s, spec_override=spec_override)
    if res.provenance.source != "csv":
        raise RuntimeError(
            f"Triangulation only supports cached CSV data, got {res.provenance.source!r} "
            f"for query {qid}."
        )

    raw_rows = res.rows
    if max_rows is not None:
        raw_rows = raw_rows[: max_rows]
    normalized = normalize_rows([{"data": row.data} for row in raw_rows])
    rows = [r["data"] for r in normalized]
    return rows, res.provenance.license


def run_triangulation(reg: QueryRegistry, ttl_s: int = 300) -> TriangulationBundle:
    """
    Cross-source deterministic checks using ONLY synthetic queries.

    Performs the following checks:
      - Employment gender shares (male + female ~= total)
      - Qatarization formula: pct ~= 100*qataris/(qataris+non_qataris)
      - EWI vs YoY employment by sector: EWI high implies negative YoY
      - Bounds sanity checks on percentages

    Args:
        reg: QueryRegistry instance with loaded queries.
        ttl_s: Cache TTL in seconds.

    Returns:
        TriangulationBundle with all check results and warnings.
    """
    out: list[TriangulationResult] = []
    license_set: set[str] = set()

    # 1) Employment shares
    employment_rows, employment_license = _sample_rows(
        "syn_employment_share_by_gender_2017_2024",
        reg,
        ttl_s,
        max_rows=16,
    )
    if employment_license:
        license_set.add(employment_license)
    res1 = TriangulationResult(check_id="employment_sum_to_one")
    if employment_rows:
        latest = sorted(employment_rows, key=lambda d: int(d["year"]))[-1]
        res1.issues += check_sum_to_one(
            latest.get("male_percent"),
            latest.get("female_percent"),
            latest.get("total_percent"),
        )
        for key, value in latest.items():
            res1.issues += check_percent_bounds(key, value)
        res1.samples.append(latest)
    out.append(res1)

    # 2) Qatarization consistency (components)
    qatarization_rows, qatarization_license = _sample_rows(
        "syn_qatarization_components",
        reg,
        ttl_s,
        max_rows=16,
    )
    if qatarization_license:
        license_set.add(qatarization_license)
    res2 = TriangulationResult(check_id="qatarization_formula")
    if qatarization_rows:
        for row in qatarization_rows[:10]:
            res2.issues += check_qatarization_formula(
                row.get("qataris"),
                row.get("non_qataris"),
                row.get("qatarization_percent"),
            )
        res2.samples.append(qatarization_rows[0])
    out.append(res2)

    # 3) EWI vs YoY employment by sector
    sector_rows, sector_license = _sample_rows(
        "syn_sector_employment_by_year",
        reg,
        ttl_s,
        max_rows=64,
    )
    ewi_rows, ewi_license = _sample_rows(
        "syn_ewi_employment_drop",
        reg,
        ttl_s,
        max_rows=32,
    )
    for lic in (sector_license, ewi_license):
        if lic:
            license_set.add(lic)
    res3 = TriangulationResult(check_id="ewi_vs_yoy")
    if sector_rows and ewi_rows:
        rows = [{"data": row} for row in sector_rows]
        growth = yoy_growth(rows, value_key="employees", out_key="yoy_percent")
        by_sector: dict[str, dict[str, Any]] = {}
        for item in growth:
            data = item["data"]
            sector = data.get("sector")
            year_value = data.get("year")
            if sector is None or year_value is None:
                continue
            year = int(year_value)
            current = by_sector.get(sector)
            if current is None or int(current["year"]) < year:
                by_sector[sector] = data
        latest_ewi: dict[str, dict[str, Any]] = {}
        for item in ewi_rows:
            sector = item.get("sector")
            year_value = item.get("year")
            if sector is None or year_value is None:
                continue
            year = int(year_value)
            current = latest_ewi.get(sector)
            if current is None or int(current["year"]) < year:
                latest_ewi[sector] = item
        for sector, data in by_sector.items():
            yoy = data.get("yoy_percent")
            drop = (latest_ewi.get(sector) or {}).get("drop_percent")
            res3.issues.extend(check_ewi_vs_yoy_sign(drop, yoy))
        if by_sector:
            sample_sector = next(iter(by_sector))
            res3.samples.append(
                {
                    "sector": sample_sector,
                    "yoy_percent": by_sector[sample_sector].get("yoy_percent"),
                    "drop_percent": (latest_ewi.get(sample_sector) or {}).get("drop_percent"),
                }
            )
    out.append(res3)

    # 4) Sanity: ensure YoY, pct bounds on a few metrics
    res4 = TriangulationResult(check_id="bounds_sanity")
    for row in (employment_rows[:2] if employment_rows else []):
        for key, value in row.items():
            res4.issues += check_percent_bounds(key, value)
    out.append(res4)

    warnings = []
    for result in out:
        if result.issues:
            warnings.append(f"{result.check_id}:{len(result.issues)}")
    return TriangulationBundle(
        results=out,
        warnings=sorted(set(warnings)),
        licenses=sorted(license_set),
    )
