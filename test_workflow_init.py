"""Test workflow initialization."""
import sys
import traceback

try:
    from src.qnwis.agents.base import DataClient
    from src.qnwis.llm.client import LLMClient
    from src.qnwis.classification.classifier import Classifier
    from src.qnwis.orchestration.graph_llm import build_workflow
    
    print("1. Initializing DataClient...")
    data_client = DataClient()
    print(f"   ✓ DataClient initialized (queries_dir={data_client.queries_dir})")
    
    print("2. Initializing LLMClient...")
    llm_client = LLMClient(provider="stub")
    print(f"   ✓ LLMClient initialized (provider=stub)")
    
    print("3. Initializing Classifier...")
    classifier = Classifier()
    print(f"   ✓ Classifier initialized")
    
    print("4. Building workflow...")
    workflow = build_workflow(data_client, llm_client, classifier)
    print(f"   ✓ Workflow built successfully")
    
    print("\n✅ All components initialized successfully!")
    
except Exception as e:
    print(f"\n❌ Error during initialization:")
    print(f"   {type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
