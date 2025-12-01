"""
Complete API Prefetch Layer - Uses ALL Available Data Sources
Integrates: MoL LMIS, GCC-STAT, World Bank, Semantic Scholar, Brave, Perplexity
"""
import asyncio
import os
import functools
from typing import Any, Awaitable, Callable, Dict, Iterable, List

from datetime import datetime
import aiohttp
import requests

# Load .env file for API keys
from dotenv import load_dotenv
load_dotenv()

from .data_quality import calculate_data_quality, identify_missing_data

import json
import logging
logger = logging.getLogger(__name__)

# =============================================================================
# LLM-BASED SMART QUERY GENERATION
# Generates contextual search queries for Semantic Scholar and Perplexity
# =============================================================================

SMART_QUERY_PROMPT = """You are a PhD researcher preparing to search academic databases. Given a user's question, generate search queries like a REAL RESEARCHER would.

USER QUESTION: {question}

THINK LIKE A RESEARCHER:
- DO NOT include specific country names (Qatar, UAE, etc.) in academic queries
- Search for the TOPIC/CONCEPT, not the geography
- Use academic terminology that yields the most papers
- The research findings will be APPLIED to the specific context later
- Broader queries = more relevant papers

Example: If question is "What skills should Qatar invest in for AI?"
- BAD query: "Qatar AI skills investment"  (too narrow, few results)
- GOOD query: "artificial intelligence workforce skills gap"  (broad, many results)
- GOOD query: "machine learning job market transformation"  (topic-focused)
- GOOD query: "digital skills future of work automation"  (conceptual)

RESPOND WITH VALID JSON:
{{
    "academic_queries": [
        "broad topic-focused academic query 1",
        "broad topic-focused academic query 2",
        "broad topic-focused academic query 3",
        "broad topic-focused academic query 4"
    ],
    "realtime_queries": [
        "specific real-time query with location for current data 1",
        "specific real-time query with location for current data 2"
    ],
    "key_concepts": ["concept1", "concept2", "concept3", "concept4", "concept5"],
    "data_needs": "brief description of what data would answer this question"
}}

CRITICAL FOR ACADEMIC QUERIES:
- Use 2-4 word phrases that academics use in paper titles
- NO country names, NO proper nouns
- Focus on phenomena, not places
- Think: what would a researcher title their paper?
"""

async def generate_smart_queries(question: str) -> Dict[str, Any]:
    """
    Use LLM to generate contextually relevant search queries.
    
    Instead of generic keyword matching, this creates smart queries
    based on understanding what the user actually wants to know.
    """
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    
    if not endpoint or not api_key:
        # Fallback to basic query extraction
        return {
            "academic_queries": [question[:100]],
            "realtime_queries": [question[:100]],
            "key_concepts": [],
            "data_needs": question
        }
    
    try:
        url = f"{endpoint}/openai/deployments/gpt-5-chat/chat/completions?api-version=2024-08-01-preview"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json={
                    "messages": [
                        {"role": "system", "content": "You are a research query optimizer. Always respond with valid JSON."},
                        {"role": "user", "content": SMART_QUERY_PROMPT.format(question=question)}
                    ],
                    "max_tokens": 400,
                    "temperature": 0.2
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Parse JSON
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    
                    result = json.loads(content.strip())
                    logger.info(f"🧠 Smart queries generated: {result.get('academic_queries', [])[:2]}")
                    return result
                    
    except Exception as e:
        logger.warning(f"⚠️ Smart query generation failed: {e}")
    
    # Fallback
    return {
        "academic_queries": [question[:100]],
        "realtime_queries": [question[:100]],
        "key_concepts": [],
        "data_needs": question
    }


# Safe printing helper to avoid UnicodeEncodeError on limited consoles
def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        sanitized = message.encode("ascii", errors="ignore").decode("ascii", errors="ignore")
        print(sanitized)

CRITICAL_DATA_CHECKLISTS = {
    "food_security": {
        "required": [
            "current_food_import_costs",
            "food_self_sufficiency_percentage",
            "agricultural_water_consumption",
            "energy_costs_for_agriculture",
        ],
        "nice_to_have": ["gcc_food_security_investments", "vertical_farming_costs"],
    },
    "labor_market": {
        "required": [
            "unemployment_rate",
            "labor_force_participation",
            "qatarization_rates",
            "sector_employment_distribution",
        ],
        "nice_to_have": ["wage_levels", "skills_gaps"],
    },
    "investment_decision": {
        "required": [
            "project_costs",
            "comparable_project_outcomes",
            "risk_factors",
            "economic_impact_estimates",
        ],
        "nice_to_have": ["financing_options", "public_opinion"],
    },
}

TARGETED_SEARCH_STRATEGIES = {
    "current_food_import_costs": [
        ("world_bank", "NE.IMP.GNFS.CD", {"country": "QAT"}),
        ("perplexity", "Qatar annual food import costs 2024", "cost_data"),
        ("brave_search", "Qatar food import statistics 2024 billion")
    ],
    "food_self_sufficiency_percentage": [
        ("qatar_open_data", "food production agriculture domestic"),
        ("perplexity", "Qatar food self-sufficiency rate percentage 2024", "statistics"),
        ("gcc_stat", "agriculture production value qatar")
    ],
    "energy_costs_for_agriculture": [
        ("world_bank", "EG.ELC.COST.KH", {"country": "QAT"}),
        ("perplexity", "Qatar electricity cost industrial agriculture 2024", "cost_data"),
        ("brave_search", "qatar energy subsidies agriculture sector")
    ],
    "agricultural_water_consumption": [
        ("world_bank", "ER.H2O.FWAG.ZS", {"country": "QAT"}),
        ("perplexity", "Qatar water consumption agriculture sector cubic meters", "statistics"),
        ("gcc_stat", "water consumption by sector qatar")
    ],
    "vertical_farming_costs": [
        ("perplexity", "vertical farming production cost per kilogram 2024", "cost_data"),
        ("semantic_scholar", "controlled environment agriculture economics cost analysis"),
        ("brave_search", "vertical farming energy costs middle east UAE")
    ],
    "gcc_food_security_investments": [
        ("gcc_stat", "agriculture investment government spending"),
        ("perplexity", "GCC countries food security investment 2024 Saudi UAE", "comparative"),
        ("brave_search", "GCC food security megaprojects 2024")
    ]
}

PERPLEXITY_PROMPT_TEMPLATES = {
    "cost_data": """Find the most recent, specific cost data for: {query}
REQUIRED FORMAT:
- Exact figures with currency (USD, QAR, etc.)
- Time period (year/quarter/month)
- Authoritative source citation (World Bank, government, industry report)
CRITICAL: If specific data not available, respond "No specific data found" rather than estimating.
Do NOT provide approximate figures without clear source attribution.""",
    
    "statistics": """Find official statistics for: {query}
REQUIRED FORMAT:
- Exact numbers/percentages with precision
- Official source (government statistics, World Bank, IMF, UN, GCC-STAT)
- Year/period of data
- Methodology if available
PRIORITIZE: Government statistics > International organizations > Peer-reviewed research > Industry reports > News""",
    
    "comparative": """Find comparative data for: {query}
REQUIRED FORMAT:
- Multiple countries/entities with SAME METRICS
- Same time period for fair comparison
- Clear data sources for each entity
- Note any methodology differences
If not directly comparable, explain why and what adjustments would be needed."""
}

def classify_query_for_extraction(query: str) -> List[str]:
    """Determine what types of data we need"""
    query_lower = query.lower()
    
    query_types = []
    
    # Food security keywords
    if any(kw in query_lower for kw in ["food", "agriculture", "farming", "self-sufficiency"]):
        query_types.append("food_security")
    
    # Labor market keywords
    if any(kw in query_lower for kw in ["employment", "labor", "workforce", "qatarization"]):
        query_types.append("labor_market")
    
    # Investment decision keywords
    if any(kw in query_lower for kw in ["invest", "project", "megaproject", "should we"]):
        query_types.append("investment_decision")
    
    return query_types if query_types else ["general"]

# Import your existing API clients (with fallbacks for legacy class names)
try:
    from src.data.apis.gcc_stat import GCCStatAPI  # type: ignore
except ImportError:  # pragma: no cover - legacy fallback
    from src.data.apis.gcc_stat import GCCStatClient

    class GCCStatAPI(GCCStatClient):
        async def get_gcc_unemployment_rates(self, *args, **kwargs):
            return await asyncio.to_thread(
                self.get_unemployment_comparison,
                *args,
                **kwargs,
            )

try:
    from src.data.apis.world_bank import WorldBankAPI  # type: ignore
except ImportError:  # pragma: no cover - legacy fallback
    from src.data.apis.world_bank import UDCGlobalDataIntegrator

    class WorldBankAPI(UDCGlobalDataIntegrator):
        async def get_indicator(self, *, indicator: str, country: str, **kwargs):
            call = functools.partial(
                super().get_indicator,
                indicator,
                countries=[country],
                **kwargs,
            )
            return await asyncio.to_thread(call)

try:
    from src.data.apis.semantic_scholar import SemanticScholarAPI  # type: ignore
except ImportError:  # pragma: no cover - legacy fallback
    from src.data.apis import semantic_scholar as _semantic_scholar_module

    class SemanticScholarAPIMixin:
        async def search_papers(
            self,
            query: str,
            fields: str | None = None,
            year_filter: str | None = None,
            limit: int = 10,
        ) -> List[Dict[str, Any]]:
            effective_fields = fields or "title,year,abstract,citationCount,authors,url,paperId"
            _safe_print(
                f"🔍 Semantic Scholar: Searching papers with query '{query}' and limit {limit}..."
            )
            return await asyncio.to_thread(
                _semantic_scholar_module.search_papers,
                query,
                effective_fields,
                year_filter,
                limit,
            )

    class SemanticScholarAPI(SemanticScholarAPIMixin):
        pass

try:
    from src.data.apis.qatar_opendata import QatarOpenDataScraperV2 # type: ignore
except ImportError:
    class QatarOpenDataScraperV2:
        def search_catalog(self, *args, **kwargs):
            return []

class QatarOpenDataAPI(QatarOpenDataScraperV2):
    async def search_datasets(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Asynchronous wrapper around the synchronous catalog API."""
        query_lower = query.lower()

        def _search() -> List[Dict[str, Any]]:
            datasets = self.get_all_datasets(limit=limit, max_results=limit * 2)
            matches: list[dict[str, Any]] = []
            for dataset in datasets:
                default_meta = dataset.get("metas", {}).get("default", {})
                haystack = f"{default_meta.get('title', '')} {default_meta.get('description', '')}".lower()
                if query_lower in haystack:
                    matches.append(dataset)
                if len(matches) >= limit:
                    break
            return matches

        return await asyncio.to_thread(_search)

    async def simple_search(self, query: str) -> List[Dict[str, Any]]:
        """Return lightweight facts for UI display when Qatar Open Data is used."""
        _safe_print(f"Qatar Open Data: searching for '{query}'")
        datasets = await self.search_datasets(query, limit=5)
        facts: list[dict[str, Any]] = []
        for dataset in datasets:
            meta = dataset.get("metas", {}).get("default", {})
            facts.append(
                {
                    "metric": meta.get("title", dataset.get("dataset_id", "dataset")),
                    "value": (meta.get("description") or "")[:200],
                    "source": "Qatar Open Data",
                    "data_type": "open_data",
                    "confidence": 0.65,
                }
            )
        return facts



class CompletePrefetchLayer:
    """Prefetch data from ALL available sources for agent analysis."""
    
    def __init__(self):
        # Initialize API clients
        self.gcc_stat = GCCStatAPI()
        self.semantic_scholar = SemanticScholarAPI()
        self.qatar_open_data = QatarOpenDataAPI()
        
        # IMF API Connector
        try:
            from src.data.apis.imf_api import IMFConnector
        except ImportError:
            IMFConnector = None  # type: ignore

        # UN Comtrade API Connector
        try:
            from src.data.apis.un_comtrade_api import UNComtradeConnector
        except ImportError:
            UNComtradeConnector = None  # type: ignore

        # FRED API Connector
        try:
            from src.data.apis.fred_api import FREDConnector
        except ImportError:
            FREDConnector = None  # type: ignore
        
        # PHASE 1 APIs (Critical Foundation)
        # World Bank API Connector (FILLS 60% OF GAPS)
        try:
            from src.data.apis.world_bank_api import WorldBankAPI as WorldBankAPIClass
        except ImportError:
            WorldBankAPIClass = None  # type: ignore
        
        # UNCTAD API Connector (Investment Climate)
        try:
            from src.data.apis.unctad_api import UNCTADAPI
        except ImportError:
            UNCTADAPI = None  # type: ignore
        
        # ILO ILOSTAT API Connector (International Labor Benchmarks)
        try:
            from src.data.apis.ilo_api import ILOAPI
        except ImportError:
            ILOAPI = None  # type: ignore
        
        # PHASE 2 APIs (Specialized Depth)
        # FAO STAT API Connector (Food Security & Agriculture)
        try:
            from src.data.apis.fao_api import FAOAPI
        except ImportError:
            FAOAPI = None  # type: ignore
        
        # UNWTO Tourism API Connector (Tourism Sector)
        try:
            from src.data.apis.unwto_api import UNWTOAPI
        except ImportError:
            UNWTOAPI = None  # type: ignore
        
        # IEA Energy API Connector (Energy Sector & Transition)
        try:
            from src.data.apis.iea_api import IEAAPI
        except ImportError:
            IEAAPI = None  # type: ignore
        
        # PHASE 3 APIs (Regional Depth)
        # Arab Development Portal API Connector (179K+ datasets)
        try:
            from src.data.apis.arab_dev_portal import ArabDevPortalClient
        except ImportError:
            ArabDevPortalClient = None  # type: ignore
        
        # ESCWA Trade Data Platform API Connector
        try:
            from src.data.apis.escwa_etdp import ESCWATradeAPI
        except ImportError:
            ESCWATradeAPI = None  # type: ignore
        
        # PHASE 4: LMIS - Ministry of Labour Qatar (OFFICIAL AUTHORITATIVE DATA)
        try:
            from src.data.apis.lmis_mol_api import LMISAPIClient
            self.lmis_connector = LMISAPIClient()
        except ImportError:
            LMISAPIClient = None  # type: ignore
            self.lmis_connector = None
        
        # Knowledge Graph for cross-domain reasoning
        try:
            from ..knowledge.graph_builder import QNWISKnowledgeGraph
            from pathlib import Path
            kg_path = Path("data/knowledge_graph.json")
            if kg_path.exists():
                self._knowledge_graph = QNWISKnowledgeGraph()
                self._knowledge_graph.load(kg_path)
                _safe_print("Knowledge Graph: Loaded successfully")
            else:
                self._knowledge_graph = None
        except ImportError:
            QNWISKnowledgeGraph = None  # type: ignore
            self._knowledge_graph = None
        
        # Initialize all connectors
        self.imf_connector = IMFConnector() if IMFConnector else None
        # DISABLED: UN Comtrade requires auth and blocks workflow with 35s waits
        self.un_comtrade_connector = None  # UNComtradeConnector() if UNComtradeConnector else None
        # DISABLED: FRED API also disabled to speed up workflow
        self.fred_connector = None  # FREDConnector() if FREDConnector else None
        
        # Phase 1 connectors
        self.world_bank_connector = WorldBankAPIClass() if WorldBankAPIClass else None
        self.unctad_connector = UNCTADAPI() if UNCTADAPI else None
        self.ilo_connector = ILOAPI() if ILOAPI else None
        
        # Phase 2 connectors
        self.fao_connector = FAOAPI() if FAOAPI else None
        self.unwto_connector = UNWTOAPI() if UNWTOAPI else None
        self.iea_connector = IEAAPI() if IEAAPI else None
        
        # Phase 3 connectors (Regional Depth)
        self.adp_connector = ArabDevPortalClient() if ArabDevPortalClient else None
        self.escwa_connector = ESCWATradeAPI() if ESCWATradeAPI else None
        
        # Legacy reference for backward compatibility
        self.world_bank = self.world_bank_connector
        
        # Get API keys from environment
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        
        # Display API status
        _safe_print(f"🔑 Brave API: {'✅' if self.brave_api_key else '❌'}")
        _safe_print(f"🔑 Perplexity API: {'✅' if self.perplexity_api_key else '❌'}")
        _safe_print(f"🔑 Semantic Scholar API: {'✅' if self.semantic_scholar else '❌'}")
        
        # Original APIs
        _safe_print(f"🔑 IMF API: {'✅' if self.imf_connector else '❌'}")
        _safe_print(f"🔑 UN Comtrade API: {'✅' if self.un_comtrade_connector else '❌'}")
        _safe_print(f"🔑 FRED API: {'✅' if self.fred_connector else '❌'}")
        
        # Phase 1 APIs (Critical Foundation)
        _safe_print(f"🔑 World Bank API: {'✅' if self.world_bank_connector else '❌'}")
        _safe_print(f"🔑 UNCTAD API: {'✅' if self.unctad_connector else '❌'}")
        _safe_print(f"🔑 ILO ILOSTAT API: {'✅' if self.ilo_connector else '❌'}")
        
        # Phase 2 APIs (Specialized Depth)
        _safe_print(f"🔑 FAO STAT API: {'✅' if self.fao_connector else '❌'}")
        _safe_print(f"🔑 UNWTO Tourism API: {'✅' if self.unwto_connector else '❌'}")
        _safe_print(f"🔑 IEA Energy API: {'✅' if self.iea_connector else '❌'}")
        
        # Phase 3 APIs (Regional Depth)
        _safe_print(f"🔑 Arab Dev Portal API: {'✅' if self.adp_connector else '❌'}")
        _safe_print(f"🔑 ESCWA Trade API: {'✅' if self.escwa_connector else '❌'}")
        
        # Phase 4: LMIS (Official Government Data)
        _safe_print(f"🏛️ LMIS MoL API: {'✅' if self.lmis_connector else '❌'}")
        _safe_print(f"🧠 Knowledge Graph: {'✅' if self._knowledge_graph else '❌'}")
        
        # Add PostgreSQL writer for caching
        from ..data.deterministic.engine import get_engine
        self.pg_engine = get_engine()
        _safe_print(f"🔑 PostgreSQL: {'✅'}")
    
    async def fetch_all_sources(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch from ALL sources in parallel based on query keywords.
        Returns comprehensive fact list for agent analysis.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # CRITICAL DEBUG: Log the FULL query to understand what's happening
        logger.warning(f"FETCH_ALL_SOURCES QUERY LENGTH: {len(query)}")
        logger.warning(f"FETCH_ALL_SOURCES QUERY FIRST 200 CHARS: {repr(query[:200])}")
        
        facts: List[Dict[str, Any]] = []
        query_lower = query.lower()
        tasks: List[Callable[[], Awaitable[List[Dict[str, Any]]]]] = []
        added_methods: set[str] = set()

        def add_task(factory: Callable[[], Awaitable[List[Dict[str, Any]]]], name: str) -> None:
            """Add coroutine factory if not already scheduled."""
            if name not in added_methods:
                tasks.append(factory)
                added_methods.add(name)
                logger.info(f"📌 Added task: {name}")

        # ========================================================================
        # TIER 1 FREE API TRIGGERS (IMF, UN Comtrade, FRED)
        # ========================================================================
        
        # IMF API Triggers (economic indicators)
        if any(
            keyword in query_lower
            for keyword in [
                "gdp", "economic growth", "fiscal", "government debt",
                "inflation", "unemployment", "current account", "deficit",
                "revenue", "expenditure", "debt", "balance"
            ]
        ):
            _safe_print("🌍 Triggering: IMF API (economic indicators)")
            add_task(self._fetch_imf_dashboard, "imf_dashboard")
        
        # UN Comtrade API Triggers (trade/food imports)
        if any(
            keyword in query_lower
            for keyword in [
                "food", "import", "trade", "self-sufficiency", "agriculture",
                "meat", "dairy", "vegetables", "cereals", "commodity", "farming"
            ]
        ):
            _safe_print("🌍 Triggering: UN Comtrade API (food imports)")
            add_task(self._fetch_comtrade_food, "comtrade_food")
        
        # FRED API Triggers (US economic benchmarks)
        if any(
            keyword in query_lower
            for keyword in [
                "united states", "usa", "us ", "american", "federal reserve",
                "compare", "benchmark", "global", "international"
            ]
        ):
            _safe_print("🇺🇸 Triggering: FRED API (US economic data)")
            add_task(self._fetch_fred_benchmarks, "fred_benchmarks")
        
        # World Bank API Triggers (PHASE 1 - HIGH PRIORITY)
        # ENHANCED: Added manufacturing, infrastructure, energy, and food keywords
        logger.info(f"🔍 Checking World Bank triggers for query: '{query_lower[:80]}...'")
        world_bank_keywords = [
                "sector", "tourism", "manufacturing", "services", "industry",]
        matching_keywords = [kw for kw in world_bank_keywords if kw in query_lower]
        logger.info(f"🔍 Matching World Bank keywords: {matching_keywords}")
        if any(
            keyword in query_lower
            for keyword in [
                "sector", "tourism", "manufacturing", "services", "industry",
                "infrastructure", "education", "health", "digital",
                "internet", "roads", "human capital", "enrollment",
                "life expectancy", "savings", "investment climate",
                # Manufacturing additions
                "industrial", "factory", "production", "competitiveness",
                "export", "value-add", "value added", "industrial zone",
                "plant", "processing", "assembly",
                # Infrastructure additions
                "metro", "transport", "railway", "rail", "highway",
                "port", "airport", "construction", "public works",
                "utilities", "water", "electricity", "telecom", "logistics",
                "connectivity", "broadband",
                # Energy additions (to get full dashboard + targeted subset)
                "energy", "renewable", "solar", "power", "oil", "gas",
                "lng", "petroleum", "emission", "carbon", "fossil",
                # Food/agriculture additions (to get full dashboard + targeted subset)
                "food", "agriculture", "farming", "self-sufficiency",
                "agricultural", "food security", "import dependency"
            ]
        ):
            _safe_print("🌍 Triggering: World Bank API (comprehensive 128-indicator dashboard)")
            add_task(self._fetch_world_bank_dashboard, "world_bank_dashboard")
        
        # UNCTAD Investment/FDI Triggers (PHASE 1)
        if any(
            keyword in query_lower
            for keyword in [
                "investment", "fdi", "foreign direct", "capital flows",
                "portfolio", "inflows", "outflows", "investor"
            ]
        ):
            _safe_print("💰 Triggering: UNCTAD API (investment climate, FDI)")
            add_task(self._fetch_unctad_investment, "unctad_investment")
        
        # ILO International Labor Benchmarks Triggers (PHASE 1)
        if any(
            keyword in query_lower
            for keyword in [
                "international", "benchmark", "gcc comparison", "global",
                "regional", "wage comparison", "labor standards"
            ]
        ):
            _safe_print("🌍 Triggering: ILO ILOSTAT API (international labor benchmarks)")
            add_task(self._fetch_ilo_benchmarks, "ilo_benchmarks")
        
        # LMIS Ministry of Labour Triggers (PHASE 4 - OFFICIAL GOVERNMENT DATA)
        if any(
            keyword in query_lower
            for keyword in [
                "labor", "labour", "employment", "workforce", "worker",
                "qatarization", "qatari", "expat", "expatriate", "skills",
                "occupation", "sector", "salary", "wage", "sme", "business",
                "nationalization", "job", "career", "training", "education",
                "human capital", "talent", "recruitment", "hiring",
                "qatar", "ministry", "mol"
            ]
        ):
            _safe_print("🏛️ Triggering: LMIS MoL API (official Qatar labor market data)")
            add_task(self._fetch_lmis_comprehensive, "lmis_comprehensive")
        
        # FAO Food Security Triggers (PHASE 2)
        # ENHANCED: Added Perplexity real-time data with citations
        if any(
            keyword in query_lower
            for keyword in [
                "food", "agriculture", "farming", "self-sufficiency",
                "imports", "crops", "agricultural", "food security"
            ]
        ):
            _safe_print("🌾 Triggering: FAO STAT API (food security, agriculture)")
            add_task(self._fetch_fao_food_security, "fao_food_security")
            if self.perplexity_api_key:
                _safe_print("🤖 Triggering: Perplexity AI (food security with citations)")
                add_task(lambda: self._fetch_perplexity_food_security(query), "perplexity_food_security")
        
        # UNWTO Tourism Triggers (PHASE 2)
        if any(
            keyword in query_lower
            for keyword in [
                "tourism", "tourist", "visitors", "hotels", "hospitality",
                "accommodation", "travel", "arrivals"
            ]
        ):
            _safe_print("✈️  Triggering: UNWTO API (tourism statistics)")
            add_task(self._fetch_unwto_tourism, "unwto_tourism")
        
        # IEA Energy Triggers (PHASE 2)
        # ENHANCED: Added oil, gas, and more energy keywords + Perplexity real-time data
        if any(
            keyword in query_lower
            for keyword in [
                "energy", "renewable", "solar", "power", "electricity",
                "transition", "wind", "clean energy", "carbon",
                # Oil & gas additions
                "oil", "gas", "lng", "natural gas", "petroleum", "hydrocarbon",
                "fossil fuel", "crude", "refinery", "emission", "co2"
            ]
        ):
            _safe_print("⚡ Triggering: IEA API (energy sector, transition)")
            add_task(self._fetch_iea_energy, "iea_energy")
            if self.perplexity_api_key:
                _safe_print("🤖 Triggering: Perplexity AI (energy sector with citations)")
                add_task(lambda: self._fetch_perplexity_energy(query), "perplexity_energy")
        
        # ========================================================================
        # EXISTING SOURCE TRIGGERS
        # ========================================================================
        
        # Labor market triggers (MoL stub, GCC-STAT, Semantic Scholar)
        if any(
            word in query_lower
            for word in [
                "unemployment",
                "employment",
                "labor",
                "labour",
                "workforce",
                "qatarization",
                "qatarisation",
                "nationalization",
                "nationalisation",
                "jobs",
                "workers",
                "employees",
                "staff",
                "personnel",
                "qatari",
                "nationals",
                "citizens",
                "expat",
                "expatriate",
                "tech",
                "technology",
                "sector",
                "industry",
                "mandate",
                "policy",
                "reform",
                "target",
            ]
        ):
            _safe_print("🎯 Triggering: Labor market sources (MoL, GCC-STAT, Semantic Scholar)")
            add_task(self._fetch_mol_data, "mol_data")
            add_task(self._fetch_gcc_stat, "gcc_stat")
            add_task(lambda: self._fetch_semantic_scholar_labor(query), "semantic_labor")

        # Economic / GDP triggers (World Bank, Brave)
        if any(
            word in query_lower
            for word in [
                "economic",
                "economy",
                "gdp",
                "growth",
                "investment",
                "sector",
                "industry",
                "business",
                "market",
                "development",
                "finance",
                "financial",
            ]
        ):
            _safe_print("🎯 Triggering: Economic sources (World Bank, Brave)")
            add_task(self._fetch_world_bank, "world_bank")
            if self.brave_api_key:
                add_task(lambda: self._fetch_brave_economic(query), "brave_economic")

        # Regional / GCC triggers (GCC-STAT, Perplexity)
        if any(
            word in query_lower
            for word in [
                "gcc",
                "gulf",
                "regional",
                "region",
                "saudi",
                "uae",
                "bahrain",
                "kuwait",
                "oman",
                "emirates",
                "compare",
                "comparison",
                "benchmark",
                "versus",
                "qatari",
                "qatar",
            ]
        ):
            _safe_print("🎯 Triggering: Regional sources (GCC-STAT, Perplexity)")
            add_task(self._fetch_gcc_stat, "gcc_stat")
            if self.perplexity_api_key:
                add_task(lambda: self._fetch_perplexity_gcc(query), "perplexity_gcc")

        # Policy / strategy triggers (Semantic Scholar, Perplexity)
        if any(
            word in query_lower
            for word in [
                "policy",
                "policies",
                "strategy",
                "strategic",
                "mandate",
                "mandating",
                "require",
                "requirement",
                "reform",
                "reforms",
                "regulation",
                "law",
                "vision",
                "2030",
                "plan",
                "planning",
                "implement",
                "implementation",
                "feasibility",
                "target",
                "goal",
                "objective",
            ]
        ):
            _safe_print("🎯 Triggering: Policy sources (Semantic Scholar, Perplexity)")
            add_task(lambda: self._fetch_semantic_scholar_policy(query), "semantic_policy")
            if self.perplexity_api_key:
                add_task(lambda: self._fetch_perplexity_policy(query), "perplexity_policy")

        # Trade / Commerce triggers (ESCWA Trade Data)
        if any(
            word in query_lower
            for word in [
                "trade",
                "export",
                "import",
                "commerce",
                "tariff",
                "customs",
                "goods",
                "commodity",
                "shipping",
                "logistics",
                "supply chain",
                "bilateral",
            ]
        ):
            if self.escwa_connector:
                _safe_print("🎯 Triggering: Trade sources (ESCWA Trade Data)")
                add_task(lambda: self._fetch_escwa_trade(query), "escwa_trade")

        # Arab World / Regional triggers (Arab Development Portal)
        if any(
            word in query_lower
            for word in [
                "arab",
                "mena",
                "middle east",
                "regional",
                "gcc",
                "gulf",
                "hdi",
                "sdg",
                "development",
                "benchmark",
            ]
        ):
            if self.adp_connector:
                _safe_print("🎯 Triggering: Arab Development Portal")
                # Determine domain from query
                adp_domain = "labor"
                if any(w in query_lower for w in ["trade", "export", "import"]):
                    adp_domain = "trade"
                elif any(w in query_lower for w in ["health", "medical", "hospital"]):
                    adp_domain = "health"
                elif any(w in query_lower for w in ["education", "school", "university"]):
                    adp_domain = "education"
                elif any(w in query_lower for w in ["energy", "oil", "gas", "power"]):
                    adp_domain = "energy"
                elif any(w in query_lower for w in ["tourism", "travel", "hotel"]):
                    adp_domain = "tourism"
                add_task(lambda d=adp_domain: self._fetch_adp_data(query, d), f"adp_{adp_domain}")

        # Knowledge Graph triggers (cross-domain reasoning)
        if self._knowledge_graph and any(
            word in query_lower
            for word in [
                "impact",
                "affect",
                "relationship",
                "connection",
                "cause",
                "effect",
                "consequence",
                "lead to",
                "result in",
                "depend",
                "influence",
                "sector",
                "cross",
                "multi",
            ]
        ):
            _safe_print("🧠 Triggering: Knowledge Graph (cross-domain reasoning)")
            add_task(lambda: self._fetch_knowledge_graph_context(query), "knowledge_graph")

        # ========================================================================
        # SMART CONTEXT-AWARE FETCHING (Always triggered for any question)
        # Uses LLM to generate contextually relevant queries
        # ========================================================================
        _safe_print("\n🧠 Triggering: Smart context-aware Semantic Scholar & Perplexity")
        add_task(lambda: self._fetch_semantic_scholar_smart(query), "semantic_smart")
        if self.perplexity_api_key:
            add_task(lambda: self._fetch_perplexity_smart(query), "perplexity_smart")

        if tasks:
            _safe_print(f"\n🚀 Executing {len(tasks)} unique parallel API calls...")
            coros = [factory() for factory in tasks]
            results = await asyncio.gather(*coros, return_exceptions=True)

            for result in results:
                if isinstance(result, list) and not isinstance(result, Exception):
                    facts.extend(result)
                elif isinstance(result, Exception):
                    _safe_print(f"⚠️  Task failed with exception: {result}")

        _safe_print(f"\n📊 Total facts extracted: {len(facts)}")
        return facts
    
    # ================== MoL LMIS (REAL DATA FROM POSTGRESQL) ==================
    
    async def _fetch_mol_data(self) -> List[Dict[str, Any]]:
        """
        Fetch REAL Qatar labor market data from PostgreSQL cache.
        
        NO STUBS. NO FAKES. NO PLACEHOLDERS.
        Returns only verified data from World Bank/ILO/GCC-STAT cached in PostgreSQL.
        """
        _safe_print("📊 MoL Data: Fetching verified data from PostgreSQL...")
        
        facts = []
        try:
            from sqlalchemy import text
            
            with self.pg_engine.begin() as conn:
                # Get Qatar unemployment from World Bank (REAL DATA)
                result = conn.execute(text("""
                    SELECT value, year FROM world_bank_indicators 
                    WHERE country_code = 'QAT' 
                    AND indicator_code = 'SL.UEM.TOTL.ZS'
                    ORDER BY year DESC LIMIT 1
                """)).fetchone()
                
                if result:
                    facts.append({
                        "metric": "qatar_unemployment_rate",
                        "value": float(result[0]),
                        "year": result[1],
                        "source": "World Bank (PostgreSQL cache)",
                        "source_priority": 98,
                        "confidence": 0.99,
                        "raw_text": f"Qatar unemployment: {result[0]}% ({result[1]})",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Get labor force participation (REAL DATA)
                result = conn.execute(text("""
                    SELECT value, year FROM world_bank_indicators 
                    WHERE country_code = 'QAT' 
                    AND indicator_code = 'SL.TLF.CACT.ZS'
                    ORDER BY year DESC LIMIT 1
                """)).fetchone()
                
                if result:
                    facts.append({
                        "metric": "qatar_labour_force_participation",
                        "value": float(result[0]),
                        "year": result[1],
                        "source": "World Bank (PostgreSQL cache)",
                        "source_priority": 98,
                        "confidence": 0.99,
                        "raw_text": f"Labour force participation: {result[0]}% ({result[1]})",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Get GDP data (REAL DATA)
                result = conn.execute(text("""
                    SELECT value, year FROM world_bank_indicators 
                    WHERE country_code = 'QAT' 
                    AND indicator_code = 'NY.GDP.MKTP.CD'
                    ORDER BY year DESC LIMIT 1
                """)).fetchone()
                
                if result:
                    gdp_billions = float(result[0]) / 1e9
                    facts.append({
                        "metric": "qatar_gdp_usd",
                        "value": gdp_billions,
                        "year": result[1],
                        "source": "World Bank (PostgreSQL cache)",
                        "source_priority": 98,
                        "confidence": 0.99,
                        "raw_text": f"Qatar GDP: ${gdp_billions:.1f}B ({result[1]})",
                        "timestamp": datetime.now().isoformat()
                    })
                
            _safe_print(f"   Retrieved {len(facts)} verified facts from PostgreSQL")
            
        except Exception as e:
            _safe_print(f"❌ PostgreSQL fetch error: {e}")
        
        return facts
    
    # ================== GCC-STAT (WORKING) ==================
    
    async def _fetch_gcc_stat(self) -> List[Dict[str, Any]]:
        """Fetch from GCC-STAT (CONFIRMED WORKING)."""
        try:
            _safe_print("✅ GCC-STAT: Fetching live data...")
            df = await self.gcc_stat.get_gcc_unemployment_rates()
            
            facts = []
            for _, row in df.iterrows():
                country_slug = row['country'].lower().replace(' ', '_')
                
                facts.append({
                    "metric": f"{country_slug}_unemployment_rate",
                    "value": row['unemployment_rate'],
                    "source": "GCC-STAT (live API)",
                    "source_priority": 95,
                    "confidence": 0.95,
                    "raw_text": f"{row['country']} unemployment: {row['unemployment_rate']}%",
                    "timestamp": datetime.now().isoformat()
                })
                
                facts.append({
                    "metric": f"{country_slug}_labour_force_participation",
                    "value": row['labor_force_participation'],
                    "source": "GCC-STAT (live API)",
                    "source_priority": 95,
                    "confidence": 0.95,
                    "raw_text": f"{row['country']} LFPR: {row['labor_force_participation']}%",
                    "timestamp": datetime.now().isoformat()
                })
            
            _safe_print(f"   Retrieved {len(facts)} facts from GCC-STAT")
            return facts
            
        except Exception as e:
            _safe_print(f"❌ GCC-STAT error: {e}")
            return []
    
    # ================== World Bank (WORKING) ==================
    
    async def _fetch_world_bank(self) -> List[Dict[str, Any]]:
        """Fetch from World Bank - DEPRECATED, use _fetch_world_bank_dashboard instead."""
        # This method is legacy - the new dashboard method is cache-first and comprehensive
        if not self.world_bank_connector:
            return []
        
        try:
            _safe_print("✅ World Bank: Fetching Qatar GDP (legacy method)...")
            data = await self.world_bank_connector.get_indicator(
                indicator_code="NY.GDP.MKTP.CD",
                country_code="QAT"
            )
            
            if "latest_value" in data and data["latest_value"]:
                return [{
                    "metric": "qatar_gdp",
                    "value": data["latest_value"],
                    "year": data.get("latest_year"),
                    "source": "World Bank (live API)",
                    "source_priority": 95,
                    "confidence": 0.98,
                    "raw_text": f"Qatar GDP: ${data['latest_value']:,.0f} ({data.get('latest_year', 'N/A')})",
                    "timestamp": datetime.now().isoformat()
                }]
            
            return []
            
        except Exception as e:
            _safe_print(f"❌ World Bank error: {e}")
            return []
    
    # ================== Semantic Scholar ==================
    
    async def _fetch_semantic_scholar_labor(self, query: str) -> List[Dict[str, Any]]:
        """Fetch labor market research using recommendations API + broad search."""
        try:
            _safe_print("🔍 Semantic Scholar: Fetching labor market research...")
            api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
            headers = {"x-api-key": api_key} if api_key else {}

            # Strategy 1: Recommendations API with seed paper
            seed_paper_id = "649def34f8be52c8b66281af98ae884c09aef38b"

            try:
                url = f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{seed_paper_id}"
                params = {
                    "fields": "title,year,abstract,url,citationCount",
                    "limit": "20",
                    "from": "recent",
                }

                _safe_print("   Strategy 1: Recommendations API...")
                response = await asyncio.to_thread(
                    lambda: requests.get(url, params=params, headers=headers, timeout=10)
                )

                if response.status_code == 200:
                    data = response.json()
                    papers = data.get("recommendedPapers", [])
                    _safe_print(f"   Recommendations returned {len(papers)} papers")

                    keywords = [
                        "labor",
                        "labour",
                        "employment",
                        "workforce",
                        "worker",
                        "nationalization",
                        "localization",
                        "qatarization",
                        "gcc",
                        "qatar",
                        "expat",
                        "migration",
                        "talent",
                        "skill",
                        "job",
                        "hiring",
                        "recruitment",
                        "training",
                        "education",
                    ]

                    filtered: List[Dict[str, Any]] = []
                    for paper in papers:
                        title = paper.get("title", "").lower()
                        abstract = str(paper.get("abstract", "")).lower()
                        if any(kw in title or kw in abstract for kw in keywords):
                            filtered.append(paper)

                    _safe_print(f"   Filtered to {len(filtered)} labor-related papers")

                    if filtered:
                        facts: List[Dict[str, Any]] = []
                        # Use TOP 10 papers instead of 3 for ministerial-grade depth
                        for paper in filtered[:10]:
                            facts.append(
                                {
                                    "metric": "research_finding",
                                    "value": paper.get("title", ""),
                                    "source": f"Semantic Scholar ({paper.get('year', 'N/A')})",
                                    "source_priority": 75,
                                    "confidence": 0.75,
                                    "raw_text": (
                                        f"Research: {paper.get('title')} | Citations: {paper.get('citationCount', 0)} | "
                                        f"{str(paper.get('abstract', ''))[:150]}"
                                    ),
                                    "timestamp": datetime.now().isoformat(),
                                    "url": paper.get("url", ""),
                                }
                            )

                        _safe_print(f"   ✅ Success! Found {len(facts)} papers via Recommendations")
                        await asyncio.sleep(1)  # Respect 1/second rate limit
                        return facts
                else:
                    _safe_print(f"   Recommendations API: HTTP {response.status_code}")

            except Exception as rec_error:
                _safe_print(f"   Recommendations error: {rec_error}")

            # Strategy 2: Broad search queries
            _safe_print("   Strategy 2: Broad search fallback...")
            search_queries = [
                "workforce development",
                "employment policy",
                "labor economics",
                "talent management",
                "human capital",
            ]

            for search_query in search_queries:
                try:
                    url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
                    params = {
                        "query": search_query,
                        "fields": "title,year,abstract,url",
                        "year": "2015-",
                        "limit": "10",
                    }

                    _safe_print(f"   Searching: '{search_query}'")
                    response = await asyncio.to_thread(
                        lambda: requests.get(url, params=params, headers=headers, timeout=10)
                    )

                    if response.status_code == 200:
                        data = response.json()
                        papers = data.get("data", [])
                        _safe_print(f"   Query '{search_query}': {len(papers)} results")

                        if papers:
                            facts = []
                            for paper in papers[:3]:
                                facts.append(
                                    {
                                        "metric": "research_finding",
                                        "value": paper.get("title", ""),
                                        "source": f"Semantic Scholar ({paper.get('year', 'N/A')})",
                                        "source_priority": 75,
                                        "confidence": 0.70,
                                        "raw_text": f"Research: {paper.get('title')}",
                                        "timestamp": datetime.now().isoformat(),
                                        "url": paper.get("url", ""),
                                    }
                                )

                            _safe_print(f"   ✅ Success! Found {len(facts)} papers")
                            await asyncio.sleep(1)
                            return facts
                    else:
                        _safe_print(f"   Search '{search_query}': HTTP {response.status_code}")

                except Exception as search_error:
                    _safe_print(f"   Search '{search_query}' error: {search_error}")
                    continue

            _safe_print("   ⚠️  All strategies exhausted, no papers found")
            return []

        except Exception as e:
            _safe_print(f"⚠️  Semantic Scholar labor error: {e}")
            import traceback

            traceback.print_exc()
            return []

    async def _fetch_semantic_scholar_policy(self, query: str) -> List[Dict[str, Any]]:
        """Fetch policy research using recommendations API + broad search."""
        try:
            _safe_print("🔍 Semantic Scholar: Fetching policy research...")
            api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
            headers = {"x-api-key": api_key} if api_key else {}

            seed_paper_id = "649def34f8be52c8b66281af98ae884c09aef38b"

            try:
                url = f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{seed_paper_id}"
                params = {
                    "fields": "title,year,abstract,url,citationCount",
                    "limit": "20",
                    "from": "recent",
                }

                _safe_print("   Strategy 1: Recommendations API...")
                response = await asyncio.to_thread(
                    lambda: requests.get(url, params=params, headers=headers, timeout=10)
                )

                if response.status_code == 200:
                    data = response.json()
                    papers = data.get("recommendedPapers", [])
                    _safe_print(f"   Recommendations returned {len(papers)} papers")

                    keywords = [
                        "policy",
                        "regulation",
                        "government",
                        "legislation",
                        "reform",
                        "strategy",
                        "initiative",
                        "program",
                        "framework",
                        "implementation",
                        "compliance",
                        "mandate",
                        "requirement",
                    ]

                    filtered: List[Dict[str, Any]] = []
                    for paper in papers:
                        title = paper.get("title", "").lower()
                        abstract = str(paper.get("abstract", "")).lower()
                        if any(kw in title or kw in abstract for kw in keywords):
                            filtered.append(paper)

                    _safe_print(f"   Filtered to {len(filtered)} policy papers")

                    if filtered:
                        facts: List[Dict[str, Any]] = []
                        # Use TOP 10 papers instead of 3 for ministerial-grade depth
                        for paper in filtered[:10]:
                            facts.append(
                                {
                                    "metric": "policy_research",
                                    "value": paper.get("title", ""),
                                    "source": f"Semantic Scholar ({paper.get('year', 'N/A')})",
                                    "source_priority": 75,
                                    "confidence": 0.75,
                                    "raw_text": (
                                        f"Policy research: {paper.get('title')} | "
                                        f"{str(paper.get('abstract', ''))[:150]}"
                                    ),
                                    "timestamp": datetime.now().isoformat(),
                                    "url": paper.get("url", ""),
                                }
                            )

                        _safe_print(f"   ✅ Success! Found {len(facts)} papers via Recommendations")
                        await asyncio.sleep(1)  # Respect 1/second rate limit
                        return facts
                else:
                    _safe_print(f"   Recommendations API: HTTP {response.status_code}")

            except Exception as rec_error:
                _safe_print(f"   Recommendations error: {rec_error}")

            _safe_print("   Strategy 2: Broad search fallback...")
            search_queries = [
                "public policy",
                "policy analysis",
                "government policy",
                "economic policy",
            ]

            for search_query in search_queries:
                try:
                    url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
                    params = {
                        "query": search_query,
                        "fields": "title,year,abstract,url",
                        "year": "2015-",
                        "limit": "10",
                    }

                    _safe_print(f"   Searching: '{search_query}'")
                    response = await asyncio.to_thread(
                        lambda: requests.get(url, params=params, headers=headers, timeout=10)
                    )

                    if response.status_code == 200:
                        data = response.json()
                        papers = data.get("data", [])
                        _safe_print(f"   Query '{search_query}': {len(papers)} results")

                        if papers:
                            facts = []
                            for paper in papers[:3]:
                                facts.append(
                                    {
                                        "metric": "policy_research",
                                        "value": paper.get("title", ""),
                                        "source": f"Semantic Scholar ({paper.get('year', 'N/A')})",
                                        "source_priority": 75,
                                        "confidence": 0.70,
                                        "raw_text": f"Policy research: {paper.get('title')}",
                                        "timestamp": datetime.now().isoformat(),
                                        "url": paper.get("url", ""),
                                    }
                                )

                            _safe_print(f"   ✅ Success! Found {len(facts)} papers")
                            await asyncio.sleep(1)
                            return facts
                    else:
                        _safe_print(f"   Search '{search_query}': HTTP {response.status_code}")

                except Exception as search_error:
                    _safe_print(f"   Search '{search_query}' error: {search_error}")
                    continue

            _safe_print("   ⚠️  All strategies exhausted, no papers found")
            return []

        except Exception as e:
            _safe_print(f"⚠️  Semantic Scholar policy error: {e}")
            import traceback

            traceback.print_exc()
            return []
    
    async def _fetch_brave_economic(self, query: str) -> List[Dict[str, Any]]:
        """Fetch real-time economic news from Brave."""
        if not self.brave_api_key:
            return []
        
        try:
            _safe_print("🔎 Brave: Searching recent economic news...")
            
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.brave_api_key
            }
            params = {
                "q": f"Qatar economic growth OR tech sector {query[:50]}",
                "count": 5,
                "freshness": "pd"  # Past day
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        facts = []
                        for result in data.get('web', {}).get('results', [])[:3]:
                            facts.append({
                                "metric": "news_finding",
                                "value": result.get('title'),
                                "source": "Brave Search (real-time)",
                                "source_priority": 65,
                                "confidence": 0.60,
                                "raw_text": f"Recent: {result.get('description', '')}",
                                "timestamp": datetime.now().isoformat(),
                                "url": result.get('url')
                            })
                        
                        _safe_print(f"   Found {len(facts)} recent articles")
                        return facts
            
            return []
            
        except Exception as e:
            _safe_print(f"⚠️  Brave error: {e}")
            return []
    
    # ================== Perplexity AI ==================
    
    async def _fetch_perplexity_gcc(self, query: str) -> List[Dict[str, Any]]:
        """Fetch GCC competitive intelligence from Perplexity."""
        if not self.perplexity_api_key:
            _safe_print("⚠️  Perplexity: No API key")
            return []

        try:
            _safe_print("🤖 Perplexity: Analyzing GCC competition...")

            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "sonar-pro",
                "messages": [{
                    "role": "user",
                    "content": (
                        "What are the latest GCC labor market trends and regional competition related to: "
                        f"{query[:200]}"
                    ),
                }],
                "max_tokens": 500
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    _safe_print(f"   Perplexity GCC status: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        answer = data["choices"][0]["message"]["content"]

                        _safe_print(f"   Perplexity GCC response: {answer[:100]}...")

                        return [
                            {
                                "metric": "gcc_intelligence",
                                "value": answer[:300],
                                "source": "Perplexity AI (real-time analysis)",
                                "source_priority": 70,
                                "confidence": 0.75,
                                "raw_text": answer,
                                "timestamp": datetime.now().isoformat(),
                            }
                        ]

                    error_text = await response.text()
                    _safe_print(f"   ❌ Perplexity GCC error: {response.status} - {error_text[:200]}")

            return []

        except Exception as e:
            _safe_print(f"⚠️  Perplexity GCC error: {e}")
            import traceback

            traceback.print_exc()
            return []
    
    async def _fetch_perplexity_policy(self, query: str) -> List[Dict[str, Any]]:
        """Fetch policy analysis from Perplexity."""
        if not self.perplexity_api_key:
            _safe_print("⚠️  Perplexity: No API key")
            return []

        try:
            _safe_print("🤖 Perplexity: Analyzing policy implications...")

            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "What are successful examples and risks of workforce nationalization policies similar to: "
                            f"{query[:200]}"
                        ),
                    }
                ],
                "max_tokens": 500
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    _safe_print(f"   Perplexity policy status: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        answer = data["choices"][0]["message"]["content"]

                        _safe_print(f"   Perplexity policy response: {answer[:100]}...")

                        return [
                            {
                                "metric": "policy_analysis",
                                "value": answer[:300],
                                "source": "Perplexity AI (policy analysis)",
                                "source_priority": 70,
                                "confidence": 0.75,
                                "raw_text": answer,
                                "timestamp": datetime.now().isoformat(),
                            }
                        ]

                    error_text = await response.text()
                    _safe_print(f"   ❌ Perplexity policy error: {response.status} - {error_text[:200]}")

            return []

        except Exception as e:
            _safe_print(f"⚠️  Perplexity policy error: {e}")
            import traceback

            traceback.print_exc()
            return []
    
    async def _fetch_perplexity_energy(self, query: str) -> List[Dict[str, Any]]:
        """Fetch energy sector analysis from Perplexity with real-time data and citations."""
        if not self.perplexity_api_key:
            _safe_print("⚠️  Perplexity: No API key")
            return []

        try:
            _safe_print("🤖 Perplexity: Analyzing energy sector with real-time data...")

            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Provide detailed, sourced data on Qatar's energy sector related to: {query[:200]}\n\n"
                            "Include SPECIFIC DATA with citations:\n"
                            "1. Current renewable energy capacity (MW) and percentage of total energy mix\n"
                            "2. Oil and gas production volumes and export revenues (recent year)\n"
                            "3. Energy transition investment commitments and timelines\n"
                            "4. Carbon emissions data and reduction targets\n"
                            "5. Comparison with GCC peers (Saudi, UAE)\n"
                            "6. Recent energy sector projects and their costs\n\n"
                            "Cite all sources and provide exact figures where available."
                        ),
                    }
                ],
                "max_tokens": 800
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    _safe_print(f"   Perplexity energy status: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        answer = data["choices"][0]["message"]["content"]
                        citations = data.get("citations", [])

                        _safe_print(f"   Perplexity energy response: {answer[:100]}...")
                        _safe_print(f"   Retrieved {len(citations)} citations")

                        facts = [
                            {
                                "metric": "energy_sector_analysis",
                                "value": answer[:500],
                                "source": "Perplexity AI (energy analysis with citations)",
                                "source_priority": 85,
                                "confidence": 0.85,
                                "raw_text": answer,
                                "citations": citations,
                                "timestamp": datetime.now().isoformat(),
                            }
                        ]
                        
                        # Extract citations as separate facts
                        for i, citation in enumerate(citations[:5]):
                            facts.append({
                                "metric": f"energy_citation_{i+1}",
                                "value": citation,
                                "source": "Perplexity AI (verified citation)",
                                "source_priority": 80,
                                "confidence": 0.80,
                                "raw_text": f"Citation: {citation}",
                                "timestamp": datetime.now().isoformat(),
                            })
                        
                        return facts

                    error_text = await response.text()
                    _safe_print(f"   ❌ Perplexity energy error: {response.status} - {error_text[:200]}")

            return []

        except Exception as e:
            _safe_print(f"⚠️  Perplexity energy error: {e}")
            return []
    
    async def _fetch_perplexity_food_security(self, query: str) -> List[Dict[str, Any]]:
        """Fetch food security analysis from Perplexity with real-time data and citations."""
        if not self.perplexity_api_key:
            _safe_print("⚠️  Perplexity: No API key")
            return []

        try:
            _safe_print("🤖 Perplexity: Analyzing food security with real-time data...")

            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Provide detailed, sourced data on Qatar's food security related to: {query[:200]}\n\n"
                            "Include SPECIFIC DATA with citations:\n"
                            "1. Current food import dependency percentage by category (meat, dairy, vegetables, cereals)\n"
                            "2. Recent food import costs (annual, in billions)\n"
                            "3. Local agricultural production capacity and percentage of consumption met\n"
                            "4. Food security investments and strategic reserves\n"
                            "5. Comparison with GCC peers on food self-sufficiency\n"
                            "6. Recent government initiatives and their budgets\n\n"
                            "Cite all sources and provide exact figures where available."
                        ),
                    }
                ],
                "max_tokens": 800
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    _safe_print(f"   Perplexity food security status: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        answer = data["choices"][0]["message"]["content"]
                        citations = data.get("citations", [])

                        _safe_print(f"   Perplexity food security response: {answer[:100]}...")
                        _safe_print(f"   Retrieved {len(citations)} citations")

                        facts = [
                            {
                                "metric": "food_security_analysis",
                                "value": answer[:500],
                                "source": "Perplexity AI (food security analysis with citations)",
                                "source_priority": 85,
                                "confidence": 0.85,
                                "raw_text": answer,
                                "citations": citations,
                                "timestamp": datetime.now().isoformat(),
                            }
                        ]
                        
                        # Extract citations as separate facts
                        for i, citation in enumerate(citations[:5]):
                            facts.append({
                                "metric": f"food_security_citation_{i+1}",
                                "value": citation,
                                "source": "Perplexity AI (verified citation)",
                                "source_priority": 80,
                                "confidence": 0.80,
                                "raw_text": f"Citation: {citation}",
                                "timestamp": datetime.now().isoformat(),
                            })
                        
                        return facts

                    error_text = await response.text()
                    _safe_print(f"   ❌ Perplexity food security error: {response.status} - {error_text[:200]}")

            return []

        except Exception as e:
            _safe_print(f"⚠️  Perplexity food security error: {e}")
            return []

    # ================== SMART CONTEXT-AWARE FETCHING ==================
    
    async def _fetch_semantic_scholar_smart(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch academic research using LLM-generated smart queries.
        
        AGGRESSIVE SEARCH STRATEGY:
        1. Use ALL generated academic queries (not just 2)
        2. Request 50 papers per query (not 10)
        3. Use multiple search strategies (search + bulk + recommendations)
        4. Soft filtering - don't discard papers, just score them
        5. Return top 20 most relevant papers
        """
        try:
            _safe_print("🧠 Semantic Scholar: Comprehensive academic research extraction...")
            
            # Generate smart queries using LLM
            smart_queries = await generate_smart_queries(query)
            academic_queries = smart_queries.get("academic_queries", [query[:100]])
            key_concepts = smart_queries.get("key_concepts", [])
            
            # Also add broader queries based on the original question
            broader_queries = [
                query[:80],  # Original question truncated
                " ".join(key_concepts[:3]) if key_concepts else query[:50],  # Key concepts
            ]
            all_queries = list(set(academic_queries + broader_queries))
            
            _safe_print(f"   📚 Searching with {len(all_queries)} queries")
            _safe_print(f"   📚 Key concepts: {key_concepts}")
            
            api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
            headers = {"x-api-key": api_key} if api_key else {}
            
            all_papers = []
            seen_ids = set()
            
            # Strategy 1: Regular search with ALL queries
            for search_query in all_queries[:4]:  # Use up to 4 queries
                try:
                    url = "https://api.semanticscholar.org/graph/v1/paper/search"
                    params = {
                        "query": search_query,
                        "fields": "title,year,abstract,url,citationCount,paperId",
                        "limit": "50"  # Get 50 per query
                    }
                    
                    _safe_print(f"   🔍 Searching: '{search_query[:50]}...'")
                    response = await asyncio.to_thread(
                        lambda q=search_query: requests.get(url, params={"query": q, "fields": "title,year,abstract,url,citationCount,paperId", "limit": "50"}, headers=headers, timeout=15)
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        papers = data.get("data", [])
                        _safe_print(f"      Found {len(papers)} papers")
                        
                        for paper in papers:
                            paper_id = paper.get("paperId")
                            if paper_id and paper_id not in seen_ids:
                                seen_ids.add(paper_id)
                                paper["_query"] = search_query
                                all_papers.append(paper)
                    
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    _safe_print(f"      Query error: {e}")
                    continue
            
            # Strategy 2: Bulk search for more results
            if len(all_papers) < 30:
                try:
                    bulk_query = " OR ".join(key_concepts[:3]) if key_concepts else query[:60]
                    url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
                    params = {
                        "query": bulk_query,
                        "fields": "title,year,abstract,url,citationCount,paperId",
                        "limit": "100"
                    }
                    
                    _safe_print(f"   📦 Bulk search: '{bulk_query[:40]}...'")
                    response = await asyncio.to_thread(
                        lambda: requests.get(url, params=params, headers=headers, timeout=15)
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        papers = data.get("data", [])
                        _safe_print(f"      Bulk returned {len(papers)} papers")
                        
                        for paper in papers:
                            paper_id = paper.get("paperId")
                            if paper_id and paper_id not in seen_ids:
                                seen_ids.add(paper_id)
                                paper["_query"] = "bulk"
                                all_papers.append(paper)
                    
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    _safe_print(f"      Bulk search error: {e}")
            
            _safe_print(f"   📊 Total unique papers collected: {len(all_papers)}")
            
            # Score and rank papers by relevance
            scored_papers = []
            for paper in all_papers:
                title = paper.get("title", "").lower()
                abstract = str(paper.get("abstract", "")).lower()
                text = title + " " + abstract
                citations = paper.get("citationCount", 0) or 0
                year = paper.get("year", 2020) or 2020
                
                # Calculate relevance score
                score = 0
                
                # Concept matching (most important)
                concept_matches = sum(1 for c in key_concepts if c.lower() in text)
                score += concept_matches * 20
                
                # Query word matching
                query_words = query.lower().split()
                word_matches = sum(1 for w in query_words if len(w) > 3 and w in text)
                score += word_matches * 5
                
                # Citation boost (log scale to avoid domination)
                import math
                score += math.log10(citations + 1) * 3
                
                # Recency boost
                score += max(0, (year - 2015)) * 2
                
                paper["_score"] = score
                scored_papers.append(paper)
            
            # Sort by score and take top results
            scored_papers.sort(key=lambda p: p.get("_score", 0), reverse=True)
            top_papers = scored_papers[:20]  # Return top 20
            
            _safe_print(f"   ✅ Selected top {len(top_papers)} most relevant papers")
            
            # Convert to facts
            all_facts = []
            for paper in top_papers:
                citations = paper.get("citationCount", 0) or 0
                all_facts.append({
                    "metric": "academic_research",
                    "value": paper.get("title", ""),
                    "source": f"Semantic Scholar ({paper.get('year', 'N/A')}) - {citations} citations",
                    "source_priority": 75 + min(paper.get("_score", 0) / 10, 15),  # Boost priority by score
                    "confidence": min(0.70 + (paper.get("_score", 0) / 100), 0.95),
                    "raw_text": f"Research: {paper.get('title')} | Citations: {citations} | {str(paper.get('abstract', ''))[:300]}",
                    "timestamp": datetime.now().isoformat(),
                    "url": paper.get("url", ""),
                    "paper_id": paper.get("paperId", ""),
                    "relevance_score": paper.get("_score", 0)
                })
            
            return all_facts
            
        except Exception as e:
            _safe_print(f"⚠️ Semantic Scholar smart search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _fetch_perplexity_smart(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch real-time intelligence using LLM-generated smart queries.
        
        Uses contextually relevant queries to get the most useful
        current information for the user's specific question.
        """
        if not self.perplexity_api_key:
            _safe_print("⚠️  Perplexity: No API key")
            return []
        
        try:
            _safe_print("🧠 Perplexity: Generating smart real-time queries...")
            
            # Generate smart queries using LLM
            smart_queries = await generate_smart_queries(query)
            realtime_queries = smart_queries.get("realtime_queries", [query[:100]])
            data_needs = smart_queries.get("data_needs", query)
            
            _safe_print(f"   Smart queries: {realtime_queries}")
            _safe_print(f"   Data needs: {data_needs[:80]}...")
            
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            all_facts = []
            
            # Combine queries into one comprehensive prompt
            combined_query = " ".join(realtime_queries[:2])
            
            payload = {
                "model": "sonar-pro",
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Find the most recent, specific data and statistics to answer:\n\n"
                        f"QUESTION: {query}\n\n"
                        f"SEARCH FOCUS: {combined_query}\n\n"
                        f"DATA NEEDED: {data_needs}\n\n"
                        "Provide:\n"
                        "1. Specific numbers and statistics with exact figures\n"
                        "2. Most recent data available (2024-2025 preferred)\n"
                        "3. Source citations for verification\n"
                        "4. Comparisons if relevant (regional, historical)\n"
                        "Be concise but data-rich."
                    ),
                }],
                "max_tokens": 700
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    _safe_print(f"   Perplexity smart status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        answer = data["choices"][0]["message"]["content"]
                        citations = data.get("citations", [])
                        
                        _safe_print(f"   Perplexity response: {answer[:100]}...")
                        _safe_print(f"   Citations: {len(citations)}")
                        
                        all_facts.append({
                            "metric": "realtime_intelligence",
                            "value": answer[:500],
                            "source": "Perplexity AI (smart context-aware search)",
                            "source_priority": 85,
                            "confidence": 0.85,
                            "raw_text": answer,
                            "citations": citations,
                            "timestamp": datetime.now().isoformat(),
                            "query_used": combined_query,
                            "data_needs": data_needs
                        })
                        
                        # Extract citations as facts
                        for i, citation in enumerate(citations[:3]):
                            all_facts.append({
                                "metric": f"verified_source_{i+1}",
                                "value": citation,
                                "source": "Perplexity (verified citation)",
                                "source_priority": 80,
                                "confidence": 0.80,
                                "raw_text": f"Source: {citation}",
                                "timestamp": datetime.now().isoformat()
                            })
                        
                        return all_facts
            
            return []
            
        except Exception as e:
            _safe_print(f"⚠️ Perplexity smart search error: {e}")
            return []

    async def fetch_all_sources_with_gaps(self, query: str) -> Dict[str, Any]:
        """
        Multi-pass extraction that identifies and fills critical data gaps
        """
        # Classify query to determine data needs
        query_types = classify_query_for_extraction(query)
        
        # Build combined checklist
        required_data = []
        for qtype in query_types:
            if qtype in CRITICAL_DATA_CHECKLISTS:
                required_data.extend(CRITICAL_DATA_CHECKLISTS[qtype]["required"])
        
        # PASS 1: Quick extraction from structured sources
        structured_facts = await self.fetch_all_sources(query)
        
        # PASS 2: Check what's missing
        data_gaps = identify_missing_data(structured_facts, required_data)
        
        if data_gaps:
            _safe_print(f"⚠️ CRITICAL DATA GAPS DETECTED: {data_gaps}")
            
            # PASS 3: Target searches for missing data
            for gap in data_gaps:
                strategies = TARGETED_SEARCH_STRATEGIES.get(gap, [])
                for strategy in strategies:
                    try:
                        additional_facts = await self._execute_targeted_search(gap, strategy)
                        if additional_facts:
                            structured_facts.extend(additional_facts)
                    except Exception as e:
                        _safe_print(f"Failed strategy {strategy} for {gap}: {e}")
        
        # PASS 4: Final gap check and scoring
        remaining_gaps = identify_missing_data(structured_facts, required_data)
        quality_score = calculate_data_quality(structured_facts, required_data)
        
        return {
            "extracted_facts": structured_facts,
            "data_quality_score": quality_score,
            "critical_gaps": remaining_gaps,
            "total_facts_extracted": len(structured_facts)
        }

    async def _execute_targeted_search(self, data_gap: str, strategy: tuple) -> List[Dict[str, Any]]:
        """Execute a specific targeted search strategy."""
        source, query_or_id, params_or_type = strategy
        results = []
        
        try:
            if source == "world_bank":
                # query_or_id is indicator, params_or_type is dict params
                params = params_or_type if isinstance(params_or_type, dict) else {}
                country = params.get("country", "QAT")
                
                df = await self.world_bank.get_indicator(
                    indicator=query_or_id,
                    country=country
                )
                if not df.empty:
                    latest = df.iloc[0]
                    results.append({
                        "metric": data_gap,
                        "value": latest['value'],
                        "source": "World Bank (Targeted)",
                        "data_type": data_gap,
                        "confidence": 0.9,
                        "timestamp": datetime.now().isoformat()
                    })
            
            elif source == "perplexity":
                # query_or_id is search query, params_or_type is search_type
                search_type = params_or_type if isinstance(params_or_type, str) else "general"
                results = await self._fetch_perplexity_targeted(query_or_id, search_type)
                # Add data_type
                for res in results:
                    res["data_type"] = data_gap
                    
            elif source == "brave_search":
                 if self.brave_api_key:
                    url = "https://api.search.brave.com/res/v1/web/search"
                    headers = {"Accept": "application/json", "X-Subscription-Token": self.brave_api_key}
                    params = {"q": query_or_id, "count": 5}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                for result in data.get('web', {}).get('results', [])[:1]:
                                    results.append({
                                        "metric": data_gap,
                                        "value": result.get('title'),
                                        "source": "Brave Search (Targeted)",
                                        "data_type": data_gap,
                                        "confidence": 0.7,
                                        "raw_text": result.get('description', ''),
                                        "timestamp": datetime.now().isoformat()
                                    })

            elif source == "qatar_open_data":
                if hasattr(self.qatar_open_data, "simple_search"):
                    od_results = await self.qatar_open_data.simple_search(query_or_id)
                    for item in od_results:
                        results.append(
                            {
                                "metric": item.get("metric", data_gap),
                                "value": item.get("value"),
                                "source": item.get("source", "Qatar Open Data"),
                                "data_type": data_gap,
                                "confidence": item.get("confidence", 0.6),
                            }
                        )
            
            elif source == "gcc_stat":
                if hasattr(self.gcc_stat, "get_labour_market_indicators"):
                    df = await asyncio.to_thread(self.gcc_stat.get_labour_market_indicators)
                    if hasattr(df, "head"):
                        sample = df.head(3).to_dict(orient="records")
                        for row in sample:
                            results.append(
                                {
                                    "metric": data_gap,
                                    "value": row,
                                    "source": "GCC-STAT Synthetic",
                                    "data_type": data_gap,
                                    "confidence": 0.7,
                                }
                            )
                 
        except Exception as e:
            _safe_print(f"Targeted search error ({source}): {e}")
            
        return results

    async def _fetch_perplexity_targeted(self, query: str, search_type: str) -> List[Dict[str, Any]]:
        """Targeted Perplexity search with specific prompts."""
        if not self.perplexity_api_key:
            return []
            
        prompt_template = PERPLEXITY_PROMPT_TEMPLATES.get(search_type, PERPLEXITY_PROMPT_TEMPLATES["statistics"])
        prompt = prompt_template.replace("{query}", query)
        
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        return [{
                            "metric": "targeted_research",
                            "value": content[:200],
                            "raw_text": content,
                            "source": "Perplexity (Targeted)",
                            "confidence": 0.85,
                            "timestamp": datetime.now().isoformat()
                        }]
        except Exception as e:
            _safe_print(f"Perplexity targeted error: {e}")
            
        return []

    async def _fetch_imf(self, indicator_code: str, params: Dict) -> List[Dict]:
        """Fetch data from IMF API"""
        if not self.imf_connector:
            return []
        
        try:
            country = params.get("country", "QAT")
            data = await self.imf_connector.get_indicator(indicator_code, country)
            
            facts = []
            values = data.get("values", {})
            metadata = data.get("metadata", {})
            
            if values:
                latest_year = max(values.keys(), key=lambda x: int(x))
                latest_value = values[latest_year]
                
                facts.append({
                    "data_type": metadata.get("description", indicator_code),
                    "value": latest_value,
                    "year": int(latest_year),
                    "source": "IMF Data Mapper API",
                    "country": metadata.get("country_name", country),
                    "indicator_code": indicator_code,
                    "confidence": "high",
                    "all_years": values
                })
            
            return facts
            
        except Exception as e:
            _safe_print(f"IMF fetch failed for {indicator_code}: {e}")
            return []

    async def _fetch_comtrade(self, commodity_code: str, params: Dict) -> List[Dict]:
        """Fetch data from UN Comtrade API"""
        if not self.un_comtrade_connector:
            return []
        
        try:
            year = params.get("year", 2023)
            
            if commodity_code == "FOOD_TOTAL":
                # Get total food imports
                data = await self.un_comtrade_connector.get_total_food_imports(year)
                total_value = data.get("TOTAL", {}).get("value_usd", 0)
                
                return [{
                    "data_type": "Total Food Imports",
                    "value": total_value,
                    "year": year,
                    "source": "UN Comtrade API",
                    "country": "Qatar",
                    "unit": "USD",
                    "confidence": "high",
                    "breakdown": {k: v for k, v in data.items() if k != "TOTAL"}
                }]
            else:
                # Get specific commodity
                data = await self.un_comtrade_connector.get_imports(commodity_code, year)
                if "data" in data and len(data["data"]) > 0:
                    total_value = sum(item.get("primaryValue", 0) for item in data["data"])
                    
                    return [{
                        "data_type": f"Imports - Commodity {commodity_code}",
                        "value": total_value,
                        "year": year,
                        "source": "UN Comtrade API",
                        "country": "Qatar",
                        "unit": "USD",
                        "confidence": "high",
                        "records": len(data["data"])
                    }]
            
            return []
            
        except Exception as e:
            _safe_print(f"UN Comtrade fetch failed: {e}")
            return []
    
    async def _fetch_fred(self, series_id: str, params: Dict) -> List[Dict]:
        """Fetch data from FRED API"""
        if not self.fred_connector:
            return []
        
        try:
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            
            data = await self.fred_connector.get_series(series_id, start_date, end_date)
            
            facts = []
            values = data.get("values", {})
            
            if values:
                latest_date = max(values.keys())
                latest_value = values[latest_date]
                
                facts.append({
                    "data_type": f"FRED Series {series_id}",
                    "value": latest_value,
                    "date": latest_date,
                    "source": "FRED (Federal Reserve Economic Data)",
                    "series_id": series_id,
                    "confidence": "high",
                    "all_values": values
                })
            
            return facts
            
        except Exception as e:
            _safe_print(f"FRED fetch failed for {series_id}: {e}")
            return []
    
    async def _fetch_imf_dashboard(self) -> List[Dict[str, Any]]:
        """Fetch Qatar economic dashboard from IMF"""
        if not self.imf_connector:
            _safe_print("⚠️  IMF connector not available")
            return []
        
        try:
            _safe_print("✅ IMF: Fetching Qatar economic dashboard...")
            dashboard = await self.imf_connector.get_qatar_dashboard()
            
            facts = []
            for indicator_name, data in dashboard.items():
                if "error" not in data:
                    values = data.get("values", {})
                    metadata = data.get("metadata", {})
                    
                    if values:
                        latest_year = max(values.keys(), key=lambda x: int(x))
                        latest_value = values[latest_year]
                        
                        facts.append({
                            "metric": indicator_name,
                            "value": latest_value,
                            "year": int(latest_year),
                            "description": metadata.get("description", indicator_name),
                            "source": "IMF Data Mapper API",
                            "source_priority": 95,
                            "country": "Qatar",
                            "confidence": 0.98,
                            "raw_text": f"{metadata.get('description', indicator_name)}: {latest_value} ({latest_year})",
                            "timestamp": datetime.now().isoformat()
                        })
            
            _safe_print(f"   Retrieved {len(facts)} IMF indicators")
            return facts
            
        except Exception as e:
            _safe_print(f"❌ IMF API error: {e}")
            return []
    
    async def _fetch_comtrade_food(self) -> List[Dict[str, Any]]:
        """Fetch Qatar food imports from UN Comtrade"""
        if not self.un_comtrade_connector:
            _safe_print("⚠️  UN Comtrade connector not available")
            return []
        
        try:
            _safe_print("✅ UN Comtrade: Fetching Qatar food imports...")
            food_imports = await self.un_comtrade_connector.get_total_food_imports(2023)
            
            facts = []
            total_value = food_imports.get("TOTAL", {}).get("value_usd", 0)
            
            # Add total
            facts.append({
                "metric": "total_food_imports",
                "value": total_value,
                "year": 2023,
                "source": "UN Comtrade API",
                "source_priority": 95,
                "confidence": 0.95,
                "raw_text": f"Qatar total food imports (2023): ${total_value:,.0f}",
                "timestamp": datetime.now().isoformat(),
                "unit": "USD"
            })
            
            # Add breakdown by category
            for category, data in food_imports.items():
                if category != "TOTAL" and "error" not in data:
                    cat_value = data.get("value_usd", 0)
                    facts.append({
                        "metric": f"food_imports_{category.lower().replace(' ', '_')}",
                        "value": cat_value,
                        "category": category,
                        "year": 2023,
                        "source": "UN Comtrade API",
                        "source_priority": 90,
                        "confidence": 0.90,
                        "raw_text": f"Qatar {category} imports (2023): ${cat_value:,.0f}",
                        "timestamp": datetime.now().isoformat()
                    })
            
            _safe_print(f"   Retrieved food import data: ${total_value:,.0f}")
            return facts
            
        except Exception as e:
            _safe_print(f"❌ UN Comtrade API error: {e}")
            return []
    
    async def _fetch_fred_benchmarks(self) -> List[Dict[str, Any]]:
        """Fetch US economic benchmarks from FRED"""
        if not self.fred_connector:
            _safe_print("⚠️  FRED connector not available")
            return []
        
        try:
            _safe_print("✅ FRED: Fetching US economic benchmarks...")
            
            # Key US indicators for comparison
            series_map = {
                "GDP": "US GDP",
                "UNRATE": "US Unemployment Rate",
                "CPIAUCSL": "US Inflation (CPI)"
            }
            
            facts = []
            for series_id, description in series_map.items():
                try:
                    latest_value = await self.fred_connector.get_latest_value(series_id)
                    if latest_value is not None:
                        facts.append({
                            "metric": f"us_{series_id.lower()}",
                            "value": latest_value,
                            "description": description,
                            "series_id": series_id,
                            "source": "FRED (Federal Reserve Economic Data)",
                            "source_priority": 90,
                            "country": "United States",
                            "confidence": 0.95,
                            "raw_text": f"{description}: {latest_value}",
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    _safe_print(f"   Failed to fetch {series_id}: {e}")
            
            _safe_print(f"   Retrieved {len(facts)} US benchmarks")
            return facts
            
        except Exception as e:
            _safe_print(f"❌ FRED API error: {e}")
            return []
    
    def _query_postgres_cache(self, source: str, country: str = "QAT") -> List[Dict]:
        """
        Query PostgreSQL cache BEFORE calling APIs
        ENTERPRISE-GRADE: Cache-first strategy reduces API calls from 2 minutes to <100ms
        """
        from sqlalchemy import text
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            with self.pg_engine.connect() as conn:
                if source == "world_bank":
                    result = conn.execute(
                        text("""
                            SELECT indicator_code, indicator_name, year, value, country_name
                            FROM world_bank_indicators
                            WHERE country_code = :country
                            ORDER BY year DESC
                        """),
                        {"country": country}
                    )
                    
                    facts = []
                    for row in result:
                        facts.append({
                            "metric": row.indicator_code,
                            "indicator_code": row.indicator_code,
                            "indicator_name": row.indicator_name,
                            "description": row.indicator_name,
                            "year": row.year,
                            "value": float(row.value),
                            "country": row.country_name,
                            "country_name": row.country_name,
                            "source": "World Bank (PostgreSQL cache)",
                            "source_priority": 98,
                            "confidence": 0.99,
                            "cached": True,
                            "raw_text": f"{row.indicator_name}: {row.value} ({row.year})",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    return facts
                
                elif source == "ilo":
                    result = conn.execute(
                        text("""
                            SELECT indicator_code, indicator_name, year, value, country_name, sex, age_group
                            FROM ilo_labour_data
                            WHERE country_code = :country
                            ORDER BY year DESC
                        """),
                        {"country": country}
                    )
                    
                    facts = []
                    for row in result:
                        facts.append({
                            "metric": row.indicator_code,
                            "indicator_code": row.indicator_code,
                            "indicator_name": row.indicator_name,
                            "description": row.indicator_name,
                            "year": row.year,
                            "value": float(row.value),
                            "country": row.country_name,
                            "country_name": row.country_name,
                            "sex": row.sex,
                            "age_group": row.age_group,
                            "source": "ILO (PostgreSQL cache)",
                            "source_priority": 98,
                            "confidence": 0.99,
                            "cached": True,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    return facts
            
        except Exception as e:
            logger.error(f"Failed to query PostgreSQL cache for {source}: {e}")
            return []
        
        return []
    
    async def _fetch_world_bank_dashboard(self) -> List[Dict[str, Any]]:
        """
        Fetch Qatar dashboard from World Bank - CACHE-FIRST STRATEGY
        
        PERFORMANCE: Queries PostgreSQL cache first (128 records in <100ms)
        Only calls API if cache is empty or stale
        
        This is the MOST CRITICAL API addition:
        - Sector GDP breakdown (tourism %, manufacturing %, services %)
        - Infrastructure quality metrics
        - Human capital indicators
        - Digital economy metrics
        """
        if not self.world_bank_connector:
            _safe_print("⚠️  World Bank connector not available")
            return []
        
        try:
            # CACHE-FIRST: Try PostgreSQL cache before API
            cached_facts = self._query_postgres_cache("world_bank", "QAT")
            
            if cached_facts and len(cached_facts) >= 100:  # Have sufficient cached data (128 rows)
                # VALIDATION: Check if cached data looks realistic for Qatar
                # Qatar's unemployment rate should be < 5% (it's actually ~0.1%)
                suspicious_values = [f for f in cached_facts if 'UEM' in str(f.get('metric', '')) and f.get('value', 0) > 5]
                if suspicious_values:
                    _safe_print(f"⚠️ World Bank: Cache has {len(suspicious_values)} suspicious unemployment values > 5% - REFRESHING from API")
                    # Don't use cache - fall through to API fetch
                else:
                    _safe_print(f"✅ World Bank: Using {len(cached_facts)} cached indicators from PostgreSQL (<100ms)")
                    return cached_facts
            
            # Cache miss or insufficient data - fetch from API
            _safe_print("📡 World Bank: Cache miss, fetching from API (this takes ~2 minutes)...")
            
            # Get sector GDP breakdown first (CRITICAL gap fix)
            sector_gdp = await self.world_bank_connector.get_sector_gdp_breakdown("QAT")
            
            facts = []
            
            # Add sector GDP data
            if "sector_breakdown" in sector_gdp:
                for sector_name, data in sector_gdp["sector_breakdown"].items():
                    if "percentage_of_gdp" in data:
                        facts.append({
                            "metric": f"{sector_name.lower()}_gdp_percentage",
                            "value": data["percentage_of_gdp"],
                            "sector": sector_name,
                            "source": "World Bank Indicators API",
                            "source_priority": 98,
                            "confidence": 0.99,
                            "raw_text": f"{sector_name} sector: {data['percentage_of_gdp']}% of GDP",
                            "timestamp": datetime.now().isoformat(),
                            "note": "FILLS CRITICAL GAP - sector GDP previously unavailable"
                        })
            
            # Get full dashboard for other indicators
            dashboard = await self.world_bank_connector.get_qatar_dashboard()
            
            for indicator_code, data in dashboard.items():
                if "error" not in data and data.get("latest_value") is not None:
                    facts.append({
                        "metric": indicator_code,
                        "value": data["latest_value"],
                        "year": data.get("latest_year"),
                        "description": data.get("description", indicator_code),
                        "source": "World Bank Indicators API",
                        "source_priority": 98,
                        "country": "Qatar",
                        "confidence": 0.99,
                        "raw_text": f"{data.get('description', indicator_code)}: {data['latest_value']} ({data.get('latest_year', 'N/A')})",
                        "timestamp": datetime.now().isoformat()
                    })
            
            _safe_print(f"   Retrieved {len(facts)} World Bank indicators (including SECTOR GDP)")
            
            # Write to PostgreSQL for caching
            self._write_facts_to_postgres(facts, "world_bank")
            
            return facts
            
        except Exception as e:
            _safe_print(f"❌ World Bank API error: {e}")
            return []
    
    async def _fetch_world_bank_indicators_subset(self, country: str = "QAT", indicator_codes: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch specific World Bank indicators from cache
        Used for targeted data extraction (energy, agriculture, manufacturing, infrastructure)
        """
        if not indicator_codes:
            return []
        
        try:
            # Query PostgreSQL cache for specific indicators
            cached_facts = self._query_postgres_cache("world_bank", country)
            
            if not cached_facts:
                return []
            
            # Filter for requested indicators
            filtered_facts = [
                fact for fact in cached_facts 
                if fact.get("metric") in indicator_codes
            ]
            
            return filtered_facts
            
        except Exception as e:
            _safe_print(f"❌ World Bank subset query error: {e}")
            return []
    
    async def _fetch_unctad_investment(self, country: str = "QAT") -> List[Dict[str, Any]]:
        """
        Fetch UNCTAD FDI and investment data - CACHE-FIRST
        FILLS GAP: Investment climate analysis
        """
        if not self.unctad_connector:
            _safe_print("⚠️  UNCTAD connector not available")
            return []
        
        try:
            _safe_print("📡 UNCTAD: Fetching investment and FDI data...")
            
            # Fetch FDI dashboard
            dashboard = await self.unctad_connector.get_investment_dashboard(country)
            
            facts = []
            
            if dashboard and "error" not in dashboard:
                for indicator, data in dashboard.items():
                    if isinstance(data, dict) and "latest_value" in data:
                        facts.append({
                            "metric": indicator,
                            "value": data["latest_value"],
                            "year": data.get("latest_year"),
                            "country": country,
                            "unit": data.get("unit", "USD millions"),
                            "source": "UNCTAD FDI Database",
                            "source_priority": 97,
                            "confidence": 0.98,
                            "raw_text": f"{indicator}: {data['latest_value']} ({data.get('latest_year')})",
                            "timestamp": datetime.now().isoformat()
                        })
            
            _safe_print(f"   Retrieved {len(facts)} UNCTAD indicators")
            return facts
            
        except Exception as e:
            _safe_print(f"❌ UNCTAD error: {e}")
            return []
    
    async def _fetch_ilo_benchmarks(self, country: str = "QAT") -> List[Dict[str, Any]]:
        """
        Fetch ILO international labor benchmarks - CACHE-FIRST
        FILLS GAP: International wage and employment comparison
        """
        if not self.ilo_connector:
            _safe_print("⚠️  ILO connector not available")
            return []
        
        try:
            # Check cache first (we already have 6 GCC countries!)
            cached_facts = self._query_postgres_cache("ilo", country)
            if cached_facts and len(cached_facts) >= 1:
                _safe_print(f"✅ ILO: Using {len(cached_facts)} cached indicators from PostgreSQL (<100ms)")
                return cached_facts
            
            _safe_print("📡 ILO: Fetching international labor benchmarks...")
            
            # Fetch employment stats
            employment = await self.ilo_connector.get_employment_stats(country)
            
            facts = []
            
            if employment and "error" not in employment:
                facts.append({
                    "metric": "employment_total",
                    "value": employment.get("total_employed", 0),
                    "year": employment.get("year", 2023),
                    "country": country,
                    "source": "ILO ILOSTAT",
                    "source_priority": 97,
                    "confidence": 0.98,
                    "raw_text": f"Total employment: {employment.get('total_employed', 0)}",
                    "timestamp": datetime.now().isoformat()
                })
            
            _safe_print(f"   Retrieved {len(facts)} ILO indicators")
            return facts
            
        except Exception as e:
            _safe_print(f"❌ ILO error: {e}")
            return []
    
    async def _fetch_lmis_comprehensive(self, lang: str = "en") -> List[Dict[str, Any]]:
        """
        Fetch comprehensive LMIS data from Ministry of Labour Qatar.
        
        OFFICIAL AUTHORITATIVE SOURCE for Qatar labor market data.
        17+ endpoints covering:
        - Main labor indicators
        - SDG progress
        - Sector growth (NDS3, ISIC)
        - Skills analysis
        - Qatarization data
        - Expat workforce dynamics
        - SME growth metrics
        """
        if not self.lmis_connector:
            _safe_print("⚠️  LMIS connector not available")
            return []
        
        try:
            _safe_print("🏛️ LMIS: Fetching official Qatar labor market data...")
            facts = []
            
            # 1. Main indicators (critical for any labor query)
            try:
                df = self.lmis_connector.get_qatar_main_indicators(lang)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        facts.append({
                            "metric": "qatar_main_indicator",
                            "data": row.to_dict(),
                            "source": "LMIS (Ministry of Labour Qatar)",
                            "source_type": "official_government",
                            "source_priority": 99,
                            "confidence": 0.98,
                            "cached": False
                        })
                    _safe_print(f"   ✅ Main indicators: {len(df)} records")
            except Exception as e:
                _safe_print(f"   ⚠️ Main indicators error: {e}")
            
            # 2. Sector growth (NDS3 strategic clusters)
            try:
                df = self.lmis_connector.get_sector_growth("NDS3", lang)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        facts.append({
                            "metric": "sector_growth_nds3",
                            "data": row.to_dict(),
                            "source": "LMIS (Ministry of Labour Qatar)",
                            "source_type": "official_government",
                            "source_priority": 98,
                            "confidence": 0.95,
                            "cached": False
                        })
                    _safe_print(f"   ✅ Sector growth (NDS3): {len(df)} records")
            except Exception as e:
                _safe_print(f"   ⚠️ Sector growth error: {e}")
            
            # 3. Top skills by sector
            try:
                df = self.lmis_connector.get_top_skills_by_sector("NDS3", lang)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        facts.append({
                            "metric": "top_skills_sector",
                            "data": row.to_dict(),
                            "source": "LMIS (Ministry of Labour Qatar)",
                            "source_type": "official_government",
                            "source_priority": 97,
                            "confidence": 0.93,
                            "cached": False
                        })
                    _safe_print(f"   ✅ Top skills: {len(df)} records")
            except Exception as e:
                _safe_print(f"   ⚠️ Top skills error: {e}")
            
            # 4. Emerging and decaying skills
            try:
                df = self.lmis_connector.get_emerging_decaying_skills(lang)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        facts.append({
                            "metric": "emerging_decaying_skills",
                            "data": row.to_dict(),
                            "source": "LMIS (Ministry of Labour Qatar)",
                            "source_type": "official_government",
                            "source_priority": 96,
                            "confidence": 0.92,
                            "cached": False
                        })
                    _safe_print(f"   ✅ Emerging skills: {len(df)} records")
            except Exception as e:
                _safe_print(f"   ⚠️ Emerging skills error: {e}")
            
            # 5. Expat dominated occupations
            try:
                df = self.lmis_connector.get_expat_dominated_occupations(lang)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        facts.append({
                            "metric": "expat_dominated_occupations",
                            "data": row.to_dict(),
                            "source": "LMIS (Ministry of Labour Qatar)",
                            "source_type": "official_government",
                            "source_priority": 95,
                            "confidence": 0.94,
                            "cached": False
                        })
                    _safe_print(f"   ✅ Expat occupations: {len(df)} records")
            except Exception as e:
                _safe_print(f"   ⚠️ Expat occupations error: {e}")
            
            # 6. Best paid occupations
            try:
                df = self.lmis_connector.get_best_paid_occupations(lang)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        facts.append({
                            "metric": "best_paid_occupations",
                            "data": row.to_dict(),
                            "source": "LMIS (Ministry of Labour Qatar)",
                            "source_type": "official_government",
                            "source_priority": 94,
                            "confidence": 0.93,
                            "cached": False
                        })
                    _safe_print(f"   ✅ Best paid occupations: {len(df)} records")
            except Exception as e:
                _safe_print(f"   ⚠️ Best paid occupations error: {e}")
            
            _safe_print(f"🏛️ LMIS TOTAL: {len(facts)} official records retrieved")
            return facts
            
        except Exception as e:
            _safe_print(f"❌ LMIS comprehensive error: {e}")
            return []
    
    async def _fetch_fao_food_security(self, country: str = "QAT") -> List[Dict[str, Any]]:
        """
        Fetch FAO food security and agriculture data with World Bank supplement
        FILLS GAP: Food security analysis
        FIX: FAO returns limited data, use World Bank agriculture indicators as primary source
        """
        facts = []
        
        # PRIMARY: Use World Bank agriculture indicators (always available from cache)
        try:
            _safe_print("📡 World Bank: Fetching agriculture/food indicators...")
            
            # Comprehensive agriculture and food security indicators from World Bank
            agriculture_indicators = [
                'AG.LND.AGRI.ZS',       # Agricultural land (% of land area)
                'AG.PRD.FOOD.XD',       # Food production index
                'AG.LND.ARBL.HA.PC',    # Arable land per person (hectares)
                'AG.YLD.CREL.KG',       # Cereal yield (kg per hectare)
                'NV.AGR.TOTL.ZS',       # Agriculture value added (% of GDP)
                'AG.CON.FERT.ZS',       # Fertilizer consumption (kg per hectare)
                'AG.LND.CROP.ZS',       # Crop land (% of land area)
                'AG.LND.IRIG.AG.ZS',    # Irrigated land (% of cropland)
                'SN.ITK.DEFC.ZS',       # Prevalence of undernourishment
                'SP.DYN.LE00.IN',       # Life expectancy (food security impact)
                'TM.VAL.FOOD.ZS.UN',    # Food imports (% of merchandise imports)
                'TX.VAL.FOOD.ZS.UN',    # Food exports (% of merchandise exports)
            ]
            
            # Get from World Bank cache (PostgreSQL)
            wb_facts = await self._fetch_world_bank_indicators_subset(country, agriculture_indicators)
            
            # Convert to agriculture facts format
            for fact in wb_facts:
                facts.append({
                    "metric": fact.get("metric", "unknown"),
                    "value": fact.get("value"),
                    "year": fact.get("year"),
                    "country": country,
                    "source": "World Bank Agriculture Indicators",
                    "source_priority": 95,
                    "confidence": 0.95,
                    "raw_text": fact.get("raw_text", ""),
                    "timestamp": datetime.now().isoformat()
                })
            
            _safe_print(f"   Retrieved {len(facts)} World Bank agriculture indicators")
            
        except Exception as e:
            _safe_print(f"❌ World Bank agriculture error: {e}")
        
        # SECONDARY: Try FAO if available (but extract properly structured data only)
        if self.fao_connector and len(facts) < 5:
            try:
                _safe_print("📡 FAO: Fetching food security data (supplement)...")
                dashboard = await self.fao_connector.get_food_security_dashboard("634")  # Qatar code
                
                if dashboard and "error" not in dashboard:
                    # Only add if we can extract real data (not just availability flags)
                    food_balance = dashboard.get("food_balance", {})
                    if food_balance and "error" not in food_balance and food_balance.get("food_balance"):
                        facts.append({
                            "metric": "food_balance_available",
                            "value": 1.0,
                            "year": 2023,
                            "country": "Qatar",
                            "source": "FAO STAT - Food Balance",
                            "source_priority": 96,
                            "confidence": 0.97,
                            "raw_text": "Food balance data available from FAO",
                            "timestamp": datetime.now().isoformat()
                        })
                
                _safe_print(f"   Retrieved {len(facts)} total food/agriculture indicators")
                
            except Exception as e:
                _safe_print(f"⚠️  FAO supplement failed: {e}")
        
        return facts
    
    async def _fetch_unwto_tourism(self, country: str = "QAT") -> List[Dict[str, Any]]:
        """
        Fetch UNWTO tourism statistics - CACHE-FIRST
        FILLS GAP: Detailed tourism sector analysis
        """
        if not self.unwto_connector:
            _safe_print("⚠️  UNWTO connector not available")
            return []
        
        try:
            _safe_print("📡 UNWTO: Fetching tourism statistics...")
            
            # Fetch tourism dashboard
            dashboard = await self.unwto_connector.get_tourism_dashboard(country)
            
            facts = []
            
            if dashboard and "error" not in dashboard:
                for indicator, data in dashboard.items():
                    if isinstance(data, dict) and "latest_value" in data:
                        facts.append({
                            "metric": indicator,
                            "value": data["latest_value"],
                            "year": data.get("latest_year"),
                            "country": country,
                            "source": "UNWTO Tourism Statistics",
                            "source_priority": 95,
                            "confidence": 0.96,
                            "raw_text": f"{indicator}: {data['latest_value']} ({data.get('latest_year')})",
                            "timestamp": datetime.now().isoformat()
                        })
            
            _safe_print(f"   Retrieved {len(facts)} UNWTO indicators")
            return facts
            
        except Exception as e:
            _safe_print(f"❌ UNWTO error: {e}")
            return []
    
    async def _fetch_iea_energy(self, country: str = "QAT") -> List[Dict[str, Any]]:
        """
        Fetch IEA energy sector and transition data with World Bank fallback
        FILLS GAP: Energy transition tracking
        FIX: IEA requires API key, use World Bank energy indicators as primary source
        """
        facts = []
        
        # PRIMARY: Use World Bank energy indicators (always available from cache)
        try:
            _safe_print("📡 World Bank: Fetching energy indicators...")
            
            # Comprehensive energy indicators from World Bank
            energy_indicators = [
                'EG.USE.PCAP.KG.OE',    # Energy use per capita (kg of oil equivalent)
                'EG.USE.ELEC.KH.PC',    # Electric power consumption (kWh per capita)
                'EG.ELC.ACCS.ZS',       # Access to electricity (% of population)
                'EG.FEC.RNEW.ZS',       # Renewable energy consumption (% of total)
                'EG.USE.COMM.FO.ZS',    # Fossil fuel energy consumption (% of total)
                'EN.ATM.CO2E.PC',       # CO2 emissions per capita (metric tons)
                'EN.ATM.CO2E.KT',       # CO2 emissions (kt)
                'EG.ELC.FOSL.ZS',       # Electricity from fossil fuels (% of total)
                'EG.ELC.RNWX.ZS',       # Electricity from renewables (% of total)
                'EG.IMP.CONS.ZS',       # Energy imports (% of energy use)
                'NV.IND.TOTL.ZS',       # Industry value added (% of GDP) - energy intensive
                'EG.GDP.PUSE.KO.PP',    # GDP per unit of energy use
            ]
            
            # Get from World Bank cache (PostgreSQL)
            wb_facts = await self._fetch_world_bank_indicators_subset(country, energy_indicators)
            
            # Convert to energy facts format
            for fact in wb_facts:
                facts.append({
                    "metric": fact.get("metric", "unknown"),
                    "value": fact.get("value"),
                    "year": fact.get("year"),
                    "country": country,
                    "source": "World Bank Energy Indicators",
                    "source_priority": 95,
                    "confidence": 0.95,
                    "raw_text": fact.get("raw_text", ""),
                    "timestamp": datetime.now().isoformat()
                })
            
            _safe_print(f"   Retrieved {len(facts)} World Bank energy indicators")
            
        except Exception as e:
            _safe_print(f"❌ World Bank energy error: {e}")
        
        # SECONDARY: Try IEA if available (requires API key)
        if self.iea_connector and len(facts) == 0:
            try:
                _safe_print("📡 IEA: Fetching energy sector data (fallback)...")
                dashboard = await self.iea_connector.get_energy_dashboard(country)
                
                if dashboard and "error" not in dashboard:
                    for indicator, data in dashboard.items():
                        if isinstance(data, dict) and "latest_value" in data:
                            facts.append({
                                "metric": indicator,
                                "value": data["latest_value"],
                                "year": data.get("latest_year"),
                                "country": country,
                                "source": "IEA Energy Statistics",
                                "source_priority": 96,
                                "confidence": 0.97,
                                "raw_text": f"{indicator}: {data['latest_value']} ({data.get('latest_year')})",
                                "timestamp": datetime.now().isoformat()
                            })
                
                _safe_print(f"   Retrieved {len(facts)} IEA indicators")
                
            except Exception as e:
                _safe_print(f"⚠️  IEA fallback failed: {e}")
        
        return facts
    
    # ================== Arab Development Portal ==================
    
    async def _fetch_adp_data(self, query: str, domain: str = "labor") -> List[Dict[str, Any]]:
        """Fetch data from Arab Development Portal (179K+ datasets)."""
        if not self.adp_connector:
            _safe_print("⚠️  Arab Dev Portal connector not available")
            return []
        
        facts = []
        try:
            _safe_print(f"📡 ADP: Searching {domain} datasets for Qatar...")
            
            datasets = await self.adp_connector.search_datasets(
                theme=domain, 
                country="QAT",
                limit=20
            )
            
            if datasets:
                for ds in datasets[:10]:  # Top 10 most relevant
                    facts.append({
                        "metric": ds.get("title", "ADP Dataset"),
                        "value": ds.get("dataset_id"),
                        "description": ds.get("description", ""),
                        "source": f"Arab Development Portal ({domain})",
                        "source_priority": 92,
                        "confidence": 0.90,
                        "raw_text": f"ADP Dataset: {ds.get('title', 'Unknown')}",
                        "timestamp": datetime.now().isoformat()
                    })
                
                _safe_print(f"   Retrieved {len(facts)} ADP {domain} datasets")
            
        except Exception as e:
            logger.debug(f"ADP error (non-critical): {e}")  # Downgrade to debug - ADP is optional
        
        return facts
    
    # ================== ESCWA Trade Data ==================
    
    async def _fetch_escwa_trade(self, query: str) -> List[Dict[str, Any]]:
        """Fetch trade data from UN ESCWA platform."""
        if not self.escwa_connector:
            _safe_print("⚠️  ESCWA Trade connector not available")
            return []
        
        facts = []
        try:
            _safe_print("📡 ESCWA: Fetching Qatar trade data...")
            
            # Get exports and imports (returns dict with "data" key)
            exports_result = await self.escwa_connector.get_qatar_exports(year=2023)
            imports_result = await self.escwa_connector.get_qatar_imports(year=2023)
            
            # Extract data from results
            export_data = exports_result.get("data", []) if exports_result else []
            import_data = imports_result.get("data", []) if imports_result else []
            
            if export_data:
                for item in export_data[:10]:
                    facts.append({
                        "metric": f"Export: {item.get('commodity_code', 'Total')}",
                        "value": item.get("value_usd"),
                        "year": item.get("year", 2023),
                        "partner": exports_result.get("partner", "World"),
                        "source": "UN ESCWA Trade Data",
                        "source_priority": 93,
                        "confidence": 0.92,
                        "raw_text": f"Qatar {item.get('flow', 'export')} to {exports_result.get('partner', 'World')}",
                        "timestamp": datetime.now().isoformat()
                    })
            
            if import_data:
                for item in import_data[:10]:
                    facts.append({
                        "metric": f"Import: {item.get('commodity_code', 'Total')}",
                        "value": item.get("value_usd"),
                        "year": item.get("year", 2023),
                        "partner": imports_result.get("partner", "World"),
                        "source": "UN ESCWA Trade Data",
                        "source_priority": 93,
                        "confidence": 0.92,
                        "raw_text": f"Qatar {item.get('flow', 'import')} from {imports_result.get('partner', 'World')}",
                        "timestamp": datetime.now().isoformat()
                    })
            
            _safe_print(f"   Retrieved {len(facts)} ESCWA trade data points")
            
        except Exception as e:
            _safe_print(f"❌ ESCWA error: {e}")
        
        return facts
    
    # ================== Knowledge Graph ==================
    
    async def _fetch_knowledge_graph_context(self, query: str) -> List[Dict[str, Any]]:
        """Fetch relevant context from knowledge graph for cross-domain reasoning."""
        if not self._knowledge_graph:
            return []
        
        facts = []
        try:
            _safe_print("🧠 Knowledge Graph: Finding related entities...")
            
            # Extract entities from query
            extracted = self._knowledge_graph.extract_entities_from_text(query)
            
            if extracted:
                _safe_print(f"   Found {len(extracted)} entities in query")
                
                # Get related entities for each extracted entity - WITH FILTERING
                seen_related = set()
                
                # Skip generic/useless entities as sources
                generic_entities = {"artificial intelligence", "ai", "machine learning", "ml",
                                   "knowledge", "entity", "graph", "data", "information",
                                   "technology", "computer science", "algorithm"}
                
                for entity_id in extracted[:5]:  # Limit to 5 entities
                    # Skip if source entity is generic
                    if str(entity_id).lower() in generic_entities:
                        continue
                    
                    related = self._knowledge_graph.get_related_entities(
                        entity_id, max_hops=2
                    )
                    
                    for related_id, edge_data in related[:3]:  # Top 3 related
                        node_data = self._knowledge_graph.graph.nodes.get(related_id, {})
                        related_name = node_data.get('name', str(related_id))
                        
                        # QUALITY FILTERS
                        # Skip generic/useless related entities
                        if related_name.lower() in generic_entities:
                            continue
                        
                        # Skip very short names
                        if len(related_name) < 3:
                            continue
                        
                        # Skip duplicates
                        related_key = related_name.lower().strip()
                        if related_key in seen_related:
                            continue
                        seen_related.add(related_key)
                        
                        entity_type = node_data.get('type', 'unknown')
                        if entity_type.lower() in ["unknown", "none", ""]:
                            continue
                        
                        facts.append({
                            "metric": f"Related: {related_name}",
                            "entity_type": entity_type,
                            "relationship": edge_data.get('relation_type', 'related_to'),
                            "source_entity": entity_id,
                            "source": "Knowledge Graph",
                            "source_priority": 70,  # Lower priority than API data
                            "confidence": min(edge_data.get('confidence', 0.7), 0.75),
                            "raw_text": f"Knowledge Graph: {entity_id} → {edge_data.get('relation_type', 'relates to')} → {related_name}",
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # Limit total KG relationships
                        if len(facts) >= 10:
                            break
                    
                    if len(facts) >= 10:
                        break
                
                _safe_print(f"   Retrieved {len(facts)} knowledge graph relationships")
            
        except Exception as e:
            _safe_print(f"❌ Knowledge Graph error: {e}")
        
        return facts
    
    def _write_facts_to_postgres(self, facts: List[Dict], source: str):
        """
        Write prefetched facts to PostgreSQL for caching
        
        Uses EXISTING tables (world_bank_indicators, ilo_labour_data, etc.)
        """
        from sqlalchemy import text
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not facts:
            return
        
        try:
            with self.pg_engine.begin() as conn:
                for fact in facts:
                    # Determine target table based on source
                    if source == "world_bank":
                        conn.execute(
                            text("""
                                INSERT INTO world_bank_indicators 
                                (country_code, country_name, indicator_code, indicator_name, year, value, created_at)
                                VALUES (:country, :country_name, :code, :name, :year, :value, :created)
                                ON CONFLICT (country_code, indicator_code, year) DO NOTHING
                            """),
                            {
                                "country": "QAT",  # Always use 3-letter code for country_code column
                                "country_name": fact.get("country_name", "Qatar"),
                                "code": fact.get("indicator_code", fact.get("metric")),
                                "name": fact.get("indicator_name", fact.get("description", "")),
                                "year": fact.get("year", datetime.now().year),
                                "value": fact.get("value", 0.0),
                                "created": datetime.utcnow()
                            }
                        )
                    elif source == "ilo":
                        conn.execute(
                            text("""
                                INSERT INTO ilo_labour_data 
                                (country_code, indicator_code, year, value, sex, age_group, created_at)
                                VALUES (:country, :code, :year, :value, :sex, :age, :created)
                                ON CONFLICT (country_code, indicator_code, year, sex, age_group) DO NOTHING
                            """),
                            {
                                "country": fact.get("country", "QAT"),
                                "code": fact.get("indicator_code", fact.get("metric")),
                                "year": fact.get("year", datetime.now().year),
                                "value": fact.get("value", 0.0),
                                "sex": fact.get("sex", "Total"),
                                "age": fact.get("age_group", "Total"),
                                "created": datetime.utcnow()
                            }
                        )
                    elif source == "fao":
                        conn.execute(
                            text("""
                                INSERT INTO fao_data 
                                (country_code, indicator_code, indicator_name, year, value, unit, created_at)
                                VALUES (:country, :code, :name, :year, :value, :unit, :created)
                                ON CONFLICT (country_code, indicator_code, year) DO NOTHING
                            """),
                            {
                                "country": fact.get("country", "QAT"),
                                "code": fact.get("indicator_code", fact.get("metric")),
                                "name": fact.get("indicator_name", fact.get("description", "")),
                                "year": fact.get("year", datetime.now().year),
                                "value": fact.get("value", 0.0),
                                "unit": fact.get("unit", ""),
                                "created": datetime.utcnow()
                            }
                        )
        except Exception as e:
            logger.error(f"Failed to write {source} facts to PostgreSQL: {e}")
    
    async def close(self):
        """Close all API connectors"""
        if self.imf_connector:
            await self.imf_connector.close()
        if self.un_comtrade_connector:
            await self.un_comtrade_connector.close()
        if self.fred_connector:
            await self.fred_connector.close()
        if self.world_bank_connector:
            await self.world_bank_connector.close()


# Singleton instance
_complete_prefetch = None

def get_complete_prefetch() -> CompletePrefetchLayer:
    """Get or create complete prefetch layer."""
    global _complete_prefetch
    if _complete_prefetch is None:
        _complete_prefetch = CompletePrefetchLayer()
    return _complete_prefetch
