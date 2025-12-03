"""Test Monte Carlo formula accuracy."""
import httpx
import math

print("=" * 60)
print("VERIFYING MONTE CARLO FORMULA ACCURACY")
print("=" * 60)
print()
print("Formula: base_value * (1 + growth_rate) ** 5")
print()

# Expected calculation
base = 100000
growth = 0.05
expected = base * (1 + growth) ** 5
print("EXPECTED (with mean values):")
print(f"  base_value = {base}")
print(f"  growth_rate = {growth}")
print(f"  Expected = {base} * (1 + {growth})^5 = {expected:.2f}")
print()

# Test 1: Near-zero variance
print("TEST 1: Near-zero variance (should match expected)")
payload = {
    "variables": {
        "growth_rate": {"distribution": "normal", "mean": 0.05, "std": 0.0001},
        "base_value": {"distribution": "normal", "mean": 100000, "std": 1}
    },
    "formula": "base_value * (1 + growth_rate) ** 5",
    "success_condition": "result > 120000",
    "n_simulations": 10000
}
resp = httpx.post("http://localhost:8001/compute/monte_carlo", json=payload, timeout=30)
result = resp.json()
print(f"  Monte Carlo mean_result: {result['mean_result']:.2f}")
print(f"  Difference: {result['mean_result'] - expected:.2f}")
accuracy = (result['mean_result'] / expected) * 100
print(f"  Accuracy: {accuracy:.4f}%")
if 99.9 < accuracy < 100.1:
    print("  ✅ FORMULA IS ACCURATE")
else:
    print("  ❌ FORMULA MAY HAVE ISSUES")
print()

# Test 2: Different growth rates
print("TEST 2: Different growth rates (verify varied success rates)")
for growth in [0.02, 0.05, 0.08]:
    payload = {
        "variables": {
            "growth_rate": {"distribution": "normal", "mean": growth, "std": 0.01},
            "base_value": {"distribution": "normal", "mean": 100000, "std": 5000}
        },
        "formula": "base_value * (1 + growth_rate) ** 5",
        "success_condition": "result > 120000",
        "n_simulations": 10000
    }
    resp = httpx.post("http://localhost:8001/compute/monte_carlo", json=payload, timeout=30)
    result = resp.json()
    exp = 100000 * (1 + growth) ** 5
    print(f"  Growth {growth*100:.0f}%: expected={exp:.0f}, actual={result['mean_result']:.0f}, success={result['success_rate']*100:.1f}%")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print("If accuracy is ~100% and success rates VARY by growth rate,")
print("then the Monte Carlo formula is computing correctly.")

