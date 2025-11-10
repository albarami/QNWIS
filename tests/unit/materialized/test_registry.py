"""
Unit tests for materialized view registry.
"""

from pathlib import Path

import pytest

import yaml
from src.qnwis.data.materialized.registry import (
    MaterializedRegistry,
    MaterializedSpecError,
)


@pytest.fixture
def valid_spec_yaml(tmp_path: Path) -> str:
    """Create valid MV specification YAML."""
    spec = [
        {
            "name": "mv_retention_monthly",
            "sql_id": "retention_by_sector",
            "params": {"period": "monthly"},
            "refresh_cron": "0 2 * * *",
            "indexes": [
                "idx_retention_sector ON mv_retention_monthly(sector)",
                "idx_retention_date ON mv_retention_monthly(period_start)",
            ],
        },
        {
            "name": "mv_salary_stats",
            "sql_id": "salary_statistics",
            "params": {},
            "refresh_cron": "0 3 * * *",
            "indexes": ["idx_salary_sector ON mv_salary_stats(sector)"],
        },
    ]
    yaml_file = tmp_path / "definitions.yml"
    yaml_file.write_text(yaml.dump(spec))
    return str(yaml_file)


@pytest.fixture
def missing_field_yaml(tmp_path: Path) -> str:
    """Create YAML with missing required field."""
    spec = [
        {
            "name": "mv_test",
            "sql_id": "test_query",
            "params": {},
            # Missing refresh_cron and indexes
        }
    ]
    yaml_file = tmp_path / "missing_field.yml"
    yaml_file.write_text(yaml.dump(spec))
    return str(yaml_file)


@pytest.fixture
def invalid_type_yaml(tmp_path: Path) -> str:
    """Create YAML with invalid field type."""
    spec = [
        {
            "name": "mv_test",
            "sql_id": "test_query",
            "params": "not_a_dict",  # Should be dict
            "refresh_cron": "0 2 * * *",
            "indexes": [],
        }
    ]
    yaml_file = tmp_path / "invalid_type.yml"
    yaml_file.write_text(yaml.dump(spec))
    return str(yaml_file)


@pytest.fixture
def invalid_indexes_yaml(tmp_path: Path) -> str:
    """Create YAML with invalid index definitions."""
    spec = [
        {
            "name": "mv_test",
            "sql_id": "test_query",
            "params": {},
            "refresh_cron": "0 2 * * *",
            "indexes": ["invalid_index_without_on_clause"],
        }
    ]
    yaml_file = tmp_path / "invalid_indexes.yml"
    yaml_file.write_text(yaml.dump(spec))
    return str(yaml_file)


class TestMaterializedRegistry:
    """Test MV specification registry loading and validation."""

    def test_load_valid_spec(self, valid_spec_yaml: str) -> None:
        """Valid YAML loads successfully."""
        registry = MaterializedRegistry(valid_spec_yaml)
        assert len(registry.specs) == 2
        assert registry.specs[0]["name"] == "mv_retention_monthly"
        assert registry.specs[1]["name"] == "mv_salary_stats"

    def test_missing_required_field_raises(self, missing_field_yaml: str) -> None:
        """Missing required field raises MaterializedSpecError."""
        with pytest.raises(MaterializedSpecError, match="Missing 'refresh_cron'"):
            MaterializedRegistry(missing_field_yaml)

    def test_invalid_field_type_raises(self, invalid_type_yaml: str) -> None:
        """Invalid field type raises MaterializedSpecError."""
        with pytest.raises(MaterializedSpecError, match="non-dict params"):
            MaterializedRegistry(invalid_type_yaml)

    def test_invalid_index_format_raises(self, invalid_indexes_yaml: str) -> None:
        """Invalid index format raises MaterializedSpecError."""
        with pytest.raises(
            MaterializedSpecError, match="Index definition must include 'ON"
        ):
            MaterializedRegistry(invalid_indexes_yaml)

    def test_by_name_success(self, valid_spec_yaml: str) -> None:
        """by_name returns correct spec."""
        registry = MaterializedRegistry(valid_spec_yaml)
        spec = registry.by_name("mv_salary_stats")
        assert spec["name"] == "mv_salary_stats"
        assert spec["sql_id"] == "salary_statistics"

    def test_by_name_not_found_raises(self, valid_spec_yaml: str) -> None:
        """by_name with unknown name raises MaterializedSpecError."""
        registry = MaterializedRegistry(valid_spec_yaml)
        with pytest.raises(MaterializedSpecError, match="Unknown MV: nonexistent"):
            registry.by_name("nonexistent")

    def test_empty_yaml_loads(self, tmp_path: Path) -> None:
        """Empty YAML file loads as empty spec list."""
        empty_file = tmp_path / "empty.yml"
        empty_file.write_text("")
        registry = MaterializedRegistry(str(empty_file))
        assert registry.specs == []

    def test_all_required_fields_validated(self, tmp_path: Path) -> None:
        """All required fields are validated."""
        required_fields = ["name", "sql_id", "params", "refresh_cron", "indexes"]

        for missing_field in required_fields:
            spec = {
                "name": "test",
                "sql_id": "query",
                "params": {},
                "refresh_cron": "0 2 * * *",
                "indexes": ["idx ON table(col)"],
            }
            del spec[missing_field]

            yaml_file = tmp_path / f"missing_{missing_field}.yml"
            yaml_file.write_text(yaml.dump([spec]))

            with pytest.raises(MaterializedSpecError, match=f"Missing '{missing_field}'"):
                MaterializedRegistry(str(yaml_file))

    def test_string_fields_must_be_strings(self, tmp_path: Path) -> None:
        """String fields must be strings, not other types."""
        for field in ["name", "sql_id", "refresh_cron"]:
            spec = {
                "name": "test",
                "sql_id": "query",
                "params": {},
                "refresh_cron": "0 2 * * *",
                "indexes": ["idx ON table(col)"],
            }
            spec[field] = 123  # Wrong type

            yaml_file = tmp_path / f"invalid_{field}.yml"
            yaml_file.write_text(yaml.dump([spec]))

            with pytest.raises(MaterializedSpecError, match=f"'{field}' must be a string"):
                MaterializedRegistry(str(yaml_file))

    def test_indexes_must_be_list_of_strings(self, tmp_path: Path) -> None:
        """Indexes must be a list of strings."""
        # Test non-list indexes
        spec = {
            "name": "test",
            "sql_id": "query",
            "params": {},
            "refresh_cron": "0 2 * * *",
            "indexes": "not_a_list",
        }
        yaml_file = tmp_path / "invalid_indexes_type.yml"
        yaml_file.write_text(yaml.dump([spec]))

        with pytest.raises(MaterializedSpecError, match="indexes must be a list"):
            MaterializedRegistry(str(yaml_file))

        # Test list with non-string elements
        spec["indexes"] = [123, 456]
        yaml_file = tmp_path / "invalid_indexes_elements.yml"
        yaml_file.write_text(yaml.dump([spec]))

        with pytest.raises(MaterializedSpecError, match="indexes must be a list"):
            MaterializedRegistry(str(yaml_file))
