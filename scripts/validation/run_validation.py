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
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import requests
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


ACCEPTANCE_LIMITS = {
    "simple": 10_000,
    "medium": 30_000,
    "complex": 90_000,
    "dashboard": 3_000,
}


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for HTTP executions."""

    max_attempts: int
    base_delay: float


class PayloadRedactor:
    """Redact sensitive values from validation payloads."""

    def __init__(
        self,
        field_rules: Sequence[Dict[str, Any]] | None,
        pattern_rules: Sequence[Dict[str, Any]] | None,
    ) -> None:
        self._field_rules: List[Tuple[Tuple[str, ...], str]] = []
        for rule in field_rules or []:
            keys = tuple(k.lower() for k in (rule.get("keys") or []))
            if not keys:
                continue
            replacement = str(rule.get("replacement", "[REDACTED]"))
            self._field_rules.append((keys, replacement))

        self._pattern_rules: List[Tuple[re.Pattern[str], str]] = []
        for rule in pattern_rules or []:
            pattern = rule.get("pattern")
            if not pattern:
                continue
            ignore_case = rule.get("ignore_case", True)
            compiled = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
            replacement = str(rule.get("replacement", "[REDACTED]"))
            self._pattern_rules.append((compiled, replacement))

    @classmethod
    def from_path(cls, path: Path) -> "PayloadRedactor":
        """Create a redactor from a YAML file."""
        if not path.exists():
            return cls([], [])

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(data.get("fields"), data.get("patterns"))

    def apply(self, payload: Any) -> Any:
        """Return a redacted deep copy of the payload."""
        return self._scrub(payload)

    def _scrub(self, value: Any) -> Any:
        if isinstance(value, dict):
            redacted: Dict[str, Any] = {}
            for key, nested in value.items():
                masked = self._maybe_redact_field(key, nested)
                redacted[key] = self._scrub(masked)
            return redacted
        if isinstance(value, list):
            return [self._scrub(v) for v in value]
        if isinstance(value, tuple):
            return tuple(self._scrub(v) for v in value)
        if isinstance(value, str):
            return self._redact_text(value)
        return value

    def _maybe_redact_field(self, key: str, value: Any) -> Any:
        """Apply field-based replacements for direct matches."""
        key_lower = key.lower()
        for keys, replacement in self._field_rules:
            if key_lower in keys:
                return replacement
        return value

    def _redact_text(self, text: str) -> str:
        redacted = text
        for pattern, replacement in self._pattern_rules:
            redacted = pattern.sub(replacement, redacted)
        return redacted


def _normalize_headers(headers: Mapping[str, Any] | None) -> Dict[str, str]:
    """Normalize header keys to lower-case for easier matching."""
    if not headers:
        return {}
    return {str(k).lower(): str(v) for k, v in headers.items()}


def _extract_rate_limits(headers: Mapping[str, str]) -> Dict[str, float | None]:
    """Extract rate-limit information from HTTP headers."""
    def _to_float(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return {
        "limit": _to_float(headers.get("x-ratelimit-limit")),
        "remaining": _to_float(headers.get("x-ratelimit-remaining")),
        "reset": _to_float(headers.get("x-ratelimit-reset")),
    }


def _has_csrf_cookie(cookies: Mapping[str, Any] | None) -> bool:
    """Return True if a CSRF cookie is present."""
    if not cookies:
        return False
    return any("csrf" in key.lower() for key in cookies.keys())


def _percentile(values: Sequence[float], pct: float) -> float | None:
    """Compute percentile for a list of values."""
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    data = sorted(values)
    k = (len(data) - 1) * pct
    lower = int(k)
    upper = min(lower + 1, len(data) - 1)
    weight = k - lower
    return (data[lower] * (1 - weight)) + (data[upper] * weight)


def _write_kpi_summary(summary_rows: List[Dict[str, Any]], output_path: Path) -> None:
    """Render KPI summary markdown for executives."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Validation KPI Summary\n\n"]

    if not summary_rows:
        lines.append("_No validation results available. Run the harness first._\n")
        output_path.write_text("".join(lines), encoding="utf-8")
        return

    total = len(summary_rows)
    pass_count = sum(1 for row in summary_rows if row.get("pass"))
    verification_pass = sum(1 for row in summary_rows if row.get("verification_passed"))

    pass_pct = (pass_count / total) * 100 if total else 0
    verification_pct = (verification_pass / total) * 100 if total else 0

    lines.append(f"- **Pass rate:** {pass_count}/{total} ({pass_pct:.1f}%)\n")
    lines.append(
        f"- **Verification pass:** {verification_pass}/{total} ({verification_pct:.1f}%)\n\n"
    )

    lines.append("| Tier | Envelope (ms) | p50 latency (ms) | p95 latency (ms) |\n")
    lines.append("|------|---------------|------------------|------------------|\n")

    for tier in ("dashboard", "simple", "medium", "complex"):
        latencies = [row["latency_ms"] for row in summary_rows if row["tier"] == tier]
        p50 = _percentile(latencies, 0.5)
        p95 = _percentile(latencies, 0.95)

        def _fmt(value: float | None) -> str:
            return f"{value:.2f}" if value is not None else "N/A"

        envelope = ACCEPTANCE_LIMITS.get(tier, 30_000)
        lines.append(
            f"| {tier.title()} | {envelope} | {_fmt(p50)} | {_fmt(p95)} |\n"
        )

    lines.append(
        "\n_Compare these latencies with `/metrics` (histograms such as "
        "`qnwis_validation_latency_ms`) to confirm production SLO alignment._\n"
    )

    output_path.write_text("".join(lines), encoding="utf-8")


def _env_int(name: str, default: int) -> int:
    """Read integer environment variable with fallback."""
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    """Read float environment variable with fallback."""
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


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


def _exec_case_http(
    case: Dict[str, Any],
    base_url: str,
    *,
    session: requests.Session,
    retry_policy: RetryPolicy,
    rng: random.Random,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute case via HTTP request with retry/backoff.
    
    Args:
        case: Case specification
        base_url: Base URL of QNWIS service
        session: Shared requests session
        retry_policy: Retry configuration
        rng: Random generator for jitter
        verbose: Emit retry logs when True
        
    Returns:
        Result dict with status, data, timing, and headers
    """
    method = (case.get("method") or "GET").upper()
    url = base_url.rstrip("/") + case["endpoint"]
    headers = dict(case.get("headers") or {})
    api_key = os.getenv("QNWIS_API_KEY")
    if api_key and not any(k.lower() == "authorization" for k in headers):
        headers["Authorization"] = f"Bearer {api_key}"
    csrf_token = os.getenv("QNWIS_CSRF_TOKEN")
    if csrf_token and not any(k.lower() == "x-csrf-token" for k in headers):
        headers["X-CSRF-Token"] = csrf_token
        session.cookies.set("csrftoken", csrf_token)
    payload = case.get("payload") or {}
    timeout = case.get("timeout", 120)
    retry_statuses = set(case.get("retry_statuses") or (429, 503))
    
    attempts = max(retry_policy.max_attempts, 1)
    
    for attempt in range(1, attempts + 1):
        t0 = time.perf_counter()
        try:
            response = session.request(
                method,
                url,
                json=payload if method in ("POST", "PUT", "PATCH") else None,
                headers=headers,
                timeout=timeout
            )
            t1 = time.perf_counter()
            
            if (
                response.status_code in retry_statuses
                and attempt < attempts
            ):
                if verbose:
                    print(
                        f"  [retry] HTTP {response.status_code} for {url} "
                        f"(attempt {attempt}/{attempts - 1})"
                    )
                backoff = retry_policy.base_delay * (2 ** (attempt - 1))
                jitter = rng.uniform(0, retry_policy.base_delay)
                time.sleep(backoff + jitter)
                continue
            
            try:
                data = response.json()
            except ValueError:
                data = {"raw": response.text}
            
            return {
                "status": response.status_code,
                "data": data,
                "timing": (t0, t1),
                "headers": dict(response.headers),
                "cookies": response.cookies.get_dict(),
            }
        
        except requests.exceptions.Timeout:
            t1 = time.perf_counter()
            if attempt >= attempts:
                return {
                    "status": 504,
                    "data": {"error": "Request timeout"},
                    "timing": (t0, t1),
                    "headers": {},
                    "cookies": {},
                }
            if verbose:
                print(
                    f"  [retry] Timeout contacting {url} "
                    f"(attempt {attempt}/{attempts - 1})"
                )
            backoff = retry_policy.base_delay * (2 ** (attempt - 1))
            jitter = rng.uniform(0, retry_policy.base_delay)
            time.sleep(backoff + jitter)
            continue
        
        except requests.exceptions.RequestException as exc:
            t1 = time.perf_counter()
            if attempt >= attempts:
                return {
                    "status": 500,
                    "data": {"error": str(exc)},
                    "timing": (t0, t1),
                    "headers": {},
                    "cookies": {},
                }
            if verbose:
                print(
                    f"  [retry] Error contacting {url}: {exc} "
                    f"(attempt {attempt}/{attempts - 1})"
                )
            backoff = retry_policy.base_delay * (2 ** (attempt - 1))
            jitter = rng.uniform(0, retry_policy.base_delay)
            time.sleep(backoff + jitter)
    
    # Fallback; should not reach due to returns above
    return {
        "status": 500,
        "data": {"error": "Unknown execution failure"},
        "timing": (time.perf_counter(), time.perf_counter()),
        "headers": {},
        "cookies": {},
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
        
        return {
            "status": r.status_code,
            "data": data,
            "timing": (t0, t1),
            "headers": dict(r.headers),
            "cookies": dict(r.cookies.items()),
        }
    
    except Exception as e:
        t1 = time.perf_counter()
        return {
            "status": 500,
            "data": {"error": str(e)},
            "timing": (t0, t1),
            "headers": {},
            "cookies": {},
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
    
    return {
        "status": 200,
        "data": data,
        "timing": (t0, t1),
        "headers": {},
        "cookies": {},
    }


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
    ap.add_argument(
        "--redaction-rules",
        default="validation/redaction_rules.yaml",
        help="Path to YAML file describing redaction rules"
    )
    ap.add_argument(
        "--max-retries",
        type=int,
        default=_env_int("QNWIS_VALIDATION_MAX_RETRIES", 3),
        help="Maximum HTTP retries on 429/503/timeouts (default: env or 3)"
    )
    ap.add_argument(
        "--retry-base",
        type=float,
        default=_env_float("QNWIS_VALIDATION_RETRY_BASE", 0.75),
        help="Base delay in seconds for exponential backoff (default 0.75)"
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=_env_int("QNWIS_VALIDATION_SEED", 1337),
        help="Seed for deterministic jitter/backoff (default 1337)"
    )
    
    args = ap.parse_args()
    
    rng = random.Random(args.seed)
    retry_policy = RetryPolicy(
        max_attempts=max(1, args.max_retries),
        base_delay=max(args.retry_base, 0.1),
    )
    
    # Resolve paths
    root = Path(".").resolve()
    cases_dir = root / args.cases
    outdir = root / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    redactor_path = root / args.redaction_rules
    redactor = PayloadRedactor.from_path(redactor_path)
    
    if args.verbose:
        print(f"[validation] Using redaction rules from {redactor_path}")
    
    # Load cases
    if args.verbose:
        print(f"[validation] Loading cases from {cases_dir}")
    
    cases = _load_cases(cases_dir)
    print(f"[validation] Loaded {len(cases)} cases")
    
    needs_http_session = any(
        (case.get("mode") or args.mode) == "http"
        for case in cases
    )
    http_session = requests.Session() if needs_http_session else None
    
    # Execute cases
    summary_rows: List[Dict[str, Any]] = []
    failures = 0
    
    try:
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
                if http_session is None:
                    http_session = requests.Session()
                res = runner(
                    case,
                    args.base_url,
                    session=http_session,
                    retry_policy=retry_policy,
                    rng=rng,
                    verbose=args.verbose,
                )
            else:
                res = runner(case)
            
            body = redactor.apply(res.get("data"))
            if not isinstance(body, dict):
                body = {"value": body}
            
            headers = _normalize_headers(res.get("headers"))
            rate_limits = _extract_rate_limits(headers)
            csrf_cookie_present = _has_csrf_cookie(res.get("cookies"))
            
            metadata = body.get("metadata") or {}
            audit_id = metadata.get("audit_id")
            
            # Compute metrics
            latency = compute_latency_ms(res["timing"])
            cov = citation_coverage(body)
            fresh = freshness_present(body)
            verified = verification_passed(body)
            tier = case.get("tier", "medium")
            
            # Compute pass/fail
            ok = compute_score(latency, tier, verified, cov, fresh) and (
                res["status"] in (200, 201)
            )
            
            if not ok:
                failures += 1
                if args.verbose:
                    print(f"  [FAIL] status={res['status']}, latency={latency:.2f}ms")
            elif args.verbose:
                print(f"  [PASS] latency={latency:.2f}ms")
            
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
                "mode": mode,
                "audit_id": audit_id,
                "audit_id_present": bool(audit_id),
                "rate_limit_limit": rate_limits["limit"],
                "rate_limit_remaining": rate_limits["remaining"],
                "rate_limit_reset": rate_limits["reset"],
                "csrf_cookie_present": csrf_cookie_present,
            }
            
            # Write detailed JSON
            detail_path = outdir / f"{case_name}.json"
            detail_path.write_text(
                json.dumps(
                    {
                        "spec": case,
                        "result": rec,
                        "body": body
                    },
                    indent=2
                ),
                encoding="utf-8"
            )
            
            summary_rows.append(rec)
    finally:
        if http_session:
            http_session.close()
    
    # Write summary CSV
    summary_path = root / "validation" / "summary.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        if summary_rows:
            w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            w.writeheader()
            w.writerows(summary_rows)
    
    kpi_path = root / "docs" / "validation" / "KPI_SUMMARY.md"
    _write_kpi_summary(summary_rows, kpi_path)
    
    # Print summary
    passed = len(summary_rows) - failures
    print(f"\n[validation] Results: {passed}/{len(summary_rows)} cases passed")
    print(f"[validation] Summary written to {summary_path}")
    print(f"[validation] Details written to {outdir}")
    print(f"[validation] KPI summary written to {kpi_path}")
    
    # Exit with failure if any cases failed
    if failures:
        print(f"\n[validation] [FAIL] {failures} case(s) failed")
        sys.exit(1)
    else:
        print("\n[validation] [PASS] All cases passed")


if __name__ == "__main__":
    main()
