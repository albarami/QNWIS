"""
QNWIS Validation Runner.

Executes validation cases against live system or in-process TestClient,
measures metrics, and produces JSON/CSV results.

Usage:
    python scripts/validation/run_validation.py --mode http --base-url http://localhost:8000
    python scripts/validation/run_validation.py --mode inproc
    python scripts/validation/run_validation.py --mode echo  # CI/testing
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.qnwis.validation.metrics import (
    citation_coverage,
    compute_latency_ms,
    compute_score,
    freshness_present,
    verification_passed,
)


def _load_cases(dir_path: Path) -> List[Dict[str, Any]]:
    """
    Load all YAML validation cases from directory.
    
    Args:
        dir_path: Directory containing *.yaml case files
        
    Returns:
        List of case specifications
    """
    cases = []
    for p in sorted(dir_path.glob("*.yaml")):
        with p.open("r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)
            spec["__path__"] = str(p)
            cases.append(spec)
    
    if not cases:
        raise SystemExit("No validation cases found")
    
    return cases


def _exec_case_http(case: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    """
    Execute case via HTTP request.
    
    Args:
        case: Case specification
        base_url: Base URL of QNWIS service
        
    Returns:
        Result dict with status, data, timing
    """
    import requests
    
    method = (case.get("method") or "GET").upper()
    url = base_url.rstrip("/") + case["endpoint"]
    headers = case.get("headers") or {}
    payload = case.get("payload") or {}
    timeout = case.get("timeout", 120)
    
    t0 = time.perf_counter()
    try:
        r = requests.request(
            method,
            url,
            json=payload if method in ("POST", "PUT", "PATCH") else None,
            headers=headers,
            timeout=timeout
        )
        t1 = time.perf_counter()
        
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        
        return {"status": r.status_code, "data": data, "timing": (t0, t1)}
    
    except requests.exceptions.Timeout:
        t1 = time.perf_counter()
        return {
            "status": 504,
            "data": {"error": "Request timeout"},
            "timing": (t0, t1)
        }
    except Exception as e:
        t1 = time.perf_counter()
        return {
            "status": 500,
            "data": {"error": str(e)},
            "timing": (t0, t1)
        }


def _exec_case_inproc(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute case via in-process TestClient.
    
    Args:
        case: Case specification
        
    Returns:
        Result dict with status, data, timing
    """
    from importlib import import_module
    from fastapi.testclient import TestClient
    
    try:
        # Import the FastAPI app
        app_module = import_module("src.qnwis.api.server")
        app = getattr(app_module, "create_app")()
        client = TestClient(app)
        
        method = (case.get("method") or "GET").upper()
        payload = case.get("payload") or {}
        
        t0 = time.perf_counter()
        r = client.request(method, case["endpoint"], json=payload)
        t1 = time.perf_counter()
        
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        
        return {"status": r.status_code, "data": data, "timing": (t0, t1)}
    
    except Exception as e:
        t1 = time.perf_counter()
        return {
            "status": 500,
            "data": {"error": str(e)},
            "timing": (t0, t1)
        }


def _exec_case_echo(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute case in echo mode (for CI/testing).
    
    Args:
        case: Case specification
        
    Returns:
        Simulated result with expected response
    """
    t0 = time.perf_counter()
    time.sleep(0.01)  # Simulate minimal latency
    t1 = time.perf_counter()
    
    # Use expected_response if provided, otherwise create default
    data = case.get("expected_response") or {
        "metadata": {
            "verification": True,
            "freshness": {"LMIS": "recent"},
            "citations": ["LMIS"]
        }
    }
    
    return {"status": 200, "data": data, "timing": (t0, t1)}


def main() -> None:
    """Main validation runner entry point."""
    ap = argparse.ArgumentParser(
        description="QNWIS Validation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--cases",
        default="validation/cases",
        help="Directory containing validation case YAML files"
    )
    ap.add_argument(
        "--mode",
        choices=["http", "inproc", "echo"],
        default=os.getenv("QNWIS_VALIDATION_MODE", "http"),
        help="Execution mode: http (live), inproc (TestClient), echo (CI)"
    )
    ap.add_argument(
        "--base-url",
        default=os.getenv("QNWIS_BASE_URL", "http://localhost:8000"),
        help="Base URL for HTTP mode"
    )
    ap.add_argument(
        "--outdir",
        default="validation/results",
        help="Output directory for results"
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = ap.parse_args()
    
    # Resolve paths
    root = Path(".").resolve()
    cases_dir = root / args.cases
    outdir = root / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Load cases
    if args.verbose:
        print(f"[validation] Loading cases from {cases_dir}")
    
    cases = _load_cases(cases_dir)
    print(f"[validation] Loaded {len(cases)} cases")
    
    # Execute cases
    summary_rows = []
    failures = 0
    
    for i, case in enumerate(cases, 1):
        case_name = case.get("name") or Path(case["__path__"]).stem
        
        if args.verbose:
            print(f"[validation] [{i}/{len(cases)}] Executing {case_name}...")
        
        # Determine execution mode
        mode = case.get("mode") or args.mode
        
        # Select runner
        runners = {
            "http": _exec_case_http,
            "inproc": _exec_case_inproc,
            "echo": _exec_case_echo
        }
        runner = runners[mode]
        
        # Execute
        if runner is _exec_case_http:
            res = runner(case, args.base_url)
        else:
            res = runner(case)
        
        # Compute metrics
        latency = compute_latency_ms(res["timing"])
        cov = citation_coverage(res["data"])
        fresh = freshness_present(res["data"])
        verified = verification_passed(res["data"])
        tier = case.get("tier", "medium")
        
        # Compute pass/fail
        ok = compute_score(latency, tier, verified, cov, fresh) and (
            res["status"] in (200, 201)
        )
        
        if not ok:
            failures += 1
            if args.verbose:
                print(f"  ✗ FAILED: status={res['status']}, latency={latency:.2f}ms")
        elif args.verbose:
            print(f"  ✓ PASSED: latency={latency:.2f}ms")
        
        # Build result record
        rec = {
            "case": case_name,
            "endpoint": case["endpoint"],
            "tier": tier,
            "status": res["status"],
            "latency_ms": round(latency, 2),
            "citation_coverage": round(cov, 2),
            "freshness_present": fresh,
            "verification_passed": verified,
            "pass": ok,
        }
        
        # Write detailed JSON
        detail_path = outdir / f"{case_name}.json"
        detail_path.write_text(
            json.dumps(
                {
                    "spec": case,
                    "result": rec,
                    "body": res["data"]
                },
                indent=2
            ),
            encoding="utf-8"
        )
        
        summary_rows.append(rec)
    
    # Write summary CSV
    summary_path = root / "validation" / "summary.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        if summary_rows:
            w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            w.writeheader()
            w.writerows(summary_rows)
    
    # Print summary
    passed = len(summary_rows) - failures
    print(f"\n[validation] Results: {passed}/{len(summary_rows)} cases passed")
    print(f"[validation] Summary written to {summary_path}")
    print(f"[validation] Details written to {outdir}")
    
    # Exit with failure if any cases failed
    if failures:
        print(f"\n[validation] ✗ {failures} case(s) failed")
        sys.exit(1)
    else:
        print("\n[validation] ✓ All cases passed")


if __name__ == "__main__":
    main()
