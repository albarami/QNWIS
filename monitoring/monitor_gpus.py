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
