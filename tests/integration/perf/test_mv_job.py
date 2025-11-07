"""
Integration test for materialized view refresh job.

Tests that the job loads definitions, calls query registry to render SQL,
and materializer executes create+refresh operations.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from src.qnwis.jobs.refresh_materializations import main as refresh_mv_main


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock database adapter with query registry."""
    mock = MagicMock()
    mock.execute_sql = MagicMock()

    # Setup mock query registry
    mock_registry = MagicMock()
    mock_registry.get.return_value = {"sql": "SELECT * FROM table"}
    mock_registry.render_select.side_effect = lambda sql_id, params: (
        f"SELECT * FROM {sql_id}_table WHERE {list(params.keys())[0]}='{list(params.values())[0]}'"
        if params
        else f"SELECT * FROM {sql_id}_table"
    )

    mock.query_registry = mock_registry

    return mock


@pytest.fixture
def mv_definitions_yaml(tmp_path: Path) -> str:
    """Create temporary MV definitions YAML."""
    specs = [
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
            "params": {"year": "2024"},
            "refresh_cron": "0 3 * * *",
            "indexes": ["idx_salary_sector ON mv_salary_stats(sector)"],
        },
    ]

    yaml_file = tmp_path / "definitions.yml"
    yaml_file.write_text(yaml.dump(specs))
    return str(yaml_file)


class TestMVRefreshJob:
    """Test MV refresh job integration."""

    def test_job_loads_definitions_and_materializes(
        self, mock_db: MagicMock, mv_definitions_yaml: str
    ) -> None:
        """Job loads definitions, renders SQL, and creates materialized views."""
        refresh_mv_main(mock_db, mv_definitions_yaml)

        # Verify query registry was called to validate queries
        assert mock_db.query_registry.get.call_count == 2
        mock_db.query_registry.get.assert_any_call("retention_by_sector")
        mock_db.query_registry.get.assert_any_call("salary_statistics")

        # Verify render_select was called for each spec
        assert mock_db.query_registry.render_select.call_count == 2

        # Verify execute_sql was called for CREATE, REFRESH, and CREATE INDEX
        # 2 MVs × (1 CREATE + 1 REFRESH + indexes) = 2×3 + 2×2 = 8 calls
        # mv_retention_monthly: CREATE, REFRESH, 2 indexes = 4 calls
        # mv_salary_stats: CREATE, REFRESH, 1 index = 3 calls
        assert mock_db.execute_sql.call_count == 7

    def test_job_uses_rendered_sql_from_registry(
        self, mock_db: MagicMock, mv_definitions_yaml: str
    ) -> None:
        """Job uses SQL rendered from query registry, not ad-hoc SQL."""
        refresh_mv_main(mock_db, mv_definitions_yaml)

        # Check that CREATE calls use rendered SQL
        create_calls = [
            call_args[0][0]
            for call_args in mock_db.execute_sql.call_args_list
            if "CREATE MATERIALIZED VIEW" in call_args[0][0]
        ]

        assert len(create_calls) == 2

        # Verify rendered SQL includes table names from sql_id
        assert any("retention_by_sector_table" in sql for sql in create_calls)
        assert any("salary_statistics_table" in sql for sql in create_calls)

    def test_job_creates_indexes_for_each_mv(
        self, mock_db: MagicMock, mv_definitions_yaml: str
    ) -> None:
        """Job creates all specified indexes for each MV."""
        refresh_mv_main(mock_db, mv_definitions_yaml)

        # Check that CREATE INDEX calls were made
        index_calls = [
            call_args[0][0]
            for call_args in mock_db.execute_sql.call_args_list
            if "CREATE INDEX" in call_args[0][0]
        ]

        assert len(index_calls) == 3  # 2 + 1 indexes

        # Verify specific indexes
        assert any("idx_retention_sector" in sql for sql in index_calls)
        assert any("idx_retention_date" in sql for sql in index_calls)
        assert any("idx_salary_sector" in sql for sql in index_calls)

    def test_job_calls_refresh_concurrently(
        self, mock_db: MagicMock, mv_definitions_yaml: str
    ) -> None:
        """Job calls REFRESH MATERIALIZED VIEW CONCURRENTLY for each MV."""
        refresh_mv_main(mock_db, mv_definitions_yaml)

        # Check that REFRESH calls were made
        refresh_calls = [
            call_args[0][0]
            for call_args in mock_db.execute_sql.call_args_list
            if "REFRESH MATERIALIZED VIEW CONCURRENTLY" in call_args[0][0]
        ]

        assert len(refresh_calls) == 2

        # Verify specific MVs were refreshed
        assert any("mv_retention_monthly" in sql for sql in refresh_calls)
        assert any("mv_salary_stats" in sql for sql in refresh_calls)

    def test_job_validates_queries_exist_in_registry(
        self, mock_db: MagicMock, mv_definitions_yaml: str
    ) -> None:
        """Job validates that sql_id exists in query registry."""
        # Setup query registry to raise on invalid query
        mock_db.query_registry.get.side_effect = [
            {"sql": "SELECT * FROM table"},  # First query exists
            KeyError("Unknown query"),  # Second query doesn't exist
        ]

        with pytest.raises(KeyError, match="Unknown query"):
            refresh_mv_main(mock_db, mv_definitions_yaml)

    def test_job_handles_empty_params(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        """Job handles MV specs with empty params dict."""
        spec = [
            {
                "name": "mv_no_params",
                "sql_id": "simple_query",
                "params": {},
                "refresh_cron": "0 2 * * *",
                "indexes": ["idx ON mv_no_params(id)"],
            }
        ]

        yaml_file = tmp_path / "empty_params.yml"
        yaml_file.write_text(yaml.dump(spec))

        refresh_mv_main(mock_db, str(yaml_file))

        # Verify render_select was called with empty params
        mock_db.query_registry.render_select.assert_called_once_with("simple_query", {})

    def test_job_output_json_format(
        self, mock_db: MagicMock, mv_definitions_yaml: str, capsys: pytest.CaptureFixture  # type: ignore[type-arg]
    ) -> None:
        """Job outputs JSON with materialized view names and sql_ids."""
        import json

        refresh_mv_main(mock_db, mv_definitions_yaml)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "materialized" in output
        assert len(output["materialized"]) == 2

        # Verify output structure
        names = [mv["name"] for mv in output["materialized"]]
        sql_ids = [mv["sql_id"] for mv in output["materialized"]]

        assert "mv_retention_monthly" in names
        assert "mv_salary_stats" in names
        assert "retention_by_sector" in sql_ids
        assert "salary_statistics" in sql_ids

    def test_job_uses_materializer_correctly(
        self, mock_db: MagicMock, mv_definitions_yaml: str
    ) -> None:
        """Job creates PostgresMaterializer and calls create_or_replace."""
        refresh_mv_main(mock_db, mv_definitions_yaml)

        # Verify the sequence of operations
        call_list = mock_db.execute_sql.call_args_list

        # First MV operations should be in sequence: CREATE, REFRESH, INDEXes
        assert "CREATE MATERIALIZED VIEW" in call_list[0][0][0]
        assert "REFRESH MATERIALIZED VIEW CONCURRENTLY" in call_list[1][0][0]
        assert "CREATE INDEX" in call_list[2][0][0]

    def test_job_passes_params_to_render_select(
        self, mock_db: MagicMock, mv_definitions_yaml: str
    ) -> None:
        """Job passes spec params to query registry render_select."""
        refresh_mv_main(mock_db, mv_definitions_yaml)

        # Verify render_select was called with correct params
        render_calls = mock_db.query_registry.render_select.call_args_list

        assert len(render_calls) == 2

        # First call: retention_by_sector with period=monthly
        assert render_calls[0][0][0] == "retention_by_sector"
        assert render_calls[0][0][1] == {"period": "monthly"}

        # Second call: salary_statistics with year=2024
        assert render_calls[1][0][0] == "salary_statistics"
        assert render_calls[1][0][1] == {"year": "2024"}

    def test_job_handles_single_mv(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        """Job handles single MV in definitions."""
        spec = [
            {
                "name": "mv_single",
                "sql_id": "single_query",
                "params": {},
                "refresh_cron": "0 2 * * *",
                "indexes": ["idx ON mv_single(id)"],
            }
        ]

        yaml_file = tmp_path / "single_mv.yml"
        yaml_file.write_text(yaml.dump(spec))

        refresh_mv_main(mock_db, str(yaml_file))

        # Should have 3 execute_sql calls: CREATE, REFRESH, CREATE INDEX
        assert mock_db.execute_sql.call_count == 3

    def test_job_handles_mv_with_no_indexes(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        """Job handles MV with empty indexes list."""
        spec = [
            {
                "name": "mv_no_indexes",
                "sql_id": "query",
                "params": {},
                "refresh_cron": "0 2 * * *",
                "indexes": [],
            }
        ]

        yaml_file = tmp_path / "no_indexes.yml"
        yaml_file.write_text(yaml.dump(spec))

        refresh_mv_main(mock_db, str(yaml_file))

        # Should have 2 execute_sql calls: CREATE, REFRESH (no indexes)
        assert mock_db.execute_sql.call_count == 2

        # Verify no CREATE INDEX calls
        index_calls = [
            call_args[0][0]
            for call_args in mock_db.execute_sql.call_args_list
            if "CREATE INDEX" in call_args[0][0]
        ]
        assert len(index_calls) == 0
