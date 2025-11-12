# QNWIS Developer Onboarding Guide

**Version:** 1.0.0  
**Audience:** Software engineers joining the QNWIS development team  
**Last Updated:** 2025-01-12

## Welcome

This guide will help you set up your development environment and understand the QNWIS codebase. QNWIS is a production system serving Qatar's Ministry of Labour—code quality and reliability are paramount.

## Prerequisites

### Required Software

- **Python**: 3.11 or higher
- **PostgreSQL**: 14+ (for local development)
- **Redis**: 6+ (for caching and rate limiting)
- **Git**: 2.30+
- **Docker**: 20+ (optional, for containerized development)

### Required Skills

- Python (FastAPI, SQLAlchemy, Pydantic)
- SQL and database design
- REST API development
- Testing (pytest, integration tests)
- Git workflow (feature branches, pull requests)

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/mol-qatar/qnwis.git
cd qnwis
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your local settings:

```bash
# Database
DATABASE_URL=postgresql://qnwis:password@localhost:5432/qnwis_dev
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# Security
SECRET_KEY=your-local-secret-key-min-32-chars
CSRF_SECRET=your-csrf-secret-min-32-chars
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# API
API_V1_PREFIX=/api/v1
RATE_LIMIT_PER_HOUR=100
RATE_LIMIT_BURST=10

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# Development
DEBUG=true
RELOAD=true
```

**Security Note**: Never commit `.env` files. Use `.env.example` as a template only.

### 5. Initialize Database

```bash
# Create database
createdb qnwis_dev

# Run migrations
alembic upgrade head

# Load test data (optional)
python scripts/load_test_data.py
```

### 6. Verify Setup

```bash
# Run tests
pytest tests/ -v

# Start development server
uvicorn src.qnwis.api.server:app --reload --port 8000

# Check health
curl http://localhost:8000/health
```

## Repository Structure

```
qnwis/
├── src/qnwis/              # Main application code
│   ├── agents/             # Multi-agent system (6 specialized agents)
│   │   ├── router.py       # Query routing and classification
│   │   ├── simple.py       # Simple queries (<10s SLO)
│   │   ├── medium.py       # Medium complexity (<30s SLO)
│   │   ├── complex.py      # Complex analysis (<90s SLO)
│   │   ├── scenario.py     # Predictive scenarios
│   │   └── verifier.py     # Result verification and confidence scoring
│   ├── api/                # FastAPI application
│   │   ├── server.py       # App factory and configuration
│   │   ├── routes/         # API endpoints
│   │   ├── middleware/     # Security, logging, rate limiting
│   │   └── dependencies.py # Dependency injection
│   ├── models/             # SQLAlchemy ORM models
│   │   ├── lmis/           # LMIS data tables (60+ tables)
│   │   ├── audit/          # Audit and logging tables
│   │   └── cache/          # Materialized views and cache
│   ├── services/           # Business logic layer
│   │   ├── query.py        # Query processing
│   │   ├── data.py         # Data access (Deterministic Data Layer)
│   │   ├── cache.py        # Redis caching
│   │   └── verification.py # Confidence scoring
│   ├── orchestration/      # LangGraph DAG orchestration
│   │   ├── graph.py        # Agent workflow definitions
│   │   └── state.py        # Shared state management
│   ├── analysis/           # Analytical components
│   │   ├── time_machine.py # Historical analysis
│   │   ├── pattern_miner.py# Pattern discovery
│   │   └── predictor.py    # Forecasting models
│   ├── alerts/             # Alert and notification system
│   └── config.py           # Configuration management
├── tests/                  # Test suite
│   ├── unit/               # Unit tests (fast, isolated)
│   ├── integration/        # Integration tests (DB, Redis, APIs)
│   ├── performance/        # Performance and load tests
│   └── system/             # End-to-end system tests
├── scripts/                # Utility scripts
│   ├── export_openapi.py   # Generate API documentation
│   ├── doc_checks.py       # Validate documentation
│   └── load_test_data.py   # Load test fixtures
├── docs/                   # Documentation
├── ops/                    # Operations and deployment
│   ├── docker/             # Docker configurations
│   └── systemd/            # Systemd service files
├── alembic/                # Database migrations
└── configs/                # Configuration files
```

## Coding Standards

### Python Style

We follow **PEP 8** with these additions:

1. **Type Hints**: Required for all function signatures
2. **Docstrings**: Google-style for all public functions
3. **Line Length**: 100 characters (not 79)
4. **Formatter**: Black (run automatically via pre-commit)
5. **Linter**: Flake8 with configured rules

**Example:**

```python
from typing import Dict, List, Optional
from pydantic import BaseModel

def extract_skills(
    cv_text: str,
    language: str = "en",
    confidence_threshold: float = 0.7
) -> Dict[str, List[str]]:
    """
    Extract explicit and inferred skills from CV text.
    
    Args:
        cv_text: Raw CV text in Arabic or English
        language: Language code (en, ar)
        confidence_threshold: Minimum confidence for skill extraction
        
    Returns:
        Dictionary with skill categories and confidence scores
        
    Raises:
        ValueError: If cv_text is empty or language unsupported
        
    Example:
        >>> skills = extract_skills("Python developer with 5 years experience")
        >>> skills["technical"]
        ["Python", "Software Development"]
    """
    if not cv_text.strip():
        raise ValueError("cv_text cannot be empty")
    
    # Implementation...
    return {"technical": [], "soft": []}
```

### File Organization

**500-Line Limit**: Split files approaching 500 lines into modules.

**Module Structure:**
```python
# 1. Standard library imports
import os
from typing import Dict

# 2. Third-party imports
from fastapi import FastAPI
from sqlalchemy import select

# 3. Local imports
from src.qnwis.models import Employment
from src.qnwis.services import DataService

# 4. Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# 5. Type definitions
QueryResult = Dict[str, Any]

# 6. Functions/classes (alphabetically)
```

### Data Validation

Use **Pydantic** for all data models:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class QueryRequest(BaseModel):
    """Request model for query submission."""
    
    question: str = Field(..., min_length=5, max_length=1000)
    user_id: str = Field(..., regex=r"^[a-z0-9_]+$")
    session_id: Optional[str] = None
    max_response_time: int = Field(default=30, ge=1, le=90)
    
    @validator("question")
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "question": "What is the unemployment rate?",
                "user_id": "analyst_123",
                "max_response_time": 30
            }
        }
```

### Error Handling

**Never swallow exceptions**. Always log and re-raise or handle appropriately:

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def fetch_employment_data(sector: str) -> Optional[Dict]:
    """Fetch employment data for a sector."""
    try:
        result = db.query(Employment).filter_by(sector=sector).first()
        if not result:
            logger.warning(f"No data found for sector: {sector}")
            return None
        return result.to_dict()
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching sector {sector}: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

### No Hardcoded Values

**Bad:**
```python
def connect_db():
    return psycopg2.connect("postgresql://user:pass@localhost/db")
```

**Good:**
```python
from src.qnwis.config import settings

def connect_db():
    return psycopg2.connect(settings.DATABASE_URL)
```

## Testing Strategy

### Test Structure

Every feature requires three types of tests:

```
tests/
├── unit/
│   └── test_skill_extraction.py      # Fast, isolated, mocked
├── integration/
│   └── test_query_pipeline.py        # Real DB/Redis, no external APIs
└── system/
    └── test_end_to_end_query.py      # Full system, realistic scenarios
```

### Writing Tests

**Unit Test Example:**

```python
import pytest
from src.qnwis.services.verification import calculate_confidence

def test_calculate_confidence_high():
    """Test confidence calculation with strong evidence."""
    sources = [
        {"confidence": 0.95, "weight": 1.0},
        {"confidence": 0.92, "weight": 0.8},
    ]
    result = calculate_confidence(sources)
    assert result >= 0.90
    assert result <= 1.0

def test_calculate_confidence_no_sources():
    """Test confidence calculation with no sources."""
    with pytest.raises(ValueError, match="No sources provided"):
        calculate_confidence([])
```

**Integration Test Example:**

```python
import pytest
from sqlalchemy import create_engine
from src.qnwis.services.data import DataService

@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("postgresql://localhost/qnwis_test")
    # Setup and teardown logic
    yield session
    session.close()

def test_fetch_employment_stats(db_session):
    """Test fetching employment statistics from database."""
    service = DataService(db_session)
    result = service.get_employment_stats(sector="construction", quarter="2024-Q3")
    
    assert result is not None
    assert result["sector"] == "construction"
    assert "employment_count" in result
    assert result["data_source"] == "LMIS_PROD"  # Deterministic Data Layer
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=src.qnwis --cov-report=html

# Specific test
pytest tests/unit/test_skill_extraction.py::test_calculate_confidence_high -v

# Performance tests
pytest tests/performance/ -v --benchmark-only
```

### Test Data

Use realistic test data, never mock data:

```python
# tests/fixtures/employment_data.py
EMPLOYMENT_TEST_DATA = [
    {
        "id": 1,
        "quarter": "2024-Q3",
        "sector": "construction",
        "employment_count": 125080,
        "unemployment_rate": 0.032,
        "source": "LMIS_PROD",
        "timestamp": "2024-10-15T14:30:00Z"
    },
    # More realistic records...
]
```

## Key System Concepts

### Deterministic Data Layer

**Critical Contract**: QNWIS never fabricates data. Every response is traceable to source tables.

```python
from src.qnwis.services.data import DataService

# Good: Explicit source tracking
result = data_service.query(
    table="qtr_employment_stats",
    filters={"quarter": "2024-Q3"},
    track_source=True  # Always True in production
)
# result includes: data, source_table, row_ids, timestamp

# Bad: Never do this
result = {"employment": 125000}  # Where did this come from?
```

**Verification**: Every data point includes:
- Source table name
- Row IDs accessed
- Query timestamp
- Data classification level

### Multi-Agent Architecture

Six specialized agents orchestrated via LangGraph:

1. **Router**: Classifies queries (simple/medium/complex)
2. **Simple Agent**: Handles straightforward lookups (<10s)
3. **Medium Agent**: Multi-table joins and aggregations (<30s)
4. **Complex Agent**: Advanced analytics and correlations (<90s)
5. **Scenario Agent**: Predictive "what-if" analysis
6. **Verifier**: Confidence scoring and citation generation

**Agent Communication:**

```python
from src.qnwis.orchestration import QueryState, agent_graph

# Agents communicate via shared state
state = QueryState(
    question="What is the unemployment rate?",
    user_id="analyst_123",
    classification=None,  # Router fills this
    data=None,            # Query agent fills this
    confidence=None,      # Verifier fills this
)

# Execute DAG
result = agent_graph.execute(state)
```

### Performance SLOs

**Non-negotiable targets:**

- Simple queries: < 10 seconds (95th percentile)
- Medium queries: < 30 seconds (95th percentile)
- Complex queries: < 90 seconds (95th percentile)
- Dashboard load: < 3 seconds (95th percentile)

**Monitoring:**

```python
from src.qnwis.monitoring import track_performance

@track_performance(slo_seconds=10, query_type="simple")
def handle_simple_query(question: str) -> Dict:
    # Implementation
    pass
```

### Security Controls (Step 34)

**Always enabled in production:**

1. **HTTPS Only**: TLS 1.2+ required
2. **CSRF Protection**: Token validation on state-changing requests
3. **Rate Limiting**: 100 req/hour default, configurable per user
4. **RBAC**: Role-based access control for all endpoints
5. **Audit Logging**: Complete request/response trail
6. **CSP/HSTS**: Content Security Policy and HTTP Strict Transport Security

**Example:**

```python
from fastapi import Depends, HTTPException
from src.qnwis.api.dependencies import get_current_user, require_role

@app.post("/api/v1/query")
async def submit_query(
    request: QueryRequest,
    user: User = Depends(get_current_user),  # Authentication
    _: None = Depends(require_role("analyst"))  # Authorization
):
    # CSRF token validated by middleware
    # Rate limit checked by middleware
    # Request logged by middleware
    pass
```

## Development Workflow

### Feature Development

1. **Create Feature Branch**
   ```bash
   git checkout -b feat/skill-inference-enhancement
   ```

2. **Write Tests First** (TDD)
   ```bash
   # Create test file
   touch tests/unit/test_skill_inference.py
   
   # Write failing tests
   pytest tests/unit/test_skill_inference.py  # Should fail
   ```

3. **Implement Feature**
   ```python
   # src/qnwis/services/skill_inference.py
   def infer_skills(cv_text: str) -> Dict[str, List[str]]:
       """Implementation..."""
       pass
   ```

4. **Run Tests**
   ```bash
   pytest tests/unit/test_skill_inference.py -v  # Should pass
   pytest tests/ -v  # All tests should pass
   ```

5. **Code Quality Checks**
   ```bash
   # Format code
   black src/ tests/
   
   # Lint
   flake8 src/ tests/
   
   # Type check
   mypy src/
   ```

6. **Commit**
   ```bash
   git add .
   git commit -m "feat(skills): implement 80/20 skill inference with confidence scoring"
   ```

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `test`: Add or update tests
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Maintenance tasks

**Examples:**
```
feat(agents): implement skill inference with 80/20 distribution

- Add skill extraction from CV text
- Implement confidence scoring
- Add unit and integration tests

Closes #123
```

```
fix(matching): resolve latency issue in Stage A pipeline

Stage A was exceeding 50ms SLO due to N+1 query pattern.
Implemented eager loading and reduced queries from 100+ to 3.

Performance: 45ms avg (was 120ms)
```

### Pull Request Process

1. **Create PR** with description:
   - What changed
   - Why it changed
   - How to test
   - Performance impact
   - Security considerations

2. **Automated Checks**:
   - All tests pass
   - Code coverage ≥ 80%
   - No linting errors
   - Documentation updated

3. **Code Review**: Requires 2 approvals

4. **Merge**: Squash and merge to main

## Common Tasks

### Adding a New API Endpoint

```python
# src/qnwis/api/routes/employment.py
from fastapi import APIRouter, Depends
from src.qnwis.api.dependencies import get_db, get_current_user
from src.qnwis.models.responses import EmploymentResponse

router = APIRouter(prefix="/employment", tags=["employment"])

@router.get("/{sector}", response_model=EmploymentResponse)
async def get_employment_by_sector(
    sector: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get employment statistics for a specific sector.
    
    Requires authentication and analyst role.
    """
    # Implementation
    pass
```

### Adding a Database Migration

```bash
# Create migration
alembic revision -m "add_skill_inference_table"

# Edit migration file
# alembic/versions/xxx_add_skill_inference_table.py

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Adding a New Test

```python
# tests/integration/test_new_feature.py
import pytest
from src.qnwis.services.new_feature import NewFeatureService

@pytest.fixture
def service(db_session):
    return NewFeatureService(db_session)

def test_expected_behavior(service):
    """Test normal use case."""
    result = service.do_something("valid_input")
    assert result is not None
    assert result.status == "success"

def test_edge_case(service):
    """Test boundary condition."""
    result = service.do_something("")
    assert result.status == "error"

def test_error_handling(service):
    """Test exception handling."""
    with pytest.raises(ValueError):
        service.do_something(None)
```

## Debugging

### Local Development

```bash
# Start with debugger
python -m debugpy --listen 5678 --wait-for-client -m uvicorn src.qnwis.api.server:app --reload

# Or use VS Code launch.json
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed diagnostic information")
logger.info("Normal operation milestone")
logger.warning("Unexpected but handled situation")
logger.error("Error that needs attention", exc_info=True)
logger.critical("System failure")
```

### Database Queries

```bash
# Connect to local DB
psql qnwis_dev

# View slow queries
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;

# Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Resources

### Documentation
- [USER_GUIDE.md](./USER_GUIDE.md) - End-user documentation
- [API_REFERENCE.md](./API_REFERENCE.md) - API documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [SECURITY.md](./SECURITY.md) - Security controls
- [PERFORMANCE.md](./PERFORMANCE.md) - Performance optimization

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Pydantic](https://docs.pydantic.dev/)
- [pytest](https://docs.pytest.org/)

### Getting Help

1. **Documentation**: Check docs/ first
2. **Code Examples**: See tests/ for usage examples
3. **Team Chat**: Internal Slack/Teams channel
4. **Code Review**: Ask during PR reviews
5. **Pair Programming**: Schedule with senior developers

## Checklist for New Developers

- [ ] Development environment set up
- [ ] All tests passing locally
- [ ] Read ARCHITECTURE.md
- [ ] Read SECURITY.md
- [ ] Understand Deterministic Data Layer contract
- [ ] Understand multi-agent architecture
- [ ] Know performance SLOs
- [ ] Completed first code review
- [ ] Deployed first feature to staging

---

**Welcome to the team! Remember: This system serves Qatar's Ministry of Labour. Every line of code matters.**
