#!/usr/bin/env python
"""
Comprehensive QNWIS System Verification
Tests all components to ensure they're working correctly
"""
import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, 'src')
os.environ['DATABASE_URL'] = 'postgresql://postgres:1234@localhost:5432/qnwis'

print("=" * 80)
print("QNWIS SYSTEM VERIFICATION")
print("=" * 80)

# Test 1: Database Connection
print("\n[1/10] Testing Database Connection...")
try:
    from qnwis.agents.base import DataClient
    client = DataClient()
    print(f"✅ DataClient initialized")
    print(f"✅ Query registry loaded: {len(client.registry.all_ids())} queries")
    for qid in list(client.registry.all_ids())[:5]:
        print(f"   - {qid}")
except Exception as e:
    print(f"❌ Database connection failed: {e}")

# Test 2: LLM Client
print("\n[2/10] Testing LLM Client...")
try:
    from qnwis.llm.client import LLMClient
    llm = LLMClient(provider='anthropic')
    print(f"✅ LLM Client initialized with provider: {llm.provider}")
    print(f"✅ Model: {llm.model}")
except Exception as e:
    print(f"❌ LLM Client failed: {e}")

# Test 3: Classifier
print("\n[3/10] Testing Classifier...")
try:
    from qnwis.classification.classifier import Classifier
    classifier = Classifier()
    result = classifier.classify_text("What is the unemployment rate in Qatar?")
    print(f"✅ Classifier working")
    print(f"   Complexity: {result.get('complexity')}")
    print(f"   Intent: {result.get('intent')}")
    print(f"   Route: {result.get('route_to')}")
except Exception as e:
    print(f"❌ Classifier failed: {e}")

# Test 4: Agents
print("\n[4/10] Testing Agents...")
try:
    from qnwis.agents.labour_economist import LabourEconomistAgent
    from qnwis.agents.nationalization import NationalizationAgent
    from qnwis.agents.skills import SkillsAgent
    from qnwis.agents.pattern_detective import PatternDetectiveLLMAgent
    from qnwis.agents.national_strategy import NationalStrategyLLMAgent
    
    agents = {
        'LabourEconomist': LabourEconomistAgent,
        'Nationalization': NationalizationAgent,
        'Skills': SkillsAgent,
        'PatternDetective': PatternDetectiveLLMAgent,
        'NationalStrategy': NationalStrategyLLMAgent
    }
    
    for name, AgentClass in agents.items():
        try:
            agent = AgentClass(client, llm)
            print(f"✅ {name} initialized")
        except Exception as e:
            print(f"❌ {name} failed: {e}")
except Exception as e:
    print(f"❌ Agent import failed: {e}")

# Test 5: LangGraph Workflow
print("\n[5/10] Testing LangGraph Workflow...")
try:
    from qnwis.orchestration.graph_llm import LLMWorkflow
    workflow = LLMWorkflow(client, llm, classifier)
    print(f"✅ LangGraph workflow initialized")
    print(f"✅ Graph compiled successfully")
except Exception as e:
    print(f"❌ LangGraph workflow failed: {e}")

# Test 6: RAG System
print("\n[6/10] Testing RAG System...")
try:
    from qnwis.rag.retriever import DocumentRetriever
    retriever = DocumentRetriever()
    results = retriever.retrieve("unemployment rate Qatar", top_k=3)
    print(f"✅ RAG retriever working")
    print(f"✅ Retrieved {len(results)} documents")
except Exception as e:
    print(f"❌ RAG system failed: {e}")

# Test 7: Prefetch System
print("\n[7/10] Testing Prefetch System...")
try:
    from qnwis.orchestration.prefetch import PrefetchOrchestrator
    prefetch = PrefetchOrchestrator(client)
    result = asyncio.run(prefetch.prefetch("What is unemployment in Qatar?"))
    print(f"✅ Prefetch working")
    print(f"   Queries attempted: {result.get('queries_attempted', 0)}")
    print(f"   Queries succeeded: {result.get('queries_succeeded', 0)}")
    print(f"   Facts extracted: {len(result.get('data', {}).get('facts', []))}")
except Exception as e:
    print(f"❌ Prefetch failed: {e}")

# Test 8: External APIs
print("\n[8/10] Testing External APIs...")
apis_to_test = [
    ('data.apis.lmis_mol_api', 'LMISAPIClient'),
    ('data.apis.world_bank', 'UDCGlobalDataIntegrator'),
    ('data.apis.gcc_stat', 'GCCStatClient'),
    ('data.apis.ilo_stats', 'ILOStatsClient'),
    ('data.apis.qatar_opendata', 'QatarOpenDataScraperV2'),
]

for module_path, class_name in apis_to_test:
    try:
        module = __import__(module_path, fromlist=[class_name])
        api_class = getattr(module, class_name)
        print(f"✅ {class_name} importable")
    except Exception as e:
        print(f"❌ {class_name} failed: {e}")

# Test 9: Database Queries
print("\n[9/10] Testing Database Queries...")
try:
    test_queries = [
        'q_unemployment_rate_gcc_latest',
        'employment_share_by_gender',
        'retention_rate_by_sector'
    ]
    
    for qid in test_queries:
        try:
            result = client.run(qid)
            rows = len(result.data) if hasattr(result, 'data') else 0
            print(f"✅ {qid}: {rows} rows")
        except Exception as e:
            print(f"❌ {qid}: {e}")
except Exception as e:
    print(f"❌ Query testing failed: {e}")

# Test 10: Full Workflow Execution
print("\n[10/10] Testing Full Workflow...")
try:
    from qnwis.orchestration.streaming import run_workflow_stream
    
    print("Running workflow with test question...")
    question = "What is the unemployment rate in Qatar?"
    
    async def test_workflow():
        events = []
        async for event in run_workflow_stream(question, client, llm, classifier):
            events.append(event)
            print(f"   Stage: {event.stage} - Status: {event.status}")
            if event.stage in ['done', 'error']:
                break
        return events
    
    events = asyncio.run(test_workflow())
    print(f"✅ Workflow completed with {len(events)} events")
    
except Exception as e:
    print(f"❌ Full workflow failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
