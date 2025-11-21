"""
Test if agents can access PostgreSQL data
Critical verification: Data in DB means nothing if agents can't use it
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_prefetch_data_access():
    """Test if prefetch layer returns PostgreSQL data"""
    print("="*80)
    print("🔍 TESTING PREFETCH ACCESS TO POSTGRESQL DATA")
    print("="*80)
    
    from qnwis.orchestration.prefetch_apis import CompletePrefetchLayer
    
    prefetch = CompletePrefetchLayer()
    
    # Test query that should trigger World Bank data
    query = "What is Qatar's GDP growth and sector breakdown from 2010 to 2024?"
    
    print(f"\nQuery: {query}")
    print("\nFetching data...")
    
    try:
        facts = await prefetch.fetch_all_sources(query)
        
        print(f"\n✅ Retrieved {len(facts)} total facts")
        
        # Check for World Bank data
        wb_facts = [f for f in facts if "World Bank" in f.get("source", "")]
        print(f"\n📊 World Bank facts: {len(wb_facts)}")
        
        if wb_facts:
            print("\nSample World Bank facts:")
            for fact in wb_facts[:5]:
                metric = fact.get("metric", "unknown")
                value = fact.get("value", "N/A")
                year = fact.get("year", "N/A")
                source = fact.get("source", "unknown")
                cached = fact.get("cached", False)
                print(f"  - {metric}: {value} ({year}) - Source: {source} - Cached: {cached}")
        
        # Check if we have multi-year data
        years_found = set()
        for fact in wb_facts:
            if "year" in fact:
                years_found.add(fact["year"])
        
        if len(years_found) > 1:
            print(f"\n✅ MULTI-YEAR DATA AVAILABLE: {sorted(years_found)}")
            print("   Agents CAN access historical data from PostgreSQL!")
        else:
            print(f"\n⚠️  Only {len(years_found)} year(s) of data found")
            print("   Agents may not be accessing full PostgreSQL cache")
        
        # Check if cached flag is set
        cached_facts = [f for f in wb_facts if f.get("cached", False)]
        if cached_facts:
            print(f"\n✅ USING CACHE: {len(cached_facts)} facts from PostgreSQL cache")
        else:
            print(f"\n⚠️  NO CACHED DATA: All {len(wb_facts)} facts from live API")
            print("   Need to implement cache-first strategy!")
        
        await prefetch.close()
        
        return len(cached_facts) > 0, len(years_found) > 5
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        await prefetch.close()
        return False, False

if __name__ == "__main__":
    uses_cache, has_historical = asyncio.run(test_prefetch_data_access())
    
    print("\n" + "="*80)
    print("RESULTS:")
    print("="*80)
    
    if uses_cache and has_historical:
        print("✅ PERFECT: Agents use PostgreSQL cache with full historical data")
        print("   Status: COMPLETE - No further action needed")
    elif has_historical and not uses_cache:
        print("⚠️  ISSUE: PostgreSQL has data but cache-first not implemented")
        print("   Action: Implement cache-first strategy in prefetch")
    else:
        print("❌ PROBLEM: Agents not accessing PostgreSQL data")
        print("   Action: Implement cache query methods")
    
    sys.exit(0 if (uses_cache and has_historical) else 1)
