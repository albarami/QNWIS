"""
Stakeholder Analysis Module - Big 4 Standard Political Feasibility

Analyzes:
- Who wins/loses from each option
- Power/interest mapping
- Coalition building strategies
- Political feasibility assessment

Domain-agnostic: Works for any strategic decision context.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Stakeholder:
    """A stakeholder with power and interest levels."""
    name: str
    category: str  # government, private, labor, education, regional
    power: int  # 1-10 scale
    interest: int  # 1-10 scale
    position: str = "neutral"  # supporter, opponent, neutral, swing


@dataclass
class StakeholderImpact:
    """Impact of an option on a stakeholder."""
    stakeholder: str
    impact: str  # POSITIVE, NEGATIVE, MIXED, NEUTRAL
    winners: str
    losers: str
    net_effect: str
    political_risk: str  # LOW, MEDIUM, HIGH, CRITICAL
    mitigation: str


@dataclass
class CoalitionStrategy:
    """Strategy for building political support."""
    natural_supporters: List[str]
    potential_opponents: List[str]
    swing_stakeholders: List[str]
    coalition_building_actions: List[Dict[str, Any]]
    communication_plan: Dict[str, Any]


class StakeholderAnalyzer:
    """
    Analyzes stakeholder impact and political feasibility.
    
    Domain-agnostic: Detects stakeholder types from query context
    and generates appropriate analysis.
    """
    
    def __init__(self):
        """Initialize with stakeholder templates."""
        
        # Generic stakeholder templates by category
        # These are customized based on query context
        self.stakeholder_templates = {
            "government": [
                {"name": "Executive Leadership", "power": 10, "interest": 10},
                {"name": "Finance Ministry", "power": 8, "interest": 9},
                {"name": "Sector Ministry", "power": 7, "interest": 10},
                {"name": "Planning Authority", "power": 6, "interest": 8},
                {"name": "Investment Authority", "power": 8, "interest": 9},
                {"name": "Regulatory Bodies", "power": 6, "interest": 7},
            ],
            "private_sector": [
                {"name": "Major Corporations", "power": 7, "interest": 8},
                {"name": "Family Business Groups", "power": 6, "interest": 7},
                {"name": "Foreign Investors", "power": 5, "interest": 8},
                {"name": "SMEs", "power": 3, "interest": 6},
                {"name": "Industry Associations", "power": 5, "interest": 7},
            ],
            "labor": [
                {"name": "National Workers", "power": 6, "interest": 10},
                {"name": "Skilled Professionals", "power": 4, "interest": 8},
                {"name": "General Workforce", "power": 2, "interest": 7},
                {"name": "Labor Unions", "power": 4, "interest": 9},
            ],
            "education": [
                {"name": "Universities", "power": 4, "interest": 8},
                {"name": "Vocational Institutions", "power": 3, "interest": 7},
                {"name": "Research Centers", "power": 4, "interest": 8},
            ],
            "civil_society": [
                {"name": "Consumer Groups", "power": 3, "interest": 6},
                {"name": "Environmental Groups", "power": 3, "interest": 7},
                {"name": "Professional Associations", "power": 4, "interest": 7},
            ],
            "regional": [
                {"name": "Regional Partners", "power": 4, "interest": 5},
                {"name": "Regional Competitors", "power": 3, "interest": 7},
                {"name": "International Organizations", "power": 3, "interest": 5},
            ]
        }
        
        # Impact patterns by option type
        self.impact_patterns = {
            "technology": {
                "National Workers": {
                    "impact": "MIXED",
                    "winners": "STEM-educated professionals, tech entrepreneurs",
                    "losers": "Mid-skill workers in sectors being automated",
                    "political_risk": "MEDIUM"
                },
                "Major Corporations": {
                    "impact": "MIXED",
                    "winners": "Tech-forward companies, IT departments",
                    "losers": "Traditional businesses without digital capabilities",
                    "political_risk": "MEDIUM"
                },
                "Family Business Groups": {
                    "impact": "NEGATIVE_SHORT_TERM",
                    "winners": "Tech-savvy family members",
                    "losers": "Traditional sectors (construction, retail)",
                    "political_risk": "HIGH"
                },
                "Universities": {
                    "impact": "POSITIVE",
                    "winners": "STEM faculties, research programs",
                    "losers": "Traditional humanities programs (relative)",
                    "political_risk": "LOW"
                },
            },
            "tourism": {
                "National Workers": {
                    "impact": "POSITIVE",
                    "winners": "Hospitality workers, service sector",
                    "losers": "Limited - mostly job creation",
                    "political_risk": "LOW"
                },
                "Major Corporations": {
                    "impact": "POSITIVE",
                    "winners": "Hotel groups, airlines, F&B chains",
                    "losers": "Limited",
                    "political_risk": "LOW"
                },
                "Family Business Groups": {
                    "impact": "POSITIVE",
                    "winners": "Real estate, hospitality investments",
                    "losers": "Limited",
                    "political_risk": "LOW"
                },
                "Environmental Groups": {
                    "impact": "MIXED",
                    "winners": "Eco-tourism advocates",
                    "losers": "Conservation priorities may conflict",
                    "political_risk": "MEDIUM"
                },
            },
            "workforce": {
                "National Workers": {
                    "impact": "POSITIVE",
                    "winners": "Nationals seeking jobs, trainees",
                    "losers": "Limited",
                    "political_risk": "LOW"
                },
                "General Workforce": {
                    "impact": "NEGATIVE",
                    "winners": "Limited",
                    "losers": "Expatriate workers facing restrictions",
                    "political_risk": "LOW"
                },
                "Major Corporations": {
                    "impact": "MIXED",
                    "winners": "Companies with strong national talent",
                    "losers": "Companies dependent on expatriate labor",
                    "political_risk": "MEDIUM"
                },
            },
            "infrastructure": {
                "Major Corporations": {
                    "impact": "POSITIVE",
                    "winners": "Construction, engineering, materials",
                    "losers": "Limited",
                    "political_risk": "LOW"
                },
                "General Workforce": {
                    "impact": "POSITIVE",
                    "winners": "Construction workers, project staff",
                    "losers": "Limited",
                    "political_risk": "LOW"
                },
            }
        }
    
    def detect_option_type(self, option_name: str) -> str:
        """Detect the type of option for appropriate analysis."""
        option_lower = option_name.lower()
        
        if any(kw in option_lower for kw in ["tech", "ai", "digital", "innovation"]):
            return "technology"
        elif any(kw in option_lower for kw in ["tourism", "hospitality", "destination"]):
            return "tourism"
        elif any(kw in option_lower for kw in ["workforce", "employment", "nationalization", "labor"]):
            return "workforce"
        elif any(kw in option_lower for kw in ["infrastructure", "construction"]):
            return "infrastructure"
        else:
            return "generic"
    
    def analyze_option(
        self,
        option_name: str,
        query: str,
        facts: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze stakeholder impacts for an option.
        
        Returns comprehensive stakeholder analysis.
        """
        option_type = self.detect_option_type(option_name)
        
        # Build stakeholder list
        stakeholders = self._build_stakeholder_list(query)
        
        # Analyze impacts
        impacts = []
        for sh in stakeholders:
            impact = self._analyze_stakeholder_impact(sh, option_type)
            impacts.append(impact)
        
        # Generate coalition strategy
        coalition = self._generate_coalition_strategy(impacts, option_name)
        
        # Calculate political feasibility score
        feasibility = self._calculate_political_feasibility(impacts)
        
        return {
            "option": option_name,
            "option_type": option_type,
            "stakeholders": stakeholders,
            "impacts": impacts,
            "coalition_strategy": coalition,
            "political_feasibility": feasibility,
            "power_interest_matrix": self._generate_power_interest_matrix(stakeholders, impacts)
        }
    
    def _build_stakeholder_list(self, query: str) -> List[Dict[str, Any]]:
        """Build relevant stakeholder list based on query context."""
        stakeholders = []
        
        # Add all categories
        for category, templates in self.stakeholder_templates.items():
            for template in templates:
                stakeholders.append({
                    "name": template["name"],
                    "category": category,
                    "power": template["power"],
                    "interest": template["interest"]
                })
        
        return stakeholders
    
    def _analyze_stakeholder_impact(
        self,
        stakeholder: Dict[str, Any],
        option_type: str
    ) -> StakeholderImpact:
        """Analyze impact on a specific stakeholder."""
        
        sh_name = stakeholder["name"]
        patterns = self.impact_patterns.get(option_type, {})
        
        if sh_name in patterns:
            pattern = patterns[sh_name]
            return StakeholderImpact(
                stakeholder=sh_name,
                impact=pattern["impact"],
                winners=pattern["winners"],
                losers=pattern["losers"],
                net_effect=self._calculate_net_effect(pattern["impact"]),
                political_risk=pattern["political_risk"],
                mitigation=self._generate_mitigation(sh_name, pattern["impact"])
            )
        
        # Default neutral impact
        return StakeholderImpact(
            stakeholder=sh_name,
            impact="NEUTRAL",
            winners="Not directly affected",
            losers="Not directly affected",
            net_effect="Minimal direct impact expected",
            political_risk="LOW",
            mitigation="Standard engagement and communication"
        )
    
    def _calculate_net_effect(self, impact: str) -> str:
        """Calculate net effect description."""
        effects = {
            "POSITIVE": "Net benefit - likely supporters",
            "NEGATIVE": "Net negative - likely opponents",
            "NEGATIVE_SHORT_TERM": "Short-term costs but potential long-term benefits",
            "MIXED": "Winners and losers within this group",
            "NEUTRAL": "Limited direct impact"
        }
        return effects.get(impact, "Unknown impact")
    
    def _generate_mitigation(self, stakeholder: str, impact: str) -> str:
        """Generate mitigation strategy for negative impacts."""
        if impact in ["POSITIVE", "NEUTRAL"]:
            return "Maintain engagement and communicate benefits"
        
        mitigations = {
            "Family Business Groups": "Create co-investment vehicles, ensure family groups have early access to opportunities",
            "National Workers": "Establish retraining programs, job placement guarantees, transition support",
            "General Workforce": "Phase implementation to allow adjustment, provide transition support",
            "Major Corporations": "Offer incentives for adoption, provide technical assistance",
            "Environmental Groups": "Commit to sustainability standards, establish oversight mechanisms"
        }
        
        return mitigations.get(stakeholder, "Develop targeted engagement and support programs")
    
    def _generate_coalition_strategy(
        self,
        impacts: List[StakeholderImpact],
        option_name: str
    ) -> CoalitionStrategy:
        """Generate strategy for building political support."""
        
        supporters = [i.stakeholder for i in impacts if i.impact == "POSITIVE"]
        opponents = [i.stakeholder for i in impacts if i.impact in ["NEGATIVE", "NEGATIVE_SHORT_TERM"]]
        swing = [i.stakeholder for i in impacts if i.impact == "MIXED"]
        
        actions = []
        
        # Actions for opponents
        for opponent in opponents:
            impact = next((i for i in impacts if i.stakeholder == opponent), None)
            if impact:
                actions.append({
                    "stakeholder": opponent,
                    "action": impact.mitigation,
                    "timeline": "Pre-announcement",
                    "responsible": "Strategy Office",
                    "success_metric": f"Reduce opposition from {opponent}"
                })
        
        # Actions for swing stakeholders
        for sh in swing:
            actions.append({
                "stakeholder": sh,
                "action": f"Targeted engagement to highlight benefits for {sh}",
                "timeline": "During consultation phase",
                "responsible": "Communications Office",
                "success_metric": f"Convert {sh} to supporter"
            })
        
        return CoalitionStrategy(
            natural_supporters=supporters,
            potential_opponents=opponents,
            swing_stakeholders=swing,
            coalition_building_actions=actions,
            communication_plan={
                "key_messages": [
                    f"Benefits of {option_name} for national development",
                    "Mitigation measures for affected groups",
                    "Timeline and implementation approach"
                ],
                "channels": ["Official briefings", "Industry consultations", "Public communications"],
                "timing": "Phased rollout starting with key supporters"
            }
        )
    
    def _calculate_political_feasibility(self, impacts: List[StakeholderImpact]) -> Dict[str, Any]:
        """Calculate overall political feasibility score."""
        
        positive = sum(1 for i in impacts if i.impact == "POSITIVE")
        negative = sum(1 for i in impacts if i.impact in ["NEGATIVE", "NEGATIVE_SHORT_TERM"])
        mixed = sum(1 for i in impacts if i.impact == "MIXED")
        
        total = len(impacts)
        
        # Calculate weighted score (account for high-power stakeholders)
        # This is simplified - in production would weight by power/interest
        support_ratio = (positive + mixed * 0.5) / total if total > 0 else 0.5
        
        if support_ratio > 0.7:
            feasibility = "HIGH"
            score = 0.85
        elif support_ratio > 0.5:
            feasibility = "MEDIUM"
            score = 0.65
        elif support_ratio > 0.3:
            feasibility = "LOW-MEDIUM"
            score = 0.45
        else:
            feasibility = "LOW"
            score = 0.25
        
        return {
            "rating": feasibility,
            "score": score,
            "supporters": positive,
            "opponents": negative,
            "swing": mixed,
            "assessment": f"{positive} natural supporters, {negative} potential opponents, {mixed} swing stakeholders"
        }
    
    def _generate_power_interest_matrix(
        self,
        stakeholders: List[Dict[str, Any]],
        impacts: List[StakeholderImpact]
    ) -> Dict[str, List[str]]:
        """Generate power/interest matrix classification."""
        
        impact_lookup = {i.stakeholder: i for i in impacts}
        
        matrix = {
            "high_power_high_interest": [],  # Key Players - manage closely
            "high_power_low_interest": [],   # Keep satisfied
            "low_power_high_interest": [],   # Keep informed
            "low_power_low_interest": []     # Monitor
        }
        
        for sh in stakeholders:
            power = sh["power"]
            interest = sh["interest"]
            
            if power >= 7 and interest >= 7:
                matrix["high_power_high_interest"].append(sh["name"])
            elif power >= 7 and interest < 7:
                matrix["high_power_low_interest"].append(sh["name"])
            elif power < 7 and interest >= 7:
                matrix["low_power_high_interest"].append(sh["name"])
            else:
                matrix["low_power_low_interest"].append(sh["name"])
        
        return matrix


def format_stakeholder_analysis_for_brief(analysis: Dict[str, Any]) -> str:
    """Format stakeholder analysis as markdown for ministerial brief."""
    
    if not analysis:
        return "Stakeholder analysis not available."
    
    output = []
    
    # Political Feasibility Summary
    feasibility = analysis.get("political_feasibility", {})
    output.append(f"""
### Political Feasibility Assessment

**Overall Rating:** {feasibility.get('rating', 'N/A')} ({feasibility.get('score', 0)*100:.0f}/100)
**Assessment:** {feasibility.get('assessment', 'N/A')}
""")
    
    # Power/Interest Matrix
    matrix = analysis.get("power_interest_matrix", {})
    output.append("""
### Stakeholder Power/Interest Matrix

**Key Players (High Power, High Interest) — Manage Closely:**
""")
    for sh in matrix.get("high_power_high_interest", []):
        output.append(f"- {sh}")
    
    output.append("""
**Keep Satisfied (High Power, Lower Interest):**
""")
    for sh in matrix.get("high_power_low_interest", []):
        output.append(f"- {sh}")
    
    # Impact Summary
    output.append("""
### Stakeholder Impact Summary

| Stakeholder | Impact | Political Risk | Mitigation |
|-------------|--------|----------------|------------|
""")
    
    for impact in analysis.get("impacts", [])[:10]:  # Top 10
        if impact.impact != "NEUTRAL":
            output.append(f"| {impact.stakeholder} | {impact.impact} | {impact.political_risk} | {impact.mitigation[:50]}... |")
    
    # Coalition Strategy
    coalition = analysis.get("coalition_strategy", {})
    if coalition:
        output.append(f"""
### Coalition Building Strategy

**Natural Supporters:** {', '.join(coalition.natural_supporters[:5])}
**Potential Opponents:** {', '.join(coalition.potential_opponents[:5])}
**Swing Stakeholders:** {', '.join(coalition.swing_stakeholders[:5])}
""")
        
        if coalition.coalition_building_actions:
            output.append("\n**Priority Actions:**")
            for action in coalition.coalition_building_actions[:3]:
                output.append(f"- {action['stakeholder']}: {action['action']}")
    
    return "\n".join(output)

