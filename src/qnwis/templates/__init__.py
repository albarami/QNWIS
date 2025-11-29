"""
QNWIS Output Templates.

McKinsey-grade templates for ministerial briefings and reports.
"""

from .ministerial_briefing import (
    MinisterialBriefingTemplate,
    render_executive_summary,
    render_financial_comparison,
    render_sensitivity_matrix,
    render_risk_assessment,
)

__all__ = [
    "MinisterialBriefingTemplate",
    "render_executive_summary",
    "render_financial_comparison",
    "render_sensitivity_matrix",
    "render_risk_assessment",
]

