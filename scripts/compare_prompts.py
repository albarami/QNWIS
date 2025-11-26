#!/usr/bin/env python3
"""
Quick Prompt Output Comparison: Azure vs Anthropic.
"""

import os
import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)


async def test_provider(provider: str, query: str) -> dict:
    """Test a single provider."""
    from src.qnwis.llm.client import LLMClient
    from src.qnwis.llm.config import get_llm_config
    
    print(f"\nTesting {provider.upper()}...")
    
    try:
        # Set provider
        os.environ["QNWIS_LLM_PROVIDER"] = provider
        config = get_llm_config()
        
        client = LLMClient(provider=provider, config=config)
        
        system = """You are a Qatar labor market expert. Provide factual, data-driven answers.
Include specific statistics and cite sources when possible."""
        
        start = time.time()
        
        response = await client.generate(prompt=query, system=system, max_tokens=800)
        
        elapsed = time.time() - start
        
        model = config.get_model(provider)
        print(f"  Model: {model}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Response length: {len(response)} chars")
        print(f"  Word count: {len(response.split())} words")
        
        return {
            "provider": provider,
            "model": model,
            "time": elapsed,
            "length": len(response),
            "word_count": len(response.split()),
            "response": response,
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {"provider": provider, "error": str(e)}


async def main():
    print("=" * 70)
    print("PROMPT OUTPUT COMPARISON: AZURE vs ANTHROPIC")
    print("=" * 70)
    
    # Check providers
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    print("\nProvider Status:")
    print(f"  Azure: {'Available' if azure_key else 'NOT SET'}")
    print(f"  Anthropic: {'Available' if anthropic_key else 'NOT SET'}")
    
    # Test query
    test_query = """What is Qatar's current unemployment rate and workforce composition? 
    Include Qatarization rates and expat workforce breakdown by sector."""
    
    print(f"\nTest Query: {test_query[:80]}...")
    
    results = []
    
    # Test Azure
    if azure_key:
        result = await test_provider("azure", test_query)
        results.append(result)
    
    # Test Anthropic  
    if anthropic_key:
        result = await test_provider("anthropic", test_query)
        results.append(result)
    
    # Show responses
    print("\n" + "=" * 70)
    print("RESPONSES:")
    print("=" * 70)
    
    for r in results:
        if "error" not in r:
            print(f"\n--- {r['provider'].upper()} ({r['model']}) ---")
            print(r["response"][:1500])
            if len(r["response"]) > 1500:
                print("... [truncated]")
    
    # Compare
    if len(results) == 2 and "error" not in results[0] and "error" not in results[1]:
        print("\n" + "=" * 70)
        print("COMPARISON SUMMARY:")
        print("=" * 70)
        
        az = results[0]
        an = results[1]
        
        print(f"\n{'Metric':<20} {'Azure':<20} {'Anthropic':<20}")
        print("-" * 60)
        print(f"{'Model':<20} {az['model']:<20} {an['model']:<20}")
        print(f"{'Response Time':<20} {az['time']:.2f}s{'':<14} {an['time']:.2f}s")
        print(f"{'Char Length':<20} {az['length']:<20} {an['length']:<20}")
        print(f"{'Word Count':<20} {az['word_count']:<20} {an['word_count']:<20}")
        
        print("\n" + "-" * 60)
        print("VERDICT:")
        
        # Speed
        if az["time"] < an["time"]:
            print(f"  Speed: Azure is {(an['time']/az['time']-1)*100:.0f}% FASTER")
        else:
            print(f"  Speed: Anthropic is {(az['time']/an['time']-1)*100:.0f}% FASTER")
        
        # Depth (word count as proxy)
        if az["word_count"] > an["word_count"]:
            print(f"  Depth: Azure response is {(az['word_count']/an['word_count']-1)*100:.0f}% LONGER")
        else:
            print(f"  Depth: Anthropic response is {(an['word_count']/az['word_count']-1)*100:.0f}% LONGER")
        
        print("\n" + "=" * 70)
    
    return results


if __name__ == "__main__":
    results = asyncio.run(main())

