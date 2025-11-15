import os
from sqlalchemy import create_engine, text

os.environ['DATABASE_URL'] = 'postgresql://postgres:1234@localhost:5432/qnwis'

engine = create_engine(os.environ['DATABASE_URL'])

print("Connecting to database...")
with engine.connect() as conn:
    # Check tables
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
    tables = [row[0] for row in result]
    
    print(f"\n✅ Database connected successfully!")
    print(f"Tables found: {len(tables)}")
    
    if tables:
        print("\nExisting tables:")
        for table in tables:
            print(f"  - {table}")
    else:
        print("\n⚠️  No tables found - database needs schema initialization")
    
    # Check if we have data
    if 'employment_records' in tables:
        result = conn.execute(text("SELECT COUNT(*) FROM employment_records"))
        count = result.scalar()
        print(f"\nemployment_records: {count} rows")
    
    if 'gcc_labour_statistics' in tables:
        result = conn.execute(text("SELECT COUNT(*) FROM gcc_labour_statistics"))
        count = result.scalar()
        print(f"gcc_labour_statistics: {count} rows")
