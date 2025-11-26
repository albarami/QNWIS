"""Simple agent instantiation test"""
import asyncio
from src.qnwis.agents.base import DataClient
from src.qnwis.llm.client import get_client

async def test_agents():
    print("Testing agent instantiation...")
    
    client = DataClient()
    llm = get_client(provider='anthropic')
    
    print("\n1. Testing NationalizationAgent...")
    try:
        from src.qnwis.agents import NationalizationAgent
        agent = NationalizationAgent(client=client, llm=llm)
        print("✅ NationalizationAgent instantiated")
        
        # Try running it
        result = await agent.run(
            question="What is Qatar's unemployment rate?",
            context={"extracted_facts": []}
        )
        print(f"✅ NationalizationAgent.run() completed: {type(result)}")
        print(f"   Result keys: {result.keys() if hasattr(result, 'keys') else 'N/A'}")
        
    except Exception as e:
        print(f"❌ NationalizationAgent failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. Testing SkillsAgent...")
    try:
        from src.qnwis.agents import SkillsAgent
        agent = SkillsAgent(client=client, llm=llm)
        print("✅ SkillsAgent instantiated")
        
    except Exception as e:
        print(f"❌ SkillsAgent failed: {e}")
    
    print("\n3. Testing labour_economist module...")
    try:
        from src.qnwis.agents import labour_economist
        result = await labour_economist.analyze(
            query="What is Qatar's unemployment rate?",
            extracted_facts=[],
            llm_client=llm
        )
        print(f"✅ labour_economist.analyze() completed: {type(result)}")
        print(f"   Result keys: {result.keys() if hasattr(result, 'keys') else 'N/A'}")
        
    except Exception as e:
        print(f"❌ labour_economist failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agents())
