# Contributing to QNWIS

## Principles

This is an **enterprise-grade system** for Qatar's Ministry of Labour. All contributions must follow these principles:

### 1. Root Cause Fixes Only
- ❌ **NO workarounds or quick fixes**
- ✅ **Always** analyze root cause
- ✅ **Always** fix properly
- ✅ **Always** document why the fix works

### 2. Enterprise-Grade Quality
- ✅ Comprehensive error handling
- ✅ Graceful degradation
- ✅ Clear error messages
- ✅ Production-ready code
- ✅ Full test coverage

### 3. Zero Fabrication
- ✅ All data must be verifiable
- ✅ Mandatory citations for all facts
- ✅ Clear confidence scores
- ✅ Honest uncertainty

### 4. Documentation
- ✅ Code comments for complex logic
- ✅ Docstrings for all functions
- ✅ README updates when needed
- ✅ Implementation reports for major changes

---

## Development Workflow

### 1. Before Starting
```bash
# Pull latest
git pull origin main

# Create feature branch
git checkout -b feat/your-feature-name
```

### 2. Make Changes
- Write code following existing patterns
- Add comprehensive error handling
- Write tests for new functionality
- Update documentation

### 3. Testing
```bash
# Run all tests
pytest

# Test specific functionality
python test_your_feature.py

# Verify data integrity
python scripts/verify_postgres_population.py
```

### 4. Commit
```bash
# Organized commits by logical unit
git add file1.py file2.py
git commit -m "feat(module): Brief description

Detailed explanation:
- What was added
- Why it was needed
- How it works

Status: Production-ready"
```

### 5. Pull Request
- Clear title and description
- Link to any related issues
- Explain root cause for bug fixes
- Show test results
- Update documentation

---

## Code Standards

### Python
- **PEP 8 compliant**
- **Type hints everywhere**
- **Comprehensive docstrings**
- **Error handling for all edge cases**

Example:
```python
def extract_skills(cv_text: str) -> Dict[str, List[str]]:
    """
    Extract explicit and inferred skills from CV text.
    
    Args:
        cv_text: Raw CV text in Arabic or English
        
    Returns:
        Dictionary with skill categories and confidence scores
        
    Raises:
        ValueError: If cv_text is empty or invalid
    """
    if not cv_text or not cv_text.strip():
        raise ValueError("CV text cannot be empty")
    
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Skill extraction failed: {e}")
        return {"explicit": [], "inferred": []}
```

### SQL
- **Use parameterized queries** (never string interpolation)
- **Proper indexes** on all queries
- **Transaction management**

Example:
```python
# ✅ Good - Parameterized query
cursor.execute(
    "INSERT INTO world_bank_indicators (country_code, indicator_code, year, value) "
    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
    (country_code, indicator_code, year, value)
)

# ❌ Bad - String interpolation (SQL injection risk!)
cursor.execute(
    f"INSERT INTO table VALUES ('{country_code}', '{indicator_code}')"
)
```

### Documentation
- **Clear and concise**
- **Examples included**
- **Troubleshooting section**
- **Links to related docs**

---

## Commit Message Format

Use conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation only
- **style**: Code style (formatting, no logic change)
- **refactor**: Code refactoring
- **test**: Adding tests
- **chore**: Maintenance tasks

### Examples

#### ✅ Good Commit
```
feat(etl): Add World Bank ETL script

Root cause: Need to cache World Bank data in PostgreSQL
for instant queries instead of 2+ minute API calls.

Implementation:
- Add etl_world_bank_to_postgres.py
- Fetch 128 indicators (2010-2024)
- Use ON CONFLICT for idempotent inserts
- Add comprehensive error handling
- Verify all data written

Result: 128 rows loaded, <100ms query time

Status: Production-ready, tested
```

#### ❌ Bad Commit
```
fix stuff

changed some files
```

---

## Error Handling

### ✅ Good Error Handling
```python
try:
    result = await api.fetch_data()
    if not result:
        logger.warning("API returned no data")
        return []
except ConnectionError as e:
    logger.error(f"API connection failed: {e}")
    logger.info("Falling back to cached data")
    return self._query_cache()
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    return []
```

### ❌ Bad Error Handling
```python
result = await api.fetch_data()  # What if it fails?
```

---

## Testing Standards

### Test Structure
```
tests/
├── test_expected_behavior.py  # Normal use case
├── test_edge_cases.py         # Boundary conditions
└── test_failures.py           # Error handling
```

### Example Test
```python
import pytest
from qnwis.data.apis.world_bank_api import WorldBankAPI

@pytest.mark.asyncio
async def test_world_bank_fetch_indicator():
    """Test fetching a single indicator from World Bank API."""
    api = WorldBankAPI()
    
    # Test successful fetch
    result = await api.get_indicator(
        country_code="QAT",
        indicator_code="NY.GDP.MKTP.CD",
        start_year=2020,
        end_year=2023
    )
    
    assert result is not None
    assert len(result) > 0
    assert all("year" in item for item in result)
    assert all("value" in item for item in result)

@pytest.mark.asyncio
async def test_world_bank_invalid_country():
    """Test graceful handling of invalid country code."""
    api = WorldBankAPI()
    
    result = await api.get_indicator(
        country_code="INVALID",
        indicator_code="NY.GDP.MKTP.CD"
    )
    
    # Should return empty list, not crash
    assert result == []
```

---

## File Organization

### Maximum File Size
- **500 lines maximum** per file
- Split into modules if approaching limit

### Module Organization
```
src/qnwis/
├── agents/          # Agent implementations
├── orchestration/   # Workflow orchestration
├── data/           # Data access layer
│   ├── apis/       # External API connectors
│   ├── queries/    # SQL queries
│   └── cache/      # Caching logic
├── models/         # Data models (Pydantic)
└── utils/          # Utility functions
```

---

## Security Requirements

### API Keys
- **NEVER hardcode API keys**
- **Use environment variables**
- **Add to .gitignore**

```python
# ✅ Good
import os
api_key = os.getenv("BRAVE_API_KEY")

# ❌ Bad
api_key = "BSA1234567890"  # NEVER DO THIS!
```

### Input Validation
```python
from pydantic import BaseModel, validator

class IndicatorRequest(BaseModel):
    country_code: str
    indicator_code: str
    
    @validator('country_code')
    def validate_country_code(cls, v):
        if len(v) != 3:
            raise ValueError("Country code must be 3 characters")
        return v.upper()
```

### SQL Injection Prevention
- **Always use parameterized queries**
- **Never concatenate SQL strings**

---

## Performance Standards

### Latency Requirements
- **Stage A:** <50ms
- **Stage B:** <60ms
- **Stage C:** <40ms
- **Overall query:** <100ms

### Optimization Tips
- Use database indexes
- Implement caching
- Batch API requests
- Profile slow operations

---

## Documentation Requirements

### For New Features
1. Update README.md
2. Add docstrings to all functions
3. Create example usage
4. Add troubleshooting section
5. Update CHANGELOG.md

### For Bug Fixes
1. Document root cause
2. Explain the fix
3. Add regression test
4. Update relevant docs

---

## Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows PEP 8 style guide
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] Tests added/updated
- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`ruff check src/ tests/`)
- [ ] Type checking passes (`mypy src/ --strict`)
- [ ] Documentation updated
- [ ] No secrets in code
- [ ] Commit messages follow convention
- [ ] PR description explains changes
- [ ] Performance requirements met

---

## Questions?

Open an issue with the **question** label, or contact the development team.

---

## Remember

**This system serves Qatar's Ministry of Labour.**

Every line of code matters.  
**No shortcuts. No compromises.**  
**Enterprise-grade quality only.**
