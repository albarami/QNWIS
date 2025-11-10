# Fix Placeholder Issues to Pass Readiness Gate

The gate found **real code quality issues**. Here's how to fix them:

## Issues to Fix

### 1. Silent Exception Handling (3 instances)

**File:** `src/qnwis/agents/utils/derived_results.py`

**Lines 94 & 99:** Replace silent `pass` with logging:

```python
# BEFORE (Line 92-94)
try:
    asof_dates.append(date.fromisoformat(value.asof_date))
except ValueError:
    pass

# AFTER
import logging
logger = logging.getLogger(__name__)

try:
    asof_dates.append(date.fromisoformat(value.asof_date))
except ValueError:
    logger.debug(f"Skipping invalid asof_date format: {value.asof_date}")
```

**Line 82 in `cache_access.py`:** Similar fix needed.

### 2. Abstract Methods Without Decorator (3 instances)

**File:** `src/qnwis/data/cache/backends.py`

**Lines 23, 27, 31:** Add proper `@abstractmethod`:

```python
# BEFORE
class CacheBackend:
    def get(self, key: str) -> str | None:
        raise NotImplementedError

# AFTER
from abc import ABC, abstractmethod

class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None:
        """Retrieve cached value by key."""
        ...
    
    @abstractmethod
    def set(self, key: str, value: str, ttl_s: int | None = None) -> None:
        """Store value with optional TTL in seconds."""
        ...
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove cached value by key."""
        ...
```

## After Fixing

Run the gate again:
```powershell
python src\qnwis\scripts\qa\readiness_gate.py
```

Expected result: Gate will proceed to next validation (linters_and_types).

## Why These Are Real Issues

1. **Silent pass = Hidden bugs:** Errors disappear without trace
2. **raise NotImplementedError without @abstractmethod:** Not proper Python interface pattern
3. **Production code standards:** These would fail code review in any serious project

The gate is doing its job - protecting your code quality.
