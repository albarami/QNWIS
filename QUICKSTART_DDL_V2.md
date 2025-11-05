# Quick Start Guide: Deterministic Data Layer V2

## 🚀 Start the API Server

```bash
# From project root
uvicorn src.qnwis.app:app --reload --host 0.0.0.0 --port 8000
```

**Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

---

## 🔍 Verify Installation

### Check Available Routes
```bash
python -c "from src.qnwis.app import app; print([r.path for r in app.routes])"
```

**Expected Output:**
```
['/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', 
 '/v1/queries', '/v1/queries/{query_id}', '/v1/queries/{query_id}/run', 
 '/v1/queries/{query_id}/cache/invalidate', '/health', '/ready']
```

### Run Tests
```bash
# All tests (64 total)
python -m pytest tests/unit/test_normalize.py tests/unit/test_metrics.py tests/unit/test_api_models.py tests/integration/test_api_queries.py -v

# Should output: 64 passed in ~5s
```

---

## 📡 API Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
# {"status":"healthy"}
```

### 2. List Queries
```bash
curl http://localhost:8000/v1/queries
# {"ids":["q_demo","gdp_growth",...]}
```

### 3. Execute Query
```bash
curl -X POST http://localhost:8000/v1/queries/q_demo/run \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: test-123" \
  -d '{
    "ttl_s": 600,
    "override_params": {"year": 2023}
  }'
```

**Response:**
```json
{
  "query_id": "q_demo",
  "unit": "percent",
  "rows": [{"year": 2023, "male_percent": 60.0, ...}],
  "provenance": {"source": "csv", ...},
  "freshness": {"asof_date": "2023-12-01"},
  "warnings": [],
  "request_id": "test-123"
}
```

### 4. Invalidate Cache
```bash
curl -X POST http://localhost:8000/v1/queries/q_demo/cache/invalidate
# {"status":"ok","invalidated":"q_demo"}
```

---

## 🐍 Python Usage

### Using the API (External Consumers)
```python
import requests

# Execute query
response = requests.post(
    "http://localhost:8000/v1/queries/gdp_growth/run",
    json={
        "ttl_s": 600,
        "override_params": {"year": 2023}
    },
    headers={"X-Request-ID": "my-request-001"}
)

data = response.json()
print(f"Query: {data['query_id']}")
print(f"Rows: {len(data['rows'])}")
for row in data['rows']:
    print(row)
```

### Using Internal API (Agents)
```python
from src.qnwis.data.deterministic.cache_access import execute_cached
from src.qnwis.data.deterministic.registry import QueryRegistry

# Load registry
registry = QueryRegistry("src/qnwis/data/queries")
registry.load_all()

# Execute with caching
result = execute_cached("gdp_growth", registry, ttl_s=600)

# Process results
for row in result.rows:
    print(row.data)
```

### Apply Derived Metrics
```python
from src.qnwis.data.derived.metrics import share_of_total, yoy_growth, cagr

# After executing a query
result = execute_cached("population", registry)

# Calculate share of total
rows_with_share = share_of_total(
    result.rows,
    value_key="population",
    group_key="year",
    out_key="share_percent"
)

# Calculate YoY growth
rows_with_growth = yoy_growth(
    result.rows,
    value_key="population",
    out_key="yoy_percent"
)

# Calculate CAGR
growth_rate = cagr(start_value=100, end_value=121, years=2)
print(f"CAGR: {growth_rate}%")  # 10.0%
```

---

## 🔧 Configuration

### Environment Variables
Create a `.env` file:
```bash
# Query definitions directory
QNWIS_QUERIES_DIR=src/qnwis/data/queries

# Cache settings
DEFAULT_CACHE_TTL_S=300

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

### Query Definition Example
Create `src/qnwis/data/queries/my_query.yaml`:
```yaml
id: my_query
title: My Custom Query
description: Query description here
source: csv
expected_unit: percent
params:
  pattern: "mydata*.csv"
  select: ["year", "value"]
  year: 2023
constraints:
  freshness_sla_days: 365
```

---

## 📊 Interactive API Docs

FastAPI automatically generates interactive documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Try the endpoints directly from your browser!

---

## 🧪 Testing

### Unit Tests
```bash
# Normalization tests (14 tests)
python -m pytest tests/unit/test_normalize.py -v

# Metrics tests (21 tests)
python -m pytest tests/unit/test_metrics.py -v

# API models tests (10 tests)
python -m pytest tests/unit/test_api_models.py -v
```

### Integration Tests
```bash
# API integration tests (19 tests)
python -m pytest tests/integration/test_api_queries.py -v
```

### All Tests with Coverage
```bash
python -m pytest tests/ --cov=src.qnwis.data.deterministic --cov=src.qnwis.data.derived --cov=src.qnwis.api -v
```

---

## 🔒 Security Features

### Parameter Whitelist
Only these parameters can be overridden:
- ✅ `year` (int)
- ✅ `timeout_s` (int)
- ✅ `max_rows` (int)
- ✅ `to_percent` (list[str])
- ❌ All other params are immutable

### TTL Bounds
```python
MIN_TTL_S = 60      # 1 minute minimum
MAX_TTL_S = 86400   # 24 hours maximum
DEFAULT_TTL_S = 300 # 5 minutes default
```

### Request Validation
```bash
# Invalid parameter (rejected)
curl -X POST http://localhost:8000/v1/queries/q_demo/run \
  -d '{"override_params": {"malicious": "value"}}'
# ✓ Parameter ignored (not in whitelist)

# TTL out of bounds (clamped)
curl -X POST http://localhost:8000/v1/queries/q_demo/run \
  -d '{"ttl_s": 99999}'
# ✓ Clamped to 86400 (24 hours)
```

---

## 📈 Performance

### Latency Targets
- **Cache hit:** <10ms
- **Cache miss (CSV):** <50ms  
- **Cache miss (World Bank API):** <200ms

### Monitoring Key Metrics
```python
# Track cache performance
cache_hit_rate = hits / (hits + misses)
avg_latency = sum(latencies) / len(latencies)
freshness_violations = len([w for w in warnings if "freshness" in w])
```

---

## 🆘 Troubleshooting

### API Won't Start
```bash
# Check if port is already in use
netstat -ano | findstr :8000

# Use different port
uvicorn src.qnwis.app:app --port 8001
```

### Tests Fail
```bash
# Verify Python version (3.11+)
python --version

# Install dependencies
pip install -r requirements.txt

# Run tests with verbose output
python -m pytest tests/ -vv
```

### Query Not Found (404)
```bash
# List available queries
curl http://localhost:8000/v1/queries

# Check query directory
ls src/qnwis/data/queries/

# Verify YAML syntax
python -c "import yaml; print(yaml.safe_load(open('src/qnwis/data/queries/q_demo.yaml')))"
```

---

## 📚 Documentation

- **Full API Reference:** [docs/ddl_v2_endpoints.md](docs/ddl_v2_endpoints.md)
- **Implementation Summary:** [DDL_V2_IMPLEMENTATION_SUMMARY.md](DDL_V2_IMPLEMENTATION_SUMMARY.md)
- **Interactive Docs:** http://localhost:8000/docs (when server is running)

---

## ✅ Verification Checklist

Before deploying to production:

- [ ] All 64 tests pass
- [ ] API server starts without errors
- [ ] Health endpoint returns `{"status":"healthy"}`
- [ ] Can list queries via `/v1/queries`
- [ ] Can execute at least one query successfully
- [ ] Request ID header is returned in responses
- [ ] Cache invalidation works
- [ ] TTL bounds are enforced (try 30s → clamped to 60s)
- [ ] Parameter whitelist is enforced (try malicious param → ignored)
- [ ] Documentation is accessible

---

## 🎉 Success!

If all verification steps pass, your Deterministic Data Layer V2 is ready!

**Next Steps:**
1. Add your query definitions in YAML format
2. Deploy to staging environment
3. Set up monitoring and alerting
4. Add authentication/authorization as needed

**Need Help?** Check [docs/ddl_v2_endpoints.md](docs/ddl_v2_endpoints.md) for detailed documentation.
