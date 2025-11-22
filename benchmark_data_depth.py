"""
Data Depth & Coverage Benchmark
Measures comprehensiveness of data collection, NOT speed
"""
import asyncio
import os
from collections import Counter

# Set to LangGraph
os.environ["QNWIS_WORKFLOW_IMPL"] = "langgraph"

from qnwis.orchestration.workflow import run_intelligence_query

DEPTH_TEST_QUERIES = [
    {
        "query": "Analyze Qatar's economic diversification progress with sector GDP breakdown",
        "category": "Economic Diversification",
        "expected_sources": ["World Bank", "IMF", "GCC-STAT"]
    },
    {
        "query": "Should Qatar invest QAR 15B in green hydrogen infrastructure by 2030?",
        "category": "Strategic Investment",
        "expected_sources": ["IEA", "World Bank", "Semantic Scholar", "Perplexity"]
    },
    {
        "query": "Assess Qatar's food security situation and self-sufficiency levels",
        "category": "Food Security",
        "expected_sources": ["FAO", "UN Comtrade", "World Bank"]
    },
    {
        "query": "Compare Qatar's labor market to other GCC countries",
        "category": "Regional Comparison",
        "expected_sources": ["ILO", "GCC-STAT", "World Bank"]
    },
]

async def benchmark_depth():
    """Measure data depth and coverage"""
    
    print("="*80)
    print("LANGGRAPH DATA DEPTH & COVERAGE BENCHMARK")
    print("Mission: Validate comprehensive data collection")
    print("="*80)
    
    all_results = []
    
    for test_case in DEPTH_TEST_QUERIES:
        query = test_case["query"]
        category = test_case["category"]
        expected = test_case["expected_sources"]
        
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category}")
        print(f"{'='*80}")
        print(f"Query: {query}")
        print(f"Expected sources: {', '.join(expected)}")
        
        # Execute query
        result = await run_intelligence_query(query)
        
        # Analyze depth
        facts_count = len(result.get("extracted_facts", []))
        sources = result.get("data_sources", [])
        confidence = result.get("confidence_score", 0.0)
        synthesis_length = len(str(result.get("final_synthesis", "")))
        
        # Check coverage
        sources_found = [s for s in expected if any(s.lower() in src.lower() for src in sources)]
        coverage = len(sources_found) / len(expected) * 100 if expected else 0
        
        print(f"\n📊 RESULTS:")
        print(f"  Facts extracted: {facts_count}")
        print(f"  Data sources: {len(sources)} ({', '.join(sources)})")
        print(f"  Expected source coverage: {coverage:.0f}% ({len(sources_found)}/{len(expected)})")
        print(f"  Confidence score: {confidence:.2f}")
        print(f"  Synthesis length: {synthesis_length} chars")
        
        # Assessment
        if facts_count >= 50 and coverage >= 66:
            assessment = "[EXCELLENT] Comprehensive data collection"
        elif facts_count >= 20 and coverage >= 50:
            assessment = "[GOOD] Adequate data collection"
        else:
            assessment = "[NEEDS IMPROVEMENT] Insufficient data"
        
        print(f"  Assessment: {assessment}")
        
        all_results.append({
            "category": category,
            "facts": facts_count,
            "sources": len(sources),
            "coverage": coverage,
            "confidence": confidence,
            "assessment": assessment
        })
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY: DATA DEPTH & COVERAGE")
    print(f"{'='*80}")
    
    avg_facts = sum(r["facts"] for r in all_results) / len(all_results)
    avg_sources = sum(r["sources"] for r in all_results) / len(all_results)
    avg_coverage = sum(r["coverage"] for r in all_results) / len(all_results)
    avg_confidence = sum(r["confidence"] for r in all_results) / len(all_results)
    
    print(f"\nAverages across {len(all_results)} queries:")
    print(f"  Facts per query: {avg_facts:.0f}")
    print(f"  Sources per query: {avg_sources:.1f}")
    print(f"  Expected source coverage: {avg_coverage:.0f}%")
    print(f"  Confidence score: {avg_confidence:.2f}")
    
    # Final verdict
    print(f"\n{'='*80}")
    if avg_facts >= 50 and avg_coverage >= 70:
        print("VERDICT: ✅ EXCELLENT - Ministerial-grade data depth achieved")
        print("Recommendation: APPROVED for production deployment")
    elif avg_facts >= 30 and avg_coverage >= 50:
        print("VERDICT: ✅ GOOD - Adequate data depth for most queries")
        print("Recommendation: APPROVED with minor optimizations")
    else:
        print("VERDICT: ⚠️ NEEDS IMPROVEMENT - Insufficient data depth")
        print("Recommendation: Investigate missing data sources")
    print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(benchmark_depth())
