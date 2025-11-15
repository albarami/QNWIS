"""Tests for the citation injector helpers."""
from types import SimpleNamespace

from src.qnwis.orchestration.citation_injector import CitationInjector


def _make_query_result(value: float):
    """Create a lightweight object that mimics a QueryResult."""
    row = SimpleNamespace(data={"value": value})
    provenance = SimpleNamespace(source="GCC-STAT")
    freshness = SimpleNamespace(asof_date="Q1-2024")
    return SimpleNamespace(rows=[row], provenance=provenance, freshness=freshness)


def test_generate_number_formats_includes_decimal_percent():
    injector = CitationInjector()

    formats = injector._generate_number_formats(0.10)

    assert "0.10%" in formats
    assert "0.1%" in formats


def test_inject_citations_matches_decimal_percent_directly():
    injector = CitationInjector()
    source_data = {"unemployment_rate": _make_query_result(0.10)}

    text = "Qatar's unemployment rate is 0.10%."
    cited_text = injector.inject_citations(text, source_data)

    assert "[Per extraction: '0.10%' from GCC-STAT Q1-2024]" in cited_text
