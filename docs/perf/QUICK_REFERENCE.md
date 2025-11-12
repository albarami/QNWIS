# Performance Optimization Quick Reference

**One-page guide for QNWIS performance features**

---

## 🚀 Quick Start

### Run Benchmarks
```bash
python scripts/benchmark_qnwis.py --base-url http://localhost:8000 --all
```

### Check Metrics
```bash
curl http://localhost:8000/metrics
```

### View Cache Stats
```python
from qnwis.cache.redis_cache import DeterministicRedisCache
print(DeterministicRedisCache().get_metrics())
```

---

## 📊 Profiling

### Timer Context Manager
```python
from qnwis.perf.profile import Timer

def my_sink(name, duration, extra):
    print(f"{name}: {duration:.3f}s")

with Timer(my_sink, "operation", {"key": "value"}):
    expensive_function()
```

### Decorator
```python
from qnwis.perf.profile import timeit

@timeit("fetch_data", {"source": "csv"})
def fetch_data():
    return data
```

---

## 📈 Metrics

### Record Metrics
```python
from qnwis.perf.metrics import LATENCY, DB_LATENCY, CACHE_HIT

# HTTP latency
LATENCY.labels(route="/api/query", method="POST").observe(0.123)

# DB latency
DB_LATENCY.labels(operation="select").observe(0.045)

# Cache hit
CACHE_HIT.labels(region="queries").inc()
```

### Available Metrics
- `qnwis_requests_total` - HTTP requests
- `qnwis_latency_seconds` - HTTP latency
- `qnwis_db_latency_seconds` - DB latency
- `qnwis_cache_hits_total` - Cache hits
- `qnwis_cache_misses_total` - Cache misses
- `qnwis_agent_latency_seconds` - Agent execution
- `qnwis_stage_latency_seconds` - Orchestration stages

---

## 💾 Cache Tuning

### Adaptive TTL
```python
from qnwis.perf.cache_tuning import ttl_for

ttl = ttl_for("get_salary_statistics", row_count=500)  # ~900s
```

### Cache Key
```python
from qnwis.perf.cache_tuning import cache_key

key = cache_key("operation", "query_id", {"year": "2024"})
```

### Should Cache?
```python
from qnwis.perf.cache_tuning import should_cache

if should_cache("operation", row_count=100, duration_ms=250):
    cache.set(key, result, ttl)
```

---

## 🗄️ Database Tuning

### Configure Pool
```python
from qnwis.perf.db_tuning import configure_pool

configure_pool(engine, pool_size=30, max_overflow=10, timeout=30)
```

### Analyze Query
```python
from qnwis.perf.db_tuning import explain, analyze

# Get plan
plan = explain(engine, "SELECT * FROM jobs WHERE sector = :s", {"s": "IT"})

# Full analysis
stats = analyze(engine, "SELECT COUNT(*) FROM jobs", {})
print(f"Time: {stats['Execution Time']}ms")
```

### Set Timeout
```python
from qnwis.perf.db_tuning import with_timeout

with with_timeout(engine, 60):
    result = session.execute(complex_query)
```

---

## 🌊 Streaming

### Stream Large Results
```python
from qnwis.api.streaming import create_streaming_response

@app.get("/data")
def get_data():
    items = [{"id": i} for i in range(10000)]
    return create_streaming_response(items, format="json", chunk_size=100)
```

### NDJSON Format
```python
return create_streaming_response(items, format="ndjson")
```

---

## 📄 Pagination

### Paginate Results
```python
from qnwis.ui.pagination import paginate

result = paginate(items, page=1, page_size=1000)
# Returns: {"items": [...], "page": 1, "total_pages": 5, ...}
```

### Should Paginate?
```python
from qnwis.ui.pagination import should_paginate

if should_paginate(len(items), threshold=1000):
    result = paginate(items)
```

---

## 🎯 Benchmarking

### Run Specific Scenario
```bash
python scripts/benchmark_qnwis.py \
  --scenario simple \
  --users 10 \
  --requests 50 \
  --output results.json
```

### Scenarios
- `simple` - Single small query (<10s target)
- `medium` - 2-3 data calls (<30s target)
- `complex` - Multi-agent (<90s target)
- `dashboard` - Dashboard load (<3s target)

---

## 🔍 Monitoring

### Prometheus Scrape
```bash
curl http://localhost:8000/metrics
```

### Cache Metrics
```python
from qnwis.cache.redis_cache import DeterministicRedisCache

cache = DeterministicRedisCache()
metrics = cache.get_metrics()
print(f"Hit rate: {metrics['hit_rate']:.2%}")
```

---

## 📚 Documentation

- **Implementation**: `docs/perf/PERF_OPTIMIZATION_NOTES.md`
- **DB Tuning**: `docs/perf/DB_TUNING.md`
- **Summary**: `PERFORMANCE_OPTIMIZATION_COMPLETE.md`
- **Step Guide**: `STEP35_PERFORMANCE_OPTIMIZATION_COMPLETE.md`

---

## 🎯 Performance Targets

| Scenario | Target (p95) |
|----------|-------------|
| Simple | <10s |
| Medium | <30s |
| Complex | <90s |
| Dashboard | <3s |

---

## ⚡ Quick Wins

1. **Enable caching** - Set appropriate TTLs
2. **Use connection pooling** - Configure at startup
3. **Parallelize agents** - Use "parallel" mode
4. **Add indexes** - For common query filters
5. **Monitor metrics** - Watch `/metrics` endpoint

---

## 🚨 Common Issues

### High Latency
1. Check cache hit rate (target >70%)
2. Analyze slow queries with EXPLAIN
3. Verify connection pool not saturated
4. Check for sequential vs parallel execution

### Low Cache Hit Rate
1. Verify TTLs are appropriate
2. Check cache key generation
3. Monitor cache eviction
4. Increase cache size if needed

### Database Slow
1. Run EXPLAIN ANALYZE on slow queries
2. Add missing indexes
3. Increase connection pool size
4. Tune work_mem for aggregations

---

**Quick Command Reference**:
```bash
# Benchmark
python scripts/benchmark_qnwis.py --all

# Metrics
curl http://localhost:8000/metrics

# Health
curl http://localhost:8000/health
```
