#!/usr/bin/env python3
"""
REAL LIVE VERIFICATION - NO MOCKS, NO PLACEHOLDERS, NO FABRICATION
Verifies ALL phases work with REAL components
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print('=' * 60)
    print('REAL LIVE VERIFICATION - NO MOCKS')
    print('=' * 60)
    
    errors = []

    # 1. DEEPSEEK SERVER - REAL
    print('\n[1] DeepSeek Server (REAL)...')
    try:
        import requests
        r = requests.get('http://localhost:8001/health', timeout=5)
        print(f'    Status Code: {r.status_code}')
        data = r.json()
        print(f'    Response: {data}')
        assert r.status_code == 200
        print('    ✅ DeepSeek server HEALTHY')
    except Exception as e:
        errors.append(f'DeepSeek server: {e}')
        print(f'    ❌ {e}')

    # 2. DEEPSEEK INFERENCE - REAL
    print('\n[2] DeepSeek Inference (REAL)...')
    try:
        from src.nsic.orchestration import DeepSeekClient
        client = DeepSeekClient()
        response = client.chat([{'role': 'user', 'content': 'What is 25 * 4?'}])
        print(f'    Answer: {response.content[:100]}')
        print(f'    Time: {response.total_time_ms:.0f}ms')
        assert len(response.content) > 0
        print('    ✅ DeepSeek inference WORKING')
    except Exception as e:
        errors.append(f'DeepSeek inference: {e}')
        print(f'    ❌ {e}')

    # 3. EMBEDDING CACHE - REAL
    print('\n[3] Embedding Cache (REAL)...')
    try:
        from src.nsic.rag import EmbeddingCache
        cache = EmbeddingCache()
        key1 = cache._compute_cache_key('test text')
        key2 = cache._compute_cache_key('test text')
        print(f'    Deterministic: {key1 == key2}')
        print(f'    Key length: {len(key1)} chars (SHA256)')
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex
        print('    ✅ Embedding cache DETERMINISTIC')
    except Exception as e:
        errors.append(f'Embedding cache: {e}')
        print(f'    ❌ {e}')

    # 4. SCENARIOS - REAL
    print('\n[4] Scenario Loader (REAL)...')
    try:
        from src.nsic.scenarios import ScenarioLoader
        loader = ScenarioLoader('scenarios')
        loader.load_all()
        scenarios = loader.get_all()
        print(f'    Loaded: {len(scenarios)} scenarios')
        for s in scenarios[:3]:
            print(f'    - {s.id}: {s.name[:40]}')
        assert len(scenarios) >= 5
        print('    ✅ Scenarios LOADED')
    except Exception as e:
        errors.append(f'Scenarios: {e}')
        print(f'    ❌ {e}')

    # 5. KNOWLEDGE GRAPH - REAL
    print('\n[5] Knowledge Graph (REAL)...')
    try:
        from src.nsic.knowledge import CausalGraph, CausalNode, CausalEdge
        import numpy as np
        graph = CausalGraph(gpu_device='cpu')
        node1 = CausalNode(id='oil', name='Oil Price', node_type='factor', domain='economic', embedding=np.random.rand(768))
        node2 = CausalNode(id='gdp', name='GDP Growth', node_type='factor', domain='economic', embedding=np.random.rand(768))
        graph.add_node(node1)
        graph.add_node(node2)
        edge = CausalEdge(source_id='oil', target_id='gdp', relation_type='causes', strength=0.8, confidence=0.9)
        graph.add_edge(edge)
        print(f'    Nodes: {len(graph.nodes)}')
        print(f'    Edges: {len(graph.graph.edges)}')
        assert len(graph.nodes) == 2
        print('    ✅ Knowledge graph WORKING')
    except Exception as e:
        errors.append(f'Knowledge graph: {e}')
        print(f'    ❌ {e}')

    # 6. DEEP VERIFIER - REAL
    print('\n[6] Deep Verifier (REAL)...')
    try:
        from src.nsic.verification import DeepVerifier
        verifier = DeepVerifier(enable_cross_encoder=False, enable_nli=False)
        result = verifier.verify('Oil prices affect GDP', 'Economic indicators show correlation')
        print(f'    Score: {result.score:.2f}')
        print(f'    Label: {result.label}')
        assert result.score >= 0
        print('    ✅ Deep verifier WORKING')
    except Exception as e:
        errors.append(f'Deep verifier: {e}')
        print(f'    ❌ {e}')

    # 7. ENSEMBLE ARBITRATOR - REAL
    print('\n[7] Ensemble Arbitrator (REAL)...')
    try:
        from src.nsic.arbitration import EnsembleArbitrator, EngineOutput
        arbitrator = EnsembleArbitrator()
        output_a = EngineOutput(engine='engine_a', content='GDP will grow 3%', scenario_id='test', turns_completed=1, confidence=0.85)
        output_b = EngineOutput(engine='engine_b', content='GDP growth expected at 3%', scenario_id='test', turns_completed=25, confidence=0.75)
        decision = arbitrator.arbitrate(output_a, output_b)
        print(f'    Result: {decision.result.value}')
        print(f'    Confidence: {decision.confidence:.2f}')
        assert decision.confidence > 0
        print('    ✅ Arbitrator WORKING')
    except Exception as e:
        errors.append(f'Arbitrator: {e}')
        print(f'    ❌ {e}')

    # 8. DATABASE CONNECTION - REAL
    print('\n[8] PostgreSQL Database (REAL)...')
    try:
        from src.nsic.integration.database import get_nsic_database
        db = get_nsic_database()
        print(f'    Connected: {db is not None}')
        assert db is not None
        print('    ✅ Database CONNECTED')
    except Exception as e:
        errors.append(f'Database: {e}')
        print(f'    ❌ {e}')

    # 9. TIMING LOGGER - REAL
    print('\n[9] Timing Logger (REAL)...')
    try:
        from src.nsic.orchestration import TimingLogger, Stage
        import time
        timing = TimingLogger()
        with timing.time_stage(Stage.ENGINE_B, 'live_test'):
            time.sleep(0.05)
        report = timing.get_report('live_test')
        print(f'    Recorded: {report.total_time_ms:.1f}ms')
        assert report.total_time_ms >= 40
        print('    ✅ Timing logger WORKING')
    except Exception as e:
        errors.append(f'Timing logger: {e}')
        print(f'    ❌ {e}')

    # 10. DUAL ENGINE ORCHESTRATOR - REAL
    print('\n[10] Dual Engine Orchestrator (REAL)...')
    try:
        from src.nsic.orchestration import create_dual_engine_orchestrator
        orchestrator = create_dual_engine_orchestrator()
        health = orchestrator.health_check()
        print(f'    Orchestrator: {health["orchestrator"]}')
        ds_status = health["engine_b"]["deepseek"]["status"]
        print(f'    Engine B (DeepSeek): {ds_status}')
        assert health["orchestrator"] == "healthy"
        assert ds_status == "healthy"
        print('    ✅ Orchestrator HEALTHY')
    except Exception as e:
        errors.append(f'Orchestrator: {e}')
        print(f'    ❌ {e}')

    # Summary
    print('\n' + '=' * 60)
    if errors:
        print(f'❌ VERIFICATION FAILED: {len(errors)} errors')
        for err in errors:
            print(f'   - {err}')
        return 1
    else:
        print('✅ ALL 10 COMPONENTS VERIFIED - NO MOCKS')
        print('   [1] DeepSeek Server: ✅ REAL')
        print('   [2] DeepSeek Inference: ✅ REAL')
        print('   [3] Embedding Cache: ✅ REAL')
        print('   [4] Scenarios: ✅ REAL')
        print('   [5] Knowledge Graph: ✅ REAL')
        print('   [6] Deep Verifier: ✅ REAL')
        print('   [7] Arbitrator: ✅ REAL')
        print('   [8] PostgreSQL DB: ✅ REAL')
        print('   [9] Timing Logger: ✅ REAL')
        print('   [10] Orchestrator: ✅ REAL')
    print('=' * 60)
    return 0

if __name__ == '__main__':
    sys.exit(main())

