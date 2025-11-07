"""Layer 2: Cross-source metric verification."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .schemas import CrossCheckRule, Issue
from ..data.deterministic.models import QueryResult

_SEGMENT_DEFAULT = "ALL"
_TOLERANCE_EPS = 1e-9
_METRIC_ALIAS_GROUPS: Mapping[str, frozenset[str]] = {
    "qatarization_rate": frozenset(
        {
            "qatarization_rate",
            "qatarization",
            "qatarization_percent",
            "qatarization_pct",
        }
    )
}
_ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in _METRIC_ALIAS_GROUPS.items()
    for alias in aliases
}


def _metric_keys_for(metric: str) -> frozenset[str]:
    """Return all acceptable field names for a metric, including aliases."""
    normalized = metric.strip()
    canonical = _ALIAS_TO_CANONICAL.get(normalized, normalized)
    if canonical in _METRIC_ALIAS_GROUPS:
        return _METRIC_ALIAS_GROUPS[canonical]
    return frozenset({canonical})


def _normalize_segment_key(data: Mapping[str, Any]) -> str:
    """Normalize segment/sector keys to support deterministic comparisons."""
    raw = data.get("segment") or data.get("sector")
    if raw is None:
        return _SEGMENT_DEFAULT
    text = str(raw).strip()
    if not text:
        return _SEGMENT_DEFAULT
    return text.upper()


def _metric_value_from_row(
    row: Mapping[str, Any],
    metric_candidates: Iterable[str],
) -> float | None:
    """
    Extract the metric value from a row, supporting both columnar and metric/value shapes.
    """
    for candidate in metric_candidates:
        value = row.get(candidate)
        if isinstance(value, (int, float)):
            return float(value)
        if (
            isinstance(row.get("metric"), str)
            and row.get("metric") == candidate
            and isinstance(row.get("value"), (int, float))
        ):
            return float(row["value"])
    return None


def _index_metric(qr: QueryResult, metric: str) -> dict[str, float]:
    """
    Index a QueryResult by normalized segment key for the requested metric.

    Supports per-row dictionaries in two shapes:
      - {"metric": "retention_rate", "value": 0.84, "segment": "..."}
      - {"retention_rate": 0.84, "segment": "..."}
    """
    out: dict[str, float] = {}
    metric_candidates = _metric_keys_for(metric)

    for row in qr.rows:
        data = row.data
        segment = _normalize_segment_key(data)
        value = _metric_value_from_row(data, metric_candidates)
        if value is not None:
            out[segment] = value

    return out


def cross_check(
    primary: QueryResult,
    references: list[QueryResult],
    rules: list[CrossCheckRule],
) -> list[Issue]:
    """
    Execute Layer 2 cross-checks between primary and reference data.

    Compares metric values across data sources and reports discrepancies
    that exceed configured tolerance thresholds.

    Args:
        primary: Primary query result (typically from LMIS)
        references: Reference query results (from MV, EXT, etc.)
        rules: Cross-check rules defining tolerances

    Returns:
        List of detected issues
    """
    issues: list[Issue] = []

    for rule in rules:
        primary_metrics = _index_metric(primary, rule.metric)

        for ref in references:
            ref_metrics = _index_metric(ref, rule.metric)

            for segment, primary_value in primary_metrics.items():
                if segment not in ref_metrics:
                    continue

                ref_value = ref_metrics[segment]
                if primary_value == 0 and ref_value == 0:
                    continue

                delta = abs(primary_value - ref_value)
                pct = (delta / max(1e-9, abs(primary_value))) * 100.0

                if pct - rule.tolerance_pct > _TOLERANCE_EPS:
                    issues.append(
                        Issue(
                            layer="L2",
                            code="XCHK_TOLERANCE_EXCEEDED",
                            message=(
                                f"{rule.metric} mismatch {pct:.2f}% "
                                f"for segment {segment}"
                            ),
                            severity="warning",
                            details={
                                "segment": segment,
                                "primary": primary_value,
                                "reference": ref_value,
                                "tolerance_pct": rule.tolerance_pct,
                                "ref_query_id": ref.query_id,
                            },
                        )
                    )

    return issues
