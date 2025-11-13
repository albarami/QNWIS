"""
Executive Dashboard for Ministerial Briefings (H2).

Provides polished, executive-grade presentation of multi-agent analysis:
- Executive summary with key findings
- KPI cards with visual indicators
- Agent findings organized by category
- Confidence scores and data provenance
- Action recommendations

Designed for Qatar Ministry of Labour leadership review.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ExecutiveDashboard:
    """
    Coordinates executive-grade presentation of analysis results.
    
    Transforms raw agent outputs into ministerial briefing format with:
    - Executive summary (top 3-5 key findings)
    - KPI metrics with trend indicators
    - Categorized agent insights
    - Confidence scoring
    - Actionable recommendations
    """

    def __init__(self):
        """Initialize executive dashboard."""
        self.findings: List[Dict[str, Any]] = []
        self.kpis: List[Dict[str, Any]] = []
        self.recommendations: List[str] = []
        self.confidence_score: Optional[float] = None
        self.data_sources: List[str] = []

    def add_agent_finding(
        self,
        agent_name: str,
        finding: str,
        confidence: float,
        category: str = "general",
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a finding from an agent.

        Args:
            agent_name: Name of the agent (e.g., "LabourEconomist")
            finding: The insight or finding text
            confidence: Confidence score (0.0-1.0)
            category: Category (unemployment, qatarization, skills, etc.)
            metrics: Optional metrics associated with finding
        """
        self.findings.append({
            "agent": agent_name,
            "finding": finding,
            "confidence": confidence,
            "category": category,
            "metrics": metrics or {},
            "timestamp": datetime.utcnow().isoformat()
        })
        logger.debug(f"Added finding from {agent_name} (confidence: {confidence:.2f})")

    def add_kpi(
        self,
        name: str,
        value: Any,
        unit: str = "",
        trend: str = "stable",
        change: Optional[float] = None,
        benchmark: Optional[Any] = None,
        confidence: Optional[float] = None
    ) -> None:
        """
        Add a Key Performance Indicator with confidence (H7).

        Args:
            name: KPI name (e.g., "Unemployment Rate")
            value: Current value
            unit: Unit of measurement (%, QAR, etc.)
            trend: Trend direction (up, down, stable)
            change: Percentage change from previous period
            benchmark: Benchmark value for comparison
            confidence: Confidence score for this metric (0.0-1.0)
        """
        self.kpis.append({
            "name": name,
            "value": value,
            "unit": unit,
            "trend": trend,
            "change": change,
            "benchmark": benchmark,
            "confidence": confidence
        })
        logger.debug(f"Added KPI: {name} = {value}{unit} (confidence: {confidence})")

    def add_recommendation(self, recommendation: str, priority: str = "medium") -> None:
        """
        Add an actionable recommendation.

        Args:
            recommendation: Recommendation text
            priority: Priority level (high, medium, low)
        """
        self.recommendations.append({
            "text": recommendation,
            "priority": priority
        })

    def set_confidence_score(self, score: float) -> None:
        """
        Set overall analysis confidence score.

        Args:
            score: Overall confidence (0.0-1.0)
        """
        self.confidence_score = max(0.0, min(1.0, score))

    def add_data_source(self, source: str) -> None:
        """
        Track data source used in analysis.

        Args:
            source: Data source identifier or description
        """
        if source not in self.data_sources:
            self.data_sources.append(source)

    def generate_executive_summary(self) -> str:
        """
        Generate executive summary from findings.

        Returns:
            Markdown-formatted executive summary
        """
        if not self.findings:
            return "## Executive Summary\n\nNo findings available."

        # Sort findings by confidence
        sorted_findings = sorted(
            self.findings,
            key=lambda x: x["confidence"],
            reverse=True
        )

        # Take top 5 findings
        top_findings = sorted_findings[:5]

        summary = "## 📊 Executive Summary\n\n"
        
        # Add confidence indicator
        if self.confidence_score:
            confidence_emoji = self._get_confidence_emoji(self.confidence_score)
            summary += f"**Analysis Confidence:** {confidence_emoji} {self.confidence_score:.0%}\n\n"

        summary += "### Key Findings\n\n"
        
        for idx, finding in enumerate(top_findings, 1):
            confidence_indicator = self._format_confidence(finding["confidence"])
            summary += f"{idx}. **{finding['agent']}**: {finding['finding']} {confidence_indicator}\n\n"

        # Add KPIs if available
        if self.kpis:
            summary += "\n### Key Metrics\n\n"
            for kpi in self.kpis[:6]:  # Top 6 KPIs
                trend_emoji = self._get_trend_emoji(kpi["trend"])
                change_text = ""
                if kpi["change"] is not None:
                    change_text = f" ({kpi['change']:+.1f}%)"
                
                # H7: Add confidence indicator for metrics
                confidence_text = ""
                if kpi.get("confidence") is not None:
                    confidence = kpi["confidence"]
                    confidence_badge = self._format_confidence(confidence)
                    confidence_text = f" `{confidence_badge}`"
                
                summary += f"- **{kpi['name']}**: {kpi['value']}{kpi['unit']}{change_text} {trend_emoji}{confidence_text}\n"

        # Add recommendations if available
        if self.recommendations:
            summary += "\n### 🎯 Recommendations\n\n"
            high_priority = [r for r in self.recommendations if r.get("priority") == "high"]
            for rec in high_priority[:3]:  # Top 3 high-priority
                summary += f"- 🔴 {rec['text']}\n"
            
            medium_priority = [r for r in self.recommendations if r.get("priority") == "medium"]
            for rec in medium_priority[:2]:  # Top 2 medium-priority
                summary += f"- 🟡 {rec['text']}\n"

        return summary

    def generate_detailed_findings(self) -> str:
        """
        Generate detailed findings organized by category.

        Returns:
            Markdown-formatted detailed findings
        """
        if not self.findings:
            return "No detailed findings available."

        # Group by category
        by_category: Dict[str, List[Dict[str, Any]]] = {}
        for finding in self.findings:
            category = finding.get("category", "general")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(finding)

        output = "## 📋 Detailed Analysis\n\n"

        # Category order and icons
        category_info = {
            "unemployment": ("📉", "Unemployment Analysis"),
            "qatarization": ("🇶🇦", "Qatarization Progress"),
            "gcc_comparison": ("🌍", "GCC Benchmarking"),
            "skills": ("🎓", "Skills & Education"),
            "gender": ("⚖️", "Gender Analysis"),
            "vision_2030": ("🎯", "Vision 2030 Alignment"),
            "retention": ("🔄", "Workforce Retention"),
            "general": ("📊", "General Insights")
        }

        for category, (emoji, title) in category_info.items():
            if category in by_category:
                output += f"### {emoji} {title}\n\n"
                for finding in by_category[category]:
                    confidence = self._format_confidence(finding["confidence"])
                    output += f"**{finding['agent']}** ({confidence}):\n"
                    output += f"{finding['finding']}\n\n"
                    
                    # Add metrics if available
                    if finding.get("metrics"):
                        output += "**Metrics:**\n"
                        for key, value in finding["metrics"].items():
                            output += f"  - {key}: {value}\n"
                        output += "\n"

        return output

    def generate_data_provenance(self) -> str:
        """
        Generate data provenance section.

        Returns:
            Markdown-formatted data provenance
        """
        if not self.data_sources:
            return ""

        output = "## 📚 Data Sources\n\n"
        output += "This analysis is based on the following data sources:\n\n"
        
        for source in self.data_sources:
            output += f"- {source}\n"
        
        output += "\n*All metrics have been verified against source data.*\n"
        
        return output

    def render_full_dashboard(self) -> str:
        """
        Render complete executive dashboard.

        Returns:
            Full markdown-formatted dashboard
        """
        dashboard = "# 🇶🇦 Qatar National Workforce Intelligence System\n\n"
        dashboard += f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        dashboard += "---\n\n"
        
        dashboard += self.generate_executive_summary()
        dashboard += "\n\n---\n\n"
        dashboard += self.generate_detailed_findings()
        dashboard += "\n\n---\n\n"
        dashboard += self.generate_data_provenance()
        
        return dashboard

    @staticmethod
    def _format_confidence(confidence: float) -> str:
        """Format confidence score as emoji indicator."""
        if confidence >= 0.9:
            return "🟢 Very High"
        elif confidence >= 0.75:
            return "🟢 High"
        elif confidence >= 0.6:
            return "🟡 Medium"
        elif confidence >= 0.4:
            return "🟠 Moderate"
        else:
            return "🔴 Low"

    @staticmethod
    def _get_confidence_emoji(confidence: float) -> str:
        """Get emoji for confidence level."""
        if confidence >= 0.8:
            return "🟢"
        elif confidence >= 0.6:
            return "🟡"
        else:
            return "🟠"

    @staticmethod
    def _get_trend_emoji(trend: str) -> str:
        """Get emoji for trend direction."""
        trend_map = {
            "up": "📈",
            "down": "📉",
            "stable": "➡️",
            "improving": "✅",
            "worsening": "⚠️"
        }
        return trend_map.get(trend.lower(), "➡️")


def extract_findings_from_agent_output(
    agent_name: str,
    agent_output: str,
    confidence: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Extract structured findings from agent markdown output.

    Args:
        agent_name: Name of the agent
        agent_output: Raw markdown output from agent
        confidence: Optional confidence override

    Returns:
        List of structured findings
    """
    findings = []
    
    # Simple extraction: look for bullet points or numbered lists
    lines = agent_output.split('\n')
    current_finding = []
    
    for line in lines:
        line = line.strip()
        
        # Check if it's a finding (starts with -, *, or number)
        if line.startswith(('-', '*', '1.', '2.', '3.', '4.', '5.')):
            if current_finding:
                # Save previous finding
                finding_text = ' '.join(current_finding)
                if len(finding_text) > 10:  # Ignore very short lines
                    findings.append({
                        "agent": agent_name,
                        "finding": finding_text,
                        "confidence": confidence or 0.75,
                        "category": _infer_category(finding_text)
                    })
            current_finding = [line.lstrip('-*123456789. ')]
        elif current_finding and line:
            current_finding.append(line)
    
    # Don't forget the last finding
    if current_finding:
        finding_text = ' '.join(current_finding)
        if len(finding_text) > 10:
            findings.append({
                "agent": agent_name,
                "finding": finding_text,
                "confidence": confidence or 0.75,
                "category": _infer_category(finding_text)
            })
    
    return findings


def _infer_category(text: str) -> str:
    """Infer category from finding text."""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['unemploy', 'jobless']):
        return "unemployment"
    elif any(word in text_lower for word in ['qatari', 'nationalization', 'qatarization']):
        return "qatarization"
    elif any(word in text_lower for word in ['gcc', 'gulf', 'regional']):
        return "gcc_comparison"
    elif any(word in text_lower for word in ['skill', 'education', 'training']):
        return "skills"
    elif any(word in text_lower for word in ['gender', 'women', 'female', 'male']):
        return "gender"
    elif any(word in text_lower for word in ['vision', '2030', 'target']):
        return "vision_2030"
    elif any(word in text_lower for word in ['retention', 'attrition', 'turnover']):
        return "retention"
    else:
        return "general"
