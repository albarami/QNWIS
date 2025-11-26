#!/usr/bin/env python3
"""
Azure OpenAI Model Testing Script.

Tests available Azure OpenAI deployments:
1. Verifies gpt-5.1-chat deployment is accessible
2. Tests with sample ministerial query
3. Measures response quality, latency
4. Falls back to gpt-4o, gpt-4o-mini if needed

Usage:
    python scripts/test_azure_models.py
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

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    print("Note: python-dotenv not installed, using system environment variables")


# Test configuration
TEST_MODELS = [
    "gpt-5.1-chat",  # Primary target
    "gpt-4o",        # Fallback 1
    "gpt-4o-mini",   # Fallback 2 (cost-efficient)
    "gpt-4-turbo",   # Fallback 3
]

# Sample ministerial query for testing
MINISTERIAL_TEST_QUERY = """
Analyze the impact of Qatar's Qatarization policy on the labor market,
considering employment rates, skills development, and economic diversification.
Provide a strategic assessment with recommendations.
"""

SYSTEM_PROMPT = """You are a senior policy advisor providing ministerial-grade analysis.
Your response should be:
- Evidence-based with specific data points
- Structured with clear sections
- Actionable with concrete recommendations
- Professional and suitable for executive briefings"""


async def test_azure_model(
    model_name: str,
    query: str,
    system_prompt: str
) -> Dict[str, Any]:
    """
    Test a specific Azure OpenAI model.
    
    Args:
        model_name: Azure deployment name
        query: Test query
        system_prompt: System prompt
        
    Returns:
        Test results dictionary
    """
    from openai import AsyncAzureOpenAI
    
    # Get Azure configuration from environment
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    
    if not api_key or not endpoint:
        return {
            "model": model_name,
            "status": "error",
            "error": "Azure OpenAI credentials not configured",
            "latency_ms": 0
        }
    
    client = AsyncAzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint,
        timeout=120
    )
    
    result = {
        "model": model_name,
        "status": "unknown",
        "latency_ms": 0,
        "response_length": 0,
        "response_preview": "",
        "error": None,
        "quality_indicators": {}
    }
    
    start_time = time.time()
    
    try:
        print(f"\n  Testing {model_name}...")
        
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        latency_ms = (time.time() - start_time) * 1000
        content = response.choices[0].message.content or ""
        
        # Analyze response quality
        quality = analyze_response_quality(content)
        
        result.update({
            "status": "success",
            "latency_ms": round(latency_ms, 2),
            "response_length": len(content),
            "response_preview": content[:500] + "..." if len(content) > 500 else content,
            "quality_indicators": quality,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
        })
        
        print(f"    SUCCESS: {latency_ms:.0f}ms, {len(content)} chars, quality={quality['overall_score']:.2f}")
        
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        error_msg = str(e)
        
        # Check for specific error types
        if "DeploymentNotFound" in error_msg or "404" in error_msg:
            result["status"] = "not_found"
            result["error"] = f"Deployment '{model_name}' not found in Azure"
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            result["status"] = "rate_limited"
            result["error"] = "Rate limit exceeded"
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            result["status"] = "auth_error"
            result["error"] = "Authentication failed"
        else:
            result["status"] = "error"
            result["error"] = error_msg
        
        result["latency_ms"] = round(latency_ms, 2)
        print(f"    FAILED: {result['status']} - {result['error'][:100]}")
    
    return result


def analyze_response_quality(content: str) -> Dict[str, Any]:
    """
    Analyze response quality based on multiple factors.
    
    Args:
        content: Response content
        
    Returns:
        Quality indicators dictionary
    """
    quality = {
        "length_score": 0.0,
        "structure_score": 0.0,
        "depth_score": 0.0,
        "overall_score": 0.0
    }
    
    # Length score (ideal: 800-2000 chars for this query)
    length = len(content)
    if length < 200:
        quality["length_score"] = 0.2
    elif length < 500:
        quality["length_score"] = 0.5
    elif length < 800:
        quality["length_score"] = 0.7
    elif length < 2000:
        quality["length_score"] = 1.0
    else:
        quality["length_score"] = 0.9
    
    # Structure score (check for sections, bullets, etc.)
    structure_indicators = [
        "##" in content or "**" in content,  # Markdown headers/bold
        "\n-" in content or "\n•" in content,  # Bullet points
        "\n1." in content or "\n2." in content,  # Numbered lists
        "recommendation" in content.lower(),
        "conclusion" in content.lower() or "summary" in content.lower()
    ]
    quality["structure_score"] = sum(structure_indicators) / len(structure_indicators)
    
    # Depth score (check for specific terms)
    depth_indicators = [
        "%" in content,  # Statistics
        any(year in content for year in ["2020", "2021", "2022", "2023", "2024", "2025"]),
        "qatar" in content.lower(),
        "qatarization" in content.lower(),
        "workforce" in content.lower() or "labor" in content.lower() or "employment" in content.lower(),
        "billion" in content.lower() or "million" in content.lower(),
        "policy" in content.lower() or "strategy" in content.lower()
    ]
    quality["depth_score"] = sum(depth_indicators) / len(depth_indicators)
    
    # Overall score (weighted average)
    quality["overall_score"] = (
        quality["length_score"] * 0.3 +
        quality["structure_score"] * 0.3 +
        quality["depth_score"] * 0.4
    )
    
    return quality


async def discover_available_models() -> List[str]:
    """
    Discover which models are available on the Azure deployment.
    
    Returns:
        List of available model names
    """
    available = []
    
    for model in TEST_MODELS:
        result = await test_azure_model(
            model,
            "Hello, this is a connectivity test. Reply with 'OK'.",
            "Reply briefly."
        )
        if result["status"] == "success":
            available.append(model)
    
    return available


async def run_full_test() -> Dict[str, Any]:
    """
    Run full Azure OpenAI model test suite.
    
    Returns:
        Complete test results
    """
    print("=" * 70)
    print("AZURE OPENAI MODEL TESTING")
    print("=" * 70)
    print(f"\nStarted: {datetime.now().isoformat()}")
    
    # Check environment
    print("\n1. ENVIRONMENT CHECK")
    print("-" * 40)
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "NOT SET")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "NOT SET")
    target_model = os.getenv("QNWIS_AZURE_MODEL", "NOT SET")
    
    print(f"  Endpoint: {endpoint[:50]}..." if len(endpoint) > 50 else f"  Endpoint: {endpoint}")
    print(f"  API Version: {api_version}")
    print(f"  Target Model: {target_model}")
    print(f"  API Key: {'SET' if os.getenv('AZURE_OPENAI_API_KEY') else 'NOT SET'}")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "endpoint": endpoint,
            "api_version": api_version,
            "target_model": target_model
        },
        "models_tested": [],
        "available_models": [],
        "recommended_model": None,
        "summary": {}
    }
    
    # Test all models
    print("\n2. MODEL TESTING")
    print("-" * 40)
    
    for model in TEST_MODELS:
        test_result = await test_azure_model(
            model,
            MINISTERIAL_TEST_QUERY,
            SYSTEM_PROMPT
        )
        results["models_tested"].append(test_result)
        
        if test_result["status"] == "success":
            results["available_models"].append(model)
    
    # Determine best model
    print("\n3. RESULTS SUMMARY")
    print("-" * 40)
    
    successful = [r for r in results["models_tested"] if r["status"] == "success"]
    
    if successful:
        # Sort by quality score, then latency
        best = sorted(
            successful,
            key=lambda x: (-x["quality_indicators"]["overall_score"], x["latency_ms"])
        )[0]
        results["recommended_model"] = best["model"]
        
        print(f"\n  RECOMMENDED MODEL: {best['model']}")
        print(f"  - Quality Score: {best['quality_indicators']['overall_score']:.2f}")
        print(f"  - Latency: {best['latency_ms']:.0f}ms")
        print(f"  - Response Length: {best['response_length']} chars")
    else:
        print("\n  NO WORKING MODELS FOUND!")
        print("  Please check your Azure OpenAI configuration.")
    
    # Summary table
    print("\n  MODEL COMPARISON:")
    print("  " + "-" * 60)
    print(f"  {'Model':<20} {'Status':<15} {'Latency':<10} {'Quality':<10}")
    print("  " + "-" * 60)
    
    for r in results["models_tested"]:
        quality = r["quality_indicators"].get("overall_score", 0) if r["status"] == "success" else "-"
        latency = f"{r['latency_ms']:.0f}ms" if r["latency_ms"] else "-"
        print(f"  {r['model']:<20} {r['status']:<15} {latency:<10} {quality if quality == '-' else f'{quality:.2f}':<10}")
    
    print("  " + "-" * 60)
    
    # Save results
    output_path = Path("data/azure_model_test_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {output_path}")
    
    results["summary"] = {
        "total_tested": len(TEST_MODELS),
        "available": len(results["available_models"]),
        "recommended": results["recommended_model"]
    }
    
    print("\n" + "=" * 70)
    print(f"TEST COMPLETE: {len(results['available_models'])}/{len(TEST_MODELS)} models available")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    results = asyncio.run(run_full_test())
    
    # Exit with error if no models available
    if not results["available_models"]:
        sys.exit(1)

