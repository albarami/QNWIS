"""
Cross-source numeric verification for QNWIS.

Includes:
- Layer 1: Numeric validation rules and triangulation (existing)
- Layer 2: Cross-source metric verification
- Layer 3: Privacy/PII redaction and policy enforcement
- Layer 4: Sanity checks (ranges, freshness, consistency)
"""

from .engine import VerificationEngine
from .schemas import (
    CrossCheckRule,
    Issue,
    PrivacyRule,
    SanityRule,
    VerificationConfig,
    VerificationSummary,
)

__all__ = [
    "VerificationEngine",
    "VerificationConfig",
    "VerificationSummary",
    "Issue",
    "CrossCheckRule",
    "PrivacyRule",
    "SanityRule",
]
