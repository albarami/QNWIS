"""
Data Quality Validation Rules for QNWIS.

Provides validation rules and functions to ensure data quality
across all domains (Labor, Health, Education, Trade, etc.).

Domain-agnostic design supports ministerial-grade data integrity.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DataQualityResult:
    """Result of data quality validation."""
    
    is_valid: bool
    quality_score: float  # 0.0 to 1.0
    quality_flags: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "quality_score": round(self.quality_score, 3),
            "quality_flags": self.quality_flags,
            "warnings": self.warnings,
            "errors": self.errors,
        }


# ============================================================================
# VALIDATION RULES BY DOMAIN AND INDICATOR
# ============================================================================

VALIDATION_RULES: Dict[str, Dict[str, Any]] = {
    # === LABOR MARKET (Qatar-specific) ===
    "qatar_unemployment": {
        "indicator_codes": ["SL.UEM.TOTL.ZS", "unemployment_rate"],
        "domain": "Labor",
        "min": 0.0,
        "max": 5.0,  # Qatar historically < 1%, but allow for definition differences
        "alert_threshold": 2.0,
        "expected_range": (0.05, 0.5),  # 0.05% to 0.5% for Qatar
        "description": "Qatar unemployment rate should be very low (0.1-0.5%)"
    },
    
    "labor_force_participation": {
        "indicator_codes": ["SL.TLF.CACT.ZS", "labor_participation_rate"],
        "domain": "Labor",
        "min": 60.0,
        "max": 95.0,
        "expected_range": (80.0, 90.0),
        "description": "Labor force participation typically 80-90% for working-age population"
    },
    
    "employment_ratio": {
        "indicator_codes": ["SL.EMP.TOTL.SP.ZS"],
        "domain": "Labor",
        "min": 50.0,
        "max": 95.0,
        "expected_range": (70.0, 85.0),
        "description": "Employment to population ratio"
    },
    
    # === ECONOMIC / GDP ===
    "gdp_growth": {
        "indicator_codes": ["NY.GDP.MKTP.KD.ZG", "gdp_growth_rate"],
        "domain": "Economy",
        "min": -30.0,  # Allow for severe recessions
        "max": 50.0,
        "alert_threshold_high": 15.0,
        "alert_threshold_low": -10.0,
        "description": "GDP growth rate - extreme values should be flagged"
    },
    
    "gdp_per_capita": {
        "indicator_codes": ["NY.GDP.PCAP.CD"],
        "domain": "Economy",
        "min": 1000.0,
        "max": 200000.0,  # Qatar is among highest in world
        "expected_range": (50000.0, 100000.0),  # Qatar typical range
        "description": "GDP per capita in current USD"
    },
    
    # === HEALTH ===
    "life_expectancy": {
        "indicator_codes": ["SP.DYN.LE00.IN"],
        "domain": "Health",
        "min": 40.0,
        "max": 95.0,
        "expected_range": (78.0, 85.0),
        "description": "Life expectancy at birth in years"
    },
    
    "health_expenditure_pct": {
        "indicator_codes": ["SH.XPD.CHEX.GD.ZS"],
        "domain": "Health",
        "min": 0.5,
        "max": 25.0,
        "expected_range": (2.0, 8.0),
        "description": "Health expenditure as % of GDP"
    },
    
    # === EDUCATION ===
    "tertiary_enrollment": {
        "indicator_codes": ["SE.TER.ENRR"],
        "domain": "Education",
        "min": 0.0,
        "max": 150.0,  # Can exceed 100% due to non-traditional age enrollment
        "expected_range": (15.0, 80.0),
        "description": "Tertiary education enrollment rate"
    },
    
    "education_spending_pct": {
        "indicator_codes": ["SE.XPD.TOTL.GD.ZS"],
        "domain": "Education",
        "min": 0.5,
        "max": 15.0,
        "expected_range": (2.0, 8.0),
        "description": "Education spending as % of GDP"
    },
    
    # === TRADE ===
    "trade_balance": {
        "indicator_codes": ["trade_balance_usd"],
        "domain": "Trade",
        "min": -500e9,  # $500B deficit
        "max": 500e9,   # $500B surplus
        "description": "Trade balance in USD"
    },
    
    "export_pct_gdp": {
        "indicator_codes": ["NE.EXP.GNFS.ZS"],
        "domain": "Trade",
        "min": 0.0,
        "max": 200.0,  # Some small economies exceed 100%
        "expected_range": (40.0, 80.0),
        "description": "Exports as % of GDP"
    },
    
    # === ENERGY ===
    "co2_per_capita": {
        "indicator_codes": ["EN.ATM.CO2E.PC"],
        "domain": "Energy",
        "min": 0.0,
        "max": 100.0,  # Qatar is among highest
        "alert_threshold": 40.0,  # Flag very high values
        "expected_range": (5.0, 50.0),
        "description": "CO2 emissions per capita (metric tons)"
    },
    
    "electricity_consumption": {
        "indicator_codes": ["EG.USE.ELEC.KH.PC"],
        "domain": "Energy",
        "min": 100.0,
        "max": 50000.0,  # Qatar has very high consumption
        "expected_range": (5000.0, 20000.0),
        "description": "Electric power consumption per capita (kWh)"
    },
    
    # === DEMOGRAPHICS ===
    "population": {
        "indicator_codes": ["SP.POP.TOTL"],
        "domain": "Demographics",
        "min": 100000.0,  # At least 100K for any country
        "max": 2e9,      # No country exceeds 2 billion
        "expected_range": (2e6, 4e6),  # Qatar range
        "description": "Total population"
    },
    
    "urban_population_pct": {
        "indicator_codes": ["SP.URB.TOTL.IN.ZS"],
        "domain": "Demographics",
        "min": 10.0,
        "max": 100.0,
        "expected_range": (90.0, 100.0),  # Qatar is highly urbanized
        "description": "Urban population as % of total"
    },
}


def get_rule_for_indicator(indicator_code: str) -> Optional[Dict[str, Any]]:
    """
    Find the validation rule for an indicator code.
    
    Args:
        indicator_code: Indicator code to look up
        
    Returns:
        Validation rule dict or None if not found
    """
    for rule_name, rule in VALIDATION_RULES.items():
        if indicator_code in rule.get("indicator_codes", []):
            return rule
    return None


def validate_data_point(
    value: float,
    indicator_code: str,
    country_code: str = "QAT",
    year: Optional[int] = None,
) -> DataQualityResult:
    """
    Validate a single data point.
    
    Args:
        value: The numeric value to validate
        indicator_code: Indicator code
        country_code: Country code
        year: Optional year of data
        
    Returns:
        DataQualityResult with validation status
    """
    result = DataQualityResult(
        is_valid=True,
        quality_score=1.0,
        quality_flags={
            "outlier": False,
            "missing": False,
            "out_of_range": False,
            "alert_triggered": False,
        }
    )
    
    # Check for missing/null value
    if value is None:
        result.is_valid = False
        result.quality_score = 0.0
        result.quality_flags["missing"] = True
        result.errors.append("Value is null/missing")
        return result
    
    # Find applicable rule
    rule = get_rule_for_indicator(indicator_code)
    
    if not rule:
        # No specific rule - apply generic validation
        result.warnings.append(f"No specific validation rule for {indicator_code}")
        result.quality_score = 0.8
        return result
    
    # Check absolute bounds
    min_val = rule.get("min")
    max_val = rule.get("max")
    
    if min_val is not None and value < min_val:
        result.is_valid = False
        result.quality_score = 0.0
        result.quality_flags["out_of_range"] = True
        result.errors.append(f"Value {value} below minimum {min_val}")
        return result
    
    if max_val is not None and value > max_val:
        result.is_valid = False
        result.quality_score = 0.0
        result.quality_flags["out_of_range"] = True
        result.errors.append(f"Value {value} above maximum {max_val}")
        return result
    
    # Check expected range (warnings, not errors)
    expected_range = rule.get("expected_range")
    if expected_range and country_code == "QAT":  # Qatar-specific expectations
        exp_min, exp_max = expected_range
        if value < exp_min or value > exp_max:
            result.quality_flags["outlier"] = True
            result.quality_score = 0.7
            result.warnings.append(
                f"Value {value} outside expected range [{exp_min}, {exp_max}] for Qatar"
            )
    
    # Check alert thresholds
    alert_high = rule.get("alert_threshold_high", rule.get("alert_threshold"))
    alert_low = rule.get("alert_threshold_low")
    
    if alert_high and value > alert_high:
        result.quality_flags["alert_triggered"] = True
        result.quality_score = min(result.quality_score, 0.8)
        result.warnings.append(f"Value {value} exceeds alert threshold {alert_high}")
    
    if alert_low and value < alert_low:
        result.quality_flags["alert_triggered"] = True
        result.quality_score = min(result.quality_score, 0.8)
        result.warnings.append(f"Value {value} below alert threshold {alert_low}")
    
    return result


def validate_batch(
    data_points: List[Dict[str, Any]],
) -> Tuple[List[DataQualityResult], Dict[str, Any]]:
    """
    Validate a batch of data points.
    
    Args:
        data_points: List of dicts with 'value', 'indicator_code', 'country_code', 'year'
        
    Returns:
        Tuple of (list of results, summary stats)
    """
    results = []
    valid_count = 0
    total_score = 0.0
    
    for dp in data_points:
        result = validate_data_point(
            value=dp.get("value"),
            indicator_code=dp.get("indicator_code", ""),
            country_code=dp.get("country_code", "QAT"),
            year=dp.get("year"),
        )
        results.append(result)
        
        if result.is_valid:
            valid_count += 1
        total_score += result.quality_score
    
    summary = {
        "total_points": len(data_points),
        "valid_points": valid_count,
        "invalid_points": len(data_points) - valid_count,
        "avg_quality_score": total_score / len(data_points) if data_points else 0.0,
        "validation_timestamp": datetime.utcnow().isoformat(),
    }
    
    return results, summary


def cross_validate_sources(
    value1: float,
    value2: float,
    source1: str,
    source2: str,
    tolerance_pct: float = 10.0,
) -> DataQualityResult:
    """
    Cross-validate data from two different sources.
    
    Args:
        value1: Value from first source
        value2: Value from second source
        source1: Name of first source
        source2: Name of second source
        tolerance_pct: Acceptable percentage difference
        
    Returns:
        DataQualityResult indicating consistency
    """
    result = DataQualityResult(
        is_valid=True,
        quality_score=1.0,
        quality_flags={
            "source_mismatch": False,
            "high_variance": False,
        }
    )
    
    if value1 is None or value2 is None:
        result.quality_flags["source_mismatch"] = True
        result.quality_score = 0.5
        result.warnings.append("One or both values missing for cross-validation")
        return result
    
    # Calculate percentage difference
    avg = (value1 + value2) / 2
    if avg == 0:
        pct_diff = 0 if value1 == value2 else 100
    else:
        pct_diff = abs(value1 - value2) / avg * 100
    
    if pct_diff > tolerance_pct:
        result.quality_flags["source_mismatch"] = True
        result.quality_flags["high_variance"] = True
        result.quality_score = max(0.0, 1.0 - (pct_diff / 100))
        result.warnings.append(
            f"Values differ by {pct_diff:.1f}% between {source1} ({value1}) "
            f"and {source2} ({value2})"
        )
    else:
        result.quality_score = 1.0 - (pct_diff / 100 * 0.5)
    
    return result

