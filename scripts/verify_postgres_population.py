"""
Verify PostgreSQL tables are populated with data from ETL scripts
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qnwis.data.deterministic.engine import get_engine
from sqlalchemy import text

def verify_postgres_tables():
    """Check that all tables are populated"""
    print("="*80)
    print("🔍 VERIFYING POSTGRESQL TABLE POPULATION")
    print("="*80)
    
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check World Bank
        try:
            result = conn.execute(text('SELECT COUNT(*) FROM world_bank_indicators'))
            wb_count = result.fetchone()[0]
            print(f'\n✅ World Bank indicators: {wb_count:,} rows')
            
            # Show sample
            result = conn.execute(text('''
                SELECT indicator_code, indicator_name, COUNT(*) as years
                FROM world_bank_indicators
                GROUP BY indicator_code, indicator_name
                LIMIT 5
            '''))
            print("   Sample indicators:")
            for row in result:
                print(f"   - {row[0]}: {row[1]} ({row[2]} years)")
                
        except Exception as e:
            print(f'\n❌ World Bank indicators: Error - {e}')
        
        # Check ILO
        try:
            result = conn.execute(text('SELECT COUNT(*) FROM ilo_labour_data'))
            ilo_count = result.fetchone()[0]
            print(f'\n✅ ILO labour data: {ilo_count:,} rows')
            
            # Show sample
            result = conn.execute(text('''
                SELECT country_code, indicator_code, COUNT(*) as records
                FROM ilo_labour_data
                GROUP BY country_code, indicator_code
                LIMIT 5
            '''))
            print("   Sample data:")
            for row in result:
                print(f"   - {row[0]}/{row[1]}: {row[2]} records")
                
        except Exception as e:
            print(f'\n❌ ILO labour data: Error - {e}')
        
        # Check FAO
        try:
            result = conn.execute(text('SELECT COUNT(*) FROM fao_data'))
            fao_count = result.fetchone()[0]
            print(f'\n✅ FAO data: {fao_count:,} rows')
            
            # Show sample
            if fao_count > 0:
                result = conn.execute(text('''
                    SELECT country_code, indicator_code, indicator_name
                    FROM fao_data
                    LIMIT 5
                '''))
                print("   Sample data:")
                for row in result:
                    print(f"   - {row[0]}: {row[2]}")
                    
        except Exception as e:
            print(f'\n❌ FAO data: Error - {e}')
        
        # Check embeddings
        try:
            result = conn.execute(text('SELECT COUNT(*) FROM document_embeddings'))
            emb_count = result.fetchone()[0]
            print(f'\n✅ Document embeddings: {emb_count:,} rows')
            
            # Show sample sources
            result = conn.execute(text('''
                SELECT source, COUNT(*) as count
                FROM document_embeddings
                GROUP BY source
                ORDER BY count DESC
                LIMIT 5
            '''))
            print("   Embeddings by source:")
            for row in result:
                print(f"   - {row[0]}: {row[1]} documents")
                
        except Exception as e:
            print(f'\n❌ Document embeddings: Error - {e}')
    
    print(f"\n{'='*80}")
    print("✅ VERIFICATION COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    verify_postgres_tables()
