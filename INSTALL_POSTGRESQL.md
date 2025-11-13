# PostgreSQL Installation for QNWIS

## ✅ PostgreSQL is the CORRECT database for this system

The system requires PostgreSQL (not SQLite) for production use.

---

## 🔽 STEP 1: Download PostgreSQL

**Download PostgreSQL 15.x for Windows:**

https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

**Click:** PostgreSQL 15.x Windows x86-64

**File size:** ~300 MB

---

## ⚙️ STEP 2: Install PostgreSQL

1. **Run the installer** (postgresql-15.x-windows-x64.exe)

2. **Installation wizard:**
   - Installation Directory: Default (C:\Program Files\PostgreSQL\15)
   - Select Components: ✅ All (PostgreSQL Server, pgAdmin 4, Command Line Tools)
   - Data Directory: Default
   - **Password for postgres user:** `qnwis_admin_2024` (IMPORTANT: Remember this!)
   - Port: `5432` (default)
   - Locale: Default

3. **Complete installation** (takes 2-3 minutes)

4. **Skip Stack Builder** when prompted

---

## 🗄️ STEP 3: Create QNWIS Database

Open PowerShell **AS ADMINISTRATOR** and run:

```powershell
# Set PostgreSQL path
$env:Path += ";C:\Program Files\PostgreSQL\15\bin"

# Create database
createdb -U postgres qnwis

# Verify
psql -U postgres -c "SELECT version();"
```

When prompted for password, enter: `qnwis_admin_2024`

---

## 🔧 STEP 4: Configure QNWIS

Update `.env` file in `d:\lmis_int\`:

```env
DATABASE_URL=postgresql://postgres:qnwis_admin_2024@localhost:5432/qnwis
QNWIS_JWT_SECRET=dev-secret-key-for-testing-change-in-production-2a8f9c3e1b7d
REDIS_URL=redis://disabled
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## 📊 STEP 5: Initialize Database Schema

```powershell
cd d:\lmis_int

# Initialize schema
python -c @"
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv('DATABASE_URL'))
with open('data/schema/lmis_schema.sql', 'r', encoding='utf-8') as f:
    schema_sql = f.read()

with engine.begin() as conn:
    for statement in schema_sql.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                conn.execute(text(statement))
            except Exception as e:
                print(f'Statement: {statement[:50]}...')
                print(f'Warning: {e}')
print('✅ Schema created')
"@
```

---

## 🚀 STEP 6: Start System

```powershell
# Terminal 1 - API Server
python -m uvicorn src.qnwis.api.server:app --host 0.0.0.0 --port 8000

# Terminal 2 - UI
python -m chainlit run src/qnwis/ui/chainlit_app_llm.py --host 0.0.0.0 --port 8001
```

---

## ✅ STEP 7: Test

Open: http://localhost:8001

Ask: "What is Qatar's unemployment rate?"

---

## 🔍 Troubleshooting

### PostgreSQL service not running:
```powershell
Start-Service postgresql-x64-15
```

### Cannot connect:
```powershell
# Test connection
psql -U postgres -d qnwis -c "SELECT 1;"
```

### Password issues:
Reset postgres password:
```powershell
# As Administrator
cd "C:\Program Files\PostgreSQL\15\bin"
.\pg_ctl.exe restart -D "C:\Program Files\PostgreSQL\15\data"
```

---

## 📝 IMPORTANT NOTES

1. **PostgreSQL is REQUIRED** - This is not optional for production
2. **Port 5432** must be available
3. **Password** must match what's in `.env`
4. **Database name** must be `qnwis`

---

**After installation, tell me and I'll configure the system to use it.**
