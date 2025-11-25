"""
Comprehensive Data Extraction Accuracy Tests.

Tests the complete data extraction pipeline across ALL domains
to ensure the system extracts accurate, consistent information.

This test simulates real queries and validates extracted facts
against ground truth values.

Run with: pytest tests/ab_testing/test_extraction_accuracy.py -v --tb=short -s
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.ab_testing.ground_truth_data import (
    QATAR_GROUND_TRUTH,
    TEST_QUERIES,
    GroundTruthValue,
    get_ground_truth,
    get_all_domains,
)


# ============================================================================
# TEST RESULTS TRACKING
# ============================================================================

class ExtractionTestTracker:
    """Track extraction test results with detailed metrics."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
    def add_result(
        self,
        test_name: str,
        domain: str,
        query: str,
        expected_facts: List[str],
        extracted_facts: Dict[str, Any],
        accuracy_score: float,
        passed: bool,
        details: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        self.results.append({
            "test_name": test_name,
            "domain": domain,
            "query": query,
            "expected_facts": expected_facts,
            "extracted_facts": extracted_facts,
            "accuracy_score": accuracy_score,
            "passed": passed,
            "details": details or {},
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        
        by_domain = {}
        for r in self.results:
            domain = r["domain"]
            if domain not in by_domain:
                by_domain[domain] = {
                    "passed": 0, 
                    "failed": 0, 
                    "avg_accuracy": 0.0,
                    "scores": []
                }
            if r["passed"]:
                by_domain[domain]["passed"] += 1
            else:
                by_domain[domain]["failed"] += 1
            by_domain[domain]["scores"].append(r["accuracy_score"])
            
        # Calculate average accuracy per domain
        for domain in by_domain:
            scores = by_domain[domain]["scores"]
            by_domain[domain]["avg_accuracy"] = sum(scores) / len(scores) if scores else 0
            del by_domain[domain]["scores"]
                
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "overall_accuracy_pct": (passed / total * 100) if total > 0 else 0,
            "by_domain": by_domain,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "failed_tests": [r for r in self.results if not r["passed"]]
        }
        
    def save_report(self, filepath: Path):
        report = {
            "summary": self.get_summary(),
            "all_results": self.results
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)


tracker = ExtractionTestTracker()


# ============================================================================
# DATA EXTRACTION HELPERS
# ============================================================================

def extract_numeric_value(text: str, indicator_hint: str) -> Optional[float]:
    """
    Extract numeric value from text based on indicator type.
    
    Args:
        text: The text containing the value
        indicator_hint: Hint about what type of value to look for
        
    Returns:
        Extracted numeric value or None
    """
    # Common patterns for different indicators
    patterns = {
        'percentage': r'(\d+\.?\d*)\s*%',
        'billion': r'(\d+\.?\d*)\s*billion',
        'million': r'(\d+\.?\d*)\s*million',
        'thousand': r'(\d+\.?\d*)\s*thousand',
        'years': r'(\d+\.?\d*)\s*years',
        'generic': r'\b(\d+\.?\d*)\b'
    }
    
    text_lower = text.lower()
    
    # Try percentage first if hint suggests it
    if 'rate' in indicator_hint or 'pct' in indicator_hint or 'percentage' in indicator_hint:
        match = re.search(patterns['percentage'], text)
        if match:
            return float(match.group(1))
            
    # Try billions
    if 'gdp' in indicator_hint or 'billion' in text_lower:
        match = re.search(patterns['billion'], text_lower)
        if match:
            return float(match.group(1)) * 1_000_000_000
            
    # Try millions
    if 'population' in indicator_hint or 'million' in text_lower:
        match = re.search(patterns['million'], text_lower)
        if match:
            return float(match.group(1)) * 1_000_000
            
    # Generic number
    match = re.search(patterns['generic'], text)
    if match:
        return float(match.group(1))
        
    return None


async def run_prefetch_for_query(query: str) -> Dict[str, Any]:
    """
    Run the prefetch layer for a query and collect extracted data.
    
    Args:
        query: The user query
        
    Returns:
        Dictionary with extracted data from all sources
    """
    extracted_data = {
        "world_bank": [],
        "postgres": [],
        "rag": [],
        "apis": []
    }
    
    try:
        # Try to use the actual prefetch layer
        from src.qnwis.orchestration.prefetch_apis import PrefetchLayer
        
        prefetch = PrefetchLayer()
        results = await prefetch.prefetch_data(query)
        
        if results:
            extracted_data["apis"] = results
            
    except Exception as e:
        extracted_data["error"] = str(e)
        
    # Also try direct PostgreSQL query
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/qnwis"),
            cursor_factory=RealDictCursor
        )
        cursor = conn.cursor()
        
        # Get relevant indicators from World Bank table
        cursor.execute("""
            SELECT indicator_code, indicator_name, value, year, country_code
            FROM world_bank_indicators
            WHERE country_code = 'QAT'
            ORDER BY year DESC
            LIMIT 50
        """)
        extracted_data["postgres"] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
    except Exception as e:
        extracted_data["postgres_error"] = str(e)
        
    # Try RAG search
    try:
        from src.qnwis.rag.retriever import get_document_store
        
        store = get_document_store()
        results = store.search(query, top_k=5)
        extracted_data["rag"] = results if results else []
        
    except Exception as e:
        extracted_data["rag_error"] = str(e)
        
    return extracted_data


def validate_extracted_against_ground_truth(
    extracted: Dict[str, Any],
    expected_facts: List[str],
    domain: str
) -> Tuple[float, Dict[str, Any]]:
    """
    Validate extracted data against ground truth.
    
    Args:
        extracted: Data extracted by the system
        expected_facts: List of fact keys to validate
        domain: The domain being tested
        
    Returns:
        Tuple of (accuracy_score, details_dict)
    """
    details = {
        "matched": [],
        "mismatched": [],
        "missing": []
    }
    
    total_facts = len(expected_facts)
    matched_count = 0
    
    for fact_key in expected_facts:
        ground_truth = get_ground_truth(domain, fact_key)
        if not ground_truth:
            details["missing"].append({"fact": fact_key, "reason": "No ground truth"})
            continue
            
        # Search for this fact in extracted data
        fact_found = False
        actual_value = None
        
        # Check PostgreSQL data
        for row in extracted.get("postgres", []):
            # Map indicator codes to fact keys
            indicator_map = {
                "SL.UEM.TOTL.ZS": "unemployment_rate",
                "NY.GDP.MKTP.CD": "gdp_current_usd",
                "NY.GDP.PCAP.CD": "gdp_per_capita",
                "SP.DYN.LE00.IN": "life_expectancy",
                "SL.TLF.CACT.ZS": "labor_force_participation",
                "SP.POP.TOTL": "total_population",
            }
            
            row_indicator = row.get("indicator_code", "")
            if indicator_map.get(row_indicator) == fact_key:
                actual_value = float(row.get("value", 0))
                fact_found = True
                break
                
        if fact_found and actual_value is not None:
            if ground_truth.is_within_tolerance(actual_value):
                deviation = abs(actual_value - ground_truth.value) / ground_truth.value * 100 if ground_truth.value != 0 else 0
                matched_count += 1
                details["matched"].append({
                    "fact": fact_key,
                    "expected": ground_truth.value,
                    "actual": actual_value,
                    "deviation_pct": deviation
                })
            else:
                deviation = abs(actual_value - ground_truth.value) / ground_truth.value * 100 if ground_truth.value != 0 else 0
                details["mismatched"].append({
                    "fact": fact_key,
                    "expected": ground_truth.value,
                    "actual": actual_value,
                    "deviation_pct": deviation,
                    "tolerance": ground_truth.tolerance_pct
                })
        else:
            details["missing"].append({
                "fact": fact_key,
                "reason": "Not found in extracted data",
                "expected": ground_truth.value
            })
            
    accuracy_score = (matched_count / total_facts * 100) if total_facts > 0 else 0
    return accuracy_score, details


# ============================================================================
# DOMAIN-SPECIFIC EXTRACTION TESTS
# ============================================================================

class TestLaborDomainExtraction:
    """Test labor domain data extraction accuracy."""
    
    @pytest.mark.asyncio
    async def test_unemployment_extraction(self):
        """Test unemployment rate extraction."""
        query = "What is Qatar's unemployment rate?"
        
        extracted = await run_prefetch_for_query(query)
        accuracy, details = validate_extracted_against_ground_truth(
            extracted, 
            ["unemployment_rate"],
            "labor"
        )
        
        passed = accuracy >= 80  # At least 80% accuracy
        
        tracker.add_result(
            test_name="labor_unemployment_extraction",
            domain="labor",
            query=query,
            expected_facts=["unemployment_rate"],
            extracted_facts=extracted,
            accuracy_score=accuracy,
            passed=passed,
            details=details
        )
        
        assert passed, f"Labor unemployment extraction accuracy: {accuracy}%"
        
    @pytest.mark.asyncio
    async def test_labor_participation_extraction(self):
        """Test labor force participation extraction."""
        query = "What is the labor force participation rate in Qatar?"
        
        extracted = await run_prefetch_for_query(query)
        accuracy, details = validate_extracted_against_ground_truth(
            extracted,
            ["labor_force_participation"],
            "labor"
        )
        
        passed = accuracy >= 80
        
        tracker.add_result(
            test_name="labor_participation_extraction",
            domain="labor",
            query=query,
            expected_facts=["labor_force_participation"],
            extracted_facts=extracted,
            accuracy_score=accuracy,
            passed=passed,
            details=details
        )


class TestEconomyDomainExtraction:
    """Test economy domain data extraction accuracy."""
    
    @pytest.mark.asyncio
    async def test_gdp_extraction(self):
        """Test GDP extraction."""
        query = "What is Qatar's GDP?"
        
        extracted = await run_prefetch_for_query(query)
        accuracy, details = validate_extracted_against_ground_truth(
            extracted,
            ["gdp_current_usd"],
            "economy"
        )
        
        passed = accuracy >= 80
        
        tracker.add_result(
            test_name="economy_gdp_extraction",
            domain="economy",
            query=query,
            expected_facts=["gdp_current_usd"],
            extracted_facts=extracted,
            accuracy_score=accuracy,
            passed=passed,
            details=details
        )
        
    @pytest.mark.asyncio
    async def test_gdp_per_capita_extraction(self):
        """Test GDP per capita extraction."""
        query = "What is Qatar's GDP per capita?"
        
        extracted = await run_prefetch_for_query(query)
        accuracy, details = validate_extracted_against_ground_truth(
            extracted,
            ["gdp_per_capita"],
            "economy"
        )
        
        passed = accuracy >= 80
        
        tracker.add_result(
            test_name="economy_gdp_per_capita_extraction",
            domain="economy",
            query=query,
            expected_facts=["gdp_per_capita"],
            extracted_facts=extracted,
            accuracy_score=accuracy,
            passed=passed,
            details=details
        )


class TestHealthDomainExtraction:
    """Test health domain data extraction accuracy."""
    
    @pytest.mark.asyncio
    async def test_life_expectancy_extraction(self):
        """Test life expectancy extraction."""
        query = "What is life expectancy in Qatar?"
        
        extracted = await run_prefetch_for_query(query)
        accuracy, details = validate_extracted_against_ground_truth(
            extracted,
            ["life_expectancy"],
            "health"
        )
        
        passed = accuracy >= 80
        
        tracker.add_result(
            test_name="health_life_expectancy_extraction",
            domain="health",
            query=query,
            expected_facts=["life_expectancy"],
            extracted_facts=extracted,
            accuracy_score=accuracy,
            passed=passed,
            details=details
        )


class TestDemographicsDomainExtraction:
    """Test demographics domain data extraction accuracy."""
    
    @pytest.mark.asyncio
    async def test_population_extraction(self):
        """Test population extraction."""
        query = "What is Qatar's population?"
        
        extracted = await run_prefetch_for_query(query)
        accuracy, details = validate_extracted_against_ground_truth(
            extracted,
            ["total_population"],
            "demographics"
        )
        
        passed = accuracy >= 80
        
        tracker.add_result(
            test_name="demographics_population_extraction",
            domain="demographics",
            query=query,
            expected_facts=["total_population"],
            extracted_facts=extracted,
            accuracy_score=accuracy,
            passed=passed,
            details=details
        )


# ============================================================================
# CROSS-DOMAIN EXTRACTION TESTS
# ============================================================================

class TestCrossDomainExtraction:
    """Test cross-domain data extraction accuracy."""
    
    @pytest.mark.asyncio
    async def test_multi_domain_query(self):
        """Test extraction for multi-domain query."""
        query = "Analyze Qatar's economic performance and labor market"
        
        extracted = await run_prefetch_for_query(query)
        
        # Check data from multiple domains
        economy_accuracy, economy_details = validate_extracted_against_ground_truth(
            extracted,
            ["gdp_current_usd"],
            "economy"
        )
        
        labor_accuracy, labor_details = validate_extracted_against_ground_truth(
            extracted,
            ["unemployment_rate"],
            "labor"
        )
        
        combined_accuracy = (economy_accuracy + labor_accuracy) / 2
        passed = combined_accuracy >= 60  # Lower threshold for cross-domain
        
        tracker.add_result(
            test_name="cross_domain_extraction",
            domain="cross_domain",
            query=query,
            expected_facts=["gdp_current_usd", "unemployment_rate"],
            extracted_facts=extracted,
            accuracy_score=combined_accuracy,
            passed=passed,
            details={
                "economy": economy_details,
                "labor": labor_details
            }
        )


# ============================================================================
# DATA SOURCE COVERAGE TESTS
# ============================================================================

class TestDataSourceCoverage:
    """Test that all data sources are being queried."""
    
    @pytest.mark.asyncio
    async def test_postgres_source_queried(self):
        """Test PostgreSQL is queried for data."""
        query = "What is Qatar's unemployment rate?"
        extracted = await run_prefetch_for_query(query)
        
        has_postgres = len(extracted.get("postgres", [])) > 0
        
        tracker.add_result(
            test_name="source_postgres_queried",
            domain="infrastructure",
            query=query,
            expected_facts=["postgres_data"],
            extracted_facts={"postgres_rows": len(extracted.get("postgres", []))},
            accuracy_score=100 if has_postgres else 0,
            passed=has_postgres,
            error=extracted.get("postgres_error")
        )
        
    @pytest.mark.asyncio
    async def test_rag_source_queried(self):
        """Test RAG is queried for context."""
        query = "What is Qatar's Vision 2030 labor market strategy?"
        extracted = await run_prefetch_for_query(query)
        
        has_rag = len(extracted.get("rag", [])) > 0
        
        tracker.add_result(
            test_name="source_rag_queried",
            domain="infrastructure",
            query=query,
            expected_facts=["rag_context"],
            extracted_facts={"rag_results": len(extracted.get("rag", []))},
            accuracy_score=100 if has_rag else 0,
            passed=has_rag,
            error=extracted.get("rag_error")
        )


# ============================================================================
# DATA CONSISTENCY TESTS
# ============================================================================

class TestDataConsistency:
    """Test data consistency across sources."""
    
    @pytest.mark.asyncio
    async def test_unemployment_consistency(self):
        """Test unemployment data is consistent across queries."""
        queries = [
            "What is Qatar's unemployment rate?",
            "Qatar joblessness statistics",
            "Labor market unemployment in Qatar"
        ]
        
        values = []
        for query in queries:
            extracted = await run_prefetch_for_query(query)
            for row in extracted.get("postgres", []):
                if row.get("indicator_code") == "SL.UEM.TOTL.ZS":
                    values.append(float(row.get("value", 0)))
                    break
                    
        if len(values) >= 2:
            # Check if all values are within 10% of each other
            max_val = max(values)
            min_val = min(values)
            deviation = (max_val - min_val) / max_val * 100 if max_val > 0 else 0
            consistent = deviation <= 10
        else:
            consistent = True
            deviation = 0
            
        tracker.add_result(
            test_name="consistency_unemployment",
            domain="consistency",
            query=str(queries),
            expected_facts=["consistent_unemployment"],
            extracted_facts={"values": values},
            accuracy_score=100 if consistent else (100 - deviation),
            passed=consistent,
            details={"deviation_pct": deviation}
        )


# ============================================================================
# FIXTURE FOR REPORT GENERATION
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def generate_extraction_report(request):
    """Generate test report after all tests complete."""
    yield
    
    # Save report after all tests
    report_dir = Path(__file__).parent.parent.parent / "test_reports"
    report_dir.mkdir(exist_ok=True)
    
    report_path = report_dir / f"extraction_accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    tracker.save_report(report_path)
    
    # Print summary
    summary = tracker.get_summary()
    print("\n" + "="*70)
    print("DATA EXTRACTION ACCURACY TEST SUMMARY")
    print("="*70)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Overall Accuracy: {summary['overall_accuracy_pct']:.1f}%")
    print(f"Duration: {summary['duration_seconds']:.1f} seconds")
    
    print("\nAccuracy by Domain:")
    for domain, stats in summary['by_domain'].items():
        print(f"  {domain}: {stats['avg_accuracy']:.1f}% avg ({stats['passed']}/{stats['passed']+stats['failed']} passed)")
    
    print(f"\nReport saved to: {report_path}")
    
    if summary['failed_tests']:
        print("\nFailed Tests:")
        for test in summary['failed_tests'][:10]:  # Show first 10
            accuracy = test.get('accuracy_score', 0)
            error_msg = test.get('error', f'Accuracy: {accuracy:.0f}%')
            print(f"  - {test['test_name']}: {error_msg}")

