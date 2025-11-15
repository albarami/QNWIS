import os
from sqlalchemy import create_engine, text

os.environ['DATABASE_URL'] = 'postgresql://postgres:1234@localhost:5432/qnwis'
engine = create_engine(os.environ['DATABASE_URL'])

with engine.connect() as conn:
    # Check employment_records structure
    result = conn.execute(text('SELECT * FROM employment_records LIMIT 3'))
    print("employment_records columns:", [col for col in result.keys()])
    print("\nSample rows:")
    for i, row in enumerate(result):
        if i < 2:
            print(f"  Row {i+1}:", row._asdict())
    
    # Check gcc_labour_statistics
    result = conn.execute(text('SELECT * FROM gcc_labour_statistics LIMIT 3'))
    print("\n\ngcc_labour_statistics columns:", [col for col in result.keys()])
    print("\nSample rows:")
    for i, row in enumerate(result):
        if i < 2:
            print(f"  Row {i+1}:", row._asdict())
