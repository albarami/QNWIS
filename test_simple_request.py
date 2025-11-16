"""Simple request test"""
import asyncio
from src.qnwis.api.routers.council_llm import CouncilRequest

# Test validation
try:
    req = CouncilRequest(
        question="Test query",
        provider="stub",
        model=None
    )
    print(f"✅ Validation passed!")
    print(f"   question: {req.question}")
    print(f"   provider: {req.provider}")
    print(f"   model: {req.model}")
except Exception as e:
    print(f"❌ Validation failed: {e}")
    import traceback
    traceback.print_exc()
