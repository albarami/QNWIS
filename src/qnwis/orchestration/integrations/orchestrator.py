"""Main CompletePrefetchLayer orchestrator - coordinates all data source integrations."""
import asyncio
import importlib
import logging
import os
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List

from .brave import fetch_brave_economic
from .common import (
    CRITICAL_DATA_CHECKLISTS,
    TARGETED_SEARCH_STRATEGIES,
    GCCStatAPI,
    QatarOpenDataAPI,
    SemanticScholarAPI,
    classify_query_for_extraction,
)
from .perplexity import (
    fetch_perplexity_energy,
    fetch_perplexity_food_security,
    fetch_perplexity_gcc,
    fetch_perplexity_policy,
    fetch_perplexity_smart,
    fetch_perplexity_targeted,
)
from .qatar_opendata import (
    fetch_adp_data,
    fetch_escwa_trade,
    fetch_gcc_stat,
    fetch_ilo_benchmarks,
    fetch_knowledge_graph_context,
    fetch_lmis_comprehensive,
    fetch_mol_data,
    fetch_unctad_investment,
    fetch_unwto_tourism,
)
from .semantic_scholar import (
    fetch_semantic_scholar_labor,
    fetch_semantic_scholar_policy,
    fetch_semantic_scholar_smart,
)
from .world_bank import (
    fetch_comtrade_food,
    fetch_fao_food_security,
    fetch_fred_benchmarks,
    fetch_iea_energy,
    fetch_imf_dashboard,
    fetch_world_bank,
    fetch_world_bank_dashboard,
)

logger = logging.getLogger(__name__)


def _try_import(module: str, cls: str):
    """Try importing a class; return None on failure."""
    try:
        mod = importlib.import_module(module)
        return getattr(mod, cls)
    except (ImportError, AttributeError):
        return None


def _kw(query_lower: str, keywords: list) -> bool:
    """Check if any keyword appears in the lowered query."""
    return any(kw in query_lower for kw in keywords)


class CompletePrefetchLayer:
    """Prefetch data from ALL available sources for agent analysis."""

    def __init__(self):
        self.gcc_stat = GCCStatAPI()
        self.semantic_scholar = SemanticScholarAPI()
        self.qatar_open_data = QatarOpenDataAPI()

        _specs = [
            ("src.data.apis.imf_api", "IMFConnector", "imf_connector"),
            ("src.data.apis.world_bank_api", "WorldBankAPI", "world_bank_connector"),
            ("src.data.apis.unctad_api", "UNCTADAPI", "unctad_connector"),
            ("src.data.apis.ilo_api", "ILOAPI", "ilo_connector"),
            ("src.data.apis.fao_api", "FAOAPI", "fao_connector"),
            ("src.data.apis.unwto_api", "UNWTOAPI", "unwto_connector"),
            ("src.data.apis.iea_api", "IEAAPI", "iea_connector"),
            ("src.data.apis.arab_dev_portal", "ArabDevPortalClient", "adp_connector"),
            ("src.data.apis.escwa_etdp", "ESCWATradeAPI", "escwa_connector"),
        ]
        for module, cls_name, attr in _specs:
            Cls = _try_import(module, cls_name)
            setattr(self, attr, Cls() if Cls else None)

        self.un_comtrade_connector = None
        self.fred_connector = None

        LMISAPIClient = _try_import("src.data.apis.lmis_mol_api", "LMISAPIClient")
        self.lmis_connector = LMISAPIClient() if LMISAPIClient else None

        self._knowledge_graph = None
        try:
            from pathlib import Path

            from ..knowledge.graph_builder import QNWISKnowledgeGraph
            kg_path = Path("data/knowledge_graph.json")
            if kg_path.exists():
                self._knowledge_graph = QNWISKnowledgeGraph()
                self._knowledge_graph.load(kg_path)
        except ImportError:
            ...

        self.world_bank = self.world_bank_connector
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

        from ..data.deterministic.engine import get_engine
        self.pg_engine = get_engine()

        for name, ok in [
            ("Brave API", bool(self.brave_api_key)),
            ("Perplexity API", bool(self.perplexity_api_key)),
            ("Semantic Scholar", True),
            ("IMF", bool(self.imf_connector)),
            ("World Bank", bool(self.world_bank_connector)),
            ("UNCTAD", bool(self.unctad_connector)),
            ("ILO", bool(self.ilo_connector)),
            ("FAO", bool(self.fao_connector)),
            ("UNWTO", bool(self.unwto_connector)),
            ("IEA", bool(self.iea_connector)),
            ("ADP", bool(self.adp_connector)),
            ("ESCWA", bool(self.escwa_connector)),
            ("LMIS MoL", bool(self.lmis_connector)),
            ("Knowledge Graph", bool(self._knowledge_graph)),
            ("PostgreSQL", True),
        ]:
            logger.info("%s: %s", name, "available" if ok else "unavailable")

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    async def fetch_all_sources(self, query: str) -> List[Dict[str, Any]]:
        """Fetch from ALL sources in parallel based on query keywords."""
        logger.warning("FETCH_ALL_SOURCES QUERY LENGTH: %d", len(query))
        logger.warning("FETCH_ALL_SOURCES QUERY FIRST 200 CHARS: %s", repr(query[:200]))

        facts: List[Dict[str, Any]] = []
        ql = query.lower()
        tasks: List[Callable[[], Awaitable[List[Dict[str, Any]]]]] = []
        added: set = set()

        def add(factory, name: str):
            if name not in added:
                tasks.append(factory)
                added.add(name)
                logger.info("Added task: %s", name)

        # --- TIER 1: Free APIs ---
        if _kw(ql, ["gdp", "economic growth", "fiscal", "government debt",
                     "inflation", "unemployment", "current account", "deficit",
                     "revenue", "expenditure", "debt", "balance"]):
            add(lambda: fetch_imf_dashboard(self.imf_connector), "imf_dashboard")

        if _kw(ql, ["food", "import", "trade", "self-sufficiency", "agriculture",
                     "meat", "dairy", "vegetables", "cereals", "commodity", "farming"]):
            add(lambda: fetch_comtrade_food(self.un_comtrade_connector), "comtrade_food")

        if _kw(ql, ["united states", "usa", "us ", "american", "federal reserve",
                     "compare", "benchmark", "global", "international"]):
            add(lambda: fetch_fred_benchmarks(self.fred_connector), "fred_benchmarks")

        # --- World Bank (128-indicator dashboard) ---
        if _kw(ql, [
            "sector", "tourism", "manufacturing", "services", "industry",
            "infrastructure", "education", "health", "digital", "internet",
            "roads", "human capital", "enrollment", "life expectancy",
            "savings", "investment climate", "industrial", "factory",
            "production", "competitiveness", "export", "value-add",
            "value added", "industrial zone", "plant", "processing",
            "assembly", "metro", "transport", "railway", "rail", "highway",
            "port", "airport", "construction", "public works", "utilities",
            "water", "electricity", "telecom", "logistics", "connectivity",
            "broadband", "energy", "renewable", "solar", "power", "oil",
            "gas", "lng", "petroleum", "emission", "carbon", "fossil",
            "food", "agriculture", "farming", "self-sufficiency",
            "agricultural", "food security", "import dependency",
        ]):
            add(lambda: fetch_world_bank_dashboard(self.world_bank_connector, self.pg_engine),
                "world_bank_dashboard")

        if _kw(ql, ["investment", "fdi", "foreign direct", "capital flows",
                     "portfolio", "inflows", "outflows", "investor"]):
            add(lambda: fetch_unctad_investment(self.unctad_connector), "unctad_investment")

        if _kw(ql, ["international", "benchmark", "gcc comparison", "global",
                     "regional", "wage comparison", "labor standards"]):
            add(lambda: fetch_ilo_benchmarks(self.ilo_connector, self.pg_engine), "ilo_benchmarks")

        # --- LMIS (official government) ---
        if _kw(ql, [
            "labor", "labour", "employment", "workforce", "worker",
            "qatarization", "qatari", "expat", "expatriate", "skills",
            "occupation", "sector", "salary", "wage", "sme", "business",
            "nationalization", "job", "career", "training", "education",
            "human capital", "talent", "recruitment", "hiring",
            "qatar", "ministry", "mol",
        ]):
            add(lambda: fetch_lmis_comprehensive(self.lmis_connector), "lmis_comprehensive")

        # --- FAO + Perplexity food security ---
        if _kw(ql, ["food", "agriculture", "farming", "self-sufficiency",
                     "imports", "crops", "agricultural", "food security"]):
            add(lambda: fetch_fao_food_security(self.fao_connector, self.pg_engine),
                "fao_food_security")
            if self.perplexity_api_key:
                add(lambda: fetch_perplexity_food_security(self.perplexity_api_key, query),
                    "perplexity_food_security")

        if _kw(ql, ["tourism", "tourist", "visitors", "hotels", "hospitality",
                     "accommodation", "travel", "arrivals"]):
            add(lambda: fetch_unwto_tourism(self.unwto_connector), "unwto_tourism")

        # --- IEA + Perplexity energy ---
        if _kw(ql, ["energy", "renewable", "solar", "power", "electricity",
                     "transition", "wind", "clean energy", "carbon",
                     "oil", "gas", "lng", "natural gas", "petroleum",
                     "hydrocarbon", "fossil fuel", "crude", "refinery",
                     "emission", "co2"]):
            add(lambda: fetch_iea_energy(self.iea_connector, self.pg_engine), "iea_energy")
            if self.perplexity_api_key:
                add(lambda: fetch_perplexity_energy(self.perplexity_api_key, query),
                    "perplexity_energy")

        # --- Labor market sources ---
        if _kw(ql, [
            "unemployment", "employment", "labor", "labour", "workforce",
            "qatarization", "qatarisation", "nationalization", "nationalisation",
            "jobs", "workers", "employees", "staff", "personnel", "qatari",
            "nationals", "citizens", "expat", "expatriate", "tech",
            "technology", "sector", "industry", "mandate", "policy",
            "reform", "target",
        ]):
            add(lambda: fetch_mol_data(self.pg_engine), "mol_data")
            add(lambda: fetch_gcc_stat(self.gcc_stat), "gcc_stat")
            add(lambda: fetch_semantic_scholar_labor(query), "semantic_labor")

        # --- Economic / GDP ---
        if _kw(ql, ["economic", "economy", "gdp", "growth", "investment",
                     "sector", "industry", "business", "market", "development",
                     "finance", "financial"]):
            add(lambda: fetch_world_bank(self.world_bank_connector), "world_bank")
            if self.brave_api_key:
                add(lambda: fetch_brave_economic(self.brave_api_key, query), "brave_economic")

        # --- Regional / GCC ---
        if _kw(ql, ["gcc", "gulf", "regional", "region", "saudi", "uae",
                     "bahrain", "kuwait", "oman", "emirates", "compare",
                     "comparison", "benchmark", "versus", "qatari", "qatar"]):
            add(lambda: fetch_gcc_stat(self.gcc_stat), "gcc_stat")
            if self.perplexity_api_key:
                add(lambda: fetch_perplexity_gcc(self.perplexity_api_key, query),
                    "perplexity_gcc")

        # --- Policy / Strategy ---
        if _kw(ql, [
            "policy", "policies", "strategy", "strategic", "mandate",
            "mandating", "require", "requirement", "reform", "reforms",
            "regulation", "law", "vision", "2030", "plan", "planning",
            "implement", "implementation", "feasibility", "target",
            "goal", "objective",
        ]):
            add(lambda: fetch_semantic_scholar_policy(query), "semantic_policy")
            if self.perplexity_api_key:
                add(lambda: fetch_perplexity_policy(self.perplexity_api_key, query),
                    "perplexity_policy")

        # --- Trade / Commerce ---
        if _kw(ql, ["trade", "export", "import", "commerce", "tariff",
                     "customs", "goods", "commodity", "shipping", "logistics",
                     "supply chain", "bilateral"]):
            if self.escwa_connector:
                add(lambda: fetch_escwa_trade(self.escwa_connector, query), "escwa_trade")

        # --- Arab World / Regional ---
        if _kw(ql, ["arab", "mena", "middle east", "regional", "gcc", "gulf",
                     "hdi", "sdg", "development", "benchmark"]):
            if self.adp_connector:
                adp_domain = "labor"
                for d, kws in [
                    ("trade", ["trade", "export", "import"]),
                    ("health", ["health", "medical", "hospital"]),
                    ("education", ["education", "school", "university"]),
                    ("energy", ["energy", "oil", "gas", "power"]),
                    ("tourism", ["tourism", "travel", "hotel"]),
                ]:
                    if any(w in ql for w in kws):
                        adp_domain = d
                        break
                add(lambda d=adp_domain: fetch_adp_data(self.adp_connector, query, d),
                    f"adp_{adp_domain}")

        # --- Knowledge Graph ---
        if self._knowledge_graph and _kw(ql, [
            "impact", "affect", "relationship", "connection", "cause",
            "effect", "consequence", "lead to", "result in", "depend",
            "influence", "sector", "cross", "multi",
        ]):
            add(lambda: fetch_knowledge_graph_context(self._knowledge_graph, query),
                "knowledge_graph")

        # --- Always-on: smart context-aware fetching ---
        add(lambda: fetch_semantic_scholar_smart(query), "semantic_smart")
        if self.perplexity_api_key:
            add(lambda: fetch_perplexity_smart(self.perplexity_api_key, query),
                "perplexity_smart")

        if tasks:
            logger.info("Executing %d unique parallel API calls...", len(tasks))
            coros = [factory() for factory in tasks]
            results = await asyncio.gather(*coros, return_exceptions=True)
            for result in results:
                if isinstance(result, list) and not isinstance(result, Exception):
                    facts.extend(result)
                elif isinstance(result, Exception):
                    logger.warning("Task failed: %s", result)

        logger.info("Total facts extracted: %d", len(facts))
        return facts

    # ------------------------------------------------------------------
    # Multi-pass gap-filling
    # ------------------------------------------------------------------

    async def fetch_all_sources_with_gaps(self, query: str) -> Dict[str, Any]:
        """Multi-pass extraction that identifies and fills critical data gaps."""
        from ..data_quality import calculate_data_quality, identify_missing_data

        query_types = classify_query_for_extraction(query)
        required_data: list = []
        for qtype in query_types:
            if qtype in CRITICAL_DATA_CHECKLISTS:
                required_data.extend(CRITICAL_DATA_CHECKLISTS[qtype]["required"])

        structured_facts = await self.fetch_all_sources(query)
        data_gaps = identify_missing_data(structured_facts, required_data)

        if data_gaps:
            logger.info("CRITICAL DATA GAPS DETECTED: %s", data_gaps)
            for gap in data_gaps:
                strategies = TARGETED_SEARCH_STRATEGIES.get(gap, [])
                for strategy in strategies:
                    try:
                        additional = await self._execute_targeted_search(gap, strategy)
                        if additional:
                            structured_facts.extend(additional)
                    except Exception as e:
                        logger.debug("Failed strategy %s for %s: %s", strategy, gap, e)

        remaining_gaps = identify_missing_data(structured_facts, required_data)
        quality_score = calculate_data_quality(structured_facts, required_data)

        return {
            "extracted_facts": structured_facts,
            "data_quality_score": quality_score,
            "critical_gaps": remaining_gaps,
            "total_facts_extracted": len(structured_facts),
        }

    async def _execute_targeted_search(
        self, data_gap: str, strategy: tuple,
    ) -> List[Dict[str, Any]]:
        """Execute a specific targeted search strategy."""
        source = strategy[0]
        query_or_id = strategy[1]
        params_or_type = strategy[2] if len(strategy) > 2 else {}
        results: List[Dict[str, Any]] = []

        try:
            if source == "world_bank":
                params = params_or_type if isinstance(params_or_type, dict) else {}
                country = params.get("country", "QAT")
                df = await self.world_bank.get_indicator(
                    indicator=query_or_id, country=country,
                )
                if not df.empty:
                    latest = df.iloc[0]
                    results.append({
                        "metric": data_gap, "value": latest["value"],
                        "source": "World Bank (Targeted)", "data_type": data_gap,
                        "confidence": 0.9, "timestamp": datetime.now().isoformat(),
                    })

            elif source == "perplexity":
                search_type = params_or_type if isinstance(params_or_type, str) else "general"
                results = await fetch_perplexity_targeted(
                    self.perplexity_api_key, query_or_id, search_type,
                )
                for res in results:
                    res["data_type"] = data_gap

            elif source == "brave_search":
                if self.brave_api_key:
                    import aiohttp
                    url = "https://api.search.brave.com/res/v1/web/search"
                    headers = {"Accept": "application/json",
                               "X-Subscription-Token": self.brave_api_key}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers,
                                               params={"q": query_or_id, "count": 5}) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                for r in data.get("web", {}).get("results", [])[:1]:
                                    results.append({
                                        "metric": data_gap, "value": r.get("title"),
                                        "source": "Brave Search (Targeted)",
                                        "data_type": data_gap, "confidence": 0.7,
                                        "raw_text": r.get("description", ""),
                                        "timestamp": datetime.now().isoformat(),
                                    })

            elif source == "qatar_open_data":
                if hasattr(self.qatar_open_data, "simple_search"):
                    od_results = await self.qatar_open_data.simple_search(query_or_id)
                    for item in od_results:
                        results.append({
                            "metric": item.get("metric", data_gap),
                            "value": item.get("value"),
                            "source": item.get("source", "Qatar Open Data"),
                            "data_type": data_gap,
                            "confidence": item.get("confidence", 0.6),
                        })

            elif source == "gcc_stat":
                if hasattr(self.gcc_stat, "get_labour_market_indicators"):
                    df = await asyncio.to_thread(self.gcc_stat.get_labour_market_indicators)
                    if hasattr(df, "head"):
                        for row in df.head(3).to_dict(orient="records"):
                            results.append({
                                "metric": data_gap, "value": row,
                                "source": "GCC-STAT Synthetic",
                                "data_type": data_gap, "confidence": 0.7,
                            })

        except Exception as e:
            logger.debug("Targeted search error (%s): %s", source, e)

        return results

    async def close(self):
        """Close all API connectors."""
        for attr in ("imf_connector", "un_comtrade_connector",
                     "fred_connector", "world_bank_connector"):
            connector = getattr(self, attr, None)
            if connector and hasattr(connector, "close"):
                await connector.close()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_complete_prefetch = None


def get_complete_prefetch() -> CompletePrefetchLayer:
    """Get or create complete prefetch layer."""
    global _complete_prefetch
    if _complete_prefetch is None:
        _complete_prefetch = CompletePrefetchLayer()
    return _complete_prefetch
