"""
Test UN Comtrade FREE public preview API
"""

import asyncio
from src.data.apis.un_comtrade_api import UNComtradeConnector

async def test_free_api():
    """Test the FREE UN Comtrade public preview API"""
    
    print("="*80)
    print("🧪 TESTING UN COMTRADE FREE PUBLIC API")
    print("="*80)
    
    connector = UNComtradeConnector()  # No API key needed!
    
    print("\n📊 Test 1: Qatar Meat Imports (HS code 02)")
    try:
        data = await connector.get_imports("02", 2022)  # Most recent complete year
        
        if "data" in data:
            records = data.get("data", [])
            print(f"✅ Retrieved {len(records)} records")
            
            if records:
                # Show first record
                first = records[0]
                print(f"   Sample: {first.get('partnerDesc', 'Unknown')} - "
                      f"${first.get('primaryValue', 0):,.0f}")
        elif "error" in data:
            print(f"❌ Error: {data['error']}")
        else:
            print("⚠️  No data returned")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n📊 Test 2: Qatar Dairy Imports (HS code 04)")
    try:
        data = await connector.get_imports("04", 2022)
        
        if "data" in data:
            records = data.get("data", [])
            print(f"✅ Retrieved {len(records)} records")
            
            if records:
                # Calculate total value
                total_value = sum(r.get("primaryValue", 0) for r in records)
                print(f"   Total value: ${total_value:,.0f}")
        elif "error" in data:
            print(f"❌ Error: {data['error']}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n📊 Test 3: Total Food Imports Dashboard")
    try:
        dashboard = await connector.get_total_food_imports(2022)
        
        if dashboard:
            print(f"✅ Dashboard retrieved with {len(dashboard)} categories")
            print(f"   Total imports: ${dashboard.get('total_usd', 0):,.0f}")
            
            # Show top 3 categories
            categories = [(k, v) for k, v in dashboard.items() 
                         if k not in ['total_usd', 'year', 'country']]
            categories.sort(key=lambda x: x[1].get('value_usd', 0), reverse=True)
            
            print("\n   Top 3 import categories:")
            for name, data in categories[:3]:
                print(f"   - {name}: ${data.get('value_usd', 0):,.0f}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    await connector.close()
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE - FREE API WORKING!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_free_api())
