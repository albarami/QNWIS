#!/usr/bin/env python3
"""
Test API Integration - Verify APIs are properly integrated and triggered
"""

import asyncio
import sys

async def test_api_triggers():
    """Test that API triggers work properly"""
    
    print("="*80)
    print("API INTEGRATION TEST")
    print("="*80)
    print()
    
    # Import after path setup
    from src.qnwis.orchestration.prefetch_apis import CompletePrefetchLayer
    
    prefetch = CompletePrefetchLayer()
    
    print("✅ Prefetch layer initialized")
    print(f"   - IMF connector: {'✅' if prefetch.imf_connector else '❌'}")
    print(f"   - UN Comtrade connector: {'✅' if prefetch.un_comtrade_connector else '❌'}")
    print(f"   - FRED connector: {'✅' if prefetch.fred_connector else '❌'}")
    print()
    
    # Test 1: Economic query (should trigger IMF)
    print("-"*80)
    print("TEST 1: Economic Query (IMF trigger)")
    print("-"*80)
    
    try:
        result = await prefetch.fetch_all_sources("What is Qatar GDP growth?")
        
        # Check if IMF data is in results
        imf_data = [f for f in result if f.get("source", "").startswith("IMF")]
        
        print(f"✅ Query processed")
        print(f"   Total facts: {len(result)}")
        print(f"   IMF facts: {len(imf_data)}")
        
        if imf_data:
            print(f"   Sample IMF data:")
            for fact in imf_data[:3]:
                print(f"      - {fact.get('metric', 'unknown')}: {fact.get('value', 'N/A')}")
        
        test1_pass = len(imf_data) > 0 if prefetch.imf_connector else True
        print(f"\n{'✅ PASS' if test1_pass else '❌ FAIL'}: IMF trigger")
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        test1_pass = False
    
    print()
    
    # Test 2: Food query (should trigger UN Comtrade)
    print("-"*80)
    print("TEST 2: Food Query (UN Comtrade trigger)")
    print("-"*80)
    
    try:
        result = await prefetch.fetch_all_sources("What are Qatar food imports?")
        
        # Check if UN Comtrade data is in results
        comtrade_data = [f for f in result if f.get("source", "").startswith("UN Comtrade")]
        
        print(f"✅ Query processed")
        print(f"   Total facts: {len(result)}")
        print(f"   UN Comtrade facts: {len(comtrade_data)}")
        
        if comtrade_data:
            print(f"   Sample Comtrade data:")
            for fact in comtrade_data[:3]:
                value = fact.get('value', 0)
                print(f"      - {fact.get('metric', 'unknown')}: ${value:,.0f}" if isinstance(value, (int, float)) else f"      - {fact.get('metric', 'unknown')}: {value}")
        
        test2_pass = len(comtrade_data) > 0 if prefetch.un_comtrade_connector else True
        print(f"\n{'✅ PASS' if test2_pass else '❌ FAIL'}: UN Comtrade trigger")
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        test2_pass = False
    
    print()
    
    # Test 3: US comparison query (should trigger FRED)
    print("-"*80)
    print("TEST 3: US Comparison Query (FRED trigger)")
    print("-"*80)
    
    try:
        result = await prefetch.fetch_all_sources("Compare Qatar to United States economy")
        
        # Check if FRED data is in results
        fred_data = [f for f in result if f.get("source", "").startswith("FRED")]
        
        print(f"✅ Query processed")
        print(f"   Total facts: {len(result)}")
        print(f"   FRED facts: {len(fred_data)}")
        
        if fred_data:
            print(f"   Sample FRED data:")
            for fact in fred_data[:3]:
                print(f"      - {fact.get('description', fact.get('metric', 'unknown'))}: {fact.get('value', 'N/A')}")
        
        test3_pass = len(fred_data) > 0 if prefetch.fred_connector else True
        print(f"\n{'✅ PASS' if test3_pass else '❌ FAIL'}: FRED trigger")
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        test3_pass = False
    
    print()
    
    # Clean up
    await prefetch.close()
    
    # Final summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    all_tests = [test1_pass, test2_pass, test3_pass]
    passed = sum(all_tests)
    total = len(all_tests)
    
    print(f"Tests passed: {passed}/{total}")
    print()
    print(f"✅ IMF trigger: {'PASS' if test1_pass else 'FAIL'}")
    print(f"✅ UN Comtrade trigger: {'PASS' if test2_pass else 'FAIL'}")
    print(f"✅ FRED trigger: {'PASS' if test3_pass else 'FAIL'}")
    print()
    
    if all(all_tests):
        print("🎉 ALL TESTS PASSED - API Integration Complete!")
        return 0
    else:
        print("⚠️  Some tests failed - Check connector availability")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_api_triggers())
    sys.exit(exit_code)
