#!/usr/bin/env python3
"""Test PyTorch first before ExLlamaV2."""
import sys
import os

# Set environment
os.environ['TORCH_CUDA_ARCH_LIST'] = '8.0'
os.environ['CUDA_HOME'] = r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1'

print("Step 1: Importing torch...", flush=True)
import torch
print(f"  PyTorch: {torch.__version__}", flush=True)
print(f"  CUDA: {torch.cuda.is_available()}", flush=True)
if torch.cuda.is_available():
    print(f"  GPUs: {torch.cuda.device_count()}", flush=True)
    print(f"  GPU 0: {torch.cuda.get_device_name(0)}", flush=True)

print("\nStep 2: Testing CUDA tensor...", flush=True)
x = torch.ones(10, device='cuda:0')
print(f"  Tensor created: {x.sum()}", flush=True)

print("\nStep 3: Importing exllamav2 module (not the extension)...", flush=True)
sys.path.insert(0, r'D:\lmis_int\.venv\Lib\site-packages')

# Try importing just the config module first
print("  Importing exllamav2.config...", flush=True)
from exllamav2 import config as exl_config
print("  Success!", flush=True)

print("\nStep 4: Checking ext module...", flush=True)
from exllamav2 import ext
print(f"  ext.extension_name: {ext.extension_name}", flush=True)
print(f"  ext.verbose: {ext.verbose}", flush=True)

# Enable verbose
ext.verbose = True

print("\nStep 5: Triggering C++ extension build...", flush=True)
print("  This will take several minutes...", flush=True)
ext.make_c_ext()

print("\nSUCCESS: ExLlamaV2 compilation complete!", flush=True)

