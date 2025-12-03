"""
AUDIT: Data flow from fact extraction to Engine B formulas
This reveals if the math is using real data or defaults.
"""

# 1. TYPICAL EXTRACTED FACTS (from World Bank, LMIS, etc.)
sample_facts = [
    {'metric': 'GDP per capita', 'value': 76000, 'source': 'World Bank'},
    {'metric': 'Unemployment rate', 'value': 2.5, 'source': 'LMIS'},
    {'metric': 'Total employment', 'value': 1850000, 'source': 'MOL'},
    {'metric': 'Qatarization rate', 'value': 0.42, 'source': 'LMIS'},
    {'metric': 'Average wage', 'value': 12500, 'source': 'LMIS'},
    {'metric': 'Population growth', 'value': 0.015, 'source': 'World Bank'},
]

print("=" * 70)
print("AUDIT: Data Flow from Fact Extraction to Engine B")
print("=" * 70)

# 2. WHAT parallel_executor.apply_assumptions_to_facts DOES:
print("\n[STEP 1] FACTS EXTRACTED FROM APIs:")
adjusted = {}
for fact in sample_facts:
    indicator = fact.get('indicator', fact.get('metric', '')).lower().replace(' ', '_')
    value = fact.get('value')
    try:
        numeric_value = float(value)
        adjusted[indicator] = numeric_value
        print(f"  ✓ {indicator} = {numeric_value}")
    except:
        pass

# 3. WHAT ENGINE B FORMULAS ACTUALLY EXPECT:
print("\n[STEP 2] WHAT ENGINE B FORMULA VARIABLES EXPECT:")
expected_vars = [
    ('growth_rate', 0.03, 'Monte Carlo / Sensitivity'),
    ('annual_growth', 0.03, 'Monte Carlo fallback'),
    ('base_value', 100000, 'Monte Carlo / Sensitivity'),
    ('initial_value', 100000, 'Monte Carlo fallback'),
    ('annual_growth_rate', 0.03, 'Sensitivity'),
    ('initial_capital', 100000, 'Sensitivity'),
    ('policy_effectiveness', 1.0, 'Sensitivity'),
    ('resource_efficiency', 0.85, 'Sensitivity'),
]

matched = 0
unmatched = 0
for var, default, used_in in expected_vars:
    if var in adjusted:
        print(f"  ✓ {var}: FOUND = {adjusted[var]} (used in {used_in})")
        matched += 1
    else:
        print(f"  ✗ {var}: MISSING → uses default = {default} (used in {used_in})")
        unmatched += 1

# 4. THE PROBLEM
print("\n" + "=" * 70)
print("VERDICT:")
print("=" * 70)
print(f"""
Facts Extracted: {len(adjusted)} metrics with REAL data
Formula Variables Expected: {len(expected_vars)} hardcoded names
Variables Matched: {matched}
Variables Using Defaults: {unmatched}

THE PROBLEM:
- Extracted facts have keys like: 'gdp_per_capita', 'unemployment_rate', 'qatarization_rate'
- But formulas expect: 'growth_rate', 'base_value', 'policy_effectiveness'
- These DON'T MATCH → formulas use DEFAULT values (0.03, 100000, etc.)

RESULT: Engine B math is CORRECT but uses GENERIC DEFAULTS, not actual extracted data!

To be truly domain-agnostic and use real data, we need DYNAMIC VARIABLE MAPPING:
1. Extract fact types semantically (e.g., "GDP" → base_value, "growth" → growth_rate)
2. OR let the formula be generated from actual fact keys
3. OR use LLM to map extracted facts to formula variables
""")

