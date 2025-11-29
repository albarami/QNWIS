#!/usr/bin/env python3
"""
Generate all 30 scenario YAML files for NSIC Phase 10.

Categories:
- Economic (6): Oil price, GDP variations
- Competitive (6): Regional competition scenarios
- Policy (6): Nationalization, immigration, subsidies
- Timing (6): Launch timing, phasing
- Deep (6): For Engine A detailed analysis
"""

import os
import yaml
from pathlib import Path

# Scenario definitions
SCENARIOS = [
    # Economic (6) - scenarios 001-006
    {
        "id": "econ_001_oil_shock_50",
        "name": "Oil Price Shock - 50% Increase",
        "domain": "economic",
        "description": "Analyze impact of oil prices rising 50% from baseline",
        "inputs": [
            {"variable": "oil_price", "base_value": 80, "shock_value": 120, "shock_type": "percentage", "unit": "USD/barrel"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "econ_002_inflation_surge",
        "name": "Inflation Surge - Global Supply Chain Disruption",
        "domain": "economic",
        "description": "Analyze impact of 8% inflation due to supply chain issues",
        "inputs": [
            {"variable": "inflation_rate", "base_value": 2.5, "shock_value": 8.0, "shock_type": "absolute", "unit": "percent"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "econ_003_oil_crash",
        "name": "Oil Price Crash - 40% Decline",
        "domain": "economic",
        "description": "Analyze impact of oil prices falling 40% from baseline",
        "inputs": [
            {"variable": "oil_price", "base_value": 80, "shock_value": 48, "shock_type": "percentage", "unit": "USD/barrel"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "econ_004_gdp_growth_5",
        "name": "GDP Growth Acceleration - 5% Annual",
        "domain": "economic",
        "description": "Analyze opportunities with 5% GDP growth rate",
        "inputs": [
            {"variable": "gdp_growth", "base_value": 2.5, "shock_value": 5.0, "shock_type": "absolute", "unit": "percent"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "econ_005_gdp_stagnation",
        "name": "GDP Stagnation - Near Zero Growth",
        "domain": "economic",
        "description": "Analyze risks of near-zero GDP growth",
        "inputs": [
            {"variable": "gdp_growth", "base_value": 2.5, "shock_value": 0.5, "shock_type": "absolute", "unit": "percent"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "econ_006_recession",
        "name": "Economic Recession - Negative Growth",
        "domain": "economic",
        "description": "Analyze impact of economic recession",
        "inputs": [
            {"variable": "gdp_growth", "base_value": 2.5, "shock_value": -2.0, "shock_type": "absolute", "unit": "percent"}
        ],
        "assigned_engine": "engine_b"
    },
    
    # Competitive (6) - scenarios 007-012
    {
        "id": "comp_007_dubai_aggressive",
        "name": "Dubai Aggressive Expansion",
        "domain": "competitive",
        "description": "Dubai launches aggressive financial hub expansion with tax incentives",
        "inputs": [
            {"variable": "competitor_intensity", "base_value": 50, "shock_value": 90, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "comp_008_saudi_neom",
        "name": "Saudi NEOM Financial District Launch",
        "domain": "competitive",
        "description": "NEOM launches competing financial services zone",
        "inputs": [
            {"variable": "new_competitor", "base_value": 0, "shock_value": 1, "shock_type": "absolute", "unit": "boolean"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "comp_009_uae_coalition",
        "name": "UAE Federal Financial Coalition",
        "domain": "competitive",
        "description": "UAE emirates form unified financial services strategy",
        "inputs": [
            {"variable": "coalition_strength", "base_value": 30, "shock_value": 80, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "comp_010_gcc_cooperation",
        "name": "GCC Financial Cooperation Agreement",
        "domain": "competitive",
        "description": "GCC countries agree on regional financial cooperation",
        "inputs": [
            {"variable": "cooperation_level", "base_value": 20, "shock_value": 70, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "comp_011_singapore_entry",
        "name": "Singapore Establishes GCC Presence",
        "domain": "competitive",
        "description": "Singapore financial institutions expand to GCC region",
        "inputs": [
            {"variable": "foreign_competition", "base_value": 30, "shock_value": 60, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "comp_020_lng_competition",
        "name": "LNG Market Competition - US Export Surge",
        "domain": "competitive",
        "description": "US LNG exports increase significantly, affecting Qatar market share",
        "inputs": [
            {"variable": "us_lng_exports", "base_value": 100, "shock_value": 180, "shock_type": "percentage", "unit": "bcm"}
        ],
        "assigned_engine": "engine_b"
    },
    
    # Policy (6) - scenarios 013-018
    {
        "id": "policy_010_trade_agreement",
        "name": "New GCC Trade Agreement Impact",
        "domain": "policy",
        "description": "Analyze impact of comprehensive GCC trade agreement",
        "inputs": [
            {"variable": "trade_barriers", "base_value": 100, "shock_value": 30, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "policy_013_fast_qatarization",
        "name": "Accelerated Qatarization - 60% in 3 Years",
        "domain": "policy",
        "description": "Rapid Qatarization policy requiring 60% local workforce",
        "inputs": [
            {"variable": "qatarization_target", "base_value": 30, "shock_value": 60, "shock_type": "absolute", "unit": "percent"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "policy_014_gradual_qatarization",
        "name": "Gradual Qatarization - 40% in 10 Years",
        "domain": "policy",
        "description": "Gradual Qatarization with 40% target over decade",
        "inputs": [
            {"variable": "qatarization_target", "base_value": 30, "shock_value": 40, "shock_type": "absolute", "unit": "percent"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "policy_015_open_immigration",
        "name": "Open Immigration Policy",
        "domain": "policy",
        "description": "Liberalized immigration for skilled workers",
        "inputs": [
            {"variable": "immigration_openness", "base_value": 50, "shock_value": 85, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "policy_016_restricted_immigration",
        "name": "Restricted Immigration Policy",
        "domain": "policy",
        "description": "More restrictive immigration requirements",
        "inputs": [
            {"variable": "immigration_openness", "base_value": 50, "shock_value": 25, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "policy_017_subsidy_reduction",
        "name": "Subsidy Reduction Program",
        "domain": "policy",
        "description": "Government reduces energy and housing subsidies",
        "inputs": [
            {"variable": "subsidy_level", "base_value": 100, "shock_value": 50, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_b"
    },
    
    # Timing (6) - scenarios 019-024
    {
        "id": "timing_019_2026_launch",
        "name": "Financial Hub Launch 2026",
        "domain": "timing",
        "description": "Aggressive 2026 target for financial hub launch",
        "inputs": [
            {"variable": "launch_year", "base_value": 2030, "shock_value": 2026, "shock_type": "absolute", "unit": "year"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "timing_020_2028_launch",
        "name": "Financial Hub Launch 2028",
        "domain": "timing",
        "description": "Moderate 2028 target for financial hub launch",
        "inputs": [
            {"variable": "launch_year", "base_value": 2030, "shock_value": 2028, "shock_type": "absolute", "unit": "year"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "timing_021_2032_launch",
        "name": "Financial Hub Launch 2032",
        "domain": "timing",
        "description": "Conservative 2032 target for financial hub launch",
        "inputs": [
            {"variable": "launch_year", "base_value": 2030, "shock_value": 2032, "shock_type": "absolute", "unit": "year"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "timing_022_phased_5yr",
        "name": "Phased Implementation - 5 Year Plan",
        "domain": "timing",
        "description": "Phased rollout over 5 years with milestones",
        "inputs": [
            {"variable": "implementation_duration", "base_value": 3, "shock_value": 5, "shock_type": "absolute", "unit": "years"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "timing_023_phased_10yr",
        "name": "Phased Implementation - 10 Year Plan",
        "domain": "timing",
        "description": "Long-term phased rollout over decade",
        "inputs": [
            {"variable": "implementation_duration", "base_value": 3, "shock_value": 10, "shock_type": "absolute", "unit": "years"}
        ],
        "assigned_engine": "engine_b"
    },
    {
        "id": "timing_030_world_cup_legacy",
        "name": "World Cup Infrastructure Legacy Utilization",
        "domain": "timing",
        "description": "Leveraging 2022 World Cup infrastructure for economic development",
        "inputs": [
            {"variable": "infrastructure_utilization", "base_value": 40, "shock_value": 85, "shock_type": "absolute", "unit": "percent"}
        ],
        "assigned_engine": "engine_b"
    },
    
    # Deep Analysis (6) - scenarios 025-030 for Engine A
    {
        "id": "deep_025_base_case",
        "name": "Base Case Comprehensive Analysis",
        "domain": "deep",
        "description": "Comprehensive baseline analysis of Qatar economic strategy",
        "inputs": [
            {"variable": "analysis_depth", "base_value": 1, "shock_value": 1, "shock_type": "absolute", "unit": "level"}
        ],
        "assigned_engine": "engine_a"
    },
    {
        "id": "deep_026_optimistic",
        "name": "Optimistic Scenario Deep Dive",
        "domain": "deep",
        "description": "Best case scenario with favorable conditions",
        "inputs": [
            {"variable": "outlook", "base_value": 50, "shock_value": 85, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_a"
    },
    {
        "id": "deep_027_pessimistic",
        "name": "Pessimistic Scenario Deep Dive",
        "domain": "deep",
        "description": "Worst case scenario with adverse conditions",
        "inputs": [
            {"variable": "outlook", "base_value": 50, "shock_value": 15, "shock_type": "absolute", "unit": "index"}
        ],
        "assigned_engine": "engine_a"
    },
    {
        "id": "deep_028_competitive_shock",
        "name": "Competitive Shock Analysis",
        "domain": "deep",
        "description": "Deep analysis of major competitive disruption",
        "inputs": [
            {"variable": "competitive_shock", "base_value": 0, "shock_value": 1, "shock_type": "absolute", "unit": "boolean"}
        ],
        "assigned_engine": "engine_a"
    },
    {
        "id": "deep_029_policy_acceleration",
        "name": "Policy Acceleration Analysis",
        "domain": "deep",
        "description": "Deep analysis of accelerated policy implementation",
        "inputs": [
            {"variable": "policy_speed", "base_value": 1, "shock_value": 2, "shock_type": "absolute", "unit": "multiplier"}
        ],
        "assigned_engine": "engine_a"
    },
    {
        "id": "deep_030_black_swan",
        "name": "Black Swan Event Analysis",
        "domain": "deep",
        "description": "Analysis of low-probability high-impact events",
        "inputs": [
            {"variable": "black_swan", "base_value": 0, "shock_value": 1, "shock_type": "absolute", "unit": "boolean"}
        ],
        "assigned_engine": "engine_a"
    },
]


def generate_scenario_yaml(scenario: dict) -> dict:
    """Generate YAML content for a scenario."""
    return {
        "id": scenario["id"],
        "name": scenario["name"],
        "domain": scenario["domain"],
        "version": "1.0",
        "description": scenario["description"],
        "inputs": scenario["inputs"],
        "assigned_engine": scenario["assigned_engine"],
        "expected_structure": {
            "must_include": ["analysis", "recommendation", "risks"],
            "min_length": 500,
        },
        "validation_rules": [
            {
                "field": "recommendation",
                "rule_type": "required",
                "message": "Must provide recommendation"
            }
        ],
        "retry_config": {
            "max_retries": 2,
            "retry_delay_seconds": 5
        }
    }


def get_domain_folder(domain: str) -> str:
    """Map domain to folder name."""
    mapping = {
        "economic": "economic",
        "competitive": "competitive",
        "policy": "policy",
        "timing": "timing",
        "deep": "deep"
    }
    return mapping.get(domain, domain)


def main():
    print("=" * 60)
    print("NSIC Scenario Generator")
    print("=" * 60)
    
    base_dir = Path("scenarios")
    created = 0
    skipped = 0
    
    for scenario in SCENARIOS:
        domain_folder = get_domain_folder(scenario["domain"])
        folder = base_dir / domain_folder
        folder.mkdir(parents=True, exist_ok=True)
        
        filename = folder / f"{scenario['id']}.yaml"
        
        # Check if file already exists
        if filename.exists():
            print(f"  [SKIP] {filename} (exists)")
            skipped += 1
            continue
        
        # Generate and write YAML
        yaml_content = generate_scenario_yaml(scenario)
        
        with open(filename, 'w') as f:
            yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)
        
        print(f"  [CREATE] {filename}")
        created += 1
    
    print("\n" + "=" * 60)
    print(f"Created: {created} new scenarios")
    print(f"Skipped: {skipped} existing scenarios")
    print(f"Total: {len(SCENARIOS)} scenarios defined")
    print("=" * 60)
    
    # Verify count
    total_files = sum(1 for _ in base_dir.rglob("*.yaml"))
    print(f"\nTotal YAML files in scenarios/: {total_files}")


if __name__ == "__main__":
    main()

