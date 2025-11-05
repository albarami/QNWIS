"""Unit tests for deterministic normalization utilities."""

from src.qnwis.data.deterministic.models import Row
from src.qnwis.data.deterministic.normalize import (
    normalize_params,
    normalize_rows,
    to_snake_case,
)


def test_to_snake_case() -> None:
    """Test column name conversion to snake_case."""
    assert to_snake_case("Male Percent") == "male_percent"
    assert to_snake_case("Year") == "year"
    assert to_snake_case("GDP(QAR)") == "gdp_qar"
    assert to_snake_case("Female-Percent") == "female_percent"
    assert to_snake_case("Total__Value") == "total_value"
    assert to_snake_case("CamelCase") == "camel_case"
    assert to_snake_case("camelCase") == "camel_case"


def test_normalize_params_year() -> None:
    """Test year parameter normalization."""
    out = normalize_params({"year": "2023"})
    assert out["year"] == 2023
    assert isinstance(out["year"], int)

    out = normalize_params({"year": "2023.0"})
    assert out["year"] == 2023

    out = normalize_params({"year": 2022})
    assert out["year"] == 2022


def test_normalize_params_timeout_and_max_rows() -> None:
    """Test timeout_s and max_rows normalization."""
    out = normalize_params({"timeout_s": "15", "max_rows": "100"})
    assert out["timeout_s"] == 15
    assert out["max_rows"] == 100
    assert isinstance(out["timeout_s"], int)
    assert isinstance(out["max_rows"], int)


def test_normalize_params_to_percent() -> None:
    """Test to_percent parameter normalization."""
    out = normalize_params({"to_percent": "male"})
    assert out["to_percent"] == ["male"]
    assert isinstance(out["to_percent"], list)

    out = normalize_params({"to_percent": ["male", "female"]})
    assert out["to_percent"] == ["male", "female"]


def test_normalize_params_combined() -> None:
    """Test combined parameter normalization."""
    out = normalize_params({
        "year": "2023",
        "timeout_s": "15",
        "to_percent": "male",
        "custom_param": "unchanged",
    })
    assert out["year"] == 2023
    assert out["timeout_s"] == 15
    assert out["to_percent"] == ["male"]
    assert out["custom_param"] == "unchanged"


def test_normalize_params_invalid_values() -> None:
    """Test normalization with invalid values leaves them unchanged."""
    out = normalize_params({"year": "not_a_year", "timeout_s": "invalid"})
    # Should leave invalid values as-is rather than crashing
    assert "year" in out
    assert "timeout_s" in out


def test_normalize_rows_basic() -> None:
    """Test basic row normalization."""
    rows = [{"data": {"Male Percent": "60.0", "Year": "2023"}}]
    out = normalize_rows(rows)
    assert len(out) == 1
    assert out[0]["data"]["male_percent"] == "60.0"
    assert out[0]["data"]["year"] == "2023"


def test_normalize_rows_plain_dict() -> None:
    """Test normalization of plain dict rows (without 'data' wrapper)."""
    rows = [{"Male Percent": "60.0", "Year": "2023"}]
    out = normalize_rows(rows)
    assert len(out) == 1
    assert out[0]["data"]["male_percent"] == "60.0"
    assert out[0]["data"]["year"] == "2023"


def test_normalize_rows_string_trimming() -> None:
    """Test that string values are trimmed."""
    rows = [{"data": {"Name": "  Qatar  ", "Value": "  100  "}}]
    out = normalize_rows(rows)
    assert out[0]["data"]["name"] == "Qatar"
    assert out[0]["data"]["value"] == "100"


def test_normalize_rows_multiple() -> None:
    """Test normalization of multiple rows."""
    rows = [
        {"data": {"Male Percent": "60", "Year": 2023}},
        {"data": {"Male Percent": "55", "Year": 2022}},
    ]
    out = normalize_rows(rows)
    assert len(out) == 2
    assert out[0]["data"]["male_percent"] == "60"
    assert out[0]["data"]["year"] == 2023
    assert out[1]["data"]["male_percent"] == "55"
    assert out[1]["data"]["year"] == 2022


def test_normalize_rows_numeric_values() -> None:
    """Test that numeric values are preserved."""
    rows = [{"data": {"Year": 2023, "Value": 100.5}}]
    out = normalize_rows(rows)
    assert out[0]["data"]["year"] == 2023
    assert out[0]["data"]["value"] == 100.5
    assert isinstance(out[0]["data"]["year"], int)
    assert isinstance(out[0]["data"]["value"], float)


def test_normalize_rows_row_model() -> None:
    """Normalize Row model inputs without errors."""
    rows = [Row(data={"Year": "2023", "Value": " 200 "})]
    out = normalize_rows(rows)
    assert out[0]["data"]["year"] == "2023"
    assert out[0]["data"]["value"] == "200"


def test_normalize_rows_idempotent() -> None:
    """Repeated normalization should not change results."""
    rows = [{"data": {"Name": "Qatar", "Value": " 10 "}}]
    first = normalize_rows(rows)
    second = normalize_rows(first)
    assert first == second


def test_normalize_rows_non_mapping_input() -> None:
    """Non-mapping inputs yield empty payloads instead of raising."""
    out = normalize_rows([{"data": {"Name": "Qatar"}}, 42])
    assert out[0]["data"]["name"] == "Qatar"
    assert out[1]["data"] == {}
