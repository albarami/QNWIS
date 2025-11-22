"""
Compare output quality: Legacy vs LangGraph
Checks for consistency in analysis and synthesis
"""
import asyncio
import os
from typing import Dict, Any
from difflib import SequenceMatcher

async def compare_outputs(query: str) -> Dict[str, Any]:
    """Compare outputs from both workflows"""
    
    # Run with legacy
    os.environ["QNWIS_WORKFLOW_IMPL"] = "legacy"
    from qnwis.orchestration.workflow import run_intelligence_query
    
    print(f"Running legacy workflow...")
    legacy_result = await run_intelligence_query(query)
    
    # Run with langgraph
    os.environ["QNWIS_WORKFLOW_IMPL"] = "langgraph"
    # Need to reload module to pick up new env var
    import importlib
    import qnwis.orchestration.workflow
    importlib.reload(qnwis.orchestration.workflow)
    from qnwis.orchestration.workflow import run_intelligence_query as run_lg
    
    print(f"Running langgraph workflow...")
    langgraph_result = await run_lg(query)
    
    # Compare
    legacy_synthesis = legacy_result.get("final_synthesis", "")
    langgraph_synthesis = langgraph_result.get("final_synthesis", "")
    
    # Calculate similarity
    similarity = SequenceMatcher(None, legacy_synthesis, langgraph_synthesis).ratio()
    
    return {
        "query": query,
        "legacy_length": len(legacy_synthesis),
        "langgraph_length": len(langgraph_synthesis),
        "similarity": similarity,
        "legacy_confidence": legacy_result.get("confidence_score", 0.0),
        "langgraph_confidence": langgraph_result.get("confidence_score", 0.0),
        "legacy_facts": len(legacy_result.get("extracted_facts", [])),
        "langgraph_facts": len(langgraph_result.get("extracted_facts", [])),
        "legacy_synthesis": legacy_synthesis[:500],
        "langgraph_synthesis": langgraph_synthesis[:500],
    }

async def main():
    """Run output comparison"""
    
    print("="*80)
    print("OUTPUT QUALITY COMPARISON")
    print("="*80)
    
    test_query = "Analyze Qatar's economic diversification progress with sector GDP breakdown"
    
    comparison = await compare_outputs(test_query)
    
    print(f"\nQuery: {comparison['query']}")
    print(f"\nLegacy workflow:")
    print(f"  Synthesis length: {comparison['legacy_length']} chars")
    print(f"  Confidence: {comparison['legacy_confidence']:.2f}")
    print(f"  Facts extracted: {comparison['legacy_facts']}")
    print(f"\nLangGraph workflow:")
    print(f"  Synthesis length: {comparison['langgraph_length']} chars")
    print(f"  Confidence: {comparison['langgraph_confidence']:.2f}")
    print(f"  Facts extracted: {comparison['langgraph_facts']}")
    print(f"\nSimilarity: {comparison['similarity']*100:.1f}%")
    
    print(f"\nLegacy synthesis (first 500 chars):")
    print(comparison['legacy_synthesis'])
    
    print(f"\nLangGraph synthesis (first 500 chars):")
    print(comparison['langgraph_synthesis'])
    
    print("\n" + "="*80)
    if comparison['similarity'] > 0.7:
        print("[OK] Outputs are highly similar (>70%)")
    elif comparison['similarity'] > 0.5:
        print("[WARN] Outputs are moderately similar (50-70%)")
    else:
        print("[ATTENTION] Outputs differ significantly (<50%)")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
