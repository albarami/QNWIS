#!/usr/bin/env python3
"""Test the deployed DeepSeek server."""

import requests
import json
import time

def test_deepseek():
    base_url = "http://localhost:8001"
    
    print("=" * 60)
    print("TESTING DEEPSEEK SERVER")
    print("=" * 60)
    
    # Test health endpoint
    print()
    print("[1] Testing health endpoint...")
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        print(f"  Status: {r.status_code}")
        print(f"  Response: {r.json()}")
    except Exception as e:
        print(f"  ❌ Health check failed: {e}")
        return False
    
    # Test models endpoint
    print()
    print("[2] Testing models endpoint...")
    try:
        r = requests.get(f"{base_url}/v1/models", timeout=5)
        models = r.json()
        print(f"  Available models: {[m['id'] for m in models['data']]}")
    except Exception as e:
        print(f"  ❌ Models check failed: {e}")
    
    # Test chat completion
    print()
    print("[3] Testing chat completion...")
    try:
        start = time.time()
        r = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": "deepseek",
                "messages": [
                    {"role": "user", "content": "What is 2+2? Answer in one word."}
                ],
                "max_tokens": 50,
                "temperature": 0.1
            },
            timeout=120
        )
        elapsed = (time.time() - start) * 1000
        
        result = r.json()
        response_text = result["choices"][0]["message"]["content"]
        model = result["model"]
        
        print(f"  Response: {response_text}")
        print(f"  Model: {model}")
        print(f"  Latency: {elapsed:.0f}ms")
    except Exception as e:
        print(f"  ❌ Chat failed: {e}")
        return False
    
    # Test with thinking prompt
    print()
    print("[4] Testing with analysis prompt...")
    try:
        start = time.time()
        r = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": "deepseek",
                "messages": [
                    {"role": "system", "content": "You are an economic analyst."},
                    {"role": "user", "content": "What happens when oil prices increase by 50%? Brief answer."}
                ],
                "max_tokens": 200,
                "temperature": 0.7
            },
            timeout=120
        )
        elapsed = (time.time() - start) * 1000
        
        result = r.json()
        response_text = result["choices"][0]["message"]["content"]
        
        print(f"  Response: {response_text[:200]}...")
        print(f"  Latency: {elapsed:.0f}ms")
    except Exception as e:
        print(f"  ❌ Analysis failed: {e}")
        return False
    
    print()
    print("=" * 60)
    print("✅ DEEPSEEK SERVER FULLY OPERATIONAL!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_deepseek()

