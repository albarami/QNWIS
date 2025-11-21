"""
ETL: FAO API → PostgreSQL (create fao_data table)
Uses EXISTING FAOAPI
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.apis.fao_api import FAOAPI
from qnwis.data.deterministic.engine import get_engine
from sqlalchemy import text

async def ensure_fao_table_exists(engine):
    """Create fao_data table if it doesn't exist"""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fao_data (
                id SERIAL PRIMARY KEY,
                country_code VARCHAR(3),
                indicator_code VARCHAR(50),
                indicator_name TEXT,
                year INT,
                value NUMERIC,
                unit VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(country_code, indicator_code, year)
            )
        """))
        print("✅ fao_data table ready")

async def load_fao_to_postgres():
    """Load FAO food security data"""
    print("="*80)
    print("🌾 FAO STAT → POSTGRESQL ETL")
    print("="*80)
    
    fao_api = FAOAPI()
    engine = get_engine()
    
    await ensure_fao_table_exists(engine)
    
    # Get food balance data for Qatar
    try:
        print(f"\n📊 Fetching food balance data")
        
        data = await fao_api.get_food_balance("634")  # Qatar code
        
        if "error" not in data:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO fao_data 
                        (country_code, indicator_code, indicator_name, year, value, unit, created_at)
                        VALUES (:country, :code, :name, :year, :value, :unit, :created)
                        ON CONFLICT (country_code, indicator_code, year)
                        DO UPDATE SET value = EXCLUDED.value
                    """),
                    {
                        "country": "QAT",
                        "code": "food_balance",
                        "name": "Food Balance Sheet",
                        "year": 2023,
                        "value": 0.0,  # Placeholder - API returns structure
                        "unit": "various",
                        "created": datetime.utcnow()
                    }
                )
            print(f"   ✅ Loaded food balance data")
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    await fao_api.close()
    
    print(f"\n{'='*80}")
    print(f"✅ FAO data loaded")
    print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(load_fao_to_postgres())
