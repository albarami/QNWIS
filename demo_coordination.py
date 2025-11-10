"""
Demo: Coordination Layer with Prefetch and Multi-Agent Execution

This demo shows the coordination layer in action:
1. Prefetcher executes declarative data prefetch
2. Coordinator plans execution waves (single/parallel/sequential)
3. Results are merged deterministically into one report
"""

from src.qnwis.orchestration import (
    Coordinator,
    Prefetcher,
    merge_results,
    CoordinationPolicy,
    get_policy_for_complexity,
)
from src.qnwis.orchestration.types import AgentCallSpec, PrefetchSpec
from src.qnwis.orchestration.schemas import (
    Citation,
    Freshness,
    OrchestrationResult,
    ReportSection,
    Reproducibility,
)
from src.qnwis.orchestration.registry import AgentRegistry


def demo_policy_selection():
    """Demonstrate policy selection based on complexity."""
    print("=" * 60)
    print("DEMO 1: Policy Selection by Complexity")
    print("=" * 60)

    for complexity in ["simple", "medium", "complex", "crisis"]:
        policy = get_policy_for_complexity(complexity)
        print(f"\n{complexity.upper():12} → max_parallel={policy.max_parallel}, "
              f"timeout={policy.per_agent_timeout_ms}ms")

    print()


def demo_execution_planning():
    """Demonstrate execution planning for different modes."""
    print("=" * 60)
    print("DEMO 2: Execution Planning")
    print("=" * 60)

    registry = AgentRegistry()
    policy = CoordinationPolicy(max_parallel=2)
    coordinator = Coordinator(registry, policy)

    # Create sample agent specs
    specs = [
        AgentCallSpec(
            intent="pattern.anomalies",
            method="detect_anomalous_retention",
            params={"months": 12},
        ),
        AgentCallSpec(
            intent="pattern.correlation",
            method="find_correlations",
            params={"months": 12},
        ),
        AgentCallSpec(
            intent="pattern.root_causes",
            method="identify_root_causes",
            params={"months": 12},
        ),
    ]

    # Test different modes
    for mode in ["single", "parallel", "sequential"]:
        if mode == "single":
            test_specs = specs[:1]
        else:
            test_specs = specs

        waves = coordinator.plan("pattern.anomalies", test_specs, mode)
        print(f"\n{mode.upper():12} → {len(waves)} waves: " + 
              ", ".join(f"[{len(wave)} agents]" for wave in waves))

    print()


def demo_result_merging():
    """Demonstrate deterministic result merging."""
    print("=" * 60)
    print("DEMO 3: Deterministic Result Merging")
    print("=" * 60)

    # Create sample results from different agents
    result1 = OrchestrationResult(
        ok=True,
        intent="pattern.anomalies",
        sections=[
            ReportSection(
                title="Executive Summary",
                body_md="Detected anomalous retention in Technology sector (15% above baseline).",
            ),
            ReportSection(
                title="Key Findings",
                body_md="### Finding 1\nRetention dropped 15% in Q4 2023.",
            ),
        ],
        citations=[
            Citation(
                query_id="retention_by_sector",
                dataset_id="lmis_qatari_workforce",
                locator="data/lmis/retention.csv",
                fields=["sector", "retention_rate", "quarter"],
            )
        ],
        freshness={
            "lmis_qatari_workforce": Freshness(
                source="lmis_qatari_workforce",
                last_updated="2024-01-15T00:00:00Z",
            )
        },
        reproducibility=Reproducibility(
            method="PatternDetectiveAgent.detect_anomalous_retention",
            params={"months": 12},
            timestamp="2024-11-06T12:00:00Z",
        ),
        warnings=["Limited data for Q1 2023"],
    )

    result2 = OrchestrationResult(
        ok=True,
        intent="pattern.anomalies",
        sections=[
            ReportSection(
                title="Evidence",
                body_md="- **lmis_qatari_workforce** (retention_by_sector): data/lmis/retention.csv",
            ),
            ReportSection(
                title="Key Findings",
                body_md="### Finding 2\nCorrelation found between salary and retention (r=0.78).",
            ),
        ],
        citations=[
            Citation(
                query_id="salary_retention_correlation",
                dataset_id="lmis_salary_data",
                locator="data/lmis/salaries.csv",
                fields=["sector", "avg_salary", "retention_rate"],
            )
        ],
        freshness={
            "lmis_salary_data": Freshness(
                source="lmis_salary_data",
                last_updated="2024-01-20T00:00:00Z",
            )
        },
        reproducibility=Reproducibility(
            method="PatternDetectiveAgent.find_correlations",
            params={"months": 12},
            timestamp="2024-11-06T12:01:00Z",
        ),
    )

    # Merge results
    merged = merge_results([result1, result2])

    print(f"\nMerged {len([result1, result2])} results:")
    print(f"  - Sections: {len(merged.sections)} (deduplicated, ordered)")
    print(f"  - Citations: {len(merged.citations)} (deduplicated)")
    print(f"  - Freshness: {len(merged.freshness)} sources")
    print(f"  - Warnings: {len(merged.warnings)}")
    print(f"  - Overall OK: {merged.ok}")

    print("\nSection Order:")
    for idx, section in enumerate(merged.sections, 1):
        print(f"  {idx}. {section.title}")

    print("\nCitations (sorted by dataset_id, query_id):")
    for citation in merged.citations:
        print(f"  - {citation.dataset_id} ({citation.query_id})")

    print()


def main():
    """Run all coordination layer demos."""
    print("\n" + "=" * 60)
    print("QNWIS COORDINATION LAYER DEMO")
    print("=" * 60 + "\n")

    demo_policy_selection()
    demo_execution_planning()
    demo_result_merging()

    print("=" * 60)
    print("Demo Complete! ✅")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
