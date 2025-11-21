"""
Comprehensive API Catalog for Qatar Ministerial Committees
Aligned with: Economic Committee, Workforce Planning Committee, NDS3 Committee
"""

from typing import Dict, List, Any

# Import the full catalog from data module
# This file provides the structure - actual catalog is in separate module for maintainability

# Phase 1 Critical APIs (Implementing NOW)
PHASE_1_CRITICAL_APIS = [
    "world_bank_indicators",  # Fills 60% of gaps
    "unctad",                 # Investment/FDI critical
    "ilo_ilostat"             # International labor benchmarks
]

# Phase 2 Specialized APIs (Next priority)
PHASE_2_APIS = [
    "fao_stat",               # Food security
    "unwto_tourism",          # Tourism statistics
    "iea_energy"              # Energy sector
]

# Currently Available
TIER_1_AVAILABLE = ["imf", "un_comtrade", "fred", "mol_lmis", "gcc_stat", "qatar_open_data"]

# Domain to API mapping
DOMAIN_TO_API_MAPPING = {
    # Economic
    "economic_growth": ["imf", "world_bank_indicators", "gcc_stat"],
    "fiscal_policy": ["imf", "world_bank_indicators"],
    "trade": ["un_comtrade", "gcc_stat"],
    "investment": ["unctad", "world_bank_indicators"],
    "fdi": ["unctad"],
    
    # Workforce
    "employment": ["mol_lmis", "ilo_ilostat", "gcc_stat"],
    "wages": ["mol_lmis", "ilo_ilostat"],
    "skills": ["ilo_ilostat", "world_bank_indicators"],
    "nationalization": ["mol_lmis", "gcc_stat"],
    
    # NDS3 Sectors
    "agriculture": ["fao_stat", "un_comtrade", "world_bank_indicators"],
    "tourism": ["unwto_tourism", "world_bank_indicators"],
    "manufacturing": ["un_comtrade", "world_bank_indicators"],
    "oil_and_gas": ["iea_energy", "un_comtrade"],
    "food_security": ["fao_stat", "un_comtrade"],
    "human_capital": ["world_bank_indicators", "ilo_ilostat", "mol_lmis"]
}

# Critical data gaps
DATA_GAPS = {
    "sector_gdp": {
        "impact": "CRITICAL",
        "gap": "No sector-level GDP breakdown",
        "solution": "world_bank_indicators"
    },
    "investment_fdi": {
        "impact": "HIGH",
        "gap": "No FDI/investment flows",
        "solution": "unctad"
    },
    "labor_international": {
        "impact": "HIGH",
        "gap": "No international labor benchmarks",
        "solution": "ilo_ilostat"
    },
    "tourism": {
        "impact": "HIGH",
        "gap": "No tourist arrivals/occupancy",
        "solution": "unwto_tourism"
    },
    "agriculture": {
        "impact": "MEDIUM",
        "gap": "No production/food security metrics",
        "solution": "fao_stat"
    }
}


def get_agent_data_sources_section() -> str:
    """Get data sources section for agent system prompts"""
    return """# DATA SOURCES AVAILABLE

**Currently Available (Use Now):**
- **IMF API**: Economic indicators (GDP, debt, inflation) - Qatar + GCC + Global
- **UN Comtrade**: Trade statistics (imports/exports by commodity) - Global
- **MoL LMIS**: Qatar labor market (employment, wages, Qatarization)
- **GCC-STAT**: Regional statistics for GCC benchmarking

**Critical Gaps (Acknowledge When Relevant):**
- ❌ Sector GDP breakdown (tourism %, manufacturing %, etc.) - NEED: World Bank API
- ❌ FDI/investment flows - NEED: UNCTAD API  
- ❌ International labor benchmarks - NEED: ILO ILOSTAT
- ❌ Tourism arrivals/occupancy - NEED: UNWTO or Qatar Tourism Authority
- ❌ Agricultural production/food security - NEED: FAO STAT

**How to Handle Gaps:**
When data is missing, state explicitly: "[Data not available - would need {source}]"
Never estimate. Always acknowledge limitations transparently."""
