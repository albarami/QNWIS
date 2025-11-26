#!/usr/bin/env python3
"""
Detailed Prompt Comparison: Original vs GPT-Optimized.
Tests both Claude and GPT with different prompt styles.
"""

import os
import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)


# Original Anthropic-style system prompt
ANTHROPIC_STYLE_PROMPT = """You are a PhD Economist from IMF/World Bank with 15 years 
experience in Qatar's labor market analysis.

# YOUR ANALYTICAL FRAMEWORK

1. **Aggregate economic impacts**: GDP, employment, balance of payments
2. **Strategic externalities**: National security, food/energy security
3. **Systemic risks**: What happens when systems fail?
4. **Long-term transformation**: Structural change, capability building

# YOUR CRITICAL LENS

Ask constantly: **"What does the data actually show?"**

You FAVOR:
- Evidence-based analysis
- Citing sources for every fact
- Acknowledging uncertainty

# CRITICAL RULES

- EVERY number MUST have citation: [Source: value]
- If data not available, say "NOT IN DATA"
- Never estimate or guess
"""

# GPT-optimized system prompt
GPT_STYLE_PROMPT = """<role>
You are Dr. Ahmed, a senior economist at Qatar's Planning and Statistics Authority with 15 years of experience analyzing labor market data.
</role>

<task>
Analyze the user's question about Qatar's labor market using factual data and provide actionable insights.
</task>

<output_format>
Structure your response as follows:
1. **Key Finding**: One-sentence summary
2. **Current Data**: Latest statistics with sources
3. **Sector Breakdown**: Table or list format
4. **Trend Analysis**: Year-over-year changes
5. **Policy Implications**: 2-3 actionable recommendations
</output_format>

<rules>
- ALWAYS cite sources: [Source: value, year]
- If data unavailable, state "Data not available"
- Use bullet points for clarity
- Include percentages and absolute numbers
- Compare to regional benchmarks (GCC)
</rules>

<available_data>
- Qatar unemployment: 0.1% (MoL LMIS 2024)
- Total workforce: 2.1M workers
- Qatari nationals: ~11% of workforce
- Expatriate workers: ~89% of workforce
- Key sectors: Construction (40%), Services (25%), Energy (15%)
</available_data>
"""


async def test_prompt_style(provider: str, prompt_style: str, system_prompt: str, query: str) -> dict:
    """Test a specific prompt style."""
    from src.qnwis.llm.client import LLMClient
    from src.qnwis.llm.config import get_llm_config
    
    print(f"\n  Testing {provider.upper()} with {prompt_style} prompt...")
    
    try:
        os.environ["QNWIS_LLM_PROVIDER"] = provider
        config = get_llm_config()
        
        client = LLMClient(provider=provider, config=config)
        
        start = time.time()
        response = await client.generate(prompt=query, system=system_prompt, max_tokens=1000)
        elapsed = time.time() - start
        
        # Score quality
        quality = score_response(response)
        
        model = config.get_model(provider)
        print(f"    Model: {model}")
        print(f"    Time: {elapsed:.2f}s")
        print(f"    Words: {len(response.split())}")
        print(f"    Quality: {quality['overall']:.2f}")
        
        return {
            "provider": provider,
            "prompt_style": prompt_style,
            "model": model,
            "time": elapsed,
            "word_count": len(response.split()),
            "quality": quality,
            "response": response,
        }
        
    except Exception as e:
        print(f"    ERROR: {e}")
        return {"provider": provider, "prompt_style": prompt_style, "error": str(e)}


def score_response(response: str) -> dict:
    """Score response quality."""
    if not response:
        return {"structure": 0, "citations": 0, "depth": 0, "overall": 0}
    
    text = response.lower()
    
    # Structure (headers, lists, organization)
    structure = sum([
        "**" in response or "##" in response,  # Headers/bold
        "1." in response or "- " in response,  # Lists
        len(response.split("\n\n")) > 2,  # Paragraphs
        "%" in response,  # Statistics
        "recommendation" in text or "action" in text,  # Actionable
    ]) / 5
    
    # Citations (sources mentioned)
    citations = sum([
        "mol" in text or "lmis" in text,
        "world bank" in text or "imf" in text,
        "psa" in text or "statistics authority" in text,
        "[" in response and "]" in response,  # Citation brackets
        "2024" in response or "2023" in response,  # Year citations
    ]) / 5
    
    # Depth (comprehensive analysis)
    depth = sum([
        len(response.split()) > 200,  # Sufficient length
        "qatarization" in text or "nationalization" in text,
        "sector" in text,
        "expat" in text or "expatriate" in text,
        any(num in response for num in ["0.1%", "0.2%", "0.3%"]),  # Correct unemployment
    ]) / 5
    
    overall = (structure * 0.3 + citations * 0.4 + depth * 0.3)
    
    return {
        "structure": round(structure, 2),
        "citations": round(citations, 2),
        "depth": round(depth, 2),
        "overall": round(overall, 2),
    }


async def main():
    print("=" * 70)
    print("DETAILED PROMPT COMPARISON: ORIGINAL vs GPT-OPTIMIZED")
    print("=" * 70)
    
    # Check providers
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    print("\nProvider Status:")
    print(f"  Azure: {'Available' if azure_key else 'NOT SET'}")
    print(f"  Anthropic: {'Available' if anthropic_key else 'NOT SET'}")
    
    query = """What is Qatar's current unemployment rate and workforce composition? 
Include Qatarization rates and sector breakdown."""
    
    print(f"\nTest Query: {query[:60]}...")
    
    results = []
    
    # Test combinations
    tests = []
    
    if azure_key:
        tests.append(("azure", "original", ANTHROPIC_STYLE_PROMPT))
        tests.append(("azure", "gpt-optimized", GPT_STYLE_PROMPT))
    
    if anthropic_key:
        tests.append(("anthropic", "original", ANTHROPIC_STYLE_PROMPT))
        tests.append(("anthropic", "gpt-optimized", GPT_STYLE_PROMPT))
    
    for provider, style, prompt in tests:
        result = await test_prompt_style(provider, style, prompt, query)
        results.append(result)
    
    # Print comparison
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)
    
    print(f"\n{'Provider':<12} {'Prompt Style':<15} {'Time':<8} {'Words':<8} {'Quality':<8}")
    print("-" * 60)
    
    for r in results:
        if "error" not in r:
            print(f"{r['provider']:<12} {r['prompt_style']:<15} {r['time']:.2f}s{'':<4} {r['word_count']:<8} {r['quality']['overall']:.2f}")
    
    # Show best combination
    valid = [r for r in results if "error" not in r]
    if valid:
        best = max(valid, key=lambda x: x["quality"]["overall"])
        fastest = min(valid, key=lambda x: x["time"])
        
        print("\n" + "-" * 60)
        print(f"BEST QUALITY: {best['provider']} + {best['prompt_style']} (score: {best['quality']['overall']:.2f})")
        print(f"FASTEST: {fastest['provider']} + {fastest['prompt_style']} ({fastest['time']:.2f}s)")
    
    # Show responses
    print("\n" + "=" * 70)
    print("SAMPLE RESPONSES")
    print("=" * 70)
    
    for r in results:
        if "error" not in r:
            print(f"\n--- {r['provider'].upper()} + {r['prompt_style'].upper()} ---")
            print(r["response"][:800])
            if len(r["response"]) > 800:
                print("... [truncated]")
    
    return results


if __name__ == "__main__":
    results = asyncio.run(main())

