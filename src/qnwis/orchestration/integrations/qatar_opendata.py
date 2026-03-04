"""Qatar Open Data, LMIS, GCC-STAT, regional, and knowledge graph data fetchers."""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MoL / PostgreSQL
# ---------------------------------------------------------------------------

async def fetch_mol_data(pg_engine) -> List[Dict[str, Any]]:
    """Fetch verified Qatar labor market data from PostgreSQL cache."""
    from sqlalchemy import text

    logger.info("MoL Data: Fetching verified data from PostgreSQL...")
    facts: List[Dict[str, Any]] = []
    try:
        with pg_engine.begin() as conn:
            indicators = [
                ("qatar_unemployment_rate", "SL.UEM.TOTL.ZS",
                 "Qatar unemployment: {0}% ({1})"),
                ("qatar_labour_force_participation", "SL.TLF.CACT.ZS",
                 "Labour force participation: {0}% ({1})"),
            ]
            for metric, code, fmt in indicators:
                result = conn.execute(text(
                    "SELECT value, year FROM world_bank_indicators "
                    "WHERE country_code = 'QAT' AND indicator_code = :ind "
                    "ORDER BY year DESC LIMIT 1"
                ), {"ind": code}).fetchone()
                if result:
                    facts.append({
                        "metric": metric, "value": float(result[0]), "year": result[1],
                        "source": "World Bank (PostgreSQL cache)",
                        "source_priority": 98, "confidence": 0.99,
                        "raw_text": fmt.format(result[0], result[1]),
                        "timestamp": datetime.now().isoformat(),
                    })

            result = conn.execute(text(
                "SELECT value, year FROM world_bank_indicators "
                "WHERE country_code = 'QAT' AND indicator_code = 'NY.GDP.MKTP.CD' "
                "ORDER BY year DESC LIMIT 1"
            )).fetchone()
            if result:
                gdp_b = float(result[0]) / 1e9
                facts.append({
                    "metric": "qatar_gdp_usd", "value": gdp_b, "year": result[1],
                    "source": "World Bank (PostgreSQL cache)",
                    "source_priority": 98, "confidence": 0.99,
                    "raw_text": f"Qatar GDP: ${gdp_b:.1f}B ({result[1]})",
                    "timestamp": datetime.now().isoformat(),
                })

        logger.info("Retrieved %d verified facts from PostgreSQL", len(facts))
    except Exception as e:
        logger.warning("PostgreSQL fetch error: %s", e)
    return facts


# ---------------------------------------------------------------------------
# GCC-STAT
# ---------------------------------------------------------------------------

async def fetch_gcc_stat(gcc_stat) -> List[Dict[str, Any]]:
    """Fetch from GCC-STAT (live API)."""
    try:
        logger.info("GCC-STAT: Fetching live data...")
        df = await gcc_stat.get_gcc_unemployment_rates()
        facts: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            slug = row["country"].lower().replace(" ", "_")
            facts.append({
                "metric": f"{slug}_unemployment_rate",
                "value": row["unemployment_rate"],
                "source": "GCC-STAT (live API)", "source_priority": 95,
                "confidence": 0.95,
                "raw_text": f"{row['country']} unemployment: {row['unemployment_rate']}%",
                "timestamp": datetime.now().isoformat(),
            })
            facts.append({
                "metric": f"{slug}_labour_force_participation",
                "value": row["labor_force_participation"],
                "source": "GCC-STAT (live API)", "source_priority": 95,
                "confidence": 0.95,
                "raw_text": f"{row['country']} LFPR: {row['labor_force_participation']}%",
                "timestamp": datetime.now().isoformat(),
            })
        logger.info("Retrieved %d facts from GCC-STAT", len(facts))
        return facts
    except Exception as e:
        logger.warning("GCC-STAT error: %s", e)
        return []


# ---------------------------------------------------------------------------
# UNCTAD / ILO
# ---------------------------------------------------------------------------

async def fetch_unctad_investment(
    unctad_connector, country: str = "QAT",
) -> List[Dict[str, Any]]:
    """Fetch UNCTAD FDI and investment data."""
    if not unctad_connector:
        return []
    try:
        logger.info("UNCTAD: Fetching investment and FDI data...")
        dashboard = await unctad_connector.get_investment_dashboard(country)
        facts: List[Dict[str, Any]] = []
        if dashboard and "error" not in dashboard:
            for indicator, data in dashboard.items():
                if isinstance(data, dict) and "latest_value" in data:
                    facts.append({
                        "metric": indicator, "value": data["latest_value"],
                        "year": data.get("latest_year"), "country": country,
                        "unit": data.get("unit", "USD millions"),
                        "source": "UNCTAD FDI Database", "source_priority": 97,
                        "confidence": 0.98,
                        "raw_text": f"{indicator}: {data['latest_value']} ({data.get('latest_year')})",
                        "timestamp": datetime.now().isoformat(),
                    })
        logger.info("Retrieved %d UNCTAD indicators", len(facts))
        return facts
    except Exception as e:
        logger.warning("UNCTAD error: %s", e)
        return []


async def fetch_ilo_benchmarks(
    ilo_connector, pg_engine, country: str = "QAT",
) -> List[Dict[str, Any]]:
    """Fetch ILO international labor benchmarks - CACHE-FIRST."""
    if not ilo_connector:
        return []
    try:
        from .world_bank import query_postgres_cache

        cached = query_postgres_cache(pg_engine, "ilo", country)
        if cached:
            logger.info("ILO: Using %d cached indicators from PostgreSQL", len(cached))
            return cached

        logger.info("ILO: Fetching international labor benchmarks...")
        employment = await ilo_connector.get_employment_stats(country)
        facts: List[Dict[str, Any]] = []
        if employment and "error" not in employment:
            facts.append({
                "metric": "employment_total",
                "value": employment.get("total_employed", 0),
                "year": employment.get("year", 2023), "country": country,
                "source": "ILO ILOSTAT", "source_priority": 97, "confidence": 0.98,
                "raw_text": f"Total employment: {employment.get('total_employed', 0)}",
                "timestamp": datetime.now().isoformat(),
            })
        return facts
    except Exception as e:
        logger.warning("ILO error: %s", e)
        return []


# ---------------------------------------------------------------------------
# LMIS Ministry of Labour
# ---------------------------------------------------------------------------

async def fetch_lmis_comprehensive(
    lmis_connector, lang: str = "en",
) -> List[Dict[str, Any]]:
    """Fetch comprehensive LMIS data from Ministry of Labour Qatar."""
    if not lmis_connector:
        return []
    try:
        logger.info("LMIS: Fetching official Qatar labor market data...")
        facts: List[Dict[str, Any]] = []
        endpoints = [
            ("qatar_main_indicator", "get_qatar_main_indicators", (lang,), 99),
            ("sector_growth_nds3", "get_sector_growth", ("NDS3", lang), 98),
            ("top_skills_sector", "get_top_skills_by_sector", ("NDS3", lang), 97),
            ("emerging_decaying_skills", "get_emerging_decaying_skills", (lang,), 96),
            ("expat_dominated_occupations", "get_expat_dominated_occupations", (lang,), 95),
            ("best_paid_occupations", "get_best_paid_occupations", (lang,), 94),
        ]
        for metric, method_name, args, priority in endpoints:
            try:
                method = getattr(lmis_connector, method_name, None)
                if method is None:
                    continue
                df = method(*args)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        facts.append({
                            "metric": metric, "data": row.to_dict(),
                            "source": "LMIS (Ministry of Labour Qatar)",
                            "source_type": "official_government",
                            "source_priority": priority,
                            "confidence": max(0.90, priority / 105),
                            "cached": False,
                        })
                    logger.info("   %s: %d records", metric, len(df))
            except Exception as e:
                logger.debug("   %s error: %s", metric, e)

        logger.info("LMIS TOTAL: %d official records retrieved", len(facts))
        return facts
    except Exception as e:
        logger.warning("LMIS comprehensive error: %s", e)
        return []


# ---------------------------------------------------------------------------
# UNWTO Tourism
# ---------------------------------------------------------------------------

async def fetch_unwto_tourism(
    unwto_connector, country: str = "QAT",
) -> List[Dict[str, Any]]:
    """Fetch UNWTO tourism statistics."""
    if not unwto_connector:
        return []
    try:
        logger.info("UNWTO: Fetching tourism statistics...")
        dashboard = await unwto_connector.get_tourism_dashboard(country)
        facts: List[Dict[str, Any]] = []
        if dashboard and "error" not in dashboard:
            for indicator, data in dashboard.items():
                if isinstance(data, dict) and "latest_value" in data:
                    facts.append({
                        "metric": indicator, "value": data["latest_value"],
                        "year": data.get("latest_year"), "country": country,
                        "source": "UNWTO Tourism Statistics", "source_priority": 95,
                        "confidence": 0.96,
                        "raw_text": f"{indicator}: {data['latest_value']} ({data.get('latest_year')})",
                        "timestamp": datetime.now().isoformat(),
                    })
        logger.info("Retrieved %d UNWTO indicators", len(facts))
        return facts
    except Exception as e:
        logger.warning("UNWTO error: %s", e)
        return []


# ---------------------------------------------------------------------------
# Arab Development Portal
# ---------------------------------------------------------------------------

async def fetch_adp_data(
    adp_connector, query: str, domain: str = "labor",
) -> List[Dict[str, Any]]:
    """Fetch data from Arab Development Portal (179K+ datasets)."""
    if not adp_connector:
        return []
    try:
        logger.info("ADP: Searching %s datasets for Qatar...", domain)
        datasets = await adp_connector.search_datasets(
            theme=domain, country="QAT", limit=20,
        )
        facts: List[Dict[str, Any]] = []
        if datasets:
            for ds in datasets[:10]:
                facts.append({
                    "metric": ds.get("title", "ADP Dataset"),
                    "value": ds.get("dataset_id"),
                    "description": ds.get("description", ""),
                    "source": f"Arab Development Portal ({domain})",
                    "source_priority": 92, "confidence": 0.90,
                    "raw_text": f"ADP Dataset: {ds.get('title', 'Unknown')}",
                    "timestamp": datetime.now().isoformat(),
                })
        return facts
    except Exception as e:
        logger.debug("ADP error (non-critical): %s", e)
        return []


# ---------------------------------------------------------------------------
# ESCWA Trade Data
# ---------------------------------------------------------------------------

async def fetch_escwa_trade(
    escwa_connector, query: str,
) -> List[Dict[str, Any]]:
    """Fetch trade data from UN ESCWA platform."""
    if not escwa_connector:
        return []
    try:
        logger.info("ESCWA: Fetching Qatar trade data...")
        exports_result = await escwa_connector.get_qatar_exports(year=2023)
        imports_result = await escwa_connector.get_qatar_imports(year=2023)
        facts: List[Dict[str, Any]] = []
        for result_data, flow_label in [
            (exports_result, "Export"), (imports_result, "Import"),
        ]:
            items = result_data.get("data", []) if result_data else []
            partner = result_data.get("partner", "World") if result_data else "World"
            for item in items[:10]:
                facts.append({
                    "metric": f"{flow_label}: {item.get('commodity_code', 'Total')}",
                    "value": item.get("value_usd"),
                    "year": item.get("year", 2023), "partner": partner,
                    "source": "UN ESCWA Trade Data", "source_priority": 93,
                    "confidence": 0.92,
                    "raw_text": f"Qatar {item.get('flow', flow_label.lower())} to {partner}",
                    "timestamp": datetime.now().isoformat(),
                })
        logger.info("Retrieved %d ESCWA trade data points", len(facts))
        return facts
    except Exception as e:
        logger.warning("ESCWA error: %s", e)
        return []


# ---------------------------------------------------------------------------
# Knowledge Graph
# ---------------------------------------------------------------------------

async def fetch_knowledge_graph_context(
    knowledge_graph, query: str,
) -> List[Dict[str, Any]]:
    """Fetch relevant context from knowledge graph for cross-domain reasoning."""
    if not knowledge_graph:
        return []
    facts: List[Dict[str, Any]] = []
    try:
        logger.info("Knowledge Graph: Finding related entities...")
        extracted = knowledge_graph.extract_entities_from_text(query)
        if not extracted:
            return []

        generic = {
            "artificial intelligence", "ai", "machine learning", "ml",
            "knowledge", "entity", "graph", "data", "information",
            "technology", "computer science", "algorithm",
        }
        seen: set = set()
        for entity_id in extracted[:5]:
            if str(entity_id).lower() in generic:
                continue
            related = knowledge_graph.get_related_entities(entity_id, max_hops=2)
            for related_id, edge_data in related[:3]:
                node = knowledge_graph.graph.nodes.get(related_id, {})
                name = node.get("name", str(related_id))
                if name.lower() in generic or len(name) < 3:
                    continue
                key = name.lower().strip()
                if key in seen:
                    continue
                seen.add(key)
                etype = node.get("type", "unknown")
                if etype.lower() in ("unknown", "none", ""):
                    continue
                facts.append({
                    "metric": f"Related: {name}", "entity_type": etype,
                    "relationship": edge_data.get("relation_type", "related_to"),
                    "source_entity": entity_id, "source": "Knowledge Graph",
                    "source_priority": 70,
                    "confidence": min(edge_data.get("confidence", 0.7), 0.75),
                    "raw_text": (
                        f"Knowledge Graph: {entity_id} -> "
                        f"{edge_data.get('relation_type', 'relates to')} -> {name}"
                    ),
                    "timestamp": datetime.now().isoformat(),
                })
                if len(facts) >= 10:
                    break
            if len(facts) >= 10:
                break
        logger.info("Retrieved %d knowledge graph relationships", len(facts))
    except Exception as e:
        logger.warning("Knowledge Graph error: %s", e)
    return facts
