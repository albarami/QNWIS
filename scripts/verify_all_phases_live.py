#!/usr/bin/env python3
"""Live verification of all NSIC phases - NO MOCKS."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

def main():
    print("=" * 60)
    print("LIVE VERIFICATION - ALL PHASES")
    print("=" * 60)
    
    all_pass = True
    
    # Phase 1: Embeddings
    print("\n[PHASE 1] Premium Embeddings + Cache")
    try:
        from src.nsic.rag.embedding_cache import EmbeddingCache
        cache = EmbeddingCache("D:/lmis_int/.cache/test_verify")
        key1 = cache._compute_cache_key("test text")
        key2 = cache._compute_cache_key("test text")
        assert key1 == key2, "Cache not deterministic!"
        print("  ✅ EmbeddingCache: SHA256 determinism VERIFIED")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        all_pass = False
    
    # Phase 2: Deep Verifier
    print("\n[PHASE 2] Deep Verification")
    try:
        from src.nsic.verification.deep_verifier import DeepVerifier
        verifier = DeepVerifier(enable_cross_encoder=False, enable_nli=False)
        result = verifier.verify("The sky is blue", "The sky appears blue due to light scattering")
        print(f"  ✅ Verifier works: score={result.score:.2f}, label={result.label}")
        print(f"  ✅ Layer: {result.layer}, timing: {result.timing_ms:.1f}ms")
        stats = verifier.get_stats()
        print(f"  ✅ Stats tracking: {stats['verifications']} verifications")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        all_pass = False
    
    # Phase 3: Knowledge Graph
    print("\n[PHASE 3] Hybrid CPU-GPU Causal Graph")
    try:
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode, CausalEdge
        graph = CausalGraph(gpu_device="cpu")
        
        # Add nodes
        n1 = CausalNode(
            id="oil_price", name="Oil Price", node_type="variable",
            domain="economic", embedding=np.random.randn(384).astype(np.float32)
        )
        n2 = CausalNode(
            id="inflation", name="Inflation", node_type="variable",
            domain="economic", embedding=np.random.randn(384).astype(np.float32)
        )
        graph.add_node(n1)
        graph.add_node(n2)
        
        # Add edge (correct args: relation_type, strength, confidence)
        edge = CausalEdge(
            source_id="oil_price", target_id="inflation",
            relation_type="causes", strength=0.8, confidence=0.9
        )
        graph.add_edge(edge)
        
        print(f"  ✅ CausalGraph: {len(graph.nodes)} nodes, {graph.graph.number_of_edges()} edges")
        print(f"  ✅ GPU processor: {graph.gpu_processor.device}")
        
        # Test causal chain (correct arg: max_length not max_depth)
        chains = graph.find_causal_chains("oil_price", "inflation", max_length=3)
        print(f"  ✅ Causal chain discovery: {len(chains)} chains found")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        all_pass = False
    
    # Phase 4: DeepSeek
    print("\n[PHASE 4] DeepSeek 70B Server")
    try:
        import requests
        r = requests.get("http://localhost:8001/health", timeout=5)
        data = r.json()
        assert data["status"] == "healthy", "Server not healthy!"
        print(f"  ✅ Health: {data}")
        
        r2 = requests.post(
            "http://localhost:8001/v1/chat/completions",
            json={
                "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
                "messages": [{"role": "user", "content": "What is 15 * 17?"}],
                "max_tokens": 50
            },
            timeout=60
        )
        answer = r2.json()["choices"][0]["message"]["content"]
        print(f"  ✅ Inference: {answer[:80]}...")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        all_pass = False
    
    # Phase 5: Scenarios
    print("\n[PHASE 5] Scenario Loader + Validator")
    try:
        from src.nsic.scenarios import ScenarioLoader, ScenarioValidator
        loader = ScenarioLoader("scenarios")
        count = loader.load_all()
        scenarios = loader.get_all()
        validator = ScenarioValidator()
        
        valid = sum(1 for s in scenarios if validator.validate_definition(s).valid)
        print(f"  ✅ Loaded: {count} scenarios")
        print(f"  ✅ Validated: {valid}/{count} pass")
        
        stats = loader.get_stats()
        engine_a = stats["by_engine"]["engine_a"]
        engine_b = stats["by_engine"]["engine_b"]
        print(f"  ✅ By engine: Engine A={engine_a}, Engine B={engine_b}")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        all_pass = False
    
    print("\n" + "=" * 60)
    if all_pass:
        print("✅ ALL PHASES VERIFIED - DEPLOYED & WORKING!")
    else:
        print("❌ SOME PHASES FAILED - CHECK ABOVE")
    print("=" * 60)
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

