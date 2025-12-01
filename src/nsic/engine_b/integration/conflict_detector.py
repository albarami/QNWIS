"""
Conflict Detection for Engine A/B Integration
Determines when Engine B's quantitative results conflict with Engine A's qualitative recommendations.
Triggers Engine A Prime (focused validation debate) when significant conflicts are detected.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# CONFLICT THRESHOLDS (from spec)
# ============================================================================

CONFLICT_THRESHOLDS = {
    # Monte Carlo: If success probability is too low
    "feasibility": 0.30,      # If success_rate < 30%, trigger debate
    
    # Forecasting: If trend contradicts Engine A's claim
    "trend_mismatch": True,   # If forecast trend contradicts claim (e.g., "growth" but trend="decreasing")
    
    # Thresholds: If any policy threshold is breached
    "threshold_breach": True, # If critical_threshold is not None and breached
    
    # Benchmarking: If Qatar is statistical outlier vs peers
    "benchmark_outlier": 2.0, # If Qatar is >2 std deviations from peer mean
    
    # Sensitivity: If top driver wasn't mentioned in Engine A analysis
    "ignored_driver": 0.40,   # If top driver has >40% impact but wasn't discussed
    
    # Correlation: If key relationship contradicts assumption
    "correlation_contradiction": 0.50,  # If r > 0.5 but Engine A assumed independence
}


class ConflictSeverity(Enum):
    """Severity levels for conflicts."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Conflict:
    """Represents a single conflict between Engine A and Engine B results."""
    
    # Conflict type
    conflict_type: str
    
    # Source service
    source_service: str
    
    # Severity
    severity: ConflictSeverity
    
    # What Engine A claimed
    engine_a_claim: str
    
    # What Engine B found
    engine_b_finding: str
    
    # Quantitative evidence
    evidence: dict = field(default_factory=dict)
    
    # Recommendation
    recommendation: str = ""
    
    # Should this trigger Engine A Prime?
    triggers_prime: bool = False


@dataclass
class ConflictReport:
    """Complete conflict analysis report."""
    
    # All detected conflicts
    conflicts: list[Conflict]
    
    # High-severity conflicts
    critical_conflicts: list[Conflict]
    
    # Should Engine A Prime be triggered?
    should_trigger_prime: bool
    
    # Prime debate focus (if triggered)
    prime_focus: Optional[str]
    prime_questions: list[str]
    
    # Overall alignment score (0-100)
    alignment_score: float
    
    # Summary
    summary: str


class ConflictDetector:
    """
    Detects conflicts between Engine A qualitative analysis and Engine B quantitative results.
    
    Engine A provides:
    - Recommendations (text)
    - Key claims (extracted)
    - Mentioned drivers
    - Trend assumptions
    
    Engine B provides:
    - Monte Carlo: success_rate, var_95, variable_contributions
    - Sensitivity: top_drivers, parameter_impacts
    - Forecasting: trend, forecasts
    - Thresholds: risk_level, critical_thresholds
    - Benchmarking: performance, is_outlier, gap_to_mean
    - Correlation: driver_analysis, significant_pairs
    """
    
    def __init__(self, thresholds: Optional[dict] = None):
        """Initialize conflict detector with custom thresholds if provided."""
        self.thresholds = thresholds or CONFLICT_THRESHOLDS
    
    def detect_conflicts(
        self,
        engine_a_result: dict,
        engine_b_result: dict
    ) -> ConflictReport:
        """
        Detect conflicts between Engine A and Engine B results.
        
        Args:
            engine_a_result: Output from Engine A debate
            engine_b_result: Output from Engine B compute services
            
        Returns:
            ConflictReport with all detected conflicts and recommendations
        """
        conflicts = []
        
        # Check each potential conflict type
        if "monte_carlo" in engine_b_result:
            conflicts.extend(self._check_monte_carlo_conflicts(
                engine_a_result, engine_b_result["monte_carlo"]
            ))
        
        if "sensitivity" in engine_b_result:
            conflicts.extend(self._check_sensitivity_conflicts(
                engine_a_result, engine_b_result["sensitivity"]
            ))
        
        if "forecasting" in engine_b_result:
            conflicts.extend(self._check_forecasting_conflicts(
                engine_a_result, engine_b_result["forecasting"]
            ))
        
        if "thresholds" in engine_b_result:
            conflicts.extend(self._check_threshold_conflicts(
                engine_a_result, engine_b_result["thresholds"]
            ))
        
        if "benchmarking" in engine_b_result:
            conflicts.extend(self._check_benchmarking_conflicts(
                engine_a_result, engine_b_result["benchmarking"]
            ))
        
        if "correlation" in engine_b_result:
            conflicts.extend(self._check_correlation_conflicts(
                engine_a_result, engine_b_result["correlation"]
            ))
        
        # Identify critical conflicts
        critical_conflicts = [
            c for c in conflicts 
            if c.severity in [ConflictSeverity.HIGH, ConflictSeverity.CRITICAL]
        ]
        
        # Determine if Engine A Prime should be triggered
        should_trigger, prime_focus, prime_questions = self._should_trigger_prime(conflicts)
        
        # Calculate alignment score
        alignment_score = self._calculate_alignment_score(conflicts)
        
        # Generate summary
        summary = self._generate_summary(conflicts, alignment_score)
        
        return ConflictReport(
            conflicts=conflicts,
            critical_conflicts=critical_conflicts,
            should_trigger_prime=should_trigger,
            prime_focus=prime_focus,
            prime_questions=prime_questions,
            alignment_score=alignment_score,
            summary=summary,
        )
    
    def _check_monte_carlo_conflicts(
        self,
        engine_a: dict,
        monte_carlo: dict
    ) -> list[Conflict]:
        """Check for feasibility conflicts from Monte Carlo."""
        conflicts = []
        
        success_rate = monte_carlo.get("success_rate", 1.0)
        
        # Check if Engine A claims success but Monte Carlo shows low probability
        if success_rate < self.thresholds["feasibility"]:
            # Extract Engine A's recommendation sentiment
            recommendation = engine_a.get("recommendation", "")
            claims_success = any(
                word in recommendation.lower() 
                for word in ["will succeed", "achievable", "feasible", "likely", "confident"]
            )
            
            if claims_success or success_rate < 0.20:  # Always flag if very low
                conflicts.append(Conflict(
                    conflict_type="feasibility",
                    source_service="monte_carlo",
                    severity=ConflictSeverity.CRITICAL if success_rate < 0.20 else ConflictSeverity.HIGH,
                    engine_a_claim="Policy is feasible/achievable",
                    engine_b_finding=f"Only {success_rate:.1%} probability of success",
                    evidence={
                        "success_rate": success_rate,
                        "var_95": monte_carlo.get("var_95"),
                        "simulations": monte_carlo.get("n_simulations"),
                    },
                    recommendation="Re-evaluate assumptions or adjust targets",
                    triggers_prime=True,
                ))
        
        # Check for high risk (VaR)
        var_95 = monte_carlo.get("var_95")
        if var_95 is not None and var_95 < 0:
            conflicts.append(Conflict(
                conflict_type="risk_warning",
                source_service="monte_carlo",
                severity=ConflictSeverity.MEDIUM,
                engine_a_claim="Risk assessment not quantified",
                engine_b_finding=f"5% chance of outcome below {var_95:.3f}",
                evidence={"var_95": var_95, "cvar_95": monte_carlo.get("cvar_95")},
                recommendation="Include downside risk in analysis",
                triggers_prime=False,
            ))
        
        return conflicts
    
    def _check_sensitivity_conflicts(
        self,
        engine_a: dict,
        sensitivity: dict
    ) -> list[Conflict]:
        """Check if top drivers were ignored in Engine A analysis."""
        conflicts = []
        
        top_drivers = sensitivity.get("top_drivers", [])
        parameter_impacts = sensitivity.get("parameter_impacts", [])
        
        # Get topics/drivers mentioned in Engine A
        engine_a_text = str(engine_a.get("synthesis", "")) + str(engine_a.get("recommendation", ""))
        engine_a_text_lower = engine_a_text.lower()
        
        for driver in top_drivers[:3]:  # Check top 3 drivers
            # Find impact for this driver
            impact = next(
                (p for p in parameter_impacts if p.get("name") == driver),
                {}
            )
            elasticity = abs(impact.get("elasticity", 0))
            
            # Check if driver was mentioned
            driver_mentioned = driver.lower().replace("_", " ") in engine_a_text_lower
            
            if elasticity > self.thresholds["ignored_driver"] and not driver_mentioned:
                conflicts.append(Conflict(
                    conflict_type="ignored_driver",
                    source_service="sensitivity",
                    severity=ConflictSeverity.MEDIUM,
                    engine_a_claim=f"Analysis focused on other factors",
                    engine_b_finding=f"'{driver}' is a top driver with {elasticity:.0%} elasticity",
                    evidence={
                        "driver": driver,
                        "elasticity": elasticity,
                        "swing": impact.get("swing"),
                    },
                    recommendation=f"Include '{driver}' in policy discussion",
                    triggers_prime=elasticity > 0.6,  # Only trigger if very impactful
                ))
        
        return conflicts
    
    def _check_forecasting_conflicts(
        self,
        engine_a: dict,
        forecasting: dict
    ) -> list[Conflict]:
        """Check for trend contradictions."""
        conflicts = []
        
        forecast_trend = forecasting.get("trend", "stable")
        
        # Check for trend claims in Engine A
        recommendation = str(engine_a.get("recommendation", "")).lower()
        synthesis = str(engine_a.get("synthesis", "")).lower()
        
        # Simple trend claim extraction
        claims_growth = any(
            word in recommendation or word in synthesis
            for word in ["will grow", "will increase", "upward trend", "positive growth"]
        )
        claims_decline = any(
            word in recommendation or word in synthesis
            for word in ["will decline", "will decrease", "downward trend", "negative growth"]
        )
        
        # Check for contradictions
        if self.thresholds["trend_mismatch"]:
            if claims_growth and forecast_trend == "decreasing":
                conflicts.append(Conflict(
                    conflict_type="trend_mismatch",
                    source_service="forecasting",
                    severity=ConflictSeverity.HIGH,
                    engine_a_claim="Expects growth/increase",
                    engine_b_finding=f"Forecast shows {forecast_trend} trend (slope: {forecasting.get('trend_slope', 0):.4f})",
                    evidence={
                        "trend": forecast_trend,
                        "slope": forecasting.get("trend_slope"),
                        "mape": forecasting.get("mape"),
                    },
                    recommendation="Review assumptions about future trajectory",
                    triggers_prime=True,
                ))
            
            if claims_decline and forecast_trend == "increasing":
                conflicts.append(Conflict(
                    conflict_type="trend_mismatch",
                    source_service="forecasting",
                    severity=ConflictSeverity.HIGH,
                    engine_a_claim="Expects decline/decrease",
                    engine_b_finding=f"Forecast shows {forecast_trend} trend",
                    evidence={
                        "trend": forecast_trend,
                        "slope": forecasting.get("trend_slope"),
                    },
                    recommendation="Review assumptions about future trajectory",
                    triggers_prime=True,
                ))
        
        return conflicts
    
    def _check_threshold_conflicts(
        self,
        engine_a: dict,
        thresholds: dict
    ) -> list[Conflict]:
        """Check for threshold breaches."""
        conflicts = []
        
        risk_level = thresholds.get("risk_level", "safe")
        critical_thresholds = thresholds.get("critical_thresholds", [])
        
        if self.thresholds["threshold_breach"]:
            for threshold in critical_thresholds:
                if threshold.get("currently_violated"):
                    conflicts.append(Conflict(
                        conflict_type="threshold_breach",
                        source_service="thresholds",
                        severity=ConflictSeverity.CRITICAL,
                        engine_a_claim="Policy within acceptable bounds",
                        engine_b_finding=f"Threshold breached: {threshold.get('constraint_description')}",
                        evidence={
                            "threshold": threshold.get("threshold_value"),
                            "constraint": threshold.get("constraint_expression"),
                            "severity": threshold.get("severity"),
                        },
                        recommendation="Address threshold violation before proceeding",
                        triggers_prime=True,
                    ))
                elif threshold.get("margin_percent", 100) < 10:
                    conflicts.append(Conflict(
                        conflict_type="threshold_warning",
                        source_service="thresholds",
                        severity=ConflictSeverity.MEDIUM,
                        engine_a_claim="Safe operating margin assumed",
                        engine_b_finding=f"Only {threshold.get('margin_percent'):.1f}% margin to threshold",
                        evidence=threshold,
                        recommendation="Consider buffer before threshold",
                        triggers_prime=False,
                    ))
        
        return conflicts
    
    def _check_benchmarking_conflicts(
        self,
        engine_a: dict,
        benchmarking: dict
    ) -> list[Conflict]:
        """Check for benchmarking outliers and gaps."""
        conflicts = []
        
        metric_benchmarks = benchmarking.get("metric_benchmarks", [])
        
        for mb in metric_benchmarks:
            # Check if Qatar is an outlier
            if mb.get("is_outlier") and abs(mb.get("z_score", 0)) > self.thresholds["benchmark_outlier"]:
                direction = mb.get("outlier_direction", "")
                performance = mb.get("performance", "")
                
                # Only flag if below average and outlier
                if direction == "below" or performance in ["below_average", "lagging"]:
                    conflicts.append(Conflict(
                        conflict_type="benchmark_outlier",
                        source_service="benchmarking",
                        severity=ConflictSeverity.MEDIUM,
                        engine_a_claim=f"Qatar's {mb.get('metric_name')} is competitive",
                        engine_b_finding=f"Qatar is {abs(mb.get('z_score', 0)):.1f} std below peer mean",
                        evidence={
                            "metric": mb.get("metric_name"),
                            "qatar_value": mb.get("qatar_value"),
                            "peer_mean": mb.get("peer_mean"),
                            "z_score": mb.get("z_score"),
                            "percentile": mb.get("qatar_percentile"),
                        },
                        recommendation=f"Address gap in {mb.get('metric_name')}",
                        triggers_prime=abs(mb.get("z_score", 0)) > 3.0,
                    ))
        
        return conflicts
    
    def _check_correlation_conflicts(
        self,
        engine_a: dict,
        correlation: dict
    ) -> list[Conflict]:
        """Check for correlation contradictions."""
        conflicts = []
        
        driver_analysis = correlation.get("driver_analysis", {})
        top_positive = driver_analysis.get("top_positive_drivers", [])
        top_negative = driver_analysis.get("top_negative_drivers", [])
        
        # Check if Engine A assumed wrong relationship direction
        engine_a_text = str(engine_a.get("synthesis", "")).lower()
        
        # Look for statements about drivers
        for driver in top_negative[:2]:
            # Check if Engine A assumed positive relationship
            positive_assumption = (
                f"increasing {driver}" in engine_a_text or
                f"higher {driver}" in engine_a_text or
                f"{driver} will help" in engine_a_text
            )
            
            if positive_assumption:
                driver_info = next(
                    (d for d in driver_analysis.get("drivers", []) if d.get("variable") == driver),
                    {}
                )
                r = driver_info.get("correlation", 0)
                
                if abs(r) > self.thresholds["correlation_contradiction"]:
                    conflicts.append(Conflict(
                        conflict_type="correlation_contradiction",
                        source_service="correlation",
                        severity=ConflictSeverity.HIGH,
                        engine_a_claim=f"Assumed positive relationship with {driver}",
                        engine_b_finding=f"Correlation is negative (r={r:.2f})",
                        evidence={
                            "variable": driver,
                            "correlation": r,
                            "p_value": driver_info.get("p_value"),
                        },
                        recommendation=f"Re-examine causal relationship with {driver}",
                        triggers_prime=True,
                    ))
        
        return conflicts
    
    def _should_trigger_prime(
        self,
        conflicts: list[Conflict]
    ) -> tuple[bool, Optional[str], list[str]]:
        """
        Determine if Engine A Prime should be triggered.
        
        Returns:
            (should_trigger, focus_area, questions_to_address)
        """
        triggering_conflicts = [c for c in conflicts if c.triggers_prime]
        
        if not triggering_conflicts:
            return False, None, []
        
        # Count by type
        high_severity = [
            c for c in triggering_conflicts 
            if c.severity in [ConflictSeverity.HIGH, ConflictSeverity.CRITICAL]
        ]
        medium_severity = [
            c for c in triggering_conflicts 
            if c.severity == ConflictSeverity.MEDIUM
        ]
        
        # Trigger if ANY high-severity OR 2+ medium-severity
        should_trigger = len(high_severity) > 0 or len(medium_severity) >= 2
        
        if not should_trigger:
            return False, None, []
        
        # Determine focus area (most severe conflict)
        focus_conflict = max(triggering_conflicts, key=lambda c: c.severity.value)
        focus_area = focus_conflict.conflict_type
        
        # Generate questions for Engine A Prime to address
        questions = []
        for conflict in triggering_conflicts:
            if conflict.conflict_type == "feasibility":
                questions.append(f"How can we improve success probability from {conflict.evidence.get('success_rate', 0):.1%}?")
            elif conflict.conflict_type == "trend_mismatch":
                questions.append(f"Why do we expect different trend than historical data shows?")
            elif conflict.conflict_type == "threshold_breach":
                questions.append(f"How do we address the {conflict.evidence.get('constraint', 'constraint')} violation?")
            elif conflict.conflict_type == "correlation_contradiction":
                questions.append(f"Re-examine the relationship with {conflict.evidence.get('variable', 'variable')}")
            elif conflict.conflict_type == "ignored_driver":
                questions.append(f"Should we prioritize {conflict.evidence.get('driver', 'driver')} given its impact?")
        
        return True, focus_area, questions[:5]  # Max 5 questions
    
    def _calculate_alignment_score(self, conflicts: list[Conflict]) -> float:
        """Calculate overall alignment score (0-100)."""
        if not conflicts:
            return 100.0
        
        # Penalty points by severity
        penalties = {
            ConflictSeverity.INFO: 2,
            ConflictSeverity.LOW: 5,
            ConflictSeverity.MEDIUM: 10,
            ConflictSeverity.HIGH: 20,
            ConflictSeverity.CRITICAL: 35,
        }
        
        total_penalty = sum(penalties.get(c.severity, 0) for c in conflicts)
        
        return max(0, 100 - total_penalty)
    
    def _generate_summary(self, conflicts: list[Conflict], alignment_score: float) -> str:
        """Generate human-readable summary."""
        if not conflicts:
            return "Engine A and Engine B results are fully aligned. No conflicts detected."
        
        n_critical = sum(1 for c in conflicts if c.severity == ConflictSeverity.CRITICAL)
        n_high = sum(1 for c in conflicts if c.severity == ConflictSeverity.HIGH)
        n_medium = sum(1 for c in conflicts if c.severity == ConflictSeverity.MEDIUM)
        
        parts = []
        parts.append(f"Alignment Score: {alignment_score:.0f}/100")
        parts.append(f"Conflicts: {len(conflicts)} total")
        
        if n_critical:
            parts.append(f"  - {n_critical} CRITICAL")
        if n_high:
            parts.append(f"  - {n_high} HIGH")
        if n_medium:
            parts.append(f"  - {n_medium} MEDIUM")
        
        if alignment_score < 50:
            parts.append("RECOMMENDATION: Significant revision needed before proceeding.")
        elif alignment_score < 75:
            parts.append("RECOMMENDATION: Address high-severity conflicts before finalizing.")
        else:
            parts.append("RECOMMENDATION: Minor adjustments suggested.")
        
        return "\n".join(parts)


def should_trigger_engine_a_prime(
    engine_a_result: dict, 
    engine_b_result: dict
) -> tuple[bool, list[Conflict]]:
    """
    Convenience function to check if Engine A Prime should be triggered.
    
    Returns:
        (should_trigger: bool, conflicts: list of Conflict objects)
    """
    detector = ConflictDetector()
    report = detector.detect_conflicts(engine_a_result, engine_b_result)
    return report.should_trigger_prime, report.conflicts
