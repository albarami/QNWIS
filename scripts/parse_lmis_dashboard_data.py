#!/usr/bin/env python3
"""
Parse LMIS Dashboard CSV and extract all API data.

This script:
1. Reads the MoL LMIS API Dashboard CSV
2. Extracts all endpoints and their sample responses
3. Saves as JSON for system use
"""

import csv
import json
import re
from pathlib import Path
from typing import Dict, Any, List

# Input/Output paths
INPUT_CSV = Path(r"C:\Users\admin-salim\Downloads\API  DashBorad(API  DashBorad).csv")
OUTPUT_JSON = Path("data/lmis_dashboard_data.json")


def clean_json_string(s: str) -> str:
    """Clean and fix JSON string for parsing."""
    if not s:
        return ""
    
    # Remove escaped quotes
    s = s.replace('""', '"')
    
    # Try to find JSON array or object
    start_array = s.find('[')
    start_obj = s.find('{')
    
    if start_array >= 0 and (start_obj < 0 or start_array < start_obj):
        # Array starts first
        end = s.rfind(']')
        if end > start_array:
            return s[start_array:end+1]
    elif start_obj >= 0:
        # Object starts first
        end = s.rfind('}')
        if end > start_obj:
            return s[start_obj:end+1]
    
    return s


def parse_lmis_csv(csv_path: Path) -> Dict[str, Any]:
    """
    Parse the LMIS Dashboard CSV file.
    
    Returns:
        Dictionary with all endpoints and their data
    """
    result = {
        "source": "MoL LMIS Dashboard API",
        "parsed_from": str(csv_path),
        "endpoints": {},
        "sample_data": {}
    }
    
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        # Read as text first to handle malformed CSV
        content = f.read()
    
    # Split by rows (handling multi-line JSON in cells)
    lines = content.split('\n')
    
    current_dashboard = ""
    current_chart = ""
    current_endpoint = ""
    current_response = ""
    
    endpoints_found = []
    
    # Parse line by line
    for i, line in enumerate(lines):
        # Skip header
        if i == 0 and 'Dashboard Name' in line:
            continue
        
        # Check for endpoint URLs
        endpoint_match = re.search(r'https://lmis-dashb-api\.mol\.gov\.qa[^\s,"\']+', line)
        if endpoint_match:
            current_endpoint = endpoint_match.group(0).replace('//', '/')
            # Fix double slashes
            current_endpoint = re.sub(r'(?<!:)//+', '/', current_endpoint)
            
            if current_endpoint not in endpoints_found:
                endpoints_found.append(current_endpoint)
        
        # Check for dashboard name at start of line
        if line.startswith('Labor Market Indicators'):
            current_dashboard = 'Labor Market Indicators'
        elif line.startswith('Economic Diversification'):
            current_dashboard = 'Economic Diversification'
        elif line.startswith('Human Capital'):
            current_dashboard = 'Human Capital'
        elif line.startswith('Skills-Based'):
            current_dashboard = 'Skills-Based Forecasting'
        elif line.startswith('Dynamic Labor'):
            current_dashboard = 'Dynamic Labor Market'
        elif line.startswith('Expat Labor'):
            current_dashboard = 'Expat Labor Dynamics'
        elif line.startswith('SMEs'):
            current_dashboard = 'SMEs and Local Businesses'
    
    print(f"Found {len(endpoints_found)} unique endpoints")
    
    # Now extract sample responses
    # Look for JSON arrays/objects in the content
    json_pattern = r'\[\s*\{[^]]+\}\s*\]'
    json_matches = re.findall(json_pattern, content, re.DOTALL)
    
    print(f"Found {len(json_matches)} JSON response samples")
    
    # Store endpoints
    for endpoint in endpoints_found:
        # Extract endpoint name from URL
        name = endpoint.split('/')[-1].replace('-', '_')
        result["endpoints"][name] = {
            "url": endpoint,
            "method": "GET"
        }
    
    # Parse JSON samples
    for i, json_str in enumerate(json_matches[:50]):  # Limit to first 50
        try:
            # Clean up the JSON
            cleaned = json_str.replace('""', '"')
            data = json.loads(cleaned)
            
            # Try to identify which endpoint this belongs to
            if isinstance(data, list) and len(data) > 0:
                sample = data[0]
                
                # Identify by keys
                if 'Qatar_Population' in sample:
                    result["sample_data"]["main_indicators"] = data
                elif 'sdgs' in sample:
                    result["sample_data"]["sdg_indicators"] = data
                elif 'entry' in sample and 'senior' in sample:
                    result["sample_data"]["job_seniority"] = data
                elif 'growth' in str(sample).lower() and 'sector' in str(sample).lower():
                    if 'sector_growth' not in result["sample_data"]:
                        result["sample_data"]["sector_growth"] = data
                elif 'skill' in str(sample).lower():
                    key = f"skills_data_{i}"
                    result["sample_data"][key] = data
                else:
                    result["sample_data"][f"dataset_{i}"] = data
                    
        except json.JSONDecodeError as e:
            continue
    
    return result


def main():
    """Main function."""
    print("=" * 70)
    print("LMIS DASHBOARD CSV PARSER")
    print("=" * 70)
    
    if not INPUT_CSV.exists():
        print(f"ERROR: Input file not found: {INPUT_CSV}")
        return
    
    print(f"\nInput: {INPUT_CSV}")
    print(f"Output: {OUTPUT_JSON}")
    
    # Parse CSV
    data = parse_lmis_csv(INPUT_CSV)
    
    # Save to JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {OUTPUT_JSON}")
    print(f"   - Endpoints: {len(data['endpoints'])}")
    print(f"   - Sample datasets: {len(data['sample_data'])}")
    
    # Print summary
    print("\n📊 ENDPOINTS FOUND:")
    for name, info in data['endpoints'].items():
        print(f"   - {name}: {info['url']}")
    
    print("\n📦 SAMPLE DATA EXTRACTED:")
    for name, records in data['sample_data'].items():
        count = len(records) if isinstance(records, list) else 1
        print(f"   - {name}: {count} records")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()


