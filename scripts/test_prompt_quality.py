#!/usr/bin/env python3
"""
Prompt Quality A/B Testing Framework.

Compares prompt outputs across providers:
1. Anthropic Claude + Claude prompts (baseline)
2. Azure GPT + Claude prompts (compatibility)
3. Azure GPT + GPT-optimized prompts (optimized)

Scores outputs on: depth, accuracy, citations, structure.

Usage:
    python scripts/test_prompt_quality.py
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


# Claude-style prompt (current)
CLAUDE_SYSTEM_PROMPT = """You are an expert policy analyst providing ministerial-grade analysis for Qatar.

Your analysis must be:
- EVIDENCE-BASED: Cite specific data, statistics, and sources
- STRUCTURED: Use clear sections with headers
- ACTIONABLE: Provide concrete, implementable recommendations
- BALANCED: Present multiple perspectives and trade-offs
- DEEP: Go beyond surface-level analysis to root causes

Format your response with:
1. Executive Summary (2-3 key insights)
2. Detailed Analysis (with data points)
3. Risk Assessment
4. Strategic Recommendations (prioritized)
5. Implementation Timeline

Always maintain a professional, objective tone suitable for ministerial briefings."""

# GPT-optimized prompt (shorter, more explicit structure)
GPT_SYSTEM_PROMPT = """You are a senior policy advisor. Provide ministerial-grade analysis.

## OUTPUT REQUIREMENTS
1. **Executive Summary**: 2-3 bullet points with key findings
2. **Analysis**: Evidence-based with specific data/statistics
3. **Risks**: Identify 2-3 key risks with mitigation strategies  
4. **Recommendations**: 3-5 actionable items, prioritized
5. **Timeline**: Implementation phases

## QUALITY STANDARDS
- Use concrete numbers and percentages
- Cite sources when available
- Structure with clear headers
- Keep language professional and direct"""

# Test query
TEST_QUERY = """Analyze Qatar's economic diversification strategy with focus on:
1. Current progress in reducing oil dependency
2. Growth sectors (tourism, finance, technology)
3. Labor market implications
4. Recommendations for accelerating diversification

Provide specific data points and actionable recommendations."""


async def test_with_provider(
    provider: str,
    model: str,
    system_prompt: str,
    prompt_name: str
) -> Dict[str, Any]:
    """
    Test a specific provider/prompt combination.
    
    Args:
        provider: LLM provider name
        model: Model name
        system_prompt: System prompt to use
        prompt_name: Name for this prompt variant
        
    Returns:
        Test results dictionary
    """
    result = {
        "provider": provider,
        "model": model,
        "prompt_name": prompt_name,
        "status": "unknown",
        "latency_ms": 0,
        "response_length": 0,
        "response": "",
        "scores": {},
        "error": None
    }
    
    start_time = time.time()
    
    try:
        if provider == "anthropic":
            from anthropic import AsyncAnthropic
            
            client = AsyncAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                timeout=120
            )
            
            response = await client.messages.create(
                model=model,
                max_tokens=3000,
                system=system_prompt,
                messages=[{"role": "user", "content": TEST_QUERY}],
                temperature=0.3
            )
            
            content = response.content[0].text if response.content else ""
            
        elif provider == "azure":
            from openai import AsyncAzureOpenAI
            
            client = AsyncAzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                timeout=120
            )
            
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": TEST_QUERY}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content or ""
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Score the response
        scores = score_response(content)
        
        result.update({
            "status": "success",
            "latency_ms": round(latency_ms, 2),
            "response_length": len(content),
            "response": content,
            "scores": scores
        })
        
    except Exception as e:
        result.update({
            "status": "error",
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "error": str(e)
        })
    
    return result


def score_response(content: str) -> Dict[str, float]:
    """
    Score response quality across multiple dimensions.
    
    Args:
        content: Response content
        
    Returns:
        Dictionary of scores (0.0-1.0)
    """
    scores = {
        "depth": 0.0,
        "structure": 0.0,
        "citations": 0.0,
        "actionability": 0.0,
        "overall": 0.0
    }
    
    content_lower = content.lower()
    
    # DEPTH SCORE: Check for specific data and analysis depth
    depth_indicators = [
        "%" in content,  # Statistics
        any(year in content for year in ["2020", "2021", "2022", "2023", "2024", "2025"]),
        "billion" in content_lower or "million" in content_lower,
        "gdp" in content_lower,
        any(num in content for num in ["1.", "2.", "3.", "4.", "5."]),  # Numbered analysis
        "according to" in content_lower or "data shows" in content_lower,
        len(content) > 2000,  # Substantial length
        "economic" in content_lower and ("diversification" in content_lower or "growth" in content_lower),
        "sector" in content_lower,
        "qatar" in content_lower
    ]
    scores["depth"] = sum(depth_indicators) / len(depth_indicators)
    
    # STRUCTURE SCORE: Check for organized formatting
    structure_indicators = [
        "##" in content or "**" in content,  # Markdown formatting
        "executive summary" in content_lower or "summary" in content_lower,
        "recommendation" in content_lower,
        "risk" in content_lower,
        "timeline" in content_lower or "implementation" in content_lower,
        "\n-" in content or "\n•" in content,  # Bullet points
        content.count("\n\n") >= 3,  # Multiple paragraphs/sections
        "analysis" in content_lower,
        len(content.split("\n")) > 20,  # Multi-line response
        "conclusion" in content_lower or "next steps" in content_lower
    ]
    scores["structure"] = sum(structure_indicators) / len(structure_indicators)
    
    # CITATIONS SCORE: Check for source references
    citation_indicators = [
        "source" in content_lower,
        "report" in content_lower,
        "study" in content_lower or "research" in content_lower,
        "world bank" in content_lower or "imf" in content_lower,
        "ministry" in content_lower,
        "statistics" in content_lower or "data" in content_lower,
        "survey" in content_lower,
        any(year in content for year in ["2022", "2023", "2024"]),
        "percent" in content_lower or "%" in content,
        "estimate" in content_lower or "projection" in content_lower
    ]
    scores["citations"] = sum(citation_indicators) / len(citation_indicators)
    
    # ACTIONABILITY SCORE: Check for concrete recommendations
    action_indicators = [
        "recommend" in content_lower,
        "should" in content_lower,
        "strategy" in content_lower or "strategic" in content_lower,
        "priority" in content_lower or "prioritize" in content_lower,
        "implement" in content_lower,
        "action" in content_lower,
        "initiative" in content_lower,
        "target" in content_lower or "goal" in content_lower,
        "invest" in content_lower or "investment" in content_lower,
        "develop" in content_lower or "development" in content_lower
    ]
    scores["actionability"] = sum(action_indicators) / len(action_indicators)
    
    # OVERALL SCORE: Weighted average
    scores["overall"] = (
        scores["depth"] * 0.30 +
        scores["structure"] * 0.25 +
        scores["citations"] * 0.20 +
        scores["actionability"] * 0.25
    )
    
    return scores


async def run_ab_test() -> Dict[str, Any]:
    """
    Run full A/B test comparing prompt variants.
    
    Returns:
        Complete test results
    """
    print("=" * 70)
    print("PROMPT QUALITY A/B TESTING")
    print("=" * 70)
    print(f"\nStarted: {datetime.now().isoformat()}")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "test_query": TEST_QUERY[:200] + "...",
        "variants": [],
        "comparison": {},
        "winner": None
    }
    
    # Define test variants
    variants = [
        # Anthropic baseline
        ("anthropic", os.getenv("QNWIS_ANTHROPIC_MODEL", "claude-sonnet-4-20250514"), 
         CLAUDE_SYSTEM_PROMPT, "claude_baseline"),
        # Azure with Claude prompt
        ("azure", os.getenv("QNWIS_AZURE_MODEL", "gpt-4o-mini"), 
         CLAUDE_SYSTEM_PROMPT, "azure_claude_prompt"),
        # Azure with GPT-optimized prompt
        ("azure", os.getenv("QNWIS_AZURE_MODEL", "gpt-4o-mini"), 
         GPT_SYSTEM_PROMPT, "azure_gpt_prompt"),
    ]
    
    print("\n1. TESTING VARIANTS")
    print("-" * 40)
    
    for provider, model, prompt, name in variants:
        print(f"\n  Testing: {name} ({provider}/{model})")
        
        # Check if provider is available
        if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            print(f"    SKIPPED: ANTHROPIC_API_KEY not set")
            continue
        if provider == "azure" and not os.getenv("AZURE_OPENAI_API_KEY"):
            print(f"    SKIPPED: AZURE_OPENAI_API_KEY not set")
            continue
        
        result = await test_with_provider(provider, model, prompt, name)
        results["variants"].append(result)
        
        if result["status"] == "success":
            print(f"    SUCCESS: {result['latency_ms']:.0f}ms, {result['response_length']} chars")
            print(f"    Scores: depth={result['scores']['depth']:.2f}, "
                  f"structure={result['scores']['structure']:.2f}, "
                  f"citations={result['scores']['citations']:.2f}, "
                  f"actionability={result['scores']['actionability']:.2f}")
            print(f"    OVERALL: {result['scores']['overall']:.2f}")
        else:
            print(f"    FAILED: {result['error'][:100] if result['error'] else 'Unknown error'}")
    
    # Compare results
    print("\n2. COMPARISON RESULTS")
    print("-" * 40)
    
    successful = [v for v in results["variants"] if v["status"] == "success"]
    
    if len(successful) >= 2:
        # Sort by overall score
        ranked = sorted(successful, key=lambda x: x["scores"]["overall"], reverse=True)
        results["winner"] = ranked[0]["prompt_name"]
        
        print(f"\n  RANKING:")
        for i, v in enumerate(ranked, 1):
            print(f"    {i}. {v['prompt_name']}: {v['scores']['overall']:.2f}")
        
        print(f"\n  WINNER: {results['winner']}")
        
        # Detailed comparison
        print("\n  DIMENSION COMPARISON:")
        print(f"  {'Variant':<25} {'Depth':<8} {'Struct':<8} {'Cite':<8} {'Action':<8} {'Overall':<8}")
        print("  " + "-" * 65)
        for v in ranked:
            s = v["scores"]
            print(f"  {v['prompt_name']:<25} {s['depth']:.2f}    {s['structure']:.2f}    "
                  f"{s['citations']:.2f}    {s['actionability']:.2f}    {s['overall']:.2f}")
        
        # Calculate improvement from baseline
        baseline = next((v for v in successful if "baseline" in v["prompt_name"]), None)
        if baseline and results["winner"] != baseline["prompt_name"]:
            winner_result = ranked[0]
            improvement = (winner_result["scores"]["overall"] - baseline["scores"]["overall"]) / baseline["scores"]["overall"] * 100
            results["comparison"]["improvement_vs_baseline"] = f"{improvement:.1f}%"
            print(f"\n  Improvement vs baseline: {improvement:.1f}%")
    
    elif len(successful) == 1:
        results["winner"] = successful[0]["prompt_name"]
        print(f"\n  Only one variant succeeded: {results['winner']}")
    else:
        print("\n  No successful variants to compare!")
    
    # Save results
    output_path = Path("data/prompt_ab_test_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove full responses for JSON (keep preview)
    for v in results["variants"]:
        if v.get("response"):
            v["response_preview"] = v["response"][:500] + "..." if len(v["response"]) > 500 else v["response"]
            del v["response"]
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {output_path}")
    
    print("\n" + "=" * 70)
    print("A/B TEST COMPLETE")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    results = asyncio.run(run_ab_test())

