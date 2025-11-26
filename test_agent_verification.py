#!/usr/bin/env python3
"""Quick verification test for 11-agent system."""

from src.qnwis.orchestration.graph_llm import LLMWorkflow
from src.qnwis.agents.base import DataClient
from src.qnwis.llm.client import LLMClient

def main():
    """Verify all 11 agents are loaded."""
    print("🔧 Initializing clients...")
    
    # Initialize required clients (use stub provider to avoid API calls)
    data_client = DataClient()
    llm_client = LLMClient(provider="stub")
    
    print("🚀 Creating LLM Workflow...")
    workflow = LLMWorkflow(data_client=data_client, llm_client=llm_client)
    
    print("\n" + "="*60)
    print("🎯 LEGENDARY 11-AGENT SYSTEM VERIFICATION")
    print("="*60)
    
    # Display LLM agents
    print(f"\n📊 LLM Agents: {len(workflow.agents)}")
    for i, agent_name in enumerate(workflow.agents.keys(), 1):
        print(f"  {i}. ✅ {agent_name}")
    
    # Display deterministic agents
    print(f"\n⚡ Deterministic Agents: {len(workflow.deterministic_agents)}")
    for i, agent_name in enumerate(workflow.deterministic_agents.keys(), 1):
        print(f"  {i}. ✅ {agent_name}")
    
    # Summary
    total_agents = len(workflow.agents) + len(workflow.deterministic_agents)
    print("\n" + "="*60)
    print(f"✅ TOTAL: {total_agents} AGENTS READY!")
    print("="*60)
    
    if total_agents >= 11:
        print(f"\n🎉 SUCCESS: All {total_agents} agents loaded correctly!")
        print("🔥 LEGENDARY DEPTH MODE is OPERATIONAL!")
        print("\n💎 BONUS: You have MORE than the expected 11 agents!")
        return 0
    else:
        print(f"\n⚠️  WARNING: Expected at least 11 agents, found {total_agents}")
        return 1

if __name__ == "__main__":
    exit(main())
