"""Test citation format generation."""
from src.qnwis.orchestration.citation_injector import CitationInjector

# Test the format generation
injector = CitationInjector()

test_value = 0.10
formats = injector._generate_number_formats(test_value)

print(f"Formats generated for {test_value}:")
for fmt in sorted(formats):
    print(f"  - '{fmt}'")

print(f"\nTotal: {len(formats)} formats")

# Check if "0.10%" is in the list
if "0.10%" in formats:
    print("\n✅ '0.10%' IS in the generated formats")
else:
    print("\n❌ '0.10%' is NOT in the generated formats")

# Check fuzzy matching
print("\n--- Fuzzy Matching Tests ---")
test_pairs = [
    ("0.10%", "0.10%"),
    ("0.10%", "0.1%"),
    ("0.10%", "10.0%"),
    ("0.10", "0.10%"),
]

for num1, num2 in test_pairs:
    match = injector._fuzzy_match(num1, num2)
    print(f"  '{num1}' ≈ '{num2}': {match}")
