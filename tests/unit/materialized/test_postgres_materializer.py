"""
Unit tests for PostgreSQL materialized view manager.
"""

from unittest.mock import MagicMock

import pytest

from src.qnwis.data.materialized.postgres import PostgresMaterializer


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock database adapter."""
    mock = MagicMock()
    mock.execute_sql = MagicMock()
    return mock


@pytest.fixture
def materializer(mock_db: MagicMock) -> PostgresMaterializer:
    """PostgresMaterializer with mocked DB."""
    return PostgresMaterializer(mock_db)


class TestPostgresMaterializer:
    """Test PostgreSQL materialized view operations."""

    def test_create_or_replace_calls_create_refresh_index(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """create_or_replace executes CREATE, REFRESH, and CREATE INDEX."""
        sql_select = """
        SELECT sector, AVG(retention_months) as avg_retention
        FROM employees
        GROUP BY sector;
        """
        indexes = [
            "idx_mv_sector ON mv_retention(sector)",
            "idx_mv_retention ON mv_retention(avg_retention)",
        ]

        materializer.create_or_replace("mv_retention", sql_select, indexes)

        # Should call execute_sql 4 times: CREATE MV, REFRESH, CREATE INDEX x2
        assert mock_db.execute_sql.call_count == 4

        calls = mock_db.execute_sql.call_args_list

        # Check CREATE MATERIALIZED VIEW call
        create_call = calls[0][0][0]
        assert "CREATE MATERIALIZED VIEW IF NOT EXISTS mv_retention AS" in create_call
        assert "SELECT sector, AVG(retention_months)" in create_call
        assert "WITH NO DATA" in create_call

        # Check REFRESH call
        refresh_call = calls[1][0][0]
        assert refresh_call == "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_retention;"

        # Check index creation calls
        index_call_1 = calls[2][0][0]
        assert index_call_1 == "CREATE INDEX IF NOT EXISTS idx_mv_sector ON mv_retention(sector);"

        index_call_2 = calls[3][0][0]
        assert index_call_2 == "CREATE INDEX IF NOT EXISTS idx_mv_retention ON mv_retention(avg_retention);"

    def test_refresh_calls_refresh_concurrently(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """refresh executes REFRESH MATERIALIZED VIEW CONCURRENTLY."""
        materializer.refresh("mv_test")

        mock_db.execute_sql.assert_called_once_with(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_test;"
        )

    def test_drop_calls_drop_if_exists(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """drop executes DROP MATERIALIZED VIEW IF EXISTS."""
        materializer.drop("mv_test")

        mock_db.execute_sql.assert_called_once_with(
            "DROP MATERIALIZED VIEW IF EXISTS mv_test;"
        )

    def test_create_strips_trailing_semicolon(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """SQL with trailing semicolon is stripped before CREATE."""
        sql_select = "SELECT * FROM employees;"
        indexes = ["idx ON mv_test(id)"]

        materializer.create_or_replace("mv_test", sql_select, indexes)

        create_call = mock_db.execute_sql.call_args_list[0][0][0]
        # Should not have double semicolons
        assert ";;" not in create_call

    def test_create_with_empty_indexes(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """create_or_replace works with empty index list."""
        sql_select = "SELECT * FROM employees"

        materializer.create_or_replace("mv_test", sql_select, [])

        # Should call execute_sql 2 times: CREATE MV, REFRESH (no indexes)
        assert mock_db.execute_sql.call_count == 2

    def test_invalid_index_format_raises(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """Invalid index format (missing ON) raises ValueError."""
        sql_select = "SELECT * FROM employees"
        invalid_indexes = ["idx_invalid"]  # Missing "ON table(cols)"

        with pytest.raises(ValueError, match="Invalid index definition"):
            materializer.create_or_replace("mv_test", sql_select, invalid_indexes)

    def test_create_handles_multiline_sql(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """create_or_replace handles multiline SQL correctly."""
        sql_select = """
            SELECT
                sector,
                AVG(salary) as avg_salary,
                COUNT(*) as employee_count
            FROM employees
            WHERE status = 'active'
            GROUP BY sector
            ORDER BY avg_salary DESC
        """
        indexes = ["idx_sector ON mv_salary(sector)"]

        materializer.create_or_replace("mv_salary", sql_select, indexes)

        create_call = mock_db.execute_sql.call_args_list[0][0][0]
        assert "SELECT" in create_call
        assert "FROM employees" in create_call
        assert "GROUP BY sector" in create_call

    def test_create_or_replace_calls_in_sequence(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """create_or_replace calls DB operations in correct sequence."""
        sql_select = "SELECT * FROM employees"
        indexes = ["idx1 ON mv_test(col1)", "idx2 ON mv_test(col2)"]

        materializer.create_or_replace("mv_test", sql_select, indexes)

        # Check that calls were made in order
        assert mock_db.execute_sql.call_count == 4

        # Verify each call
        call_list = mock_db.execute_sql.call_args_list

        # First call: CREATE MATERIALIZED VIEW
        assert "CREATE MATERIALIZED VIEW IF NOT EXISTS mv_test AS" in call_list[0][0][0]
        assert "SELECT * FROM employees" in call_list[0][0][0]

        # Second call: REFRESH
        assert call_list[1][0][0] == "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_test;"

        # Third and fourth calls: CREATE INDEX
        assert call_list[2][0][0] == "CREATE INDEX IF NOT EXISTS idx1 ON mv_test(col1);"
        assert call_list[3][0][0] == "CREATE INDEX IF NOT EXISTS idx2 ON mv_test(col2);"

    def test_refresh_with_special_chars_in_name(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """refresh handles MV names with special characters."""
        materializer.refresh("mv_test_2024_q1")

        mock_db.execute_sql.assert_called_once_with(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_test_2024_q1;"
        )

    def test_drop_with_special_chars_in_name(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """drop handles MV names with special characters."""
        materializer.drop("mv_test_2024_q1")

        mock_db.execute_sql.assert_called_once_with(
            "DROP MATERIALIZED VIEW IF EXISTS mv_test_2024_q1;"
        )

    def test_multiple_indexes_created_in_order(
        self, materializer: PostgresMaterializer, mock_db: MagicMock
    ) -> None:
        """Multiple indexes are created in the order specified."""
        sql_select = "SELECT * FROM employees"
        indexes = [
            "idx_a ON mv_test(col_a)",
            "idx_b ON mv_test(col_b)",
            "idx_c ON mv_test(col_c)",
        ]

        materializer.create_or_replace("mv_test", sql_select, indexes)

        # Verify CREATE INDEX calls for each index
        index_calls = mock_db.execute_sql.call_args_list[2:]  # Skip CREATE and REFRESH
        assert len(index_calls) == 3
        assert "idx_a ON mv_test(col_a)" in index_calls[0][0][0]
        assert "idx_b ON mv_test(col_b)" in index_calls[1][0][0]
        assert "idx_c ON mv_test(col_c)" in index_calls[2][0][0]
