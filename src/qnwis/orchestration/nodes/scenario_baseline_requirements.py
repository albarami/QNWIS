"""
Scenario Baseline Requirements for Prefetch Enhancement.

PURPOSE: Ensure prefetch fetches the specific baseline metrics needed 
for stake-prompting to generate scenarios with real numbers.

Based on Columbia/Harvard research finding: specific stakes drive differentiated reasoning.
Without real baseline data, stake-prompting produces fabricated numbers.
"""

import logging
from typing import Dict, List, Any, Set

logger = logging.getLogger(__name__)


# =============================================================================
# SCENARIO BASELINE REQUIREMENTS MAPPING
# =============================================================================

SCENARIO_BASELINE_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # WORKFORCE / QATARIZATION QUERIES
    # -------------------------------------------------------------------------
    "workforce": {
        "keywords": [
            "qatarization", "nationalization", "workforce", "employment",
            "labor", "jobs", "hiring", "recruitment", "talent", "skills"
        ],
        "required_metrics": [
            # Current state
            "current_qatarization_rate",
            "qatari_workforce_total",
            "qatari_private_sector_employed",
            "qatari_public_sector_employed",
            "total_private_sector_jobs",
            "total_public_sector_jobs",
            # Targets and gaps
            "qatarization_target_rate",
            "qatarization_gap_headcount",
            # Costs and investments
            "avg_qatari_salary_private",
            "avg_qatari_salary_public",
            "avg_expat_salary_equivalent_role",
            "training_budget_annual",
            "wage_subsidy_budget",
            # Pipeline
            "university_graduates_annual",
            "vocational_graduates_annual",
            "job_seekers_registered",
            # Competitor context
            "uae_nationalization_rate",
            "saudi_nationalization_rate",
        ],
        "api_sources": ["mol_lmis", "gcc_stat", "qatar_open_data"],
    },
    
    # -------------------------------------------------------------------------
    # ECONOMIC / FISCAL QUERIES
    # -------------------------------------------------------------------------
    "economic": {
        "keywords": [
            "economic", "gdp", "growth", "revenue", "budget", "fiscal",
            "oil", "gas", "hydrocarbon", "diversification", "investment"
        ],
        "required_metrics": [
            # Revenue
            "government_revenue_total",
            "hydrocarbon_revenue",
            "non_hydrocarbon_revenue",
            "hydrocarbon_revenue_pct",
            # GDP
            "gdp_nominal",
            "gdp_growth_rate",
            "gdp_per_capita",
            "non_oil_gdp_pct",
            # Oil/Gas
            "oil_price_current",
            "lng_price_current",
            "oil_production_bpd",
            "lng_exports_annual",
            # Budget
            "government_expenditure",
            "budget_surplus_deficit",
            "sovereign_wealth_fund_size",
            # Diversification
            "tourism_revenue",
            "financial_services_gdp_pct",
            "manufacturing_gdp_pct",
        ],
        "api_sources": ["world_bank", "qatar_open_data", "gcc_stat"],
    },
    
    # -------------------------------------------------------------------------
    # STRATEGIC HUB QUERIES (Financial, Logistics, Tech, Tourism)
    # -------------------------------------------------------------------------
    "strategic_hub": {
        "keywords": [
            "hub", "financial", "logistics", "technology", "tech", "tourism",
            "fintech", "aviation", "port", "trade", "services"
        ],
        "required_metrics": [
            # Current rankings/position
            "global_competitiveness_rank",
            "ease_of_doing_business_rank",
            "financial_center_rank",
            "logistics_performance_index",
            # Sector specifics
            "financial_services_employment",
            "logistics_sector_employment",
            "tourism_arrivals_annual",
            "tourism_revenue_annual",
            "hotel_occupancy_rate",
            # Infrastructure
            "airport_capacity_passengers",
            "port_capacity_teu",
            "free_zone_companies",
            # Investment
            "fdi_inflows_annual",
            "qia_assets_under_management",
            # Competitor context
            "dubai_financial_center_size",
            "dubai_tourism_arrivals",
            "saudi_tourism_target",
        ],
        "api_sources": ["world_bank", "qatar_open_data", "gcc_stat"],
    },
    
    # -------------------------------------------------------------------------
    # EDUCATION / SKILLS QUERIES
    # -------------------------------------------------------------------------
    "education": {
        "keywords": [
            "education", "training", "skills", "university", "vocational",
            "stem", "graduate", "scholarship", "capacity building"
        ],
        "required_metrics": [
            "university_enrollment",
            "stem_graduates_annual",
            "vocational_graduates_annual",
            "scholarship_recipients",
            "education_budget",
            "private_sector_training_spend",
            "skills_gap_priority_sectors",
            "employer_satisfaction_rate",
        ],
        "api_sources": ["mol_lmis", "qatar_open_data"],
    },
    
    # -------------------------------------------------------------------------
    # COMPETITION / GCC QUERIES
    # -------------------------------------------------------------------------
    "gcc_competition": {
        "keywords": [
            "gcc", "saudi", "uae", "dubai", "bahrain", "oman", "kuwait",
            "competition", "competitive", "regional", "vision 2030"
        ],
        "required_metrics": [
            # Qatar baseline
            "qatar_gdp",
            "qatar_population",
            "qatar_gdp_per_capita",
            # Competitor metrics
            "uae_gdp",
            "saudi_gdp",
            "uae_population",
            "saudi_population",
            "dubai_fdi_inflows",
            "saudi_vision_2030_investment",
            # Relative position
            "qatar_gcc_gdp_share",
            "qatar_gcc_trade_share",
        ],
        "api_sources": ["world_bank", "gcc_stat"],
    },
}


# =============================================================================
# METRIC FALLBACK VALUES (Used when APIs unavailable)
# =============================================================================

METRIC_FALLBACKS: Dict[str, Dict[str, Any]] = {
    # Workforce metrics
    "current_qatarization_rate": {"value": "52%", "source": "estimate", "year": "2024"},
    "qatari_workforce_total": {"value": "378,000", "source": "estimate", "year": "2024"},
    "qatari_private_sector_employed": {"value": "85,000", "source": "estimate", "year": "2024"},
    "qatari_public_sector_employed": {"value": "293,000", "source": "estimate", "year": "2024"},
    "total_private_sector_jobs": {"value": "1,200,000", "source": "estimate", "year": "2024"},
    "total_public_sector_jobs": {"value": "350,000", "source": "estimate", "year": "2024"},
    "qatarization_target_rate": {"value": "70%", "source": "Vision 2030", "year": "2030"},
    "qatarization_gap_headcount": {"value": "85,000", "source": "estimate", "year": "2024"},
    "avg_qatari_salary_private": {"value": "QR 28,000/month", "source": "estimate", "year": "2024"},
    "avg_qatari_salary_public": {"value": "QR 32,000/month", "source": "estimate", "year": "2024"},
    "avg_expat_salary_equivalent_role": {"value": "QR 15,000/month", "source": "estimate", "year": "2024"},
    "training_budget_annual": {"value": "QR 2.5B", "source": "estimate", "year": "2024"},
    "university_graduates_annual": {"value": "12,000", "source": "estimate", "year": "2024"},
    "job_seekers_registered": {"value": "15,000", "source": "estimate", "year": "2024"},
    
    # Economic metrics
    "government_revenue_total": {"value": "QR 240B", "source": "estimate", "year": "2024"},
    "hydrocarbon_revenue": {"value": "QR 144B", "source": "estimate", "year": "2024"},
    "non_hydrocarbon_revenue": {"value": "QR 96B", "source": "estimate", "year": "2024"},
    "hydrocarbon_revenue_pct": {"value": "60%", "source": "estimate", "year": "2024"},
    "gdp_nominal": {"value": "$220B", "source": "estimate", "year": "2024"},
    "gdp_growth_rate": {"value": "2.4%", "source": "IMF estimate", "year": "2024"},
    "gdp_per_capita": {"value": "$82,000", "source": "estimate", "year": "2024"},
    "non_oil_gdp_pct": {"value": "40%", "source": "estimate", "year": "2024"},
    "oil_price_current": {"value": "$78/barrel", "source": "estimate", "year": "2024"},
    "lng_price_current": {"value": "$12/MMBtu", "source": "estimate", "year": "2024"},
    "sovereign_wealth_fund_size": {"value": "$475B", "source": "QIA estimate", "year": "2024"},
    
    # GCC comparison metrics
    "uae_nationalization_rate": {"value": "10%", "source": "estimate", "year": "2024"},
    "saudi_nationalization_rate": {"value": "23%", "source": "Nitaqat estimate", "year": "2024"},
    "qatar_unemployment_rate": {"value": "0.1%", "source": "GCC-STAT", "year": "2024"},
    "uae_gdp": {"value": "$500B", "source": "estimate", "year": "2024"},
    "saudi_gdp": {"value": "$1.1T", "source": "estimate", "year": "2024"},
    
    # Tourism/Hub metrics
    "tourism_arrivals_annual": {"value": "4M", "source": "estimate", "year": "2024"},
    "tourism_revenue_annual": {"value": "QR 45B", "source": "estimate", "year": "2024"},
    "fdi_inflows_annual": {"value": "$2.3B", "source": "UNCTAD estimate", "year": "2024"},
}


# =============================================================================
# QUERY ANALYZER - Detects which baseline requirements apply
# =============================================================================

def analyze_query_requirements(query: str) -> Dict[str, Any]:
    """
    Analyze query to determine which baseline metrics are needed.
    
    Args:
        query: The ministerial question
        
    Returns:
        Dict with matched categories, required metrics, and API sources
    """
    query_lower = query.lower()
    
    matched_categories: List[Dict[str, Any]] = []
    all_required_metrics: Set[str] = set()
    all_api_sources: Set[str] = set()
    
    for category, config in SCENARIO_BASELINE_REQUIREMENTS.items():
        # Check if any keywords match
        keyword_matches = [kw for kw in config["keywords"] if kw in query_lower]
        
        if keyword_matches:
            matched_categories.append({
                "category": category,
                "matched_keywords": keyword_matches,
                "confidence": len(keyword_matches) / len(config["keywords"])
            })
            
            # Collect metrics and sources
            all_required_metrics.update(config["required_metrics"])
            all_api_sources.update(config["api_sources"])
    
    # Sort by confidence
    matched_categories.sort(key=lambda x: x["confidence"], reverse=True)
    
    # Always include core economic metrics as baseline
    if not matched_categories:
        # Default to economic if no matches
        all_required_metrics.update(
            SCENARIO_BASELINE_REQUIREMENTS["economic"]["required_metrics"][:10]
        )
        all_api_sources.update(
            SCENARIO_BASELINE_REQUIREMENTS["economic"]["api_sources"]
        )
        matched_categories.append({
            "category": "economic",
            "matched_keywords": [],
            "confidence": 0.1
        })
    
    result = {
        "matched_categories": matched_categories,
        "required_metrics": list(all_required_metrics),
        "api_sources": list(all_api_sources),
        "primary_category": matched_categories[0]["category"] if matched_categories else "economic"
    }
    
    logger.info(
        f"Query analysis: {result['primary_category']} "
        f"({len(result['required_metrics'])} metrics from {result['api_sources']})"
    )
    
    return result


# =============================================================================
# BASELINE EXTRACTOR - Extract baselines from existing facts
# =============================================================================

def extract_baselines_from_facts(
    extracted_facts: List[Dict[str, Any]],
    required_metrics: List[str]
) -> Dict[str, Dict[str, Any]]:
    """
    Extract baseline metrics from already-fetched facts.
    
    Args:
        extracted_facts: List of facts from prefetch
        required_metrics: List of metric names we need
        
    Returns:
        Dict mapping metric names to values with sources
    """
    baselines: Dict[str, Dict[str, Any]] = {}
    
    # Build a lookup of available facts by various keys
    fact_lookup: Dict[str, Dict[str, Any]] = {}
    for fact in extracted_facts:
        if isinstance(fact, dict):
            # Index by metric name
            metric = fact.get("metric", "").lower().replace(" ", "_")
            if metric:
                fact_lookup[metric] = fact
            
            # Index by indicator
            indicator = fact.get("indicator", "").lower().replace(" ", "_")
            if indicator:
                fact_lookup[indicator] = fact
    
    # Try to match required metrics to available facts
    for metric in required_metrics:
        metric_lower = metric.lower()
        
        # Direct match
        if metric_lower in fact_lookup:
            fact = fact_lookup[metric_lower]
            baselines[metric] = {
                "value": fact.get("value", fact.get("data", "N/A")),
                "source": fact.get("source", "extracted"),
                "year": fact.get("year", "2024")
            }
            continue
        
        # Fuzzy match - check if metric keywords appear in any fact
        for fact_key, fact in fact_lookup.items():
            if any(kw in fact_key for kw in metric_lower.split("_")):
                baselines[metric] = {
                    "value": fact.get("value", fact.get("data", "N/A")),
                    "source": fact.get("source", "extracted"),
                    "year": fact.get("year", "2024")
                }
                break
        
        # Use fallback if not found
        if metric not in baselines and metric in METRIC_FALLBACKS:
            baselines[metric] = METRIC_FALLBACKS[metric].copy()
    
    # Fill remaining with fallbacks
    for metric in required_metrics:
        if metric not in baselines and metric in METRIC_FALLBACKS:
            baselines[metric] = METRIC_FALLBACKS[metric].copy()
    
    logger.info(
        f"Extracted {len(baselines)} baselines "
        f"({sum(1 for v in baselines.values() if v.get('source') != 'estimate')} from data)"
    )
    
    return baselines


# =============================================================================
# INTEGRATION: Enhanced Extraction for Scenarios
# =============================================================================

def enhance_facts_with_scenario_baselines(
    query: str,
    extracted_facts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Enhance extracted facts with scenario-specific baseline metrics.
    
    Call this in extraction node AFTER prefetch, BEFORE scenario generation.
    
    Args:
        query: The ministerial question
        extracted_facts: Already extracted facts from prefetch (list format)
        
    Returns:
        Enhanced facts dict with baseline metrics for scenarios
    """
    # 1. Analyze query to determine required metrics
    requirements = analyze_query_requirements(query)
    
    # 2. Extract baselines from existing facts or use fallbacks
    baseline_metrics = extract_baselines_from_facts(
        extracted_facts,
        requirements["required_metrics"]
    )
    
    # 3. Build enhanced facts structure
    enhanced_facts = {
        "_scenario_baselines": baseline_metrics,
        "_scenario_category": requirements["primary_category"],
        "_scenario_requirements": requirements,
        "_original_facts": extracted_facts,  # Preserve original list
    }
    
    # Also flatten baselines into top-level for easy access
    for metric, value in baseline_metrics.items():
        enhanced_facts[metric] = value
    
    logger.info(
        f"Enhanced facts with {len(baseline_metrics)} scenario baselines "
        f"(category: {requirements['primary_category']})"
    )
    
    return enhanced_facts


# =============================================================================
# SCENARIO GENERATOR INTEGRATION
# =============================================================================

def format_baselines_for_prompt(extracted_facts: Any) -> str:
    """
    Format baseline metrics for scenario generator prompt.
    
    Call this in scenario_generator._format_facts() or _build_scenario_prompt()
    
    Args:
        extracted_facts: Either dict with _scenario_baselines or list of facts
        
    Returns:
        Formatted string for LLM prompt
    """
    # Handle different input formats
    if isinstance(extracted_facts, dict):
        baselines = extracted_facts.get("_scenario_baselines", {})
        category = extracted_facts.get("_scenario_category", "general")
    else:
        # List format - no baselines available
        return "No baseline metrics available. Use realistic Qatar estimates."
    
    if not baselines:
        return "No baseline metrics available. Use realistic Qatar estimates."
    
    lines = [f"BASELINE METRICS FOR SCENARIOS (Category: {category.upper()}):"]
    lines.append("=" * 60)
    
    # Group by type for clarity
    grouped: Dict[str, List[str]] = {
        "current_state": [],
        "targets": [],
        "competitors": [],
        "financial": [],
        "other": []
    }
    
    for metric, data in baselines.items():
        if isinstance(data, dict):
            value = data.get("value", "N/A")
            source = data.get("source", "extracted")
            year = data.get("year", "")
        else:
            value = str(data)
            source = "extracted"
            year = ""
        
        year_str = f" ({year})" if year else ""
        line = f"  • {metric}: {value}{year_str} [source: {source}]"
        
        # Categorize
        if any(kw in metric for kw in ["current", "rate", "total", "employed", "workforce"]):
            grouped["current_state"].append(line)
        elif any(kw in metric for kw in ["target", "goal", "gap", "vision"]):
            grouped["targets"].append(line)
        elif any(kw in metric for kw in ["uae", "saudi", "dubai", "gcc", "bahrain"]):
            grouped["competitors"].append(line)
        elif any(kw in metric for kw in ["revenue", "budget", "gdp", "price", "salary", "cost"]):
            grouped["financial"].append(line)
        else:
            grouped["other"].append(line)
    
    for group_name, items in grouped.items():
        if items:
            lines.append(f"\n{group_name.upper().replace('_', ' ')}:")
            lines.extend(items)
    
    lines.append("\n" + "=" * 60)
    lines.append("INSTRUCTION: Use these EXACT numbers as baselines.")
    lines.append("Scenarios should MODIFY these values to show impact.")
    lines.append("Example: 'From current 52% Qatarization to 70% requires...'")
    
    return "\n".join(lines)


# =============================================================================
# QUICK TEST
# =============================================================================

def test_query_analysis() -> None:
    """Test query requirement detection."""
    test_queries = [
        "Should Qatar accelerate Qatarization to 70% by 2028?",
        "What is the impact of oil price decline on government budget?",
        "Should we focus on becoming a financial hub or logistics hub?",
        "How does Qatar compare to UAE in attracting talent?",
    ]
    
    for query in test_queries:
        result = analyze_query_requirements(query)
        print(f"\nQuery: {query[:50]}...")
        print(f"  Category: {result['primary_category']}")
        print(f"  Metrics needed: {len(result['required_metrics'])}")
        print(f"  APIs: {result['api_sources']}")


if __name__ == "__main__":
    test_query_analysis()

