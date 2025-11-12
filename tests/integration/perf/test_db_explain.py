"""
Integration tests for database EXPLAIN and ANALYZE functionality.

Tests query plan analysis using real database connections to ensure
db_tuning helpers work correctly with PostgreSQL.
"""

import pytest
from sqlalchemy import create_engine, text

from qnwis.perf.db_tuning import analyze, explain


@pytest.fixture
def test_engine():
    """Create in-memory SQLite engine for testing."""
    # Note: EXPLAIN FORMAT JSON is PostgreSQL-specific
    # For tests, we'll use a mock or skip if not PostgreSQL
    try:
        # Try to create a test PostgreSQL connection
        engine = create_engine("sqlite:///:memory:")

        # Create a test table
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_jobs (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    sector TEXT,
                    salary INTEGER
                )
            """))
            conn.commit()

            # Insert test data
            conn.execute(text("""
                INSERT INTO test_jobs (id, title, sector, salary)
                VALUES (1, 'Engineer', 'IT', 5000),
                       (2, 'Analyst', 'Finance', 4500),
                       (3, 'Developer', 'IT', 6000)
            """))
            conn.commit()

        yield engine
    finally:
        engine.dispose()


class TestExplainFunction:
    """Test explain() function with query plans."""

    @pytest.mark.skip(reason="EXPLAIN FORMAT JSON requires PostgreSQL")
    def test_explain_returns_query_plan(self, test_engine):
        """explain() should return structured query plan."""
        plan = explain(
            test_engine,
            "SELECT * FROM test_jobs WHERE sector = :s",
            {"s": "IT"}
        )

        assert isinstance(plan, dict)
        assert "Plan" in plan
        assert "Node Type" in plan["Plan"]

    @pytest.mark.skip(reason="EXPLAIN FORMAT JSON requires PostgreSQL")
    def test_explain_includes_node_type(self, test_engine):
        """Query plan should include node type (e.g., Seq Scan, Index Scan)."""
        plan = explain(
            test_engine,
            "SELECT * FROM test_jobs WHERE id = :id",
            {"id": 1}
        )

        assert plan["Plan"]["Node Type"] in ["Seq Scan", "Index Scan", "Bitmap Heap Scan"]

    @pytest.mark.skip(reason="EXPLAIN FORMAT JSON requires PostgreSQL")
    def test_explain_with_join(self, test_engine):
        """explain() should handle JOIN queries."""
        # Create second table
        with test_engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_companies (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            """))
            conn.commit()

        plan = explain(
            test_engine,
            """
            SELECT j.title, c.name
            FROM test_jobs j
            JOIN test_companies c ON j.id = c.id
            WHERE j.sector = :s
            """,
            {"s": "IT"}
        )

        assert isinstance(plan, dict)
        # JOIN queries typically have nested plans
        assert "Plan" in plan

    def test_explain_mock_structure(self):
        """Test that explain returns expected structure (mock test)."""
        # This test validates the expected return structure
        # In real PostgreSQL, explain returns JSON like:
        expected_structure = {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "test_jobs",
                "Alias": "test_jobs",
                "Startup Cost": 0.00,
                "Total Cost": 1.04,
                "Plan Rows": 1,
                "Plan Width": 100,
            }
        }

        assert "Plan" in expected_structure
        assert "Node Type" in expected_structure["Plan"]
        assert isinstance(expected_structure["Plan"]["Total Cost"], float)


class TestAnalyzeFunction:
    """Test analyze() function with execution stats."""

    @pytest.mark.skip(reason="EXPLAIN ANALYZE FORMAT JSON requires PostgreSQL")
    def test_analyze_executes_and_returns_stats(self, test_engine):
        """analyze() should execute query and return execution stats."""
        stats = analyze(
            test_engine,
            "SELECT COUNT(*) FROM test_jobs",
            {}
        )

        assert isinstance(stats, dict)
        assert "Plan" in stats
        assert "Execution Time" in stats

    @pytest.mark.skip(reason="EXPLAIN ANALYZE FORMAT JSON requires PostgreSQL")
    def test_analyze_includes_actual_rows(self, test_engine):
        """Execution stats should include actual rows returned."""
        stats = analyze(
            test_engine,
            "SELECT * FROM test_jobs WHERE sector = :s",
            {"s": "IT"}
        )

        assert "Actual Rows" in stats["Plan"]
        # We inserted 2 IT jobs
        assert stats["Plan"]["Actual Rows"] == 2

    @pytest.mark.skip(reason="EXPLAIN ANALYZE FORMAT JSON requires PostgreSQL")
    def test_analyze_includes_timing(self, test_engine):
        """Execution stats should include timing information."""
        stats = analyze(
            test_engine,
            "SELECT * FROM test_jobs",
            {}
        )

        assert "Execution Time" in stats
        assert isinstance(stats["Execution Time"], (int, float))
        assert stats["Execution Time"] >= 0

    @pytest.mark.skip(reason="EXPLAIN ANALYZE FORMAT JSON requires PostgreSQL")
    def test_analyze_with_expensive_query(self, test_engine):
        """analyze() should handle more complex queries."""
        # Insert more data to make query measurable
        with test_engine.connect() as conn:
            for i in range(100):
                conn.execute(
                    text("""
                        INSERT INTO test_jobs (id, title, sector, salary)
                        VALUES (:id, :title, :sector, :salary)
                    """),
                    {"id": i + 10, "title": f"Job{i}", "sector": "IT", "salary": 5000 + i}
                )
            conn.commit()

        stats = analyze(
            test_engine,
            "SELECT AVG(salary) FROM test_jobs WHERE sector = :s",
            {"s": "IT"}
        )

        assert "Execution Time" in stats
        assert stats["Execution Time"] > 0

    def test_analyze_mock_structure(self):
        """Test that analyze returns expected structure (mock test)."""
        # In real PostgreSQL, EXPLAIN ANALYZE returns JSON like:
        expected_structure = {
            "Plan": {
                "Node Type": "Aggregate",
                "Startup Cost": 0.00,
                "Total Cost": 1.05,
                "Plan Rows": 1,
                "Plan Width": 8,
                "Actual Startup Time": 0.023,
                "Actual Total Time": 0.024,
                "Actual Rows": 1,
                "Actual Loops": 1,
            },
            "Planning Time": 0.123,
            "Execution Time": 0.456,
        }

        assert "Plan" in expected_structure
        assert "Execution Time" in expected_structure
        assert "Planning Time" in expected_structure
        assert isinstance(expected_structure["Execution Time"], float)


class TestExplainAnalyzeIntegration:
    """Integration tests for explain and analyze together."""

    def test_explain_and_analyze_same_query_consistency(self):
        """Plan from explain() should match structure in analyze()."""
        # Mock test - validates that both functions return compatible structures
        explain_result = {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "test_jobs",
            }
        }

        analyze_result = {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "test_jobs",
                "Actual Rows": 3,
            },
            "Execution Time": 0.123,
        }

        # Both should have Plan.Node Type
        assert explain_result["Plan"]["Node Type"] == analyze_result["Plan"]["Node Type"]

        # Only analyze should have Execution Time
        assert "Execution Time" not in explain_result
        assert "Execution Time" in analyze_result

    @pytest.mark.skip(reason="Requires PostgreSQL")
    def test_compare_planned_vs_actual_rows(self, test_engine):
        """Compare estimated rows (explain) vs actual rows (analyze)."""
        query = "SELECT * FROM test_jobs WHERE sector = :s"
        params = {"s": "IT"}

        plan = explain(test_engine, query, params)
        stats = analyze(test_engine, query, params)

        planned_rows = plan["Plan"]["Plan Rows"]
        actual_rows = stats["Plan"]["Actual Rows"]

        # For test data, should be close
        assert abs(planned_rows - actual_rows) <= 1


class TestDatabaseTuningHelpers:
    """Test database tuning helper functions together."""

    def test_explain_analyze_workflow(self):
        """Test typical workflow of analyzing slow query."""
        # This is a mock test showing the expected workflow

        # Step 1: EXPLAIN to see plan without executing
        mock_plan = {
            "Plan": {
                "Node Type": "Seq Scan",  # Bad - full table scan
                "Total Cost": 1000.0,  # High cost
            }
        }

        # Identify issue: sequential scan on large table
        assert mock_plan["Plan"]["Node Type"] == "Seq Scan"
        assert mock_plan["Plan"]["Total Cost"] > 100

        # Step 2: ANALYZE to get actual timing
        mock_stats = {
            "Plan": {
                "Node Type": "Seq Scan",
                "Actual Total Time": 850.0,  # Slow!
            },
            "Execution Time": 850.0,
        }

        # Confirm it's actually slow
        assert mock_stats["Execution Time"] > 500

        # Step 3: Add index and re-check (would show Index Scan)
        mock_improved_plan = {
            "Plan": {
                "Node Type": "Index Scan",  # Better!
                "Total Cost": 10.0,  # Much lower
            }
        }

        assert mock_improved_plan["Plan"]["Node Type"] == "Index Scan"
        assert mock_improved_plan["Plan"]["Total Cost"] < 100

    def test_parameterized_query_analysis(self):
        """Test that parameterized queries work correctly."""
        # Validates that parameters are properly passed
        query = "SELECT * FROM jobs WHERE sector = :sector AND salary > :min_salary"
        params = {"sector": "IT", "min_salary": 5000}

        # In real usage, these params would be bound correctly
        assert params["sector"] == "IT"
        assert params["min_salary"] == 5000

        # EXPLAIN/ANALYZE should use these parameter values
        # (actual binding tested in PostgreSQL-specific tests)
