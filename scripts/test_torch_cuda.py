"""Test PyTorch CUDA with detailed error handling."""
import sys
import os
import traceback

print("=" * 60)
print("PyTorch CUDA Test")
print("=" * 60)

# Check if CUDA paths are set
print(f"\nCUDA_HOME: {os.environ.get('CUDA_HOME', 'NOT SET')}")
print(f"CUDA_PATH: {os.environ.get('CUDA_PATH', 'NOT SET')}")

print("\nImporting torch...")
sys.stdout.flush()

try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    sys.stdout.flush()
    
    print("\nCalling torch.cuda.is_available()...")
    sys.stdout.flush()
    
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    sys.stdout.flush()
    
    if cuda_available:
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        sys.stdout.flush()
        
        # Try allocating some memory
        print("\nTesting GPU memory allocation...")
        x = torch.zeros(1000, 1000, device="cuda:0")
        print(f"Allocated tensor on GPU 0: {x.shape}")
        print(f"Memory used: {torch.cuda.memory_allocated(0) / 1e6:.1f} MB")
        del x
        print("SUCCESS!")
    else:
        print("CUDA is not available!")
        
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Test completed successfully!")
print("=" * 60)

