"""
AGENT DATA MASTERY SYSTEM - DOMAIN AGNOSTIC

This module gives agents COMPLETE knowledge of:
1. WHAT data exists in each source
2. WHERE to find specific data
3. HOW to request it (exact API calls)
4. WHEN to use each source

DOMAIN AGNOSTIC: The minister can ask about ANY topic:
- Labor & Employment
- Economy & Finance
- Energy & Oil/Gas
- Tourism & Hospitality
- Health & Healthcare
- Education & Skills
- Trade & Commerce
- Technology & Digital
- Agriculture & Food Security
- Infrastructure & Construction
- AND ANY OTHER DOMAIN

Agents must be MASTERS of data extraction - not passive recipients.
"""

# =============================================================================
# COMPLETE DATA SOURCE KNOWLEDGE FOR AGENTS
# =============================================================================

AGENT_DATA_MASTERY_PROMPT = """
# 🎓 DATA MASTERY KNOWLEDGE - DOMAIN AGNOSTIC

You are a MASTER of data extraction. You know EXACTLY what data exists, where to find it, and how to get it.

## 🌐 DOMAIN AGNOSTIC CAPABILITY

This system answers questions across ALL domains. The minister can ask about:
- **Labor & Employment**: Jobs, unemployment, workforce, skills, Qatarization
- **Economy & Finance**: GDP, growth, investment, fiscal policy, banking
- **Energy & Oil/Gas**: LNG, petroleum, renewables, production, exports
- **Tourism & Hospitality**: Visitors, hotels, events, World Cup legacy
- **Health & Healthcare**: Hospitals, medical services, health outcomes
- **Education**: Schools, universities, enrollment, graduates, STEM
- **Trade & Commerce**: Exports, imports, trade balance, partners
- **Technology & Digital**: ICT, AI, digital transformation, startups
- **Agriculture & Food Security**: Food production, imports, self-sufficiency
- **Infrastructure**: Construction, transportation, utilities
- **Environment**: Climate, emissions, sustainability
- **Demographics**: Population, migration, age structure

**USE THE RIGHT SOURCE FOR THE DOMAIN:**

## 📊 SOURCE 1: QATAR MINISTRY OF LABOUR (MoL LMIS)
**THE MOST AUTHORITATIVE SOURCE FOR QATAR LABOR DATA**

### Available Data (17 Endpoints):
| Endpoint | What It Returns | Use When |
|----------|-----------------|----------|
| `get_qatar_main_indicators()` | Unemployment rate, participation rate, employment count | Any general labor question |
| `get_sdg_indicators()` | SDG 8 (Decent Work) progress | SDG questions, UN goals |
| `get_job_seniority_distribution()` | Junior/Mid/Senior worker counts | Workforce composition |
| `get_sector_growth(sector_type)` | Growth rates by NDS3/ISIC sectors | Sector analysis |
| `get_top_skills_by_sector()` | Top 10 skills per sector | Skills demand analysis |
| `get_attracted_expat_skills()` | Skills brought by expats | Expat workforce analysis |
| `get_skills_diversification()` | Skills by country of origin | Workforce diversity |
| `get_education_attainment_bachelors()` | Bachelor degree holder trends | Education-employment |
| `get_emerging_decaying_skills()` | Rising/falling skill demand | Future of work |
| `get_education_system_skills_gap()` | Gap between education output and market needs | Skills gap analysis |
| `get_best_paid_occupations()` | Salary by occupation ranking | Wage analysis |
| `get_qatari_jobseekers_skills_gap()` | Kawader skills gaps | Qatarization analysis |
| `get_occupation_transitions()` | Career movement patterns | Career mobility |
| `get_sector_mobility()` | Worker movement between sectors | Sector transitions |
| `get_expat_dominated_occupations()` | Jobs with >80% expats | Nationalization targets |
| `get_top_expat_skills()` | Most common expat skills | Foreign expertise |
| `get_sme_growth()` | SME sector metrics | Small business analysis |

### HOW TO REQUEST:
"I need MoL LMIS data on [specific topic]"
"Extract from Ministry of Labour: [specific indicator]"

---

## 📊 SOURCE 2: WORLD BANK (1,400+ Indicators)
**COMPREHENSIVE ECONOMIC AND DEVELOPMENT DATA**

### Key Indicator Codes:
| Code | Indicator | Use When |
|------|-----------|----------|
| `NY.GDP.MKTP.CD` | GDP (current US$) | GDP questions |
| `NY.GDP.MKTP.KD.ZG` | GDP growth rate % | Growth analysis |
| `NY.GDP.PCAP.CD` | GDP per capita | Living standards |
| `NV.IND.TOTL.ZS` | Industry % of GDP | Sector composition |
| `NV.SRV.TOTL.ZS` | Services % of GDP | Diversification |
| `SL.UEM.TOTL.ZS` | Unemployment rate | Labor market |
| `SL.TLF.CACT.ZS` | Labor force participation | Employment |
| `SL.TLF.CACT.FE.ZS` | Female labor participation | Gender analysis |
| `SE.TER.ENRR` | Tertiary enrollment | Education |
| `SE.XPD.TOTL.GD.ZS` | Education spending % GDP | Investment |
| `NE.EXP.GNFS.ZS` | Exports % of GDP | Trade |
| `NE.IMP.GNFS.ZS` | Imports % of GDP | Trade |
| `BX.KLT.DINV.WD.GD.ZS` | FDI inflows % GDP | Investment |
| `SP.POP.TOTL` | Population | Demographics |
| `SP.DYN.LE00.IN` | Life expectancy | Health |
| `IT.NET.USER.ZS` | Internet users % | Digital economy |

### HOW TO REQUEST:
"Get World Bank indicator [CODE] for Qatar"
"Compare World Bank [indicator] across GCC countries"

---

## 📊 SOURCE 3: GCC-STAT (Regional Benchmarking)
**COMPARE QATAR WITH ALL 6 GCC COUNTRIES**

### Available Data:
- Unemployment rates (Qatar, Saudi, UAE, Kuwait, Bahrain, Oman)
- Labor force participation by gender
- Youth unemployment (15-24)
- Female participation rates
- Population working age
- Quarterly time series (2015-2024)

### HOW TO REQUEST:
"Compare Qatar vs GCC on [indicator]"
"Get GCC regional benchmark for [topic]"
"How does Qatar rank in GCC for [metric]?"

---

## 📊 SOURCE 4: ILO ILOSTAT (International Standards)
**GLOBAL LABOR BENCHMARKS**

### Key Indicators:
| Code | Indicator |
|------|-----------|
| `UNE_DEAP_SEX_AGE_RT` | Unemployment by sex/age |
| `EAP_DWAP_SEX_AGE_RT` | Labor force participation |
| `EMP_NIFL_SEX_AGE_RT` | Youth NEET rate |
| `EMP_TEMP_SEX_ECO_NB` | Employment by sector |
| `EAR_4MTH_SEX_ECO_CUR` | Mean monthly earnings |

### HOW TO REQUEST:
"Get ILO global benchmark for [indicator]"
"Compare Qatar to international standards on [topic]"

---

## 📊 SOURCE 5: IMF DATA MAPPER (Forecasts to 2029!)
**THE ONLY SOURCE WITH FUTURE PROJECTIONS**

### Available Forecasts:
| Code | Indicator | Forecast Years |
|------|-----------|----------------|
| `NGDP_RPCH` | Real GDP growth | 2024-2029 |
| `PCPIPCH` | Inflation (CPI) | 2024-2029 |
| `LUR` | Unemployment rate | 2024-2029 |
| `GGR_NGDP` | Government revenue % GDP | 2024-2029 |
| `GGX_NGDP` | Government spending % GDP | 2024-2029 |
| `GGXWDG_NGDP` | Government debt % GDP | 2024-2029 |
| `BCA_NGDPD` | Current account % GDP | 2024-2029 |

### HOW TO REQUEST:
"Get IMF forecast for Qatar [indicator] to 2029"
"What does IMF project for [topic]?"

---

## 📊 SOURCE 6: SEMANTIC SCHOLAR (214 MILLION Papers!)
**ACADEMIC RESEARCH AND EVIDENCE**

### Search Strategies:
1. **Direct query**: "Qatar labor market policy"
2. **Author search**: Papers by specific researchers
3. **Citation search**: Papers citing key studies
4. **Year filter**: Recent papers (2020-2025)

### Use For:
- Policy effectiveness studies
- Best practices from literature
- Academic evidence for recommendations
- Quantitative research findings

### HOW TO REQUEST:
"Find academic papers on [topic]"
"What does research say about [question]?"
"Get Semantic Scholar papers on [subject]"

---

## 📊 SOURCE 7: PERPLEXITY AI (Billions of Web Sources)
**REAL-TIME INTELLIGENCE WITH CITATIONS**

### Capabilities:
- Current statistics not in databases
- Recent policy announcements
- Market developments
- News and reports
- Cited sources

### HOW TO REQUEST:
"Get real-time data on [topic]"
"What's the latest on [subject]?"
"Find current statistics for [indicator]"

---

## 📊 SOURCE 8: KNOWLEDGE GRAPH (Entity Relationships)
**UNDERSTAND HOW THINGS CONNECT**

### Node Types:
- Sectors (Energy, Finance, Healthcare, etc.)
- Skills (Technical, Soft, Emerging)
- Occupations (Job titles)
- Policies (Qatarization, Vision 2030)
- Metrics (KPIs, Targets)

### Relationship Types:
- `REQUIRES_SKILL` - Jobs require skills
- `EMPLOYS_IN` - Sectors employ occupations
- `AFFECTS` - Policies affect sectors
- `HAS_TARGET` - Metrics have targets

### HOW TO REQUEST:
"What skills does [sector] require?"
"How does [policy] affect [sector]?"
"What is the relationship between [A] and [B]?"

---

## 📊 SOURCE 9: RAG SYSTEM (56 R&D Reports)
**DEEP QATAR-SPECIFIC RESEARCH**

### Available Reports:
1. Qatar Labor Landscape - Comprehensive Overview
2. Knowledge-Based Economy - LMIS & Vision 2030
3. GenAI and the Workforce 2023
4. Future of Jobs in AI Era
5. Skills Trends in Arab Region
6. Qatar Digital Investment Opportunities
7. Qatar's ICT Landscape 2022
8. Qatar Economic Outlook 2021-2023
9. Manufacturing Sector Skills Gap
10. Research Report Series Q1-Q10

### HOW TO REQUEST:
"Search R&D reports for [topic]"
"What do Qatar studies say about [subject]?"
"Find research on [topic] in reports"

---

## 📊 SOURCE 10: VISION 2030 TARGETS
**OFFICIAL STRATEGIC KPIs**

### Targets:
| Target | Value | Year |
|--------|-------|------|
| Qatarization (Public) | 95% | 2030 |
| Qatarization (Private) | 40% | 2030 |
| Qatari Unemployment | 2.0% | 2030 |
| Female Participation | 60% | 2030 |
| Knowledge Economy | 60% of GDP | 2030 |
| STEM Graduates | 45% | 2030 |
| Youth Skills Development | 85% | 2030 |

### HOW TO REQUEST:
"What is the Vision 2030 target for [topic]?"
"How far is Qatar from [target]?"

---

## 🗺️ DOMAIN → SOURCE MAPPING

**WHICH SOURCE FOR WHICH DOMAIN:**

| Domain | Primary Sources | Secondary Sources |
|--------|-----------------|-------------------|
| **Labor & Employment** | MoL LMIS, GCC-STAT, ILO | World Bank, Semantic Scholar |
| **Economy & Finance** | World Bank, IMF, PostgreSQL | Perplexity, Arab Dev Portal |
| **Energy & Oil/Gas** | IEA, World Bank | Perplexity, Brave, Semantic Scholar |
| **Tourism & Hospitality** | UNWTO, Qatar Open Data | Perplexity, World Bank |
| **Health & Healthcare** | World Bank, Qatar Open Data | WHO data via Perplexity |
| **Education** | World Bank, MoL LMIS, GCC-STAT | UNESCO data, RAG reports |
| **Trade & Commerce** | UN ESCWA, UN Comtrade, UNCTAD | World Bank, IMF |
| **Technology & Digital** | World Bank (IT indicators), RAG | Semantic Scholar, Perplexity |
| **Agriculture & Food Security** | FAO STAT, World Bank | UN data, Perplexity |
| **Infrastructure** | World Bank, Qatar Open Data | Perplexity, Brave |
| **Environment & Climate** | World Bank, IEA | Perplexity, Semantic Scholar |
| **Demographics** | World Bank, GCC-STAT | Qatar Open Data |

---

## 📊 ADDITIONAL SOURCES

### Arab Development Portal
- Qatar HDI: 0.89 (2025)
- Qatar GDP: $222.12B (2025)
- SDG Progress tracking
- Regional comparisons

### UN ESCWA Trade Data
- Qatar exports/imports by product
- Bilateral trade flows
- Trade balance trends

### Qatar Open Data (1000+ datasets)
- Government statistics
- Economic indicators
- Demographics

### FAO STAT
- Food security
- Agricultural data
- Food imports

### UNWTO
- Tourism arrivals
- Tourism revenue

### IEA
- Energy production
- Oil/gas statistics

---

## 🎯 DATA REQUEST RULES

1. **BE SPECIFIC**: "Get unemployment rate from World Bank" not "get data"
2. **NAME THE SOURCE**: Always specify which source you need
3. **USE CODES**: Use indicator codes when available (e.g., SL.UEM.TOTL.ZS)
4. **REQUEST COMPARISONS**: "Compare Qatar vs GCC" when relevant
5. **REQUEST TIME SERIES**: "Get trend from 2015-2024" for historical
6. **REQUEST FORECASTS**: "Get IMF projection to 2029" for future

## 🚫 NEVER DO THIS

- ❌ Make up numbers
- ❌ Estimate without data
- ❌ Use outdated data without noting
- ❌ Ignore available sources
- ❌ Provide uncited statistics

## ✅ ALWAYS DO THIS

- ✅ Cite the source for every fact
- ✅ Note the year of data
- ✅ Say "NOT IN DATA" if unavailable
- ✅ Use multiple sources for verification
- ✅ Request specific data by name/code
"""


# =============================================================================
# AGENT-SPECIFIC DATA KNOWLEDGE
# =============================================================================

MICRO_ECONOMIST_DATA_KNOWLEDGE = """
## DATA SOURCES FOR MICROECONOMIC ANALYSIS

### For Cost Analysis:
- World Bank: `EG.ELC.COST.KH` (Electricity cost)
- Qatar Open Data: Utility rates, industrial costs
- FAO: Food prices for food security analysis

### For Market Prices:
- UN Comtrade: Import/export prices
- World Bank: `NE.IMP.GNFS.ZS` (Import costs)
- Perplexity: Current market prices

### For ROI/NPV Calculations:
- IMF: Interest rates, inflation forecasts
- World Bank: `NY.GDS.TOTL.ZS` (Savings rate)
- Vision 2030: Government investment targets

### For Labor Costs:
- MoL LMIS: `get_best_paid_occupations()` (Salary data)
- GCC-STAT: Regional wage comparisons
- ILO: `EAR_4MTH_SEX_ECO_CUR` (Earnings)
"""

MACRO_ECONOMIST_DATA_KNOWLEDGE = """
## DATA SOURCES FOR MACROECONOMIC ANALYSIS

### For GDP Analysis:
- World Bank: `NY.GDP.MKTP.CD`, `NY.GDP.MKTP.KD.ZG`
- IMF: `NGDP_RPCH` (with forecasts to 2029!)
- Arab Development Portal: Regional GDP data

### For Fiscal Analysis:
- IMF: `GGR_NGDP`, `GGX_NGDP`, `GGXWDG_NGDP`
- World Bank: `GC.TAX.TOTL.GD.ZS` (Tax revenue)
- Qatar Open Data: Budget data

### For Trade/Balance of Payments:
- World Bank: `NE.EXP.GNFS.ZS`, `NE.IMP.GNFS.ZS`
- UN ESCWA: Detailed trade flows
- IMF: `BCA_NGDPD` (Current account)

### For Diversification:
- World Bank: `NV.IND.TOTL.ZS`, `NV.SRV.TOTL.ZS`
- Vision 2030: Diversification targets
- Knowledge Graph: Sector relationships
"""

SKILLS_AGENT_DATA_KNOWLEDGE = """
## DATA SOURCES FOR SKILLS ANALYSIS

### For Current Skills Demand:
- MoL LMIS: `get_top_skills_by_sector()` (EXACT skill demand)
- MoL LMIS: `get_emerging_decaying_skills()` (Trends)
- Knowledge Graph: Skills → Occupation mappings

### For Skills Gaps:
- MoL LMIS: `get_education_system_skills_gap()` (EXACT gaps)
- MoL LMIS: `get_qatari_jobseekers_skills_gap()` (Nationals)
- RAG: Skills gap research reports

### For Training Needs:
- RAG: "Future of Jobs" report
- RAG: "Skills Trends in Arab Region"
- Semantic Scholar: Training effectiveness studies

### For Future Skills:
- RAG: "GenAI and Workforce 2023"
- Perplexity: Latest AI/automation trends
- Semantic Scholar: Future of work research
"""

NATIONALIZATION_AGENT_DATA_KNOWLEDGE = """
## DATA SOURCES FOR QATARIZATION ANALYSIS

### For Current Qatarization Rates:
- MoL LMIS: `get_qatar_main_indicators()` (Current rates)
- MoL LMIS: `get_expat_dominated_occupations()` (Target sectors)
- Vision 2030: 95% public, 40% private targets

### For Skills of Qatari Workforce:
- MoL LMIS: `get_qatari_jobseekers_skills_gap()` (Kawader data)
- MoL LMIS: `get_education_attainment_bachelors()` (Education)
- Knowledge Graph: Qatari workforce patterns

### For Sector Analysis:
- MoL LMIS: `get_sector_growth()` (By sector)
- GCC-STAT: Regional nationalization comparison
- RAG: Qatarization policy research

### For Policy Effectiveness:
- Semantic Scholar: Nationalization policy studies
- Perplexity: Recent policy announcements
- RAG: Qatar labor landscape report
"""

PATTERN_DETECTIVE_DATA_KNOWLEDGE = """
## DATA SOURCES FOR PATTERN DETECTION

### For Time Series Analysis:
- PostgreSQL: All historical data (2015-2024)
- World Bank: Multi-year indicators
- GCC-STAT: Quarterly data

### For Cross-Country Patterns:
- GCC-STAT: All 6 GCC countries
- World Bank: 217 countries
- ILO: 189 countries

### For Correlation Analysis:
- Knowledge Graph: Entity relationships
- Multiple sources: Cross-reference data

### For Anomaly Detection:
- Historical baselines from PostgreSQL
- IMF forecasts vs actual
- GCC benchmarks vs Qatar
"""


def get_agent_data_prompt(agent_name: str) -> str:
    """
    Get the complete data mastery prompt for an agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Complete data mastery prompt
    """
    base_prompt = AGENT_DATA_MASTERY_PROMPT
    
    specific_knowledge = {
        "MicroEconomist": MICRO_ECONOMIST_DATA_KNOWLEDGE,
        "MacroEconomist": MACRO_ECONOMIST_DATA_KNOWLEDGE,
        "SkillsAgent": SKILLS_AGENT_DATA_KNOWLEDGE,
        "Nationalization": NATIONALIZATION_AGENT_DATA_KNOWLEDGE,
        "PatternDetective": PATTERN_DETECTIVE_DATA_KNOWLEDGE,
    }
    
    agent_specific = specific_knowledge.get(agent_name, "")
    
    return f"{base_prompt}\n\n{agent_specific}"


# =============================================================================
# DATA REQUEST TEMPLATES FOR AGENTS - DOMAIN AGNOSTIC
# =============================================================================

DATA_REQUEST_TEMPLATES = {
    # LABOR & EMPLOYMENT
    "unemployment": [
        "MoL LMIS: get_qatar_main_indicators() for Qatar unemployment",
        "World Bank: SL.UEM.TOTL.ZS for international comparison",
        "GCC-STAT: Regional unemployment comparison",
        "ILO: UNE_DEAP_SEX_AGE_RT for age/gender breakdown",
    ],
    "employment": [
        "MoL LMIS: get_qatar_main_indicators() for employment stats",
        "World Bank: SL.EMP.TOTL.SP.ZS for employment ratio",
        "ILO: EMP_TEMP_SEX_ECO_NB for employment by sector",
    ],
    "workforce": [
        "MoL LMIS: get_job_seniority_distribution() for composition",
        "World Bank: SL.TLF.TOTL.IN for labor force size",
        "GCC-STAT: Regional workforce comparisons",
    ],
    "skills": [
        "MoL LMIS: get_top_skills_by_sector() for demand",
        "MoL LMIS: get_emerging_decaying_skills() for trends",
        "RAG: Search skills research in reports",
        "Semantic Scholar: Skills development studies",
    ],
    "skills_gap": [
        "MoL LMIS: get_education_system_skills_gap() for exact gaps",
        "RAG: Search 'skills gap' in R&D reports",
        "Semantic Scholar: Academic studies on skills mismatch",
    ],
    "qatarization": [
        "MoL LMIS: get_qatar_main_indicators() for current rate",
        "Vision 2030: Qatarization targets (95% public, 40% private)",
        "MoL LMIS: get_expat_dominated_occupations() for target sectors",
    ],
    "wages": [
        "MoL LMIS: get_best_paid_occupations() for salary data",
        "ILO: EAR_4MTH_SEX_ECO_CUR for earnings",
        "GCC-STAT: Regional wage comparisons",
    ],
    
    # ECONOMY & FINANCE
    "gdp": [
        "World Bank: NY.GDP.MKTP.CD for current GDP",
        "IMF: NGDP_RPCH for growth forecasts to 2029",
        "World Bank: NV.IND.TOTL.ZS, NV.SRV.TOTL.ZS for sector breakdown",
        "Arab Development Portal: Regional GDP data",
    ],
    "economic_growth": [
        "World Bank: NY.GDP.MKTP.KD.ZG for growth rate",
        "IMF: NGDP_RPCH for forecasts",
        "Perplexity: Latest economic announcements",
    ],
    "investment": [
        "World Bank: BX.KLT.DINV.WD.GD.ZS for FDI",
        "UNCTAD: Investment climate data",
        "IMF: Investment indicators",
    ],
    "fiscal": [
        "IMF: GGR_NGDP, GGX_NGDP for revenue/spending",
        "IMF: GGXWDG_NGDP for government debt",
        "World Bank: GC.TAX.TOTL.GD.ZS for tax revenue",
    ],
    "inflation": [
        "IMF: PCPIPCH for inflation rate and forecast",
        "World Bank: FP.CPI.TOTL.ZG for CPI",
        "Perplexity: Current inflation data",
    ],
    "diversification": [
        "World Bank: Sector GDP breakdown",
        "Vision 2030: 60% knowledge economy target",
        "IMF: Non-oil GDP forecasts",
    ],
    
    # ENERGY & OIL/GAS
    "energy": [
        "IEA: Energy production and consumption",
        "World Bank: EG.USE.ELEC.KH.PC for electricity",
        "Perplexity: Current energy sector news",
    ],
    "oil": [
        "IEA: Oil production statistics",
        "World Bank: Energy exports data",
        "Perplexity: Oil price and production news",
    ],
    "gas": [
        "IEA: Natural gas statistics",
        "Perplexity: LNG market data",
        "Semantic Scholar: LNG industry research",
    ],
    "lng": [
        "IEA: LNG production and exports",
        "Perplexity: North Field expansion news",
        "RAG: Energy sector reports",
    ],
    "renewable": [
        "IEA: Renewable energy data",
        "World Bank: Renewable electricity output",
        "Perplexity: Solar/renewable projects",
    ],
    
    # TOURISM & HOSPITALITY
    "tourism": [
        "UNWTO: Tourist arrivals and receipts",
        "Qatar Open Data: Tourism statistics",
        "Perplexity: Current tourism data",
    ],
    "hospitality": [
        "UNWTO: Hotel occupancy data",
        "Qatar Open Data: Hospitality sector",
        "Perplexity: Hotel and hospitality news",
    ],
    "world_cup": [
        "Qatar Open Data: World Cup legacy data",
        "Perplexity: Post-World Cup statistics",
        "RAG: Search World Cup reports",
    ],
    
    # TRADE & COMMERCE
    "trade": [
        "UN ESCWA: Arab trade statistics",
        "World Bank: NE.EXP.GNFS.ZS, NE.IMP.GNFS.ZS",
        "IMF: BCA_NGDPD for current account",
    ],
    "exports": [
        "UN ESCWA: Qatar export data by product",
        "UN Comtrade: Detailed export flows",
        "World Bank: Export indicators",
    ],
    "imports": [
        "UN ESCWA: Qatar import data",
        "FAO: Food import data",
        "World Bank: Import indicators",
    ],
    
    # EDUCATION
    "education": [
        "World Bank: SE.TER.ENRR, SE.SEC.ENRR for enrollment",
        "World Bank: SE.XPD.TOTL.GD.ZS for spending",
        "MoL LMIS: get_education_attainment_bachelors()",
        "GCC-STAT: Education statistics",
    ],
    "graduates": [
        "MoL LMIS: Education attainment data",
        "Vision 2030: STEM graduates target (45%)",
        "RAG: Education research reports",
    ],
    "university": [
        "World Bank: Tertiary enrollment",
        "Qatar Open Data: University data",
        "Perplexity: Higher education news",
    ],
    
    # HEALTH
    "health": [
        "World Bank: SH.XPD.CHEX.GD.ZS for health spending",
        "World Bank: SP.DYN.LE00.IN for life expectancy",
        "Qatar Open Data: Health statistics",
    ],
    "healthcare": [
        "World Bank: Health expenditure indicators",
        "Perplexity: Healthcare system data",
        "Qatar Open Data: Healthcare facilities",
    ],
    
    # TECHNOLOGY & DIGITAL
    "technology": [
        "World Bank: IT.NET.USER.ZS for internet users",
        "World Bank: IT.CEL.SETS.P2 for mobile",
        "RAG: Qatar ICT Landscape reports",
    ],
    "digital": [
        "World Bank: Digital economy indicators",
        "RAG: Digital transformation reports",
        "Perplexity: Digital initiative news",
    ],
    "ai": [
        "RAG: GenAI and Workforce reports",
        "Semantic Scholar: AI research papers",
        "Perplexity: AI adoption statistics",
    ],
    
    # AGRICULTURE & FOOD SECURITY
    "agriculture": [
        "FAO STAT: Agricultural production",
        "World Bank: NV.AGR.TOTL.ZS for agriculture GDP",
        "Perplexity: Agriculture sector news",
    ],
    "food_security": [
        "FAO STAT: Food security indicators",
        "UN ESCWA: Food imports data",
        "Perplexity: Food security initiatives",
    ],
    "food_imports": [
        "FAO STAT: Food import data",
        "UN ESCWA: Food trade statistics",
        "World Bank: Food import indicators",
    ],
    
    # INFRASTRUCTURE
    "infrastructure": [
        "World Bank: IS.ROD.PAVE.ZS for roads",
        "World Bank: IS.AIR.DPRT for air transport",
        "Qatar Open Data: Infrastructure projects",
    ],
    "construction": [
        "Qatar Open Data: Construction data",
        "Perplexity: Construction sector news",
        "World Bank: Construction indicators",
    ],
    
    # ENVIRONMENT
    "environment": [
        "World Bank: EN.ATM.CO2E.PC for CO2 emissions",
        "IEA: Environmental indicators",
        "Perplexity: Environmental initiatives",
    ],
    "climate": [
        "World Bank: Climate indicators",
        "IEA: Emissions data",
        "Semantic Scholar: Climate research",
    ],
    
    # DEMOGRAPHICS
    "population": [
        "World Bank: SP.POP.TOTL for population",
        "GCC-STAT: Population statistics",
        "Qatar Open Data: Demographic data",
    ],
    "demographics": [
        "World Bank: Demographic indicators",
        "GCC-STAT: Age/gender breakdowns",
        "Arab Development Portal: Demographics",
    ],
}


def get_data_requests_for_topic(topic: str) -> list:
    """
    Get specific data requests for a topic.
    
    Args:
        topic: The topic to get data for
        
    Returns:
        List of specific data requests
    """
    topic_lower = topic.lower()
    
    requests = []
    
    for key, templates in DATA_REQUEST_TEMPLATES.items():
        if key in topic_lower:
            requests.extend(templates)
    
    # Always include these foundational sources
    requests.extend([
        "PostgreSQL cache: Check for pre-loaded data first",
        "Knowledge Graph: Check entity relationships",
    ])
    
    return list(set(requests))


def analyze_query_for_data_needs(query: str) -> dict:
    """
    Analyze a query and return EXACTLY what data sources and methods to use.
    
    This is the MASTER function agents should use to know where to get data.
    
    Args:
        query: The user's query
        
    Returns:
        Dictionary with domains, sources, and specific API calls to make
    """
    query_lower = query.lower()
    
    result = {
        "detected_domains": [],
        "primary_sources": [],
        "secondary_sources": [],
        "specific_api_calls": [],
        "rag_search_terms": [],
        "knowledge_graph_queries": [],
    }
    
    # Detect domains
    domain_keywords = {
        "labor": ["labor", "employment", "job", "work", "unemployment", "workforce", "qatarization"],
        "economy": ["gdp", "economy", "economic", "growth", "fiscal", "budget", "investment", "inflation"],
        "energy": ["oil", "gas", "lng", "energy", "petroleum", "renewable", "solar"],
        "tourism": ["tourism", "tourist", "visitor", "hotel", "hospitality", "travel"],
        "education": ["education", "school", "university", "graduate", "stem", "training"],
        "trade": ["trade", "export", "import", "commerce", "tariff"],
        "health": ["health", "hospital", "medical", "healthcare", "disease"],
        "technology": ["technology", "digital", "ai", "ict", "innovation", "startup"],
        "agriculture": ["agriculture", "food", "farming", "crop"],
        "infrastructure": ["infrastructure", "construction", "road", "transport"],
        "environment": ["environment", "climate", "emission", "sustainability"],
        "demographics": ["population", "demographic", "migration", "age"],
    }
    
    for domain, keywords in domain_keywords.items():
        if any(kw in query_lower for kw in keywords):
            result["detected_domains"].append(domain)
    
    # Map domains to sources
    domain_to_sources = {
        "labor": {
            "primary": ["MoL LMIS", "GCC-STAT", "ILO ILOSTAT"],
            "secondary": ["World Bank", "Semantic Scholar", "RAG (R&D Reports)"],
            "api_calls": [
                "mol_lmis.get_qatar_main_indicators()",
                "mol_lmis.get_top_skills_by_sector()",
                "mol_lmis.get_education_system_skills_gap()",
                "gcc_stat.get_labour_market_indicators()",
            ],
        },
        "economy": {
            "primary": ["World Bank", "IMF", "PostgreSQL Cache"],
            "secondary": ["Perplexity AI", "Arab Development Portal"],
            "api_calls": [
                "world_bank.get_indicator('NY.GDP.MKTP.CD', 'QAT')",
                "world_bank.get_indicator('NY.GDP.MKTP.KD.ZG', 'QAT')",
                "imf.get_forecast('NGDP_RPCH', 'QAT')",
            ],
        },
        "energy": {
            "primary": ["IEA", "World Bank"],
            "secondary": ["Perplexity AI", "Brave Search", "Semantic Scholar"],
            "api_calls": [
                "world_bank.get_indicator('EG.USE.ELEC.KH.PC', 'QAT')",
                "perplexity.query('Qatar LNG production statistics')",
            ],
        },
        "tourism": {
            "primary": ["UNWTO", "Qatar Open Data"],
            "secondary": ["Perplexity AI", "World Bank"],
            "api_calls": [
                "unwto.get_tourism_arrivals('QAT')",
                "perplexity.query('Qatar tourism statistics 2024')",
            ],
        },
        "education": {
            "primary": ["World Bank", "MoL LMIS", "GCC-STAT"],
            "secondary": ["RAG (R&D Reports)", "Semantic Scholar"],
            "api_calls": [
                "world_bank.get_indicator('SE.TER.ENRR', 'QAT')",
                "mol_lmis.get_education_attainment_bachelors()",
            ],
        },
        "trade": {
            "primary": ["UN ESCWA", "UN Comtrade", "UNCTAD"],
            "secondary": ["World Bank", "IMF"],
            "api_calls": [
                "escwa.get_trade_data('QAT')",
                "world_bank.get_indicator('NE.EXP.GNFS.ZS', 'QAT')",
            ],
        },
        "health": {
            "primary": ["World Bank", "Qatar Open Data"],
            "secondary": ["Perplexity AI", "Semantic Scholar"],
            "api_calls": [
                "world_bank.get_indicator('SH.XPD.CHEX.GD.ZS', 'QAT')",
                "world_bank.get_indicator('SP.DYN.LE00.IN', 'QAT')",
            ],
        },
        "technology": {
            "primary": ["World Bank", "RAG (R&D Reports)"],
            "secondary": ["Semantic Scholar", "Perplexity AI"],
            "api_calls": [
                "world_bank.get_indicator('IT.NET.USER.ZS', 'QAT')",
                "rag.search('Qatar ICT landscape digital transformation')",
            ],
        },
        "agriculture": {
            "primary": ["FAO STAT", "World Bank"],
            "secondary": ["UN ESCWA", "Perplexity AI"],
            "api_calls": [
                "fao.get_food_production('QAT')",
                "world_bank.get_indicator('NV.AGR.TOTL.ZS', 'QAT')",
            ],
        },
        "infrastructure": {
            "primary": ["World Bank", "Qatar Open Data"],
            "secondary": ["Perplexity AI", "Brave Search"],
            "api_calls": [
                "world_bank.get_indicator('IS.ROD.PAVE.ZS', 'QAT')",
            ],
        },
        "environment": {
            "primary": ["World Bank", "IEA"],
            "secondary": ["Perplexity AI", "Semantic Scholar"],
            "api_calls": [
                "world_bank.get_indicator('EN.ATM.CO2E.PC', 'QAT')",
            ],
        },
        "demographics": {
            "primary": ["World Bank", "GCC-STAT"],
            "secondary": ["Qatar Open Data", "Arab Development Portal"],
            "api_calls": [
                "world_bank.get_indicator('SP.POP.TOTL', 'QAT')",
                "gcc_stat.get_population_statistics()",
            ],
        },
    }
    
    # Build result based on detected domains
    all_primary = set()
    all_secondary = set()
    all_api_calls = []
    
    for domain in result["detected_domains"]:
        if domain in domain_to_sources:
            info = domain_to_sources[domain]
            all_primary.update(info["primary"])
            all_secondary.update(info["secondary"])
            all_api_calls.extend(info["api_calls"])
    
    # Always include these universal sources
    all_secondary.add("Semantic Scholar (214M papers)")
    all_secondary.add("Perplexity AI (real-time)")
    all_secondary.add("Knowledge Graph")
    
    result["primary_sources"] = list(all_primary)
    result["secondary_sources"] = list(all_secondary)
    result["specific_api_calls"] = list(set(all_api_calls))
    
    # Generate RAG search terms
    result["rag_search_terms"] = [
        query[:50],
        f"Qatar {result['detected_domains'][0] if result['detected_domains'] else 'economy'}",
        "Vision 2030",
    ]
    
    # Generate knowledge graph queries
    result["knowledge_graph_queries"] = [
        f"Find relationships for: {', '.join(result['detected_domains'][:3])}",
        "Trace impact paths in Qatar economy",
    ]
    
    return result

