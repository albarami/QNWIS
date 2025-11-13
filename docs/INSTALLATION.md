# QNWIS Installation Guide

## Prerequisites

- **Python 3.11+** (required for `tomllib` and modern type hints)
- **PostgreSQL 15+** (or SQLite for dev/test)
- **Redis 7+** (optional; in-memory fallback exists)
- **API Keys**: One of `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` 

## Development Install (Recommended)

### Quick Start

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Generate requirements.txt (optional)
python scripts/generate_requirements_txt.py

# Verify critical imports (optional)
python scripts/verify_runtime_dependencies.py
```

### Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys:
# - ANTHROPIC_API_KEY=sk-ant-***
# - OPENAI_API_KEY=sk-***
# - DATABASE_URL=postgresql://user:pass@localhost:5432/qnwis
```

### Verify Installation

```bash
# Run tests
pytest -v

# Run linting
ruff check .
black --check .

# Run type checking
mypy src
```

## Production Install

### Option 1: Using requirements.txt

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Option 2: Using pyproject.toml

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[production]"
```

### Production Configuration

1. **Set environment variables** (never commit secrets):
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-***
   export DATABASE_URL=postgresql://user:pass@host:5432/qnwis
   export REDIS_URL=redis://host:6379/0
   export ENVIRONMENT=production
   ```

2. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Start the application**:
```bash
gunicorn -c configs/gunicorn.conf.py src.qnwis.api.main:app
```

## Packaging / Wheel Build

Run these steps whenever you need to verify the editable install can be packaged for distribution:

```bash
# Ensure build backend dependencies are installed (part of dev extra)
pip install -e ".[dev]"

# Clean previous artifacts
# (PowerShell): Remove-Item -Recurse -Force dist,build,*.egg-info
rm -rf dist build *.egg-info

# Build a wheel + sdist bundle
python -m build --wheel --sdist

# (Optional) Sanity-check the wheel
pip install dist/qnwis-*.whl --force-reinstall
```

The project uses the default `setuptools.build_meta` backend defined in `pyproject.toml`, so `python -m build` will emit both source and wheel archives under `dist/`.

## Docker Installation

### Build Image

```bash
docker build -t qnwis:latest .
```

### Run Container

```bash
docker run -d \
  -e ANTHROPIC_API_KEY=sk-ant-*** \
  -e DATABASE_URL=postgresql://user:pass@host:5432/qnwis \
  -e REDIS_URL=redis://host:6379/0 \
  -p 8001:8001 \
  --name qnwis \
  qnwis:latest
```

### Docker Compose (Example)

```yaml
version: '3.8'
services:
  qnwis:
    build: .
    ports:
      - "8001:8001"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/qnwis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=qnwis
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Troubleshooting

### Missing Dependencies

**Issue**: `ModuleNotFoundError: No module named 'anthropic'`

**Solution**:
```bash
pip install anthropic openai
# or reinstall all dependencies
pip install -e ".[dev]"
```

### API Key Issues

**Issue**: `AuthenticationError: Invalid API key`

**Solution**:
```bash
# Set environment variable
export ANTHROPIC_API_KEY=sk-ant-your-key-here
# or add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env
```

### Database Connection

**Issue**: `psycopg.OperationalError: connection refused`

**Solution for local development**:
```bash
# Use SQLite for testing
export DATABASE_URL=sqlite:///./qnwis.db
# or add to .env
echo "DATABASE_URL=sqlite:///./qnwis.db" >> .env
```

### Redis Connection

**Issue**: `redis.exceptions.ConnectionError`

**Solution**: Redis is optional. The system will fall back to in-memory caching if Redis is unavailable.

### Import Errors

**Issue**: Various import failures

**Solution**:
```bash
# Verify all critical imports
python scripts/verify_runtime_dependencies.py

# Reinstall in editable mode
pip install -e ".[dev]"
```

## Development Workflow

### Using Makefile (Linux/Mac/WSL)

```bash
# Install dev dependencies
make dev

# Run tests with coverage
make test

# Run all linters
make lint

# Run type checking
make type

# Security audit
make audit

# Generate requirements.txt
make lock

# Verify runtime dependencies
make verify
```

### Windows PowerShell Commands

```powershell
# Install dev dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest -v --cov=src

# Generate requirements.txt
python scripts/generate_requirements_txt.py

# Verify runtime dependencies
python scripts/verify_runtime_dependencies.py

# Run all linters
ruff check .
flake8
black --check .
isort --check-only .

# Run type checking
mypy src

# Security audit
bandit -r src
safety check
pip-audit -r requirements.txt
```

### Manual Commands (Cross-Platform)

```bash
# Install
pip install -e ".[dev]"

# Test
pytest -v --cov=src

# Lint
ruff check .
flake8
black --check .
isort --check-only .

# Type check
mypy src

# Security audit
bandit -r src
safety check || true
pip-audit -r requirements.txt || true
```

## Verification Checklist

Before deploying to production, verify:

- [ ] All tests pass: `pytest -v`
- [ ] No linting errors: `make lint`
- [ ] Type checking passes: `make type`
- [ ] All critical imports work: `python scripts/verify_runtime_dependencies.py`
- [ ] Environment variables are set (never hardcoded)
- [ ] Database migrations applied: `alembic upgrade head`
- [ ] Security audit clean: `make audit`

## Next Steps

After successful installation:

1. **Review documentation**: See `docs/` for architecture and API specs
2. **Configure agents**: Review agent configuration in `src/qnwis/agents/`
3. **Set up monitoring**: Configure Prometheus/Grafana (see `grafana/dashboards/`)
4. **Run validation**: Execute validation suite in `validation/`

## Support

For issues or questions:
- Review existing documentation in `docs/`
- Check `QUICKSTART_*.md` files for specific components
- Consult `IMPLEMENTATION_*.md` files for detailed specifications
