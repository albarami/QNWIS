#!/usr/bin/env python3
"""
10-Query Regression Test for Azure Model Comparison.

Runs pilot queries through GPT-4o, GPT-5, and GPT-5.1,
comparing results on:
- Facts extracted (count)
- Source diversity (unique sources)
- Confidence score
- Response time (seconds)
- Synthesis quality (word count, structure)

Usage:
    python scripts/regression_test_azure_models.py
    
Prerequisites:
    - Azure OpenAI credentials configured in .env
    - GPT-4o, GPT-5, GPT-5.1 deployments available
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from openai import AsyncAzureOpenAI
import httpx

# Output directory
OUTPUT_DIR = Path("data/model_comparison_results")

# Helper to extract base endpoint from full URL
def get_base_endpoint(url: str) -> str:
    """Extract base Azure endpoint from full URL."""
    if not url:
        return ""
    # Handle URLs like https://xxx.openai.azure.com/openai/responses?...
    # We need just https://xxx.openai.azure.com/
    if "openai.azure.com" in url:
        parts = url.split("openai.azure.com")
        return parts[0] + "openai.azure.com/"
    return url

# Model configurations from user's .env
MODELS_CONFIG = {
    "GPT-4o": {
        "deployment": os.getenv("QNWIS_AZURE_MODEL", "gpt-4o"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
    },
    "GPT-5": {
        "deployment": os.getenv("DEPLOYMENT_5", "gpt-5-chat").strip().strip('"'),
        "api_version": os.getenv("API_VERSION_5", "2024-12-01-preview").strip().strip('"'),
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.getenv("API_KEY_5", os.getenv("AZURE_OPENAI_API_KEY")),
    },
    "GPT-5.1": {
        "deployment": os.getenv("MODEL_NAME_5.1", "gpt-5.1").strip().strip('"'),
        # GPT-5.1 uses Responses API with specific version
        "api_version": "2025-03-01-preview",
        "endpoint": os.getenv("ENDPOINT_5.1", os.getenv("AZURE_OPENAI_ENDPOINT", "")).strip(),
        "api_key": os.getenv("API_KEY_5.1", os.getenv("AZURE_OPENAI_API_KEY")),
        # GPT-5.1 uses Responses API (different from Chat Completions)
        "use_responses_api": True,
        "use_max_completion_tokens": True,
        # Try multiple deployment names
        "alt_deployments": ["gpt-5.1", "gpt-51", "gpt-5-1", "gpt-5.1-chat", "gpt-51-chat"],
    },
}

# Pilot queries for testing
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

async def call_responses_api(config: Dict, query: str, timeout: int = 120) -> str:
    """
    Call the GPT-5.1 Responses API (different from Chat Completions).
    
    GPT-5.1 uses the Responses API with different parameters:
    - Uses 'input' instead of 'messages'
    - Uses 'instructions' instead of 'system' message
    - Supports 'reasoning' parameter for chain-of-thought
    """
    endpoint = config["endpoint"].rstrip("/")
    api_key = config["api_key"]
    model = config["deployment"]
    api_version = config["api_version"]
    
    # Build Responses API URL
    url = f"{endpoint}/openai/deployments/{model}/responses?api-version={api_version}"
    
    # Responses API request format
    payload = {
        "input": query,
        "instructions": SYSTEM_PROMPT,
        "max_output_tokens": 4000,
        # Encourage concise text output and bounded reasoning
        "reasoning": {"effort": "low"},
        "text": {"verbosity": "medium"}
    }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            # If Responses API fails, try Chat Completions as fallback
            return await call_chat_completions_fallback(config, query, timeout)
        
        data = response.json()

        # Save raw response for diagnostics
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            import json as _json
            raw_file = OUTPUT_DIR / f"raw_gpt51_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(raw_file, "w", encoding="utf-8") as f:
                _json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        
        # Extract content from Responses API response
        # Response format: {"output": [{"type": "message", "content": [...]}]}
        output = data.get("output", [])
        content_parts = []
        
        for item in output:
            if item.get("type") == "message":
                for content_item in item.get("content", []):
                    if content_item.get("type") == "output_text":
                        content_parts.append(content_item.get("text", ""))
                    elif content_item.get("type") == "text":
                        content_parts.append(content_item.get("text", ""))
            # Some variants nest under item['message']
            if "message" in item and isinstance(item["message"], dict):
                for content_item in item["message"].get("content", []):
                    if content_item.get("type") in ("output_text", "text"):
                        content_parts.append(content_item.get("text", ""))
        
        # If no content found, check alternative response formats
        if not content_parts:
            # Try direct 'output_text' field
            if "output_text" in data:
                content_parts.append(data["output_text"])
            # Try 'choices' format (fallback)
            elif "choices" in data:
                for choice in data["choices"]:
                    if "message" in choice:
                        content_parts.append(choice["message"].get("content", ""))
                    elif "text" in choice:
                        content_parts.append(choice["text"])
            # Try top-level 'content' (some previews)
            elif isinstance(data.get("content"), str):
                content_parts.append(data["content"])
        
        return "\n".join(content_parts)


async def call_chat_completions_fallback(config: Dict, query: str, timeout: int = 120) -> str:
    """Fallback to Chat Completions API if Responses API fails."""
    client = AsyncAzureOpenAI(
        api_key=config["api_key"],
        api_version="2024-12-01-preview",
        azure_endpoint=config["endpoint"],
        timeout=timeout
    )
    
    response = await client.chat.completions.create(
        model=config["deployment"],
        messages=[
            {"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{query}"}
        ],
        max_completion_tokens=4000
    )
    
    return response.choices[0].message.content or ""


# System prompt for ministerial-grade analysis
SYSTEM_PROMPT = """You are a senior economic advisor to Qatar's Ministry of Labour.
Provide PhD-level ministerial-grade analysis with:
- Specific data points and statistics
- Structured sections with clear headers
- Risk assessments and recommendations
- Actionable insights suitable for executive briefings

Be thorough, evidence-based, and cite sources where possible."""


async def test_model_availability(model_name: str, config: Dict) -> Tuple[bool, str]:
    """Check if a model deployment is available. Returns (available, deployment_name)."""
    if not config["endpoint"] or not config["api_key"]:
        print(f"    {model_name}: Missing endpoint or API key")
        return False, config["deployment"]
    
    # List of deployments to try (primary + alternates)
    deployments_to_try = [config["deployment"]]
    if "alt_deployments" in config:
        deployments_to_try.extend(config["alt_deployments"])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_deployments = []
    for d in deployments_to_try:
        if d not in seen:
            seen.add(d)
            unique_deployments.append(d)
    
    for deployment in unique_deployments:
        try:
            client = AsyncAzureOpenAI(
                api_key=config["api_key"],
                api_version=config["api_version"],
                azure_endpoint=config["endpoint"],
                timeout=30
            )
            
            # Check if this model uses Responses API (GPT-5.1)
            if config.get("use_responses_api"):
                # Test using Responses API
                test_content = await call_responses_api(
                    {**config, "deployment": deployment},
                    "Say OK",
                    timeout=30
                )
                if not test_content:
                    raise Exception("Empty response from Responses API")
            elif config.get("use_max_completion_tokens"):
                # o1 models: use max_completion_tokens, no temperature
                await client.chat.completions.create(
                    model=deployment,
                    messages=[{"role": "user", "content": "Say OK"}],
                    max_completion_tokens=500
                )
            else:
                # Standard models (GPT-4o, GPT-5): use max_tokens
                await client.chat.completions.create(
                    model=deployment,
                    messages=[{"role": "user", "content": "Say OK"}],
                    max_tokens=100
                )
            
            # Found working deployment
            if deployment != config["deployment"]:
                print(f"    (found as '{deployment}')")
            return True, deployment
        except Exception as e:
            error_msg = str(e)[:80]
            if "404" in error_msg or "not found" in error_msg.lower():
                continue  # Try next deployment
            else:
                print(f"    {model_name} ({deployment}) error: {error_msg}")
                return False, deployment
    
    print(f"    {model_name} not available: No working deployment found")
    print(f"      Tried: {unique_deployments}")
    return False, config["deployment"]


async def run_query_with_model(
    query: str,
    model_name: str,
    config: Dict,
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Run a single query through Azure OpenAI with specified model.
    
    Args:
        query: The query to test
        model_name: Display name of the model
        config: Model configuration
        timeout: Request timeout in seconds
        
    Returns:
        Test result dictionary
    """
    result = {
        "model": model_name,
        "deployment": config["deployment"],
        "query": query[:100] + "...",
        "status": "unknown",
        "response_length": 0,
        "word_count": 0,
        "execution_time": 0.0,
        "quality_score": {},
        "error": None
    }
    
    start_time = time.time()
    
    try:
        # GPT-5.1 uses the Responses API (different from Chat Completions)
        if config.get("use_responses_api"):
            content = await call_responses_api(config, query, timeout)
        else:
            # Standard Chat Completions API (GPT-4o, GPT-5)
            client = AsyncAzureOpenAI(
                api_key=config["api_key"],
                api_version=config["api_version"],
                azure_endpoint=config["endpoint"],
                timeout=timeout
            )
            
            request_params = {
                "model": config["deployment"],
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ]
            }
            
            # GPT-5.1/o1 models: use max_completion_tokens, no temperature
            if config.get("use_max_completion_tokens"):
                request_params["max_completion_tokens"] = 4000
            else:
                request_params["max_tokens"] = 2500
                request_params["temperature"] = 0.3
            
            response = await client.chat.completions.create(**request_params)
            content = response.choices[0].message.content or ""
        execution_time = time.time() - start_time
        
        # Score quality
        quality = score_synthesis(content)
        
        # Build usage safely depending on API used
        usage: Dict[str, Any] = {}
        if not config.get("use_responses_api"):
            try:
                usage = {
                    "prompt_tokens": getattr(getattr(response, "usage", None), "prompt_tokens", 0),
                    "completion_tokens": getattr(getattr(response, "usage", None), "completion_tokens", 0),
                    "total_tokens": getattr(getattr(response, "usage", None), "total_tokens", 0),
                }
            except NameError:
                usage = {}

        # If content is empty, treat as error to avoid false success
        if not content or not content.strip():
            raise ValueError("Responses API returned empty content")

        result.update({
            "status": "success",
            "response_length": len(content),
            "word_count": len(content.split()),
            "execution_time": round(execution_time, 2),
            "quality_score": quality,
            "response_preview": content[:500] + "..." if len(content) > 500 else content,
            "full_response": content,
            "usage": usage,
        })
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["execution_time"] = round(time.time() - start_time, 2)
    
    return result


def score_synthesis(content: str) -> Dict[str, float]:
    """Score synthesis quality based on multiple factors."""
    if not content:
        return {"structure": 0, "depth": 0, "actionability": 0, "overall": 0}
    
    content_lower = content.lower()
    
    # Structure score
    structure_indicators = [
        "##" in content or "**" in content,
        "executive summary" in content_lower or "summary" in content_lower,
        "recommendation" in content_lower,
        "risk" in content_lower,
        len(content.split("\n\n")) > 3,
        "\n1." in content or "\n-" in content,  # Lists
    ]
    structure = sum(structure_indicators) / len(structure_indicators)
    
    # Depth score
    depth_indicators = [
        "%" in content,
        any(year in content for year in ["2023", "2024", "2025", "2030"]),
        "billion" in content_lower or "million" in content_lower,
        "$" in content or "qar" in content_lower,
        "qatar" in content_lower,
        "gdp" in content_lower,
        len(content) > 2000,
        any(w in content_lower for w in ["roi", "npv", "irr"]),
    ]
    depth = sum(depth_indicators) / len(depth_indicators)
    
    # Actionability score
    action_indicators = [
        "recommend" in content_lower,
        "should" in content_lower,
        "action" in content_lower or "implement" in content_lower,
        "priority" in content_lower,
        "strategy" in content_lower,
        "phase" in content_lower or "timeline" in content_lower,
    ]
    actionability = sum(action_indicators) / len(action_indicators)
    
    overall = (structure * 0.25 + depth * 0.45 + actionability * 0.30)
    
    return {
        "structure": round(structure, 3),
        "depth": round(depth, 3),
        "actionability": round(actionability, 3),
        "overall": round(overall, 3)
    }


def calculate_aggregate_score(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate aggregate score across all queries for a model."""
    if not results:
        return {"total": 0}
    
    successful = [r for r in results if r["status"] == "success"]
    if not successful:
        return {"total": 0, "success_rate": 0}
    
    avg_words = sum(r["word_count"] for r in successful) / len(successful)
    avg_time = sum(r["execution_time"] for r in successful) / len(successful)
    avg_quality = sum(r["quality_score"]["overall"] for r in successful) / len(successful)
    avg_structure = sum(r["quality_score"]["structure"] for r in successful) / len(successful)
    avg_depth = sum(r["quality_score"]["depth"] for r in successful) / len(successful)
    avg_action = sum(r["quality_score"]["actionability"] for r in successful) / len(successful)
    
    # Calculate total score (weighted)
    total = (
        min(avg_words / 1500, 1.0) * 20 +    # Comprehensiveness (max 20 points)
        avg_quality * 50 +                     # Quality (max 50 points)
        avg_depth * 20 +                       # Depth (max 20 points)
        (1 - min(avg_time / 60, 1.0)) * 10    # Speed bonus (max 10 points)
    )
    
    return {
        "total": round(total, 2),
        "success_rate": len(successful) / len(results),
        "avg_words": round(avg_words, 1),
        "avg_time": round(avg_time, 1),
        "avg_quality": round(avg_quality, 3),
        "avg_structure": round(avg_structure, 3),
        "avg_depth": round(avg_depth, 3),
        "avg_actionability": round(avg_action, 3),
        "queries_passed": len(successful),
        "queries_total": len(results)
    }


async def run_model_comparison() -> Dict[str, Any]:
    """Run full comparison test across Azure models."""
    print("=" * 70)
    print("10-QUERY REGRESSION TEST: GPT-4o vs GPT-5 vs GPT-5.1")
    print("=" * 70)
    print(f"\nStarted: {datetime.now().isoformat()}")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "queries_tested": len(PILOT_QUERIES),
        "models_tested": [],
        "model_results": {},
        "comparison": {},
        "winner": None
    }
    
    # Check model availability
    print("\n1. CHECKING MODEL AVAILABILITY")
    print("-" * 50)
    
    available_models = {}
    for model_name, config in MODELS_CONFIG.items():
        print(f"  Testing {model_name} ({config['deployment']})...", end=" ")
        is_available, working_deployment = await test_model_availability(model_name, config)
        if is_available:
            print("AVAILABLE")
            # Update config with working deployment name
            config["deployment"] = working_deployment
            available_models[model_name] = config
        else:
            print("NOT AVAILABLE")
    
    if len(available_models) < 2:
        print(f"\nERROR: Only {len(available_models)} model(s) available. Need at least 2 for comparison.")
        return results
    
    results["models_tested"] = list(available_models.keys())
    print(f"\nTesting {len(available_models)} models: {list(available_models.keys())}")
    
    # Test each model
    for model_name, config in available_models.items():
        print("\n" + "-" * 70)
        print(f"TESTING: {model_name} (deployment: {config['deployment']})")
        print("-" * 70)
        
        model_results = []
        
        for i, (domain, query) in enumerate(PILOT_QUERIES, 1):
            print(f"\n  [{i}/10] {domain}")
            result = await run_query_with_model(query, model_name, config)
            result["domain"] = domain
            model_results.append(result)
            
            if result["status"] == "success":
                print(f"    SUCCESS: {result['word_count']} words, {result['execution_time']}s, "
                      f"quality={result['quality_score']['overall']:.3f}")
            else:
                print(f"    FAILED: {result['error'][:60]}")
            
            # Brief pause between queries
            await asyncio.sleep(1)
        
        results["model_results"][model_name] = model_results
    
    # Calculate aggregate scores
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    scores = {}
    for model_name in available_models:
        scores[model_name] = calculate_aggregate_score(results["model_results"][model_name])
    
    results["comparison"] = scores
    
    # Print comparison table
    print("\n  AGGREGATE SCORES:")
    header = f"  {'Metric':<20}"
    for model in available_models:
        header += f" {model:<15}"
    print(header)
    print("  " + "-" * (20 + 15 * len(available_models)))
    
    metrics = ["total", "success_rate", "avg_words", "avg_time", "avg_quality", 
               "avg_structure", "avg_depth", "avg_actionability"]
    
    for metric in metrics:
        row = f"  {metric:<20}"
        for model in available_models:
            val = scores[model].get(metric, 0)
            if isinstance(val, float):
                row += f" {val:<15.3f}"
            else:
                row += f" {val:<15}"
        print(row)
    
    # Determine winner
    print("\n" + "=" * 70)
    print("WINNER DETERMINATION")
    print("=" * 70)
    
    # Sort by total score
    ranked = sorted(scores.items(), key=lambda x: x[1]["total"], reverse=True)
    
    print("\n  FINAL RANKING:")
    for i, (model, score) in enumerate(ranked, 1):
        print(f"    {i}. {model}: {score['total']:.2f} points")
    
    winner = ranked[0][0]
    results["winner"] = winner
    
    print(f"\n  🏆 WINNER: {winner}")
    print(f"     Total Score: {scores[winner]['total']:.2f}")
    print(f"     Avg Quality: {scores[winner]['avg_quality']:.3f}")
    print(f"     Avg Words: {scores[winner]['avg_words']:.0f}")
    print(f"     Avg Time: {scores[winner]['avg_time']:.1f}s")
    
    # Recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    
    winner_config = available_models[winner]
    print(f"""
Based on the 10-query regression test, {winner} demonstrates the best
performance for ministerial-grade Qatar labor market analysis.

RECOMMENDED .env CONFIGURATION:
  QNWIS_AZURE_MODEL={winner_config['deployment']}
  AZURE_OPENAI_API_VERSION={winner_config['api_version']}

Score Breakdown:
  - Quality:       {scores[winner]['avg_quality']:.3f} (structure + depth + actionability)
  - Comprehensiveness: {scores[winner]['avg_words']:.0f} words avg
  - Response Time: {scores[winner]['avg_time']:.1f}s avg
  - Success Rate:  {scores[winner]['success_rate']*100:.0f}%
""")
    
    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Summary JSON
    output_file = OUTPUT_DIR / f"model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    summary_data = {k: v for k, v in results.items()}
    # Remove full responses from JSON to keep file size reasonable
    for model in summary_data.get("model_results", {}):
        for r in summary_data["model_results"][model]:
            r.pop("full_response", None)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, default=str)
    
    print(f"\n  Results saved to: {output_file}")
    
    # Save full responses for manual review
    for model_name in available_models:
        response_file = OUTPUT_DIR / f"responses_{model_name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(response_file, "w", encoding="utf-8") as f:
            f.write(f"MODEL: {model_name}\n")
            f.write(f"{'='*70}\n\n")
            for r in results["model_results"][model_name]:
                f.write(f"QUERY [{r['domain']}]: {r['query']}\n")
                f.write(f"Status: {r['status']}, Time: {r['execution_time']}s, Words: {r['word_count']}\n")
                f.write(f"Quality: {r['quality_score']}\n")
                f.write("-"*50 + "\n")
                response_text = r.get("full_response") or r.get("error") or "No response"
                f.write(str(response_text) + "\n")
                f.write("\n" + "="*70 + "\n\n")
        print(f"  Responses saved to: {response_file}")
    
    print("\n" + "=" * 70)
    print("MODEL COMPARISON TEST COMPLETE")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    results = asyncio.run(run_model_comparison())
    
    # Exit with appropriate code
    if results.get("winner"):
        print(f"\nWinner: {results['winner']}")
        sys.exit(0)
    else:
        print("\nNo winner determined - check model availability")
        sys.exit(1)

