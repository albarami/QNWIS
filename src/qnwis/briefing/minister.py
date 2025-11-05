"""Build executive-ready Minister Briefing from council + verification."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..data.catalog.registry import DatasetCatalog
from ..data.deterministic.registry import QueryRegistry
from ..orchestration.council import CouncilConfig, run_council
from ..verification.triangulation import TriangulationBundle, run_triangulation


@dataclass
class MinisterBriefing:
    """Executive briefing combining council findings and verification results."""

    title: str
    headline: list[str]
    key_metrics: dict[str, float]
    red_flags: list[str]
    provenance: list[str]
    min_confidence: float
    licenses: list[str]
    markdown: str


def _collect_confidence(findings: list[dict[str, Any]]) -> float:
    """Return the minimum confidence score across findings (defaulting to 1.0)."""
    scores = [
        float(f.get("confidence_score", 1.0))
        for f in findings
        if isinstance(f, dict) and isinstance(f.get("confidence_score", 1.0), (int, float))
    ]
    return min(scores) if scores else 1.0


def _collect_provenance(findings: list[dict[str, Any]]) -> list[str]:
    """Return a deduplicated list of evidence locators from council findings."""
    locators: list[str] = []
    for finding in findings:
        for evidence in finding.get("evidence", []):
            locator = evidence.get("locator")
            if locator and locator not in locators:
                locators.append(locator)
    return locators


def _collect_licenses(
    findings: list[dict[str, Any]],
    triangulation: TriangulationBundle,
) -> list[str]:
    """Aggregate known licenses from catalog metadata and triangulation queries."""
    licenses: set[str] = set(triangulation.licenses)
    catalog_path = Path("data") / "catalog" / "datasets.yaml"
    if not catalog_path.exists():
        return sorted(licenses)
    catalog = DatasetCatalog(catalog_path)
    for finding in findings:
        evidence_items = finding.get("evidence", [])
        for evidence in evidence_items:
            locator = evidence.get("locator")
            dataset_id = evidence.get("dataset_id")
            license_value: str | None = None
            if locator:
                match = catalog.match(locator)
                if match:
                    license_value = match.get("license")
            if not license_value and dataset_id:
                match = catalog.match(dataset_id)
                if match:
                    license_value = match.get("license")
            if license_value:
                licenses.add(str(license_value))
    return sorted(licenses)


def build_briefing(queries_dir: str | None = None, ttl_s: int = 300) -> MinisterBriefing:
    """
    Run council + triangulation on synthetic data and build executive briefing.

    This is a deterministic process using only synthetic CSV data:
    1. Run the council to gather findings and consensus.
    2. Run triangulation to cross-check numeric consistency.
    3. Build a structured briefing with markdown output.

    Args:
        queries_dir: Optional queries directory path.
        ttl_s: Cache TTL in seconds.

    Returns:
        MinisterBriefing with structured data and markdown content.
    """
    resolved_queries_dir = queries_dir or "src/qnwis/data/queries"

    council_json = run_council(CouncilConfig(queries_dir=resolved_queries_dir, ttl_s=ttl_s))
    council_payload = council_json["council"]
    findings = council_payload["findings"]
    consensus = council_payload["consensus"]

    registry = QueryRegistry(resolved_queries_dir)
    registry.load_all()
    triangulation = run_triangulation(registry, ttl_s=ttl_s)

    min_confidence = _collect_confidence(findings)

    headline: list[str] = []
    headline_metric: tuple[str, float] | None = None
    if isinstance(consensus, dict):
        value = consensus.get("employment_total_percent")
        if isinstance(value, (int, float)):
            headline_metric = ("employment_total_percent", float(value))
        else:
            for key, raw in consensus.items():
                if isinstance(raw, (int, float)):
                    headline_metric = (key, float(raw))
                    break
    if headline_metric:
        key, metric_value = headline_metric
        headline.append(f"{key} = {metric_value:.1f} (synthetic consensus).")
    else:
        headline.append("No consensus metrics available; using synthetic baseline only.")

    if triangulation.warnings:
        headline.append(f"Verification warnings: {', '.join(triangulation.warnings)}.")
    else:
        headline.append("Verification checks passed without warnings.")

    headline.append(f"Minimum finding confidence: {min_confidence:.2f}.")

    key_metrics: dict[str, float] = {}
    if isinstance(consensus, dict):
        for key, value in list(consensus.items())[:5]:
            if isinstance(value, (int, float)):
                key_metrics[key] = float(value)

    red_flags: list[str] = []
    for result in triangulation.results:
        for issue in result.issues:
            red_flags.append(f"{issue.code}: {issue.detail}")
    red_flags = red_flags[:8]

    provenance = _collect_provenance(findings)
    licenses = _collect_licenses(findings, triangulation)

    markdown_lines = [
        "# Minister Briefing (Synthetic Demo)",
        "## Headline",
        *[f"- {bullet}" for bullet in headline],
        "## Key Metrics",
    ]
    for key, value in key_metrics.items():
        markdown_lines.append(f"- **{key}**: {value:.2f}")
    markdown_lines.append("## Confidence")
    markdown_lines.append(f"- Minimum confidence across findings: {min_confidence:.2f}")
    if red_flags:
        markdown_lines.append("## Red Flags")
        for flag in red_flags:
            markdown_lines.append(f"- {flag}")
    if provenance:
        markdown_lines.append("## Provenance")
        for locator in provenance[:10]:
            markdown_lines.append(f"- {locator}")
    if licenses:
        markdown_lines.append("## Licenses")
        for license_name in licenses:
            markdown_lines.append(f"- {license_name}")
    markdown = "\n".join(markdown_lines)

    return MinisterBriefing(
        title="Minister Briefing - Synthetic Demo",
        headline=headline,
        key_metrics=key_metrics,
        red_flags=red_flags,
        provenance=provenance,
        min_confidence=min_confidence,
        licenses=licenses,
        markdown=markdown,
    )
