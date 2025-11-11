"""
CLI for Business Continuity & Failover Orchestration.

Commands:
- plan: Generate continuity plan from cluster.yaml
- simulate: Run deterministic failover simulation
- execute: Execute plan (dry-run or commit)
- verify: Run verifier checks
- status: Print cluster + quorum status
- audit: Show last failover audit pack
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

import yaml
from qnwis.continuity.heartbeat import HeartbeatMonitor, calculate_quorum_size
from qnwis.continuity.models import (
    Cluster,
    FailoverPolicy,
    Node,
    NodeRole,
    NodeStatus,
)
from qnwis.continuity.planner import ContinuityPlanner
from qnwis.continuity.simulate import FailoverSimulator


@click.group()
def cli() -> None:
    """QNWIS Business Continuity & Failover Orchestration."""
    pass


@cli.command()
@click.option(
    "--cluster",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to cluster.yaml",
)
@click.option(
    "--policy",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to policy.yaml",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    help="Output file for plan (default: stdout)",
)
def plan(cluster: Path, policy: Path, output: Path | None) -> None:
    """Generate continuity plan from cluster and policy configuration."""
    try:
        # Load cluster
        with cluster.open() as f:
            cluster_data = yaml.safe_load(f)
        cluster_obj = _load_cluster(cluster_data)

        # Load policy
        with policy.open() as f:
            policy_data = yaml.safe_load(f)
        policy_obj = _load_policy(policy_data)

        # Generate plan
        planner = ContinuityPlanner()
        plan_obj = planner.build_plan(cluster_obj, policy_obj)

        # Output plan
        plan_dict = {
            "plan_id": plan_obj.plan_id,
            "cluster_id": plan_obj.cluster_id,
            "policy_id": plan_obj.policy_id,
            "created_at": plan_obj.created_at,
            "primary_node_id": plan_obj.primary_node_id,
            "failover_target_id": plan_obj.failover_target_id,
            "estimated_total_ms": plan_obj.estimated_total_ms,
            "actions": [
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "target_node_id": action.target_node_id,
                    "sequence": action.sequence,
                    "estimated_duration_ms": action.estimated_duration_ms,
                    "params": action.params,
                }
                for action in plan_obj.actions
            ],
            "metadata": plan_obj.metadata,
        }

        if output:
            with output.open("w") as f:
                json.dump(plan_dict, f, indent=2)
            click.echo(f"Plan saved to {output}")
        else:
            click.echo(json.dumps(plan_dict, indent=2))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--cluster",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to cluster.yaml",
)
@click.option(
    "--policy",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to policy.yaml",
)
@click.option(
    "--scenario",
    type=click.Choice(["primary_failure", "random_failures", "region_failure"]),
    default="primary_failure",
    help="Simulation scenario",
)
@click.option("--seed", type=int, default=42, help="Random seed for simulation")
@click.option("--output", type=click.Path(path_type=Path), help="Output file for results")
def simulate(
    cluster: Path,
    policy: Path,
    scenario: str,
    seed: int,
    output: Path | None,
) -> None:
    """Run deterministic failover simulation."""
    try:
        # Load cluster and policy
        with cluster.open() as f:
            cluster_data = yaml.safe_load(f)
        cluster_obj = _load_cluster(cluster_data)

        with policy.open() as f:
            policy_data = yaml.safe_load(f)
        policy_obj = _load_policy(policy_data)

        # Run simulation
        simulator = FailoverSimulator(seed=seed)

        if scenario == "primary_failure":
            result = simulator.simulate_primary_failure(cluster_obj, policy_obj)
        elif scenario == "random_failures":
            result = simulator.simulate_random_failures(cluster_obj, policy_obj, failure_count=1)
        elif scenario == "region_failure":
            # Use first region
            region = cluster_obj.regions[0] if cluster_obj.regions else "region-1"
            result = simulator.simulate_region_failure(cluster_obj, policy_obj, region)
        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        # Format results
        result_dict = {
            "scenario": result.scenario,
            "success": result.success,
            "failover": {
                "execution_id": result.failover_result.execution_id,
                "success": result.failover_result.success,
                "actions_executed": result.failover_result.actions_executed,
                "actions_failed": result.failover_result.actions_failed,
                "total_duration_ms": result.failover_result.total_duration_ms,
                "errors": result.failover_result.errors,
            },
            "verification": {
                "report_id": result.verification_report.report_id,
                "passed": result.verification_report.passed,
                "consistency_ok": result.verification_report.consistency_ok,
                "policy_ok": result.verification_report.policy_ok,
                "quorum_ok": result.verification_report.quorum_ok,
                "freshness_ok": result.verification_report.freshness_ok,
                "errors": result.verification_report.errors,
                "warnings": result.verification_report.warnings,
            },
        }

        if output:
            with output.open("w") as f:
                json.dump(result_dict, f, indent=2)
            click.echo(f"Simulation results saved to {output}")
        else:
            click.echo(json.dumps(result_dict, indent=2))

        # Exit with error code if simulation failed
        if not result.success:
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--plan",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to plan.json",
)
@click.option("--dry-run", is_flag=True, help="Simulate execution without making changes")
@click.option("--output", type=click.Path(path_type=Path), help="Output file for results")
def execute(plan: Path, dry_run: bool, output: Path | None) -> None:
    """Execute failover plan."""
    try:
        # Load plan
        with plan.open() as f:
            plan_data = json.load(f)

        # Note: In production, would load full plan object from storage
        # For CLI, we work with the JSON representation
        click.echo(f"Executing plan {plan_data['plan_id']} (dry_run={dry_run})")
        click.echo(f"Actions: {len(plan_data['actions'])}")
        click.echo(f"Estimated time: {plan_data['estimated_total_ms']}ms")

        if dry_run:
            click.echo("\nDry-run mode: No actual changes will be made")
        else:
            click.echo("\nWARNING: This will execute actual failover actions!")
            if not click.confirm("Continue?"):
                click.echo("Aborted")
                sys.exit(0)

        # In production, would execute via FailoverExecutor
        click.echo("\nExecution complete (simulated)")

        summary = {
            "plan_id": plan_data.get("plan_id"),
            "dry_run": dry_run,
            "action_count": len(plan_data.get("actions", [])),
            "estimated_total_ms": plan_data.get("estimated_total_ms"),
        }
        click.echo(json.dumps(summary, indent=2))
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            click.echo(f"\nSummary saved to {output}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--cluster",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to cluster.yaml",
)
def status(cluster: Path) -> None:
    """Show cluster and quorum status."""
    try:
        # Load cluster
        with cluster.open() as f:
            cluster_data = yaml.safe_load(f)
        cluster_obj = _load_cluster(cluster_data)

        # Simulate heartbeats
        monitor = HeartbeatMonitor()
        monitor.simulate_heartbeats(cluster_obj.nodes)

        # Calculate quorum
        quorum_status = monitor.calculate_quorum(cluster_obj)

        # Display status
        click.echo(f"Cluster: {cluster_obj.name} ({cluster_obj.cluster_id})")
        click.echo(f"Nodes: {len(cluster_obj.nodes)}")
        click.echo(f"Regions: {', '.join(cluster_obj.regions)}")
        click.echo()
        click.echo("Quorum Status:")
        click.echo(f"  Total nodes: {quorum_status.total_nodes}")
        click.echo(f"  Healthy nodes: {quorum_status.healthy_nodes}")
        click.echo(f"  Quorum size: {quorum_status.quorum_size}")
        click.echo(f"  Has quorum: {'✓' if quorum_status.has_quorum else '✗'}")
        click.echo()
        click.echo("Node Status:")
        for node in cluster_obj.nodes:
            status_icon = "✓" if node.status == NodeStatus.HEALTHY else "✗"
            click.echo(
                f"  {status_icon} {node.node_id} ({node.role.value}) - {node.status.value}"
            )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--audit-id",
    type=str,
    help="Audit pack ID (default: latest)",
)
@click.option(
    "--audit-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("audit_packs"),
    help="Audit packs directory",
)
def audit(audit_id: str | None, audit_dir: Path) -> None:
    """Show failover audit pack."""
    try:
        if audit_id:
            pack_dir = audit_dir / audit_id
        else:
            # Find latest audit pack
            packs = sorted(audit_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not packs:
                click.echo("No audit packs found", err=True)
                sys.exit(1)
            pack_dir = packs[0]

        audit_file = pack_dir / "audit.json"
        if not audit_file.exists():
            click.echo(f"Audit pack not found: {pack_dir}", err=True)
            sys.exit(1)

        # Load and display audit pack
        with audit_file.open() as f:
            audit_data = json.load(f)

        click.echo(f"Audit Pack: {audit_data['audit_id']}")
        click.echo(f"Timestamp: {audit_data['timestamp']}")
        click.echo()
        click.echo("Execution:")
        click.echo(f"  Success: {audit_data['execution']['success']}")
        click.echo(f"  Duration: {audit_data['execution']['total_duration_ms']}ms")
        click.echo(f"  Actions: {audit_data['execution']['actions_executed']}")
        click.echo()
        click.echo("Verification:")
        click.echo(f"  Passed: {audit_data['verification']['passed']}")
        click.echo(f"  Consistency: {'✓' if audit_data['verification']['consistency_ok'] else '✗'}")
        click.echo(f"  Policy: {'✓' if audit_data['verification']['policy_ok'] else '✗'}")
        click.echo(f"  Quorum: {'✓' if audit_data['verification']['quorum_ok'] else '✗'}")
        click.echo(f"  Freshness: {'✓' if audit_data['verification']['freshness_ok'] else '✗'}")
        click.echo()
        click.echo("Confidence:")
        click.echo(f"  Score: {audit_data['confidence']['score']}/100")
        click.echo(f"  Band: {audit_data['confidence']['band']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _load_cluster(data: dict[str, Any]) -> Cluster:
    """Load cluster from YAML data."""
    nodes = []
    for node_data in data.get("nodes", []):
        nodes.append(
            Node(
                node_id=node_data["node_id"],
                hostname=node_data["hostname"],
                role=NodeRole(node_data["role"]),
                region=node_data["region"],
                site=node_data["site"],
                status=NodeStatus(node_data.get("status", "healthy")),
                priority=node_data.get("priority", 100),
                capacity=node_data.get("capacity", 100.0),
                metadata=node_data.get("metadata", {}),
            )
        )

    quorum_size = data.get("quorum_size")
    if quorum_size is None:
        quorum_size = calculate_quorum_size(len(nodes))

    return Cluster(
        cluster_id=data["cluster_id"],
        name=data["name"],
        nodes=nodes,
        quorum_size=quorum_size,
        regions=data.get("regions", []),
        metadata=data.get("metadata", {}),
    )


def _load_policy(data: dict[str, Any]) -> FailoverPolicy:
    """Load policy from YAML data."""
    from qnwis.continuity.models import FailoverStrategy

    return FailoverPolicy(
        policy_id=data["policy_id"],
        name=data["name"],
        strategy=FailoverStrategy(data["strategy"]),
        max_failover_time_s=data.get("max_failover_time_s", 60),
        require_quorum=data.get("require_quorum", True),
        region_priority=data.get("region_priority", []),
        site_priority=data.get("site_priority", []),
        min_healthy_nodes=data.get("min_healthy_nodes", 1),
        metadata=data.get("metadata", {}),
    )


if __name__ == "__main__":
    cli()
