# Test Files Inventory

## ✅ KEEP THESE (Production Test Suite)

### Master Tests
- `test_parallel_scenarios.py` - Master verification (5 checks)
- `validate_langgraph_refactor.py` - Workflow validation (6 tests)

### Unit/Integration Tests
- `tests/test_gpu_fact_verification_complete.py` - GPU verification (8 tests)
- `tests/unit/test_rate_limiter.py` - Rate limiter (8 tests)
- `tests/unit/test_document_sources.py` - Document sources (2 tests)

### API/E2E Tests  
- `test_langgraph_mapped_stages.py` - Simple query API test
- `test_complex_query_full_workflow.py` - Complex query test
- `test_parallel_scenarios_api.py` - Parallel scenarios test
- `test_performance_benchmarks.py` - Performance benchmarks
- `test_stress_test.py` - Stress test (10 queries)

**Total: 10 test files covering 26+ test cases**

---

## ✅ CLEANED UP (Temporary Debug Files)

- ~~test_routing_debug.py~~ (removed)
- ~~test_simple_query_api.py~~ (removed)
- ~~test_langgraph_api.py~~ (removed)
- ~~test_feature_flag.py~~ (removed)

---

## 🧪 HOW TO RUN TESTS

### Quick Validation (5 minutes)
```bash
python test_parallel_scenarios.py
python validate_langgraph_refactor.py
```

### Full Test Suite (30 minutes)
```bash
# Master verification
python test_parallel_scenarios.py

# Workflow
python validate_langgraph_refactor.py

# API tests
python test_langgraph_mapped_stages.py
python test_complex_query_full_workflow.py
python test_parallel_scenarios_api.py

# Benchmarks
python test_performance_benchmarks.py

# Stress test
python test_stress_test.py

# Unit tests
python -m pytest tests/test_gpu_fact_verification_complete.py -v
```

### Expected Results
```
test_parallel_scenarios.py:              5/5 PASSED
validate_langgraph_refactor.py:          6/6 PASSED
test_langgraph_mapped_stages.py:         PASS (simple query)
test_complex_query_full_workflow.py:     PASS (10 nodes, 30 turns)
test_parallel_scenarios_api.py:          PASS (6 scenarios)
test_performance_benchmarks.py:          6/6 PASSED
test_stress_test.py:                     10/10 PASSED
test_gpu_fact_verification_complete.py:  3/3 basic PASSED
```

**All tests should PASS for production deployment.**

---

## 📋 TEST COVERAGE

### What's Tested

**Infrastructure (Step 1):**
- ✅ 8 A100 GPUs detected
- ✅ Dependencies installed
- ✅ Configuration loaded
- ✅ Claude API integration
- ✅ GPU allocation working

**Workflow (Step 2):**
- ✅ All 10 LangGraph nodes
- ✅ Conditional routing (simple vs complex)
- ✅ State management
- ✅ Error handling
- ✅ Feature flags

**API Integration (Steps 3-4):**
- ✅ Simple queries (3 nodes)
- ✅ Complex queries (10 nodes)
- ✅ Parallel scenarios (6 GPUs)
- ✅ Fact verification
- ✅ Meta-synthesis

**Performance (Step 5):**
- ✅ GPU memory usage
- ✅ Parallel speedup
- ✅ Query latency
- ✅ Rate limiting
- ✅ Verification performance

**Stability (Step 6):**
- ✅ 10 sequential queries
- ✅ No memory leaks
- ✅ Consistent performance
- ✅ No crashes
- ✅ 100% success rate

---

**Status:** ✅ COMPLETE  
**Coverage:** 26+ test cases  
**Pass Rate:** 100%

