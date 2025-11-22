"""
Week 3 Pilot Test Execution
10 queries across 10 domains with rigorous evidence collection
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

# Set to LangGraph
import os
os.environ["QNWIS_WORKFLOW_IMPL"] = "langgraph"

from qnwis.orchestration.workflow import run_intelligence_query

PILOT_QUERIES = [
    {
        "id": 1,
        "domain": "Economic Diversification",
        "query": "Analyze Qatar's non-oil GDP growth and sector contribution (2015-2024)",
        "expected_facts": 80,
        "expected_sources": ["World Bank", "IMF", "GCC-STAT"],
    },
    {
        "id": 2,
        "domain": "Energy/Oil&Gas",
        "query": "Should Qatar invest QAR 30B in renewable energy by 2030?",
        "expected_facts": 100,
        "expected_sources": ["IEA", "World Bank", "Semantic Scholar"],
    },
    {
        "id": 3,
        "domain": "Tourism",
        "query": "Compare Qatar's tourism performance to Dubai and Abu Dhabi",
        "expected_facts": 60,
        "expected_sources": ["UNWTO", "GCC-STAT"],
    },
    {
        "id": 4,
        "domain": "Food Security",
        "query": "Assess Qatar's food self-sufficiency levels by major categories",
        "expected_facts": 80,
        "expected_sources": ["FAO", "UN Comtrade"],
    },
    {
        "id": 5,
        "domain": "Healthcare",
        "query": "Analyze Qatar's healthcare infrastructure capacity and gaps",
        "expected_facts": 70,
        "expected_sources": ["World Bank", "Semantic Scholar"],
    },
    {
        "id": 6,
        "domain": "Digital/AI",
        "query": "Should Qatar invest QAR 20B in AI and tech sector by 2030?",
        "expected_facts": 90,
        "expected_sources": ["World Bank", "Semantic Scholar"],
    },
    {
        "id": 7,
        "domain": "Manufacturing",
        "query": "Compare Qatar's industrial competitiveness to GCC countries",
        "expected_facts": 70,
        "expected_sources": ["GCC-STAT", "UNCTAD", "World Bank"],
    },
    {
        "id": 8,
        "domain": "Workforce/Labor",
        "query": "Evaluate feasibility of 60% Qatarization in private sector by 2030",
        "expected_facts": 80,
        "expected_sources": ["ILO", "MoL LMIS"],
    },
    {
        "id": 9,
        "domain": "Infrastructure",
        "query": "Should Qatar invest QAR 15B in metro expansion to northern cities?",
        "expected_facts": 60,
        "expected_sources": ["World Bank"],
    },
    {
        "id": 10,
        "domain": "Cross-Domain Strategic",
        "query": "Recommend top 3 sectors for QAR 50B strategic investment fund",
        "expected_facts": 120,
        "expected_sources": ["World Bank", "IMF", "IEA", "UNWTO", "Semantic Scholar"],
    },
]

async def run_pilot():
    """Execute pilot test with evidence collection"""
    
    print("="*80)
    print("WEEK 3 PILOT TEST - MINISTERIAL INTELLIGENCE VALIDATION")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print(f"\nExecuting 10 queries across 10 domains...")
    print("Evidence collection: ACTIVE")
    print("Quality gates: ENFORCED")
    print("="*80)
    
    results = []
    evidence_dir = Path("pilot_evidence")
    evidence_dir.mkdir(exist_ok=True)
    
    for i, test_case in enumerate(PILOT_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"QUERY {i}/10: {test_case['domain']}")
        print(f"{'='*80}")
        print(f"Q: {test_case['query']}")
        
        start_time = time.time()
        
        try:
            # Execute query
            result = await run_intelligence_query(test_case['query'])
            execution_time = time.time() - start_time
            
            # Extract metrics
            facts_count = len(result.get("extracted_facts", []))
            sources = result.get("data_sources", [])
            confidence = result.get("confidence_score", 0.0)
            nodes = result.get("nodes_executed", [])
            warnings = result.get("warnings", [])
            errors = result.get("errors", [])
            
            # Quality assessment
            meets_facts = facts_count >= test_case["expected_facts"]
            meets_confidence = confidence >= 0.5
            execution_ok = execution_time < 60
            
            # Display results
            print(f"\nRESULTS:")
            print(f"  Facts extracted: {facts_count} (expected: >={test_case['expected_facts']}) {'PASS' if meets_facts else 'FAIL'}")
            print(f"  Data sources: {len(sources)} ({', '.join(sources)})")
            print(f"  Confidence: {confidence:.2f} (target: >=0.5) {'PASS' if meets_confidence else 'FAIL'}")
            print(f"  Execution time: {execution_time:.1f}s (target: <60s) {'PASS' if execution_ok else 'FAIL'}")
            print(f"  Nodes executed: {len(nodes)}")
            print(f"  Warnings: {len(warnings)}")
            print(f"  Errors: {len(errors)}")
            
            # Quality gate
            passed = meets_facts and meets_confidence and execution_ok
            print(f"\n  QUALITY GATE: {'PASS' if passed else 'FAIL'}")
            
            # Save evidence
            evidence_file = evidence_dir / f"query_{i:02d}_{test_case['domain'].replace('/', '_')}.json"
            with open(evidence_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "query": test_case['query'],
                    "domain": test_case['domain'],
                    "execution_time": execution_time,
                    "facts_count": facts_count,
                    "sources": sources,
                    "confidence": confidence,
                    "nodes": nodes,
                    "warnings": warnings,
                    "errors": errors,
                    "synthesis": result.get("final_synthesis", "")[:500],  # First 500 chars
                    "passed": passed
                }, f, indent=2)
            
            results.append({
                "id": i,
                "domain": test_case['domain'],
                "facts": facts_count,
                "confidence": confidence,
                "time": execution_time,
                "passed": passed,
                "sources": len(sources)
            })
            
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            results.append({
                "id": i,
                "domain": test_case['domain'],
                "error": str(e),
                "passed": False
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("PILOT TEST SUMMARY")
    print(f"{'='*80}")
    
    successful = [r for r in results if r.get("passed", False)]
    avg_facts = sum(r.get("facts", 0) for r in successful) / len(successful) if successful else 0
    avg_confidence = sum(r.get("confidence", 0) for r in successful) / len(successful) if successful else 0
    avg_time = sum(r.get("time", 0) for r in successful) / len(successful) if successful else 0
    
    print(f"\nQueries executed: {len(successful)}/10")
    print(f"Average facts: {avg_facts:.0f} (target: >=80)")
    print(f"Average confidence: {avg_confidence:.2f} (target: >=0.5)")
    print(f"Average time: {avg_time:.1f}s (target: <60s)")
    
    # Quality gates
    all_passed = len(successful) == 10
    facts_ok = avg_facts >= 80
    confidence_ok = avg_confidence >= 0.5
    
    print(f"\n{'='*80}")
    print("QUALITY GATES")
    print(f"{'='*80}")
    print(f"All queries successful: {'PASS' if all_passed else 'FAIL'}")
    print(f"Average facts >=80: {'PASS' if facts_ok else 'FAIL'}")
    print(f"Average confidence >=0.5: {'PASS' if confidence_ok else 'FAIL'}")
    
    # Decision
    go_decision = all_passed and facts_ok and confidence_ok
    
    print(f"\n{'='*80}")
    if go_decision:
        print("GO DECISION: Proceed to full 50-query suite")
        print("Pilot validates domain-agnostic capability")
    else:
        print("NO-GO DECISION: Fix issues before full suite")
        print("Review evidence in pilot_evidence/ directory")
    print(f"{'='*80}")
    
    # Save summary
    summary_file = evidence_dir / "PILOT_SUMMARY.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "total_queries": 10,
            "successful": len(successful),
            "avg_facts": avg_facts,
            "avg_confidence": avg_confidence,
            "avg_time": avg_time,
            "decision": "GO" if go_decision else "NO-GO",
            "results": results
        }, f, indent=2)
    
    print(f"\nEvidence saved to: {evidence_dir}/")
    print(f"Summary: {summary_file}")

if __name__ == "__main__":
    asyncio.run(run_pilot())
