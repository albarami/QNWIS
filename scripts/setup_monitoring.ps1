# Production Monitoring Setup Script
# Sets up monitoring for Multi-GPU System

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "PRODUCTION MONITORING SETUP" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Create monitoring directory
$monitoringDir = "monitoring"
if (-not (Test-Path $monitoringDir)) {
    New-Item -ItemType Directory -Path $monitoringDir | Out-Null
    Write-Host "[INFO] Created monitoring directory" -ForegroundColor Green
}

# Create GPU monitoring script
Write-Host "[1/5] Creating GPU monitoring script..." -ForegroundColor Yellow

$gpuMonitorScript = @'
# GPU Monitoring Script
# Checks GPU utilization and memory every 30 seconds

import torch
import time
import json
from datetime import datetime

def monitor_gpus():
    """Monitor all GPUs and log metrics."""
    if not torch.cuda.is_available():
        print("No CUDA GPUs available")
        return
    
    while True:
        timestamp = datetime.now().isoformat()
        metrics = {
            "timestamp": timestamp,
            "gpus": []
        }
        
        for i in range(torch.cuda.device_count()):
            mem_allocated = torch.cuda.memory_allocated(i) / 1e9
            mem_reserved = torch.cuda.memory_reserved(i) / 1e9
            mem_total = torch.cuda.get_device_properties(i).total_memory / 1e9
            utilization = (mem_allocated / mem_total) * 100
            
            gpu_metric = {
                "gpu_id": i,
                "name": torch.cuda.get_device_name(i),
                "memory_allocated_gb": round(mem_allocated, 2),
                "memory_reserved_gb": round(mem_reserved, 2),
                "memory_total_gb": round(mem_total, 1),
                "utilization_percent": round(utilization, 1)
            }
            
            metrics["gpus"].append(gpu_metric)
            
            # Alert if GPU 6 >8GB
            if i == 6 and mem_allocated > 8.0:
                print(f"[ALERT] GPU 6 memory high: {mem_allocated:.2f}GB")
        
        # Write to log file
        with open("monitoring/gpu_metrics.jsonl", "a") as f:
            f.write(json.dumps(metrics) + "\n")
        
        # Print summary
        print(f"{timestamp} - GPU Status:")
        for gpu in metrics["gpus"]:
            print(f"  GPU {gpu['gpu_id']}: {gpu['memory_allocated_gb']:.2f}GB / {gpu['memory_total_gb']:.1f}GB ({gpu['utilization_percent']:.1f}%)")
        
        time.sleep(30)  # Monitor every 30 seconds

if __name__ == "__main__":
    monitor_gpus()
'@

Set-Content -Path "monitoring/monitor_gpus.py" -Value $gpuMonitorScript
Write-Host "  [PASS] Created monitoring/monitor_gpus.py" -ForegroundColor Green

# Create API monitoring script
Write-Host "[2/5] Creating API monitoring script..." -ForegroundColor Yellow

$apiMonitorScript = @'
# API Monitoring Script
# Checks API health and performance

import requests
import time
import json
from datetime import datetime

API_URL = "http://localhost:8000"

def monitor_api():
    """Monitor API health and performance."""
    while True:
        timestamp = datetime.now().isoformat()
        
        try:
            # Health check
            start = time.time()
            response = requests.get(f"{API_URL}/health", timeout=10)
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code == 200:
                health_data = response.json()
                
                metrics = {
                    "timestamp": timestamp,
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 1),
                    "gpus": health_data.get("gpus", 0),
                    "agents": health_data.get("agents", 0),
                    "fact_verification": health_data.get("fact_verification", "unknown"),
                    "documents_indexed": health_data.get("documents_indexed", 0),
                    "parallel_scenarios": health_data.get("parallel_scenarios", "unknown")
                }
                
                # Alert conditions
                if latency_ms > 1000:
                    print(f"[ALERT] Health check slow: {latency_ms:.0f}ms")
                
                if health_data.get("fact_verification") != "ready":
                    print(f"[ALERT] Fact verification not ready")
                
                # Write to log
                with open("monitoring/api_health.jsonl", "a") as f:
                    f.write(json.dumps(metrics) + "\n")
                
                print(f"{timestamp} - API Health: OK ({latency_ms:.0f}ms)")
                print(f"  GPUs: {metrics['gpus']}, Agents: {metrics['agents']}")
                print(f"  Verification: {metrics['fact_verification']}, Docs: {metrics['documents_indexed']}")
                
            else:
                print(f"[ALERT] API unhealthy: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"[ERROR] Health check failed: {e}")
        
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    monitor_api()
'@

Set-Content -Path "monitoring/monitor_api.py" -Value $apiMonitorScript
Write-Host "  [PASS] Created monitoring/monitor_api.py" -ForegroundColor Green

# Create query performance tracker
Write-Host "[3/5] Creating query performance tracker..." -ForegroundColor Yellow

$queryTrackerScript = @'
# Query Performance Tracker
# Analyzes query logs for performance metrics

import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

def analyze_query_logs():
    """Analyze query logs for performance metrics."""
    log_file = Path("logs/production.log")
    
    if not log_file.exists():
        print("No log file found")
        return
    
    query_times = []
    error_count = 0
    verification_rates = []
    
    with open(log_file, "r") as f:
        for line in f:
            try:
                log_entry = json.loads(line)
                
                # Track query completion times
                if "query completed" in log_entry.get("message", "").lower():
                    # Extract time from message if available
                    pass
                
                # Track errors
                if log_entry.get("level") == "ERROR":
                    error_count += 1
                
                # Track verification rates
                if "verification rate" in log_entry.get("message", "").lower():
                    # Extract verification rate
                    pass
                    
            except json.JSONDecodeError:
                continue
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(query_times),
        "total_errors": error_count,
        "error_rate": error_count / max(len(query_times), 1),
        "avg_query_time_s": sum(query_times) / len(query_times) if query_times else 0,
        "avg_verification_rate": sum(verification_rates) / len(verification_rates) if verification_rates else 0
    }
    
    print(json.dumps(report, indent=2))
    
    # Write report
    with open("monitoring/query_performance.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    analyze_query_logs()
'@

Set-Content -Path "monitoring/analyze_queries.py" -Value $queryTrackerScript
Write-Host "  [PASS] Created monitoring/analyze_queries.py" -ForegroundColor Green

# Create monitoring dashboard script
Write-Host "[4/5] Creating monitoring dashboard..." -ForegroundColor Yellow

$dashboardScript = @'
# Real-Time Monitoring Dashboard
# Displays live system metrics

import time
import os
import json
from datetime import datetime

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def display_dashboard():
    """Display real-time monitoring dashboard."""
    while True:
        clear_screen()
        
        print("="*80)
        print("QNWIS PRODUCTION MONITORING DASHBOARD")
        print("="*80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        # GPU Metrics
        try:
            with open("monitoring/gpu_metrics.jsonl", "r") as f:
                lines = f.readlines()
                if lines:
                    latest = json.loads(lines[-1])
                    print("GPU Status:")
                    for gpu in latest["gpus"]:
                        mem = gpu["memory_allocated_gb"]
                        total = gpu["memory_total_gb"]
                        util = gpu["utilization_percent"]
                        status = "OK" if mem < 8.0 else "HIGH"
                        print(f"  GPU {gpu['gpu_id']}: {mem:.2f}GB / {total:.1f}GB ({util:.1f}%) [{status}]")
        except:
            print("GPU Status: No data")
        
        print("")
        
        # API Health
        try:
            with open("monitoring/api_health.jsonl", "r") as f:
                lines = f.readlines()
                if lines:
                    latest = json.loads(lines[-1])
                    print(f"API Status: {latest['status'].upper()}")
                    print(f"  Health latency: {latest['latency_ms']:.0f}ms")
                    print(f"  GPUs detected: {latest['gpus']}")
                    print(f"  Agents: {latest['agents']}")
                    print(f"  Fact verification: {latest['fact_verification']}")
                    print(f"  Documents indexed: {latest['documents_indexed']}")
        except:
            print("API Status: No data")
        
        print("")
        print("Press Ctrl+C to exit")
        print("="*80)
        
        time.sleep(5)  # Refresh every 5 seconds

if __name__ == "__main__":
    try:
        display_dashboard()
    except KeyboardInterrupt:
        print("\nDashboard stopped")
'@

Set-Content -Path "monitoring/dashboard.py" -Value $dashboardScript
Write-Host "  [PASS] Created monitoring/dashboard.py" -ForegroundColor Green

# Create README
Write-Host "[5/5] Creating monitoring README..." -ForegroundColor Yellow

$monitoringReadme = @'
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
'@

Set-Content -Path "monitoring/README.md" -Value $monitoringReadme
Write-Host "  [PASS] Created monitoring/README.md" -ForegroundColor Green

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "MONITORING SETUP COMPLETE" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Created:" -ForegroundColor Cyan
Write-Host "  monitoring/monitor_gpus.py - GPU monitoring" -ForegroundColor White
Write-Host "  monitoring/monitor_api.py - API health monitoring" -ForegroundColor White
Write-Host "  monitoring/dashboard.py - Real-time dashboard" -ForegroundColor White
Write-Host "  monitoring/analyze_queries.py - Query analysis" -ForegroundColor White
Write-Host "  monitoring/README.md - Usage guide" -ForegroundColor White
Write-Host ""

