#!/usr/bin/env python3
"""
NSIC Environment Check - Phase 0 Validation

Writes all output to nsic_env_check_results.txt for verification.
"""

import sys
import json
from pathlib import Path

results = {
    "phase": "0",
    "tests": [],
    "passed": 0,
    "failed": 0,
}

def log_test(name: str, passed: bool, details: str = ""):
    """Log test result."""
    status = "PASS" if passed else "FAIL"
    results["tests"].append({
        "name": name,
        "passed": passed,
        "details": details,
    })
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    print(f"[{status}] {name}: {details}")

# Test 1: Python version
try:
    version = sys.version_info
    passed = version.major == 3 and version.minor >= 10
    log_test("Python Version", passed, f"{version.major}.{version.minor}.{version.micro}")
except Exception as e:
    log_test("Python Version", False, str(e))

# Test 2: PyTorch
try:
    import torch
    log_test("PyTorch Installed", True, torch.__version__)
except ImportError as e:
    log_test("PyTorch Installed", False, str(e))

# Test 3: CUDA Available
try:
    import torch
    cuda_available = torch.cuda.is_available()
    log_test("CUDA Available", cuda_available, f"torch.cuda.is_available() = {cuda_available}")
except Exception as e:
    log_test("CUDA Available", False, str(e))

# Test 4: GPU Count
try:
    import torch
    gpu_count = torch.cuda.device_count()
    passed = gpu_count >= 8
    log_test("GPU Count >= 8", passed, f"Found {gpu_count} GPUs")
except Exception as e:
    log_test("GPU Count >= 8", False, str(e))

# Test 5: GPU Names
try:
    import torch
    if torch.cuda.is_available():
        gpu_names = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
        log_test("GPU Names", True, ", ".join(gpu_names[:4]) + "...")
    else:
        log_test("GPU Names", False, "CUDA not available")
except Exception as e:
    log_test("GPU Names", False, str(e))

# Test 6: sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    log_test("sentence-transformers", True, "Installed")
except ImportError:
    log_test("sentence-transformers", False, "Not installed")

# Test 7: transformers
try:
    import transformers
    log_test("transformers", True, transformers.__version__)
except ImportError:
    log_test("transformers", False, "Not installed")

# Test 8: faiss
try:
    import faiss
    has_gpu = hasattr(faiss, 'StandardGpuResources')
    log_test("faiss-gpu", has_gpu, "GPU support available" if has_gpu else "CPU only")
except ImportError:
    log_test("faiss-gpu", False, "Not installed")

# Test 9: vllm
try:
    import vllm
    log_test("vllm", True, "Installed")
except ImportError:
    log_test("vllm", False, "Not installed - run: pip install vllm")

# Test 10: diskcache
try:
    import diskcache
    log_test("diskcache", True, "Installed")
except ImportError:
    log_test("diskcache", False, "Not installed - run: pip install diskcache")

# Summary
print("\n" + "=" * 50)
print(f"PHASE 0 ENVIRONMENT CHECK: {results['passed']}/{len(results['tests'])} tests passed")
print("=" * 50)

if results['failed'] > 0:
    print("\nFailed tests:")
    for test in results["tests"]:
        if not test["passed"]:
            print(f"  - {test['name']}: {test['details']}")

# Write results to file
output_file = Path("nsic_env_check_results.json")
with open(output_file, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: {output_file}")

# Exit with error if any tests failed
sys.exit(0 if results["failed"] == 0 else 1)

