import asyncio
from qnwis.orchestration.prefetch_apis import get_complete_prefetch

async def verify():
    print('='*80)
    print('VERIFICATION: CACHE-FIRST STRATEGY')
    print('='*80)
    
    prefetch = get_complete_prefetch()
    
    # Test cache query
    print('\n1. Testing World Bank cache query...')
    cached = prefetch._query_postgres_cache('world_bank', 'QAT')
    print(f'   Result: {len(cached)} cached records')
    if cached:
        print(f'   Sample: {cached[0].get("metric", "unknown")}')
        print(f'   ✅ Cache-first: WORKING')
    else:
        print(f'   ❌ Cache empty!')
    
    # Test ILO cache
    print('\n2. Testing ILO cache query...')
    cached_ilo = prefetch._query_postgres_cache('ilo', 'QAT')
    print(f'   Result: {len(cached_ilo)} cached records')
    if cached_ilo:
        print(f'   ✅ ILO cache: WORKING')
    else:
        print(f'   ⚠️  ILO cache: Empty (will fetch from API)')
    
    print('\n' + '='*80)
    print('VERIFICATION COMPLETE')
    print('='*80)

asyncio.run(verify())
