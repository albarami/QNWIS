"""
ETL: World Bank API -> PostgreSQL world_bank_indicators table
EXPANDED: 23+ indicators for all 6 GCC countries (Qatar + benchmarking)

Domain-Agnostic: Covers Labor, Health, Education, Energy, Trade, Finance, Environment
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.apis.world_bank_api import WorldBankAPI
from qnwis.data.deterministic.engine import get_engine
from sqlalchemy import text


def safe_print(msg: str) -> None:
    """Print with ASCII fallback for Windows console compatibility"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="ignore").decode("ascii"))


# All GCC countries for benchmarking
GCC_COUNTRIES = {
    "QAT": "Qatar",
    "SAU": "Saudi Arabia", 
    "ARE": "United Arab Emirates",
    "KWT": "Kuwait",
    "BHR": "Bahrain",
    "OMN": "Oman"
}

# EXPANDED: 23+ indicators across ALL domains (domain-agnostic)
COMPREHENSIVE_INDICATORS = {
    # === LABOR MARKET (Critical for QNWIS) ===
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force)",
    "SL.UEM.TOTL.NE.ZS": "Unemployment, total (% of total labor force) (national estimate)",
    "SL.TLF.CACT.ZS": "Labor force participation rate, total (% of population 15+)",
    "SL.TLF.CACT.MA.ZS": "Labor force participation rate, male (% of male population 15+)",
    "SL.TLF.CACT.FE.ZS": "Labor force participation rate, female (% of female population 15+)",
    "SL.EMP.TOTL.SP.ZS": "Employment to population ratio, 15+, total (%)",
    "SL.GDP.PCAP.EM.KD": "GDP per person employed (constant 2017 PPP $)",
    
    # === ECONOMIC / GDP ===
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "NV.IND.TOTL.ZS": "Industry, value added (% of GDP)",
    "NV.SRV.TOTL.ZS": "Services, value added (% of GDP)",
    "NV.AGR.TOTL.ZS": "Agriculture, value added (% of GDP)",
    
    # === HEALTH ===
    "SH.XPD.CHEX.GD.ZS": "Current health expenditure (% of GDP)",
    "SP.DYN.LE00.IN": "Life expectancy at birth, total (years)",
    "SH.MED.BEDS.ZS": "Hospital beds (per 1,000 people)",
    
    # === EDUCATION ===
    "SE.TER.ENRR": "School enrollment, tertiary (% gross)",
    "SE.SEC.ENRR": "School enrollment, secondary (% gross)",
    "SE.XPD.TOTL.GD.ZS": "Government expenditure on education, total (% of GDP)",
    
    # === INFRASTRUCTURE / DIGITAL ===
    "IT.NET.USER.ZS": "Individuals using the Internet (% of population)",
    "IT.CEL.SETS.P2": "Mobile cellular subscriptions (per 100 people)",
    "IS.AIR.DPRT": "Air transport, registered carrier departures worldwide",
    
    # === TRADE / INVESTMENT ===
    "NE.EXP.GNFS.ZS": "Exports of goods and services (% of GDP)",
    "NE.IMP.GNFS.ZS": "Imports of goods and services (% of GDP)",
    "BX.KLT.DINV.WD.GD.ZS": "Foreign direct investment, net inflows (% of GDP)",
    "NY.GDS.TOTL.ZS": "Gross savings (% of GDP)",
    
    # === ENERGY / ENVIRONMENT ===
    "EG.USE.ELEC.KH.PC": "Electric power consumption (kWh per capita)",
    "EN.ATM.CO2E.PC": "CO2 emissions (metric tons per capita)",
    "EG.FEC.RNEW.ZS": "Renewable energy consumption (% of total final energy consumption)",
    
    # === POPULATION / DEMOGRAPHICS ===
    "SP.POP.TOTL": "Population, total",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total population)",
}


async def clear_old_data(engine):
    """Clear old placeholder/incorrect data before fresh load"""
    safe_print("\n[CLEANUP] Clearing old World Bank data...")
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM world_bank_indicators"))
        safe_print(f"   Deleted {result.rowcount} old records")


async def load_world_bank_to_postgres(clear_first: bool = True):
    """
    Fetch World Bank data for ALL GCC countries
    Load into world_bank_indicators table
    
    Args:
        clear_first: If True, clear old data before loading fresh data
    """
    safe_print("=" * 80)
    safe_print("[ETL] WORLD BANK -> POSTGRESQL (EXPANDED)")
    safe_print(f"   Indicators: {len(COMPREHENSIVE_INDICATORS)}")
    safe_print(f"   Countries: {len(GCC_COUNTRIES)} GCC nations")
    safe_print("=" * 80)
    
    wb_api = WorldBankAPI()
    engine = get_engine()
    
    if clear_first:
        await clear_old_data(engine)
    
    total_records = 0
    failed_indicators = []
    
    for country_code, country_name in GCC_COUNTRIES.items():
        safe_print(f"\n{'=' * 60}")
        safe_print(f"[COUNTRY] Processing: {country_name} ({country_code})")
        safe_print(f"{'=' * 60}")
        
        country_records = 0
        
        for indicator_code, indicator_name in COMPREHENSIVE_INDICATORS.items():
            try:
                safe_print(f"\n[FETCH] {indicator_code}: {indicator_name[:50]}...")
                
                # Fetch from World Bank API
                data = await wb_api.get_indicator(indicator_code, country_code, start_year=2010)
                
                values = data.get("values", {})
                if not values:
                    safe_print(f"   [WARN] No data available for {country_code}")
                    continue
                
                # Insert into PostgreSQL
                with engine.begin() as conn:
                    for year, value in values.items():
                        if value is not None:
                            conn.execute(
                                text("""
                                    INSERT INTO world_bank_indicators 
                                    (country_code, country_name, indicator_code, indicator_name, year, value, created_at)
                                    VALUES (:country, :country_name, :code, :name, :year, :value, :created)
                                    ON CONFLICT (country_code, indicator_code, year) 
                                    DO UPDATE SET value = EXCLUDED.value, indicator_name = EXCLUDED.indicator_name
                                """),
                                {
                                    "country": country_code,
                                    "country_name": country_name,
                                    "code": indicator_code,
                                    "name": indicator_name,
                                    "year": int(year),
                                    "value": float(value),
                                    "created": datetime.utcnow()
                                }
                            )
                
                records_loaded = len([v for v in values.values() if v is not None])
                safe_print(f"   [OK] Loaded {records_loaded} records")
                country_records += records_loaded
                total_records += records_loaded
                
                # Rate limiting - be nice to World Bank API
                await asyncio.sleep(0.2)
                
            except Exception as e:
                safe_print(f"   [ERROR] Failed: {e}")
                failed_indicators.append((country_code, indicator_code, str(e)))
        
        safe_print(f"\n   [TOTAL] {country_name}: {country_records} records")
    
    await wb_api.close()
    
    # Summary
    safe_print(f"\n{'=' * 80}")
    safe_print(f"[COMPLETE] ETL FINISHED")
    safe_print(f"   Total records loaded: {total_records}")
    safe_print(f"   Countries: {len(GCC_COUNTRIES)}")
    safe_print(f"   Indicators: {len(COMPREHENSIVE_INDICATORS)}")
    
    if failed_indicators:
        safe_print(f"\n[WARN] Failed indicators ({len(failed_indicators)}):")
        for country, indicator, error in failed_indicators[:10]:
            safe_print(f"   - {country}/{indicator}: {error[:50]}")
    
    safe_print(f"{'=' * 80}")
    
    return total_records


async def validate_data():
    """Validate loaded data has realistic values"""
    safe_print("\n[VALIDATE] Checking data quality...")
    engine = get_engine()
    
    validations = []
    
    with engine.connect() as conn:
        # Check Qatar unemployment is realistic (should be 0.1-0.5%, definitely < 5%)
        result = conn.execute(text("""
            SELECT year, value FROM world_bank_indicators 
            WHERE indicator_code = 'SL.UEM.TOTL.ZS' AND country_code = 'QAT'
            ORDER BY year DESC LIMIT 5
        """))
        rows = result.fetchall()
        
        if rows:
            safe_print(f"\n   Qatar Unemployment (should be < 1%):")
            for row in rows:
                status = "[OK]" if row.value < 5 else "[BAD] UNREALISTIC"
                safe_print(f"      {row.year}: {row.value:.2f}% {status}")
                validations.append(("Qatar unemployment", row.value < 5))
        else:
            safe_print(f"   [WARN] No unemployment data found")
            validations.append(("Qatar unemployment data exists", False))
        
        # Check we have data for all GCC countries
        result = conn.execute(text("""
            SELECT country_code, COUNT(DISTINCT indicator_code) as indicators
            FROM world_bank_indicators
            GROUP BY country_code
            ORDER BY country_code
        """))
        rows = result.fetchall()
        
        safe_print(f"\n   Data coverage by country:")
        for row in rows:
            status = "[OK]" if row.indicators >= 10 else "[WARN]"
            safe_print(f"      {row.country_code}: {row.indicators} indicators {status}")
            validations.append((f"{row.country_code} has data", row.indicators >= 5))
        
        # Check total record count
        result = conn.execute(text("SELECT COUNT(*) as total FROM world_bank_indicators"))
        total = result.scalar()
        safe_print(f"\n   Total records: {total}")
        validations.append(("Has sufficient records", total > 100))
    
    # Summary
    passed = sum(1 for _, v in validations if v)
    total_checks = len(validations)
    
    safe_print(f"\n{'=' * 60}")
    safe_print(f"   Validation: {passed}/{total_checks} checks passed")
    if passed == total_checks:
        safe_print(f"   [SUCCESS] DATA QUALITY: GOOD")
    else:
        safe_print(f"   [WARN] DATA QUALITY: ISSUES FOUND")
    safe_print(f"{'=' * 60}")
    
    return passed == total_checks


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="World Bank ETL for QNWIS")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation")
    parser.add_argument("--no-clear", action="store_true", help="Don't clear existing data")
    args = parser.parse_args()
    
    async def main():
        if args.validate_only:
            await validate_data()
        else:
            await load_world_bank_to_postgres(clear_first=not args.no_clear)
            await validate_data()
    
    asyncio.run(main())
