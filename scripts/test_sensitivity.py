"""Test the corrected sensitivity formula."""
import httpx

# Test sensitivity with the corrected formula
payload = {
    'base_values': {
        'annual_growth_rate': 0.03,
        'initial_capital': 100000,
        'policy_effectiveness': 1.0,
        'resource_efficiency': 0.85
    },
    'formula': 'initial_capital * (1 + annual_growth_rate) ** 5 * policy_effectiveness * resource_efficiency',
    'ranges': {
        'annual_growth_rate': {'low': 0.015, 'high': 0.045},
        'initial_capital': {'low': 80000, 'high': 120000},
        'policy_effectiveness': {'low': 0.7, 'high': 1.3},
        'resource_efficiency': {'low': 0.68, 'high': 1.02}
    },
    'n_steps': 10
}

r = httpx.post('http://localhost:8001/compute/sensitivity', json=payload, timeout=30)
print('Status:', r.status_code)
d = r.json()

# Show calculated contributions
if d.get('parameter_impacts'):
    total_swing = sum(p['swing'] for p in d['parameter_impacts'])
    print(f'Total Swing: {total_swing:.2f}')
    print('Contributions:')
    for p in d['parameter_impacts']:
        contrib = p['swing'] / total_swing * 100 if total_swing > 0 else 0
        print(f"  {p['name']}: {contrib:.1f}% (swing={p['swing']:.2f})")
else:
    print('No parameter impacts returned!')
    print('Response:', d)

