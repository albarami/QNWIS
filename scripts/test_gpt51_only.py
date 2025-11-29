#!/usr/bin/env python3
"""
Test GPT-5.1 ONLY - Quick validation before full comparison.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

import httpx

OUTPUT_DIR = Path("data/model_comparison_results")

print("=" * 70)
print("GPT-5.1 QUICK TEST")
print("=" * 70)

# Show .env config
print("\n1. YOUR .ENV CONFIGURATION:")
print("-" * 50)
print(f"   MODEL_NAME_5.1:    {os.getenv('MODEL_NAME_5.1', 'NOT SET')}")
print(f"   API_VERSION_5.1:   {os.getenv('API_VERSION_5.1', 'NOT SET')}")
print(f"   API_KEY_5.1:       {'SET (' + os.getenv('API_KEY_5.1', '')[:8] + '...)' if os.getenv('API_KEY_5.1') else 'NOT SET'}")
print(f"   ENDPOINT_5.1:      {os.getenv('ENDPOINT_5.1', 'NOT SET')}")

# Build config
config = {
    "deployment": os.getenv("MODEL_NAME_5.1", "gpt-5.1").strip().strip('"'),
    "api_version": os.getenv("API_VERSION_5.1", "2024-08-01-preview").strip().strip('"'),
    "endpoint": os.getenv("ENDPOINT_5.1", os.getenv("AZURE_OPENAI_ENDPOINT", "")).strip(),
    "api_key": os.getenv("API_KEY_5.1", os.getenv("AZURE_OPENAI_API_KEY", "")),
}

print("\n2. PARSED CONFIG:")
print("-" * 50)
print(f"   deployment:  {config['deployment']}")
print(f"   api_version: {config['api_version']}")
print(f"   endpoint:    {config['endpoint']}")
print(f"   api_key:     {'SET' if config['api_key'] else 'NOT SET'}")

if not config['endpoint'] or not config['api_key']:
    print("\n❌ ERROR: Missing endpoint or API key!")
    sys.exit(1)


async def test_responses_api():
    endpoint = config["endpoint"].rstrip("/")
    model = config["deployment"]
    api_version = config["api_version"]
    api_key = config["api_key"]
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }
    
    # Test query
    query = "What is 2+2? Answer in one word."
    
    # Try multiple URL variants
    url_variants = [
        # Variant A: deployments/{model}/responses
        (
            f"{endpoint}/openai/deployments/{model}/responses?api-version={api_version}",
            {"input": query, "max_output_tokens": 100}
        ),
        # Variant B: /openai/responses with model in body
        (
            f"{endpoint}/openai/responses?api-version={api_version}",
            {"model": model, "input": query, "max_output_tokens": 100}
        ),
        # Variant C: Chat Completions API (fallback test)
        (
            f"{endpoint}/openai/deployments/{model}/chat/completions?api-version={api_version}",
            {
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 100
            }
        ),
        # Variant D: Chat Completions with max_completion_tokens
        (
            f"{endpoint}/openai/deployments/{model}/chat/completions?api-version={api_version}",
            {
                "messages": [{"role": "user", "content": query}],
                "max_completion_tokens": 100
            }
        ),
    ]
    
    print("\n3. TESTING API ENDPOINTS:")
    print("-" * 50)
    
    async with httpx.AsyncClient(timeout=60) as client:
        for i, (url, payload) in enumerate(url_variants, 1):
            api_type = "Responses" if "responses" in url else "Chat Completions"
            print(f"\n   [{i}/4] {api_type} API")
            print(f"   URL: {url[:80]}...")
            print(f"   Payload: {json.dumps(payload)[:100]}...")
            
            try:
                resp = await client.post(url, json=payload, headers=headers)
                print(f"   HTTP Status: {resp.status_code}")
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Save raw response
                    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    raw_file = OUTPUT_DIR / f"test_gpt51_variant{i}_{ts}.json"
                    with open(raw_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"   Saved: {raw_file.name}")
                    
                    # Try to extract content
                    content = ""
                    
                    # Responses API format
                    if "output" in data:
                        output = data["output"]
                        if isinstance(output, str):
                            content = output
                        elif isinstance(output, list):
                            for item in output:
                                if isinstance(item, dict):
                                    if item.get("type") == "message":
                                        for c in item.get("content", []):
                                            if isinstance(c, dict) and "text" in c:
                                                content += c["text"]
                                    elif "text" in item:
                                        content += item["text"]
                    
                    # Chat Completions format
                    if "choices" in data:
                        for choice in data["choices"]:
                            msg = choice.get("message", {})
                            if msg.get("content"):
                                content += msg["content"]
                    
                    # Direct fields
                    for field in ["output_text", "text", "content"]:
                        if field in data and isinstance(data[field], str):
                            content += data[field]
                    
                    if content:
                        print(f"   ✅ SUCCESS! Content: {content[:100]}")
                        print(f"\n{'='*70}")
                        print(f"✅ GPT-5.1 WORKS with variant {i} ({api_type} API)")
                        print(f"   URL: {url}")
                        print(f"{'='*70}")
                        return True, i, url
                    else:
                        print(f"   ⚠️ 200 OK but no content extracted")
                        print(f"   Response keys: {list(data.keys())}")
                else:
                    error = resp.text[:200]
                    print(f"   ❌ Error: {error}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
    
    print(f"\n{'='*70}")
    print("❌ GPT-5.1 NOT WORKING with any API variant")
    print("   Check your Azure deployment name and API version")
    print(f"{'='*70}")
    return False, 0, ""


if __name__ == "__main__":
    success, variant, url = asyncio.run(test_responses_api())
    
    if success:
        print(f"\n📋 TO USE IN COMPARISON TEST:")
        print(f"   The working API variant is #{variant}")
        print(f"   URL pattern: {url}")
        sys.exit(0)
    else:
        sys.exit(1)

