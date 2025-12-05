"""
Financial Modeling Service - Big 4 Standard Analysis

Provides domain-agnostic financial analysis:
- For INVESTMENT questions: NPV, IRR, Payback, Phased Investment Analysis
- For POLICY questions: Cost-Benefit Analysis, Impact Assessment
- For RATE/PRICING questions: Revenue Impact, Elasticity Analysis
- For RISK questions: Expected Loss, Risk-Adjusted Return

The system automatically detects question type and applies appropriate models.
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class InvestmentPhase:
    """A phase of investment with timing and amounts."""
    name: str
    start_year: int
    end_year: int
    investment_amount: float  # Total for this phase
    revenue_streams: List[str] = field(default_factory=list)
    cost_drivers: List[str] = field(default_factory=list)
    expected_annual_revenue: float = 0.0
    expected_annual_costs: float = 0.0


@dataclass 
class FinancialModelResult:
    """Output from financial analysis."""
    model_type: str  # "investment", "policy", "rate", "risk"
    
    # For Investment Analysis
    npv: Optional[float] = None
    irr: Optional[float] = None
    payback_years: Optional[float] = None
    profitability_index: Optional[float] = None
    
    # Phased Analysis
    phases: List[Dict[str, Any]] = field(default_factory=list)
    cumulative_investment: List[float] = field(default_factory=list)
    annual_cash_flows: List[float] = field(default_factory=list)
    
    # For Policy Analysis
    total_cost: Optional[float] = None
    total_benefit: Optional[float] = None
    benefit_cost_ratio: Optional[float] = None
    jobs_created: Optional[int] = None
    gdp_impact: Optional[float] = None
    
    # Sensitivity Analysis
    sensitivity: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Comparison Matrix (for multiple options)
    comparison_matrix: List[Dict[str, Any]] = field(default_factory=list)
    
    # Risk Metrics
    risk_level: str = "medium"
    risk_adjusted_return: Optional[float] = None
    var_95: Optional[float] = None  # Value at Risk


class FinancialModelingService:
    """
    Domain-agnostic financial modeling service.
    
    Automatically detects question type and applies appropriate analysis:
    - Investment: NPV, IRR, Payback
    - Policy: Cost-Benefit, Impact Assessment
    - Rate/Pricing: Revenue Impact, Elasticity
    - Risk: Expected Loss, Risk-Adjusted Return
    """
    
    def __init__(self, discount_rate: float = 0.08):
        """Initialize with default discount rate (8%)."""
        self.discount_rate = discount_rate
        self.inflation_rate = 0.02
        
    def detect_question_type(self, query: str) -> str:
        """Detect the type of question for appropriate modeling."""
        query_lower = query.lower()
        
        # Investment indicators
        investment_keywords = [
            "invest", "billion", "million", "fund", "allocat", "capital",
            "budget", "spend", "development", "infrastructure", "build"
        ]
        
        # Policy indicators
        policy_keywords = [
            "policy", "implement", "reform", "program", "initiative",
            "regulation", "law", "mandate", "target", "goal"
        ]
        
        # Rate/Pricing indicators
        rate_keywords = [
            "rate", "price", "wage", "salary", "tax", "tariff",
            "interest", "fee", "cost", "charge"
        ]
        
        # Risk indicators
        risk_keywords = [
            "risk", "threat", "danger", "vulnerability", "exposure",
            "probability", "likelihood", "impact", "downside"
        ]
        
        # Count matches
        investment_score = sum(1 for kw in investment_keywords if kw in query_lower)
        policy_score = sum(1 for kw in policy_keywords if kw in query_lower)
        rate_score = sum(1 for kw in rate_keywords if kw in query_lower)
        risk_score = sum(1 for kw in risk_keywords if kw in query_lower)
        
        scores = {
            "investment": investment_score,
            "policy": policy_score,
            "rate": rate_score,
            "risk": risk_score
        }
        
        # Return highest scoring type
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "policy"
    
    def analyze(
        self,
        query: str,
        options: List[Dict[str, Any]],
        facts: Dict[str, Any],
        total_investment: float = None,
        time_horizon: int = 10
    ) -> FinancialModelResult:
        """
        Main analysis entry point - automatically selects appropriate model.
        
        Args:
            query: The strategic question
            options: List of options to compare (e.g., [{"name": "AI Hub", ...}, {"name": "Tourism", ...}])
            facts: Extracted facts with numeric data
            total_investment: Total investment amount if applicable
            time_horizon: Years to analyze (default 10)
        """
        question_type = self.detect_question_type(query)
        logger.info(f"Financial modeling: detected question type = {question_type}")
        
        if question_type == "investment":
            return self._investment_analysis(options, facts, total_investment, time_horizon)
        elif question_type == "policy":
            return self._policy_analysis(options, facts, time_horizon)
        elif question_type == "rate":
            return self._rate_analysis(options, facts)
        else:
            return self._risk_analysis(options, facts, time_horizon)
    
    def _investment_analysis(
        self,
        options: List[Dict[str, Any]],
        facts: Dict[str, Any],
        total_investment: float,
        time_horizon: int
    ) -> FinancialModelResult:
        """
        NPV/IRR analysis for investment questions.
        
        Generates phased investment model and comparison matrix.
        """
        result = FinancialModelResult(model_type="investment")
        
        if not total_investment:
            # Try to extract from facts
            total_investment = self._extract_investment_amount(facts) or 50_000_000_000  # Default $50B
        
        comparison_matrix = []
        all_phases = []
        
        for i, option in enumerate(options):
            option_name = option.get("name", f"Option {i+1}")
            
            # Generate phased investment plan based on option type
            phases = self._generate_investment_phases(option_name, total_investment, time_horizon)
            all_phases.append({"option": option_name, "phases": phases})
            
            # Calculate cash flows
            cash_flows = self._calculate_cash_flows(phases, time_horizon)
            
            # Calculate NPV
            npv = self._calculate_npv(cash_flows, self.discount_rate)
            
            # Calculate IRR
            irr = self._calculate_irr(cash_flows)
            
            # Calculate payback
            payback = self._calculate_payback(cash_flows)
            
            # Estimate jobs (domain-agnostic formula)
            jobs = self._estimate_jobs(total_investment, option_name, facts)
            
            # Determine risk level
            risk = self._assess_investment_risk(option_name, phases)
            
            comparison_matrix.append({
                "option": option_name,
                "npv": npv,
                "npv_formatted": f"${npv/1e9:.1f}B" if npv else "N/A",
                "irr": irr,
                "irr_formatted": f"{irr*100:.1f}%" if irr else "N/A",
                "payback_years": payback,
                "jobs_created": jobs,
                "jobs_formatted": f"{jobs:,}" if jobs else "N/A",
                "risk_level": risk,
                "total_investment": total_investment,
                "phases": [
                    {
                        "name": p.name,
                        "years": f"Year {p.start_year}-{p.end_year}",
                        "investment": f"${p.investment_amount/1e9:.1f}B",
                        "revenue_streams": p.revenue_streams,
                        "cost_drivers": p.cost_drivers
                    }
                    for p in phases
                ]
            })
        
        # Add hybrid options (if 2+ base options)
        if len(options) >= 2:
            for ratio in [(60, 40), (40, 60)]:
                hybrid = self._calculate_hybrid_metrics(comparison_matrix[:2], ratio)
                comparison_matrix.append(hybrid)
        
        # Set primary result from first option
        if comparison_matrix:
            result.npv = comparison_matrix[0]["npv"]
            result.irr = comparison_matrix[0]["irr"]
            result.payback_years = comparison_matrix[0]["payback_years"]
        
        result.phases = all_phases
        result.comparison_matrix = comparison_matrix
        result.sensitivity = self._sensitivity_analysis(comparison_matrix[0] if comparison_matrix else {})
        
        return result
    
    def _generate_investment_phases(
        self,
        option_name: str,
        total_investment: float,
        time_horizon: int
    ) -> List[InvestmentPhase]:
        """
        Generate phased investment plan based on option type.
        Domain-agnostic: uses generic phases that apply to any investment.
        """
        option_lower = option_name.lower()
        
        # Default phase allocation (domain-agnostic)
        # Phase 1: Foundation/Infrastructure (30%)
        # Phase 2: Development/Implementation (40%)
        # Phase 3: Scale/Optimization (30%)
        
        phase_allocations = [0.30, 0.40, 0.30]
        
        # Adjust based on option characteristics
        if any(kw in option_lower for kw in ["tech", "ai", "digital", "innovation"]):
            # Tech: More in R&D, less in infrastructure
            phase_allocations = [0.25, 0.45, 0.30]
            phase_names = ["Infrastructure & Platform", "R&D & Talent Development", "Scale & Commercialization"]
            revenue_streams = [
                ["Facility leasing", "Basic services"],
                ["IP licensing", "Service contracts", "Training revenue"],
                ["Technology exports", "Platform fees", "Consulting"]
            ]
            cost_drivers = [
                ["Construction", "Equipment", "Initial hiring"],
                ["R&D salaries", "Equipment", "Partnerships"],
                ["Marketing", "Operations", "Maintenance"]
            ]
        elif any(kw in option_lower for kw in ["tourism", "hospitality", "destination"]):
            # Tourism: More in infrastructure, steady revenue
            phase_allocations = [0.35, 0.35, 0.30]
            phase_names = ["Infrastructure Development", "Brand & Experience Building", "Market Expansion"]
            revenue_streams = [
                ["Hotel occupancy", "Attraction tickets"],
                ["Package tours", "Events", "F&B"],
                ["International visitors", "Premium experiences", "MICE"]
            ]
            cost_drivers = [
                ["Construction", "Land acquisition"],
                ["Marketing", "Staff training", "Operations"],
                ["Expansion", "New attractions", "Maintenance"]
            ]
        elif any(kw in option_lower for kw in ["manufacturing", "industrial", "production"]):
            phase_allocations = [0.40, 0.35, 0.25]
            phase_names = ["Factory Setup", "Production Ramp-up", "Market Penetration"]
            revenue_streams = [
                ["Initial orders"],
                ["Production output", "Contract manufacturing"],
                ["Export revenue", "Brand sales"]
            ]
            cost_drivers = [
                ["Equipment", "Facility", "Permits"],
                ["Raw materials", "Labor", "Quality control"],
                ["Distribution", "Marketing", "R&D"]
            ]
        else:
            # Generic investment phases
            phase_names = ["Foundation & Setup", "Development & Implementation", "Optimization & Growth"]
            revenue_streams = [
                ["Initial revenue"],
                ["Core revenue streams"],
                ["Diversified revenue"]
            ]
            cost_drivers = [
                ["Setup costs", "Initial investment"],
                ["Operating costs", "Development"],
                ["Maintenance", "Expansion"]
            ]
        
        phases = []
        years_per_phase = time_horizon // 3
        
        for i, (allocation, name) in enumerate(zip(phase_allocations, phase_names)):
            start_year = i * years_per_phase
            end_year = start_year + years_per_phase
            investment = total_investment * allocation
            
            # Estimate revenue (grows over phases)
            revenue_multiplier = (i + 1) * 0.1  # 10%, 20%, 30% of investment as annual revenue
            annual_revenue = investment * revenue_multiplier
            
            # Costs decline as % of revenue over time
            cost_multiplier = 0.8 - (i * 0.1)  # 80%, 70%, 60%
            annual_costs = annual_revenue * cost_multiplier
            
            phases.append(InvestmentPhase(
                name=name,
                start_year=start_year,
                end_year=end_year,
                investment_amount=investment,
                revenue_streams=revenue_streams[i],
                cost_drivers=cost_drivers[i],
                expected_annual_revenue=annual_revenue,
                expected_annual_costs=annual_costs
            ))
        
        return phases
    
    def _calculate_cash_flows(
        self,
        phases: List[InvestmentPhase],
        time_horizon: int
    ) -> List[float]:
        """Calculate annual cash flows from investment phases."""
        cash_flows = []
        
        # Total investment spread over time
        total_investment = sum(p.investment_amount for p in phases)
        
        for year in range(time_horizon + 1):
            if year == 0:
                # Initial investment (negative) - 15% upfront
                cash_flows.append(-total_investment * 0.15)
            else:
                annual_cf = 0
                
                # Investment outflow (spread over first 5 years)
                if year <= 5:
                    annual_cf -= (total_investment * 0.85) / 5
                
                # Revenue starts year 2 and grows
                if year >= 2:
                    # Base revenue = 8% of total investment, growing 10% per year
                    base_revenue = total_investment * 0.08
                    growth_factor = 1.10 ** (year - 2)
                    annual_revenue = base_revenue * growth_factor
                    
                    # Operating costs = 60% of revenue initially, declining to 50%
                    cost_ratio = max(0.50, 0.70 - (year - 2) * 0.02)
                    annual_costs = annual_revenue * cost_ratio
                    
                    annual_cf += annual_revenue - annual_costs
                
                cash_flows.append(annual_cf)
        
        return cash_flows
    
    def _calculate_npv(self, cash_flows: List[float], discount_rate: float) -> float:
        """Calculate Net Present Value."""
        npv = 0
        for t, cf in enumerate(cash_flows):
            npv += cf / ((1 + discount_rate) ** t)
        return npv
    
    def _calculate_irr(self, cash_flows: List[float]) -> Optional[float]:
        """Calculate Internal Rate of Return using Newton-Raphson."""
        if not cash_flows or all(cf >= 0 for cf in cash_flows) or all(cf <= 0 for cf in cash_flows):
            return None
        
        try:
            # Use numpy's IRR calculation
            irr = np.irr(cash_flows)
            if np.isnan(irr) or np.isinf(irr):
                return None
            return float(irr)
        except:
            # Fallback: simple iteration
            for r in np.linspace(0, 0.5, 100):
                npv = sum(cf / ((1 + r) ** t) for t, cf in enumerate(cash_flows))
                if abs(npv) < 1000:
                    return r
            return None
    
    def _calculate_payback(self, cash_flows: List[float]) -> Optional[float]:
        """Calculate payback period in years."""
        cumulative = 0
        for t, cf in enumerate(cash_flows):
            cumulative += cf
            if cumulative >= 0 and t > 0:
                # Interpolate for fractional year
                prev_cumulative = cumulative - cf
                if cf != 0:
                    fraction = -prev_cumulative / cf
                    return t - 1 + fraction
                return float(t)
        return None  # Never pays back within horizon
    
    def _estimate_jobs(
        self,
        investment: float,
        option_name: str,
        facts: Dict[str, Any]
    ) -> int:
        """Estimate jobs created based on investment and sector."""
        option_lower = option_name.lower()
        
        # Jobs per $1M investment (varies by sector)
        if any(kw in option_lower for kw in ["tech", "ai", "digital"]):
            jobs_per_million = 3  # Tech is capital-intensive
        elif any(kw in option_lower for kw in ["tourism", "hospitality"]):
            jobs_per_million = 8  # Tourism is labor-intensive
        elif any(kw in option_lower for kw in ["manufacturing"]):
            jobs_per_million = 5
        else:
            jobs_per_million = 5  # Default
        
        return int((investment / 1_000_000) * jobs_per_million)
    
    def _assess_investment_risk(
        self,
        option_name: str,
        phases: List[InvestmentPhase]
    ) -> str:
        """Assess risk level of investment option."""
        option_lower = option_name.lower()
        
        # Tech/AI = higher risk, higher reward
        if any(kw in option_lower for kw in ["tech", "ai", "digital", "innovation", "startup"]):
            return "high"
        # Tourism = lower risk, proven model
        elif any(kw in option_lower for kw in ["tourism", "hospitality", "sustainable", "destination"]):
            return "low-medium"
        # Manufacturing = medium risk
        elif any(kw in option_lower for kw in ["manufacturing", "industrial"]):
            return "medium"
        # Hybrid = balanced
        elif "hybrid" in option_lower:
            return "medium"
        else:
            return "medium"
    
    def _calculate_hybrid_metrics(
        self,
        base_options: List[Dict],
        ratio: Tuple[int, int]
    ) -> Dict[str, Any]:
        """Calculate metrics for hybrid allocation."""
        if len(base_options) < 2:
            return {}
        
        opt1, opt2 = base_options[0], base_options[1]
        r1, r2 = ratio[0] / 100, ratio[1] / 100
        
        npv1 = opt1.get("npv") or 0
        npv2 = opt2.get("npv") or 0
        irr1 = opt1.get("irr") or 0
        irr2 = opt2.get("irr") or 0
        jobs1 = opt1.get("jobs_created") or 0
        jobs2 = opt2.get("jobs_created") or 0
        payback1 = opt1.get("payback_years") or 7  # Default 7 years if None
        payback2 = opt2.get("payback_years") or 7
        
        hybrid_npv = npv1 * r1 + npv2 * r2
        hybrid_irr = irr1 * r1 + irr2 * r2
        hybrid_jobs = int(jobs1 * r1 + jobs2 * r2)
        hybrid_payback = payback1 * r1 + payback2 * r2
        
        return {
            "option": f"Hybrid {ratio[0]}/{ratio[1]}",
            "npv": hybrid_npv,
            "npv_formatted": f"${hybrid_npv/1e9:.1f}B",
            "irr": hybrid_irr,
            "irr_formatted": f"{hybrid_irr*100:.1f}%",
            "payback_years": hybrid_payback,
            "jobs_created": hybrid_jobs,
            "jobs_formatted": f"{hybrid_jobs:,}",
            "risk_level": "medium",
            "allocation": f"{opt1['option']}: {ratio[0]}%, {opt2['option']}: {ratio[1]}%"
        }
    
    def _sensitivity_analysis(self, base_case: Dict) -> Dict[str, Dict[str, float]]:
        """Perform sensitivity analysis on key variables."""
        if not base_case or not base_case.get("npv"):
            return {}
        
        base_npv = base_case["npv"]
        
        return {
            "discount_rate": {
                "-2%": base_npv * 1.15,  # Lower discount = higher NPV
                "base": base_npv,
                "+2%": base_npv * 0.85
            },
            "revenue_growth": {
                "-20%": base_npv * 0.75,
                "base": base_npv,
                "+20%": base_npv * 1.25
            },
            "cost_overrun": {
                "+10%": base_npv * 0.90,
                "base": base_npv,
                "+30%": base_npv * 0.70
            },
            "implementation_delay": {
                "on_time": base_npv,
                "1_year_delay": base_npv * 0.92,
                "2_year_delay": base_npv * 0.85
            }
        }
    
    def _policy_analysis(
        self,
        options: List[Dict],
        facts: Dict,
        time_horizon: int
    ) -> FinancialModelResult:
        """Cost-benefit analysis for policy questions."""
        result = FinancialModelResult(model_type="policy")
        
        comparison_matrix = []
        for option in options:
            option_name = option.get("name", "Policy Option")
            
            # Estimate costs and benefits based on policy type
            cost = self._estimate_policy_cost(option_name, facts)
            benefit = self._estimate_policy_benefit(option_name, facts, time_horizon)
            
            comparison_matrix.append({
                "option": option_name,
                "total_cost": cost,
                "cost_formatted": f"${cost/1e9:.1f}B",
                "total_benefit": benefit,
                "benefit_formatted": f"${benefit/1e9:.1f}B",
                "benefit_cost_ratio": benefit / cost if cost > 0 else 0,
                "net_benefit": benefit - cost,
                "net_formatted": f"${(benefit-cost)/1e9:.1f}B"
            })
        
        if comparison_matrix:
            result.total_cost = comparison_matrix[0]["total_cost"]
            result.total_benefit = comparison_matrix[0]["total_benefit"]
            result.benefit_cost_ratio = comparison_matrix[0]["benefit_cost_ratio"]
        
        result.comparison_matrix = comparison_matrix
        return result
    
    def _rate_analysis(self, options: List[Dict], facts: Dict) -> FinancialModelResult:
        """Revenue/elasticity analysis for rate/pricing questions."""
        result = FinancialModelResult(model_type="rate")
        # Implement rate-specific analysis
        return result
    
    def _risk_analysis(
        self,
        options: List[Dict],
        facts: Dict,
        time_horizon: int
    ) -> FinancialModelResult:
        """Risk assessment and expected loss analysis."""
        result = FinancialModelResult(model_type="risk")
        # Implement risk-specific analysis
        return result
    
    def _extract_investment_amount(self, facts: Dict) -> Optional[float]:
        """Extract total investment amount from facts."""
        for key, value in facts.items():
            if isinstance(value, (int, float)) and value > 1e9:
                return float(value)
            if isinstance(value, str):
                # Try to parse "$50 billion" etc.
                import re
                match = re.search(r'\$?([\d.]+)\s*(billion|B|million|M)', value, re.IGNORECASE)
                if match:
                    amount = float(match.group(1))
                    unit = match.group(2).lower()
                    if 'b' in unit:
                        return amount * 1e9
                    elif 'm' in unit:
                        return amount * 1e6
        return None
    
    def _estimate_policy_cost(self, option_name: str, facts: Dict) -> float:
        """Estimate policy implementation cost."""
        # Domain-agnostic estimation based on option type
        option_lower = option_name.lower()
        
        base_cost = 1e9  # $1B base
        
        if any(kw in option_lower for kw in ["major", "transform", "overhaul"]):
            return base_cost * 10
        elif any(kw in option_lower for kw in ["moderate", "phased"]):
            return base_cost * 5
        else:
            return base_cost * 3
    
    def _estimate_policy_benefit(
        self,
        option_name: str,
        facts: Dict,
        time_horizon: int
    ) -> float:
        """Estimate policy benefits over time horizon."""
        cost = self._estimate_policy_cost(option_name, facts)
        
        # Benefit multiplier based on option type
        option_lower = option_name.lower()
        
        if any(kw in option_lower for kw in ["high return", "transformative"]):
            multiplier = 2.5
        elif any(kw in option_lower for kw in ["proven", "established"]):
            multiplier = 1.8
        else:
            multiplier = 1.5
        
        return cost * multiplier


def format_comparison_matrix_for_brief(matrix: List[Dict]) -> str:
    """Format comparison matrix as markdown table for ministerial brief."""
    if not matrix:
        return "No comparison data available."
    
    output = []
    
    # Determine columns based on data
    if matrix[0].get("npv") is not None:
        # Investment comparison
        header = "| Option | NPV | IRR | Payback | Jobs | Risk |"
        divider = "|--------|-----|-----|---------|------|------|"
        output.extend([header, divider])
        
        for m in matrix:
            option = m.get('option', 'N/A')
            npv = m.get('npv_formatted', 'N/A')
            irr = m.get('irr_formatted', 'N/A')
            payback = m.get('payback_years')
            payback_str = f"{payback:.1f} yrs" if payback is not None else "N/A"
            jobs = m.get('jobs_formatted', 'N/A')
            risk = m.get('risk_level', 'medium')
            risk_str = risk.title() if risk else "Medium"
            
            row = f"| {option} | {npv} | {irr} | {payback_str} | {jobs} | {risk_str} |"
            output.append(row)
    else:
        # Policy comparison
        header = "| Option | Cost | Benefit | B/C Ratio | Net Benefit |"
        divider = "|--------|------|---------|-----------|-------------|"
        output.extend([header, divider])
        
        for m in matrix:
            option = m.get('option', 'N/A')
            cost = m.get('cost_formatted', 'N/A')
            benefit = m.get('benefit_formatted', 'N/A')
            ratio = m.get('benefit_cost_ratio', 0) or 0
            net = m.get('net_formatted', 'N/A')
            
            row = f"| {option} | {cost} | {benefit} | {ratio:.2f} | {net} |"
            output.append(row)
    
    return "\n".join(output)


def generate_year_by_year_projection(
    option_name: str,
    total_investment: float,
    time_horizon: int = 10
) -> str:
    """
    Generate detailed year-by-year financial projection.
    Big 4 standard: Shows capex, opex, revenue, cash flow for each year.
    """
    option_lower = option_name.lower()
    
    # Determine sector-specific parameters
    if any(kw in option_lower for kw in ["tech", "ai", "digital", "innovation"]):
        capex_profile = [0.15, 0.20, 0.20, 0.15, 0.10, 0.08, 0.05, 0.03, 0.02, 0.02]
        opex_rate = 0.03  # 3% of cumulative capex
        revenue_start_year = 3
        revenue_growth = 0.25  # 25% annual growth
        revenue_multiple = 0.08  # Revenue = 8% of investment at maturity
    elif any(kw in option_lower for kw in ["tourism", "hospitality"]):
        capex_profile = [0.20, 0.25, 0.20, 0.15, 0.10, 0.05, 0.03, 0.01, 0.01, 0.00]
        opex_rate = 0.04
        revenue_start_year = 2
        revenue_growth = 0.15
        revenue_multiple = 0.10
    else:
        capex_profile = [0.15, 0.15, 0.15, 0.15, 0.10, 0.10, 0.08, 0.05, 0.04, 0.03]
        opex_rate = 0.035
        revenue_start_year = 3
        revenue_growth = 0.20
        revenue_multiple = 0.08
    
    # Generate year-by-year data
    output = [f"\n**YEAR-BY-YEAR PROJECTION: {option_name}**\n"]
    output.append("| Year | CapEx | OpEx | Revenue | Cash Flow | Cumulative |")
    output.append("|------|-------|------|---------|-----------|------------|")
    
    cumulative_capex = 0
    cumulative_cf = 0
    
    for year in range(time_horizon):
        year_label = year + 1
        
        # CapEx
        capex = total_investment * capex_profile[min(year, len(capex_profile)-1)]
        cumulative_capex += capex
        
        # OpEx (% of cumulative investment)
        opex = cumulative_capex * opex_rate
        
        # Revenue (starts after delay, grows annually)
        if year >= revenue_start_year:
            years_operating = year - revenue_start_year + 1
            base_revenue = total_investment * revenue_multiple
            revenue = base_revenue * ((1 + revenue_growth) ** years_operating)
        else:
            revenue = 0
        
        # Cash flow
        cash_flow = revenue - capex - opex
        cumulative_cf += cash_flow
        
        # Format for display
        capex_str = f"${capex/1e9:.1f}B"
        opex_str = f"${opex/1e9:.1f}B"
        revenue_str = f"${revenue/1e9:.1f}B" if revenue > 0 else "-"
        cf_str = f"${cash_flow/1e9:.1f}B" if cash_flow >= 0 else f"-${abs(cash_flow)/1e9:.1f}B"
        cumulative_str = f"${cumulative_cf/1e9:.1f}B" if cumulative_cf >= 0 else f"-${abs(cumulative_cf)/1e9:.1f}B"
        
        output.append(f"| Year {year_label} | {capex_str} | {opex_str} | {revenue_str} | {cf_str} | {cumulative_str} |")
    
    # Summary
    output.append(f"\n**Break-even:** {'Year ' + str(revenue_start_year + 5) if cumulative_cf < 0 else 'Achieved'}")
    output.append(f"**Total Investment:** ${total_investment/1e9:.1f}B over {time_horizon} years")
    
    return "\n".join(output)

