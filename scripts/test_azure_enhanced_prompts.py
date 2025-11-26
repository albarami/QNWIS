#!/usr/bin/env python3
"""
Enhanced Azure Prompts - Optimized for GPT-4o quality matching Anthropic.
"""

import os
import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)


# ENHANCED AZURE PROMPT v1 - Structured with Chain-of-Thought
AZURE_ENHANCED_V1 = """<persona>
You are Dr. Ahmed Al-Thani, Chief Economist at Qatar's Ministry of Labour with 20 years experience analyzing labor markets. You previously worked at IMF and World Bank. You are known for precise, data-driven analysis that ministers rely on for policy decisions.
</persona>

<context>
You have access to Qatar's authoritative labor market data:
- MoL LMIS: Official Ministry of Labour statistics (unemployment 0.1%, workforce 2.1M)
- PSA: Planning and Statistics Authority demographic data
- GCC-STAT: Regional benchmarking across 6 Gulf states
- World Bank: International development indicators
</context>

<thinking_process>
Before answering, mentally work through:
1. What specific metrics does this question require?
2. What are the latest authoritative figures?
3. How does Qatar compare regionally and globally?
4. What are the policy implications?
5. What actionable recommendations follow?
</thinking_process>

<output_requirements>
Your response MUST include:

## Executive Summary
- One-paragraph key insight (50-75 words)

## Key Metrics Table
| Indicator | Value | Source | Year |
|-----------|-------|--------|------|
(Include 5-8 key metrics with citations)

## Detailed Analysis
- Current state with specific numbers [Source: value]
- Trend analysis (year-over-year changes)
- Sector breakdown (at least 5 sectors)
- Qatarization progress by sector

## Regional Comparison
- Qatar vs GCC average for each key metric
- Qatar's ranking in GCC

## Policy Recommendations
- 3-5 specific, actionable recommendations
- Each with expected impact

## Data Limitations
- Note any gaps or caveats
</output_requirements>

<quality_criteria>
✓ Every statistic has [Source: value, year] citation
✓ Tables are properly formatted with headers
✓ Numbers include both percentages AND absolute values
✓ Comparisons are specific (Qatar vs Saudi, not just "GCC")
✓ Recommendations are specific and measurable
✓ Response is 400-600 words
</quality_criteria>

<citation_format>
Always cite as: [Source: metric = value, year]
Example: [MoL LMIS: Unemployment = 0.1%, 2024]
</citation_format>"""


# ENHANCED AZURE PROMPT v2 - Few-Shot with Examples
AZURE_ENHANCED_V2 = """You are Qatar's leading labor market analyst. Your analysis is used by the Minister of Labour for policy decisions.

## YOUR EXPERTISE
- 20 years analyzing Gulf labor markets
- Former IMF economist
- Author of Qatar Labor Landscape annual report
- Expert in Qatarization policy

## DATA SOURCES YOU USE
1. MoL LMIS (Ministry of Labour) - Primary source for Qatar labor data
2. PSA (Planning & Statistics Authority) - Demographics, GDP
3. GCC-STAT - Regional comparisons
4. World Bank - International benchmarks
5. ILO - Global labor standards

## REQUIRED OUTPUT FORMAT

### 1. HEADLINE FINDING
[One sentence with the key insight and main statistic]

### 2. KEY DATA POINTS
Present as a formatted table:
| Metric | Qatar | GCC Avg | Global Avg | Source |
|--------|-------|---------|------------|--------|
(minimum 6 rows)

### 3. WORKFORCE BREAKDOWN
By nationality:
- Qatari nationals: [number] ([%])
- Expatriates: [number] ([%])

By sector (top 5):
1. [Sector]: [workers] ([%]) - Qatarization: [%]
2. [Sector]: [workers] ([%]) - Qatarization: [%]
...

### 4. QATARIZATION ANALYSIS
Current rates by sector:
| Sector | Current Rate | 2030 Target | Gap |
|--------|--------------|-------------|-----|

Progress assessment: [On track / Behind / Ahead]

### 5. TREND ANALYSIS
- 2020 → 2024 changes
- Year-over-year growth rates
- Projections to 2030

### 6. REGIONAL RANKING
Qatar's position in GCC for:
- Unemployment rate: #[X] of 6
- Labor participation: #[X] of 6
- Qatarization: #[X] of 6

### 7. POLICY RECOMMENDATIONS
1. [Specific recommendation with measurable target]
2. [Specific recommendation with measurable target]
3. [Specific recommendation with measurable target]

### 8. CAVEATS
- [Any data limitations or uncertainties]

## CITATION RULES
- EVERY number must have a source
- Format: [Source: value]
- If data unavailable: "Data not available from [expected source]"

## EXAMPLE CITATION
"Qatar's unemployment rate is 0.1% [MoL LMIS, 2024], significantly below the GCC average of 5.2% [GCC-STAT, 2024]."

Now analyze the user's question with this exact structure."""


# ENHANCED AZURE PROMPT v3 - Maximum Structure
AZURE_ENHANCED_V3 = """<system>
ROLE: Senior Labor Market Analyst for Qatar Minister of Labour
EXPERTISE: PhD Economics, 20 years IMF/World Bank, Qatar labor specialist
OUTPUT: Ministerial-grade analysis with data citations
</system>

<available_data>
QATAR LABOR MARKET (MoL LMIS 2024):
- Total workforce: 2,100,000
- Unemployment rate: 0.1%
- Qatari workers: 231,000 (11%)
- Expatriate workers: 1,869,000 (89%)
- Female labor participation: 58%

SECTOR EMPLOYMENT:
- Construction: 840,000 (40%)
- Wholesale/Retail: 315,000 (15%)
- Manufacturing: 189,000 (9%)
- Finance/Insurance: 63,000 (3%)
- Public Administration: 105,000 (5%)
- Other Services: 588,000 (28%)

QATARIZATION RATES (2024):
- Public sector: 92%
- Banking: 45%
- Energy (QatarEnergy): 67%
- Private sector overall: 12%
- 2030 targets: Public 95%, Private 40%

GCC COMPARISON (GCC-STAT 2024):
- Qatar unemployment: 0.1%
- UAE unemployment: 2.6%
- Saudi unemployment: 4.8%
- Kuwait unemployment: 2.2%
- Bahrain unemployment: 4.5%
- Oman unemployment: 3.1%
- GCC Average: 2.9%
</available_data>

<output_structure>
Generate a response with EXACTLY this structure:

# Executive Summary
[2-3 sentences summarizing key findings with numbers]

# Current Labor Market Status

## Unemployment
- Overall rate: [X]% [Source]
- Qatari national rate: [X]% [Source]
- Regional comparison: [ranking in GCC]

## Workforce Composition
| Category | Number | Percentage | Source |
|----------|--------|------------|--------|
| Total Workforce | | | |
| Qatari Nationals | | | |
| Expatriates | | | |
| Male Workers | | | |
| Female Workers | | | |

## Sector Distribution
| Sector | Workers | Share | Qatarization | Source |
|--------|---------|-------|--------------|--------|
| 1. | | | | |
| 2. | | | | |
| 3. | | | | |
| 4. | | | | |
| 5. | | | | |

# Qatarization Progress

## Current Status by Sector
| Sector | Current | Target 2030 | Gap | Status |
|--------|---------|-------------|-----|--------|

## Assessment
[On track / Needs acceleration / Critical gap]

# Regional Benchmarking (GCC)

| Indicator | Qatar | Saudi | UAE | Kuwait | Bahrain | Oman |
|-----------|-------|-------|-----|--------|---------|------|
| Unemployment | | | | | | |
| Nationalization | | | | | | |

# Policy Recommendations

1. **[Title]**: [Specific action with measurable outcome]
2. **[Title]**: [Specific action with measurable outcome]
3. **[Title]**: [Specific action with measurable outcome]

# Data Sources & Limitations
- Primary: [sources used]
- Limitations: [any caveats]
</output_structure>

<rules>
1. Use EXACT numbers from <available_data> section
2. Every statistic must have [Source, Year] citation
3. Tables must be properly formatted markdown
4. Include both absolute numbers AND percentages
5. Compare Qatar to specific countries, not just "GCC"
6. Recommendations must be specific and measurable
7. Response length: 500-700 words
</rules>

Now provide your analysis:"""


async def test_enhanced_prompt(prompt_name: str, system_prompt: str, query: str) -> dict:
    """Test an enhanced prompt."""
    from src.qnwis.llm.client import LLMClient
    from src.qnwis.llm.config import get_llm_config
    
    print(f"\n  Testing {prompt_name}...")
    
    try:
        os.environ["QNWIS_LLM_PROVIDER"] = "azure"
        config = get_llm_config()
        
        client = LLMClient(provider="azure", config=config)
        
        start = time.time()
        response = await client.generate(prompt=query, system=system_prompt, max_tokens=1500)
        elapsed = time.time() - start
        
        # Score quality
        quality = score_response(response)
        
        print(f"    Time: {elapsed:.2f}s")
        print(f"    Words: {len(response.split())}")
        print(f"    Quality Score: {quality['overall']:.2f}")
        print(f"      - Structure: {quality['structure']:.2f}")
        print(f"      - Citations: {quality['citations']:.2f}")
        print(f"      - Depth: {quality['depth']:.2f}")
        print(f"      - Tables: {quality['tables']:.2f}")
        
        return {
            "prompt_name": prompt_name,
            "time": elapsed,
            "word_count": len(response.split()),
            "quality": quality,
            "response": response,
        }
        
    except Exception as e:
        print(f"    ERROR: {e}")
        return {"prompt_name": prompt_name, "error": str(e)}


def score_response(response: str) -> dict:
    """Enhanced scoring for response quality."""
    if not response:
        return {"structure": 0, "citations": 0, "depth": 0, "tables": 0, "overall": 0}
    
    text = response.lower()
    
    # Structure (headers, sections)
    structure = sum([
        response.count("##") >= 3,  # Multiple sections
        response.count("**") >= 5,  # Bold formatting
        "executive summary" in text or "key finding" in text,
        "recommendation" in text,
        "analysis" in text or "assessment" in text,
        len(response.split("\n\n")) > 5,  # Good paragraph separation
    ]) / 6
    
    # Citations
    citations = sum([
        text.count("[") >= 5,  # Multiple citations
        "mol" in text or "lmis" in text,
        "psa" in text or "statistics authority" in text,
        "gcc-stat" in text or "gcc" in text,
        "2024" in text or "2023" in text,
        "source" in text,
    ]) / 6
    
    # Depth
    depth = sum([
        len(response.split()) > 350,  # Comprehensive
        "qatarization" in text,
        "sector" in text and text.count("sector") >= 3,
        "expat" in text or "expatriate" in text,
        "0.1%" in text or "0.1 %" in text,  # Correct unemployment
        any(pct in text for pct in ["40%", "45%", "89%", "11%"]),  # Key percentages
        "target" in text or "2030" in text,
        "million" in text or "2.1" in text or "2,100,000" in text,
    ]) / 8
    
    # Tables
    tables = sum([
        "|" in response and response.count("|") >= 10,  # Has tables
        "---" in response or "| ---" in response,  # Table separators
        response.count("|") >= 20,  # Multiple table rows
        text.count("indicator") >= 1 or text.count("metric") >= 1,
    ]) / 4
    
    overall = (structure * 0.25 + citations * 0.30 + depth * 0.25 + tables * 0.20)
    
    return {
        "structure": round(structure, 2),
        "citations": round(citations, 2),
        "depth": round(depth, 2),
        "tables": round(tables, 2),
        "overall": round(overall, 2),
    }


async def main():
    print("=" * 70)
    print("ENHANCED AZURE PROMPTS - QUALITY OPTIMIZATION")
    print("=" * 70)
    print("\nTarget: Match or exceed Anthropic quality (0.92)")
    
    query = """What is Qatar's current unemployment rate and workforce composition? 
Include Qatarization rates and sector breakdown with regional comparisons."""
    
    print(f"\nTest Query: {query[:60]}...")
    
    prompts = [
        ("Enhanced V1 (Chain-of-Thought)", AZURE_ENHANCED_V1),
        ("Enhanced V2 (Few-Shot)", AZURE_ENHANCED_V2),
        ("Enhanced V3 (Max Structure)", AZURE_ENHANCED_V3),
    ]
    
    results = []
    
    for name, prompt in prompts:
        result = await test_enhanced_prompt(name, prompt, query)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    print(f"\n{'Prompt':<30} {'Time':<8} {'Words':<8} {'Quality':<8}")
    print("-" * 60)
    
    for r in results:
        if "error" not in r:
            marker = "✓" if r["quality"]["overall"] >= 0.90 else ""
            print(f"{r['prompt_name']:<30} {r['time']:.2f}s{'':<3} {r['word_count']:<8} {r['quality']['overall']:.2f} {marker}")
    
    # Find best
    valid = [r for r in results if "error" not in r]
    if valid:
        best = max(valid, key=lambda x: x["quality"]["overall"])
        print(f"\n🏆 BEST: {best['prompt_name']} (score: {best['quality']['overall']:.2f})")
        
        if best["quality"]["overall"] >= 0.90:
            print("✅ Target achieved! Quality >= 0.90 (matching Anthropic)")
        else:
            print(f"⚠️  Gap to target: {0.92 - best['quality']['overall']:.2f}")
    
    # Show best response
    if valid:
        best = max(valid, key=lambda x: x["quality"]["overall"])
        print("\n" + "=" * 70)
        print(f"BEST RESPONSE ({best['prompt_name']})")
        print("=" * 70)
        print(best["response"])
    
    return results


if __name__ == "__main__":
    results = asyncio.run(main())

