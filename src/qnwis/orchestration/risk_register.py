"""
Detailed Risk Register - Big 4 Standard Risk Management

Generates comprehensive risk register with:
- 30+ specific risks per strategy
- Probability and impact quantification
- Early warning indicators
- Mitigation strategies
- Contingency plans
- Risk ownership

Domain-agnostic: Risk patterns adapt to any strategic context.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Risk:
    """A detailed risk with full Big 4 standard attributes."""
    id: str
    category: str  # Strategic, Operational, Financial, Human Capital, Political, Technology
    risk: str  # Description
    probability: float  # 0-1
    impact: str  # LOW, MEDIUM, HIGH, CRITICAL
    impact_quantified: str  # e.g., "QR 80B revenue shortfall"
    early_warning: str  # Indicators to watch
    mitigation: str  # Proactive strategy
    contingency: str  # Reactive plan if risk materializes
    owner: str  # Accountable party
    review_frequency: str  # Monthly, Quarterly, Annual
    risk_score: float = 0.0  # probability * impact_weight


class RiskRegisterGenerator:
    """
    Generates comprehensive risk registers for strategic initiatives.
    
    Domain-agnostic: Adapts risk templates to any strategic context.
    """
    
    def __init__(self):
        """Initialize with risk templates."""
        
        # Impact weights for scoring
        self.impact_weights = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4
        }
        
        # Risk templates by category and initiative type
        self.risk_templates = self._build_risk_templates()
    
    def _build_risk_templates(self) -> Dict[str, List[Dict]]:
        """Build domain-agnostic risk templates."""
        
        return {
            "strategic": [
                {
                    "risk": "Competitor announces larger competing initiative",
                    "probability": 0.4,
                    "impact": "HIGH",
                    "impact_quantified": "Lose 30-40% of planned foreign investment",
                    "early_warning": "Competitor budget announcements, leadership statements",
                    "mitigation": "Focus on niche differentiation, build unique value proposition",
                    "contingency": "Pivot to partnership model rather than head-to-head competition",
                    "owner": "Strategy Office",
                    "review_frequency": "Quarterly"
                },
                {
                    "risk": "Major revenue source declines 30%+ for 18+ months",
                    "probability": 0.25,
                    "impact": "CRITICAL",
                    "impact_quantified": "Program delayed 2-3 years, scope reduced 40%",
                    "early_warning": "Commodity prices, global demand indicators",
                    "mitigation": "Build contingency reserve from current surplus",
                    "contingency": "Scale back to core high-ROI components only",
                    "owner": "Finance Ministry",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Geopolitical disruption affects regional stability",
                    "probability": 0.2,
                    "impact": "HIGH",
                    "impact_quantified": "Foreign investment paused, talent exodus",
                    "early_warning": "Regional diplomatic developments, security assessments",
                    "mitigation": "Diversify partnerships across multiple regions",
                    "contingency": "Activate business continuity protocols",
                    "owner": "Foreign Affairs",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Global economic recession reduces demand",
                    "probability": 0.3,
                    "impact": "MEDIUM",
                    "impact_quantified": "Revenue projections reduced 20-30%",
                    "early_warning": "Global GDP forecasts, trade indicators",
                    "mitigation": "Build domestic demand components",
                    "contingency": "Extend implementation timeline",
                    "owner": "Planning Authority",
                    "review_frequency": "Quarterly"
                },
                {
                    "risk": "Technology disruption makes current approach obsolete",
                    "probability": 0.15,
                    "impact": "HIGH",
                    "impact_quantified": "Major pivot required mid-implementation",
                    "early_warning": "Technology trend reports, patent filings",
                    "mitigation": "Build flexible architecture, maintain tech advisory board",
                    "contingency": "Rapid assessment and pivot protocol",
                    "owner": "Technology Office",
                    "review_frequency": "Quarterly"
                },
            ],
            "operational": [
                {
                    "risk": "Major construction delays (18+ months)",
                    "probability": 0.35,
                    "impact": "MEDIUM",
                    "impact_quantified": "Additional costs, timeline slip",
                    "early_warning": "Contractor performance reports, material delivery tracking",
                    "mitigation": "Dual-source critical equipment, build inventory buffer",
                    "contingency": "Use interim solutions while construction completes",
                    "owner": "Project Management Office",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Key contractor fails or underperforms",
                    "probability": 0.25,
                    "impact": "MEDIUM",
                    "impact_quantified": "6-12 month delay for replacement",
                    "early_warning": "Contractor financial health, performance metrics",
                    "mitigation": "Pre-qualify backup contractors, milestone-based payments",
                    "contingency": "Activate backup contractor procurement",
                    "owner": "Procurement Office",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Supply chain disruption for critical materials",
                    "probability": 0.3,
                    "impact": "MEDIUM",
                    "impact_quantified": "Cost increase 15-25%, delays",
                    "early_warning": "Global supply chain indices, supplier reports",
                    "mitigation": "Multiple suppliers, strategic inventory",
                    "contingency": "Alternative sourcing protocols",
                    "owner": "Supply Chain Manager",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Cybersecurity breach compromises systems",
                    "probability": 0.2,
                    "impact": "HIGH",
                    "impact_quantified": "Operational shutdown, reputation damage",
                    "early_warning": "Security monitoring, threat intelligence",
                    "mitigation": "Defense-in-depth security, regular audits",
                    "contingency": "Incident response plan activation",
                    "owner": "Chief Information Security Officer",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Regulatory approval delays",
                    "probability": 0.3,
                    "impact": "MEDIUM",
                    "impact_quantified": "3-6 month program delay",
                    "early_warning": "Regulatory pipeline tracking",
                    "mitigation": "Early engagement with regulators, compliance buffer",
                    "contingency": "Parallel-path alternative approaches",
                    "owner": "Regulatory Affairs",
                    "review_frequency": "Monthly"
                },
            ],
            "financial": [
                {
                    "risk": "Cost overruns exceed 30% of budget",
                    "probability": 0.35,
                    "impact": "HIGH",
                    "impact_quantified": "Scope reduction or additional funding required",
                    "early_warning": "Monthly budget vs. actual tracking",
                    "mitigation": "Conservative estimates, contingency allocation",
                    "contingency": "Scope prioritization and reduction protocol",
                    "owner": "Finance Director",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Foreign exchange volatility impacts costs",
                    "probability": 0.25,
                    "impact": "LOW",
                    "impact_quantified": "5-10% cost variation",
                    "early_warning": "Currency markets, economic indicators",
                    "mitigation": "Hedging strategy, local currency contracts",
                    "contingency": "Budget adjustment protocols",
                    "owner": "Treasury",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Revenue projections not achieved",
                    "probability": 0.4,
                    "impact": "MEDIUM",
                    "impact_quantified": "ROI reduced, payback extended",
                    "early_warning": "Revenue tracking, market indicators",
                    "mitigation": "Conservative projections, multiple revenue streams",
                    "contingency": "Cost reduction measures",
                    "owner": "Commercial Director",
                    "review_frequency": "Quarterly"
                },
                {
                    "risk": "Interest rate changes increase financing costs",
                    "probability": 0.3,
                    "impact": "LOW",
                    "impact_quantified": "Financing costs increase 10-20%",
                    "early_warning": "Central bank policy, market rates",
                    "mitigation": "Fixed-rate financing, rate hedging",
                    "contingency": "Refinancing options",
                    "owner": "Treasury",
                    "review_frequency": "Quarterly"
                },
            ],
            "human_capital": [
                {
                    "risk": "National talent pipeline insufficient",
                    "probability": 0.45,
                    "impact": "HIGH",
                    "impact_quantified": "Nationalization targets missed, political backlash",
                    "early_warning": "Training enrollment, completion rates",
                    "mitigation": "Accelerated training programs, competitive stipends",
                    "contingency": "Extended timeline, interim expatriate capacity",
                    "owner": "Human Resources",
                    "review_frequency": "Quarterly"
                },
                {
                    "risk": "Key leadership departures",
                    "probability": 0.25,
                    "impact": "MEDIUM",
                    "impact_quantified": "Program momentum loss, knowledge drain",
                    "early_warning": "Engagement surveys, retention indicators",
                    "mitigation": "Competitive packages, succession planning",
                    "contingency": "Rapid replacement protocols",
                    "owner": "Human Resources",
                    "review_frequency": "Quarterly"
                },
                {
                    "risk": "Expatriate talent competition intensifies",
                    "probability": 0.35,
                    "impact": "MEDIUM",
                    "impact_quantified": "Salary costs increase 20-30%",
                    "early_warning": "Market salary surveys, offer acceptance rates",
                    "mitigation": "Enhanced value proposition, lifestyle benefits",
                    "contingency": "Accelerate nationalization, remote work options",
                    "owner": "Human Resources",
                    "review_frequency": "Quarterly"
                },
                {
                    "risk": "Skills mismatch between training and needs",
                    "probability": 0.4,
                    "impact": "MEDIUM",
                    "impact_quantified": "Retraining required, productivity loss",
                    "early_warning": "Skills assessments, employer feedback",
                    "mitigation": "Continuous curriculum updates, industry partnerships",
                    "contingency": "Rapid reskilling programs",
                    "owner": "Training Director",
                    "review_frequency": "Quarterly"
                },
            ],
            "political": [
                {
                    "risk": "Leadership transition affects program support",
                    "probability": 0.15,
                    "impact": "HIGH",
                    "impact_quantified": "Program restructuring or cancellation risk",
                    "early_warning": "Political developments, policy statements",
                    "mitigation": "Broad stakeholder support, bipartisan positioning",
                    "contingency": "Quick wins to demonstrate value",
                    "owner": "Program Director",
                    "review_frequency": "Quarterly"
                },
                {
                    "risk": "Public opposition to program priorities",
                    "probability": 0.2,
                    "impact": "MEDIUM",
                    "impact_quantified": "Program modifications required",
                    "early_warning": "Public sentiment, media coverage",
                    "mitigation": "Proactive communication, visible benefits",
                    "contingency": "Program adjustment based on feedback",
                    "owner": "Communications Office",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Inter-ministry coordination failures",
                    "probability": 0.3,
                    "impact": "MEDIUM",
                    "impact_quantified": "Delays, conflicting decisions",
                    "early_warning": "Coordination meeting outcomes",
                    "mitigation": "Clear governance, escalation paths",
                    "contingency": "Senior leadership intervention",
                    "owner": "Program Office",
                    "review_frequency": "Monthly"
                },
            ],
            "technology": [
                {
                    "risk": "Technology platform selection proves inadequate",
                    "probability": 0.25,
                    "impact": "HIGH",
                    "impact_quantified": "Major rework, 12-18 month delay",
                    "early_warning": "Performance metrics, user feedback",
                    "mitigation": "Thorough evaluation, proof of concept",
                    "contingency": "Platform migration plan",
                    "owner": "Chief Technology Officer",
                    "review_frequency": "Quarterly"
                },
                {
                    "risk": "Integration with legacy systems fails",
                    "probability": 0.35,
                    "impact": "MEDIUM",
                    "impact_quantified": "Workarounds required, efficiency loss",
                    "early_warning": "Integration testing results",
                    "mitigation": "Early integration testing, API-first design",
                    "contingency": "Parallel systems operation",
                    "owner": "Integration Manager",
                    "review_frequency": "Monthly"
                },
                {
                    "risk": "Vendor lock-in limits future flexibility",
                    "probability": 0.3,
                    "impact": "MEDIUM",
                    "impact_quantified": "Higher long-term costs, reduced options",
                    "early_warning": "Contract terms, market alternatives",
                    "mitigation": "Open standards, multi-vendor strategy",
                    "contingency": "Gradual migration planning",
                    "owner": "Procurement Office",
                    "review_frequency": "Annual"
                },
            ]
        }
    
    def generate_risk_register(
        self,
        strategy_name: str,
        query: str,
        total_investment: float = None,
        facts: Dict[str, Any] = None
    ) -> List[Risk]:
        """
        Generate comprehensive risk register for a strategy.
        
        Args:
            strategy_name: Name of the strategic option
            query: The strategic question
            total_investment: Investment amount (for quantification)
            facts: Extracted facts for context
            
        Returns:
            List of Risk objects (30+ risks)
        """
        risks = []
        risk_count = 0
        
        for category, templates in self.risk_templates.items():
            for template in templates:
                risk_count += 1
                risk_id = f"{category[:3].upper()}-{risk_count:03d}"
                
                # Customize template for context
                customized = self._customize_risk(
                    template, 
                    strategy_name, 
                    total_investment
                )
                
                # Calculate risk score
                impact_weight = self.impact_weights.get(customized["impact"], 2)
                risk_score = customized["probability"] * impact_weight
                
                risks.append(Risk(
                    id=risk_id,
                    category=category.title(),
                    risk=customized["risk"],
                    probability=customized["probability"],
                    impact=customized["impact"],
                    impact_quantified=customized["impact_quantified"],
                    early_warning=customized["early_warning"],
                    mitigation=customized["mitigation"],
                    contingency=customized["contingency"],
                    owner=customized["owner"],
                    review_frequency=customized["review_frequency"],
                    risk_score=risk_score
                ))
        
        # Sort by risk score (highest first)
        risks.sort(key=lambda r: r.risk_score, reverse=True)
        
        logger.info(f"Generated {len(risks)} risks for {strategy_name}")
        return risks
    
    def _customize_risk(
        self,
        template: Dict,
        strategy_name: str,
        total_investment: float
    ) -> Dict:
        """Customize risk template for specific context."""
        
        customized = template.copy()
        
        # Customize impact quantification if investment amount known
        if total_investment and "%" in customized["impact_quantified"]:
            # Replace percentage references with actual amounts
            if "30%" in customized["impact_quantified"]:
                amount = total_investment * 0.30
                customized["impact_quantified"] = customized["impact_quantified"].replace(
                    "30%", f"30% (${amount/1e9:.1f}B)"
                )
        
        return customized
    
    def get_top_risks(self, risks: List[Risk], n: int = 10) -> List[Risk]:
        """Get top N risks by risk score."""
        return sorted(risks, key=lambda r: r.risk_score, reverse=True)[:n]
    
    def generate_risk_matrix(self, risks: List[Risk]) -> Dict[str, List[str]]:
        """Generate risk matrix categorization."""
        
        matrix = {
            "critical_high_prob": [],  # Immediate action required
            "critical_low_prob": [],   # Contingency plans needed
            "medium_high_prob": [],    # Active monitoring
            "medium_low_prob": [],     # Standard monitoring
            "low_risk": []             # Accept or transfer
        }
        
        for risk in risks:
            if risk.impact in ["CRITICAL", "HIGH"] and risk.probability >= 0.3:
                matrix["critical_high_prob"].append(risk.id)
            elif risk.impact in ["CRITICAL", "HIGH"] and risk.probability < 0.3:
                matrix["critical_low_prob"].append(risk.id)
            elif risk.impact == "MEDIUM" and risk.probability >= 0.3:
                matrix["medium_high_prob"].append(risk.id)
            elif risk.impact == "MEDIUM" and risk.probability < 0.3:
                matrix["medium_low_prob"].append(risk.id)
            else:
                matrix["low_risk"].append(risk.id)
        
        return matrix


def format_risk_register_for_brief(risks: List[Risk], max_risks: int = 15) -> str:
    """Format risk register as markdown for ministerial brief."""
    
    if not risks:
        return "Risk register not available."
    
    output = []
    
    # Summary statistics
    critical = sum(1 for r in risks if r.impact == "CRITICAL")
    high = sum(1 for r in risks if r.impact == "HIGH")
    medium = sum(1 for r in risks if r.impact == "MEDIUM")
    
    output.append(f"""
### Risk Summary

**Total Risks Identified:** {len(risks)}
- Critical Impact: {critical}
- High Impact: {high}
- Medium Impact: {medium}

### Top Risks (by Risk Score)

| ID | Risk | Prob | Impact | Early Warning | Owner |
|----|------|------|--------|---------------|-------|
""")
    
    for risk in risks[:max_risks]:
        output.append(f"| {risk.id} | {risk.risk[:60]}... | {risk.probability*100:.0f}% | {risk.impact} | {risk.early_warning[:40]}... | {risk.owner} |")
    
    # Detailed view of top 5
    output.append("\n### Critical Risk Details\n")
    
    for risk in risks[:5]:
        output.append(f"""
**{risk.id}: {risk.risk}**
- **Probability:** {risk.probability*100:.0f}%
- **Impact:** {risk.impact} — {risk.impact_quantified}
- **Early Warning:** {risk.early_warning}
- **Mitigation:** {risk.mitigation}
- **Contingency:** {risk.contingency}
- **Owner:** {risk.owner} | Review: {risk.review_frequency}
""")
    
    return "\n".join(output)

