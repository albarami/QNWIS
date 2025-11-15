"""Check if database actually has data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qnwis.data.deterministic.engine import get_engine
from sqlalchemy import text

engine = get_engine()

print("\n=== CHECKING DATABASE ===\n")

tables_to_check = [
    "gcc_labour_statistics",
    "vision_2030_targets",
    "employment_records",
    "ilo_labour_data",
    "world_bank_indicators",
]

with engine.connect() as conn:
    for table in tables_to_check:
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            status = "OK" if count > 0 else "EMPTY"
            print(f"{status:6} {table:30} {count:>8,} records")
        except Exception as e:
            print(f"ERROR  {table:30} {str(e)[:50]}")

print("\n=== CHECKING QUERY FILES ===\n")

from qnwis.data.deterministic.registry import QueryRegistry
registry = QueryRegistry()
registry.load_all()

print(f"Loaded {len(registry._queries)} query definitions")

# Check if GCC queries exist
gcc_queries = [q for q in registry._queries.values() if 'gcc' in q.query_id.lower()]
print(f"\nGCC-related queries: {len(gcc_queries)}")
for q in gcc_queries:
    print(f"  - {q.query_id:40} dataset={q.dataset}")
