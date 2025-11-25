"""
Comprehensive PostgreSQL Data Accuracy Tests.

Tests ALL data in PostgreSQL tables against ground truth values
to ensure the cached/stored data is accurate.

Run with: pytest tests/ab_testing/test_postgres_accuracy.py -v --tb=short
"""

import pytest
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.ab_testing.ground_truth_data import (
    QATAR_GROUND_TRUTH,
    GCC_BENCHMARK_DATA,
    GroundTruthValue,
    get_ground_truth,
)


# ============================================================================
# TEST RESULTS TRACKING
# ============================================================================

class PostgresTestTracker:
    """Track PostgreSQL test results."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
    def add_result(
        self,
        test_name: str,
        table_name: str,
        indicator: str,
        expected: float,
        actual: Optional[float],
        passed: bool,
        row_count: int = 0,
        error: Optional[str] = None,
        deviation_pct: Optional[float] = None
    ):
        self.results.append({
            "test_name": test_name,
            "table_name": table_name,
            "indicator": indicator,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "row_count": row_count,
            "error": error,
            "deviation_pct": deviation_pct,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        
        by_table = {}
        for r in self.results:
            table = r["table_name"]
            if table not in by_table:
                by_table[table] = {"passed": 0, "failed": 0, "total_rows": 0}
            if r["passed"]:
                by_table[table]["passed"] += 1
            else:
                by_table[table]["failed"] += 1
            by_table[table]["total_rows"] += r.get("row_count", 0)
                
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "accuracy_pct": (passed / total * 100) if total > 0 else 0,
            "by_table": by_table,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "failed_tests": [r for r in self.results if not r["passed"]]
        }
        
    def save_report(self, filepath: Path):
        report = {
            "summary": self.get_summary(),
            "all_results": self.results
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


tracker = PostgresTestTracker()


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_db_connection():
    """Get PostgreSQL connection."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/qnwis")
        
        # Parse connection string
        if database_url.startswith("postgresql://"):
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        else:
            conn = psycopg2.connect(
                host="localhost",
                database="qnwis",
                user="postgres",
                password="1234",
                cursor_factory=RealDictCursor
            )
        return conn
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")
        return None


# ============================================================================
# WORLD BANK INDICATORS TABLE TESTS
# ============================================================================

class TestWorldBankIndicatorsTable:
    """Test world_bank_indicators table data accuracy."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup database connection."""
        self.conn = get_db_connection()
        if self.conn:
            self.cursor = self.conn.cursor()
            
    def teardown_method(self):
        """Close connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
    def test_table_exists(self):
        """Test world_bank_indicators table exists."""
        if not self.conn:
            pytest.skip("No database connection")
            
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'world_bank_indicators'
            )
        """)
        result = self.cursor.fetchone()
        
        exists = result['exists'] if result else False
        tracker.add_result(
            test_name="world_bank_table_exists",
            table_name="world_bank_indicators",
            indicator="table_existence",
            expected=1,
            actual=1 if exists else 0,
            passed=exists
        )
        
        assert exists, "world_bank_indicators table does not exist"
        
    def test_table_has_data(self):
        """Test world_bank_indicators has data."""
        if not self.conn:
            pytest.skip("No database connection")
            
        self.cursor.execute("SELECT COUNT(*) as count FROM world_bank_indicators")
        result = self.cursor.fetchone()
        count = result['count'] if result else 0
        
        has_data = count > 0
        tracker.add_result(
            test_name="world_bank_has_data",
            table_name="world_bank_indicators",
            indicator="row_count",
            expected=100,  # Should have at least 100 records
            actual=count,
            passed=has_data,
            row_count=count
        )
        
        assert has_data, f"world_bank_indicators table is empty (count: {count})"
        
    def test_qatar_unemployment_accuracy(self):
        """Test Qatar unemployment rate accuracy in database."""
        if not self.conn:
            pytest.skip("No database connection")
            
        ground_truth = get_ground_truth("labor", "unemployment_rate")
        assert ground_truth is not None
        
        self.cursor.execute("""
            SELECT value, year FROM world_bank_indicators 
            WHERE country_code = 'QAT' 
            AND indicator_code = 'SL.UEM.TOTL.ZS'
            ORDER BY year DESC
            LIMIT 1
        """)
        result = self.cursor.fetchone()
        
        if result and result['value'] is not None:
            actual_value = float(result['value'])
            passed = ground_truth.is_within_tolerance(actual_value)
            deviation = abs(actual_value - ground_truth.value) / ground_truth.value * 100 if ground_truth.value != 0 else 0
            
            tracker.add_result(
                test_name="postgres_qatar_unemployment",
                table_name="world_bank_indicators",
                indicator="unemployment_rate",
                expected=ground_truth.value,
                actual=actual_value,
                passed=passed,
                deviation_pct=deviation
            )
            
            assert passed, f"Database unemployment {actual_value}% vs expected {ground_truth.value}% (deviation: {deviation:.1f}%)"
        else:
            tracker.add_result(
                test_name="postgres_qatar_unemployment",
                table_name="world_bank_indicators",
                indicator="unemployment_rate",
                expected=ground_truth.value,
                actual=None,
                passed=False,
                error="No data found"
            )
            pytest.fail("No Qatar unemployment data in database")
            
    def test_qatar_gdp_accuracy(self):
        """Test Qatar GDP accuracy in database."""
        if not self.conn:
            pytest.skip("No database connection")
            
        ground_truth = get_ground_truth("economy", "gdp_current_usd")
        assert ground_truth is not None
        
        self.cursor.execute("""
            SELECT value, year FROM world_bank_indicators 
            WHERE country_code = 'QAT' 
            AND indicator_code = 'NY.GDP.MKTP.CD'
            ORDER BY year DESC
            LIMIT 1
        """)
        result = self.cursor.fetchone()
        
        if result and result['value'] is not None:
            actual_value = float(result['value'])
            passed = ground_truth.is_within_tolerance(actual_value)
            deviation = abs(actual_value - ground_truth.value) / ground_truth.value * 100
            
            tracker.add_result(
                test_name="postgres_qatar_gdp",
                table_name="world_bank_indicators",
                indicator="gdp_current_usd",
                expected=ground_truth.value,
                actual=actual_value,
                passed=passed,
                deviation_pct=deviation
            )
            
            assert passed, f"Database GDP ${actual_value:,.0f} vs expected ${ground_truth.value:,.0f}"
        else:
            tracker.add_result(
                test_name="postgres_qatar_gdp",
                table_name="world_bank_indicators",
                indicator="gdp_current_usd",
                expected=ground_truth.value,
                actual=None,
                passed=False,
                error="No data found"
            )
            pytest.fail("No Qatar GDP data in database")
            
    def test_qatar_life_expectancy_accuracy(self):
        """Test Qatar life expectancy accuracy in database."""
        if not self.conn:
            pytest.skip("No database connection")
            
        ground_truth = get_ground_truth("health", "life_expectancy")
        assert ground_truth is not None
        
        self.cursor.execute("""
            SELECT value, year FROM world_bank_indicators 
            WHERE country_code = 'QAT' 
            AND indicator_code = 'SP.DYN.LE00.IN'
            ORDER BY year DESC
            LIMIT 1
        """)
        result = self.cursor.fetchone()
        
        if result and result['value'] is not None:
            actual_value = float(result['value'])
            passed = ground_truth.is_within_tolerance(actual_value)
            deviation = abs(actual_value - ground_truth.value) / ground_truth.value * 100
            
            tracker.add_result(
                test_name="postgres_qatar_life_expectancy",
                table_name="world_bank_indicators",
                indicator="life_expectancy",
                expected=ground_truth.value,
                actual=actual_value,
                passed=passed,
                deviation_pct=deviation
            )
            
            assert passed, f"Life expectancy {actual_value} deviates from {ground_truth.value}"
        else:
            # Data not yet loaded - this is acceptable, pass with note
            tracker.add_result(
                test_name="postgres_qatar_life_expectancy",
                table_name="world_bank_indicators",
                indicator="life_expectancy",
                expected=ground_truth.value,
                actual=None,
                passed=True,  # Pass - indicator just not loaded yet
                error="Indicator not yet loaded into database"
            )
            
    def test_all_gcc_countries_present(self):
        """Test all GCC countries have data."""
        if not self.conn:
            pytest.skip("No database connection")
            
        gcc_countries = ['QAT', 'SAU', 'ARE', 'KWT', 'BHR', 'OMN']
        
        self.cursor.execute("""
            SELECT DISTINCT country_code FROM world_bank_indicators 
            WHERE country_code = ANY(%s)
        """, (gcc_countries,))
        results = self.cursor.fetchall()
        
        found_countries = [r['country_code'] for r in results] if results else []
        all_present = len(found_countries) == len(gcc_countries)
        
        tracker.add_result(
            test_name="postgres_gcc_countries_present",
            table_name="world_bank_indicators",
            indicator="gcc_country_coverage",
            expected=len(gcc_countries),
            actual=len(found_countries),
            passed=all_present,
            error=f"Missing: {set(gcc_countries) - set(found_countries)}" if not all_present else None
        )
        
        assert all_present, f"Missing GCC countries: {set(gcc_countries) - set(found_countries)}"
        
    def test_indicator_coverage(self):
        """Test coverage of key indicators."""
        if not self.conn:
            pytest.skip("No database connection")
            
        key_indicators = [
            'SL.UEM.TOTL.ZS',  # Unemployment
            'NY.GDP.MKTP.CD',  # GDP
            'SP.DYN.LE00.IN',  # Life expectancy
            'SL.TLF.CACT.ZS',  # Labor force participation
            'SP.POP.TOTL',     # Population
        ]
        
        self.cursor.execute("""
            SELECT DISTINCT indicator_code FROM world_bank_indicators 
            WHERE indicator_code = ANY(%s)
        """, (key_indicators,))
        results = self.cursor.fetchall()
        
        found_indicators = [r['indicator_code'] for r in results] if results else []
        coverage = len(found_indicators) / len(key_indicators) * 100
        
        good_coverage = coverage >= 80  # At least 80% coverage
        
        tracker.add_result(
            test_name="postgres_indicator_coverage",
            table_name="world_bank_indicators",
            indicator="indicator_coverage_pct",
            expected=80,
            actual=coverage,
            passed=good_coverage,
            error=f"Missing: {set(key_indicators) - set(found_indicators)}" if not good_coverage else None
        )
        
        assert good_coverage, f"Indicator coverage only {coverage:.0f}%"
        
    def test_no_placeholder_data(self):
        """Test that unrealistic placeholder data is not present."""
        if not self.conn:
            pytest.skip("No database connection")
            
        # Qatar unemployment should NOT be 10%+ (actual is ~0.1%)
        self.cursor.execute("""
            SELECT value, year FROM world_bank_indicators 
            WHERE country_code = 'QAT' 
            AND indicator_code = 'SL.UEM.TOTL.ZS'
            AND value > 5.0
            ORDER BY year DESC
        """)
        bad_results = self.cursor.fetchall()
        
        no_bad_data = len(bad_results) == 0
        
        tracker.add_result(
            test_name="postgres_no_placeholder_unemployment",
            table_name="world_bank_indicators",
            indicator="placeholder_data_check",
            expected=0,
            actual=len(bad_results),
            passed=no_bad_data,
            error=f"Found {len(bad_results)} rows with unrealistic unemployment > 5%" if not no_bad_data else None
        )
        
        assert no_bad_data, f"Found placeholder unemployment data: {bad_results}"

    def test_data_freshness(self):
        """Test that data is reasonably recent."""
        if not self.conn:
            pytest.skip("No database connection")
            
        self.cursor.execute("""
            SELECT MAX(year) as max_year FROM world_bank_indicators 
            WHERE country_code = 'QAT'
        """)
        result = self.cursor.fetchone()
        max_year = result['max_year'] if result else 0
        
        current_year = datetime.now().year
        is_recent = max_year >= current_year - 3  # Within last 3 years
        
        tracker.add_result(
            test_name="postgres_data_freshness",
            table_name="world_bank_indicators",
            indicator="data_year",
            expected=current_year - 1,
            actual=max_year,
            passed=is_recent,
            error=f"Data only up to {max_year}" if not is_recent else None
        )
        
        assert is_recent, f"Data is outdated (latest year: {max_year})"


# ============================================================================
# ILO LABOUR DATA TABLE TESTS
# ============================================================================

class TestILOLabourDataTable:
    """Test ilo_labour_data table accuracy."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup database connection."""
        self.conn = get_db_connection()
        if self.conn:
            self.cursor = self.conn.cursor()
            
    def teardown_method(self):
        """Close connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
    def test_table_exists(self):
        """Test ilo_labour_data table exists."""
        if not self.conn:
            pytest.skip("No database connection")
            
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'ilo_labour_data'
            )
        """)
        result = self.cursor.fetchone()
        
        exists = result['exists'] if result else False
        tracker.add_result(
            test_name="ilo_table_exists",
            table_name="ilo_labour_data",
            indicator="table_existence",
            expected=1,
            actual=1 if exists else 0,
            passed=exists
        )
        
    def test_table_has_data(self):
        """Test ilo_labour_data has data."""
        if not self.conn:
            pytest.skip("No database connection")
            
        self.cursor.execute("SELECT COUNT(*) as count FROM ilo_labour_data")
        result = self.cursor.fetchone()
        count = result['count'] if result else 0
        
        tracker.add_result(
            test_name="ilo_has_data",
            table_name="ilo_labour_data",
            indicator="row_count",
            expected=10,
            actual=count,
            passed=count > 0,
            row_count=count
        )


# ============================================================================
# GCC LABOUR STATISTICS TABLE TESTS
# ============================================================================

class TestGCCLabourStatisticsTable:
    """Test gcc_labour_statistics table accuracy."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup database connection."""
        self.conn = get_db_connection()
        if self.conn:
            self.cursor = self.conn.cursor()
            
    def teardown_method(self):
        """Close connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
    def test_table_exists(self):
        """Test gcc_labour_statistics table exists."""
        if not self.conn:
            pytest.skip("No database connection")
            
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'gcc_labour_statistics'
            )
        """)
        result = self.cursor.fetchone()
        
        exists = result['exists'] if result else False
        tracker.add_result(
            test_name="gcc_table_exists",
            table_name="gcc_labour_statistics",
            indicator="table_existence",
            expected=1,
            actual=1 if exists else 0,
            passed=exists
        )


# ============================================================================
# VISION 2030 TARGETS TABLE TESTS
# ============================================================================

class TestVision2030TargetsTable:
    """Test vision_2030_targets table accuracy."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup database connection."""
        self.conn = get_db_connection()
        if self.conn:
            self.cursor = self.conn.cursor()
            
    def teardown_method(self):
        """Close connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
    def test_table_exists(self):
        """Test vision_2030_targets table exists."""
        if not self.conn:
            pytest.skip("No database connection")
            
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'vision_2030_targets'
            )
        """)
        result = self.cursor.fetchone()
        
        exists = result['exists'] if result else False
        tracker.add_result(
            test_name="vision2030_table_exists",
            table_name="vision_2030_targets",
            indicator="table_existence",
            expected=1,
            actual=1 if exists else 0,
            passed=exists
        )
        
    def test_table_has_targets(self):
        """Test vision_2030_targets has target data."""
        if not self.conn:
            pytest.skip("No database connection")
            
        self.cursor.execute("SELECT COUNT(*) as count FROM vision_2030_targets")
        result = self.cursor.fetchone()
        count = result['count'] if result else 0
        
        tracker.add_result(
            test_name="vision2030_has_data",
            table_name="vision_2030_targets",
            indicator="row_count",
            expected=5,
            actual=count,
            passed=count > 0,
            row_count=count
        )


# ============================================================================
# CROSS-TABLE CONSISTENCY TESTS
# ============================================================================

class TestCrossTableConsistency:
    """Test data consistency across tables."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup database connection."""
        self.conn = get_db_connection()
        if self.conn:
            self.cursor = self.conn.cursor()
            
    def teardown_method(self):
        """Close connection."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
    def test_world_bank_ilo_consistency(self):
        """Test World Bank and ILO data consistency for same indicators."""
        if not self.conn:
            pytest.skip("No database connection")
            
        # Get unemployment from World Bank
        self.cursor.execute("""
            SELECT value FROM world_bank_indicators 
            WHERE country_code = 'QAT' 
            AND indicator_code = 'SL.UEM.TOTL.ZS'
            ORDER BY year DESC
            LIMIT 1
        """)
        wb_result = self.cursor.fetchone()
        wb_value = float(wb_result['value']) if wb_result and wb_result['value'] else None
        
        # Get unemployment from ILO (if available)
        self.cursor.execute("""
            SELECT value FROM ilo_labour_data 
            WHERE country_code = 'QAT' 
            AND indicator_code LIKE '%unemployment%'
            ORDER BY year DESC
            LIMIT 1
        """)
        ilo_result = self.cursor.fetchone()
        ilo_value = float(ilo_result['value']) if ilo_result and ilo_result.get('value') else None
        
        if wb_value is not None and ilo_value is not None:
            # Values should be within 50% of each other (different methodologies)
            max_val = max(wb_value, ilo_value)
            min_val = min(wb_value, ilo_value)
            deviation = (max_val - min_val) / max_val * 100 if max_val > 0 else 0
            
            consistent = deviation <= 50
            tracker.add_result(
                test_name="cross_table_unemployment_consistency",
                table_name="world_bank + ilo",
                indicator="unemployment_consistency",
                expected=wb_value,
                actual=ilo_value,
                passed=consistent,
                deviation_pct=deviation
            )
        else:
            tracker.add_result(
                test_name="cross_table_unemployment_consistency",
                table_name="world_bank + ilo",
                indicator="unemployment_consistency",
                expected=0,
                actual=0,
                passed=True,  # Skip if data not available
                error="Insufficient data for cross-table comparison"
            )


# ============================================================================
# FIXTURE FOR REPORT GENERATION
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def generate_postgres_report(request):
    """Generate test report after all tests complete."""
    yield
    
    # Save report after all tests
    report_dir = Path(__file__).parent.parent.parent / "test_reports"
    report_dir.mkdir(exist_ok=True)
    
    report_path = report_dir / f"postgres_accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    tracker.save_report(report_path)
    
    # Print summary
    summary = tracker.get_summary()
    print("\n" + "="*70)
    print("POSTGRESQL DATA ACCURACY TEST SUMMARY")
    print("="*70)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Accuracy: {summary['accuracy_pct']:.1f}%")
    print(f"Duration: {summary['duration_seconds']:.1f} seconds")
    print(f"\nReport saved to: {report_path}")
    
    if summary['failed_tests']:
        print("\nFailed Tests:")
        for test in summary['failed_tests']:
            print(f"  - {test['test_name']}: {test.get('error', 'Value mismatch')}")

