#!/usr/bin/env python3
"""Test actual Azure LLM connection."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from dotenv import load_dotenv

# Load .env BEFORE importing qnwis modules
load_dotenv()

async def test_llm():
    print("=" * 60)
    print("TESTING AZURE LLM CONNECTION")
    print("=" * 60)
    
    try:
        from src.qnwis.llm.client import LLMClient, get_client
        from src.qnwis.llm.model_router import get_router
        
        router = get_router()
        print(f"\nPrimary model: {router.primary_config.deployment}")
        print(f"Endpoint: {router.primary_config.endpoint[:50]}...")
        
        # Create client
        client = get_client(provider="azure")
        
        print("\nSending test prompt...")
        
        # Simple test
        response_parts = []
        async for chunk in client.generate_stream(
            prompt="What is 2+2? Answer in one word.",
            system="You are a helpful assistant. Be brief.",
            max_tokens=10,
            temperature=0.1,
        ):
            response_parts.append(chunk)
        
        response = "".join(response_parts)
        print(f"Response: {response}")
        print("\n✅ Azure LLM connection WORKING!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_llm())

