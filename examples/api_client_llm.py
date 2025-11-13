"""
Example: LLM council client (streaming + non-stream).

Demonstrates how to interact with the QNWIS LLM council API endpoints:
- Streaming mode: Real-time token-by-token output via Server-Sent Events
- Complete mode: Single response with full analysis

Usage:
    python examples/api_client_llm.py "What are Qatar's unemployment trends?"
"""

from __future__ import annotations

import asyncio
import json
import sys

import httpx

BASE = "http://localhost:8001"


async def query_streaming(question: str) -> None:
    """
    Query council using streaming endpoint.

    Streams events via SSE, printing stage transitions and tokens in real-time.

    Args:
        question: Question to analyze
    """
    url = f"{BASE}/api/v1/council/stream"
    payload = {"question": question, "provider": "anthropic"}

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            print(f"🔗 Connected to {url}")
            print(f"📝 Question: {question}\n")

            async for line in response.aiter_lines():
                if not line:
                    continue

                # Parse SSE data lines
                if line.startswith("data: "):
                    try:
                        evt = json.loads(line[6:])
                        stage = evt.get("stage", "unknown")
                        status = evt.get("status", "unknown")

                        if status == "running":
                            print(f"\n▶ {stage} ...")
                        elif status == "streaming" and "token" in evt.get("payload", {}):
                            print(evt["payload"]["token"], end="", flush=True)
                        elif status == "complete":
                            latency = evt.get("latency_ms", 0)
                            print(f"\n✅ {stage} ({latency:.0f} ms)")
                    except json.JSONDecodeError:
                        # Skip malformed events
                        continue
                elif line.startswith("event: heartbeat"):
                    # Ignore heartbeat events
                    continue


async def query_complete(question: str) -> None:
    """
    Query council using complete (non-streaming) endpoint.

    Returns full structured response after all stages complete.

    Args:
        question: Question to analyze
    """
    url = f"{BASE}/api/v1/council/run-llm"
    payload = {"question": question, "provider": "anthropic"}

    async with httpx.AsyncClient(timeout=120.0) as client:
        print(f"🔗 Sending request to {url}")
        print(f"📝 Question: {question}\n")
        print("⏳ Processing (this may take a minute)...\n")

        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    # Display results
    print("=" * 80)
    print("📊 FINAL ANALYSIS")
    print("=" * 80)
    print(data.get("synthesis", "No synthesis available"))
    print()

    # Display metadata
    metadata = data.get("metadata", {})
    print("=" * 80)
    print("📋 METADATA")
    print("=" * 80)
    print(f"Provider: {metadata.get('provider', 'N/A')}")
    print(f"Model: {metadata.get('model', 'N/A')}")

    stages = metadata.get("stages", {})
    if stages:
        print("\nStage Timings:")
        for stage_name, stage_data in stages.items():
            latency = stage_data.get("latency_ms", 0)
            print(f"  • {stage_name}: {latency:.0f} ms")

    # Display classification
    classification = data.get("classification")
    if classification:
        print("\n📑 Classification:")
        print(f"  {json.dumps(classification, indent=2)}")

    # Display agent reports count
    agent_reports = data.get("agent_reports", [])
    if agent_reports:
        print(f"\n🤖 Agent Reports: {len(agent_reports)} agents executed")


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python examples/api_client_llm.py 'Your question'")
        print("\nExample:")
        print("  python examples/api_client_llm.py 'What are Qatar unemployment trends?'")
        sys.exit(1)

    question = sys.argv[1]

    print("=" * 80)
    print("QNWIS LLM Council Client")
    print("=" * 80)
    print("\nSelect mode:")
    print("  1) Streaming (real-time token output)")
    print("  2) Complete (single structured response)")

    mode = input("\n> ").strip()

    try:
        if mode == "1":
            await query_streaming(question)
        elif mode == "2":
            await query_complete(question)
        else:
            print("Invalid selection. Use 1 or 2.")
            sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"\n❌ Request Error: {e}")
        print("Is the QNWIS API server running at http://localhost:8001?")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹ Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
