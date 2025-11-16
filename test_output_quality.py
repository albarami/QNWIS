import asyncio
import os
import sys

# Ensure src is on the path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from qnwis.orchestration.graph_llm import LLMWorkflow


async def test_full_output() -> None:
    """Run the full workflow using the real Anthropic client."""

    workflow = LLMWorkflow()

    model_name = getattr(workflow.llm_client, "model", "unknown")
    if "stub" in model_name.lower():
        raise RuntimeError(
            "❌ Still using stub LLM model. Ensure QNWIS_LLM_PROVIDER=anthropic and an Anthropic API key are set."
        )

    print(f"✅ Using real LLM model: {model_name}\n")

    test_query = (
        "Analyze Qatar's tech sector Qatarization feasibility. "
        "What percentage of tech roles can realistically be filled by "
        "Qatari nationals in the next 5 years given current graduate "
        "production rates?"
    )

    print("\n" + "=" * 60)
    print("🧪 TESTING FULL SYSTEM OUTPUT")
    print("=" * 60)
    print(f"\nQuery: {test_query}\n")

    result = await workflow.run(test_query)

    classification = result.get("classification", {})
    complexity = classification.get("complexity", "N/A")
    agents_invoked = result.get("agents_invoked", [])
    confidence = result.get("confidence_score", 0.0)

    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)
    print(f"\n1) Complexity: {complexity}")
    print(f"2) Agents invoked: {agents_invoked}")
    print(f"3) Confidence: {confidence:.1%}")

    print("\n" + "-" * 60)
    print("4) Reasoning chain:")
    print("-" * 60)
    for idx, step in enumerate(result.get("reasoning_chain", []), 1):
        print(f"{idx}. {step}")

    labour_analysis = result.get("labour_economist_analysis", "NOT FOUND")

    print("\n" + "-" * 60)
    print("5) Labour Economist analysis (truncated):")
    print("-" * 60)
    if labour_analysis and labour_analysis != "NOT FOUND":
        snippet = labour_analysis[:1000]
        print(snippet + ("..." if len(labour_analysis) > 1000 else ""))
    else:
        print(labour_analysis)

    has_citations = "Per extraction:" in str(labour_analysis)
    print(f"\nContains citations: {has_citations}")

    debate = result.get("multi_agent_debate", "NOT FOUND")
    print("\n" + "-" * 60)
    print("6) Multi-agent debate (truncated):")
    print("-" * 60)
    if debate and debate != "NOT FOUND":
        print(debate[:800] + ("..." if len(debate) > 800 else ""))
    else:
        print(debate)

    synthesis = result.get("final_synthesis", "NOT FOUND")
    print("\n" + "-" * 60)
    print("7) Final synthesis (truncated):")
    print("-" * 60)
    if synthesis and synthesis != "NOT FOUND":
        print(synthesis[:1000] + ("..." if len(synthesis) > 1000 else ""))
    else:
        print(synthesis)

    print("\n" + "=" * 60)
    print("🔍 QUALITY CHECKS")
    print("=" * 60)

    checks = {
        "Extracted facts present": len(result.get("extracted_facts", [])) > 0,
        "Multiple agents invoked": len(agents_invoked) >= 2,
        "Citations in labour analysis": has_citations,
        "Debate node executed": bool(debate and not debate.startswith("⚠️")),
        "Confidence score calculated": confidence > 0,
        "Synthesis mentions recommendations": "recommend" in str(synthesis).lower()
        if synthesis != "NOT FOUND"
        else False,
    }

    for label, ok in checks.items():
        symbol = "✅" if ok else "❌"
        print(f"{symbol} {label}")

    passed_checks = sum(checks.values())
    total_checks = len(checks)
    print(f"\n📈 OVERALL: {passed_checks}/{total_checks} checks passed")

    if passed_checks == total_checks:
        print("🎉 SYSTEM IS WORKING AT FULL CAPACITY!")
    elif passed_checks >= total_checks * 0.7:
        print("⚠️ SYSTEM MOSTLY WORKING - Some improvements needed")
    else:
        print("🚨 CRITICAL GAPS DETECTED")


if __name__ == "__main__":
    asyncio.run(test_full_output())
