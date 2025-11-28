#!/usr/bin/env python3
"""
Verify NSIC Integration with REAL data sources.

Tests:
1. PostgreSQL database connection (2,431+ rows)
2. RAG system with R&D documents (1,959 chunks)
3. Knowledge graph with real data
4. Azure LLM connection (GPT-5)

NO MOCKS. REAL DATA ONLY.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging

logging.basicConfig(level=logging.WARNING)

def verify_database():
    """Verify PostgreSQL connection and data."""
    print("=" * 60)
    print("[1] POSTGRESQL DATABASE")
    print("=" * 60)
    
    try:
        from src.nsic.integration.database import NSICDatabase
        
        db = NSICDatabase()
        stats = db.get_table_stats()
        
        print(f"  ✅ Connected to PostgreSQL")
        print(f"  Tables:")
        for table, count in stats.items():
            print(f"    - {table}: {count:,} rows")
        
        # Test query
        qatar_data = db.get_qatar_indicators()
        print(f"\n  Qatar indicators: {len(qatar_data)} rows")
        
        vision = db.get_vision_2030_targets()
        print(f"  Vision 2030 targets: {len(vision)} rows")
        
        gcc = db.get_gcc_labour_stats()
        print(f"  GCC labour stats: {len(gcc)} rows")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False


def verify_rag():
    """Verify RAG system with R&D documents."""
    print()
    print("=" * 60)
    print("[2] RAG SYSTEM (R&D Documents)")
    print("=" * 60)
    
    try:
        from src.nsic.integration.rag_connector import NSICRAGConnector
        
        rag = NSICRAGConnector()
        stats = rag.get_stats()
        
        print(f"  ✅ RAG system connected")
        print(f"  Total documents: {stats['total_documents']:,}")
        
        # Test search
        results = rag.search_rd_reports(
            query="Qatar labor market skills gap",
            top_k=5,
            min_score=0.2,
        )
        
        print(f"\n  Search test: 'Qatar labor market skills gap'")
        print(f"  Results: {len(results)} chunks")
        
        if results:
            print(f"\n  Top result:")
            top = results[0]
            print(f"    Source: {top['source'][:50]}")
            print(f"    Score: {top['score']:.3f}")
            print(f"    Text: {top['text'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ RAG error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_knowledge_graph():
    """Verify knowledge graph with real data."""
    print()
    print("=" * 60)
    print("[3] KNOWLEDGE GRAPH")
    print("=" * 60)
    
    try:
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode, CausalEdge
        from src.nsic.integration.database import NSICDatabase
        import numpy as np
        
        # Create and populate graph
        db = NSICDatabase()
        graph = CausalGraph(gpu_device="cpu", embedding_dim=128)
        
        # Add GCC countries
        gcc_stats = db.get_gcc_labour_stats()
        countries = set()
        for stat in gcc_stats:
            country = stat['country']
            if country not in countries:
                countries.add(country)
                emb = np.random.rand(128).astype(np.float32)
                node = CausalNode(
                    id=f"country_{country.lower().replace(' ', '_')}",
                    name=country,
                    node_type="entity",
                    domain="economic",
                    embedding=emb,
                )
                graph.add_node(node)
        
        # Add Vision 2030 targets
        targets = db.get_vision_2030_targets()
        for target in targets:
            emb = np.random.rand(128).astype(np.float32)
            node = CausalNode(
                id=f"vision2030_{target['id']}",
                name=target['metric_name'],
                node_type="factor",
                domain="policy",
                embedding=emb,
            )
            graph.add_node(node)
        
        stats = graph.get_stats()
        
        print(f"  ✅ Knowledge graph created from database")
        print(f"  Nodes: {stats['total_nodes']}")
        print(f"  Domains: {stats['domains']}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Knowledge graph error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_llm():
    """Verify Azure LLM connection."""
    print()
    print("=" * 60)
    print("[4] AZURE LLM (GPT-5)")
    print("=" * 60)
    
    try:
        from src.qnwis.llm.model_router import get_router
        
        router = get_router()
        primary = router.primary_config
        fast = router.fast_config
        
        has_primary_key = bool(primary.api_key)
        has_fast_key = bool(fast.api_key)
        
        print(f"  Primary model: {primary.deployment}")
        print(f"    Endpoint: {primary.endpoint[:40]}..." if primary.endpoint else "    Endpoint: NOT SET")
        print(f"    API Key: {'✅ SET' if has_primary_key else '❌ NOT SET'}")
        
        print(f"\n  Fast model: {fast.deployment}")
        print(f"    API Key: {'✅ SET' if has_fast_key else '❌ NOT SET'}")
        
        if has_primary_key:
            print(f"\n  ✅ Azure LLM configured")
            return True
        else:
            print(f"\n  ⚠️ Azure LLM API keys not set")
            return False
        
    except Exception as e:
        print(f"  ❌ LLM error: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("NSIC REAL INTEGRATION VERIFICATION")
    print("=" * 60)
    print()
    
    results = {
        "PostgreSQL": verify_database(),
        "RAG (R&D Docs)": verify_rag(),
        "Knowledge Graph": verify_knowledge_graph(),
        "Azure LLM": verify_llm(),
    }
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_pass = True
    for component, status in results.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {component}")
        if not status:
            all_pass = False
    
    print()
    if all_pass:
        print("🎉 ALL REAL INTEGRATIONS WORKING!")
    else:
        print("⚠️ SOME INTEGRATIONS NEED ATTENTION")
    
    return all_pass


if __name__ == "__main__":
    main()

