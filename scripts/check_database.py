#!/usr/bin/env python3
"""Check what real data exists in the QNWIS PostgreSQL database."""

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres:1234@localhost:5432/qnwis"

def main():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=" * 60)
        print("REAL DATABASE TABLES IN QNWIS")
        print("=" * 60)
        
        # Get all tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        
        for t in tables:
            print(f"  - {t['table_name']}")
        
        print()
        print("TABLE ROW COUNTS:")
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t['table_name']}")
                count = cur.fetchone()['count']
                print(f"  {t['table_name']}: {count} rows")
            except Exception as e:
                print(f"  {t['table_name']}: ERROR - {e}")
        
        # Sample data from key tables
        print()
        print("=" * 60)
        print("SAMPLE DATA FROM KEY TABLES")
        print("=" * 60)
        
        # World Bank indicators
        try:
            cur.execute("SELECT * FROM world_bank_indicators LIMIT 3")
            rows = cur.fetchall()
            print()
            print("world_bank_indicators:")
            for row in rows:
                print(f"  {dict(row)}")
        except:
            print("  world_bank_indicators: Table not found or empty")
        
        # Vision 2030 targets
        try:
            cur.execute("SELECT * FROM vision_2030_targets LIMIT 3")
            rows = cur.fetchall()
            print()
            print("vision_2030_targets:")
            for row in rows:
                print(f"  {dict(row)}")
        except:
            print("  vision_2030_targets: Table not found or empty")
        
        # GCC labour statistics
        try:
            cur.execute("SELECT * FROM gcc_labour_statistics LIMIT 3")
            rows = cur.fetchall()
            print()
            print("gcc_labour_statistics:")
            for row in rows:
                print(f"  {dict(row)}")
        except:
            print("  gcc_labour_statistics: Table not found or empty")
        
        conn.close()
        print()
        print("✅ Database connection successful!")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()

