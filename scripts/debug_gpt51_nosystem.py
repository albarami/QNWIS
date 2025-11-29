#!/usr/bin/env python3
"""
Debug: Test GPT-5.1 WITHOUT system prompt.
GPT-5.1 may conflict with system prompts, causing empty responses.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

import httpx

OUTPUT_DIR = Path("data/model_comparison_results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

config = {
    "deployment": os.getenv("MODEL_NAME_5.1", "gpt-5.1").strip().strip('"'),
    "api_version": os.getenv("API_VERSION_5.1", "2024-08-01-preview").strip().strip('"'),
    "endpoint": os.getenv("ENDPOINT_5.1", "").strip().rstrip("/"),
    "api_key": os.getenv("API_KEY_5.1", ""),
}

# Same query that FAILED
FAILING_QUERY = "Analyze Qatar's non-oil GDP growth and sector contribution (2015-2024)"


async def test_without_system_prompt():
    print("=" * 70)
    print("TEST 1: GPT-5.1 WITHOUT System Prompt")
    print("=" * 70)
    
    url = f"{config['endpoint']}/openai/deployments/{config['deployment']}/chat/completions?api-version={config['api_version']}"
    
    # NO system prompt - just user message
    payload = {
        "messages": [
            {"role": "user", "content": FAILING_QUERY}
        ],
        "max_completion_tokens": 4000,
    }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config["api_key"],
    }
    
    print(f"Query: {FAILING_QUERY}")
    print(f"System Prompt: NONE")
    print("\nSending request...")
    
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, json=payload, headers=headers)
        
        print(f"\nHTTP Status: {response.status_code}")
        print(f"Content-Length: {response.headers.get('content-length', 'N/A')}")
        print(f"x-ms-rai-invoked: {response.headers.get('x-ms-rai-invoked', 'N/A')}")
        
        if response.text:
            try:
                data = response.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content")
                    if content:
                        print(f"\n✅ SUCCESS! Got {len(content)} chars")
                        print(f"Preview: {content[:300]}...")
                        return True
                    else:
                        print(f"\n❌ Content is empty/None")
                elif "error" in data:
                    print(f"\n❌ Error: {data['error']}")
            except:
                print(f"\n❌ Not valid JSON")
        else:
            print(f"\n❌ Empty body")
    
    return False


async def test_with_developer_prompt():
    print("\n" + "=" * 70)
    print("TEST 2: GPT-5.1 WITH 'developer' role (for reasoning models)")
    print("=" * 70)
    
    url = f"{config['endpoint']}/openai/deployments/{config['deployment']}/chat/completions?api-version={config['api_version']}"
    
    # Use 'developer' role instead of 'system' for reasoning models
    payload = {
        "messages": [
            {"role": "developer", "content": "You are an economic analyst. Provide data-driven analysis."},
            {"role": "user", "content": FAILING_QUERY}
        ],
        "max_completion_tokens": 4000,
    }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config["api_key"],
    }
    
    print(f"Query: {FAILING_QUERY}")
    print(f"Using 'developer' role instead of 'system'")
    print("\nSending request...")
    
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, json=payload, headers=headers)
        
        print(f"\nHTTP Status: {response.status_code}")
        print(f"Content-Length: {response.headers.get('content-length', 'N/A')}")
        print(f"x-ms-rai-invoked: {response.headers.get('x-ms-rai-invoked', 'N/A')}")
        
        if response.text:
            try:
                data = response.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content")
                    if content:
                        print(f"\n✅ SUCCESS! Got {len(content)} chars")
                        print(f"Preview: {content[:300]}...")
                        return True
                    else:
                        print(f"\n❌ Content is empty/None")
                elif "error" in data:
                    print(f"\n❌ Error: {json.dumps(data['error'], indent=2)}")
            except:
                print(f"\n❌ Not valid JSON: {response.text[:500]}")
        else:
            print(f"\n❌ Empty body")
    
    return False


async def test_simpler_query():
    print("\n" + "=" * 70)
    print("TEST 3: Simpler query (no complex analysis)")
    print("=" * 70)
    
    url = f"{config['endpoint']}/openai/deployments/{config['deployment']}/chat/completions?api-version={config['api_version']}"
    
    simple_query = "What was Qatar's GDP in 2023?"
    
    payload = {
        "messages": [
            {"role": "user", "content": simple_query}
        ],
        "max_completion_tokens": 1000,
    }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config["api_key"],
    }
    
    print(f"Query: {simple_query}")
    print("\nSending request...")
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload, headers=headers)
        
        print(f"\nHTTP Status: {response.status_code}")
        print(f"Content-Length: {response.headers.get('content-length', 'N/A')}")
        
        if response.text:
            try:
                data = response.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content")
                    if content:
                        print(f"\n✅ SUCCESS! Got {len(content)} chars")
                        print(f"Content: {content}")
                        return True
            except:
                pass
        print(f"\n❌ Failed")
    
    return False


async def main():
    print("Testing different configurations for GPT-5.1...")
    print(f"Deployment: {config['deployment']}")
    print(f"Endpoint: {config['endpoint']}")
    print()
    
    results = {}
    
    results["no_system"] = await test_without_system_prompt()
    results["developer_role"] = await test_with_developer_prompt()
    results["simple_query"] = await test_simpler_query()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test}: {status}")
    
    if results["no_system"]:
        print("\n💡 FIX: Remove system prompt for GPT-5.1")
    elif results["developer_role"]:
        print("\n💡 FIX: Use 'developer' role instead of 'system' for GPT-5.1")
    elif results["simple_query"]:
        print("\n💡 ISSUE: Complex analytical queries are being filtered")
    else:
        print("\n⚠️ All tests failed - may be Azure content filter or deployment issue")


if __name__ == "__main__":
    asyncio.run(main())

