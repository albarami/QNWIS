# Chainlit UI Error Fix - Complete Solution

## Error Symptoms
- Chainlit UI shows: "Unable to complete analysis. The system may be temporarily unavailable."
- Error ID: 1418122195872

## Root Causes Found

### 1. Dataset Name Typo (FIXED ✅)
**Files:** `data/queries/q_unemployment_rate_gcc_latest.yaml`, `data/queries/syn_unemployment_gcc_latest.yaml`

**Issue:** Used `dataset: GCC_STATS` but schema expects `GCC_STAT` (singular)

**Fix Applied:**
```yaml
# Changed from:
dataset: GCC_STATS

# To:
dataset: GCC_STAT
```

### 2. Attribute Name Mismatch (FIXED ✅)
**Files:** `src/qnwis/data/deterministic/cache_access.py`, `src/qnwis/data/deterministic/access.py`

**Issue:** Code was using `spec.id` and `spec.params` but `QueryDefinition` (from YAML) has `spec.query_id` and `spec.parameters`

**Fix Applied:**
- Updated `_key_for()` function to handle both `QuerySpec` and `QueryDefinition` types
- Updated `execute_cached()` to use `spec.query_id` for `QueryDefinition` objects
- Updated `execute()` to handle both types correctly

### 3. CRITICAL - Missing SQL Connector (FIXED ✅)
**New File:** `src/qnwis/data/connectors/sql_executor.py`

**Issue:** YAML queries contain SQL (`employment_share_by_gender.yaml` has `SELECT ... FROM employment_records`) but there was NO connector to execute SQL queries against PostgreSQL.

**Fix Applied:**
- Created new `sql_executor.py` connector that executes `QueryDefinition` SQL against PostgreSQL
- Updated `access.py` to use SQL connector for `QueryDefinition` objects
- Uses existing `src/qnwis/data/deterministic/engine.py` for database connection

## Files Modified

1. ✅ `data/queries/q_unemployment_rate_gcc_latest.yaml` - Fixed dataset name
2. ✅ `data/queries/syn_unemployment_gcc_latest.yaml` - Fixed dataset name
3. ✅ `src/qnwis/data/deterministic/cache_access.py` - Handle QueryDefinition type
4. ✅ `src/qnwis/data/deterministic/access.py` - Handle QueryDefinition type, use SQL connector
5. ✅ `src/qnwis/data/connectors/sql_executor.py` - NEW FILE - SQL query execution

## How to Apply the Fix

### Step 1: Restart the API Server
```bash
# Find the API server process (port 8000)
netstat -ano | findstr ":8000"

# Kill the process (replace PID with actual process ID)
taskkill /F /PID <PID>

# Restart the API server
uvicorn src.qnwis.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Restart the Chainlit UI Server
```bash
# Find the Chainlit process (port 8001)
netstat -ano | findstr ":8001"

# Kill the process (replace PID with actual process ID)
taskkill /F /PID <PID>

# Restart Chainlit UI
chainlit run src/qnwis/ui/chainlit_app_llm.py --port 8001
```

### Step 3: Test the System
Open your browser to `http://localhost:8001` and ask a question like:
- "What is the unemployment rate in Qatar?"
- "Show me employment trends by gender"

## Expected Behavior After Fix

✅ Classification stage completes
✅ Prefetch stage completes
✅ RAG retrieval completes
✅ Agents execute successfully (LabourEconomist, Nationalization, etc.)
✅ Verification completes
✅ Synthesis generates ministerial response
✅ Executive dashboard displays findings

## Database Requirement

Your `.env` file must have:
```env
DATABASE_URL=postgresql://postgres:1234@localhost:5432/qnwis
```

The PostgreSQL database must be running and contain the tables referenced in your YAML queries (e.g., `employment_records`, `gcc_labour_statistics`).

## Testing the Fixes

To verify the fixes without restarting servers:

```bash
# Test that imports work
python -c "from src.qnwis.data.connectors.sql_executor import run_sql_query; print('SQL connector OK')"

# Test query registry loads
python -c "from src.qnwis.agents.base import DataClient; client = DataClient(); print(f'Registry OK: {len(client._registry.all_ids())} queries')"

# Test API endpoint
curl -X POST "http://localhost:8000/api/v1/council/stream" \
  -H "Content-Type: application/json" \
  -d '{"question":"Test","provider":"stub"}' \
  --max-time 5
```

## Summary

The Chainlit error "Unable to complete analysis" was caused by:
1. **Typo in YAML files** (`GCC_STATS` → `GCC_STAT`)
2. **Type mismatch** between `QuerySpec` and `QueryDefinition`
3. **Missing SQL connector** - SQL queries couldn't be executed

All three issues have been fixed. **You must restart both servers** for the changes to take effect.

---

**Next Steps:**
1. Restart API server (port 8000)
2. Restart Chainlit server (port 8001)
3. Test a query in the UI
4. If you still see errors, check that PostgreSQL is running and accessible
