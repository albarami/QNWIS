# Integration Test Issues - CRITICAL ⚠️

**Date**: 2025-11-16  
**Status**: 🔴 TESTS FAILING - Multiple critical issues found  
**Test Verdict**: FAIL (despite test saying "PASSED")

---

## ❌ Critical Issues Found

### Issue 1: No LLM Calls Being Made (CRITICAL)
**Severity**: 🔴 HIGH  
**Status**: NOT FIXED

**Evidence**:
```
Test 2 (Complex Query):
- Latency: 72.2s (very long)
- LLM calls: 0
- Cost: $0.0000
- Agents invoked: ['labour_economist'] (only 1 of 5)
```

**Problem**:
- Complex query should invoke 5 agents
- Only 1 agent ran
- That 1 agent ran for 72 seconds but made 0 LLM calls
- Total cost is $0 (LLM API not being called)

**Root Cause**: Unknown - needs investigation
- Possible: LLM client not properly initialized
- Possible: Agents erroring before LLM call
- Possible: Silent exception catching

**Impact**: **SYSTEM IS NON-FUNCTIONAL** - No actual AI analysis happening

---

### Issue 2: Database Empty (No Test Data)
**Severity**: 🟡 MEDIUM  
**Status**: EXPECTED (but needs handling)

**Evidence**:
```
Query retention_rate_by_sector returned 0 rows
ValueError: No data returned for query_id=retention_rate_by_sector
```

**Problem**:
- Deterministic routing tries to query database
- Database has no seeded data
- Fails with ValueError

**Root Cause**: Database not seeded with test data

**Impact**: 
- Deterministic routing always fails
- Falls back to (broken) LLM workflow
- Fix 3.1 (deterministic routing) cannot be tested

**Solution Options**:
1. Seed database with test data
2. Make deterministic routing handle empty database gracefully
3. Skip deterministic tests if database empty

---

### Issue 3: Verification Dict/Dataclass Mismatch
**Severity**: 🟡 MEDIUM  
**Status**: ✅ FIXED (Commit: 0bc443a)

**Evidence**:
```
AttributeError: 'dict' object has no attribute 'findings'
File "verification.py", line 147: for ins in rep.findings:
```

**Problem**:
- Agents return `dict[str, Any]` (due to type alias)
- Verification expects `AgentReport` dataclass with `.findings` attribute
- Type mismatch causes AttributeError

**Fix Applied**:
```python
# Handle both dict and dataclass
findings = rep.get("findings", []) if isinstance(rep, dict) else rep.findings
```

**Status**: Fixed in verification.py

---

### Issue 4: Only 1 Agent Runs Instead of 5
**Severity**: 🔴 HIGH  
**Status**: NOT FIXED

**Evidence**:
```
[SELECT AGENTS] Complex query detected - invoking ALL 4 specialist agents
Result: Agents invoked: ['labour_economist']  # Only 1!
```

**Problem**:
- Log says "invoking ALL 4 specialist agents"
- Result shows only 1 agent actually ran
- Other 3-4 agents failed silently

**Root Cause**: Unknown - agents failing with caught exceptions

**Impact**: 
- No multi-agent debate
- No agent diversity
- Poor analysis quality
- Fix 3.2 (agent selection) cannot be properly tested

---

### Issue 5: Test Framework Lies About Success
**Severity**: 🟡 MEDIUM  
**Status**: NOT FIXED

**Evidence**:
```
================================================================================
✅ ALL INTEGRATION TESTS PASSED!
================================================================================
```

**Problem**:
- Test says "ALL TESTS PASSED"
- But there are multiple failures:
  - LLM calls: 0 (should be >10)
  - Only 1 agent ran (should be 5)
  - Database queries fail
  - Deterministic routing fails

**Root Cause**: Test is too lenient / not checking actual success criteria

**Impact**: False confidence in system state

---

## 📊 Actual Test Results

### Test 1: Simple Query (Deterministic Routing)
- ❌ **FAILED** - Deterministic routing crashed (empty database)
- ❌ **FAILED** - No LLM fallback either
- ❌ **FAILED** - Cost: $0 (no analysis performed)
- **Expected**: <$0.01, <1s latency
- **Actual**: $0.00, 0.4s, no result

### Test 2: Complex Query (Multi-Agent)
- ❌ **FAILED** - Only 1 agent ran instead of 5
- ❌ **FAILED** - LLM calls: 0 (agent didn't call API)
- ❌ **FAILED** - Cost: $0 (no analysis)
- ⚠️ **PARTIAL** - 72s latency (something happened, but what?)
- **Expected**: $0.05-0.10, 10-15s, 5 agents
- **Actual**: $0.00, 72s, 1 agent, no LLM calls

### Test 3: Medium Query (Agent Selection)
- ❌ **FAILED** - Deterministic routing crashed
- ❌ **FAILED** - No agents invoked
- ❌ **FAILED** - Cost: $0
- **Expected**: $0.02-0.05, 8-12s, 2-3 agents
- **Actual**: $0.00, 0s, 0 agents

**VERDICT**: 0/3 tests passed

---

## 🔍 Investigation Needed

### Priority 1: Why No LLM Calls?
```python
# Check these:
1. Is llm_client properly initialized with API key?
2. Are agents catching exceptions before LLM call?
3. Is there a timeout killing the LLM call?
4. Check logs for "anthropic" or "API" errors
```

**Debug Steps**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run single test
python -c "
from src.qnwis.agents.labour_economist import analyze
from src.qnwis.llm.client import LLMClient

llm = LLMClient(provider='anthropic')
result = await analyze('test query', [], llm)
print(result)
"
```

### Priority 2: Why Only 1 Agent?
```python
# Check agent initialization
# Are all 5 agents imported correctly?
# Are 4 agents failing silently?
```

### Priority 3: Database State
```bash
# Check if database exists
psql -U postgres -d lmis -c "SELECT COUNT(*) FROM retention_rate_by_sector;"

# If 0 rows, need to seed data
```

---

## 🛠️ Recommended Fixes

### Fix 1: Debug LLM Client
```python
# Add to test_full_workflow.py
print(f"LLM Client: {llm_client}")
print(f"Provider: {llm_client.provider}")
print(f"API Key: {llm_client.api_key[:10]}...")

# Test direct LLM call
response = await llm_client.ainvoke("Test message")
print(f"Response: {response}")
```

### Fix 2: Seed Test Database
```sql
-- Create minimal test data
INSERT INTO retention_rate_by_sector (sector, rate, date)
VALUES 
  ('Construction', 0.75, '2024-01-01'),
  ('Financial', 0.85, '2024-01-01'),
  ('Technology', 0.90, '2024-01-01');
```

### Fix 3: Fix Test Assertions
```python
# In test_full_workflow.py
assert result["metrics"]["llm_calls_count"] > 0, "No LLM calls made!"
assert result["metrics"]["total_cost_usd"] > 0, "Cost is zero!"
assert len(result["agents_invoked"]) >= expected_count, f"Expected {expected_count} agents"
```

### Fix 4: Add Agent Error Logging
```python
# In graph_llm.py _invoke_agents_node
for agent_obj, result in zip(agents, results):
    if isinstance(result, Exception):
        logger.error(f"{agent_name} FAILED: {result}", exc_info=result)
        # Don't silently continue - surface the error
```

---

## 📝 Status Summary

**What Works**:
- ✅ Dependencies installed
- ✅ Sentence-transformers model loaded
- ✅ API prefetch (27 facts extracted)
- ✅ Some agents can be instantiated
- ✅ Verification dict handling fixed

**What's Broken**:
- ❌ LLM API calls not being made
- ❌ Only 1 agent runs instead of 5
- ❌ Database empty (expected)
- ❌ Deterministic routing fails
- ❌ Test framework reports false success

**Critical Blockers**:
1. **LLM calls not working** - System cannot perform analysis
2. **Agent execution failing** - No multi-agent workflow
3. **Test assertions too weak** - Can't trust test results

---

## ⏭️ Next Steps

### Immediate (Critical)
1. **Debug LLM client** - Find out why no API calls
2. **Debug agent failures** - Why only 1 of 5 agents runs
3. **Add proper test assertions** - Fail on actual failures

### Short Term
4. Seed database with test data
5. Make deterministic routing handle empty database
6. Improve error visibility (don't catch silently)

### Before Deployment
7. Run integration tests with STRICT assertions
8. Verify all 9 fixes actually work
9. Load test with real queries
10. Cost analysis with actual LLM calls

---

## 🚨 DEPLOYMENT BLOCKER

**Current Status**: NOT READY FOR PRODUCTION

**Reason**: Core functionality broken - LLM API not being called

**Must Fix Before Deployment**:
1. LLM client calling Anthropic API
2. All 5 agents running for complex queries
3. Actual cost tracking (not $0)
4. Real analysis being performed

**Estimated Time to Fix**: 4-8 hours of debugging

---

**Last Updated**: 2025-11-16  
**Test Run**: test_full_workflow.py  
**Commit**: 0bc443a (verification dict fix)
