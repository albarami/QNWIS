"""Direct test of LLM client with real Claude Sonnet."""
import asyncio
import os
import sys

os.environ['QNWIS_LLM_PROVIDER'] = 'anthropic'
os.environ['QNWIS_ANTHROPIC_MODEL'] = 'claude-sonnet-4-20250514'

sys.path.insert(0, 'src')

from qnwis.llm.client import LLMClient


async def test_llm():
    print("Testing LLM Client with Real Claude Sonnet")
    print("=" * 60)

    # Initialize client
    client = LLMClient(provider='anthropic')
    print(f"Provider: {client.provider}")
    print(f"Model: {client.model}")
    print(f"Timeout: {client.timeout_s}s")
    print()

    # Test prompt
    prompt = """Based on this data:
Qatar unemployment: 0.1%
UAE unemployment: 2.7%
Saudi Arabia unemployment: 4.9%

Provide a brief 2-sentence analysis comparing Qatar to other GCC countries."""

    print("Sending prompt to Claude...")
    print()

    # Stream response
    response = ""
    token_count = 0

    try:
        async for token in client.generate_stream(
            prompt=prompt,
            system="You are a labour market analyst. Be concise.",
            temperature=0.3,
            max_tokens=200
        ):
            response += token
            token_count += 1
            if token_count <= 5:
                print(f"Token {token_count}: {repr(token)}")

        print()
        print("=" * 60)
        print("RESPONSE:")
        print("=" * 60)
        print(response)
        print()
        print(f"Total tokens: {token_count}")
        print(f"Length: {len(response)} characters")

        # Check if it's stub data
        if "test finding" in response.lower() or "test_metric" in response.lower():
            print("\n[FAIL] Response is stub test data!")
            return False
        else:
            print("\n[PASS] Response is real Claude Sonnet analysis!")
            return True

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_llm())
    sys.exit(0 if success else 1)
