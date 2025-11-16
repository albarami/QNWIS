"""
Diagnostic: Check which agents exist and are being used
"""

print("=" * 60)
print("AGENT IMPORT TEST")
print("=" * 60)

try:
    from src.qnwis.agents import labour_economist
    print("✅ 1. labour_economist imported")
except Exception as e:
    print(f"❌ 1. labour_economist FAILED: {e}")

try:
    from src.qnwis.agents import financial_economist
    print("✅ 2. financial_economist imported")
except Exception as e:
    print(f"❌ 2. financial_economist FAILED: {e}")

try:
    from src.qnwis.agents import market_economist
    print("✅ 3. market_economist imported")
except Exception as e:
    print(f"❌ 3. market_economist FAILED: {e}")

try:
    from src.qnwis.agents import operations_expert
    print("✅ 4. operations_expert imported")
except Exception as e:
    print(f"❌ 4. operations_expert FAILED: {e}")

try:
    from src.qnwis.agents import research_scientist
    print("✅ 5. research_scientist imported")
except Exception as e:
    print(f"❌ 5. research_scientist FAILED: {e}")

print("\n" + "=" * 60)
print("AGENT ANALYZE FUNCTION TEST")
print("=" * 60)

try:
    from src.qnwis.agents.labour_economist import analyze
    print("✅ labour_economist.analyze exists")
    print(f"   Type: {type(analyze)}")
except Exception as e:
    print(f"❌ labour_economist.analyze FAILED: {e}")

try:
    from src.qnwis.agents.financial_economist import analyze
    print("✅ financial_economist.analyze exists")
except Exception as e:
    print(f"❌ financial_economist.analyze FAILED: {e}")

try:
    from src.qnwis.agents.market_economist import analyze
    print("✅ market_economist.analyze exists")
except Exception as e:
    print(f"❌ market_economist.analyze FAILED: {e}")

try:
    from src.qnwis.agents.operations_expert import analyze
    print("✅ operations_expert.analyze exists")
except Exception as e:
    print(f"❌ operations_expert.analyze FAILED: {e}")

try:
    from src.qnwis.agents.research_scientist import analyze
    print("✅ research_scientist.analyze exists")
except Exception as e:
    print(f"❌ research_scientist.analyze FAILED: {e}")

print("\n" + "=" * 60)
print("AGENT MAP IN WORKFLOW")
print("=" * 60)

try:
    from src.qnwis.orchestration.graph_llm import LLMWorkflow
    print("Creating workflow...")
    workflow = LLMWorkflow()
    print("✅ Workflow created")
except Exception as e:
    print(f"❌ Workflow creation FAILED: {e}")
    import traceback
    traceback.print_exc()
