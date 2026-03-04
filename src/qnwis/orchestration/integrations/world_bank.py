"""World Bank, IMF, FRED, Comtrade fetchers and PostgreSQL cache helpers."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PostgreSQL cache helpers
# ---------------------------------------------------------------------------

def query_postgres_cache(pg_engine, source: str, country: str = "QAT") -> List[Dict]:
    """Query PostgreSQL cache BEFORE calling APIs (<100ms vs minutes)."""
    from sqlalchemy import text

    try:
        with pg_engine.connect() as conn:
            if source == "world_bank":
                result = conn.execute(text(
                    "SELECT indicator_code, indicator_name, year, value, country_name "
                    "FROM world_bank_indicators WHERE country_code = :country ORDER BY year DESC"
                ), {"country": country})
                return [{
                    "metric": r.indicator_code, "indicator_code": r.indicator_code,
                    "indicator_name": r.indicator_name, "description": r.indicator_name,
                    "year": r.year, "value": float(r.value), "country": r.country_name,
                    "country_name": r.country_name, "source": "World Bank (PostgreSQL cache)",
                    "source_priority": 98, "confidence": 0.99, "cached": True,
                    "raw_text": f"{r.indicator_name}: {r.value} ({r.year})",
                    "timestamp": datetime.now().isoformat(),
                } for r in result]

            if source == "ilo":
                result = conn.execute(text(
                    "SELECT indicator_code, indicator_name, year, value, country_name, sex, age_group "
                    "FROM ilo_labour_data WHERE country_code = :country ORDER BY year DESC"
                ), {"country": country})
                return [{
                    "metric": r.indicator_code, "indicator_code": r.indicator_code,
                    "indicator_name": r.indicator_name, "description": r.indicator_name,
                    "year": r.year, "value": float(r.value), "country": r.country_name,
                    "country_name": r.country_name, "sex": r.sex, "age_group": r.age_group,
                    "source": "ILO (PostgreSQL cache)", "source_priority": 98,
                    "confidence": 0.99, "cached": True,
                    "timestamp": datetime.now().isoformat(),
                } for r in result]
    except Exception as e:
        logger.error("Failed to query PostgreSQL cache for %s: %s", source, e)
    return []


def write_facts_to_postgres(pg_engine, facts: List[Dict], source: str) -> None:
    """Write prefetched facts to PostgreSQL for caching."""
    from sqlalchemy import text

    if not facts:
        return
    try:
        with pg_engine.begin() as conn:
            for fact in facts:
                if source == "world_bank":
                    conn.execute(text(
                        "INSERT INTO world_bank_indicators "
                        "(country_code, country_name, indicator_code, indicator_name, year, value, created_at) "
                        "VALUES (:country, :country_name, :code, :name, :year, :value, :created) "
                        "ON CONFLICT (country_code, indicator_code, year) DO NOTHING"
                    ), {
                        "country": "QAT",
                        "country_name": fact.get("country_name", "Qatar"),
                        "code": fact.get("indicator_code", fact.get("metric")),
                        "name": fact.get("indicator_name", fact.get("description", "")),
                        "year": fact.get("year", datetime.now().year),
                        "value": fact.get("value", 0.0),
                        "created": datetime.utcnow(),
                    })
                elif source == "ilo":
                    conn.execute(text(
                        "INSERT INTO ilo_labour_data "
                        "(country_code, indicator_code, year, value, sex, age_group, created_at) "
                        "VALUES (:country, :code, :year, :value, :sex, :age, :created) "
                        "ON CONFLICT (country_code, indicator_code, year, sex, age_group) DO NOTHING"
                    ), {
                        "country": fact.get("country", "QAT"),
                        "code": fact.get("indicator_code", fact.get("metric")),
                        "year": fact.get("year", datetime.now().year),
                        "value": fact.get("value", 0.0),
                        "sex": fact.get("sex", "Total"),
                        "age": fact.get("age_group", "Total"),
                        "created": datetime.utcnow(),
                    })
                elif source == "fao":
                    conn.execute(text(
                        "INSERT INTO fao_data "
                        "(country_code, indicator_code, indicator_name, year, value, unit, created_at) "
                        "VALUES (:country, :code, :name, :year, :value, :unit, :created) "
                        "ON CONFLICT (country_code, indicator_code, year) DO NOTHING"
                    ), {
                        "country": fact.get("country", "QAT"),
                        "code": fact.get("indicator_code", fact.get("metric")),
                        "name": fact.get("indicator_name", fact.get("description", "")),
                        "year": fact.get("year", datetime.now().year),
                        "value": fact.get("value", 0.0),
                        "unit": fact.get("unit", ""),
                        "created": datetime.utcnow(),
                    })
    except Exception as e:
        logger.error("Failed to write %s facts to PostgreSQL: %s", source, e)


# ---------------------------------------------------------------------------
# World Bank
# ---------------------------------------------------------------------------

async def fetch_world_bank(world_bank_connector) -> List[Dict[str, Any]]:
    """Legacy World Bank GDP fetch (use fetch_world_bank_dashboard instead)."""
    if not world_bank_connector:
        return []
    try:
        logger.info("World Bank: Fetching Qatar GDP (legacy)...")
        data = await world_bank_connector.get_indicator(
            indicator_code="NY.GDP.MKTP.CD", country_code="QAT",
        )
        if "latest_value" in data and data["latest_value"]:
            return [{
                "metric": "qatar_gdp", "value": data["latest_value"],
                "year": data.get("latest_year"), "source": "World Bank (live API)",
                "source_priority": 95, "confidence": 0.98,
                "raw_text": f"Qatar GDP: ${data['latest_value']:,.0f} ({data.get('latest_year', 'N/A')})",
                "timestamp": datetime.now().isoformat(),
            }]
        return []
    except Exception as e:
        logger.warning("World Bank error: %s", e)
        return []


async def fetch_world_bank_dashboard(world_bank_connector, pg_engine) -> List[Dict[str, Any]]:
    """Fetch Qatar dashboard from World Bank - CACHE-FIRST STRATEGY."""
    if not world_bank_connector:
        logger.debug("World Bank connector not available")
        return []
    try:
        cached_facts = query_postgres_cache(pg_engine, "world_bank", "QAT")
        if cached_facts and len(cached_facts) >= 100:
            suspicious = [
                f for f in cached_facts
                if "UEM" in str(f.get("metric", "")) and f.get("value", 0) > 5
            ]
            if not suspicious:
                logger.info("World Bank: Using %d cached indicators (<100ms)", len(cached_facts))
                return cached_facts
            logger.info("World Bank: Cache has suspicious values - refreshing from API")

        logger.info("World Bank: Cache miss, fetching from API...")
        sector_gdp = await world_bank_connector.get_sector_gdp_breakdown("QAT")
        facts: List[Dict[str, Any]] = []
        if "sector_breakdown" in sector_gdp:
            for sector_name, data in sector_gdp["sector_breakdown"].items():
                if "percentage_of_gdp" in data:
                    facts.append({
                        "metric": f"{sector_name.lower()}_gdp_percentage",
                        "value": data["percentage_of_gdp"], "sector": sector_name,
                        "source": "World Bank Indicators API", "source_priority": 98,
                        "confidence": 0.99,
                        "raw_text": f"{sector_name} sector: {data['percentage_of_gdp']}% of GDP",
                        "timestamp": datetime.now().isoformat(),
                    })

        dashboard = await world_bank_connector.get_qatar_dashboard()
        for indicator_code, data in dashboard.items():
            if "error" not in data and data.get("latest_value") is not None:
                facts.append({
                    "metric": indicator_code, "value": data["latest_value"],
                    "year": data.get("latest_year"),
                    "description": data.get("description", indicator_code),
                    "source": "World Bank Indicators API", "source_priority": 98,
                    "country": "Qatar", "confidence": 0.99,
                    "raw_text": f"{data.get('description', indicator_code)}: {data['latest_value']} ({data.get('latest_year', 'N/A')})",
                    "timestamp": datetime.now().isoformat(),
                })

        logger.info("Retrieved %d World Bank indicators (including sector GDP)", len(facts))
        write_facts_to_postgres(pg_engine, facts, "world_bank")
        return facts
    except Exception as e:
        logger.warning("World Bank API error: %s", e)
        return []


async def fetch_world_bank_indicators_subset(
    pg_engine, country: str = "QAT", indicator_codes: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Fetch specific World Bank indicators from cache."""
    if not indicator_codes:
        return []
    try:
        cached = query_postgres_cache(pg_engine, "world_bank", country)
        return [f for f in cached if f.get("metric") in indicator_codes]
    except Exception as e:
        logger.warning("World Bank subset query error: %s", e)
        return []


# ---------------------------------------------------------------------------
# IMF
# ---------------------------------------------------------------------------

async def fetch_imf(imf_connector, indicator_code: str, params: Dict) -> List[Dict]:
    """Fetch a single IMF indicator."""
    if not imf_connector:
        return []
    try:
        country = params.get("country", "QAT")
        data = await imf_connector.get_indicator(indicator_code, country)
        values = data.get("values", {})
        metadata = data.get("metadata", {})
        if values:
            latest_year = max(values.keys(), key=lambda x: int(x))
            return [{
                "data_type": metadata.get("description", indicator_code),
                "value": values[latest_year], "year": int(latest_year),
                "source": "IMF Data Mapper API",
                "country": metadata.get("country_name", country),
                "indicator_code": indicator_code, "confidence": "high",
                "all_years": values,
            }]
        return []
    except Exception as e:
        logger.warning("IMF fetch failed for %s: %s", indicator_code, e)
        return []


async def fetch_imf_dashboard(imf_connector) -> List[Dict[str, Any]]:
    """Fetch Qatar economic dashboard from IMF."""
    if not imf_connector:
        return []
    try:
        logger.info("IMF: Fetching Qatar economic dashboard...")
        dashboard = await imf_connector.get_qatar_dashboard()
        facts: List[Dict[str, Any]] = []
        for indicator_name, data in dashboard.items():
            if "error" not in data:
                values = data.get("values", {})
                metadata = data.get("metadata", {})
                if values:
                    latest_year = max(values.keys(), key=lambda x: int(x))
                    facts.append({
                        "metric": indicator_name, "value": values[latest_year],
                        "year": int(latest_year),
                        "description": metadata.get("description", indicator_name),
                        "source": "IMF Data Mapper API", "source_priority": 95,
                        "country": "Qatar", "confidence": 0.98,
                        "raw_text": f"{metadata.get('description', indicator_name)}: {values[latest_year]} ({latest_year})",
                        "timestamp": datetime.now().isoformat(),
                    })
        logger.info("Retrieved %d IMF indicators", len(facts))
        return facts
    except Exception as e:
        logger.warning("IMF API error: %s", e)
        return []


# ---------------------------------------------------------------------------
# UN Comtrade
# ---------------------------------------------------------------------------

async def fetch_comtrade(comtrade_connector, commodity_code: str, params: Dict) -> List[Dict]:
    """Fetch data from UN Comtrade API."""
    if not comtrade_connector:
        return []
    try:
        year = params.get("year", 2023)
        if commodity_code == "FOOD_TOTAL":
            data = await comtrade_connector.get_total_food_imports(year)
            total_value = data.get("TOTAL", {}).get("value_usd", 0)
            return [{
                "data_type": "Total Food Imports", "value": total_value, "year": year,
                "source": "UN Comtrade API", "country": "Qatar", "unit": "USD",
                "confidence": "high",
                "breakdown": {k: v for k, v in data.items() if k != "TOTAL"},
            }]
        data = await comtrade_connector.get_imports(commodity_code, year)
        if "data" in data and data["data"]:
            total_value = sum(item.get("primaryValue", 0) for item in data["data"])
            return [{
                "data_type": f"Imports - Commodity {commodity_code}",
                "value": total_value, "year": year,
                "source": "UN Comtrade API", "country": "Qatar", "unit": "USD",
                "confidence": "high", "records": len(data["data"]),
            }]
        return []
    except Exception as e:
        logger.warning("UN Comtrade fetch failed: %s", e)
        return []


async def fetch_comtrade_food(comtrade_connector) -> List[Dict[str, Any]]:
    """Fetch Qatar food imports from UN Comtrade."""
    if not comtrade_connector:
        return []
    try:
        logger.info("UN Comtrade: Fetching Qatar food imports...")
        food_imports = await comtrade_connector.get_total_food_imports(2023)
        total_value = food_imports.get("TOTAL", {}).get("value_usd", 0)
        facts: List[Dict[str, Any]] = [{
            "metric": "total_food_imports", "value": total_value, "year": 2023,
            "source": "UN Comtrade API", "source_priority": 95, "confidence": 0.95,
            "raw_text": f"Qatar total food imports (2023): ${total_value:,.0f}",
            "timestamp": datetime.now().isoformat(), "unit": "USD",
        }]
        for category, data in food_imports.items():
            if category != "TOTAL" and "error" not in data:
                cat_value = data.get("value_usd", 0)
                facts.append({
                    "metric": f"food_imports_{category.lower().replace(' ', '_')}",
                    "value": cat_value, "category": category, "year": 2023,
                    "source": "UN Comtrade API", "source_priority": 90,
                    "confidence": 0.90,
                    "raw_text": f"Qatar {category} imports (2023): ${cat_value:,.0f}",
                    "timestamp": datetime.now().isoformat(),
                })
        return facts
    except Exception as e:
        logger.warning("UN Comtrade API error: %s", e)
        return []


# ---------------------------------------------------------------------------
# FRED
# ---------------------------------------------------------------------------

async def fetch_fred(fred_connector, series_id: str, params: Dict) -> List[Dict]:
    """Fetch data from FRED API."""
    if not fred_connector:
        return []
    try:
        data = await fred_connector.get_series(
            series_id, params.get("start_date"), params.get("end_date"),
        )
        values = data.get("values", {})
        if values:
            latest_date = max(values.keys())
            return [{
                "data_type": f"FRED Series {series_id}",
                "value": values[latest_date], "date": latest_date,
                "source": "FRED (Federal Reserve Economic Data)",
                "series_id": series_id, "confidence": "high",
                "all_values": values,
            }]
        return []
    except Exception as e:
        logger.warning("FRED fetch failed for %s: %s", series_id, e)
        return []


async def fetch_fred_benchmarks(fred_connector) -> List[Dict[str, Any]]:
    """Fetch US economic benchmarks from FRED."""
    if not fred_connector:
        return []
    try:
        logger.info("FRED: Fetching US economic benchmarks...")
        series_map = {
            "GDP": "US GDP",
            "UNRATE": "US Unemployment Rate",
            "CPIAUCSL": "US Inflation (CPI)",
        }
        facts: List[Dict[str, Any]] = []
        for series_id, description in series_map.items():
            try:
                latest_value = await fred_connector.get_latest_value(series_id)
                if latest_value is not None:
                    facts.append({
                        "metric": f"us_{series_id.lower()}", "value": latest_value,
                        "description": description, "series_id": series_id,
                        "source": "FRED (Federal Reserve Economic Data)",
                        "source_priority": 90, "country": "United States",
                        "confidence": 0.95, "raw_text": f"{description}: {latest_value}",
                        "timestamp": datetime.now().isoformat(),
                    })
            except Exception as e:
                logger.debug("Failed to fetch %s: %s", series_id, e)
        return facts
    except Exception as e:
        logger.warning("FRED API error: %s", e)
        return []


# ---------------------------------------------------------------------------
# FAO Food Security (World Bank primary + FAO supplement)
# ---------------------------------------------------------------------------

async def fetch_fao_food_security(
    fao_connector, pg_engine, country: str = "QAT",
) -> List[Dict[str, Any]]:
    """Fetch FAO food security with World Bank agriculture indicators as primary."""
    facts: List[Dict[str, Any]] = []
    try:
        logger.info("World Bank: Fetching agriculture/food indicators...")
        agriculture_indicators = [
            "AG.LND.AGRI.ZS", "AG.PRD.FOOD.XD", "AG.LND.ARBL.HA.PC",
            "AG.YLD.CREL.KG", "NV.AGR.TOTL.ZS", "AG.CON.FERT.ZS",
            "AG.LND.CROP.ZS", "AG.LND.IRIG.AG.ZS", "SN.ITK.DEFC.ZS",
            "SP.DYN.LE00.IN", "TM.VAL.FOOD.ZS.UN", "TX.VAL.FOOD.ZS.UN",
        ]
        wb_facts = await fetch_world_bank_indicators_subset(
            pg_engine, country, agriculture_indicators,
        )
        for fact in wb_facts:
            facts.append({
                "metric": fact.get("metric", "unknown"), "value": fact.get("value"),
                "year": fact.get("year"), "country": country,
                "source": "World Bank Agriculture Indicators", "source_priority": 95,
                "confidence": 0.95, "raw_text": fact.get("raw_text", ""),
                "timestamp": datetime.now().isoformat(),
            })
        logger.info("Retrieved %d World Bank agriculture indicators", len(facts))
    except Exception as e:
        logger.warning("World Bank agriculture error: %s", e)

    if fao_connector and len(facts) < 5:
        try:
            logger.info("FAO: Fetching food security data (supplement)...")
            dashboard = await fao_connector.get_food_security_dashboard("634")
            if dashboard and "error" not in dashboard:
                food_balance = dashboard.get("food_balance", {})
                if food_balance and "error" not in food_balance and food_balance.get("food_balance"):
                    facts.append({
                        "metric": "food_balance_available", "value": 1.0,
                        "year": 2023, "country": "Qatar",
                        "source": "FAO STAT - Food Balance", "source_priority": 96,
                        "confidence": 0.97,
                        "raw_text": "Food balance data available from FAO",
                        "timestamp": datetime.now().isoformat(),
                    })
        except Exception as e:
            logger.debug("FAO supplement failed: %s", e)
    return facts


# ---------------------------------------------------------------------------
# IEA Energy (World Bank primary + IEA supplement)
# ---------------------------------------------------------------------------

async def fetch_iea_energy(
    iea_connector, pg_engine, country: str = "QAT",
) -> List[Dict[str, Any]]:
    """Fetch IEA energy data with World Bank fallback."""
    facts: List[Dict[str, Any]] = []
    try:
        logger.info("World Bank: Fetching energy indicators...")
        energy_indicators = [
            "EG.USE.PCAP.KG.OE", "EG.USE.ELEC.KH.PC", "EG.ELC.ACCS.ZS",
            "EG.FEC.RNEW.ZS", "EG.USE.COMM.FO.ZS", "EN.ATM.CO2E.PC",
            "EN.ATM.CO2E.KT", "EG.ELC.FOSL.ZS", "EG.ELC.RNWX.ZS",
            "EG.IMP.CONS.ZS", "NV.IND.TOTL.ZS", "EG.GDP.PUSE.KO.PP",
        ]
        wb_facts = await fetch_world_bank_indicators_subset(
            pg_engine, country, energy_indicators,
        )
        for fact in wb_facts:
            facts.append({
                "metric": fact.get("metric", "unknown"), "value": fact.get("value"),
                "year": fact.get("year"), "country": country,
                "source": "World Bank Energy Indicators", "source_priority": 95,
                "confidence": 0.95, "raw_text": fact.get("raw_text", ""),
                "timestamp": datetime.now().isoformat(),
            })
        logger.info("Retrieved %d World Bank energy indicators", len(facts))
    except Exception as e:
        logger.warning("World Bank energy error: %s", e)

    if iea_connector and not facts:
        try:
            logger.info("IEA: Fetching energy sector data (fallback)...")
            dashboard = await iea_connector.get_energy_dashboard(country)
            if dashboard and "error" not in dashboard:
                for indicator, data in dashboard.items():
                    if isinstance(data, dict) and "latest_value" in data:
                        facts.append({
                            "metric": indicator, "value": data["latest_value"],
                            "year": data.get("latest_year"), "country": country,
                            "source": "IEA Energy Statistics", "source_priority": 96,
                            "confidence": 0.97,
                            "raw_text": f"{indicator}: {data['latest_value']} ({data.get('latest_year')})",
                            "timestamp": datetime.now().isoformat(),
                        })
        except Exception as e:
            logger.debug("IEA fallback failed: %s", e)
    return facts
