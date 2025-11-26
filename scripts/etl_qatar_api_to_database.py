"""
ETL Script: Load Qatar Open Data API into PostgreSQL Database
Demonstrates integration of new API data with existing database
"""

import asyncio
import httpx
import psycopg
from datetime import datetime
from typing import List, Dict, Any

# Database connection
DATABASE_URL = "postgresql://postgres:1234@localhost:5432/qnwis"

async def fetch_qatar_api_data(dataset_id: str, where: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch data from Qatar Open Data API v2.1"""
    url = f"https://www.data.gov.qa/api/explore/v2.1/catalog/datasets/{dataset_id}/records"
    params = {"limit": limit}
    if where:
        params["where"] = where
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])


async def load_employment_by_sector():
    """Load employee counts by economic activity into qatar_open_data table"""
    print("\n" + "="*80)
    print("📥 LOADING: Employee Counts by Sector & Nationality")
    print("="*80)
    
    dataset_id = "number-of-employees-and-compensation-of-employees-by-nationality-and-main-economic-activity"
    
    # Fetch data from API
    print(f"Fetching data from Qatar Open Data API...")
    records = await fetch_qatar_api_data(
        dataset_id,
        where="labor_indicator='Number of Employees' AND year IN ('2020', '2021')",
        limit=500
    )
    print(f"✅ Fetched {len(records)} records from API")
    
   # Insert into database
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    
    inserted_count = 0
    for record in records:
        try:
            cur.execute("""
                INSERT INTO qatar_open_data (
                    dataset_id, dataset_name, category, indicator_name,
                    time_period, value, unit, gender, nationality, metadata, source_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                dataset_id,
                "Employee Counts by Economic Activity",
                "Labor Market",
                f"{record.get('main_economic_activity')} - {record.get('economic_activity')}",
                record.get('year'),
                record.get('value'),
                "count",
                None,  # No gender in this dataset
                record.get('nationality'),
                psycopg.types.json.Jsonb(record),  # Store full record as metadata
                f"https://www.data.gov.qa/explore/dataset/{dataset_id}"
            ))
            inserted_count += 1
        except Exception as e:
            print(f"⚠️  Error inserting record: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Inserted {inserted_count} records into qatar_open_data table")


async def load_training_center_data():
    """Load training center enrollment into qatar_open_data table"""
    print("\n" + "="*80)
    print("📥 LOADING: Training Center Enrollment Data")
    print("="*80)
    
    dataset_id = "trainees-at-the-private-training-centers-by-field-of-training-gender-nationality-and-age-groups"
    
    # Fetch data from API
    print(f"Fetching data from Qatar Open Data API...")
    records = await fetch_qatar_api_data(dataset_id, limit=500)
    print(f"✅ Fetched {len(records)} records from API")
    
    # Insert into database
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    
    inserted_count = 0
    for record in records:
        try:
            cur.execute("""
                INSERT INTO qatar_open_data (
                    dataset_id, dataset_name, category, indicator_name,
                    time_period, value, unit, gender, nationality, age_group, metadata, source_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                dataset_id,
                "Private Training Center Enrollment",
                "Education & Training",
                record.get('field_of_training'),
                record.get('year'),
                record.get('value'),
                "count",
                record.get('gender'),
                record.get('nationality'),
                record.get('age_groups'),
                psycopg.types.json.Jsonb(record),
                f"https://www.data.gov.qa/explore/dataset/{dataset_id}"
            ))
            inserted_count += 1
        except Exception as e:
            print(f"⚠️  Error inserting record: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Inserted {inserted_count} records into qatar_open_data table")


def query_enriched_database():
    """Query the database to show how Qatar API data enriches existing data"""
    print("\n" + "="*80)
    print("🔍 QUERYING ENRICHED DATABASE")
    print("="*80)
    
    conn = psycopg.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Query 1: Count records by data source
    print("\n1. Data Sources in qatar_open_data Table:")
    print("-" * 80)
    cur.execute("""
        SELECT dataset_name, COUNT(*) as record_count
        FROM qatar_open_data
        GROUP BY dataset_name
        ORDER BY record_count DESC
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} records")
    
    # Query 2: Employment by sector from Qatar API
    print("\n2. Top 5 Sectors by Employment (2020, Qatar API Data):")
    print("-" * 80)
    cur.execute("""
        SELECT 
            indicator_name,
            SUM(value) as total_employees,
            nationality
        FROM qatar_open_data
        WHERE dataset_id LIKE '%number-of-employees%'
          AND time_period = '2020'
        GROUP BY indicator_name, nationality
        ORDER BY total_employees DESC
        LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"  {row[0][:60]}: {row[1]:,.0f} ({row[2]}) employees")
    
    # Query 3: Training enrollment by field
    print("\n3. Training Enrollment by Field (Qatar API Data):")
    print("-" * 80)
    cur.execute("""
        SELECT 
            indicator_name,
            SUM(value) as total_trainees
        FROM qatar_open_data
        WHERE dataset_id LIKE '%trainees%'
        GROUP BY indicator_name
        ORDER BY total_trainees DESC
        LIMIT 5
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,.0f} trainees")
    
    # Query 4: Compare with existing employment_records
    print("\n4. Data Comparison - Database vs Qatar API:")
    print("-" * 80)
    cur.execute("SELECT COUNT(*) FROM employment_records WHERE status='employed'")
    db_employed = cur.fetchone()[0]
    cur.execute("SELECT SUM(value) FROM qatar_open_data WHERE dataset_id LIKE'%number-of-employees%' AND time_period='2020'")
    api_employed = cur.fetchone()[0] or 0
    
    print(f"  Internal DB (employment_records): {db_employed:,} employed")
    print(f"  Qatar API (2020 official data): {api_employed:,.0f} employees")
    print(f"  → Agents can triangulate between internal DB and official statistics!")
    
    cur.close()
    conn.close()


async def demonstrate_multi_source_enrichment():
    """Show how all data sources work together"""
    print("\n" + "="*80)
    print("🌐 MULTI-SOURCE DATA ENRICHMENT DEMO")
    print("="*80)
    
   # Simulate what agents see when querying "Qatar employment by sector"
    print("\nAgent Query: 'What is the employment distribution by sector in Qatar?'")
    print("-" * 80)
    
    print("\n📊 Data Sources Available:")
    print("  1. ✅ PostgreSQL (employment_records) - 1,000 internal records")
    print("  2. ✅ PostgreSQL (qatar_open_data) - Official PSA statistics via API")
    print("  3. ✅ Brave Search API - Latest news and policy documents")
    print("  4. ✅ Semantic Scholar API - Academic research on labor markets")
    print("  5. ✅ Perplexity API - Real-time synthesized analysis")
    print("  6. ✅ World Bank API - International comparisons")
    print("  7. ✅ GCC-STAT API - Regional benchmarking")
    
    print("\n🎯 Agent Strategy:")
    print("  MacroEconomist:")
    print("    - Queries `qatar_open_data` for official sector employment (2016-2021)")
    print("    - Uses Perplexity to find 2024 policy targets")
    print("    - Uses GCC-STAT for regional comparison")
    print("  MicroEconomist:")
    print("    - Queries `employment_records` for granular company-level data")
    print("    - Uses Semantic Scholar for skills gap research")
    print("    - Uses `qatar_open_data` training enrollment for workforce pipeline")
    
    print("\n💡 Insight: Qatar Open Data API bridges the gap between:")
    print("    - Internal granular data (employment_records)")
    print("    - Official national statistics (qatar_open_data table)")
    print("    - Real-time web intelligence (Brave + Perplexity)")
    print("    - Academic research (Semantic Scholar)")


async def main():
    """Main ETL execution"""
    print("\n\n" + "="*80)
    print("QATAR OPEN DATA ETL - DATABASE INTEGRATION")
    print("="*80)
    
    # Load data from API into database
    await load_employment_by_sector()
    await load_training_center_data()
    
    # Query enriched database
    query_enriched_database()
    
    # Demonstrate multi-source strategy
    await demonstrate_multi_source_enrichment()
    
    print("\n" + "="*80)
    print("✅ ETL COMPLETE")
    print("="*80)
    print("\nNext Steps:")
    print("  1. Agents can now query qatar_open_data table for official statistics")
    print("  2. SQL queries combine internal DB + Qatar API data")
    print("  3. Brave/Semantic Scholar/Perplexity add real-time context")
    print("  4. System provides comprehensive labor market intelligence!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
