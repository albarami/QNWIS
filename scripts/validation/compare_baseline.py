"""
QNWIS Baseline Comparison Tool.

Compares current validation results against baseline consultant performance
to demonstrate efficiency gains.

Usage:
    python scripts/validation/compare_baseline.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_results(results_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load current validation results.
    
    Args:
        results_dir: Directory containing result JSON files
        
    Returns:
        Dict mapping case name to result data
    """
    out = {}
    for p in results_dir.glob("*.json"):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            result = j.get("result", {})
            case_name = result.get("case")
            if case_name:
                out[case_name] = result
        except Exception as e:
            print(f"Warning: Failed to load {p}: {e}", file=sys.stderr)
    
    return out


def load_baselines(baseline_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load baseline consultant performance data.
    
    Args:
        baseline_dir: Directory containing baseline JSON files
        
    Returns:
        Dict mapping case name to baseline data
    """
    out = {}
    for p in baseline_dir.glob("*.json"):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            case_name = j.get("case")
            if case_name:
                out[case_name] = j
        except Exception as e:
            print(f"Warning: Failed to load {p}: {e}", file=sys.stderr)
    
    return out


def compute_improvements(
    results: Dict[str, Dict[str, Any]],
    baselines: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Compute improvement metrics vs baseline.
    
    Args:
        results: Current results
        baselines: Baseline performance
        
    Returns:
        List of improvement records
    """
    improvements = []
    
    for case_name, result in results.items():
        baseline = baselines.get(case_name)
        if not baseline:
            continue
        
        # Extract metrics
        latency_now = result.get("latency_ms", 0)
        latency_then = baseline.get("latency_ms", 0)
        
        # Compute gains
        if latency_then > 0:
            throughput_gain = round(latency_then / max(latency_now, 1), 2)
            time_saved_pct = round(
                ((latency_then - latency_now) / latency_then) * 100, 1
            )
        else:
            throughput_gain = 1.0
            time_saved_pct = 0.0
        
        # Quality comparison
        quality_now = result.get("verification_passed", False)
        quality_then = baseline.get("verified", False)
        
        # Cost comparison (if available)
        cost_now = baseline.get("cost_qar", 0)
        cost_then = baseline.get("cost_qar", 0)
        
        improvements.append({
            "case": case_name,
            "latency_ms_now": latency_now,
            "latency_ms_then": latency_then,
            "throughput_gain_x": throughput_gain,
            "time_saved_pct": time_saved_pct,
            "quality_now": quality_now,
            "quality_then": quality_then,
            "quality_improved": quality_now and not quality_then,
            "cost_now_qar": cost_now,
            "cost_then_qar": cost_then,
        })
    
    return improvements


def main() -> None:
    """Main entry point."""
    root = Path(".").resolve()
    
    # Load data
    results = load_results(root / "validation" / "results")
    baselines = load_baselines(root / "validation" / "baselines")
    
    if not results:
        print("Error: No results found in validation/results", file=sys.stderr)
        sys.exit(1)
    
    if not baselines:
        print("Warning: No baselines found in validation/baselines", file=sys.stderr)
        print("Skipping comparison", file=sys.stderr)
        sys.exit(0)
    
    # Compute improvements
    improvements = compute_improvements(results, baselines)
    
    # Calculate summary statistics
    if improvements:
        avg_throughput = sum(i["throughput_gain_x"] for i in improvements) / len(improvements)
        avg_time_saved = sum(i["time_saved_pct"] for i in improvements) / len(improvements)
        quality_improvements = sum(1 for i in improvements if i["quality_improved"])
        
        summary = {
            "total_cases_compared": len(improvements),
            "avg_throughput_gain_x": round(avg_throughput, 2),
            "avg_time_saved_pct": round(avg_time_saved, 1),
            "quality_improvements": quality_improvements,
            "improvements": improvements
        }
    else:
        summary = {
            "total_cases_compared": 0,
            "improvements": []
        }
    
    # Output results
    print(json.dumps(summary, indent=2))
    
    # Write to file
    output_path = root / "validation" / "baseline_comparison.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n[compare] Wrote comparison to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
