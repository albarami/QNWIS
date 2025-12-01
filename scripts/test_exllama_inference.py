#!/usr/bin/env python3
"""Quick test of ExLlamaV2 inference speed."""

import requests
import time

def test_inference(port=8001):
    print(f"Testing ExLlamaV2 on port {port}...")
    
    # Simple test
    start = time.time()
    response = requests.post(
        f'http://localhost:{port}/v1/chat/completions',
        json={
            'messages': [{'role': 'user', 'content': 'What is 2+2? Answer in one word.'}],
            'max_tokens': 50
        },
        timeout=60
    )
    elapsed = time.time() - start
    
    data = response.json()
    content = data['choices'][0]['message']['content']
    tokens_per_sec = data.get('tokens_per_second', 'N/A')
    
    print(f"Response: {content}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Tokens/sec: {tokens_per_sec}")
    
    # Longer test
    print("\nTesting longer response...")
    start = time.time()
    response = requests.post(
        f'http://localhost:{port}/v1/chat/completions',
        json={
            'messages': [{'role': 'user', 'content': 'Explain quantum computing in 3 sentences.'}],
            'max_tokens': 200
        },
        timeout=120
    )
    elapsed = time.time() - start
    
    data = response.json()
    content = data['choices'][0]['message']['content']
    tokens_per_sec = data.get('tokens_per_second', 'N/A')
    completion_tokens = data.get('usage', {}).get('completion_tokens', 'N/A')
    
    print(f"Response: {content[:200]}...")
    print(f"Time: {elapsed:.2f}s")
    print(f"Completion tokens: {completion_tokens}")
    print(f"Tokens/sec: {tokens_per_sec}")
    
    return True

if __name__ == "__main__":
    test_inference()

