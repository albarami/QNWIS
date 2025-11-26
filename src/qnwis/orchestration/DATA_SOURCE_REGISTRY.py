"""
COMPLETE DATA SOURCE REGISTRY - QNWIS

This registry documents EVERY data source available to the system.
Agents MUST consult this to know what data to request.

TOTAL: 18+ APIs + 56 R&D Reports + Knowledge Graph + PostgreSQL Cache
"""

# =============================================================================
# DATA SOURCE REGISTRY - AGENTS MUST KNOW ALL OF THIS
# =============================================================================

DATA_SOURCES = {
    
    # =========================================================================
    # 1. QATAR MINISTRY OF LABOUR (MoL LMIS) - PRIMARY AUTHORITY
    # =========================================================================
    "MOL_LMIS": {
        "name": "Qatar Ministry of Labour LMIS API",
        "priority": 100,  # HIGHEST - Official government data
        "base_url": "https://lmis-dashb-api.mol.gov.qa/api",
        "authentication": "Bearer Token (LMIS_API_TOKEN)",
        "client_file": "src/data/apis/lmis_mol_api.py",
        "client_class": "LMISAPIClient",
        
        "endpoints": {
            # Labor Market Indicators
            "main_indicators": {
                "method": "get_qatar_main_indicators()",
                "data": "Main labor market KPIs - unemployment, participation, employment rates",
                "use_when": ["labor market overview", "KPIs", "main indicators"]
            },
            "sdg_indicators": {
                "method": "get_sdg_indicators()",
                "data": "SDG progress - decent work, gender equality, education access",
                "use_when": ["SDG", "sustainable development", "UN goals"]
            },
            "job_seniority": {
                "method": "get_job_seniority_distribution()",
                "data": "Workforce by seniority level",
                "use_when": ["seniority", "experience levels", "workforce composition"]
            },
            
            # Economic Diversification
            "sector_growth": {
                "method": "get_sector_growth(sector_type)",
                "data": "Sector growth rates (NDS3/ISIC)",
                "use_when": ["sector growth", "industry growth", "diversification"]
            },
            "skills_by_sector": {
                "method": "get_top_skills_by_sector()",
                "data": "In-demand skills per economic sector",
                "use_when": ["skills demand", "sector skills", "hiring trends"]
            },
            "expat_skills": {
                "method": "get_attracted_expat_skills()",
                "data": "Skills brought by expatriates",
                "use_when": ["expat skills", "foreign workers", "skills import"]
            },
            "skills_diversification": {
                "method": "get_skills_diversification()",
                "data": "Skills by country of origin",
                "use_when": ["skills by nationality", "workforce diversity"]
            },
            
            # Human Capital Development
            "education_bachelors": {
                "method": "get_education_attainment_bachelors()",
                "data": "Bachelor's degree holders growth",
                "use_when": ["education", "degrees", "higher education"]
            },
            "emerging_skills": {
                "method": "get_emerging_decaying_skills()",
                "data": "Rising and declining skills trends",
                "use_when": ["skills trends", "emerging skills", "obsolete skills"]
            },
            "skills_gap": {
                "method": "get_education_system_skills_gap()",
                "data": "Gap between education output and market needs",
                "use_when": ["skills gap", "education mismatch", "training needs"]
            },
            "salaries": {
                "method": "get_best_paid_occupations()",
                "data": "Salary levels by occupation",
                "use_when": ["salaries", "wages", "compensation", "pay"]
            },
            
            # Qatarization
            "qatari_skills_gap": {
                "method": "get_qatari_jobseekers_skills_gap()",
                "data": "Skills gaps for Qatari job seekers (Kawader)",
                "use_when": ["Qatarization", "nationals employment", "Kawader"]
            },
            
            # Labor Mobility
            "occupation_transitions": {
                "method": "get_occupation_transitions()",
                "data": "Career movement patterns between occupations",
                "use_when": ["career mobility", "job transitions", "career paths"]
            },
            "sector_mobility": {
                "method": "get_sector_mobility()",
                "data": "Worker movement between sectors",
                "use_when": ["sector transitions", "industry changes"]
            },
            
            # Expat Labor
            "expat_occupations": {
                "method": "get_expat_dominated_occupations()",
                "data": "Occupations with high expat concentration",
                "use_when": ["expat jobs", "foreign worker roles"]
            },
            "top_expat_skills": {
                "method": "get_top_expat_skills()",
                "data": "Most common skills among expats",
                "use_when": ["expat skill profiles", "foreign expertise"]
            },
            
            # SMEs
            "occupations_by_company_size": {
                "method": "get_occupations_by_company_size()",
                "data": "Job distribution by firm size",
                "use_when": ["SME employment", "firm size analysis"]
            },
            "sme_growth": {
                "method": "get_sme_growth()",
                "data": "SME sector metrics and growth",
                "use_when": ["SME growth", "small business", "entrepreneurs"]
            },
        },
        
        "coverage": {
            "geographic": "Qatar only",
            "temporal": "Real-time + historical",
            "update_frequency": "Daily/Weekly"
        }
    },
    
    # =========================================================================
    # 2. GCC-STAT - REGIONAL BENCHMARKING
    # =========================================================================
    "GCC_STAT": {
        "name": "GCC Statistical Centre",
        "priority": 95,
        "client_file": "src/data/apis/gcc_stat.py",
        "client_class": "GCCStatClient",
        
        "methods": {
            "unemployment": {
                "method": "get_gcc_unemployment_rates()",
                "data": "Unemployment rates for all 6 GCC countries",
                "use_when": ["GCC comparison", "regional benchmarking", "unemployment comparison"]
            },
            "labor_indicators": {
                "method": "get_labour_market_indicators()",
                "data": "Comprehensive labor indicators for GCC",
                "use_when": ["GCC labor market", "regional analysis"]
            },
            "labor_force_participation": {
                "method": "get_labour_force_participation()",
                "data": "Labor force participation by country",
                "use_when": ["participation rates", "workforce engagement"]
            },
            "youth_unemployment": {
                "method": "get_youth_unemployment()",
                "data": "Youth unemployment across GCC",
                "use_when": ["youth employment", "young workers"]
            },
            "female_participation": {
                "method": "get_female_participation()",
                "data": "Female labor force participation",
                "use_when": ["gender", "women in workforce", "female employment"]
            }
        },
        
        "coverage": {
            "countries": ["Qatar", "Saudi Arabia", "UAE", "Kuwait", "Bahrain", "Oman"],
            "temporal": "Quarterly updates"
        }
    },
    
    # =========================================================================
    # 3. WORLD BANK - INTERNATIONAL INDICATORS
    # =========================================================================
    "WORLD_BANK": {
        "name": "World Bank Open Data API",
        "priority": 95,
        "base_url": "https://api.worldbank.org/v2",
        "client_file": "src/data/apis/world_bank_api.py",
        "client_class": "WorldBankAPI",
        
        "indicators": {
            # GDP & Economy
            "NY.GDP.MKTP.CD": "GDP (current US$)",
            "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
            "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
            "NY.GDP.PCAP.KD.ZG": "GDP per capita growth",
            
            # Labor Market
            "SL.UEM.TOTL.ZS": "Unemployment rate (%)",
            "SL.UEM.TOTL.NE.ZS": "Unemployment (national estimate)",
            "SL.TLF.CACT.ZS": "Labor force participation rate (%)",
            "SL.TLF.CACT.MA.ZS": "Labor force participation - male",
            "SL.TLF.CACT.FE.ZS": "Labor force participation - female",
            "SL.TLF.TOTL.IN": "Total labor force",
            "SL.EMP.TOTL.SP.ZS": "Employment to population ratio",
            
            # Education
            "SE.XPD.TOTL.GD.ZS": "Education expenditure (% of GDP)",
            "SE.TER.ENRR": "Tertiary school enrollment",
            "SE.SEC.ENRR": "Secondary school enrollment",
            
            # Trade
            "NE.EXP.GNFS.ZS": "Exports (% of GDP)",
            "NE.IMP.GNFS.ZS": "Imports (% of GDP)",
            "BN.CAB.XOKA.CD": "Current account balance",
            
            # Demographics
            "SP.POP.TOTL": "Total population",
            "SP.DYN.LE00.IN": "Life expectancy at birth",
            "SP.URB.TOTL.IN.ZS": "Urban population (%)",
            
            # Energy
            "EG.USE.PCAP.KG.OE": "Energy use (kg oil equivalent)",
            "EN.ATM.CO2E.PC": "CO2 emissions (metric tons per capita)",
        },
        
        "coverage": {
            "countries": "All 217 countries",
            "temporal": "1960-2024"
        }
    },
    
    # =========================================================================
    # 4. ILO ILOSTAT - INTERNATIONAL LABOR STANDARDS
    # =========================================================================
    "ILO_ILOSTAT": {
        "name": "International Labour Organization Statistics",
        "priority": 93,
        "base_url": "https://www.ilo.org/sdmx/rest",
        "client_file": "src/data/apis/ilo_stats.py",
        "client_class": "ILOStatsClient",
        
        "indicators": {
            "UNE_2EAP_SEX_AGE_RT_A": "Unemployment rate by sex and age",
            "EAP_2WAP_SEX_AGE_RT_A": "Labor force participation by sex and age",
            "EIP_NEET_SEX_RT_A": "Youth NEET rate (Not in Education, Employment, Training)",
            "EMP_2EMP_SEX_ECO_NB_A": "Employment by economic activity",
            "SDG_0852_SEX_RT_A": "Working poverty rate",
            "EAR_4MTH_SEX_ECO_CUR_NB_M": "Mean monthly earnings"
        },
        
        "coverage": {
            "geographic": "Global (189 countries)",
            "temporal": "1990-2024"
        }
    },
    
    # =========================================================================
    # 5. IMF DATA MAPPER - ECONOMIC FORECASTS
    # =========================================================================
    "IMF_DATA": {
        "name": "IMF Data Mapper API",
        "priority": 93,
        "client_file": "src/data/apis/imf_api.py",
        "client_class": "IMFDataMapper",
        
        "indicators": {
            "NGDP_RPCH": "Real GDP growth",
            "PCPIPCH": "Inflation rate (CPI)",
            "LUR": "Unemployment rate",
            "GGR_NGDP": "Government revenue (% GDP)",
            "GGX_NGDP": "Government expenditure (% GDP)",
            "GGXWDG_NGDP": "Government debt (% GDP)",
            "BCA_NGDPD": "Current account balance (% GDP)"
        },
        
        "unique_value": "FORECASTS up to 2029 - only source with future projections",
        
        "coverage": {
            "geographic": "190 countries",
            "temporal": "Historical + Forecasts to 2029"
        }
    },
    
    # =========================================================================
    # 6. QATAR OPEN DATA PORTAL - GOVERNMENT DATASETS
    # =========================================================================
    "QATAR_OPEN_DATA": {
        "name": "Qatar Open Data Portal (Hukoomi)",
        "priority": 92,
        "base_url": "https://hukoomi.gov.qa/dataportal",
        "client_file": "src/data/apis/qatar_opendata.py",
        "client_class": "QatarOpenDataScraperV2",
        
        "datasets": {
            "count": "1000+ public datasets",
            "categories": [
                "National statistics",
                "Economic indicators",
                "Population demographics",
                "Employment data",
                "Infrastructure metrics",
                "Social indicators",
                "Health statistics",
                "Education data",
                "Environment",
                "Transportation"
            ]
        },
        
        "features": [
            "Multilingual (Arabic/English)",
            "Real-time updates",
            "CSV/JSON export",
            "API access"
        ]
    },
    
    # =========================================================================
    # 7. ARAB DEVELOPMENT PORTAL - REGIONAL DATA
    # =========================================================================
    "ARAB_DEV_PORTAL": {
        "name": "Arab Development Portal",
        "priority": 90,
        "base_url": "https://data.arabdevelopmentportal.org",
        "client_file": "src/data/apis/arab_dev_portal.py",
        "client_class": "ArabDevPortalClient",
        
        "data_types": [
            "Country profiles (22 Arab countries)",
            "Economic indicators",
            "SDG progress tracking",
            "Social development metrics",
            "Human development index",
            "Education statistics",
            "Health indicators",
            "Climate data"
        ],
        
        "qatar_profile": {
            "gdp_2025": "$222.12 billion",
            "hdi_2025": "0.89",
            "population_2024": "2.86 million"
        }
    },
    
    # =========================================================================
    # 8. UN ESCWA TRADE DATA - ARAB TRADE STATISTICS
    # =========================================================================
    "ESCWA_TRADE": {
        "name": "UN ESCWA Trade Data Platform (ETDP)",
        "priority": 88,
        "base_url": "https://etdp.unescwa.org",
        "client_file": "src/data/apis/escwa_etdp.py",
        "client_class": "ESCWATradeAPI",
        
        "data_types": [
            "Export/Import data (2012-present)",
            "6-digit HS code product detail",
            "Bilateral trade flows",
            "Economic grouping breakdowns",
            "Trade balance trends"
        ],
        
        "use_when": ["trade", "exports", "imports", "commerce", "bilateral"]
    },
    
    # =========================================================================
    # 9. SEMANTIC SCHOLAR - ACADEMIC RESEARCH
    # =========================================================================
    "SEMANTIC_SCHOLAR": {
        "name": "Semantic Scholar Academic API",
        "priority": 85,
        "base_url": "https://api.semanticscholar.org/graph/v1",
        "authentication": "API Key (SEMANTIC_SCHOLAR_API_KEY)",
        "client_file": "src/data/apis/semantic_scholar.py",
        
        "capabilities": {
            "paper_search": "Search 200M+ academic papers",
            "recommendations": "Get related papers",
            "citations": "Citation networks",
            "abstracts": "Full paper abstracts"
        },
        
        "search_strategies": [
            "Direct query search",
            "Author-based search",
            "Citation-based recommendations",
            "Field-specific filtering"
        ],
        
        "use_when": [
            "Academic research needed",
            "Policy analysis papers",
            "Best practices from literature",
            "Evidence-based recommendations",
            "Skills/labor market research"
        ]
    },
    
    # =========================================================================
    # 10. PERPLEXITY AI - REAL-TIME INTELLIGENCE
    # =========================================================================
    "PERPLEXITY": {
        "name": "Perplexity AI Search API",
        "priority": 80,
        "authentication": "API Key (PERPLEXITY_API_KEY)",
        
        "capabilities": {
            "real_time_search": "Current information with citations",
            "synthesis": "AI-synthesized answers from multiple sources",
            "fact_checking": "Verification with source attribution"
        },
        
        "models": [
            "llama-3.1-sonar-small-128k-online",
            "llama-3.1-sonar-large-128k-online"
        ],
        
        "use_when": [
            "Current events analysis",
            "Recent statistics not in databases",
            "Policy announcements",
            "Market developments",
            "Real-time verification"
        ]
    },
    
    # =========================================================================
    # 11. BRAVE SEARCH - WEB INTELLIGENCE
    # =========================================================================
    "BRAVE_SEARCH": {
        "name": "Brave Search API",
        "priority": 75,
        "authentication": "API Key (BRAVE_API_KEY)",
        
        "capabilities": {
            "web_search": "General web search",
            "news_search": "Recent news articles",
            "local_search": "Business information"
        },
        
        "use_when": [
            "Recent news needed",
            "Company information",
            "Industry reports",
            "Government announcements"
        ]
    },
    
    # =========================================================================
    # 12-18. SPECIALIZED INTERNATIONAL APIS
    # =========================================================================
    "FAO_STAT": {
        "name": "FAO Statistics (Food & Agriculture)",
        "priority": 85,
        "client_file": "src/data/apis/fao_api.py",
        "data": ["Food security", "Agricultural production", "Land use", "Food imports"],
        "use_when": ["food security", "agriculture", "food imports"]
    },
    
    "UNWTO": {
        "name": "UN World Tourism Organization",
        "priority": 85,
        "client_file": "src/data/apis/unwto_api.py",
        "data": ["Tourism arrivals", "Tourism revenue", "Hospitality sector"],
        "use_when": ["tourism", "hospitality", "visitors", "world cup"]
    },
    
    "IEA": {
        "name": "International Energy Agency",
        "priority": 85,
        "client_file": "src/data/apis/iea_api.py",
        "data": ["Energy production", "Oil/gas statistics", "Renewable energy"],
        "use_when": ["energy", "oil", "gas", "LNG", "renewables"]
    },
    
    "UNCTAD": {
        "name": "UN Conference on Trade and Development",
        "priority": 85,
        "client_file": "src/data/apis/unctad_api.py",
        "data": ["FDI flows", "Investment climate", "Trade facilitation"],
        "use_when": ["investment", "FDI", "trade", "development"]
    },
    
    "FRED": {
        "name": "Federal Reserve Economic Data",
        "priority": 75,
        "client_file": "src/data/apis/fred_api.py",
        "data": ["US economic indicators", "Global benchmarks"],
        "use_when": ["US comparison", "global benchmarks", "interest rates"]
    },
    
    "UN_COMTRADE": {
        "name": "UN Comtrade Database",
        "priority": 80,
        "client_file": "src/data/apis/un_comtrade_api.py",
        "data": ["Detailed trade flows", "HS code level", "Partner analysis"],
        "use_when": ["detailed trade", "product-level trade", "trade partners"]
    },
    
    # =========================================================================
    # LOCAL KNOWLEDGE SOURCES
    # =========================================================================
    "KNOWLEDGE_GRAPH": {
        "name": "QNWIS Knowledge Graph",
        "priority": 90,
        "file": "data/knowledge_graph.json",
        "client_file": "src/qnwis/knowledge/graph_builder.py",
        
        "contents": {
            "nodes": [
                "Sectors (Energy, Finance, Healthcare, Education, etc.)",
                "Skills (Technical, Soft, Emerging)",
                "Occupations (detailed job titles)",
                "Policies (Qatarization, Vision 2030)",
                "Metrics (KPIs, targets)",
                "Organizations (ministries, companies)"
            ],
            "edges": [
                "REQUIRES_SKILL - jobs require skills",
                "EMPLOYS_IN - sectors employ occupations",
                "AFFECTS - policies affect sectors",
                "HAS_TARGET - metrics have targets"
            ]
        },
        
        "use_when": [
            "Relationship analysis",
            "Causal reasoning",
            "Skills-job matching",
            "Policy impact analysis"
        ]
    },
    
    "RAG_SYSTEM": {
        "name": "RAG - 56 R&D Research Reports",
        "priority": 92,
        "client_file": "src/qnwis/rag/retriever.py",
        
        "reports": [
            # Core Qatar Labor Market
            "Qatar Labor Landscape - Comprehensive Overview",
            "Knowledge-Based Economy - LMIS Role in Vision 2030",
            "Korea LMIS Case Study - World Class Systems",
            
            # Skills & Future of Work
            "GenAI and the Workforce 2023",
            "Future of Jobs in the Era of AI",
            "Skills Trends in Arab Region (ChatGPT era)",
            "Emerging and Decaying Skills Analysis",
            "Manufacturing Sector Skills Gap",
            
            # Digital & Technology
            "Qatar Digital Investment Opportunities",
            "Qatar's ICT Landscape 2022",
            "State of AI 2023",
            "State of Data + AI 2023",
            
            # Economic Analysis
            "Qatar Economic Outlook 2021-2023",
            "Global Economic Prospects 2023",
            "Economic Potential of Generative AI",
            
            # Policy & Strategy
            "Workforce of the Future 2030",
            "Digitization, AI, and Future of Work (Europe)",
            "Knowledge Graphs for Responsive Businesses",
            "Blockchain in Employment Law",
            
            # Research Reports Q1-Q10 Series
            "Research Report Series (Q1-Q10) - Detailed labor analytics"
        ],
        
        "use_when": [
            "Detailed Qatar labor market analysis",
            "Skills gap research",
            "Vision 2030 progress",
            "AI/digital transformation impact",
            "Policy recommendations",
            "Academic-quality research"
        ]
    },
    
    "POSTGRESQL_CACHE": {
        "name": "PostgreSQL Data Cache",
        "priority": 99,  # Fastest retrieval
        
        "tables": {
            "world_bank_indicators": "128+ cached World Bank indicators",
            "gcc_labour_statistics": "GCC regional comparisons",
            "ilo_labour_data": "ILO international data",
            "vision_2030_targets": "Qatar Vision 2030 KPIs",
            "qatar_open_data": "Qatar government datasets"
        },
        
        "use_when": [
            "Fast retrieval needed (<100ms)",
            "Historical time series",
            "Pre-validated data"
        ]
    },
    
    "VISION_2030_TARGETS": {
        "name": "Qatar National Vision 2030 Targets",
        "priority": 98,
        
        "targets": {
            "qatarization_public": {"target": 95, "unit": "%", "year": 2030},
            "qatarization_private": {"target": 40, "unit": "%", "year": 2030},
            "qatari_unemployment": {"target": 2.0, "unit": "%", "year": 2030},
            "female_participation": {"target": 60, "unit": "%", "year": 2030},
            "knowledge_economy_share": {"target": 60, "unit": "%", "year": 2030},
            "stem_graduates": {"target": 45, "unit": "%", "year": 2030},
            "youth_skills_development": {"target": 85, "unit": "%", "year": 2030}
        },
        
        "use_when": ["Vision 2030", "targets", "KPIs", "strategic goals"]
    }
}


# =============================================================================
# QUERY-TO-SOURCE MAPPING - WHAT TO USE WHEN
# =============================================================================

QUERY_ROUTING = {
    "labor_market": {
        "primary": ["MOL_LMIS", "POSTGRESQL_CACHE"],
        "secondary": ["GCC_STAT", "ILO_ILOSTAT", "RAG_SYSTEM"],
        "keywords": ["unemployment", "employment", "labor", "workforce", "jobs"]
    },
    
    "qatarization": {
        "primary": ["MOL_LMIS", "VISION_2030_TARGETS"],
        "secondary": ["RAG_SYSTEM", "KNOWLEDGE_GRAPH"],
        "keywords": ["qatarization", "nationalization", "nationals", "qatari"]
    },
    
    "skills": {
        "primary": ["MOL_LMIS", "RAG_SYSTEM"],
        "secondary": ["SEMANTIC_SCHOLAR", "KNOWLEDGE_GRAPH"],
        "keywords": ["skills", "training", "education", "graduates", "gap"]
    },
    
    "economy": {
        "primary": ["WORLD_BANK", "IMF_DATA", "POSTGRESQL_CACHE"],
        "secondary": ["PERPLEXITY", "RAG_SYSTEM"],
        "keywords": ["GDP", "growth", "economy", "fiscal", "investment"]
    },
    
    "trade": {
        "primary": ["ESCWA_TRADE", "UN_COMTRADE", "WORLD_BANK"],
        "secondary": ["UNCTAD"],
        "keywords": ["trade", "exports", "imports", "commerce"]
    },
    
    "energy": {
        "primary": ["IEA", "WORLD_BANK"],
        "secondary": ["PERPLEXITY", "BRAVE_SEARCH"],
        "keywords": ["energy", "oil", "gas", "LNG", "petroleum"]
    },
    
    "tourism": {
        "primary": ["UNWTO", "QATAR_OPEN_DATA"],
        "secondary": ["PERPLEXITY"],
        "keywords": ["tourism", "visitors", "hospitality", "hotels"]
    },
    
    "regional_comparison": {
        "primary": ["GCC_STAT", "ARAB_DEV_PORTAL"],
        "secondary": ["WORLD_BANK", "ILO_ILOSTAT"],
        "keywords": ["GCC", "regional", "comparison", "benchmark", "Saudi", "UAE"]
    },
    
    "research": {
        "primary": ["RAG_SYSTEM", "SEMANTIC_SCHOLAR"],
        "secondary": ["KNOWLEDGE_GRAPH"],
        "keywords": ["research", "study", "analysis", "academic", "paper"]
    },
    
    "current_events": {
        "primary": ["PERPLEXITY", "BRAVE_SEARCH"],
        "secondary": ["QATAR_OPEN_DATA"],
        "keywords": ["recent", "latest", "news", "announcement", "2024", "2025"]
    }
}


# =============================================================================
# AGENT DATA AWARENESS PROMPT
# =============================================================================

AGENT_DATA_PROMPT = """
## AVAILABLE DATA SOURCES - YOU MUST USE THESE

You have access to 18+ authoritative data sources. USE THEM ALL when relevant.

### TIER 1 - QATAR OFFICIAL (Priority 100)
1. **MOL LMIS** - Qatar Ministry of Labour: 17 endpoints
   - Main indicators, skills gaps, sector growth, Qatarization, salaries
   - USE FOR: Any Qatar labor market question

2. **Qatar Open Data** - 1000+ government datasets
   - USE FOR: Qatar-specific statistics

3. **Vision 2030 Targets** - Official KPIs
   - USE FOR: Any strategic/target question

### TIER 2 - AUTHORITATIVE INTERNATIONAL (Priority 90-95)
4. **World Bank** - 128+ economic indicators
5. **GCC-STAT** - Regional GCC comparisons
6. **ILO ILOSTAT** - International labor standards
7. **IMF Data** - Economic FORECASTS to 2029
8. **Arab Development Portal** - Arab region data

### TIER 3 - SPECIALIZED (Priority 80-90)
9. **Semantic Scholar** - 200M+ academic papers
10. **UN ESCWA Trade** - Arab trade statistics
11. **FAO STAT** - Food security data
12. **UNWTO** - Tourism statistics
13. **IEA** - Energy sector data
14. **UNCTAD** - Investment/FDI data

### TIER 4 - REAL-TIME (Priority 70-80)
15. **Perplexity AI** - Current events with citations
16. **Brave Search** - Recent news/reports

### LOCAL KNOWLEDGE (Priority 90+)
17. **Knowledge Graph** - Entity relationships, causal links
18. **RAG System** - 56 R&D reports with Qatar research:
    - Qatar labor landscape analysis
    - Skills gap studies
    - AI/Digital transformation impact
    - Vision 2030 implementation
    - Future of jobs research

### PostgreSQL Cache - FASTEST (Priority 99)
- Pre-cached World Bank, GCC-STAT, ILO data
- Sub-100ms retrieval

## DATA EXTRACTION RULES

1. **ALWAYS** check PostgreSQL cache first for fast data
2. **ALWAYS** use MOL LMIS for Qatar labor questions
3. **ALWAYS** use RAG for research-backed insights
4. **ALWAYS** use Knowledge Graph for relationships
5. **NEVER** make up data - say "NOT IN DATA" if unavailable
6. **CITE** the source for every fact
7. **COMPARE** using GCC-STAT for regional context
8. **VERIFY** using multiple sources when possible
"""


def get_sources_for_query(query: str) -> list:
    """
    Determine which data sources to use for a query.
    Returns ordered list of source IDs by relevance.
    """
    query_lower = query.lower()
    sources = set()
    
    for category, config in QUERY_ROUTING.items():
        if any(kw in query_lower for kw in config["keywords"]):
            sources.update(config["primary"])
            sources.update(config["secondary"])
    
    # Always include these for comprehensive analysis
    sources.add("POSTGRESQL_CACHE")
    sources.add("RAG_SYSTEM")
    sources.add("KNOWLEDGE_GRAPH")
    
    # Sort by priority
    sorted_sources = sorted(
        sources,
        key=lambda s: DATA_SOURCES.get(s, {}).get("priority", 0),
        reverse=True
    )
    
    return sorted_sources

