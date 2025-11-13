"""
Agent Findings Panel for Executive Dashboard (H2).

Organizes and displays findings from multiple LLM agents in a
ministerial-grade format with:
- Agent-specific sections with icons
- Confidence scoring for each insight
- Category organization
- Data citations
- Visual hierarchy

Designed for Qatar Ministry of Labour executive reviews.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentFinding:
    """Represents a single finding from an LLM agent."""

    def __init__(
        self,
        agent_name: str,
        content: str,
        confidence: float,
        category: str = "general",
        data_sources: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize agent finding.

        Args:
            agent_name: Name of the agent (e.g., "LabourEconomist")
            content: Finding content/insight text
            confidence: Confidence score (0.0-1.0)
            category: Category classification
            data_sources: List of data sources used
            metrics: Associated metrics
            timestamp: When finding was generated
        """
        self.agent_name = agent_name
        self.content = content
        self.confidence = max(0.0, min(1.0, confidence))
        self.category = category
        self.data_sources = data_sources or []
        self.metrics = metrics or {}
        self.timestamp = timestamp or datetime.utcnow()

    def render_markdown(self, include_metadata: bool = True) -> str:
        """
        Render finding as markdown.

        Args:
            include_metadata: Whether to include metadata (confidence, sources)

        Returns:
            Markdown-formatted finding
        """
        output = self.content
        
        if include_metadata:
            # Add confidence indicator
            confidence_badge = self._format_confidence_badge()
            output = f"{output} {confidence_badge}"
            
            # Add data sources if available
            if self.data_sources:
                output += "\n\n  *Sources: " + ", ".join(self.data_sources) + "*"
            
            # Add key metrics if available
            if self.metrics:
                output += "\n\n  **Key Metrics:**\n"
                for key, value in list(self.metrics.items())[:3]:  # Top 3 metrics
                    output += f"  - {key}: {value}\n"
        
        return output + "\n"

    def _format_confidence_badge(self) -> str:
        """Format confidence as a badge."""
        if self.confidence >= 0.9:
            return "`🟢 Very High Confidence`"
        elif self.confidence >= 0.75:
            return "`🟢 High Confidence`"
        elif self.confidence >= 0.6:
            return "`🟡 Medium Confidence`"
        elif self.confidence >= 0.4:
            return "`🟠 Moderate Confidence`"
        else:
            return "`🔴 Low Confidence`"


class AgentFindingsPanel:
    """
    Organizes and displays findings from multiple agents.
    
    Provides executive-grade presentation with:
    - Agent-specific sections
    - Category-based organization
    - Confidence filtering
    - Priority sorting
    """

    # Agent metadata
    AGENT_INFO = {
        "LabourEconomist": {
            "icon": "📊",
            "title": "Labour Economist",
            "description": "Employment trends, economic indicators, and labour market analysis"
        },
        "Nationalization": {
            "icon": "🇶🇦",
            "title": "Nationalization Expert",
            "description": "Qatarization progress, GCC benchmarking, and strategic workforce planning"
        },
        "SkillsAgent": {
            "icon": "🎓",
            "title": "Skills Analyst",
            "description": "Skills gaps, education alignment, and workforce development"
        },
        "PatternDetective": {
            "icon": "🔍",
            "title": "Pattern Detective",
            "description": "Data quality, anomaly detection, and trend identification"
        },
        "NationalStrategy": {
            "icon": "🎯",
            "title": "National Strategy Advisor",
            "description": "Vision 2030 alignment, policy recommendations, and strategic priorities"
        }
    }

    def __init__(self):
        """Initialize agent findings panel."""
        self.findings: List[AgentFinding] = []
        self.by_agent: Dict[str, List[AgentFinding]] = {}
        self.by_category: Dict[str, List[AgentFinding]] = {}

    def add_finding(self, finding: AgentFinding) -> None:
        """
        Add a finding to the panel.

        Args:
            finding: AgentFinding instance
        """
        self.findings.append(finding)
        
        # Index by agent
        if finding.agent_name not in self.by_agent:
            self.by_agent[finding.agent_name] = []
        self.by_agent[finding.agent_name].append(finding)
        
        # Index by category
        if finding.category not in self.by_category:
            self.by_category[finding.category] = []
        self.by_category[finding.category].append(finding)
        
        logger.debug(
            f"Added finding from {finding.agent_name} "
            f"(category: {finding.category}, confidence: {finding.confidence:.2f})"
        )

    def render_by_agent(
        self,
        min_confidence: float = 0.0,
        max_findings_per_agent: Optional[int] = None
    ) -> str:
        """
        Render findings organized by agent.

        Args:
            min_confidence: Minimum confidence threshold
            max_findings_per_agent: Maximum findings to show per agent

        Returns:
            Markdown-formatted agent findings
        """
        if not self.findings:
            return "No findings available."

        output = "## 🤖 Agent Analysis\n\n"
        
        # Preferred agent order
        agent_order = [
            "LabourEconomist",
            "Nationalization",
            "SkillsAgent",
            "NationalStrategy",
            "PatternDetective"
        ]
        
        for agent_name in agent_order:
            if agent_name in self.by_agent:
                agent_findings = self.by_agent[agent_name]
                
                # Filter by confidence
                filtered = [f for f in agent_findings if f.confidence >= min_confidence]
                
                if not filtered:
                    continue
                
                # Sort by confidence
                filtered.sort(key=lambda x: x.confidence, reverse=True)
                
                # Limit number of findings
                if max_findings_per_agent:
                    filtered = filtered[:max_findings_per_agent]
                
                # Get agent info
                info = self.AGENT_INFO.get(agent_name, {
                    "icon": "🤖",
                    "title": agent_name,
                    "description": ""
                })
                
                # Render agent section
                output += f"### {info['icon']} {info['title']}\n\n"
                if info['description']:
                    output += f"*{info['description']}*\n\n"
                
                for idx, finding in enumerate(filtered, 1):
                    output += f"{idx}. {finding.render_markdown()}\n"
                
                output += "---\n\n"
        
        # Handle unrecognized agents
        unrecognized = [a for a in self.by_agent.keys() if a not in agent_order]
        for agent_name in unrecognized:
            agent_findings = self.by_agent[agent_name]
            filtered = [f for f in agent_findings if f.confidence >= min_confidence]
            
            if filtered:
                filtered.sort(key=lambda x: x.confidence, reverse=True)
                if max_findings_per_agent:
                    filtered = filtered[:max_findings_per_agent]
                
                output += f"### 🤖 {agent_name}\n\n"
                for idx, finding in enumerate(filtered, 1):
                    output += f"{idx}. {finding.render_markdown()}\n"
                output += "---\n\n"
        
        return output

    def render_by_category(self, min_confidence: float = 0.0) -> str:
        """
        Render findings organized by category.

        Args:
            min_confidence: Minimum confidence threshold

        Returns:
            Markdown-formatted category findings
        """
        if not self.findings:
            return "No findings available."

        output = "## 📂 Findings by Category\n\n"
        
        # Category metadata
        category_info = {
            "unemployment": ("📉", "Unemployment Analysis"),
            "qatarization": ("🇶🇦", "Qatarization Progress"),
            "gcc_comparison": ("🌍", "GCC Benchmarking"),
            "skills": ("🎓", "Skills & Education"),
            "gender": ("⚖️", "Gender Analysis"),
            "vision_2030": ("🎯", "Vision 2030 Alignment"),
            "retention": ("🔄", "Workforce Retention"),
            "salary": ("💰", "Compensation Analysis"),
            "general": ("📊", "General Insights")
        }
        
        for category, (icon, title) in category_info.items():
            if category in self.by_category:
                findings = self.by_category[category]
                
                # Filter by confidence
                filtered = [f for f in findings if f.confidence >= min_confidence]
                
                if not filtered:
                    continue
                
                # Sort by confidence
                filtered.sort(key=lambda x: x.confidence, reverse=True)
                
                output += f"### {icon} {title}\n\n"
                
                for finding in filtered:
                    agent_icon = self.AGENT_INFO.get(finding.agent_name, {}).get("icon", "🤖")
                    output += f"**{agent_icon} {finding.agent_name}**: "
                    output += finding.render_markdown()
                    output += "\n"
                
                output += "---\n\n"
        
        return output

    def get_top_findings(
        self,
        n: int = 5,
        min_confidence: float = 0.6
    ) -> List[AgentFinding]:
        """
        Get top N findings by confidence.

        Args:
            n: Number of findings to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of top AgentFinding instances
        """
        filtered = [f for f in self.findings if f.confidence >= min_confidence]
        filtered.sort(key=lambda x: x.confidence, reverse=True)
        return filtered[:n]

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics about findings.

        Returns:
            Dictionary of statistics
        """
        if not self.findings:
            return {}

        return {
            "total_findings": len(self.findings),
            "agents_count": len(self.by_agent),
            "categories_count": len(self.by_category),
            "avg_confidence": sum(f.confidence for f in self.findings) / len(self.findings),
            "high_confidence_count": len([f for f in self.findings if f.confidence >= 0.75]),
            "agents": list(self.by_agent.keys()),
            "categories": list(self.by_category.keys())
        }

    def render_summary(self) -> str:
        """
        Render summary of findings panel.

        Returns:
            Markdown-formatted summary
        """
        stats = self.get_summary_stats()
        
        if not stats:
            return "No findings available for summary."

        output = "## 📋 Analysis Summary\n\n"
        output += f"**Total Findings:** {stats['total_findings']}\n\n"
        output += f"**Agents Consulted:** {stats['agents_count']} "
        output += f"({', '.join(stats['agents'])})\n\n"
        output += f"**Categories Analyzed:** {stats['categories_count']} "
        output += f"({', '.join(stats['categories'])})\n\n"
        output += f"**Average Confidence:** {stats['avg_confidence']:.1%}\n\n"
        output += f"**High Confidence Insights:** {stats['high_confidence_count']} "
        output += f"({stats['high_confidence_count']/stats['total_findings']*100:.0f}%)\n\n"
        
        return output


def parse_agent_output_to_findings(
    agent_name: str,
    output: str,
    default_confidence: float = 0.75
) -> List[AgentFinding]:
    """
    Parse agent markdown output into structured findings.

    Args:
        agent_name: Name of the agent
        output: Raw markdown output from agent
        default_confidence: Default confidence if not specified

    Returns:
        List of AgentFinding instances
    """
    findings = []
    lines = output.split('\n')
    
    current_finding = []
    current_category = "general"
    
    for line in lines:
        line_stripped = line.strip()
        
        # Detect category headers
        if line_stripped.startswith('##') and not line_stripped.startswith('###'):
            current_category = _extract_category_from_header(line_stripped)
            continue
        
        # Detect findings (bullet points or numbered lists)
        if line_stripped.startswith(('-', '*', '•')) or \
           any(line_stripped.startswith(f'{i}.') for i in range(1, 10)):
            
            # Save previous finding
            if current_finding:
                content = ' '.join(current_finding)
                if len(content) > 15:  # Ignore very short findings
                    findings.append(AgentFinding(
                        agent_name=agent_name,
                        content=content,
                        confidence=default_confidence,
                        category=current_category
                    ))
            
            # Start new finding
            current_finding = [line_stripped.lstrip('-*•123456789. ')]
        
        elif current_finding and line_stripped:
            # Continue current finding
            current_finding.append(line_stripped)
    
    # Save last finding
    if current_finding:
        content = ' '.join(current_finding)
        if len(content) > 15:
            findings.append(AgentFinding(
                agent_name=agent_name,
                content=content,
                confidence=default_confidence,
                category=current_category
            ))
    
    logger.info(f"Parsed {len(findings)} findings from {agent_name}")
    return findings


def _extract_category_from_header(header: str) -> str:
    """Extract category from markdown header."""
    header_lower = header.lower()
    
    if 'unemploy' in header_lower:
        return 'unemployment'
    elif 'qatari' in header_lower or 'national' in header_lower:
        return 'qatarization'
    elif 'gcc' in header_lower or 'gulf' in header_lower:
        return 'gcc_comparison'
    elif 'skill' in header_lower or 'education' in header_lower:
        return 'skills'
    elif 'gender' in header_lower or 'women' in header_lower:
        return 'gender'
    elif 'vision' in header_lower or '2030' in header_lower:
        return 'vision_2030'
    elif 'retention' in header_lower or 'attrition' in header_lower:
        return 'retention'
    elif 'salary' in header_lower or 'wage' in header_lower or 'compensation' in header_lower:
        return 'salary'
    else:
        return 'general'
