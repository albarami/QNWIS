#!/usr/bin/env python3
"""
QNWIS GPU Reality Check

Run this on your actual deployment machine to see:
1. Do you have GPUs?
2. Is PyTorch configured to use them?
3. What's actually happening vs what logs claim?
"""

import sys
import subprocess
import os


def main():
    print("=" * 70)
    print("🔍 QNWIS GPU REALITY CHECK")
    print("=" * 70)
    
    results = {
        "nvidia_driver": False,
        "gpu_count": 0,
        "gpu_names": [],
        "pytorch_installed": False,
        "pytorch_cuda": False,
        "cuda_version": None,
    }
    
    # =========================================
    # CHECK 1: NVIDIA Driver & Hardware
    # =========================================
    print("\n[1/3] CHECKING NVIDIA HARDWARE")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'],
            capture_output=True, 
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            results["nvidia_driver"] = True
            lines = result.stdout.strip().split('\n')
            results["gpu_count"] = len(lines)
            
            print(f"✅ NVIDIA Driver: FOUND")
            print(f"✅ GPU Count: {len(lines)}")
            
            for i, line in enumerate(lines):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    gpu_name = parts[0]
                    results["gpu_names"].append(gpu_name)
                    print(f"\n   GPU {i}: {gpu_name}")
                    print(f"          Memory: {parts[1]}")
                    print(f"          Driver: {parts[2]}")
        else:
            print("❌ NVIDIA Driver: NOT FOUND or NO GPUs")
            print("   nvidia-smi returned no output")
            
    except FileNotFoundError:
        print("❌ NVIDIA Driver: NOT INSTALLED")
        print("   'nvidia-smi' command not found")
    except subprocess.TimeoutExpired:
        print("❌ NVIDIA Driver: TIMEOUT")
    except Exception as e:
        print(f"❌ NVIDIA Driver: ERROR - {e}")
    
    # =========================================
    # CHECK 2: PyTorch Configuration
    # =========================================
    print("\n[2/3] CHECKING PYTORCH CONFIGURATION")
    print("-" * 50)
    
    try:
        import torch
        results["pytorch_installed"] = True
        print(f"✅ PyTorch Version: {torch.__version__}")
        
        # Check if CUDA is available
        cuda_available = torch.cuda.is_available()
        results["pytorch_cuda"] = cuda_available
        
        if cuda_available:
            results["cuda_version"] = torch.version.cuda
            print(f"✅ CUDA Available: YES")
            print(f"   CUDA Version: {torch.version.cuda}")
            print(f"   cuDNN Version: {torch.backends.cudnn.version()}")
            print(f"   Visible GPUs: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                print(f"\n   GPU {i}: {torch.cuda.get_device_name(i)}")
                props = torch.cuda.get_device_properties(i)
                print(f"          Memory: {props.total_memory / 1e9:.1f} GB")
                print(f"          Compute: {props.major}.{props.minor}")
        else:
            print(f"❌ CUDA Available: NO")
            
            # Diagnose why
            if '+cu' in torch.__version__:
                print("   ⚠️  CUDA PyTorch installed but can't find CUDA runtime")
                print("   → Check: NVIDIA drivers installed?")
                print("   → Check: CUDA toolkit installed?")
                print("   → Check: LD_LIBRARY_PATH includes CUDA libs?")
            else:
                print("   ⚠️  CPU-only PyTorch version installed")
                print("   → You have the wrong PyTorch!")
                
    except ImportError:
        print("❌ PyTorch: NOT INSTALLED")
    except Exception as e:
        print(f"❌ PyTorch: ERROR - {e}")
    
    # =========================================
    # CHECK 3: What QNWIS Claims vs Reality
    # =========================================
    print("\n[3/3] QNWIS CLAIMS vs REALITY")
    print("-" * 50)
    
    claims = [
        ("8 A100 GPUs for parallel scenarios", results["gpu_count"] >= 8 and "A100" in str(results["gpu_names"])),
        ("GPU 0-5 for scenario execution", results["gpu_count"] >= 6 and results["pytorch_cuda"]),
        ("GPU 6 for embeddings", results["gpu_count"] >= 7 and results["pytorch_cuda"]),
        ("GPU 7 as standby", results["gpu_count"] >= 8),
        ("CUDA-accelerated embeddings", results["pytorch_cuda"]),
        ("GPU-parallel debate execution", results["pytorch_cuda"]),
    ]
    
    lies_found = 0
    for claim, is_true in claims:
        if is_true:
            print(f"   ✅ {claim}")
        else:
            print(f"   ❌ {claim} ← THIS IS A LIE")
            lies_found += 1
    
    # =========================================
    # VERDICT
    # =========================================
    print("\n" + "=" * 70)
    print("📋 VERDICT")
    print("=" * 70)
    
    if results["gpu_count"] == 0:
        print("""
🔴 NO GPUs DETECTED

Your system has NO GPU hardware (or drivers aren't installed).
All GPU claims in QNWIS are FALSE.

OPTIONS:
1. Deploy to a machine WITH GPUs (Azure NC/ND series, etc.)
2. Remove all GPU claims from the code and documentation
3. Accept CPU-only operation (still works, just no GPU acceleration)
        """)
    elif results["gpu_count"] > 0 and not results["pytorch_cuda"]:
        print(f"""
🟡 GPUs EXIST BUT PYTORCH CAN'T USE THEM

You have {results["gpu_count"]} GPU(s): {', '.join(results["gpu_names"])}
But PyTorch is installed WITHOUT CUDA support.

TO FIX:
1. Uninstall current PyTorch:
   pip uninstall torch torchvision torchaudio

2. Install CUDA-enabled PyTorch:
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

3. Verify:
   python -c "import torch; print(torch.cuda.is_available())"  # Should print True
        """)
    elif results["pytorch_cuda"]:
        print(f"""
🟢 GPUs ARE AVAILABLE AND PYTORCH CAN USE THEM

You have {results["gpu_count"]} GPU(s) with CUDA {results["cuda_version"]}

But the code may still not be USING them properly.
Check that:
1. Embeddings model loads with device='cuda'
2. Tensors are moved to GPU before operations
3. Parallel executor actually assigns GPU devices
        """)
    
    if lies_found > 0:
        print(f"\n⚠️  {lies_found} FALSE CLAIMS found in QNWIS documentation/logs")
        print("   These need to be corrected immediately.")
    
    print("\n" + "=" * 70)
    
    return 0 if results["pytorch_cuda"] else 1


if __name__ == "__main__":
    sys.exit(main())
