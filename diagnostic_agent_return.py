"""
Diagnostic: Check what agents actually return
"""
import asyncio
from src.qnwis.agents.labour_economist import analyze
from src.qnwis.llm.client import LLMClient

async def test_agent_return():
    """Check what agents actually return"""
    
    llm = LLMClient(provider='anthropic', model='claude-sonnet-4-20250514')
    
    test_facts = [
        {
            "metric": "test_metric",
            "value": 100,
            "source": "test",
            "confidence": 0.8
        }
    ]
    
    print("Calling labour_economist.analyze()...")
    result = await analyze("What is the unemployment rate?", test_facts, llm)
    
    print(f"\nResult type: {type(result)}")
    print(f"Is dict: {isinstance(result, dict)}")
    
    if isinstance(result, dict):
        print(f"Result keys: {list(result.keys())}")
        print(f"Has 'agent_name': {'agent_name' in result}")
        if 'agent_name' in result:
            print(f"agent_name value: {result['agent_name']}")
    else:
        print(f"Result is NOT a dict!")
        print(f"Result preview: {str(result)[:200]}...")

asyncio.run(test_agent_return())
