#!/usr/bin/env python3
"""
10-Query Regression Test for Provider Comparison.

Runs all 10 pilot queries through both Azure and Anthropic providers,
comparing results on:
- Facts extracted (count)
- Source diversity (unique sources)
- Confidence score
- Response time (seconds)
- Synthesis quality (word count, structure)

Usage:
    python scripts/regression_test_providers.py
    
Prerequisites:
    - ANTHROPIC_API_KEY set (for baseline)
    - AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT set (for Azure)
    - Backend server running on port 8000
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

import httpx

# Test configuration
BACKEND_URL = "http://localhost:8000"
PILOT_EVIDENCE_DIR = Path("pilot_evidence")
OUTPUT_DIR = Path("data/regression_results")

# Pilot queries (loaded from pilot_evidence folder)
PILOT_QUERIES = [
    ("Economic Diversification", "Analyze Qatar's non-oil GDP growth and sector contribution (2015-2024)"),
    ("Energy/Oil&Gas", "What is Qatar's current oil production capacity and LNG export strategy?"),
    ("Tourism", "Analyze Qatar's tourism sector growth post-2022 World Cup"),
    ("Food Security", "What is Qatar's food self-sufficiency rate and import dependency?"),
    ("Healthcare", "Analyze Qatar's healthcare infrastructure and medical workforce capacity"),
    ("Digital/AI", "What is Qatar's digital transformation progress and AI adoption rate?"),
    ("Manufacturing", "Analyze Qatar's manufacturing sector growth and industrial diversification"),
    ("Workforce/Labor", "What is the current Qatarization rate and workforce nationalization progress?"),
    ("Infrastructure", "Analyze Qatar's infrastructure development for Vision 2030"),
    ("Cross-Domain Strategic", "How do Qatar's labor, energy, and economic policies align with Vision 2030?"),
]


def load_pilot_queries() -> List[Dict[str, Any]]:
    """Load pilot queries from evidence files."""
    queries = []
    
    for i, (domain, default_query) in enumerate(PILOT_QUERIES, 1):
        # Try to load from file
        safe_domain = domain.replace("/", "_").replace("&", "and")
        file_pattern = f"query_{i:02d}_*"
        
        matching_files = list(PILOT_EVIDENCE_DIR.glob(file_pattern + ".json"))
        
        if matching_files:
            with open(matching_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                queries.append({
                    "id": i,
                    "domain": domain,
                    "query": data.get("query", default_query),
                    "baseline_facts": data.get("facts_count", 0),
                    "baseline_confidence": data.get("confidence", 0),
                    "baseline_time": data.get("execution_time", 0)
                })
        else:
            queries.append({
                "id": i,
                "domain": domain,
                "query": default_query,
                "baseline_facts": 0,
                "baseline_confidence": 0,
                "baseline_time": 0
            })
    
    return queries


async def run_query_with_provider(
    query: str,
    provider: str,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Run a single query through the backend with specified provider.
    
    Args:
        query: The query to test
        provider: LLM provider ('anthropic' or 'azure')
        timeout: Request timeout in seconds
        
    Returns:
        Test result dictionary
    """
    result = {
        "provider": provider,
        "query": query[:100] + "...",
        "status": "unknown",
        "facts_count": 0,
        "sources_count": 0,
        "confidence": 0.0,
        "execution_time": 0.0,
        "synthesis_length": 0,
        "synthesis_quality": {},
        "error": None
    }
    
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Use the streaming endpoint
            response = await client.post(
                f"{BACKEND_URL}/api/intelligence/stream",
                json={
                    "query": query,
                    "enable_parallel_scenarios": False,
                    "provider_override": provider  # Note: This may need backend support
                },
                headers={"Accept": "text/event-stream"}
            )
            
            if response.status_code != 200:
                result["status"] = "error"
                result["error"] = f"HTTP {response.status_code}"
                return result
            
            # Parse SSE response
            synthesis_content = ""
            facts_count = 0
            sources = set()
            confidence = 0.0
            
            for line in response.text.split("\n"):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        event_type = data.get("event", "")
                        payload = data.get("payload", {})
                        
                        if event_type == "extraction":
                            facts_count = payload.get("facts_count", 0)
                            for source in payload.get("sources", []):
                                sources.add(source)
                        
                        elif event_type == "synthesize":
                            synthesis_content = payload.get("final_synthesis", "")
                        
                        elif event_type == "done":
                            confidence = payload.get("confidence", 0.0)
                            
                    except json.JSONDecodeError:
                        continue
            
            execution_time = time.time() - start_time
            
            # Score synthesis quality
            synthesis_quality = score_synthesis(synthesis_content)
            
            result.update({
                "status": "success",
                "facts_count": facts_count,
                "sources_count": len(sources),
                "sources": list(sources),
                "confidence": confidence,
                "execution_time": round(execution_time, 2),
                "synthesis_length": len(synthesis_content),
                "synthesis_quality": synthesis_quality
            })
            
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["execution_time"] = round(time.time() - start_time, 2)
    
    return result


def score_synthesis(content: str) -> Dict[str, float]:
    """Score synthesis quality."""
    if not content:
        return {"structure": 0, "depth": 0, "actionability": 0, "overall": 0}
    
    content_lower = content.lower()
    
    # Structure score
    structure_indicators = [
        "##" in content or "**" in content,
        "executive summary" in content_lower or "summary" in content_lower,
        "recommendation" in content_lower,
        "risk" in content_lower,
        len(content.split("\n\n")) > 3
    ]
    structure = sum(structure_indicators) / len(structure_indicators)
    
    # Depth score
    depth_indicators = [
        "%" in content,
        any(year in content for year in ["2023", "2024", "2025"]),
        "billion" in content_lower or "million" in content_lower,
        "qatar" in content_lower,
        len(content) > 2000
    ]
    depth = sum(depth_indicators) / len(depth_indicators)
    
    # Actionability score
    action_indicators = [
        "recommend" in content_lower,
        "should" in content_lower,
        "action" in content_lower or "implement" in content_lower,
        "priority" in content_lower,
        "strategy" in content_lower
    ]
    actionability = sum(action_indicators) / len(action_indicators)
    
    overall = (structure * 0.3 + depth * 0.4 + actionability * 0.3)
    
    return {
        "structure": round(structure, 2),
        "depth": round(depth, 2),
        "actionability": round(actionability, 2),
        "overall": round(overall, 2)
    }


def calculate_aggregate_score(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate aggregate score across all queries."""
    if not results:
        return {"total": 0}
    
    successful = [r for r in results if r["status"] == "success"]
    if not successful:
        return {"total": 0, "success_rate": 0}
    
    avg_facts = sum(r["facts_count"] for r in successful) / len(successful)
    avg_sources = sum(r["sources_count"] for r in successful) / len(successful)
    avg_confidence = sum(r["confidence"] for r in successful) / len(successful)
    avg_time = sum(r["execution_time"] for r in successful) / len(successful)
    avg_quality = sum(r["synthesis_quality"]["overall"] for r in successful) / len(successful)
    
    # Calculate total score (weighted)
    total = (
        min(avg_facts / 100, 1.0) * 20 +  # Facts (max 20 points)
        min(avg_sources / 10, 1.0) * 20 +  # Sources (max 20 points)
        avg_confidence * 20 +               # Confidence (max 20 points)
        avg_quality * 30 +                  # Quality (max 30 points)
        (1 - min(avg_time / 120, 1.0)) * 10  # Speed bonus (max 10 points)
    )
    
    return {
        "total": round(total, 2),
        "success_rate": len(successful) / len(results),
        "avg_facts": round(avg_facts, 1),
        "avg_sources": round(avg_sources, 1),
        "avg_confidence": round(avg_confidence, 3),
        "avg_time": round(avg_time, 1),
        "avg_quality": round(avg_quality, 3)
    }


async def run_regression_test() -> Dict[str, Any]:
    """Run full regression test comparing providers."""
    print("=" * 70)
    print("10-QUERY REGRESSION TEST: AZURE vs ANTHROPIC")
    print("=" * 70)
    print(f"\nStarted: {datetime.now().isoformat()}")
    
    # Load pilot queries
    queries = load_pilot_queries()
    print(f"\nLoaded {len(queries)} pilot queries")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "queries_tested": len(queries),
        "azure_results": [],
        "anthropic_results": [],
        "comparison": {},
        "winner": None
    }
    
    # Check which providers are available
    azure_available = bool(os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"))
    anthropic_available = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    print(f"\nProvider availability:")
    print(f"  Azure OpenAI: {'YES' if azure_available else 'NO'}")
    print(f"  Anthropic: {'YES' if anthropic_available else 'NO'}")
    
    if not azure_available and not anthropic_available:
        print("\nERROR: No providers available. Set API keys.")
        return results
    
    # Test Azure
    if azure_available:
        print("\n" + "-" * 70)
        print("TESTING: AZURE OPENAI")
        print("-" * 70)
        
        for q in queries:
            print(f"\n  [{q['id']}/10] {q['domain']}")
            result = await run_query_with_provider(q["query"], "azure")
            result["domain"] = q["domain"]
            results["azure_results"].append(result)
            
            if result["status"] == "success":
                print(f"    SUCCESS: {result['facts_count']} facts, {result['sources_count']} sources, "
                      f"{result['execution_time']}s, quality={result['synthesis_quality']['overall']:.2f}")
            else:
                print(f"    FAILED: {result['error']}")
    
    # Test Anthropic
    if anthropic_available:
        print("\n" + "-" * 70)
        print("TESTING: ANTHROPIC")
        print("-" * 70)
        
        for q in queries:
            print(f"\n  [{q['id']}/10] {q['domain']}")
            result = await run_query_with_provider(q["query"], "anthropic")
            result["domain"] = q["domain"]
            results["anthropic_results"].append(result)
            
            if result["status"] == "success":
                print(f"    SUCCESS: {result['facts_count']} facts, {result['sources_count']} sources, "
                      f"{result['execution_time']}s, quality={result['synthesis_quality']['overall']:.2f}")
            else:
                print(f"    FAILED: {result['error']}")
    
    # Calculate aggregate scores
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    azure_score = calculate_aggregate_score(results["azure_results"]) if results["azure_results"] else None
    anthropic_score = calculate_aggregate_score(results["anthropic_results"]) if results["anthropic_results"] else None
    
    results["comparison"] = {
        "azure": azure_score,
        "anthropic": anthropic_score
    }
    
    print("\n  AGGREGATE SCORES:")
    print(f"  {'Metric':<20} {'Azure':<15} {'Anthropic':<15}")
    print("  " + "-" * 50)
    
    if azure_score and anthropic_score:
        for metric in ["total", "success_rate", "avg_facts", "avg_sources", "avg_confidence", "avg_time", "avg_quality"]:
            az_val = azure_score.get(metric, 0)
            an_val = anthropic_score.get(metric, 0)
            print(f"  {metric:<20} {az_val:<15} {an_val:<15}")
        
        # Determine winner
        if azure_score["total"] >= anthropic_score["total"]:
            results["winner"] = "azure"
            print(f"\n  WINNER: AZURE (score: {azure_score['total']:.1f} >= {anthropic_score['total']:.1f})")
            print("  VERDICT: Azure OpenAI PASSES regression test")
        else:
            results["winner"] = "anthropic"
            print(f"\n  WINNER: ANTHROPIC (score: {anthropic_score['total']:.1f} > {azure_score['total']:.1f})")
            print("  VERDICT: Azure OpenAI needs improvement before switching")
    elif azure_score:
        results["winner"] = "azure"
        print(f"\n  Azure total: {azure_score['total']:.1f}")
        print("  (Anthropic not tested)")
    elif anthropic_score:
        results["winner"] = "anthropic"
        print(f"\n  Anthropic total: {anthropic_score['total']:.1f}")
        print("  (Azure not tested)")
    
    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"regression_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n  Results saved to: {output_file}")
    print("\n" + "=" * 70)
    print("REGRESSION TEST COMPLETE")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    results = asyncio.run(run_regression_test())
    
    # Exit with appropriate code
    if results.get("winner") == "azure":
        sys.exit(0)  # Azure passes
    else:
        sys.exit(1)  # Azure needs improvement

