"""Test SQL executor directly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qnwis.data.deterministic.engine import get_engine
from qnwis.data.deterministic.registry import QueryRegistry
from qnwis.data.deterministic.access import execute

# Load registry
registry = QueryRegistry()
registry.load_all()

print(f"\nLoaded {len(registry._items)} queries\n")

# Find a GCC query
gcc_query_id = "syn_unemployment_gcc_latest"
spec = registry.get(gcc_query_id)

if not spec:
    print(f"ERROR: Query '{gcc_query_id}' not found!")
    print(f"Available queries: {list(registry._items.keys())[:10]}")
    sys.exit(1)

print(f"Testing query: {spec.query_id}")
print(f"Dataset: {spec.dataset}")
print(f"SQL: {spec.sql[:200]}...")

# Execute it
try:
    result = execute(gcc_query_id, registry)
    print(f"\nSUCCESS!")
    print(f"Rows: {len(result.rows)}")
    print(f"Columns: {result.columns}")
    if result.rows:
        print(f"First row: {result.rows[0]}")
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
