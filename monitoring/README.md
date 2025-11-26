# Production Monitoring

## Quick Start

### Start Monitoring (3 terminals)

**Terminal 1: GPU Monitoring**
```bash
python monitoring/monitor_gpus.py
```

**Terminal 2: API Monitoring**
```bash
python monitoring/monitor_api.py
```

**Terminal 3: Dashboard**
```bash
python monitoring/dashboard.py
```

## Monitoring Scripts

### monitor_gpus.py
- Checks GPU utilization every 30 seconds
- Logs to `monitoring/gpu_metrics.jsonl`
- Alerts if GPU 6 >8GB

### monitor_api.py
- Checks API health every minute
- Logs to `monitoring/api_health.jsonl`
- Alerts on latency >1s or verification issues

### dashboard.py
- Real-time dashboard
- Refreshes every 5 seconds
- Shows GPU status, API health, system metrics

### analyze_queries.py
- Analyzes query logs
- Generates performance report
- Run on-demand: `python monitoring/analyze_queries.py`

## Metrics Files

- `gpu_metrics.jsonl` - GPU metrics (30s intervals)
- `api_health.jsonl` - API health (60s intervals)
- `query_performance.json` - Query analysis report

## Alerts

Watch for:
- GPU 6 memory >8GB
- API latency >1s
- Fact verification not ready
- Error rates >5%
