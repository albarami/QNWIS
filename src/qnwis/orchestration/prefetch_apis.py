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

# Safe printing helper to avoid UnicodeEncodeError on limited consoles
def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        sanitized = message.encode("ascii", errors="ignore").decode("ascii", errors="ignore")
        print(sanitized)

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


class CompletePrefetchLayer:
    """Prefetch data from ALL available sources for agent analysis."""
    
    def __init__(self):
        # Initialize API clients
        self.gcc_stat = GCCStatAPI()
        self.world_bank = WorldBankAPI()
        self.semantic_scholar = SemanticScholarAPI()
        
        # Get API keys from environment
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        
        _safe_print(f"🔑 Brave API: {'✅' if self.brave_api_key else '❌'}")
        _safe_print(f"🔑 Perplexity API: {'✅' if self.perplexity_api_key else '❌'}")
    
    async def fetch_all_sources(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch from ALL sources in parallel based on query keywords.
        Returns comprehensive fact list for agent analysis.
        """
        facts: List[Dict[str, Any]] = []
        query_lower = query.lower()
        tasks: List[Callable[[], Awaitable[List[Dict[str, Any]]]]] = []
        added_methods: set[str] = set()

        def add_task(factory: Callable[[], Awaitable[List[Dict[str, Any]]]], name: str) -> None:
            """Add coroutine factory if not already scheduled."""
            if name not in added_methods:
                tasks.append(factory)
                added_methods.add(name)

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
            add_task(self._fetch_mol_stub, "mol_stub")
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
    
    # ================== MoL LMIS (Stub until DNS/auth fixed) ==================
    
    async def _fetch_mol_stub(self) -> List[Dict[str, Any]]:
        """MoL LMIS stub data for Qatar labor market."""
        _safe_print("⚠️  MoL LMIS: Using stub data (awaiting API token)")
        
        return [
            {
                "metric": "qatar_unemployment_rate",
                "value": 0.1,
                "source": "MoL LMIS (stub)",
                "source_priority": 90,
                "confidence": 0.80,
                "raw_text": "Qatar unemployment: 0.1% (Q4 2024)",
                "timestamp": datetime.now().isoformat()
            },
            {
                "metric": "qatar_labour_force_participation",
                "value": 88.7,
                "source": "MoL LMIS (stub)",
                "source_priority": 90,
                "confidence": 0.80,
                "raw_text": "Labour force participation: 88.7%",
                "timestamp": datetime.now().isoformat()
            },
            {
                "metric": "qatar_tech_sector_employment",
                "value": 12400,
                "source": "MoL LMIS (stub)",
                "source_priority": 90,
                "confidence": 0.75,
                "raw_text": "Tech sector employment: 12,400 workers",
                "timestamp": datetime.now().isoformat()
            },
            {
                "metric": "qatar_tech_qatarization_current",
                "value": 8.2,
                "source": "MoL LMIS (stub)",
                "source_priority": 90,
                "confidence": 0.80,
                "raw_text": "Tech sector Qatarization: 8.2%",
                "timestamp": datetime.now().isoformat()
            },
            {
                "metric": "qatari_tech_graduates_annual",
                "value": 347,
                "source": "MoL Education Data (stub)",
                "source_priority": 85,
                "confidence": 0.70,
                "raw_text": "Annual Qatari tech graduates: 347",
                "timestamp": datetime.now().isoformat()
            },
        ]
    
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
        """Fetch from World Bank (CONFIRMED WORKING)."""
        try:
            _safe_print("✅ World Bank: Fetching Qatar GDP...")
            df = await self.world_bank.get_indicator(
                indicator="NY.GDP.MKTP.CD",
                country="QAT"
            )
            
            latest = df.iloc[0]
            
            return [{
                "metric": "qatar_gdp",
                "value": latest['value'],
                "source": "World Bank (live API)",
                "source_priority": 95,
                "confidence": 0.98,
                "raw_text": f"Qatar GDP: ${latest['value']:,.0f} ({latest['year']})",
                "timestamp": datetime.now().isoformat()
            }]
            
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
                        for paper in filtered[:3]:
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
                        await asyncio.sleep(1)
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
                        for paper in filtered[:3]:
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
                        await asyncio.sleep(1)
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


# Singleton instance
_complete_prefetch = None

def get_complete_prefetch() -> CompletePrefetchLayer:
    """Get or create complete prefetch layer."""
    global _complete_prefetch
    if _complete_prefetch is None:
        _complete_prefetch = CompletePrefetchLayer()
    return _complete_prefetch