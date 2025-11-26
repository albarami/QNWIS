#!/usr/bin/env python3
"""Analyze all LMIS endpoints from CSV file."""

import re
from pathlib import Path

csv_path = Path(r"C:\Users\admin-salim\Downloads\API  DashBorad(API  DashBorad).csv")

with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Find all endpoints
endpoints = set()
pattern = r'https://lmis-dashb-api\.mol\.gov\.qa/api/[^\s,"\'\\\)]+' 

for match in re.finditer(pattern, content):
    url = match.group(0).strip()
    # Remove trailing punctuation
    url = url.rstrip('.,;:')
    # Get base URL without query params
    base_url = url.split('?')[0]
    if base_url and '/api/' in base_url:
        endpoints.add(base_url)

# Also look for dashboard names
dashboards = set()
dashboard_pattern = r'^([A-Z][a-zA-Z\s\-&]+),'
for line in content.split('\n'):
    if line and not line.startswith('Dashboard'):
        match = re.match(r'^([A-Z][a-zA-Z\s\-&]+),', line)
        if match:
            dashboards.add(match.group(1).strip())

print(f'TOTAL UNIQUE ENDPOINTS: {len(endpoints)}')
print('='*70)
for i, ep in enumerate(sorted(endpoints), 1):
    # Extract endpoint name
    name = ep.split('/api/')[-1] if '/api/' in ep else ep
    print(f'{i:2}. {name}')
    print(f'    URL: {ep}')

print('\n' + '='*70)
print(f'DASHBOARDS FOUND: {len(dashboards)}')
for d in sorted(dashboards):
    print(f'  - {d}')


