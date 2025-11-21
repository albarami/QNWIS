#!/usr/bin/env python
"""
Test script to verify QueryRegistry can load all query definitions.

Usage:
    python scripts/test_query_loading.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qnwis.data.deterministic.registry import QueryRegistry, DEFAULT_QUERY_ROOT


def main() -> int:
    """Test query loading."""
    print("🔍 Testing QueryRegistry query loading...")
    print(f"📁 Query directory: {DEFAULT_QUERY_ROOT}")
    print("=" * 80)

    try:
        # Initialize registry
        registry = QueryRegistry(root=str(DEFAULT_QUERY_ROOT))
        
        # Load all queries
        print("\n📥 Loading queries...")
        registry.load_all()

        # Get all query IDs
        query_ids = sorted(registry.list_query_ids())

        if not query_ids:
            print("❌ Error: No queries loaded")
            return 1

        print(f"\n✅ Loaded {len(query_ids)} queries:\n")

        # Test each query
        errors = []
        for query_id in query_ids:
            try:
                query_def = registry.get(query_id)
                print(f"  ✅ {query_id:40} | {query_def.dataset:15} | TTL: {query_def.cache_ttl}s")
            except Exception as e:
                errors.append(f"  ❌ {query_id}: {e}")
                print(errors[-1])

        print("\n" + "=" * 80)

        if errors:
            print(f"\n❌ Failed to load {len(errors)} queries")
            return 1

        print(f"\n✅ All {len(query_ids)} queries loaded successfully!")

        # Show statistics
        print("\n📊 Query Statistics:")
        datasets = {}
        access_levels = {}
        for query_id in query_ids:
            q = registry.get(query_id)
            datasets[q.dataset] = datasets.get(q.dataset, 0) + 1
            access_levels[q.access_level] = access_levels.get(q.access_level, 0) + 1

        print(f"\n  Datasets:")
        for dataset, count in sorted(datasets.items()):
            print(f"    - {dataset:20} : {count} queries")

        print(f"\n  Access Levels:")
        for level, count in sorted(access_levels.items()):
            print(f"    - {level:20} : {count} queries")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
