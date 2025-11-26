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
