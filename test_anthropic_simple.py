#!/usr/bin/env python3
"""Simple Anthropic test."""
import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.config import get_llm_config

async def test_anthropic():
    """Test Anthropic connection."""
    print("=" * 60)
    print("ANTHROPIC CONNECTION TEST")
    print("=" * 60)
    
    try:
        config = get_llm_config()
        print(f"✓ Config loaded: provider={config.provider}, model={config.anthropic_model}")
        
        client = LLMClient(provider="anthropic")
        print(f"✓ Client initialized: {client.model}")
        
        print("\nSending test prompt...")
        prompt = "What is 2+2? Answer in one sentence."
        
        tokens = []
        async for token in client.generate_stream(prompt=prompt, system="You are a helpful assistant.", temperature=0.7, max_tokens=100):
            tokens.append(token)
            sys.stdout.write(token)
            sys.stdout.flush()
        
        print(f"\n\n✓ Response received: {len(tokens)} tokens")
        print("=" * 60)
        print("✅ ANTHROPIC IS WORKING!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_anthropic())
    sys.exit(0 if result else 1)
