"""Debug JSON parsing issue."""
import json

# This is what the LLM is outputting (with literal newlines for formatting)
sample_json = """{
  "title": "Test Title",
  "summary": "Test summary",
  "metrics": {"test": 1.0},
  "analysis": "Line 1
Line 2",
  "recommendations": ["Rec 1"],
  "confidence": 0.75,
  "citations": ["test"],
  "data_quality_notes": "Notes"
}"""

print("Original JSON:")
print(sample_json[:200])
print()

# Try to parse it
try:
    data = json.loads(sample_json)
    print("✓ Parsing successful!")
    print(f"  Title: {data['title']}")
except json.JSONDecodeError as e:
    print(f"✗ Parsing failed: {e}")
    print(f"  Error at position {e.pos}: '{sample_json[max(0,e.pos-10):e.pos+10]}'")
