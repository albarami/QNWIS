"""Check what data is available for deterministic agents."""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from src.qnwis.data.deterministic.registry import QueryRegistry
import os

def main():
    print("=" * 60)
    print("DATA AVAILABILITY CHECK FOR DETERMINISTIC AGENTS")
    print("=" * 60)
    
    # Load registry
    registry = QueryRegistry()
    registry.load_all()
    
    query_ids = registry.list_query_ids()
    print(f"\nTotal registered queries: {len(query_ids)}")
    
    # Check specific queries used by agents
    agent_queries = {
        "NationalStrategy": [
            "syn_unemployment_gcc_latest",
            "syn_attrition_by_sector_latest", 
            "syn_qatarization_by_sector_latest",
            "gcc_unemployment_comparison",
        ],
        "LabourEconomist": [
            "syn_employment_share_by_gender_latest",
            "employment_share_by_gender",
        ],
        "TimeMachine": [
            "retention_rate_by_sector",
        ],
        "Predictor": [
            "attrition_rate_monthly",
        ],
        "PatternMiner": [
            "employment_share_by_gender",
        ],
    }
    
    print("\n" + "=" * 60)
    print("QUERY STATUS BY AGENT")
    print("=" * 60)
    
    from src.qnwis.agents.base import DataClient
    
    try:
        client = DataClient()
        
        for agent_name, queries in agent_queries.items():
            print(f"\n{agent_name}:")
            for qid in queries:
                try:
                    if not registry.has_query(qid):
                        print(f"  {qid}: NOT REGISTERED")
                        continue
                        
                    result = client.run(qid)
                    if result.rows is None:
                        print(f"  {qid}: NULL ROWS")
                    else:
                        rows = list(result.rows)
                        if len(rows) == 0:
                            print(f"  {qid}: 0 ROWS (empty)")
                        else:
                            print(f"  {qid}: {len(rows)} rows")
                            # Check first row data
                            first = rows[0]
                            if hasattr(first, 'data') and first.data:
                                keys = list(first.data.keys())[:4]
                                print(f"    Columns: {keys}")
                except Exception as e:
                    print(f"  {qid}: ERROR - {str(e)[:50]}")
                    
    except Exception as e:
        print(f"DataClient error: {e}")
    
    # Check CSV queries that might have data
    print("\n" + "=" * 60)
    print("CSV QUERIES WITH DATA")
    print("=" * 60)
    
    csv_queries = [q for q in query_ids if q.startswith('q_') or 'syn_' in q]
    for qid in sorted(csv_queries)[:15]:
        try:
            spec = registry.get(qid)
            if spec and spec.get('source') == 'csv':
                result = client.run(qid)
                rows = list(result.rows) if result.rows else []
                if len(rows) > 0:
                    print(f"  {qid}: {len(rows)} rows")
        except:
            pass

if __name__ == "__main__":
    main()

