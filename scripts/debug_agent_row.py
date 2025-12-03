"""Debug agent row data access."""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from src.qnwis.agents.base import DataClient

client = DataClient()

result = client.run('syn_unemployment_gcc_latest')
print(f'Rows type: {type(result.rows)}')
rows = list(result.rows) if result.rows else []
print(f'Number of rows: {len(rows)}')

for i, row in enumerate(rows[:3]):
    print(f'\nRow {i}:')
    print(f'  type: {type(row)}')
    has_data = hasattr(row, 'data')
    print(f'  has .data: {has_data}')
    if has_data:
        print(f'  .data type: {type(row.data)}')
        print(f'  .data value: {row.data}')
        if row.data:
            country = row.data.get('country')
            rate = row.data.get('unemployment_rate')
            print(f'  country: {country}')
            print(f'  rate: {rate}, type: {type(rate)}')

# Now test NationalStrategy directly
print("\n" + "=" * 60)
print("Testing NationalStrategy.gcc_benchmark()...")
print("=" * 60)

from src.qnwis.agents.national_strategy import NationalStrategyAgent

agent = NationalStrategyAgent(client)
try:
    report = agent.gcc_benchmark(min_countries=3)
    print(f"SUCCESS! Findings: {len(report.findings)}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

