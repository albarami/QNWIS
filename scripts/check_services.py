#!/usr/bin/env python3
"""Check all NSIC services health."""

import requests
import time

def check_services():
    print("=" * 60)
    print("NSIC Services Health Check")
    print("=" * 60)
    print()
    
    # CPU Services
    print("CPU Services:")
    cpu_services = [
        ('Embeddings', 8100),
        ('KG', 8101),
        ('Verification', 8102)
    ]
    
    for name, port in cpu_services:
        try:
            r = requests.get(f'http://localhost:{port}/health', timeout=7200)
            data = r.json()
            device = data.get('device', 'cpu')
            status = data.get('status', 'healthy')
            print(f"  ✅ {name} (port {port}): {status} - device={device}")
        except requests.exceptions.ConnectionError:
            print(f"  ❌ {name} (port {port}): Connection refused")
        except Exception as e:
            print(f"  ❌ {name} (port {port}): {type(e).__name__}")
    
    print()
    
    # DeepSeek Instances
    print("DeepSeek ExLlamaV2 Instances:")
    healthy_count = 0
    for i in range(8):
        port = 8001 + i
        try:
            r = requests.get(f'http://localhost:{port}/health', timeout=7200)
            data = r.json()
            mem = data.get('gpu_memory_gb', 0)
            print(f"  ✅ Instance {i+1} (GPU {i}, port {port}): Healthy - {mem:.1f}GB VRAM")
            healthy_count += 1
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Instance {i+1} (GPU {i}, port {port}): Connection refused")
        except Exception as e:
            print(f"  ❌ Instance {i+1} (GPU {i}, port {port}): {type(e).__name__}")
    
    print()
    print(f"DeepSeek instances: {healthy_count}/8 healthy")
    print("=" * 60)
    
    return healthy_count

if __name__ == "__main__":
    check_services()

