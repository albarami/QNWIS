#!/usr/bin/env python3
"""Quick test to debug JSON parsing issue."""

import json
import sys

test_json = r'''{
  "title": "Qatar's Gender Employment Distribution",
  "summary": "Qatar shows [Per extraction: '55.00%' from sql 2025-11-19] female employment share",
  "metrics": {
    "female_employment_share": 55.0
  },
  "analysis": "### Analysis text here",
  "recommendations": ["Rec 1"],
  "confidence": 0.15,
  "citations": ["sql"],
  "data_quality_notes": "Notes"
}'''

print("Testing JSON parsing...")
print(f"First 50 chars: {repr(test_json[:50])}")
print(f"Character codes of first 10 chars: {[ord(c) for c in test_json[:10]]}")

try:
    data = json.loads(test_json)
    print("✅ JSON parsed successfully!")
    print(f"Title: {data.get('title')}")
except json.JSONDecodeError as e:
    print(f"❌ JSON parse error: {e}")
    print(f"Error position: {e.pos}")
    if hasattr(e, 'pos') and e.pos < len(test_json):
        start = max(0, e.pos - 20)
        end = min(len(test_json), e.pos + 40)
        print(f"Context around error: {repr(test_json[start:end])}")
