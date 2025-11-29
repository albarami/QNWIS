#!/usr/bin/env python3
"""
Diagnose PyTorch CUDA installation issues.
Saves results to diagnose_pytorch_results.txt
"""

import subprocess
import sys
import os
from pathlib import Path

def run_cmd(cmd: str) -> str:
    """Run a command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nEXIT: {result.returncode}"
    except Exception as e:
        return f"ERROR: {e}"

def main():
    output_file = Path(__file__).parent.parent / "diagnose_pytorch_results.txt"
    
    results = []
    results.append("=" * 70)
    results.append("PYTORCH CUDA DIAGNOSIS")
    results.append("=" * 70)
    
    # 1. Check current torch version
    results.append("\n[1] CURRENT TORCH VERSION:")
    results.append("-" * 40)
    try:
        import torch
        results.append(f"torch.__version__ = {torch.__version__}")
        results.append(f"torch.cuda.is_available() = {torch.cuda.is_available()}")
        results.append(f"torch.version.cuda = {torch.version.cuda}")
        results.append(f"torch.backends.cudnn.enabled = {torch.backends.cudnn.enabled}")
        if torch.cuda.is_available():
            results.append(f"torch.cuda.device_count() = {torch.cuda.device_count()}")
    except ImportError as e:
        results.append(f"torch not installed: {e}")
    except Exception as e:
        results.append(f"Error checking torch: {e}")
    
    # 2. Check pip show torch
    results.append("\n[2] PIP SHOW TORCH:")
    results.append("-" * 40)
    results.append(run_cmd("pip show torch"))
    
    # 3. Check pip list for torch packages
    results.append("\n[3] TORCH-RELATED PACKAGES:")
    results.append("-" * 40)
    results.append(run_cmd("pip list | findstr torch"))
    
    # 4. Check NVIDIA driver
    results.append("\n[4] NVIDIA-SMI:")
    results.append("-" * 40)
    results.append(run_cmd("nvidia-smi --query-gpu=driver_version,cuda_version --format=csv"))
    
    # 5. Check CUDA environment variables
    results.append("\n[5] CUDA ENVIRONMENT VARIABLES:")
    results.append("-" * 40)
    cuda_vars = ['CUDA_HOME', 'CUDA_PATH', 'CUDA_VISIBLE_DEVICES', 'PATH']
    for var in cuda_vars:
        val = os.environ.get(var, 'NOT SET')
        if var == 'PATH':
            # Show only CUDA-related paths
            paths = [p for p in val.split(os.pathsep) if 'cuda' in p.lower() or 'nvidia' in p.lower()]
            val = '\n    '.join(paths) if paths else 'No CUDA paths found'
        results.append(f"{var}: {val}")
    
    # 6. Check nvcc
    results.append("\n[6] NVCC VERSION:")
    results.append("-" * 40)
    results.append(run_cmd("nvcc --version"))
    
    # 7. Check Python and pip paths
    results.append("\n[7] PYTHON/PIP PATHS:")
    results.append("-" * 40)
    results.append(f"sys.executable = {sys.executable}")
    results.append(f"sys.prefix = {sys.prefix}")
    results.append(run_cmd("where pip"))
    results.append(run_cmd("where python"))
    
    # 8. Check pip cache
    results.append("\n[8] PIP CACHE INFO:")
    results.append("-" * 40)
    results.append(run_cmd("pip cache info"))
    
    # Write results
    output_text = "\n".join(results)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_text)
    
    print(f"Results written to: {output_file}")
    print("\n" + output_text)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

