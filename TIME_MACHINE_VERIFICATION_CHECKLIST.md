# Time Machine Module - Verification Checklist

Use this checklist to verify the Time Machine module implementation before deployment.

## Pre-Flight Checks

### 1. File Structure ✓

```bash
# Verify all files exist
ls src/qnwis/analysis/*.py
ls src/qnwis/agents/time_machine.py
ls src/qnwis/agents/prompts/time_machine_prompts.py
ls src/qnwis/cli/qnwis_time.py
ls tests/unit/analysis/*.py
ls tests/unit/agents/test_time_machine.py
ls docs/analysis/step23_time_machine.md
```

**Expected Files** (14 total):
- [x] `src/qnwis/analysis/trend_utils.py`
- [x] `src/qnwis/analysis/change_points.py`
- [x] `src/qnwis/analysis/baselines.py`
- [x] `src/qnwis/analysis/__init__.py`
- [x] `src/qnwis/agents/time_machine.py`
- [x] `src/qnwis/agents/prompts/time_machine_prompts.py`
- [x] `src/qnwis/cli/qnwis_time.py`
- [x] `src/qnwis/orchestration/intent_catalog.yml` (modified)
- [x] `src/qnwis/orchestration/registry.py` (modified)
- [x] `tests/unit/analysis/test_trend_utils.py`
- [x] `tests/unit/analysis/test_change_points.py`
- [x] `tests/unit/analysis/test_baselines.py`
- [x] `tests/unit/analysis/__init__.py`
- [x] `tests/unit/agents/test_time_machine.py`
- [x] `docs/analysis/step23_time_machine.md`

---

## Code Quality Checks

### 2. Syntax Validation ✓

```bash
# Compile all Python files to check for syntax errors
python -m py_compile src/qnwis/analysis/*.py
python -m py_compile src/qnwis/agents/time_machine.py
python -m py_compile tests/unit/analysis/*.py
python -m py_compile tests/unit/agents/test_time_machine.py
```

**Status**: ✅ All files compile successfully

### 3. Linting

```bash
# Run ruff for style checks
ruff check src/qnwis/analysis/
ruff check src/qnwis/agents/time_machine.py
ruff check src/qnwis/cli/qnwis_time.py

# Run mypy for type checking
mypy src/qnwis/analysis/
mypy src/qnwis/agents/time_machine.py

# Run flake8
flake8 src/qnwis/analysis/
flake8 src/qnwis/agents/time_machine.py
```

**Expected**: No errors (or only minor warnings)

---

## Unit Test Execution

### 4. Run Test Suite

```bash
# Run all Time Machine tests
pytest tests/unit/analysis/ -v
pytest tests/unit/agents/test_time_machine.py -v

# Or use the provided script
.\run_time_machine_tests.ps1
```

**Expected Results**:
- [ ] All tests pass (0 failures)
- [ ] No skipped tests
- [ ] No syntax errors
- [ ] Test time < 5 seconds

### 5. Coverage Report

```bash
# Generate coverage report
pytest tests/unit/analysis/ tests/unit/agents/test_time_machine.py \
  --cov=src.qnwis.analysis \
  --cov=src.qnwis.agents.time_machine \
  --cov-report=term-missing \
  --cov-report=html
```

**Expected Coverage**:
- [ ] `trend_utils.py`: >90%
- [ ] `change_points.py`: >90%
- [ ] `baselines.py`: >90%
- [ ] `time_machine.py`: >85%

**Review Coverage Report**:
```bash
# Open HTML report
start htmlcov/index.html  # Windows
```

---

## Integration Verification

### 6. Orchestration Integration

**Check `intent_catalog.yml`**:
```bash
# Verify intents are present
grep -A 5 "time.baseline" src/qnwis/orchestration/intent_catalog.yml
grep -A 5 "time.trend" src/qnwis/orchestration/intent_catalog.yml
grep -A 5 "time.breaks" src/qnwis/orchestration/intent_catalog.yml
```

**Expected**: Each intent has:
- [ ] Description
- [ ] Keywords list
- [ ] Metrics_hint
- [ ] Examples (3-4)
- [ ] Prefetch configuration

**Check `registry.py`**:
```bash
# Verify registrations
grep "TimeMachineAgent" src/qnwis/orchestration/registry.py
grep "time.baseline" src/qnwis/orchestration/registry.py
grep "time.trend" src/qnwis/orchestration/registry.py
grep "time.breaks" src/qnwis/orchestration/registry.py
```

**Expected**:
- [ ] `TimeMachineAgent` imported
- [ ] Agent instantiated in `create_default_registry()`
- [ ] Three `registry.register()` calls

### 7. CLI Verification (Optional)

```bash
# Test CLI help
python -m src.qnwis.cli.qnwis_time --help

# Test with mock data (will fail if DataClient not configured)
python -m src.qnwis.cli.qnwis_time \
  --intent time.baseline \
  --metric retention \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --verbose
```

**Expected**:
- [ ] Help text displays
- [ ] Arguments parsed correctly
- [ ] Error message if data not available (expected)

---

## Code Review Checklist

### 8. Analysis Modules

**`trend_utils.py`**:
- [ ] All functions have type hints
- [ ] Docstrings with examples
- [ ] Edge case handling (zeros, empty lists)
- [ ] No external dependencies (NumPy/Pandas)

**`change_points.py`**:
- [ ] CUSUM algorithm correct
- [ ] Z-score calculation correct
- [ ] Handles constant series gracefully
- [ ] Returns empty lists for insufficient data

**`baselines.py`**:
- [ ] Seasonal baseline uses phase averaging
- [ ] MAD-based bands (robust)
- [ ] Handles small samples
- [ ] Percentage gaps handle zero baseline

### 9. Agent Implementation

**`time_machine.py`**:
- [ ] Uses `DataClient.run()` exclusively
- [ ] Wraps derived results with `make_derived_query_result()`
- [ ] Validates inputs (metric, date ranges)
- [ ] Raises clear error messages
- [ ] Returns citation-ready narratives
- [ ] Includes reproducibility snippets

**`time_machine_prompts.py`**:
- [ ] SYSTEM_CONTEXT emphasizes citation discipline
- [ ] BASELINE prompt specifies table structure
- [ ] TREND prompt includes growth rates
- [ ] BREAKS prompt requires audit trail

### 10. Test Quality

**Test Files**:
- [ ] Each test has clear docstring
- [ ] Test names follow `test_<behavior>` pattern
- [ ] Edge cases tested (zeros, negatives, empty)
- [ ] Mock DataClient used for isolation
- [ ] No external data dependencies

---

## Documentation Review

### 11. Check Documentation

**`step23_time_machine.md`**:
- [ ] Overview section
- [ ] Architecture diagram/description
- [ ] API reference for all functions
- [ ] CLI usage examples
- [ ] Math notes for algorithms
- [ ] Testing strategy
- [ ] Performance characteristics
- [ ] Runbook for common tasks

**`STEP23_TIME_MACHINE_IMPLEMENTATION_COMPLETE.md`**:
- [ ] Executive summary
- [ ] File inventory
- [ ] Feature descriptions
- [ ] Integration notes
- [ ] Test coverage summary
- [ ] Known limitations
- [ ] Next steps

---

## Final Approval Checklist

### Before Merge

- [ ] All unit tests pass
- [ ] Coverage >90% for analysis modules
- [ ] Linters pass (ruff, mypy, flake8)
- [ ] No syntax errors
- [ ] Orchestration integration verified
- [ ] Documentation complete
- [ ] Code review by team member

### Post-Merge Tasks

- [ ] Create query YAML definitions for time-series
- [ ] Run integration tests with real data
- [ ] Performance benchmark (confirm <50ms)
- [ ] User acceptance testing (Ministry of Labour)
- [ ] Update main README with Time Machine section

---

## Quick Test Command

```bash
# Run everything in one go
pytest tests/unit/analysis/ tests/unit/agents/test_time_machine.py \
  --cov=src.qnwis.analysis \
  --cov=src.qnwis.agents.time_machine \
  --cov-report=term-missing \
  --cov-report=html \
  -v
```

---

## Troubleshooting

### Common Issues

**Import Errors**:
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/Mac
$env:PYTHONPATH = "$(pwd)"                # PowerShell
```

**Test Discovery Issues**:
```bash
# Verify __init__.py exists in test directories
ls tests/__init__.py
ls tests/unit/__init__.py
ls tests/unit/analysis/__init__.py
```

**Module Not Found**:
```bash
# Check package structure
python -c "import src.qnwis.analysis; print('OK')"
python -c "from src.qnwis.agents.time_machine import TimeMachineAgent; print('OK')"
```

---

## Approval Sign-Off

**Implementation**: ✅ Complete  
**Tests**: ⏳ Pending Execution  
**Linting**: ⏳ Pending  
**Documentation**: ✅ Complete  
**Integration**: ✅ Complete  

**Approved By**: _________________  
**Date**: _________________  
**Notes**: _________________

---

**Last Updated**: 2025-11-08  
**Module Version**: 1.0  
**Status**: Ready for Testing
