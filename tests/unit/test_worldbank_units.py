"""
Unit tests for World Bank percent indicator normalization.

Ensures that *_ZS indicators are not double-scaled.
"""

from src.qnwis.data.connectors import world_bank_det as wb_module
from src.qnwis.data.connectors.world_bank_det import (
    PERCENT_INDICATORS,
    _normalize_value,
)
from src.qnwis.data.deterministic.models import QuerySpec


def test_normalize_value_percent_indicators():
    """Percent indicators should pass through unchanged."""
    # SL.UEM.TOTL.ZS is a percent indicator
    assert _normalize_value("SL.UEM.TOTL.ZS", 0.11) == 0.11
    assert _normalize_value("SL.UEM.TOTL.MA.ZS", 5.66) == 5.66
    assert _normalize_value("SL.UEM.TOTL.FE.ZS", 0.0) == 0.0


def test_normalize_value_non_percent_indicators():
    """Non-percent indicators should also pass through unchanged."""
    assert _normalize_value("SP.POP.TOTL", 2800000.0) == 2800000.0
    assert _normalize_value("NY.GDP.MKTP.CD", 183000000000.0) == 183000000000.0


def test_normalize_value_handles_none():
    """None values should pass through as None."""
    assert _normalize_value("SL.UEM.TOTL.ZS", None) is None
    assert _normalize_value("SP.POP.TOTL", None) is None


def test_percent_indicators_set_contains_unemployment():
    """Verify that unemployment indicators are in the percent set."""
    assert "SL.UEM.TOTL.ZS" in PERCENT_INDICATORS
    assert "SL.UEM.TOTL.MA.ZS" in PERCENT_INDICATORS
    assert "SL.UEM.TOTL.FE.ZS" in PERCENT_INDICATORS


def test_no_double_scaling():
    """
    Critical test: 0.11 from World Bank should stay 0.11 (meaning 0.11%),
    NOT be multiplied to 11.0.
    """
    raw_value = 0.11  # World Bank returns this for Qatar unemployment
    normalized = _normalize_value("SL.UEM.TOTL.ZS", raw_value)
    
    # Should NOT multiply by 100
    assert normalized == 0.11
    assert normalized != 11.0
    
    # When displayed, this should show as "0.11%"
    display = f"{normalized:.2f}%"
    assert display == "0.11%"


def test_units_metadata_exposed_for_percent_indicators(monkeypatch):
    """run_world_bank_query should annotate metadata.units for percent indicators."""

    class DummyFrame:
        columns = ["country", "year", "value"]

        @property
        def empty(self) -> bool:  # pragma: no cover - trivial
            return False

        def to_dict(self, orient: str):
            assert orient == "records"
            return [{"country": "QAT", "year": 2024, "value": 0.11}]

    class DummyIntegrator:
        def get_indicator(self, **_: object) -> DummyFrame:
            return DummyFrame()

    monkeypatch.setattr(wb_module, "UDCGlobalDataIntegrator", lambda: DummyIntegrator())

    spec = QuerySpec(
        id="world_bank_unemployment",
        title="WB unemployment",
        description="Unemployment rate from World Bank",
        source="world_bank",
        params={"indicator": "SL.UEM.TOTL.ZS"},
        expected_unit="percent",
    )

    result = wb_module.run_world_bank_query(spec)

    assert result.metadata["units"]["SL.UEM.TOTL.ZS"] == "percent"
