"""
Reproducibility snippet for audit pack.
Registry version: v1.0
"""

from src.qnwis.data.deterministic.api import DataAPI

# Initialize Data API with the same registry version
api = DataAPI(registry_version="v1.0")

# Query IDs from original execution
query_ids = [
    "qid_abc123"
]

# Fetch all QueryResults
results = []
for qid in query_ids:
    try:
        result = api.fetch(qid)
        results.append(result)
    except Exception as exc:
        print(f"Failed to fetch {qid}: {exc}")

# Compare results to evidence/*.json in audit pack
print(f"Fetched {len(results)} / {len(query_ids)} QueryResults")
