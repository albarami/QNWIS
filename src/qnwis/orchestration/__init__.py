"""
Deterministic orchestration layer for multi-agent council.

This package provides:
- Numeric verification harness for agent outputs
- Consensus synthesis across agent reports
- Council execution with sequential fallback
"""

from .council import CouncilConfig, build_council_graph, run_council
from .synthesis import CouncilReport, synthesize
from .verification import VerificationIssue, VerificationResult, verify_insight, verify_report

__all__ = [
    "CouncilConfig",
    "build_council_graph",
    "run_council",
    "CouncilReport",
    "synthesize",
    "VerificationIssue",
    "VerificationResult",
    "verify_insight",
    "verify_report",
]
