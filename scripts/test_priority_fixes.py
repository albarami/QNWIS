"""Quick test of priority fixes before full diagnostic run."""
import sys
sys.path.insert(0, ".")

print("=" * 60)
print("TESTING PRIORITY FIXES")
print("=" * 60)

# ============================================================
# FIX 1: engine_a_had_quantitative_context in streaming.py
# ============================================================
print("\n[FIX 1] Checking streaming.py payload includes flag...")
try:
    with open("src/qnwis/orchestration/streaming.py", "r") as f:
        content = f.read()
    
    if '"engine_a_had_quantitative_context"' in content:
        # Check it's in the payload section
        if 'accumulated_state.get("engine_a_had_quantitative_context"' in content:
            print("  ✅ PASS: Flag added to payload with accumulated_state.get()")
        else:
            print("  ⚠️ WARN: Flag found but might not use accumulated_state.get()")
    else:
        print("  ❌ FAIL: Flag not found in streaming.py")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

# ============================================================
# FIX 2: NationalStrategy null check
# ============================================================
print("\n[FIX 2] Checking NationalStrategy null check...")
try:
    with open("src/qnwis/agents/national_strategy.py", "r") as f:
        content = f.read()
    
    if "gcc_res.rows is None or len(gcc_res.rows)" in content:
        print("  ✅ PASS: Null check added for gcc_res.rows")
    else:
        print("  ❌ FAIL: Null check not found")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

# ============================================================
# FIX 3: LabourEconomist null check
# ============================================================
print("\n[FIX 3] Checking LabourEconomist null check...")
try:
    with open("src/qnwis/agents/labour_economist.py", "r") as f:
        content = f.read()
    
    if "result.rows is None" in content:
        print("  ✅ PASS: Null check added for result.rows")
    else:
        print("  ❌ FAIL: Null check not found")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

# ============================================================
# FIX 4: Test NationalStrategy with None data
# ============================================================
print("\n[FIX 4] Testing NationalStrategy with None data...")
try:
    from unittest.mock import MagicMock
    from src.qnwis.agents.national_strategy import NationalStrategyAgent
    
    # Create mock client that returns None rows
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.rows = None  # Simulate no data
    mock_client.run.return_value = mock_result
    
    agent = NationalStrategyAgent(mock_client)
    result = agent.gcc_benchmark(min_countries=3)
    
    if hasattr(result, 'warnings') and result.warnings:
        print(f"  ✅ PASS: Agent handled None rows gracefully")
        print(f"     Warnings: {result.warnings}")
    else:
        print("  ⚠️ WARN: Agent returned but no warnings")
except TypeError as e:
    if "NoneType" in str(e):
        print(f"  ❌ FAIL: Still getting NoneType error: {e}")
    else:
        print(f"  ❌ ERROR: {e}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

# ============================================================
# FIX 5: Test LabourEconomist with None data
# ============================================================
print("\n[FIX 5] Testing LabourEconomist with None data...")
try:
    from unittest.mock import MagicMock
    from src.qnwis.agents.labour_economist import LabourEconomistAgent
    
    # Create mock client that returns None rows
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.rows = None  # Simulate no data
    mock_result.warnings = []
    mock_client.run.return_value = mock_result
    
    agent = LabourEconomistAgent(mock_client)
    result = agent.run()
    
    if hasattr(result, 'warnings') and result.warnings:
        print(f"  ✅ PASS: Agent handled None rows gracefully")
        print(f"     Warnings: {result.warnings}")
    else:
        print("  ⚠️ WARN: Agent returned but no warnings")
except TypeError as e:
    if "NoneType" in str(e):
        print(f"  ❌ FAIL: Still getting NoneType error: {e}")
    else:
        print(f"  ❌ ERROR: {e}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)

