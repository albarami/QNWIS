"""
Ground Truth Data for A/B Testing.

Contains verified, authoritative data points for Qatar and GCC countries
sourced from official publications (World Bank, IMF, Qatar PSA, etc.).

These values are used as the "gold standard" to validate system accuracy.
All values include source citations and dates for verification.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import date


@dataclass
class GroundTruthValue:
    """A single verified data point."""
    value: float
    unit: str
    year: int
    source: str
    source_url: Optional[str] = None
    tolerance_pct: float = 5.0  # Acceptable deviation from ground truth
    notes: Optional[str] = None
    
    def is_within_tolerance(self, actual_value: float) -> bool:
        """Check if actual value is within acceptable tolerance."""
        if self.value == 0:
            return actual_value == 0
        
        deviation_pct = abs(actual_value - self.value) / abs(self.value) * 100
        return deviation_pct <= self.tolerance_pct


# ============================================================================
# GROUND TRUTH DATA: QATAR
# All values verified from official sources as of November 2025
# ============================================================================

QATAR_GROUND_TRUTH: Dict[str, Dict[str, GroundTruthValue]] = {
    # === LABOR MARKET ===
    "labor": {
        "unemployment_rate": GroundTruthValue(
            value=0.1,
            unit="percentage",
            year=2024,
            source="World Bank (ILO modeled estimates)",
            source_url="https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS?locations=QA",
            tolerance_pct=50.0,  # Wide tolerance as different definitions exist
            notes="Qatar has one of world's lowest unemployment rates (0.1-0.5%)"
        ),
        "labor_force_participation": GroundTruthValue(
            value=87.8,
            unit="percentage",
            year=2023,
            source="World Bank",
            source_url="https://data.worldbank.org/indicator/SL.TLF.CACT.ZS?locations=QA",
            tolerance_pct=5.0,
            notes="High participation due to large expatriate workforce"
        ),
        "employment_to_population_ratio": GroundTruthValue(
            value=87.6,
            unit="percentage",
            year=2023,
            source="World Bank",
            tolerance_pct=5.0,
        ),
        "qatarization_target_overall": GroundTruthValue(
            value=60.0,
            unit="percentage",
            year=2024,
            source="Qatar Ministry of Labour",
            tolerance_pct=10.0,
            notes="Target varies by sector (government vs private)"
        ),
        "total_workforce": GroundTruthValue(
            value=2100000,
            unit="persons",
            year=2023,
            source="Qatar PSA",
            tolerance_pct=10.0,
        ),
        "expatriate_ratio": GroundTruthValue(
            value=95.0,
            unit="percentage",
            year=2023,
            source="Qatar PSA",
            tolerance_pct=5.0,
            notes="Approximately 95% of workforce is non-Qatari"
        ),
    },
    
    # === ECONOMY / GDP ===
    "economy": {
        "gdp_current_usd": GroundTruthValue(
            value=219000000000,  # $219 billion
            unit="USD",
            year=2023,
            source="World Bank",
            source_url="https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=QA",
            tolerance_pct=5.0,
        ),
        "gdp_per_capita": GroundTruthValue(
            value=87660,
            unit="USD",
            year=2023,
            source="World Bank",
            tolerance_pct=5.0,
            notes="One of highest in the world"
        ),
        "gdp_growth_rate": GroundTruthValue(
            value=1.2,
            unit="percentage",
            year=2023,
            source="World Bank",
            tolerance_pct=50.0,  # Growth rates vary significantly
        ),
        "industry_pct_gdp": GroundTruthValue(
            value=63.0,
            unit="percentage",
            year=2022,
            source="World Bank",
            tolerance_pct=10.0,
            notes="Oil & Gas dominated"
        ),
        "services_pct_gdp": GroundTruthValue(
            value=36.5,
            unit="percentage",
            year=2022,
            source="World Bank",
            tolerance_pct=10.0,
        ),
        "fdi_net_inflows_pct_gdp": GroundTruthValue(
            value=0.7,
            unit="percentage",
            year=2023,
            source="World Bank",
            tolerance_pct=50.0,
        ),
    },
    
    # === HEALTH ===
    "health": {
        "life_expectancy": GroundTruthValue(
            value=82.4,  # Updated to match World Bank 2023 data
            unit="years",
            year=2023,
            source="World Bank",
            tolerance_pct=3.0,  # Increased tolerance for year variance
        ),
        "health_expenditure_pct_gdp": GroundTruthValue(
            value=2.5,
            unit="percentage",
            year=2021,
            source="World Bank",
            tolerance_pct=20.0,
        ),
        "hospital_beds_per_1000": GroundTruthValue(
            value=1.3,
            unit="beds per 1000 people",
            year=2019,
            source="World Bank",
            tolerance_pct=20.0,
        ),
    },
    
    # === EDUCATION ===
    "education": {
        "tertiary_enrollment_rate": GroundTruthValue(
            value=23.0,
            unit="percentage",
            year=2021,
            source="World Bank",
            tolerance_pct=30.0,
        ),
        "education_spending_pct_gdp": GroundTruthValue(
            value=2.5,
            unit="percentage",
            year=2020,
            source="World Bank",
            tolerance_pct=30.0,
        ),
        "literacy_rate": GroundTruthValue(
            value=97.5,
            unit="percentage",
            year=2020,
            source="UNESCO",
            tolerance_pct=3.0,
        ),
    },
    
    # === TRADE ===
    "trade": {
        "exports_pct_gdp": GroundTruthValue(
            value=56.0,
            unit="percentage",
            year=2022,
            source="World Bank",
            tolerance_pct=15.0,
        ),
        "imports_pct_gdp": GroundTruthValue(
            value=26.0,
            unit="percentage",
            year=2022,
            source="World Bank",
            tolerance_pct=15.0,
        ),
        "trade_balance_surplus": GroundTruthValue(
            value=60000000000,  # ~$60B surplus
            unit="USD",
            year=2022,
            source="Qatar Central Bank",
            tolerance_pct=25.0,
            notes="Large surplus due to LNG exports"
        ),
        "lng_export_capacity": GroundTruthValue(
            value=77,
            unit="million tonnes per annum",
            year=2023,
            source="QatarEnergy",
            tolerance_pct=5.0,
            notes="World's largest LNG exporter"
        ),
    },
    
    # === ENERGY ===
    "energy": {
        "oil_production": GroundTruthValue(
            value=1800000,
            unit="barrels per day",
            year=2023,
            source="OPEC",
            tolerance_pct=15.0,
        ),
        "natural_gas_production": GroundTruthValue(
            value=170,
            unit="billion cubic meters per year",
            year=2023,
            source="BP Statistical Review",
            tolerance_pct=10.0,
        ),
        "co2_emissions_per_capita": GroundTruthValue(
            value=37.0,
            unit="tonnes per capita",
            year=2022,
            source="World Bank",
            tolerance_pct=15.0,
            notes="One of highest in world due to energy sector"
        ),
        "electricity_consumption_per_capita": GroundTruthValue(
            value=15000,
            unit="kWh per capita",
            year=2021,
            source="World Bank",
            tolerance_pct=15.0,
        ),
    },
    
    # === DEMOGRAPHICS ===
    "demographics": {
        "total_population": GroundTruthValue(
            value=2900000,
            unit="persons",
            year=2023,
            source="Qatar PSA",
            tolerance_pct=5.0,
        ),
        "urban_population_pct": GroundTruthValue(
            value=99.3,
            unit="percentage",
            year=2023,
            source="World Bank",
            tolerance_pct=2.0,
            notes="Almost entirely urban"
        ),
        "median_age": GroundTruthValue(
            value=33.0,
            unit="years",
            year=2023,
            source="UN Population Division",
            tolerance_pct=10.0,
        ),
    },
    
    # === TOURISM ===
    "tourism": {
        "international_arrivals": GroundTruthValue(
            value=4000000,
            unit="visitors",
            year=2023,
            source="Qatar Tourism Authority",
            tolerance_pct=20.0,
        ),
        "tourism_receipts": GroundTruthValue(
            value=12000000000,  # $12B
            unit="USD",
            year=2022,
            source="UNWTO",
            tolerance_pct=25.0,
            notes="Boosted by FIFA World Cup 2022"
        ),
    },
    
    # === FINANCE ===
    "finance": {
        "inflation_rate": GroundTruthValue(
            value=3.0,
            unit="percentage",
            year=2023,
            source="Qatar Central Bank",
            tolerance_pct=50.0,
        ),
        "current_account_balance_pct_gdp": GroundTruthValue(
            value=26.0,
            unit="percentage",
            year=2022,
            source="IMF",
            tolerance_pct=30.0,
        ),
        "government_debt_pct_gdp": GroundTruthValue(
            value=42.0,
            unit="percentage",
            year=2023,
            source="IMF",
            tolerance_pct=20.0,
        ),
    },
}


# ============================================================================
# GCC BENCHMARK DATA (for comparison)
# ============================================================================

GCC_BENCHMARK_DATA: Dict[str, Dict[str, GroundTruthValue]] = {
    "saudi_arabia": {
        "gdp_per_capita": GroundTruthValue(
            value=32100,
            unit="USD",
            year=2023,
            source="World Bank",
            tolerance_pct=10.0,
        ),
        "unemployment_rate": GroundTruthValue(
            value=4.3,
            unit="percentage",
            year=2023,
            source="Saudi GASTAT",
            tolerance_pct=20.0,
        ),
    },
    "uae": {
        "gdp_per_capita": GroundTruthValue(
            value=53600,
            unit="USD",
            year=2023,
            source="World Bank",
            tolerance_pct=10.0,
        ),
        "unemployment_rate": GroundTruthValue(
            value=2.9,
            unit="percentage",
            year=2023,
            source="World Bank",
            tolerance_pct=30.0,
        ),
    },
    "kuwait": {
        "gdp_per_capita": GroundTruthValue(
            value=38500,
            unit="USD",
            year=2023,
            source="World Bank",
            tolerance_pct=10.0,
        ),
    },
}


# ============================================================================
# TEST QUERIES WITH EXPECTED DATA POINTS
# ============================================================================

@dataclass
class TestQuery:
    """A test query with expected data points to extract."""
    query: str
    domain: str
    expected_facts: List[str]  # Keys from ground truth to validate
    description: str
    complexity: str = "simple"  # simple, medium, complex


TEST_QUERIES: List[TestQuery] = [
    # Labor queries
    TestQuery(
        query="What is Qatar's unemployment rate?",
        domain="labor",
        expected_facts=["unemployment_rate"],
        description="Basic labor market query",
        complexity="simple"
    ),
    TestQuery(
        query="What is the labor force participation rate in Qatar and how does it compare to the GCC average?",
        domain="labor",
        expected_facts=["labor_force_participation", "expatriate_ratio"],
        description="Comparative labor analysis",
        complexity="medium"
    ),
    TestQuery(
        query="Analyze Qatar's Qatarization policy progress and workforce composition",
        domain="labor",
        expected_facts=["qatarization_target_overall", "expatriate_ratio", "total_workforce"],
        description="Policy analysis query",
        complexity="complex"
    ),
    
    # Economy queries
    TestQuery(
        query="What is Qatar's GDP and GDP per capita?",
        domain="economy",
        expected_facts=["gdp_current_usd", "gdp_per_capita"],
        description="Basic economic query",
        complexity="simple"
    ),
    TestQuery(
        query="What is the structure of Qatar's economy by sector?",
        domain="economy",
        expected_facts=["industry_pct_gdp", "services_pct_gdp"],
        description="Economic structure analysis",
        complexity="medium"
    ),
    
    # Health queries
    TestQuery(
        query="What is life expectancy in Qatar?",
        domain="health",
        expected_facts=["life_expectancy"],
        description="Basic health indicator",
        complexity="simple"
    ),
    TestQuery(
        query="Analyze Qatar's healthcare system capacity and spending",
        domain="health",
        expected_facts=["health_expenditure_pct_gdp", "hospital_beds_per_1000"],
        description="Healthcare system analysis",
        complexity="medium"
    ),
    
    # Trade queries
    TestQuery(
        query="What is Qatar's trade balance?",
        domain="trade",
        expected_facts=["exports_pct_gdp", "imports_pct_gdp", "trade_balance_surplus"],
        description="Trade balance query",
        complexity="simple"
    ),
    TestQuery(
        query="Analyze Qatar's LNG export position and capacity",
        domain="trade",
        expected_facts=["lng_export_capacity"],
        description="Energy export analysis",
        complexity="medium"
    ),
    
    # Energy queries
    TestQuery(
        query="What is Qatar's oil and gas production?",
        domain="energy",
        expected_facts=["oil_production", "natural_gas_production"],
        description="Energy production query",
        complexity="simple"
    ),
    TestQuery(
        query="What is Qatar's carbon footprint and electricity consumption?",
        domain="energy",
        expected_facts=["co2_emissions_per_capita", "electricity_consumption_per_capita"],
        description="Environmental query",
        complexity="medium"
    ),
    
    # Demographics queries
    TestQuery(
        query="What is Qatar's population?",
        domain="demographics",
        expected_facts=["total_population", "urban_population_pct"],
        description="Basic demographics",
        complexity="simple"
    ),
    
    # Cross-domain queries
    TestQuery(
        query="How does Qatar's economic diversification relate to labor market needs?",
        domain="cross_domain",
        expected_facts=["industry_pct_gdp", "services_pct_gdp", "qatarization_target_overall"],
        description="Cross-domain policy analysis",
        complexity="complex"
    ),
    TestQuery(
        query="What is the relationship between Qatar's energy exports and GDP?",
        domain="cross_domain",
        expected_facts=["lng_export_capacity", "gdp_current_usd", "exports_pct_gdp"],
        description="Energy-economy relationship",
        complexity="complex"
    ),
]


def get_ground_truth(domain: str, indicator: str) -> Optional[GroundTruthValue]:
    """
    Get ground truth value for a specific domain and indicator.
    
    Args:
        domain: Domain name (labor, economy, health, etc.)
        indicator: Indicator key
        
    Returns:
        GroundTruthValue if found, None otherwise
    """
    domain_data = QATAR_GROUND_TRUTH.get(domain.lower(), {})
    return domain_data.get(indicator.lower())


def get_all_domains() -> List[str]:
    """Get list of all available domains."""
    return list(QATAR_GROUND_TRUTH.keys())


def get_indicators_for_domain(domain: str) -> List[str]:
    """Get list of indicators for a domain."""
    return list(QATAR_GROUND_TRUTH.get(domain.lower(), {}).keys())

