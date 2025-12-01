import sys
import traceback

print("Step 1: Importing exllamav2...", flush=True)
try:
    import exllamav2
    print("Step 2: ExLlamaV2 module loaded", flush=True)
    print(f"  Version: {exllamav2.__version__ if hasattr(exllamav2, '__version__') else 'N/A'}", flush=True)
    print(f"  Path: {exllamav2.__file__}", flush=True)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

print("Step 3: Importing ExLlamaV2 class...", flush=True)
try:
    from exllamav2 import ExLlamaV2
    print("  ExLlamaV2 class imported", flush=True)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

print("SUCCESS: ExLlamaV2 is working!", flush=True)

