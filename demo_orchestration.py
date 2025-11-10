"""
Demo script for QNWIS Orchestration Workflow.

This script demonstrates the complete workflow with real agents and mock data.
Run with: python demo_orchestration.py
"""

from src.qnwis.agents.base import DataClient
from src.qnwis.data.deterministic.models import Freshness, Provenance, QueryResult, Row
from src.qnwis.orchestration import (
    OrchestrationTask,
    create_default_registry,
    create_graph,
)


class MockDataClient(DataClient):
    """Mock data client for demo purposes."""

    def run(self, query_id: str) -> QueryResult:
        """Return mock data."""
        from datetime import datetime
        
        # Mock different data based on query_id
        if "attrition" in query_id:
            rows = [
                Row(data={"sector": "Construction", "attrition_rate": 18.5}),
                Row(data={"sector": "Finance", "attrition_rate": 8.2}),
                Row(data={"sector": "Healthcare", "attrition_rate": 12.3}),
                Row(data={"sector": "Education", "attrition_rate": 6.1}),
            ]
        elif "gcc" in query_id or "unemployment" in query_id:
            rows = [
                Row(data={"country": "Qatar", "unemployment_rate": 3.1}),
                Row(data={"country": "UAE", "unemployment_rate": 2.8}),
                Row(data={"country": "Saudi Arabia", "unemployment_rate": 5.6}),
                Row(data={"country": "Bahrain", "unemployment_rate": 4.2}),
            ]
        else:
            rows = [
                Row(data={"year": 2023, "value": 100.0}),
                Row(data={"year": 2024, "value": 105.0}),
            ]

        return QueryResult(
            query_id=query_id,
            rows=rows,
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="mock_dataset",
                locator="/mock/data.csv",
                fields=list(rows[0].data.keys()) if rows else [],
            ),
            freshness=Freshness(
                asof_date=datetime.utcnow().date().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
            ),
            warnings=[],
        )




def main():
    """Run orchestration demo."""
    print("=" * 70)
    print("QNWIS Orchestration Workflow - Demo")
    print("=" * 70)
    print()

    # Setup with mock client
    print("1. Setting up environment with mock data client...")
    client = MockDataClient()
    registry = create_default_registry(client)

    print(f"   ✓ Registry created with {len(registry.intents())} intent(s)")
    print(f"   ✓ Available intents: {', '.join(registry.intents()[:3])}...")
    print()

    # Build graph
    print("2. Building LangGraph workflow...")
    graph = create_graph(registry)
    print("   ✓ Graph built successfully")
    print()

    # Create task - using pattern.anomalies as example
    print("3. Creating orchestration task...")
    task = OrchestrationTask(
        intent="pattern.anomalies",
        params={"z_threshold": 2.5, "min_sample_size": 3},
        user_id="demo_user",
        request_id="DEMO-001",
    )
    print(f"   ✓ Task: intent={task.intent}, params={task.params}")
    print()

    # Execute workflow
    print("4. Executing workflow...")
    result = graph.run(task)
    print(f"   ✓ Workflow complete: ok={result.ok}")
    print()

    # Display results
    print("5. Results:")
    print("-" * 70)
    print(f"Request ID: {result.request_id}")
    print(f"Status: {'✓ SUCCESS' if result.ok else '✗ FAILED'}")
    print(f"Intent: {result.intent}")
    print(f"Timestamp: {result.timestamp}")
    print(f"Sections: {len(result.sections)}")
    print(f"Citations: {len(result.citations)}")
    print(f"Warnings: {len(result.warnings)}")
    print()

    # Show sections
    for i, section in enumerate(result.sections, 1):
        print(f"\n--- Section {i}: {section.title} ---")
        print(section.body_md[:300])  # First 300 chars
        if len(section.body_md) > 300:
            print("... (truncated)")

    # Show reproducibility
    print("\n" + "-" * 70)
    print("Reproducibility Metadata:")
    print(f"  Method: {result.reproducibility.method}")
    print(f"  Params: {result.reproducibility.params}")
    print(f"  Timestamp: {result.reproducibility.timestamp}")

    print("\n" + "=" * 70)
    print("Demo Complete! ✓")
    print("=" * 70)


if __name__ == "__main__":
    main()
