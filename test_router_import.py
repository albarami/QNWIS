"""Test if router imports correctly"""
import sys

try:
    print("Importing router...")
    from src.qnwis.api.routers import council_llm
    print("✅ Router imported successfully")
    
    print("\nChecking council_stream_llm function...")
    func = council_llm.council_stream_llm
    print(f"✅ Function exists: {func}")
    
    print("\nChecking function signature...")
    import inspect
    sig = inspect.signature(func)
    print(f"Parameters: {sig.parameters}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
