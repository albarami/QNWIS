"""Direct unit-style test to prove CitationInjector adds inline citations.

This bypasses LLM and DB, hitting only the core citation logic.
"""

from __future__ import annotations

from src.qnwis.orchestration.citation_injector import CitationInjector
from src.qnwis.data.deterministic.models import QueryResult, Row, Provenance, Freshness


def run_test() -> bool:
    """Create synthetic source data and ensure citations are injected."""
    # Synthetic deterministic source data
    source_data = {
        "unemployment_query": QueryResult(
            query_id="unemployment_query",
            rows=[Row(data={"unemployment_rate": 0.10})],
            unit="percent",
            provenance=Provenance(
                source="sql",
                dataset_id="gcc_unemployment",
                locator="stub://unemployment_query",
                fields=["unemployment_rate"],
            ),
            freshness=Freshness(asof_date="2024-03-31", updated_at=None),
        )
    }

    injector = CitationInjector()

    original = "Qatar's unemployment is 0.10% compared to Saudi's 4.9%."
    result = injector.inject_citations(original, source_data)

    print("\nORIGINAL:")
    print(original)
    print("\nWITH CITATIONS:")
    print(result)
    print("\n" + "=" * 80)

    # Basic assertions
    assert "[Per extraction:" in result, "No citations found in result"
    # Depending on formatting, the injector may match "0.10" and append the
    # citation before the percent sign. Accept either raw or percent form.
    assert "0.10" in result, "Primary number missing from result"
    assert (
        "gcc_unemployment" in result
        or "stub://unemployment_query" in result
        or "2024-03-31" in result
    ), "Provenance details not visible in citation"

    print("✅ ALL ASSERTIONS PASSED - CitationInjector is working correctly")
    print("=" * 80)
    return True


if __name__ == "__main__":
    ok = run_test()
    raise SystemExit(0 if ok else 1)
