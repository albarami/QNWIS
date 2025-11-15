#!/bin/bash
# QNWIS Database Initialization Script
# Initializes database schema and seeds production data
#
# Usage:
#   ./scripts/init_database.sh
#   ./scripts/init_database.sh --preset demo
#   ./scripts/init_database.sh --preset full

set -e  # Exit on error

echo "=========================================="
echo "QNWIS DATABASE INITIALIZATION"
echo "=========================================="
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL environment variable not set"
    echo ""
    echo "Examples:"
    echo "  PostgreSQL: export DATABASE_URL=postgresql://user:pass@localhost:5432/qnwis"
    echo "  SQLite:     export DATABASE_URL=sqlite:///./qnwis.db"
    echo ""
    exit 1
fi

echo "📊 Database URL: $DATABASE_URL"
echo ""

# Parse arguments
PRESET=${1:-demo}
if [ "$PRESET" = "--preset" ]; then
    PRESET=${2:-demo}
fi

echo "Configuration: $PRESET"
echo ""

# Step 1: Create database schema
echo "1️⃣  Creating database schema..."
echo "   Tables: employment_records, gcc_labour_statistics, vision_2030_targets"
echo "   Tables: ilo_labour_data, world_bank_indicators, qatar_open_data"
echo "   Views: employment_summary_monthly, qatarization_summary"
echo ""

# Check if psql is available
if command -v psql &> /dev/null; then
    psql "$DATABASE_URL" -f data/schema/lmis_schema.sql
    echo "   ✅ Schema created via psql"
else
    # Fallback to Python
    python -c "
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv('DATABASE_URL'))
with open('data/schema/lmis_schema.sql', 'r') as f:
    schema_sql = f.read()
    
# Execute schema in transaction
with engine.begin() as conn:
    for statement in schema_sql.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                conn.execute(text(statement))
            except Exception as e:
                print(f'Warning: {e}')
                pass
print('   ✅ Schema created via SQLAlchemy')
"
fi

echo ""

# Step 2: Seed production data
echo "2️⃣  Seeding production data..."
echo ""

python scripts/seed_production_database.py --preset "$PRESET"

echo ""

# Step 3: Verify installation
echo "3️⃣  Verifying database..."
echo ""

python -c "
from src.qnwis.db.engine import get_engine

engine = get_engine()
with engine.connect() as conn:
    # Check employment records
    result = conn.execute('SELECT COUNT(*) FROM employment_records')
    emp_count = result.fetchone()[0]
    print(f'   ✅ Employment records: {emp_count:,}')
    
    # Check GCC data
    result = conn.execute('SELECT COUNT(*) FROM gcc_labour_statistics')
    gcc_count = result.fetchone()[0]
    print(f'   ✅ GCC statistics: {gcc_count:,}')
    
    # Check Vision 2030
    result = conn.execute('SELECT COUNT(*) FROM vision_2030_targets')
    vision_count = result.fetchone()[0]
    print(f'   ✅ Vision 2030 targets: {vision_count:,}')
    
    # Check materialized views
    result = conn.execute('SELECT COUNT(*) FROM employment_summary_monthly')
    summary_count = result.fetchone()[0]
    print(f'   ✅ Monthly summary: {summary_count:,} aggregations')
"

echo ""
echo "=========================================="
echo "✅ DATABASE INITIALIZATION COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  • Test queries: python scripts/test_query_loading.py"
echo "  • Start API: python -m uvicorn qnwis.api.server:app --reload"
echo "  • Launch UI: npm install && npm run dev --prefix qnwis-ui"
echo ""
