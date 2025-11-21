"""
ETL: World Bank API → PostgreSQL world_bank_indicators table
Uses EXISTING WorldBankAPI connector and EXISTING table
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.apis.world_bank_api import WorldBankAPI
from qnwis.data.deterministic.engine import get_engine
from sqlalchemy import text

async def load_world_bank_to_postgres():
    """
    Fetch World Bank data using EXISTING API connector
    Load into EXISTING world_bank_indicators table
    """
    print("="*80)
    print("🏦 WORLD BANK → POSTGRESQL ETL")
    print("="*80)
    
    wb_api = WorldBankAPI()
    engine = get_engine()
    
    # Key indicators for Qatar
    indicators_to_fetch = {
        "NY.GDP.MKTP.CD": "GDP (current US$)",
        "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
        "NV.IND.TOTL.ZS": "Industry value added (% of GDP)",
        "NV.AGR.TOTL.ZS": "Agriculture value added (% of GDP)",
        "NV.SRV.TOTL.ZS": "Services value added (% of GDP)",
        "NE.GDI.TOTL.ZS": "Gross capital formation (% of GDP)",
        "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force)",
        "SE.TER.ENRR": "School enrollment, tertiary (% gross)",
        "IT.NET.USER.ZS": "Individuals using Internet (% of population)",
    }
    
    total_records = 0
    
    for indicator_code, indicator_name in indicators_to_fetch.items():
        try:
            print(f"\n📊 Fetching {indicator_code}: {indicator_name}")
            
            # Use EXISTING API connector
            data = await wb_api.get_indicator(indicator_code, "QAT", start_year=2010)
            
            values = data.get("values", {})
            if not values:
                print(f"   ⚠️  No data available")
                continue
            
            # Insert into EXISTING table
            with engine.begin() as conn:
                for year, value in values.items():
                    conn.execute(
                        text("""
                            INSERT INTO world_bank_indicators 
                            (country_code, country_name, indicator_code, indicator_name, year, value, created_at)
                            VALUES (:country, :country_name, :code, :name, :year, :value, :created)
                            ON CONFLICT (country_code, indicator_code, year) 
                            DO UPDATE SET value = EXCLUDED.value
                        """),
                        {
                            "country": "QAT",
                            "country_name": "Qatar",
                            "code": indicator_code,
                            "name": indicator_name,
                            "year": int(year),
                            "value": float(value),
                            "created": datetime.utcnow()
                        }
                    )
            
            print(f"   ✅ Loaded {len(values)} records")
            total_records += len(values)
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    await wb_api.close()
    
    print(f"\n{'='*80}")
    print(f"✅ Total records loaded: {total_records}")
    print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(load_world_bank_to_postgres())
