"""Test API endpoint with proper authentication."""
import asyncio
import httpx
import os
from dotenv import load_dotenv


load_dotenv()


async def test_api_authenticated() -> bool:
    """Test API with authentication."""

    # Try multiple auth methods
    api_key = os.getenv("QNWIS_API_KEY", "dev-test-key-12345")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "question": "What is Qatar's unemployment rate?",
        "provider": "anthropic",
    }

    print("\n" + "=" * 80)
    print("API AUTHENTICATION TEST")
    print("=" * 80)
    print("URL: http://127.0.0.1:8001/api/v1/council/stream")
    print(f"API Key: {api_key[:20]}...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8001/api/v1/council/stream",
                json=payload,
                headers=headers,
            )

            print(f"\nStatus Code: {response.status_code}")

            if response.status_code == 200:
                print("\n✅ API CALL SUCCESSFUL!")

                # Try to parse response
                try:
                    data = response.json()
                    print(f"\nResponse keys: {list(data.keys())}")

                    # Check for expected fields
                    if "synthesis" in data:
                        print(f"✅ Synthesis present: {len(data['synthesis'])} chars")
                    if "agent_reports" in data:
                        print(
                            f"✅ Agent reports: {len(data['agent_reports'])} agents"
                        )
                    if "reasoning_chain" in data:
                        print(
                            f"✅ Reasoning chain: {len(data['reasoning_chain'])} steps"
                        )
                    if "debate_result" in data:
                        print("✅ Debate result present")
                    if "critique_result" in data:
                        print("✅ Critique result present")

                    return True
                except Exception:
                    print(
                        f"\n✅ Response received (not JSON): {response.text[:200]}"
                    )
                    return True

            elif response.status_code == 401:
                print("\n❌ AUTHENTICATION FAILED (401)")
                print(f"Response: {response.text}")
                print("\nFIX NEEDED: Check .env file for QNWIS_API_KEY")
                return False

            else:
                print(f"\n❌ API ERROR: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:  # pragma: no cover - manual diagnostic script
            print(f"\n❌ REQUEST FAILED: {e}")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_api_authenticated())
    raise SystemExit(0 if success else 1)
