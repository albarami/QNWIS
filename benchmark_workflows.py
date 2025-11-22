"""
Performance benchmark: Legacy vs LangGraph workflows
Compares execution time, output quality, and resource usage
"""
import asyncio
import time
import os
from typing import Dict, Any, List

# Test queries representing different complexity levels
TEST_QUERIES = [
    # Simple queries (fact lookups)
    {
        "query": "What is Qatar's current unemployment rate?",
        "expected_complexity": "simple",
        "category": "fact_lookup"
    },
    {
        "query": "What is Qatar's GDP in 2024?",
        "expected_complexity": "simple",
        "category": "fact_lookup"
    },
    {
        "query": "Show me Qatar's latest inflation rate",
        "expected_complexity": "simple",
        "category": "fact_lookup"
    },
    
    # Medium queries (analysis)
    {
        "query": "Analyze Qatar's employment trends over the last 5 years",
        "expected_complexity": "medium",
        "category": "trend_analysis"
    },
    {
        "query": "How is Qatar's economic diversification progressing?",
        "expected_complexity": "medium",
        "category": "sector_analysis"
    },
    {
        "query": "What are the key workforce planning challenges in Qatar?",
        "expected_complexity": "medium",
        "category": "strategic_analysis"
    },
    
    # Complex queries (strategic decisions)
    {
        "query": "Should Qatar invest QAR 15B in green hydrogen infrastructure by 2030?",
        "expected_complexity": "complex",
        "category": "strategic_decision"
    },
    {
        "query": "Evaluate the feasibility of achieving 50% Qatarization by 2030",
        "expected_complexity": "complex",
        "category": "policy_evaluation"
    },
]

async def benchmark_query(query: str, workflow_impl: str) -> Dict[str, Any]:
    """
    Benchmark a single query
    
    Args:
        query: Query to test
        workflow_impl: "legacy" or "langgraph"
        
    Returns:
        Performance metrics
    """
    # Set environment variable for workflow selection
    os.environ["QNWIS_WORKFLOW_IMPL"] = workflow_impl
    
    # Import after setting env var
    from qnwis.orchestration.workflow import run_intelligence_query
    
    # Execute and measure
    start_time = time.time()
    
    try:
        result = await run_intelligence_query(query)
        execution_time = time.time() - start_time
        
        return {
            "success": True,
            "execution_time": execution_time,
            "nodes_executed": len(result.get("nodes_executed", [])),
            "facts_extracted": len(result.get("extracted_facts", [])),
            "confidence_score": result.get("confidence_score", 0.0),
            "synthesis_length": len(result.get("final_synthesis", "")),
            "warnings": len(result.get("warnings", [])),
            "errors": len(result.get("errors", [])),
        }
    except Exception as e:
        execution_time = time.time() - start_time
        return {
            "success": False,
            "execution_time": execution_time,
            "error": str(e)
        }

async def run_benchmark():
    """Run complete benchmark suite"""
    
    print("="*80)
    print("WORKFLOW PERFORMANCE BENCHMARK")
    print("Comparing Legacy vs LangGraph implementations")
    print("="*80)
    
    results = {
        "legacy": [],
        "langgraph": []
    }
    
    for test_case in TEST_QUERIES:
        query = test_case["query"]
        category = test_case["category"]
        
        print(f"\n[QUERY] {query}")
        print(f"Category: {category}")
        
        # Benchmark legacy
        print("  Testing legacy workflow...")
        legacy_result = await benchmark_query(query, "legacy")
        results["legacy"].append({
            "query": query,
            "category": category,
            **legacy_result
        })
        print(f"    Time: {legacy_result['execution_time']:.2f}s")
        
        # Benchmark langgraph
        print("  Testing langgraph workflow...")
        langgraph_result = await benchmark_query(query, "langgraph")
        results["langgraph"].append({
            "query": query,
            "category": category,
            **langgraph_result
        })
        print(f"    Time: {langgraph_result['execution_time']:.2f}s")
        
        # Compare
        if legacy_result["success"] and langgraph_result["success"]:
            speedup = legacy_result["execution_time"] / langgraph_result["execution_time"]
            if speedup > 1.0:
                print(f"  [RESULT] LangGraph {speedup:.1f}x faster")
            elif speedup < 1.0:
                print(f"  [RESULT] Legacy {1/speedup:.1f}x faster")
            else:
                print(f"  [RESULT] Same performance")
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    for impl in ["legacy", "langgraph"]:
        impl_results = results[impl]
        successful = [r for r in impl_results if r["success"]]
        
        if successful:
            avg_time = sum(r["execution_time"] for r in successful) / len(successful)
            avg_nodes = sum(r["nodes_executed"] for r in successful) / len(successful)
            avg_facts = sum(r["facts_extracted"] for r in successful) / len(successful)
            avg_confidence = sum(r["confidence_score"] for r in successful) / len(successful)
            
            print(f"\n{impl.upper()}:")
            print(f"  Success rate: {len(successful)}/{len(impl_results)} ({100*len(successful)/len(impl_results):.0f}%)")
            print(f"  Avg execution time: {avg_time:.2f}s")
            print(f"  Avg nodes executed: {avg_nodes:.1f}")
            print(f"  Avg facts extracted: {avg_facts:.0f}")
            print(f"  Avg confidence: {avg_confidence:.2f}")
    
    # Category breakdown
    print("\n" + "="*80)
    print("PERFORMANCE BY CATEGORY")
    print("="*80)
    
    categories = set(tc["category"] for tc in TEST_QUERIES)
    for category in categories:
        print(f"\n{category.upper().replace('_', ' ')}:")
        
        legacy_cat = [r for r in results["legacy"] if r["category"] == category and r["success"]]
        langgraph_cat = [r for r in results["langgraph"] if r["category"] == category and r["success"]]
        
        if legacy_cat and langgraph_cat:
            legacy_avg = sum(r["execution_time"] for r in legacy_cat) / len(legacy_cat)
            langgraph_avg = sum(r["execution_time"] for r in langgraph_cat) / len(langgraph_cat)
            
            print(f"  Legacy avg: {legacy_avg:.2f}s")
            print(f"  LangGraph avg: {langgraph_avg:.2f}s")
            
            if langgraph_avg < legacy_avg:
                speedup = legacy_avg / langgraph_avg
                print(f"  [WIN] LangGraph {speedup:.1f}x faster")
            elif langgraph_avg > legacy_avg:
                slowdown = langgraph_avg / legacy_avg
                print(f"  [LOSS] LangGraph {slowdown:.1f}x slower")
            else:
                print(f"  [TIE] Same performance")
    
    print("\n" + "="*80)
    print("BENCHMARK COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
