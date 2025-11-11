"""
Continuity audit trail generation.

Generates audit reports with L19-L22 fields and SHA-256 manifest
of failover actions.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from qnwis.utils.clock import Clock

if TYPE_CHECKING:
    from qnwis.continuity.models import (
        ContinuityPlan,
        FailoverResult,
        VerificationReport,
    )


class ContinuityAuditor:
    """
    Generates audit packs for continuity operations.

    Creates comprehensive audit trails with:
    - L19: Citations (policy, cluster config)
    - L20: Verification results
    - L21: Audit pack with manifest
    - L22: Confidence scoring
    """

    def __init__(self, clock: Clock | None = None, audit_dir: Path | None = None) -> None:
        """
        Initialize continuity auditor.

        Args:
            clock: Clock instance for deterministic time (default: system clock)
            audit_dir: Directory for audit packs (default: audit_packs/)
        """
        self._clock = clock or Clock()
        self._audit_dir = audit_dir or Path("audit_packs")

    def generate_audit_pack(
        self,
        plan: ContinuityPlan,
        result: FailoverResult,
        verification: VerificationReport,
    ) -> dict[str, Any]:
        """
        Generate complete audit pack for failover execution.

        Args:
            plan: Continuity plan
            result: Failover execution result
            verification: Verification report

        Returns:
            Audit pack dictionary
        """
        audit_id = str(uuid.uuid4())
        timestamp = self._clock.utcnow()

        # Build audit pack
        audit_pack = {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "version": "1.0",
            "plan": {
                "plan_id": plan.plan_id,
                "cluster_id": plan.cluster_id,
                "policy_id": plan.policy_id,
                "created_at": plan.created_at,
                "primary_node_id": plan.primary_node_id,
                "failover_target_id": plan.failover_target_id,
                "estimated_total_ms": plan.estimated_total_ms,
                "action_count": len(plan.actions),
            },
            "execution": {
                "execution_id": result.execution_id,
                "started_at": result.started_at,
                "completed_at": result.completed_at,
                "success": result.success,
                "actions_executed": result.actions_executed,
                "actions_failed": result.actions_failed,
                "total_duration_ms": result.total_duration_ms,
                "errors": result.errors,
            },
            "verification": {
                "report_id": verification.report_id,
                "verified_at": verification.verified_at,
                "consistency_ok": verification.consistency_ok,
                "policy_ok": verification.policy_ok,
                "quorum_ok": verification.quorum_ok,
                "freshness_ok": verification.freshness_ok,
                "passed": verification.passed,
                "errors": verification.errors,
                "warnings": verification.warnings,
            },
            "citations": self._generate_citations(plan),
            "confidence": self._calculate_confidence(result, verification),
            "manifest": self._generate_manifest(plan, result),
        }

        # Calculate manifest hash
        manifest_str = json.dumps(audit_pack["manifest"], sort_keys=True)
        manifest_hash = hashlib.sha256(manifest_str.encode()).hexdigest()
        audit_pack["manifest_hash"] = manifest_hash

        return audit_pack

    def save_audit_pack(
        self,
        audit_pack: dict[str, Any],
        pack_dir: Path | None = None,
    ) -> Path:
        """
        Save audit pack to disk.

        Args:
            audit_pack: Audit pack dictionary
            pack_dir: Directory to save pack (default: audit_packs/{audit_id})

        Returns:
            Path to saved audit pack directory
        """
        if pack_dir is None:
            pack_dir = self._audit_dir / audit_pack["audit_id"]

        pack_dir.mkdir(parents=True, exist_ok=True)

        # Save main audit file
        audit_file = pack_dir / "audit.json"
        with audit_file.open("w") as f:
            json.dump(audit_pack, f, indent=2)

        # Save manifest separately
        manifest_file = pack_dir / "manifest.json"
        with manifest_file.open("w") as f:
            json.dump(audit_pack["manifest"], f, indent=2)

        # Save verification report
        verification_file = pack_dir / "verification.json"
        with verification_file.open("w") as f:
            json.dump(audit_pack["verification"], f, indent=2)

        # Create README
        readme_file = pack_dir / "README.md"
        with readme_file.open("w") as f:
            f.write(self._generate_readme(audit_pack))

        return pack_dir

    def _generate_citations(self, plan: ContinuityPlan) -> list[dict[str, str]]:
        """
        Generate L19 citations.

        Args:
            plan: Continuity plan

        Returns:
            List of citation dictionaries
        """
        return [
            {
                "type": "policy",
                "id": plan.policy_id,
                "note": "Failover policy configuration",
            },
            {
                "type": "cluster",
                "id": plan.cluster_id,
                "note": "Cluster topology configuration",
            },
            {
                "type": "plan",
                "id": plan.plan_id,
                "note": "Generated continuity plan",
            },
        ]

    def _calculate_confidence(
        self,
        result: FailoverResult,
        verification: VerificationReport,
    ) -> dict[str, Any]:
        """
        Calculate L22 confidence score.

        Args:
            result: Failover execution result
            verification: Verification report

        Returns:
            Confidence scoring dictionary
        """
        # Base score starts at 100
        score = 100

        # Deduct for failed actions
        if result.actions_failed > 0:
            score -= result.actions_failed * 20

        # Deduct for verification failures
        if not verification.consistency_ok:
            score -= 25
        if not verification.policy_ok:
            score -= 15
        if not verification.quorum_ok:
            score -= 25
        if not verification.freshness_ok:
            score -= 10

        # Deduct for warnings
        score -= len(verification.warnings) * 5

        # Clamp to 0-100
        score = max(0, min(100, score))

        # Determine band
        if score >= 90:
            band = "very_high"
        elif score >= 70:
            band = "high"
        elif score >= 50:
            band = "med"
        else:
            band = "low"

        return {
            "score": score,
            "band": band,
            "components": {
                "execution_success": 100 if result.success else 0,
                "verification_passed": 100 if verification.passed else 0,
                "consistency": 100 if verification.consistency_ok else 0,
                "policy_adherence": 100 if verification.policy_ok else 0,
                "quorum": 100 if verification.quorum_ok else 0,
                "freshness": 100 if verification.freshness_ok else 0,
            },
        }

    def _generate_manifest(
        self,
        plan: ContinuityPlan,
        result: FailoverResult,
    ) -> dict[str, Any]:
        """
        Generate action manifest.

        Args:
            plan: Continuity plan
            result: Failover execution result

        Returns:
            Manifest dictionary
        """
        actions = []
        for action in plan.actions:
            actions.append(
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "target_node_id": action.target_node_id,
                    "sequence": action.sequence,
                    "estimated_duration_ms": action.estimated_duration_ms,
                    "params": action.params,
                }
            )

        return {
            "plan_id": plan.plan_id,
            "execution_id": result.execution_id,
            "actions": actions,
            "metadata": {
                "total_actions": len(actions),
                "actions_executed": result.actions_executed,
                "actions_failed": result.actions_failed,
            },
        }

    def _generate_readme(self, audit_pack: dict[str, Any]) -> str:
        """
        Generate README for audit pack.

        Args:
            audit_pack: Audit pack dictionary

        Returns:
            README content
        """
        return f"""# Continuity Audit Pack

**Audit ID**: {audit_pack['audit_id']}
**Timestamp**: {audit_pack['timestamp']}
**Version**: {audit_pack['version']}

## Execution Summary

- **Plan ID**: {audit_pack['plan']['plan_id']}
- **Cluster ID**: {audit_pack['plan']['cluster_id']}
- **Policy ID**: {audit_pack['plan']['policy_id']}
- **Execution ID**: {audit_pack['execution']['execution_id']}
- **Success**: {audit_pack['execution']['success']}
- **Duration**: {audit_pack['execution']['total_duration_ms']}ms

## Verification

- **Consistency**: {'✓' if audit_pack['verification']['consistency_ok'] else '✗'}
- **Policy**: {'✓' if audit_pack['verification']['policy_ok'] else '✗'}
- **Quorum**: {'✓' if audit_pack['verification']['quorum_ok'] else '✗'}
- **Freshness**: {'✓' if audit_pack['verification']['freshness_ok'] else '✗'}
- **Overall**: {'PASS' if audit_pack['verification']['passed'] else 'FAIL'}

## Confidence Score

- **Score**: {audit_pack['confidence']['score']}/100
- **Band**: {audit_pack['confidence']['band']}

## Files

- `audit.json` - Complete audit pack
- `manifest.json` - Action manifest
- `verification.json` - Verification report
- `README.md` - This file

## Manifest Hash

```
{audit_pack['manifest_hash']}
```

## Citations

{chr(10).join(f"- {c['type']}: {c['id']} - {c['note']}" for c in audit_pack['citations'])}
"""


__all__ = ["ContinuityAuditor"]
