"""
Demonstration: Qatar Open Data + Brave + Semantic Scholar + Perplexity
Shows how all data sources enrich labor market intelligence
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

async def demo_employment_data_enrichment():
    """
    Demonstrate: Qatar Open Data API + Web Search + Academic Papers + AI Analysis
    Query: "Employee counts by sector and Qatarization rates in Qatar"
    """
    
    print("="*80)
    print("QATAR LABOR MARKET DATA ENRICHMENT DEMO")
    print("="*80)
    print()
    
    # ============================================================================
    # PART 1: Qatar Open Data API (Newly Integrated)
    # ============================================================================
    print("📊 PART 1: Official Qatar Open Data Portal API")
    print("-" * 80)
    
    import httpx
    
    # Dataset 1: Employee counts by sector
    url1 = "https://www.data.gov.qa/api/explore/v2.1/catalog/datasets/number-of-employees-and-compensation-of-employees-by-nationality-and-main-economic-activity/records"
    params1 = {"where": "year='2020' AND labor_indicator='Number of Employees'", "limit": 5}
    
    print("Query: Employee counts by economic activity & nationality (2020)")
    async with httpx.AsyncClient() as client:
        response = await client.get(url1, params=params1, timeout=15.0)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"✅ Retrieved {len(results)} records")
            for r in results[:3]:
                print(f"  - {r['main_economic_activity']}: {r['value']:,} {r['nationality']} employees")
        else:
            print(f"❌ API Error: {response.status_code}")
    
    print()
    
    # Dataset 2: Training center enrollment
    url2 = "https://www.data.gov.qa/api/explore/v2.1/catalog/datasets/trainees-at-the-private-training-centers-by-field-of-training-gender-nationality-and-age-groups/records"
    params2 = {"where": "field_of_training='Computer'", "limit": 5}
    
    print("Query: Computer training enrollment by demographics")
    async with httpx.AsyncClient() as client:
        response = await client.get(url2, params=params2, timeout=15.0)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"✅ Retrieved {len(results)} records")
            for r in results[:3]:
                print(f"  - {r['nationality']}/{r['gender']}/{r['age_groups']}: {r['value']} trainees")
        else:
            print(f" ❌ API Error: {response.status_code}")
    
    print("\n" + "="*80)
    
    # ============================================================================
    # PART 2: Brave Search (Already integrated)
    # ============================================================================
    print("🌐 PART 2: Brave Web Search API")
    print("-" * 80)
    
    brave_api_key = os.getenv("BRAVE_API_KEY")
    if brave_api_key:
        url_brave = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": brave_api_key
        }
        params_brave = {
            "q": "Qatar Qatarization policy 2024 employment targets",
            "count": 5
        }
        
        print("Query: Qatar Qatarization policy 2024 employment targets")
        async with httpx.AsyncClient() as client:
            response = await client.get(url_brave, headers=headers, params=params_brave, timeout=15.0)
            if response.status_code == 200:
                data = response.json()
                results = data.get("web", {}).get("results", [])
                print(f"✅ Found {len(results)} web results")
                for i, r in enumerate(results[:3], 1):
                    print(f"  {i}. {r.get('title', 'No title')}")
                    print(f"     {r.get('url', '')}")
                    print(f"     {r.get('description', '')[:100]}...")
            else:
                print(f"❌ Brave API Error: {response.status_code}")
    else:
        print("⚠️  BRAVE_API_KEY not set")
    
    print("\n" + "="*80)
    
    # ============================================================================
    # PART 3: Semantic Scholar (Already integrated)
    # ============================================================================
    print("📚 PART 3: Semantic Scholar Academic Papers")
    print("-" * 80)
    
    semantic_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    headers_semantic = {"x-api-key": semantic_api_key} if semantic_api_key else {}
    
    url_semantic = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
    params_semantic = {
        "query": "workforce nationalization GCC Qatar employment",
        "fields": "title,year,abstract,citationCount,url",
        "year": "2020-",
        "limit": "5"
    }
    
    print("Query: Workforce nationalization GCC Qatar employment (2020+)")
    async with httpx.AsyncClient() as client:
        response = await client.get(url_semantic, headers=headers_semantic, params=params_semantic, timeout=15.0)
        if response.status_code == 200:
            data = response.json()
            papers = data.get("data", [])
            print(f"✅ Found {len(papers)} papers")
            for i, paper in enumerate(papers[:3], 1):
                print(f"  {i}. {paper.get('title', 'No title')} ({paper.get('year', 'N/A')})")
                print(f"     Citations: {paper.get('citationCount', 0)} | {paper.get('url', '')}")
                abstract = paper.get('abstract', '')
                if abstract:
                    print(f"     {abstract[:150]}...")
        else:
            print(f"❌ Semantic Scholar Error: {response.status_code}")
    
    print("\n" + "="*80)
    
    # ============================================================================
    # PART 4: Perplexity AI (Already integrated)
    # ============================================================================
    print("🤖 PART 4: Perplexity AI Real-Time Analysis")
    print("-" * 80)
    
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    if perplexity_api_key:
        url_perplexity = "https://api.perplexity.ai/chat/completions"
        headers_perplexity = {
            "Authorization": f"Bearer {perplexity_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a labor market analyst. Find the most recent, specific data with sources."
                },
                {
                    "role": "user",
                    "content": "What are the current Qatarization employment targets by sector in Qatar for 2024-2025? Provide exact percentages and sources."
                }
            ]
        }
        
        print("Query: Current Qatarization targets by sector (2024-2025)")
        async with httpx.AsyncClient() as client:
            response = await client.post(url_perplexity, headers=headers_perplexity, json=payload, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"✅ Perplexity Response:")
                print(f"  {answer[:400]}...")
            else:
                print(f"❌ Perplexity Error: {response.status_code}")
    else:
        print("⚠️  PERPLEXITY_API_KEY not set")
    
    print("\n" + "="*80)
    print("🎯 SUMMARY: Data Triangulation")
    print("-" * 80)
    print("""
This demonstration shows how QNWIS enriches labor market intelligence:

1. Qatar Open Data API → Official government statistics (employment by sector, training)
2. Brave Search → Latest policy documents and news
3. Semantic Scholar → Academic research on Qatarization effectiveness
4. Perplexity AI → Real-time analysis synthesizing multiple sources

AGENT USAGE:
- MacroEconomist: Uses Qatar API + Perplexity for sector-wide trends
- MicroEconomist: Uses Semantic Scholar + Qatar API for skill gap analysis
- Both triangulate official data (Qatar API) with research (Semantic Scholar)
  and real-time intel (Brave + Perplexity)
    """)
    print("="*80)


async def demo_qatar_api_direct():
    """Direct test of Qatar Open Data API connector"""
    print("\n\n" + "="*80)
    print("TESTING QATAR API CONNECTOR")
    print("="*80)
    print()
    
    try:
        from qnwis.data.connectors.qatar_opendata_api import run_qatar_api_query
        from qnwis.data.deterministic.models import QuerySpec
        
        spec = QuerySpec(
            id="test_employees",
            source="qatar_api",
            expected_unit="count",
            params={
                "dataset_id": "number-of-employees-and-compensation-of-employees-by-nationality-and-main-economic-activity",
                "where": "year='2020' AND labor_indicator='Number of Employees'",
                "limit": 10
            }
        )
        
        print("Executing Qatar API query...")
        result = run_qatar_api_query(spec)
        
        print(f"✅ SUCCESS!")
        print(f"  Query ID: {result.query_id}")
        print(f"  Source: {result.provenance.source}")
        print(f"  Dataset: {result.provenance.dataset_id}")
        print(f"  License: {result.provenance.license}")
        print(f"  Rows fetched: {len(result.rows)}")
        print(f"  Fields: {result.provenance.fields}")
        print(f"  As of date: {result.freshness.asof_date}")
        
        if result.rows:
            print(f"\nSample data:")
            for i, row in enumerate(result.rows[:3], 1):
                print(f"  {i}. {row.data}")
        
    except Exception as e:
        print(f"❌ Error testing Qatar API connector: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n\nQNWIS Multi-Source Data Enrichment Demo")
    print("Demonstrating: Qatar Open Data + Brave + Semantic Scholar + Perplexity\n")
    
    asyncio.run(demo_employment_data_enrichment())
    asyncio.run(demo_qatar_api_direct())
