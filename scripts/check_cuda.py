import sys
print("Checking CUDA...")
sys.stdout.flush()

import torch
print(f"CUDA available: {torch.cuda.is_available()}")
sys.stdout.flush()

print(f"CUDA device count: {torch.cuda.device_count()}")
sys.stdout.flush()

for i in range(torch.cuda.device_count()):
    print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
    sys.stdout.flush()

print("SUCCESS")

