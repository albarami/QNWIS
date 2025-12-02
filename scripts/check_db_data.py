"""Check what data exists in the database."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv('.env')

from sqlalchemy import create_engine, text

db_url = os.getenv('DATABASE_URL')
print(f"Connecting to: {db_url[:40]}...")

engine = create_engine(db_url)

# Check what tables exist
with engine.connect() as conn:
    result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
    tables = [row[0] for row in result]
    print(f'\nTables in database ({len(tables)}):')
    for t in tables:
        # Count rows in each table
        try:
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
            count = count_result.scalar()
            print(f'  - {t}: {count} rows')
        except Exception as e:
            print(f'  - {t}: ERROR ({e})')

