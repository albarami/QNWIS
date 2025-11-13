#!/usr/bin/env python
"""Parse LMIS API documentation from CSV and generate Python client."""

import pandas as pd
import json
from pathlib import Path

# Read the CSV
df = pd.read_csv("API_DashBorad_API_DashBorad.csv")

print(f"📊 Total LMIS APIs: {len(df)}\n")
print("=" * 80)
print("API Endpoints:\n")

for i, row in df.iterrows():
    dashboard = row["Dashboard Name"]
    chart = row["CHART_NAME"]
    endpoint = row["ENDPOINT"]
    
    print(f"{i+1:2}. {dashboard:40} | {chart}")
    print(f"    → {endpoint}")
    print()

print("=" * 80)

# Extract unique dashboards
dashboards = df["Dashboard Name"].unique()
print(f"\n📁 Dashboards ({len(dashboards)}):")
for dash in dashboards:
    count = len(df[df["Dashboard Name"] == dash])
    print(f"  • {dash}: {count} endpoints")

# Show sample response structure
print("\n" + "=" * 80)
print("Sample Response Structures:\n")

for i in range(min(3, len(df))):
    row = df.iloc[i]
    print(f"Endpoint: {row['CHART_NAME']}")
    
    try:
        if pd.notna(row["E.g Response"]):
            response_sample = row["E.g Response"][:200]
            print(f"Response: {response_sample}...")
    except:
        pass
    
    print()
