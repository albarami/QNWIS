"""Quick seed of employment records so queries work."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qnwis.data.deterministic.engine import get_engine
import pandas as pd
from datetime import date, timedelta
import random

engine = get_engine()

print("\n🌱 SEEDING EMPLOYMENT RECORDS...")

# Create synthetic employment data
data = []
nationalities = ['Qatari', 'Indian', 'Filipino', 'Egyptian', 'Pakistani', 'Nepali', 'Bangladeshi']
genders = ['Male', 'Female']
sectors = ['Public Administration', 'Private Sector', 'Healthcare', 'Education', 'Construction', 'Retail']
statuses = ['employed']
education_levels = ['High School', 'Bachelor', 'Master', 'PhD', 'Diploma']

# Create 1000 sample records across last 12 months
base_date = date(2024, 1, 1)
for i in range(1000):
    month_offset = random.randint(0, 11)
    record_date = base_date + timedelta(days=30 * month_offset)
    
    data.append({
        'person_id': f'PER{i:06d}',
        'company_id': f'COM{random.randint(1, 200):04d}',
        'nationality': random.choice(nationalities),
        'gender': random.choice(genders),
        'age': random.randint(22, 65),
        'education_level': random.choice(education_levels),
        'sector': random.choice(sectors),
        'job_title': f'Position {random.randint(1, 50)}',
        'status': 'employed',
        'month': record_date,
        'salary_qar': random.randint(3000, 25000),
        'start_date': record_date - timedelta(days=random.randint(30, 1000)),
    })

df = pd.DataFrame(data)

# Insert
df.to_sql('employment_records', engine, if_exists='append', index=False)

print(f"✅ Seeded {len(df)} employment records")

# Verify
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM employment_records"))
    count = result.fetchone()[0]
    print(f"✅ Total employment records now: {count:,}")
    
    # Check latest month
    result = conn.execute(text("SELECT MAX(month) FROM employment_records"))
    latest = result.fetchone()[0]
    print(f"✅ Latest data: {latest}")

print("\n✅ DATABASE READY FOR QUERIES!")
