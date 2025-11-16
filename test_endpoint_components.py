"""Test creating the components like the endpoint does"""
import os

try:
    from src.qnwis.agents.base import DataClient
    from src.qnwis.llm.client import LLMClient
    from src.qnwis.classification.classifier import Classifier
    
    # Simulate what the endpoint does
    provider = "stub" or os.getenv("QNWIS_LLM_PROVIDER", "anthropic")
    model = None
    
    print(f"Creating components with provider='{provider}', model={model}")
    
    print("1. Creating DataClient...")
    data_client = DataClient()
    print("   ✅ DataClient created")
    
    print("2. Creating LLMClient...")
    llm_client = LLMClient(provider=provider, model=model)
    print(f"   ✅ LLMClient created: {llm_client}")
    
    print("3. Creating Classifier...")
    classifier = Classifier()
    print("   ✅ Classifier created")
    
    print("\n✅ All components created successfully!")
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
