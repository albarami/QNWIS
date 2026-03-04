"""Shared HTTP helpers, constants, and API client wrappers for integrations."""
import asyncio
import functools
import json
import logging
import os
from typing import Any, Dict, List

import aiohttp
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM-BASED SMART QUERY GENERATION
# ---------------------------------------------------------------------------

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
    """Use LLM to generate contextually relevant search queries."""
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    fallback = {
        "academic_queries": [question[:100]],
        "realtime_queries": [question[:100]],
        "key_concepts": [],
        "data_needs": question,
    }
    if not endpoint or not api_key:
        return fallback
    try:
        url = f"{endpoint}/openai/deployments/gpt-5-chat/chat/completions?api-version=2024-08-01-preview"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json={
                    "messages": [
                        {"role": "system", "content": "You are a research query optimizer. Always respond with valid JSON."},
                        {"role": "user", "content": SMART_QUERY_PROMPT.format(question=question)},
                    ],
                    "max_tokens": 400,
                    "temperature": 0.2,
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    result = json.loads(content.strip())
                    logger.info("Smart queries generated: %s", result.get("academic_queries", [])[:2])
                    return result
    except Exception as e:
        logger.warning("Smart query generation failed: %s", e)
    return fallback


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

CRITICAL_DATA_CHECKLISTS: Dict[str, Dict[str, list]] = {
    "food_security": {
        "required": [
            "current_food_import_costs", "food_self_sufficiency_percentage",
            "agricultural_water_consumption", "energy_costs_for_agriculture",
        ],
        "nice_to_have": ["gcc_food_security_investments", "vertical_farming_costs"],
    },
    "labor_market": {
        "required": [
            "unemployment_rate", "labor_force_participation",
            "qatarization_rates", "sector_employment_distribution",
        ],
        "nice_to_have": ["wage_levels", "skills_gaps"],
    },
    "investment_decision": {
        "required": [
            "project_costs", "comparable_project_outcomes",
            "risk_factors", "economic_impact_estimates",
        ],
        "nice_to_have": ["financing_options", "public_opinion"],
    },
}

TARGETED_SEARCH_STRATEGIES: Dict[str, list] = {
    "current_food_import_costs": [
        ("world_bank", "NE.IMP.GNFS.CD", {"country": "QAT"}),
        ("perplexity", "Qatar annual food import costs 2024", "cost_data"),
        ("brave_search", "Qatar food import statistics 2024 billion"),
    ],
    "food_self_sufficiency_percentage": [
        ("qatar_open_data", "food production agriculture domestic"),
        ("perplexity", "Qatar food self-sufficiency rate percentage 2024", "statistics"),
        ("gcc_stat", "agriculture production value qatar"),
    ],
    "energy_costs_for_agriculture": [
        ("world_bank", "EG.ELC.COST.KH", {"country": "QAT"}),
        ("perplexity", "Qatar electricity cost industrial agriculture 2024", "cost_data"),
        ("brave_search", "qatar energy subsidies agriculture sector"),
    ],
    "agricultural_water_consumption": [
        ("world_bank", "ER.H2O.FWAG.ZS", {"country": "QAT"}),
        ("perplexity", "Qatar water consumption agriculture sector cubic meters", "statistics"),
        ("gcc_stat", "water consumption by sector qatar"),
    ],
    "vertical_farming_costs": [
        ("perplexity", "vertical farming production cost per kilogram 2024", "cost_data"),
        ("semantic_scholar", "controlled environment agriculture economics cost analysis"),
        ("brave_search", "vertical farming energy costs middle east UAE"),
    ],
    "gcc_food_security_investments": [
        ("gcc_stat", "agriculture investment government spending"),
        ("perplexity", "GCC countries food security investment 2024 Saudi UAE", "comparative"),
        ("brave_search", "GCC food security megaprojects 2024"),
    ],
}

PERPLEXITY_PROMPT_TEMPLATES: Dict[str, str] = {
    "cost_data": (
        "Find the most recent, specific cost data for: {query}\n"
        "REQUIRED FORMAT:\n"
        "- Exact figures with currency (USD, QAR, etc.)\n"
        "- Time period (year/quarter/month)\n"
        "- Authoritative source citation (World Bank, government, industry report)\n"
        "CRITICAL: If specific data not available, respond \"No specific data found\" rather than estimating.\n"
        "Do NOT provide approximate figures without clear source attribution."
    ),
    "statistics": (
        "Find official statistics for: {query}\n"
        "REQUIRED FORMAT:\n"
        "- Exact numbers/percentages with precision\n"
        "- Official source (government statistics, World Bank, IMF, UN, GCC-STAT)\n"
        "- Year/period of data\n"
        "- Methodology if available\n"
        "PRIORITIZE: Government statistics > International organizations > "
        "Peer-reviewed research > Industry reports > News"
    ),
    "comparative": (
        "Find comparative data for: {query}\n"
        "REQUIRED FORMAT:\n"
        "- Multiple countries/entities with SAME METRICS\n"
        "- Same time period for fair comparison\n"
        "- Clear data sources for each entity\n"
        "- Note any methodology differences\n"
        "If not directly comparable, explain why and what adjustments would be needed."
    ),
}


def classify_query_for_extraction(query: str) -> List[str]:
    """Determine what types of data we need."""
    ql = query.lower()
    types: List[str] = []
    if any(kw in ql for kw in ["food", "agriculture", "farming", "self-sufficiency"]):
        types.append("food_security")
    if any(kw in ql for kw in ["employment", "labor", "workforce", "qatarization"]):
        types.append("labor_market")
    if any(kw in ql for kw in ["invest", "project", "megaproject", "should we"]):
        types.append("investment_decision")
    return types if types else ["general"]


# ---------------------------------------------------------------------------
# API CLIENT WRAPPERS (with legacy fallbacks)
# ---------------------------------------------------------------------------

try:
    from src.data.apis.gcc_stat import GCCStatAPI  # type: ignore
except ImportError:  # pragma: no cover
    from src.data.apis.gcc_stat import GCCStatClient

    class GCCStatAPI(GCCStatClient):  # type: ignore[no-redef]
        async def get_gcc_unemployment_rates(self, *args, **kwargs):
            return await asyncio.to_thread(self.get_unemployment_comparison, *args, **kwargs)


try:
    from src.data.apis.world_bank import WorldBankAPI  # type: ignore
except ImportError:  # pragma: no cover
    from src.data.apis.world_bank import UDCGlobalDataIntegrator

    class WorldBankAPI(UDCGlobalDataIntegrator):  # type: ignore[no-redef]
        async def get_indicator(self, *, indicator: str, country: str, **kwargs):
            call = functools.partial(super().get_indicator, indicator, countries=[country], **kwargs)
            return await asyncio.to_thread(call)


try:
    from src.data.apis.semantic_scholar import SemanticScholarAPI  # type: ignore
except ImportError:  # pragma: no cover
    from src.data.apis import semantic_scholar as _semantic_scholar_module

    class _SemanticScholarAPIMixin:
        async def search_papers(
            self, query: str, fields: str | None = None,
            year_filter: str | None = None, limit: int = 10,
        ) -> List[Dict[str, Any]]:
            effective_fields = fields or "title,year,abstract,citationCount,authors,url,paperId"
            logger.info("Semantic Scholar: Searching '%s' (limit %d)", query, limit)
            return await asyncio.to_thread(
                _semantic_scholar_module.search_papers, query, effective_fields, year_filter, limit,
            )

    class SemanticScholarAPI(_SemanticScholarAPIMixin):  # type: ignore[no-redef]
        ...


try:
    from src.data.apis.qatar_opendata import QatarOpenDataScraperV2  # type: ignore
except ImportError:

    class QatarOpenDataScraperV2:  # type: ignore[no-redef]
        def search_catalog(self, *args, **kwargs):
            return []


class QatarOpenDataAPI(QatarOpenDataScraperV2):
    async def search_datasets(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
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
        logger.debug("Qatar Open Data: searching for '%s'", query)
        datasets = await self.search_datasets(query, limit=5)
        facts: list[dict[str, Any]] = []
        for dataset in datasets:
            meta = dataset.get("metas", {}).get("default", {})
            facts.append({
                "metric": meta.get("title", dataset.get("dataset_id", "dataset")),
                "value": (meta.get("description") or "")[:200],
                "source": "Qatar Open Data",
                "data_type": "open_data",
                "confidence": 0.65,
            })
        return facts
