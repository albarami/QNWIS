"""
Implementation Plan Generator - Big 4 Standard Detail

Generates quarterly implementation plans with:
- Specific actions by quarter
- Named institutions and partners
- Budget allocations
- Success metrics
- Key hires and roles

Domain-agnostic: Works for any strategic initiative type.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QuarterlyMilestone:
    """A specific quarterly milestone with actions."""
    quarter: str  # e.g., "Q1 2025"
    year: int
    actions: List[Dict[str, Any]]
    budget: float
    success_metrics: List[str]
    key_deliverables: List[str]
    risks: List[str] = field(default_factory=list)


@dataclass
class PhaseDetail:
    """Detailed phase with quarterly breakdown."""
    phase_name: str
    phase_number: int
    start_year: int
    end_year: int
    total_budget: float
    strategic_objective: str
    quarters: List[QuarterlyMilestone]
    key_partners: List[str]
    governance_structure: str
    success_criteria: List[str]


class ImplementationPlanner:
    """
    Generates Big 4 standard implementation plans.
    
    Domain-agnostic: Detects initiative type and generates appropriate
    milestones, partners, and metrics.
    """
    
    def __init__(self, start_year: int = None):
        """Initialize with start year (defaults to next year)."""
        self.start_year = start_year or (datetime.now().year + 1)
        
        # Domain-agnostic partner templates
        self.partner_templates = {
            "technology": {
                "government": ["Ministry of Communications", "Ministry of Economy", "Investment Authority"],
                "education": ["National University", "Technical College", "Research Institute"],
                "private": ["Global Tech Company", "Local Tech Firm", "Industry Association"],
                "international": ["International Standards Body", "Regional Tech Hub", "Global Accelerator"]
            },
            "tourism": {
                "government": ["Tourism Authority", "Ministry of Culture", "Civil Aviation Authority"],
                "education": ["Hospitality College", "Tourism Institute"],
                "private": ["Hotel Group", "Airline Partner", "Event Management Company"],
                "international": ["UNWTO", "Regional Tourism Board", "International Hotel Chain"]
            },
            "workforce": {
                "government": ["Ministry of Labour", "Social Development Ministry", "Education Ministry"],
                "education": ["University", "Vocational Training Institute", "Skills Academy"],
                "private": ["Industry Association", "Major Employers", "Training Provider"],
                "international": ["ILO", "World Bank", "Regional Labor Organization"]
            },
            "infrastructure": {
                "government": ["Planning Ministry", "Public Works", "Utilities Authority"],
                "education": ["Engineering University", "Research Center"],
                "private": ["Construction Company", "Engineering Firm", "Equipment Supplier"],
                "international": ["Development Bank", "International Engineering Firm"]
            },
            "financial": {
                "government": ["Central Bank", "Finance Ministry", "Regulatory Authority"],
                "education": ["Business School", "Finance Institute"],
                "private": ["Major Bank", "Investment Firm", "Insurance Company"],
                "international": ["IMF", "World Bank", "Regional Development Bank"]
            },
            "healthcare": {
                "government": ["Health Ministry", "Medical Council", "Insurance Authority"],
                "education": ["Medical School", "Nursing College", "Research Hospital"],
                "private": ["Hospital Group", "Pharmaceutical Company", "Medical Supplier"],
                "international": ["WHO", "International Medical Association"]
            }
        }
        
        # Generic role templates
        self.role_templates = {
            "executive": ["CEO", "Executive Director", "Chief Officer"],
            "technical": ["Chief Technology Officer", "Technical Director", "Head of Engineering"],
            "operations": ["Chief Operating Officer", "Operations Director", "Program Manager"],
            "strategy": ["Chief Strategy Officer", "Strategy Director", "Planning Head"],
            "finance": ["Chief Financial Officer", "Finance Director", "Investment Manager"]
        }
    
    def detect_initiative_type(self, query: str, option_name: str = "") -> str:
        """Detect the type of initiative for appropriate planning."""
        combined = f"{query} {option_name}".lower()
        
        type_keywords = {
            "technology": ["ai", "tech", "digital", "innovation", "data", "software", "ict"],
            "tourism": ["tourism", "hospitality", "destination", "visitor", "hotel", "attraction"],
            "workforce": ["workforce", "employment", "skills", "training", "labor", "jobs", "nationalization"],
            "infrastructure": ["infrastructure", "construction", "transport", "utilities", "development"],
            "financial": ["financial", "banking", "investment", "fiscal", "monetary"],
            "healthcare": ["health", "medical", "hospital", "pharmaceutical"]
        }
        
        scores = {}
        for init_type, keywords in type_keywords.items():
            scores[init_type] = sum(1 for kw in keywords if kw in combined)
        
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "infrastructure"
    
    def generate_implementation_plan(
        self,
        query: str,
        option_name: str,
        total_budget: float,
        time_horizon: int = 10,
        facts: Dict[str, Any] = None
    ) -> List[PhaseDetail]:
        """
        Generate detailed implementation plan with quarterly milestones.
        
        Args:
            query: The strategic question
            option_name: Name of the option being planned
            total_budget: Total budget in currency units
            time_horizon: Years for implementation
            facts: Extracted facts with context
        
        Returns:
            List of PhaseDetail objects with quarterly breakdowns
        """
        init_type = self.detect_initiative_type(query, option_name)
        logger.info(f"Generating {init_type} implementation plan for: {option_name}")
        
        # Define phases based on initiative type
        phases = self._generate_phases(init_type, option_name, total_budget, time_horizon)
        
        # Add detailed quarterly milestones
        for phase in phases:
            phase.quarters = self._generate_quarterly_milestones(
                init_type, phase, option_name, facts
            )
            phase.key_partners = self._get_relevant_partners(init_type)
            phase.governance_structure = self._generate_governance_structure(init_type, option_name)
        
        return phases
    
    def _generate_phases(
        self,
        init_type: str,
        option_name: str,
        total_budget: float,
        time_horizon: int
    ) -> List[PhaseDetail]:
        """Generate high-level phases for the initiative."""
        
        # Phase templates by initiative type (domain-agnostic names)
        phase_templates = {
            "technology": [
                ("Foundation & Infrastructure", 0.25, "Establish governance, initial infrastructure, talent pipeline"),
                ("Development & Capability Building", 0.40, "Build core capabilities, launch key programs"),
                ("Scale & Ecosystem Growth", 0.35, "Scale operations, attract investment, achieve targets")
            ],
            "tourism": [
                ("Infrastructure & Brand Development", 0.35, "Build core attractions, establish brand"),
                ("Experience & Service Excellence", 0.35, "Develop experiences, train workforce"),
                ("Market Expansion & Sustainability", 0.30, "Expand markets, ensure sustainability")
            ],
            "workforce": [
                ("Assessment & Program Design", 0.20, "Skills gap analysis, program development"),
                ("Training Delivery & Placement", 0.50, "Execute training programs, job placement"),
                ("Optimization & Scale", 0.30, "Refine programs, scale successful initiatives")
            ],
            "infrastructure": [
                ("Planning & Design", 0.20, "Feasibility, design, permitting"),
                ("Construction & Development", 0.55, "Execute construction, major works"),
                ("Commissioning & Operations", 0.25, "Testing, handover, operations setup")
            ],
            "financial": [
                ("Regulatory Framework", 0.15, "Policy development, legal framework"),
                ("Institutional Setup", 0.35, "Establish institutions, systems"),
                ("Market Development", 0.50, "Launch products, grow market")
            ],
            "healthcare": [
                ("Assessment & Planning", 0.15, "Needs assessment, facility planning"),
                ("Infrastructure & Workforce", 0.50, "Build facilities, train staff"),
                ("Service Delivery & Quality", 0.35, "Launch services, quality programs")
            ]
        }
        
        templates = phase_templates.get(init_type, phase_templates["infrastructure"])
        
        phases = []
        years_per_phase = time_horizon // len(templates)
        current_year = self.start_year
        
        for i, (name, budget_share, objective) in enumerate(templates):
            phase_budget = total_budget * budget_share
            
            phases.append(PhaseDetail(
                phase_name=name,
                phase_number=i + 1,
                start_year=current_year,
                end_year=current_year + years_per_phase - 1,
                total_budget=phase_budget,
                strategic_objective=objective,
                quarters=[],
                key_partners=[],
                governance_structure="",
                success_criteria=self._generate_success_criteria(init_type, i + 1)
            ))
            
            current_year += years_per_phase
        
        return phases
    
    def _generate_quarterly_milestones(
        self,
        init_type: str,
        phase: PhaseDetail,
        option_name: str,
        facts: Dict[str, Any]
    ) -> List[QuarterlyMilestone]:
        """Generate detailed quarterly milestones for a phase."""
        
        milestones = []
        phase_years = phase.end_year - phase.start_year + 1
        quarters_total = phase_years * 4
        quarterly_budget = phase.total_budget / quarters_total
        
        # Generate actions based on phase number and initiative type
        action_templates = self._get_action_templates(init_type, phase.phase_number)
        
        quarter_num = 0
        for year in range(phase.start_year, phase.end_year + 1):
            for q in range(1, 5):
                quarter_num += 1
                quarter_label = f"Q{q} {year}"
                
                # Get actions for this quarter
                actions = []
                template_idx = min(quarter_num - 1, len(action_templates) - 1)
                
                if template_idx < len(action_templates):
                    for action in action_templates[template_idx]:
                        actions.append({
                            "action": action["action"],
                            "responsible": action.get("responsible", "Program Office"),
                            "budget": action.get("budget_share", 0.25) * quarterly_budget,
                            "deliverable": action.get("deliverable", "Milestone achieved"),
                            "dependencies": action.get("dependencies", [])
                        })
                
                # Generate success metrics for this quarter
                metrics = self._generate_quarterly_metrics(init_type, phase.phase_number, quarter_num)
                
                milestones.append(QuarterlyMilestone(
                    quarter=quarter_label,
                    year=year,
                    actions=actions,
                    budget=quarterly_budget,
                    success_metrics=metrics,
                    key_deliverables=[a["deliverable"] for a in actions],
                    risks=self._identify_quarterly_risks(init_type, phase.phase_number, quarter_num)
                ))
        
        return milestones[:8]  # Limit to 8 quarters shown (2 years of detail)
    
    def _get_action_templates(self, init_type: str, phase_number: int) -> List[List[Dict]]:
        """Get action templates based on initiative type and phase."""
        
        # Phase 1 actions (Foundation)
        phase1_actions = {
            "technology": [
                [
                    {"action": "Establish governing authority via legislation", "responsible": "Ministry of Communications", "deliverable": "Authority established", "budget_share": 0.3},
                    {"action": "Recruit executive leadership team", "responsible": "Executive Search Firm", "deliverable": "CEO and C-suite hired", "budget_share": 0.2},
                ],
                [
                    {"action": "Launch national skills initiative with universities", "responsible": "Education Ministry", "deliverable": "Program launched with 3+ partners", "budget_share": 0.35},
                    {"action": "Establish scholarship and faculty programs", "responsible": "Authority", "deliverable": "500 scholarships awarded", "budget_share": 0.25},
                ],
                [
                    {"action": "Issue RFP for Tier 1 infrastructure", "responsible": "Procurement Office", "deliverable": "RFP issued, 5+ bidders", "budget_share": 0.15},
                    {"action": "Complete site selection and environmental assessment", "responsible": "Planning Ministry", "deliverable": "Site approved", "budget_share": 0.2},
                ],
                [
                    {"action": "Award major infrastructure contracts", "responsible": "Authority Board", "deliverable": "Contracts signed", "budget_share": 0.4},
                    {"action": "Begin construction of primary facility", "responsible": "Contractor", "deliverable": "Groundbreaking complete", "budget_share": 0.3},
                ],
            ],
            "tourism": [
                [
                    {"action": "Establish tourism development authority", "responsible": "Tourism Ministry", "deliverable": "Authority operational", "budget_share": 0.25},
                    {"action": "Complete destination brand strategy", "responsible": "Marketing Agency", "deliverable": "Brand launched", "budget_share": 0.3},
                ],
                [
                    {"action": "Launch hospitality training program", "responsible": "Hospitality College", "deliverable": "1,000 trainees enrolled", "budget_share": 0.3},
                    {"action": "Sign agreements with international hotel brands", "responsible": "Investment Authority", "deliverable": "3+ agreements signed", "budget_share": 0.25},
                ],
                [
                    {"action": "Begin construction of flagship attraction", "responsible": "Development Company", "deliverable": "Construction started", "budget_share": 0.4},
                    {"action": "Launch international marketing campaign", "responsible": "Tourism Authority", "deliverable": "Campaign live in 10+ markets", "budget_share": 0.2},
                ],
                [
                    {"action": "Open first phase of new attractions", "responsible": "Operations Team", "deliverable": "Attractions operational", "budget_share": 0.35},
                    {"action": "Launch visitor experience monitoring", "responsible": "Quality Team", "deliverable": "Monitoring system live", "budget_share": 0.15},
                ],
            ],
            "workforce": [
                [
                    {"action": "Complete national skills gap assessment", "responsible": "Labour Ministry", "deliverable": "Assessment report published", "budget_share": 0.3},
                    {"action": "Establish program governance committee", "responsible": "Ministry", "deliverable": "Committee operational", "budget_share": 0.15},
                ],
                [
                    {"action": "Design training curriculum with industry", "responsible": "Training Institute", "deliverable": "Curriculum approved", "budget_share": 0.25},
                    {"action": "Certify training providers", "responsible": "Quality Authority", "deliverable": "10+ providers certified", "budget_share": 0.2},
                ],
                [
                    {"action": "Launch first cohort of trainees", "responsible": "Program Office", "deliverable": "1,000+ trainees enrolled", "budget_share": 0.35},
                    {"action": "Establish employer placement partnerships", "responsible": "Industry Liaison", "deliverable": "50+ employer partners", "budget_share": 0.2},
                ],
                [
                    {"action": "Graduate first cohort with placements", "responsible": "Program Office", "deliverable": "70%+ placement rate", "budget_share": 0.3},
                    {"action": "Collect and publish program outcomes", "responsible": "Monitoring Team", "deliverable": "Outcomes report published", "budget_share": 0.1},
                ],
            ]
        }
        
        # Phase 2 and 3 have similar structure but different focus
        phase2_actions = {
            "technology": [
                [
                    {"action": "Launch venture capital fund", "responsible": "Investment Authority", "deliverable": "Fund operational with capital", "budget_share": 0.4},
                    {"action": "Establish international partnerships", "responsible": "Authority", "deliverable": "5+ MoUs signed", "budget_share": 0.2},
                ],
                [
                    {"action": "Open applications for startup relocation program", "responsible": "Authority", "deliverable": "50+ applications received", "budget_share": 0.15},
                    {"action": "Complete first investment round", "responsible": "VC Fund", "deliverable": "10+ investments made", "budget_share": 0.35},
                ],
            ],
            "tourism": [
                [
                    {"action": "Launch premium experience packages", "responsible": "Tourism Authority", "deliverable": "10+ packages available", "budget_share": 0.25},
                    {"action": "Achieve international quality certification", "responsible": "Quality Team", "deliverable": "ISO/UNWTO certification", "budget_share": 0.2},
                ],
            ],
            "workforce": [
                [
                    {"action": "Scale program to additional sectors", "responsible": "Program Office", "deliverable": "3+ new sectors added", "budget_share": 0.3},
                    {"action": "Launch employer co-investment scheme", "responsible": "Finance Team", "deliverable": "Scheme operational", "budget_share": 0.25},
                ],
            ]
        }
        
        if phase_number == 1:
            return phase1_actions.get(init_type, phase1_actions.get("technology", []))
        else:
            return phase2_actions.get(init_type, phase2_actions.get("technology", []))
    
    def _generate_quarterly_metrics(
        self,
        init_type: str,
        phase_number: int,
        quarter_num: int
    ) -> List[str]:
        """Generate success metrics for a specific quarter."""
        
        base_metrics = {
            "technology": [
                "Number of graduates/certifications",
                "Investment attracted ($)",
                "Companies registered",
                "Jobs created",
                "Patents filed"
            ],
            "tourism": [
                "Visitor arrivals",
                "Average daily rate ($)",
                "Occupancy rate (%)",
                "Tourism revenue ($)",
                "Satisfaction score"
            ],
            "workforce": [
                "Trainees enrolled",
                "Completion rate (%)",
                "Placement rate (%)",
                "Employer satisfaction (%)",
                "Wage increase (%)"
            ],
            "infrastructure": [
                "Construction progress (%)",
                "Budget variance (%)",
                "Safety incidents",
                "Quality scores",
                "Schedule adherence"
            ]
        }
        
        metrics = base_metrics.get(init_type, base_metrics["infrastructure"])
        
        # Return 2-3 metrics per quarter
        start_idx = (quarter_num - 1) % len(metrics)
        return metrics[start_idx:start_idx + 3]
    
    def _identify_quarterly_risks(
        self,
        init_type: str,
        phase_number: int,
        quarter_num: int
    ) -> List[str]:
        """Identify risks for a specific quarter."""
        
        phase_risks = {
            1: ["Recruitment delays", "Regulatory approval delays", "Budget constraints"],
            2: ["Market conditions", "Partner performance", "Technical challenges"],
            3: ["Demand shortfall", "Competition", "Sustainability concerns"]
        }
        
        return phase_risks.get(phase_number, phase_risks[1])[:2]
    
    def _get_relevant_partners(self, init_type: str) -> List[str]:
        """Get list of relevant partners for initiative type."""
        templates = self.partner_templates.get(init_type, self.partner_templates["infrastructure"])
        
        partners = []
        for category, orgs in templates.items():
            partners.extend(orgs[:2])  # Top 2 from each category
        
        return partners
    
    def _generate_governance_structure(self, init_type: str, option_name: str) -> str:
        """Generate governance structure description."""
        return f"""
**Governance Structure:**
- Steering Committee: Cabinet-level oversight, quarterly meetings
- Executive Board: Authority CEO + key ministry representatives
- Program Management Office: Day-to-day execution
- Technical Advisory Committee: Industry and academic experts
- Monitoring & Evaluation Unit: Independent outcome tracking
"""
    
    def _generate_success_criteria(self, init_type: str, phase_number: int) -> List[str]:
        """Generate success criteria for a phase."""
        
        criteria_templates = {
            "technology": {
                1: ["Authority fully operational", "First cohort enrolled", "Infrastructure construction started"],
                2: ["VC fund making investments", "First companies relocated", "International partnerships active"],
                3: ["Target companies achieved", "Target jobs created", "Positive ROI trajectory"]
            },
            "tourism": {
                1: ["Brand launched internationally", "First attractions open", "Training program operational"],
                2: ["Target visitor growth achieved", "Quality certifications obtained", "Revenue targets met"],
                3: ["Sustainable operations", "Market position established", "Repeat visitor rate >30%"]
            },
            "workforce": {
                1: ["Skills assessment complete", "Training programs launched", "Initial cohort graduated"],
                2: ["Placement rate >70%", "Employer satisfaction >80%", "Program scaled to 5+ sectors"],
                3: ["Self-sustaining funding model", "National skills gap reduced by X%", "Wage premium demonstrated"]
            }
        }
        
        return criteria_templates.get(init_type, criteria_templates["technology"]).get(phase_number, [])


def format_implementation_plan_for_brief(phases: List[PhaseDetail], currency: str = "QR") -> str:
    """Format implementation plan as detailed markdown for ministerial brief."""
    
    if not phases:
        return "Implementation plan not available."
    
    output = []
    
    for phase in phases:
        budget_display = f"{currency} {phase.total_budget/1e9:.1f}B" if phase.total_budget >= 1e9 else f"{currency} {phase.total_budget/1e6:.0f}M"
        
        output.append(f"""
### Phase {phase.phase_number}: {phase.phase_name} ({phase.start_year}-{phase.end_year}) — {budget_display}

**Strategic Objective:** {phase.strategic_objective}

**Key Partners:** {', '.join(phase.key_partners[:5])}
""")
        
        # Add quarterly details (first 4 quarters)
        for q in phase.quarters[:4]:
            q_budget = f"{currency} {q.budget/1e6:.0f}M" if q.budget >= 1e6 else f"{currency} {q.budget/1e3:.0f}K"
            
            output.append(f"""
**{q.quarter}:** (Budget: {q_budget})
""")
            for action in q.actions[:3]:
                action_budget = f"{currency} {action['budget']/1e6:.0f}M" if action['budget'] >= 1e6 else f"{currency} {action['budget']/1e3:.0f}K"
                output.append(f"""- {action['action']}
  - Responsible: {action['responsible']}
  - Budget: {action_budget}
  - Deliverable: {action['deliverable']}
""")
            
            if q.success_metrics:
                output.append(f"  - Success metrics: {', '.join(q.success_metrics[:2])}")
        
        # Success criteria
        if phase.success_criteria:
            output.append(f"""
**Phase {phase.phase_number} Success Criteria:**
""")
            for criterion in phase.success_criteria:
                output.append(f"- {criterion}")
    
    return "\n".join(output)

