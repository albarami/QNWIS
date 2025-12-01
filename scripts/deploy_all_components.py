#!/usr/bin/env python3
"""
NSIC Complete Component Deployment

Deploys ALL components to their CORRECT GPUs:
- GPU 0-1: Premium Embeddings (instructor-xl)
- GPU 2-3: DeepSeek Instance 1 (separate server)
- GPU 4:   Knowledge Graph
- GPU 5:   Deep Verification
- GPU 6-7: DeepSeek Instance 2 (separate server)

This script pre-loads and verifies all components.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_gpu_status():
    """Check current GPU status."""
    try:
        import torch
        print("\n" + "="*60)
        print("GPU STATUS")
        print("="*60)
        
        for i in range(torch.cuda.device_count()):
            name = torch.cuda.get_device_name(i)
            mem_total = torch.cuda.get_device_properties(i).total_memory / 1e9
            mem_used = torch.cuda.memory_allocated(i) / 1e9
            print(f"GPU {i}: {name}")
            print(f"       Memory: {mem_used:.1f}GB / {mem_total:.1f}GB")
        print("="*60)
    except Exception as e:
        print(f"GPU check failed: {e}")


def deploy_embeddings():
    """Deploy Premium Embeddings on GPU 0-1."""
    print("\n" + "="*60)
    print("DEPLOYING: Premium Embeddings (GPU 0-1)")
    print("="*60)
    
    try:
        from src.nsic.rag import PremiumEmbeddingService
        
        start = time.time()
        service = PremiumEmbeddingService(
            gpu_ids=[0, 1],
            cache_enabled=True,
        )
        
        # Test encoding
        test_texts = [
            "What is Qatar's economic diversification strategy?",
            "How does oil price affect GDP growth?"
        ]
        
        embeddings = service.encode(test_texts)
        elapsed = time.time() - start
        
        print(f"✅ Embeddings deployed in {elapsed:.1f}s")
        print(f"   Model: {service.model_name}")
        print(f"   Dimension: {service.embedding_dim}")
        print(f"   GPUs: {service.gpu_ids}")
        print(f"   Test encoding: {len(embeddings)} vectors of dim {embeddings[0].shape}")
        
        return service
        
    except Exception as e:
        print(f"❌ Embeddings deployment FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def deploy_verification():
    """Deploy Deep Verification on GPU 5."""
    print("\n" + "="*60)
    print("DEPLOYING: Deep Verification Engine (GPU 5)")
    print("="*60)
    
    try:
        from src.nsic.verification import DeepVerifier
        
        start = time.time()
        verifier = DeepVerifier(
            gpu_id=5,
            enable_cross_encoder=True,
            enable_nli=True,
        )
        
        # Test verification
        result = verifier.verify(
            claim="Qatar hosted the 2022 FIFA World Cup",
            evidence="The 2022 FIFA World Cup was held in Qatar from November to December 2022."
        )
        elapsed = time.time() - start
        
        print(f"✅ Verification deployed in {elapsed:.1f}s")
        print(f"   GPU: 5")
        print(f"   Test result: score={result.score:.2f}, label={result.label}")
        
        return verifier
        
    except Exception as e:
        print(f"❌ Verification deployment FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def deploy_knowledge_graph():
    """Deploy Knowledge Graph on GPU 4."""
    print("\n" + "="*60)
    print("DEPLOYING: Knowledge Graph (GPU 4)")
    print("="*60)
    
    try:
        from src.nsic.knowledge import CausalGraph, CausalNode, CausalEdge
        import numpy as np
        
        start = time.time()
        graph = CausalGraph(
            gpu_device="cuda:4",
            embedding_dim=768,
        )
        
        # Add test nodes
        node1 = CausalNode(
            id="oil_price", 
            name="Oil Price", 
            node_type="factor",
            domain="economic",
            embedding=np.random.rand(768).astype(np.float32)
        )
        node2 = CausalNode(
            id="gdp_growth",
            name="GDP Growth",
            node_type="factor",
            domain="economic",
            embedding=np.random.rand(768).astype(np.float32)
        )
        
        graph.add_node(node1)
        graph.add_node(node2)
        
        # Add test edge
        edge = CausalEdge(
            source_id="oil_price",
            target_id="gdp_growth",
            relation_type="causes",
            strength=0.8,
            confidence=0.9
        )
        graph.add_edge(edge)
        
        elapsed = time.time() - start
        
        print(f"✅ Knowledge Graph deployed in {elapsed:.1f}s")
        print(f"   GPU: 4")
        print(f"   Nodes: {len(graph.nodes)}")
        print(f"   Edges: {len(graph.graph.edges)}")
        
        return graph
        
    except Exception as e:
        print(f"❌ Knowledge Graph deployment FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_deepseek_instances():
    """Check DeepSeek instances are running."""
    print("\n" + "="*60)
    print("CHECKING: DeepSeek Instances (GPU 2-3, 6-7)")
    print("="*60)
    
    import requests
    
    instances = [
        ("Instance 1", "http://localhost:8001/health", [2, 3]),
        ("Instance 2", "http://localhost:8002/health", [6, 7]),
    ]
    
    all_healthy = True
    for name, url, gpus in instances:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {name}: HEALTHY")
                print(f"   GPUs: {data.get('gpus', gpus)}")
                print(f"   Port: {data.get('port')}")
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"❌ {name}: NOT RUNNING - {e}")
            all_healthy = False
    
    return all_healthy


def main():
    print("="*60)
    print("NSIC COMPLETE COMPONENT DEPLOYMENT")
    print("="*60)
    print()
    print("CORRECT GPU Allocation:")
    print("  GPU 0-1: Premium Embeddings (instructor-xl)")
    print("  GPU 2-3: DeepSeek Instance 1 (port 8001)")
    print("  GPU 4:   Knowledge Graph")
    print("  GPU 5:   Deep Verification")
    print("  GPU 6-7: DeepSeek Instance 2 (port 8002)")
    print()
    
    # Check initial GPU status
    check_gpu_status()
    
    # Deploy components
    results = {}
    
    # 1. Check DeepSeek (should already be running)
    results["deepseek"] = check_deepseek_instances()
    
    # 2. Deploy Embeddings
    results["embeddings"] = deploy_embeddings() is not None
    
    # 3. Deploy Knowledge Graph
    results["knowledge_graph"] = deploy_knowledge_graph() is not None
    
    # 4. Deploy Verification
    results["verification"] = deploy_verification() is not None
    
    # Final GPU status
    check_gpu_status()
    
    # Summary
    print("\n" + "="*60)
    print("DEPLOYMENT SUMMARY")
    print("="*60)
    
    all_ok = True
    for component, status in results.items():
        emoji = "✅" if status else "❌"
        print(f"  {emoji} {component}: {'DEPLOYED' if status else 'FAILED'}")
        if not status:
            all_ok = False
    
    print("="*60)
    
    if all_ok:
        print("\n✅ ALL COMPONENTS DEPLOYED SUCCESSFULLY")
        print("   Ready for Phase 10 E2E Testing")
        return 0
    else:
        print("\n❌ SOME COMPONENTS FAILED TO DEPLOY")
        print("   Fix issues before running E2E tests")
        return 1


if __name__ == "__main__":
    sys.exit(main())

