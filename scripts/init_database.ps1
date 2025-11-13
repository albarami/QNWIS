# QNWIS Database Initialization Script (PowerShell)
# Initializes database schema and seeds production data
#
# Usage:
#   .\scripts\init_database.ps1
#   .\scripts\init_database.ps1 -Preset demo
#   .\scripts\init_database.ps1 -Preset full

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('demo', 'full')]
    [string]$Preset = 'demo'
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "QNWIS DATABASE INITIALIZATION" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if DATABASE_URL is set
if (-not $env:DATABASE_URL) {
    Write-Host "❌ DATABASE_URL environment variable not set" -ForegroundColor Red
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  PostgreSQL: `$env:DATABASE_URL = 'postgresql://user:pass@localhost:5432/qnwis'"
    Write-Host "  SQLite:     `$env:DATABASE_URL = 'sqlite:///./qnwis.db'"
    Write-Host ""
    exit 1
}

Write-Host "📊 Database URL: $env:DATABASE_URL" -ForegroundColor Yellow
Write-Host ""
Write-Host "Configuration: $Preset" -ForegroundColor Yellow
Write-Host ""

# Step 1: Create database schema
Write-Host "1️⃣  Creating database schema..." -ForegroundColor Green
Write-Host "   Tables: employment_records, gcc_labour_statistics, vision_2030_targets"
Write-Host "   Tables: ilo_labour_data, world_bank_indicators, qatar_open_data"
Write-Host "   Views: employment_summary_monthly, qatarization_summary"
Write-Host ""

try {
    # Try psql first
    $psqlPath = Get-Command psql -ErrorAction SilentlyContinue
    
    if ($psqlPath) {
        psql $env:DATABASE_URL -f data\schema\lmis_schema.sql
        Write-Host "   ✅ Schema created via psql" -ForegroundColor Green
    } else {
        # Fallback to Python
        python -c @"
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv('DATABASE_URL'))
with open('data/schema/lmis_schema.sql', 'r', encoding='utf-8') as f:
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
"@
    }
} catch {
    Write-Host "   ❌ Failed to create schema: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Seed production data
Write-Host "2️⃣  Seeding production data..." -ForegroundColor Green
Write-Host ""

try {
    python scripts\seed_production_database.py --preset $Preset
} catch {
    Write-Host "   ❌ Failed to seed data: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Verify installation
Write-Host "3️⃣  Verifying database..." -ForegroundColor Green
Write-Host ""

try {
    python -c @"
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
"@
} catch {
    Write-Host "   ⚠️  Verification warnings: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ DATABASE INITIALIZATION COMPLETE" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  • Test queries: python scripts/test_query_loading.py"
Write-Host "  • Start API: python -m uvicorn qnwis.api.server:app --reload"
Write-Host "  • Launch UI: chainlit run apps/chainlit/app.py"
Write-Host ""
