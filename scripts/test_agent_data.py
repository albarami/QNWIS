"""Test agent data access."""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from src.qnwis.agents.base import DataClient
from src.qnwis.agents.national_strategy import NationalStrategyAgent

def main():
    print("=" * 60)
    print("TESTING AGENT DATA ACCESS")
    print("=" * 60)
    
    client = DataClient()
    
    # Test 1: Check raw query result structure
    print("\n1. Raw query result for syn_unemployment_gcc_latest:")
    result = client.run('syn_unemployment_gcc_latest')
    print(f"   Result type: {type(result)}")
    print(f"   Result.rows: {result.rows}")
    print(f"   Rows type: {type(result.rows)}")
    
    if result.rows is not None:
        rows = list(result.rows)
        print(f"   Number of rows: {len(rows)}")
        
        if rows:
            first = rows[0]
            print(f"   First row type: {type(first)}")
            has_data = hasattr(first, 'data')
            print(f"   Has .data attr: {has_data}")
            if has_data:
                print(f"   first.data type: {type(first.data)}")
                print(f"   first.data value: {first.data}")
                if first.data:
                    print(f"   first.data keys: {list(first.data.keys())}")
    
    # Test 2: Test NationalStrategy agent directly
    print("\n2. Testing NationalStrategy.gcc_benchmark():")
    agent = NationalStrategyAgent(client)
    try:
        report = agent.gcc_benchmark()
        print(f"   Report type: {type(report)}")
        print(f"   Findings: {len(report.findings)}")
        print(f"   Warnings: {report.warnings}")
        if report.findings:
            print(f"   First finding: {report.findings[0].title}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Check employment_share_by_gender
    print("\n3. Raw query result for syn_employment_share_by_gender_latest:")
    result2 = client.run('syn_employment_share_by_gender_latest')
    print(f"   Rows: {result2.rows}")
    if result2.rows:
        rows2 = list(result2.rows)
        print(f"   Number of rows: {len(rows2)}")
        if rows2:
            first2 = rows2[0]
            print(f"   First row: {first2}")
            if hasattr(first2, 'data'):
                print(f"   first.data: {first2.data}")

if __name__ == "__main__":
    main()

