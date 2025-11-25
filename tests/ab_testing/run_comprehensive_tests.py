"""
Master Test Runner for Comprehensive A/B Data Accuracy Testing.

This script runs ALL accuracy tests across:
- APIs (World Bank, ADP, ESCWA, ILO, IMF, GCC-STAT)
- PostgreSQL database
- Knowledge Graph
- RAG Document Store
- Data Extraction Pipeline
- Cross-domain queries

Usage:
    python tests/ab_testing/run_comprehensive_tests.py [--quick] [--domain DOMAIN]

Options:
    --quick     Run quick smoke tests only (faster)
    --domain    Test specific domain only (labor, economy, health, etc.)
    --verbose   Show detailed output
    --report    Generate HTML report

Expected Duration: 30-60 minutes for full test suite
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import subprocess


# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ComprehensiveTestRunner:
    """
    Orchestrates all accuracy tests and generates comprehensive reports.
    """
    
    def __init__(self, quick_mode: bool = False, domain_filter: str = None, verbose: bool = False):
        self.quick_mode = quick_mode
        self.domain_filter = domain_filter
        self.verbose = verbose
        self.start_time = datetime.now()
        self.results: Dict[str, Any] = {
            "metadata": {
                "start_time": self.start_time.isoformat(),
                "quick_mode": quick_mode,
                "domain_filter": domain_filter
            },
            "test_suites": {},
            "overall_summary": {}
        }
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "[*]",
            "SUCCESS": "[+]",
            "ERROR": "[-]",
            "WARNING": "[!]"
        }.get(level, "[*]")
        print(f"{timestamp} {prefix} {message}")
        
    def run_pytest_suite(self, test_file: str, suite_name: str) -> Dict[str, Any]:
        """
        Run a pytest test suite and collect results.
        
        Args:
            test_file: Path to test file
            suite_name: Name of the test suite
            
        Returns:
            Dictionary with test results
        """
        self.log(f"Running {suite_name}...")
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            "-q",
            "--no-header"
        ]
        
        if self.quick_mode:
            cmd.extend(["-x", "--timeout=60"])  # Stop on first failure, 60s timeout
            
        # Run pytest
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
                cwd=str(PROJECT_ROOT),
                env={**os.environ, "DATABASE_URL": os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/qnwis")}
            )
            
            output = result.stdout + result.stderr
            
            # Parse results
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            skipped = output.count(" SKIPPED")
            errors = output.count(" ERROR")
            
            suite_result = {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "errors": errors,
                "total": passed + failed + skipped + errors,
                "return_code": result.returncode,
                "output_preview": output[:2000] if self.verbose else output[:500]
            }
            
            status = "SUCCESS" if result.returncode == 0 else "ERROR"
            self.log(f"  {suite_name}: {passed} passed, {failed} failed, {skipped} skipped", status)
            
            return suite_result
            
        except subprocess.TimeoutExpired:
            self.log(f"  {suite_name}: TIMEOUT after 30 minutes", "ERROR")
            return {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 1,
                "total": 1,
                "return_code": -1,
                "output_preview": "Test suite timed out after 30 minutes"
            }
        except Exception as e:
            self.log(f"  {suite_name}: Exception - {e}", "ERROR")
            return {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 1,
                "total": 1,
                "return_code": -1,
                "output_preview": str(e)
            }
            
    def run_api_tests(self) -> Dict[str, Any]:
        """Run API accuracy tests."""
        test_file = PROJECT_ROOT / "tests" / "ab_testing" / "test_api_accuracy.py"
        return self.run_pytest_suite(test_file, "API Accuracy Tests")
        
    def run_postgres_tests(self) -> Dict[str, Any]:
        """Run PostgreSQL accuracy tests."""
        test_file = PROJECT_ROOT / "tests" / "ab_testing" / "test_postgres_accuracy.py"
        return self.run_pytest_suite(test_file, "PostgreSQL Accuracy Tests")
        
    def run_kg_rag_tests(self) -> Dict[str, Any]:
        """Run Knowledge Graph and RAG tests."""
        test_file = PROJECT_ROOT / "tests" / "ab_testing" / "test_knowledge_graph_accuracy.py"
        return self.run_pytest_suite(test_file, "Knowledge Graph & RAG Tests")
        
    def run_extraction_tests(self) -> Dict[str, Any]:
        """Run data extraction accuracy tests."""
        test_file = PROJECT_ROOT / "tests" / "ab_testing" / "test_extraction_accuracy.py"
        return self.run_pytest_suite(test_file, "Data Extraction Accuracy Tests")
        
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run existing integration tests."""
        test_file = PROJECT_ROOT / "tests" / "integration" / "test_data_accuracy.py"
        if test_file.exists():
            return self.run_pytest_suite(test_file, "Integration Tests")
        return {"skipped": True, "reason": "Test file not found"}
        
    def validate_ground_truth_coverage(self) -> Dict[str, Any]:
        """Validate that all ground truth values are testable."""
        self.log("Validating ground truth coverage...")
        
        try:
            from tests.ab_testing.ground_truth_data import (
                QATAR_GROUND_TRUTH,
                get_all_domains,
                get_indicators_for_domain
            )
            
            coverage = {}
            total_indicators = 0
            
            for domain in get_all_domains():
                indicators = get_indicators_for_domain(domain)
                coverage[domain] = {
                    "indicators": indicators,
                    "count": len(indicators)
                }
                total_indicators += len(indicators)
                
            self.log(f"  Ground truth: {total_indicators} indicators across {len(coverage)} domains", "SUCCESS")
            
            return {
                "domains": len(coverage),
                "total_indicators": total_indicators,
                "coverage": coverage
            }
            
        except Exception as e:
            self.log(f"  Ground truth validation failed: {e}", "ERROR")
            return {"error": str(e)}
            
    def check_database_connection(self) -> Dict[str, Any]:
        """Check database connectivity and data availability."""
        self.log("Checking database connection...")
        
        try:
            import psycopg2
            
            conn = psycopg2.connect(
                os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/qnwis")
            )
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # Check row counts for key tables
            row_counts = {}
            for table in ['world_bank_indicators', 'ilo_labour_data', 'gcc_labour_statistics']:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    row_counts[table] = cursor.fetchone()[0]
                    
            conn.close()
            
            self.log(f"  Database: {len(tables)} tables, {sum(row_counts.values())} rows in key tables", "SUCCESS")
            
            return {
                "connected": True,
                "tables": tables,
                "row_counts": row_counts
            }
            
        except Exception as e:
            self.log(f"  Database connection failed: {e}", "ERROR")
            return {"connected": False, "error": str(e)}
            
    def check_apis_available(self) -> Dict[str, Any]:
        """Check API availability."""
        self.log("Checking API availability...")
        
        api_status = {}
        
        # World Bank API
        try:
            from src.data.apis.world_bank_api import WorldBankAPI
            api = WorldBankAPI()
            result = api.get_indicator("SP.POP.TOTL", "QAT")
            api_status["world_bank"] = "available" if result else "no_data"
        except Exception as e:
            api_status["world_bank"] = f"error: {str(e)[:50]}"
            
        # ADP API
        try:
            from src.data.apis.arab_dev_portal import ArabDevPortalClient
            api_status["arab_dev_portal"] = "available"
        except Exception as e:
            api_status["arab_dev_portal"] = f"error: {str(e)[:50]}"
            
        # ESCWA API
        try:
            from src.data.apis.escwa_etdp import ESCWATradeAPI
            api_status["escwa_trade"] = "available"
        except Exception as e:
            api_status["escwa_trade"] = f"error: {str(e)[:50]}"
            
        available_count = sum(1 for v in api_status.values() if v == "available")
        self.log(f"  APIs: {available_count}/{len(api_status)} available", "SUCCESS" if available_count > 0 else "WARNING")
        
        return api_status
        
    def calculate_overall_summary(self) -> Dict[str, Any]:
        """Calculate overall test summary."""
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_errors = 0
        
        for suite_name, suite_result in self.results["test_suites"].items():
            if isinstance(suite_result, dict) and "passed" in suite_result:
                total_passed += suite_result.get("passed", 0)
                total_failed += suite_result.get("failed", 0)
                total_skipped += suite_result.get("skipped", 0)
                total_errors += suite_result.get("errors", 0)
                
        total_tests = total_passed + total_failed + total_skipped + total_errors
        accuracy = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "errors": total_errors,
            "accuracy_pct": round(accuracy, 2),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds()
        }
        
    def generate_html_report(self, filepath: Path):
        """Generate HTML report."""
        summary = self.results["overall_summary"]
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>QNWIS Data Accuracy Test Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a1a2e; border-bottom: 3px solid #4a69bd; padding-bottom: 10px; }}
        h2 {{ color: #4a69bd; margin-top: 30px; }}
        .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .card {{ padding: 20px; border-radius: 8px; text-align: center; }}
        .card.passed {{ background: #d4edda; color: #155724; }}
        .card.failed {{ background: #f8d7da; color: #721c24; }}
        .card.total {{ background: #e2e3e5; color: #383d41; }}
        .card.accuracy {{ background: #cce5ff; color: #004085; }}
        .card h3 {{ margin: 0; font-size: 36px; }}
        .card p {{ margin: 5px 0 0 0; font-size: 14px; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #4a69bd; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .status-pass {{ color: #155724; font-weight: bold; }}
        .status-fail {{ color: #721c24; font-weight: bold; }}
        .timestamp {{ color: #666; font-size: 14px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>QNWIS Data Accuracy Test Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary-cards">
            <div class="card total">
                <h3>{summary.get('total_tests', 0)}</h3>
                <p>Total Tests</p>
            </div>
            <div class="card passed">
                <h3>{summary.get('passed', 0)}</h3>
                <p>Passed</p>
            </div>
            <div class="card failed">
                <h3>{summary.get('failed', 0) + summary.get('errors', 0)}</h3>
                <p>Failed</p>
            </div>
            <div class="card accuracy">
                <h3>{summary.get('accuracy_pct', 0):.1f}%</h3>
                <p>Accuracy</p>
            </div>
        </div>
        
        <h2>Test Suite Results</h2>
        <table>
            <tr>
                <th>Test Suite</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Skipped</th>
                <th>Status</th>
            </tr>
"""
        
        for suite_name, suite_result in self.results["test_suites"].items():
            if isinstance(suite_result, dict) and "passed" in suite_result:
                passed = suite_result.get("passed", 0)
                failed = suite_result.get("failed", 0) + suite_result.get("errors", 0)
                skipped = suite_result.get("skipped", 0)
                status = "PASS" if suite_result.get("return_code", -1) == 0 else "FAIL"
                status_class = "status-pass" if status == "PASS" else "status-fail"
                
                html += f"""
            <tr>
                <td>{suite_name}</td>
                <td>{passed}</td>
                <td>{failed}</td>
                <td>{skipped}</td>
                <td class="{status_class}">{status}</td>
            </tr>
"""
                
        html += """
        </table>
        
        <h2>Infrastructure Status</h2>
        <table>
            <tr>
                <th>Component</th>
                <th>Status</th>
                <th>Details</th>
            </tr>
"""
        
        # Database status
        db_status = self.results.get("infrastructure", {}).get("database", {})
        db_connected = db_status.get("connected", False)
        html += f"""
            <tr>
                <td>PostgreSQL Database</td>
                <td class="{'status-pass' if db_connected else 'status-fail'}">{'Connected' if db_connected else 'Disconnected'}</td>
                <td>{sum(db_status.get('row_counts', {}).values())} rows in key tables</td>
            </tr>
"""
        
        # API status
        apis = self.results.get("infrastructure", {}).get("apis", {})
        for api_name, api_status in apis.items():
            is_available = api_status == "available"
            html += f"""
            <tr>
                <td>{api_name.replace('_', ' ').title()}</td>
                <td class="{'status-pass' if is_available else 'status-fail'}">{'Available' if is_available else 'Unavailable'}</td>
                <td>{api_status}</td>
            </tr>
"""
            
        html += """
        </table>
        
        <h2>Test Duration</h2>
        <p>Total test duration: <strong>{:.1f} seconds</strong> ({:.1f} minutes)</p>
    </div>
</body>
</html>
""".format(summary.get('duration_seconds', 0), summary.get('duration_seconds', 0) / 60)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
            
        self.log(f"HTML report saved to: {filepath}", "SUCCESS")
        
    def run_all(self):
        """Run all tests."""
        self.log("=" * 70)
        self.log("QNWIS COMPREHENSIVE DATA ACCURACY TEST SUITE")
        self.log("=" * 70)
        self.log(f"Mode: {'QUICK' if self.quick_mode else 'FULL'}")
        if self.domain_filter:
            self.log(f"Domain Filter: {self.domain_filter}")
        self.log("")
        
        # Pre-flight checks
        self.log("PHASE 1: Pre-flight Checks")
        self.log("-" * 40)
        
        self.results["infrastructure"] = {
            "ground_truth": self.validate_ground_truth_coverage(),
            "database": self.check_database_connection(),
            "apis": self.check_apis_available()
        }
        
        self.log("")
        self.log("PHASE 2: Running Test Suites")
        self.log("-" * 40)
        
        # Run test suites
        self.results["test_suites"]["API Accuracy"] = self.run_api_tests()
        self.results["test_suites"]["PostgreSQL Accuracy"] = self.run_postgres_tests()
        self.results["test_suites"]["Knowledge Graph & RAG"] = self.run_kg_rag_tests()
        self.results["test_suites"]["Data Extraction"] = self.run_extraction_tests()
        self.results["test_suites"]["Integration Tests"] = self.run_integration_tests()
        
        # Calculate summary
        self.results["overall_summary"] = self.calculate_overall_summary()
        self.results["metadata"]["end_time"] = datetime.now().isoformat()
        
        # Print final summary
        self.log("")
        self.log("=" * 70)
        self.log("FINAL SUMMARY")
        self.log("=" * 70)
        
        summary = self.results["overall_summary"]
        self.log(f"Total Tests: {summary['total_tests']}")
        self.log(f"Passed: {summary['passed']}")
        self.log(f"Failed: {summary['failed']}")
        self.log(f"Skipped: {summary['skipped']}")
        self.log(f"Accuracy: {summary['accuracy_pct']:.1f}%")
        self.log(f"Duration: {summary['duration_seconds']:.1f} seconds ({summary['duration_seconds']/60:.1f} minutes)")
        
        # Save reports
        report_dir = PROJECT_ROOT / "test_reports"
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON report
        json_path = report_dir / f"comprehensive_test_report_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        self.log(f"\nJSON report: {json_path}")
        
        # HTML report
        html_path = report_dir / f"comprehensive_test_report_{timestamp}.html"
        self.generate_html_report(html_path)
        
        # Return success/failure
        return summary['failed'] == 0 and summary['errors'] == 0


def main():
    parser = argparse.ArgumentParser(description="QNWIS Comprehensive Data Accuracy Tests")
    parser.add_argument("--quick", action="store_true", help="Run quick smoke tests only")
    parser.add_argument("--domain", type=str, help="Test specific domain only")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    # Set environment variable for database
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql://postgres:1234@localhost:5432/qnwis"
    
    runner = ComprehensiveTestRunner(
        quick_mode=args.quick,
        domain_filter=args.domain,
        verbose=args.verbose
    )
    
    success = runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

