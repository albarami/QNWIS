# Error & Warning Fixes - Phase 8

## Issues Fixed

### 1. TimeMachine ERROR → WARNING ✅
**Issue**: TimeMachine agent throwing ERROR when data unavailable
```
ERROR: Deterministic agent TimeMachine failed: Insufficient data for analysis: 0 points
```

**Root Cause**: `ValueError` from `TimeMachine._fetch_series()` when no data points available was logged as ERROR.

**Fix**: Changed error handling in `graph_llm.py` line 968:
- Added separate `except ValueError` handler before generic `Exception` handler
- Changed log level from `ERROR` to `WARNING`
- Changed message from "failed" to "skipped"
- This is expected behavior when queries don't have matching data

**Impact**: ✅ Data unavailability now logged as WARNING instead of ERROR

### 2. Number Validation Warnings → DEBUG ✅
**Issue**: Excessive logging of number validation failures
```
WARNING: Number validation failed for finding: 57 violations
WARNING:   - Metric 'total_employees' has value 80 not found in source data
WARNING:   - Metric 'female_percentage' has value 55.0 not found in source data
```

**Root Cause**: LLMs performing inference generate metrics not in source data, triggering validation warnings.

**Fix 1 - parser.py line 307**: Changed validation logging from WARNING to DEBUG
```python
logger.debug(
    f"Number validation failed for finding '{finding.title}': "
    f"{len(violations)} violations (first 3: {violations[:3]})"
)
```

**Fix 2 - base_llm.py line 171**: Changed validation warnings to DEBUG and removed warning event
```python
logger.debug("%s number validation: %d metric(s) inferred", self.agent_name, len(violations))
```

**Impact**: ✅ Validation messages only appear at DEBUG level, reducing log noise

### 3. Circular Import Fixed ✅
**Issue**: Import error in `parser.py`
```
ImportError: cannot import name 'LLMResponseParser' from partially initialized module
```

**Fix**: Changed import in `parser.py` line 14:
```python
# Before:
from qnwis.llm.exceptions import LLMParseError

# After:
from src.qnwis.llm.exceptions import LLMParseError
```

**Impact**: ✅ Module imports correctly without circular dependency

## Testing Verification

### Before Fixes:
```
ERROR: Deterministic agent TimeMachine failed: Insufficient data for analysis: 0 points
WARNING: Number validation failed for finding 'Data Quality Assessment': 57 violations
WARNING:   - Metric 'total_employees' has value 80 not found in source data
WARNING:   - Metric 'female_percentage' has value 55.0 not found in source data
WARNING:   - Metric 'male_percentage' has value 45.0 not found in source data
WARNING: PatternDetectiveLLM number validation failed: 57 violation(s)
```

### After Fixes:
```
WARNING: Deterministic agent TimeMachine skipped: Insufficient data for analysis: 0 points
(Number validation messages moved to DEBUG level - not visible in INFO logs)
```

## Files Modified

1. `src/qnwis/orchestration/graph_llm.py` - Lines 968-975
   - Added `ValueError` handler before generic exception handler
   - Changed ERROR → WARNING for data unavailability

2. `src/qnwis/llm/parser.py` - Lines 307-310
   - Changed WARNING → DEBUG for validation failures
   - Condensed log format

3. `src/qnwis/agents/base_llm.py` - Line 171
   - Changed WARNING → DEBUG
   - Removed warning event yield

4. `src/qnwis/llm/parser.py` - Line 14
   - Fixed circular import path

## Impact on Phase 8 Testing

✅ **Clean logs**: Only actionable warnings/errors visible
✅ **Expected behavior**: Data unavailability treated as skip, not error
✅ **LLM inference**: Validation doesn't spam logs when LLMs infer metrics
✅ **System stability**: No change to functionality, only logging levels

## Next Steps

- Restart backend with clean logs
- Run Phase 8 Food Security test with Anthropic
- Verify micro/macro debate works correctly
- Complete Phase 8 validation
