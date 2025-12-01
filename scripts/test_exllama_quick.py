#!/usr/bin/env python3
"""Quick test for ExLlamaV2."""
import sys
print("Testing ExLlamaV2...")

try:
    from exllamav2 import ExLlamaV2, ExLlamaV2Config
    print("✓ ExLlamaV2 imported successfully!")
except Exception as e:
    print(f"✗ ExLlamaV2 import failed: {e}")
    sys.exit(1)

try:
    import torch
    print(f"✓ PyTorch version: {torch.__version__}")
    print(f"✓ CUDA available: {torch.cuda.is_available()}")
    print(f"✓ GPU count: {torch.cuda.device_count()}")
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
except Exception as e:
    print(f"✗ PyTorch error: {e}")
    sys.exit(1)

print("\n✓ ExLlamaV2 is ready!")

