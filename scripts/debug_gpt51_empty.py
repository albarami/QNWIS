#!/usr/bin/env python3
"""
Debug script to capture RAW API response from GPT-5.1 for a failing query.
This will show us exactly what the API returns.
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

# Config from .env
config = {
    "deployment": os.getenv("MODEL_NAME_5.1", "gpt-5.1").strip().strip('"'),
    "api_version": os.getenv("API_VERSION_5.1", "2024-08-01-preview").strip().strip('"'),
    "endpoint": os.getenv("ENDPOINT_5.1", "").strip().rstrip("/"),
    "api_key": os.getenv("API_KEY_5.1", ""),
}

# A query that FAILED in the test
FAILING_QUERY = "Analyze Qatar's non-oil GDP growth and sector contribution (2015-2024)"

# System prompt used in comparison test
SYSTEM_PROMPT = """You are a senior economic advisor to Qatar's Ministry of Labour.
Provide PhD-level ministerial-grade analysis with:
- Specific data points and statistics
- Structured sections with clear headers
- Risk assessments and recommendations
- Actionable insights suitable for executive briefings

Be thorough, evidence-based, and cite sources where possible."""


async def debug_gpt51():
    print("=" * 70)
    print("DEBUG: GPT-5.1 EMPTY RESPONSE INVESTIGATION")
    print("=" * 70)
    
    print(f"\nConfig:")
    print(f"  Deployment: {config['deployment']}")
    print(f"  API Version: {config['api_version']}")
    print(f"  Endpoint: {config['endpoint']}")
    
    print(f"\nQuery (FAILING in test):")
    print(f"  {FAILING_QUERY[:80]}...")
    
    url = f"{config['endpoint']}/openai/deployments/{config['deployment']}/chat/completions?api-version={config['api_version']}"
    
    # The payload matching the comparison test
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": FAILING_QUERY}
        ],
        "max_completion_tokens": 4000,
        # No temperature for GPT-5.1
    }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config["api_key"],
    }
    
    print(f"\nURL: {url}")
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2)[:500] + "...")
    
    print("\n" + "-" * 70)
    print("SENDING REQUEST (may take 40-50 seconds)...")
    print("-" * 70)
    
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"\nHTTP Status: {response.status_code}")
            print(f"Response Headers (selected):")
            for h in ["x-request-id", "x-ms-region", "content-type"]:
                if h in response.headers:
                    print(f"  {h}: {response.headers[h]}")
            
            # Save raw response
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            raw_file = OUTPUT_DIR / f"debug_gpt51_raw_{ts}.txt"
            
            raw_text = response.text
            with open(raw_file, "w", encoding="utf-8") as f:
                f.write(f"HTTP Status: {response.status_code}\n")
                f.write(f"Headers: {dict(response.headers)}\n\n")
                f.write("BODY:\n")
                f.write(raw_text)
            
            print(f"\nSaved raw response to: {raw_file}")
            
            # Try to parse JSON
            try:
                data = response.json()
                json_file = OUTPUT_DIR / f"debug_gpt51_json_{ts}.json"
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"Saved parsed JSON to: {json_file}")
                
                print("\n" + "=" * 70)
                print("ANALYSIS OF RESPONSE")
                print("=" * 70)
                
                # Check structure
                print(f"\nTop-level keys: {list(data.keys())}")
                
                if "error" in data:
                    print(f"\n❌ ERROR in response:")
                    print(json.dumps(data["error"], indent=2))
                    return
                
                if "choices" in data:
                    choices = data["choices"]
                    print(f"\nNumber of choices: {len(choices)}")
                    
                    if choices:
                        choice = choices[0]
                        print(f"\nchoices[0] keys: {list(choice.keys())}")
                        
                        # Check message
                        if "message" in choice:
                            msg = choice["message"]
                            print(f"\nmessage keys: {list(msg.keys())}")
                            print(f"  role: {msg.get('role')}")
                            
                            content = msg.get("content")
                            print(f"  content type: {type(content).__name__}")
                            print(f"  content is None: {content is None}")
                            print(f"  content == '': {content == ''}")
                            
                            if content:
                                print(f"  content length: {len(content)}")
                                print(f"  content preview: {content[:200]}...")
                            else:
                                print(f"\n  ⚠️ CONTENT IS EMPTY/NONE!")
                            
                            # Check for refusal
                            if "refusal" in msg:
                                print(f"\n  refusal: {msg['refusal']}")
                        
                        # Check finish_reason
                        finish = choice.get("finish_reason")
                        print(f"\nfinish_reason: {finish}")
                        
                        if finish == "content_filter":
                            print("  ⚠️ Response was FILTERED!")
                        elif finish == "length":
                            print("  ⚠️ Response was TRUNCATED (length limit)!")
                
                # Check usage
                if "usage" in data:
                    usage = data["usage"]
                    print(f"\nUsage:")
                    print(f"  prompt_tokens: {usage.get('prompt_tokens')}")
                    print(f"  completion_tokens: {usage.get('completion_tokens')}")
                    print(f"  total_tokens: {usage.get('total_tokens')}")
                    
                    if "completion_tokens_details" in usage:
                        details = usage["completion_tokens_details"]
                        print(f"\n  Completion tokens details:")
                        print(f"    reasoning_tokens: {details.get('reasoning_tokens')}")
                        print(f"    audio_tokens: {details.get('audio_tokens')}")
                        
            except json.JSONDecodeError as e:
                print(f"\n❌ Failed to parse JSON: {e}")
                print(f"\nRaw response (first 2000 chars):\n{raw_text[:2000]}")
                
    except Exception as e:
        print(f"\n❌ Request failed: {e}")


if __name__ == "__main__":
    asyncio.run(debug_gpt51())

