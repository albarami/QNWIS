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
