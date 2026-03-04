"""E2E Pipeline Monitor — sends a real question and traces every stage.

Usage:
    python scripts/e2e_monitor.py "What is the current Qatarization rate in the private sector?"
    python scripts/e2e_monitor.py --all   # runs all 3 test questions
"""

import json
import sys
import time
from datetime import datetime

import httpx

BASE_URL = "http://localhost:8000"
TIMEOUT = httpx.Timeout(connect=10, read=7200, write=30, pool=30)


def stream_question(question: str, debate_depth: str = "standard") -> dict:
    """Send question via SSE and collect all events."""
    print(f"\n{'='*80}")
    print(f"QUESTION: {question}")
    print(f"DEBATE DEPTH: {debate_depth}")
    print(f"TIME: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")

    payload = {
        "question": question,
        "provider": "azure",
        "debate_depth": debate_depth,
    }

    stages = {}
    events = []
    debate_turns = []
    errors = []
    start = time.time()

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            with client.stream(
                "POST",
                f"{BASE_URL}/api/v1/council/stream",
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status_code != 200:
                    print(f"ERROR: HTTP {response.status_code}")
                    body = response.read().decode()
                    print(body[:500])
                    return {"error": body, "status_code": response.status_code}

                buffer = ""
                for chunk in response.iter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        event_text, buffer = buffer.split("\n\n", 1)
                        for line in event_text.strip().split("\n"):
                            if line.startswith("data: "):
                                data_str = line[6:]
                                try:
                                    data = json.loads(data_str)
                                except json.JSONDecodeError:
                                    continue

                                events.append(data)
                                stage = data.get("stage", "unknown")
                                status = data.get("status", "")
                                elapsed = time.time() - start

                                if stage not in stages:
                                    stages[stage] = {
                                        "first_seen": elapsed,
                                        "events": 0,
                                        "statuses": [],
                                    }
                                stages[stage]["events"] += 1
                                stages[stage]["statuses"].append(status)
                                stages[stage]["last_seen"] = elapsed

                                if stage == "debate" and data.get("data"):
                                    turn_data = data["data"]
                                    if isinstance(turn_data, dict):
                                        agent = turn_data.get("agent", "")
                                        turn_num = turn_data.get("turn", "")
                                        phase = turn_data.get("phase", "")
                                        if agent or turn_num:
                                            debate_turns.append({
                                                "turn": turn_num,
                                                "agent": agent,
                                                "phase": phase,
                                            })

                                if status == "error":
                                    err_msg = data.get("data", {})
                                    if isinstance(err_msg, dict):
                                        err_msg = err_msg.get("error", str(err_msg))
                                    errors.append(f"[{stage}] {err_msg}")

                                indicator = "+" if status == "complete" else "." if status == "in_progress" else "!" if status == "error" else ">"
                                print(f"  [{elapsed:7.1f}s] {indicator} {stage}: {status}", end="")
                                if data.get("data") and isinstance(data["data"], dict):
                                    summary_keys = ["complexity", "question_type", "sources_count", "facts_count", "scenarios_count", "debate_turns", "confidence"]
                                    for k in summary_keys:
                                        if k in data["data"]:
                                            print(f" | {k}={data['data'][k]}", end="")
                                print()

                                if stage == "done" and status == "complete":
                                    break

    except httpx.ReadTimeout:
        errors.append("TIMEOUT: SSE stream timed out")
        print("\nTIMEOUT: Stream exceeded timeout")
    except Exception as e:
        errors.append(f"EXCEPTION: {e}")
        print(f"\nEXCEPTION: {e}")

    total_time = time.time() - start

    print(f"\n{'─'*80}")
    print(f"PIPELINE SUMMARY")
    print(f"{'─'*80}")
    print(f"Total time: {total_time:.1f}s")
    print(f"Total SSE events: {len(events)}")
    print(f"Errors: {len(errors)}")
    print(f"\nStage Progression:")
    for stage_name, info in stages.items():
        duration = info["last_seen"] - info["first_seen"]
        print(f"  {stage_name:25s} | {info['events']:3d} events | {info['first_seen']:7.1f}s - {info['last_seen']:7.1f}s ({duration:.1f}s)")

    if debate_turns:
        agents_seen = set(t["agent"] for t in debate_turns if t["agent"])
        phases_seen = set(t["phase"] for t in debate_turns if t["phase"])
        print(f"\nDebate: {len(debate_turns)} turns")
        print(f"  Agents: {', '.join(sorted(agents_seen)) if agents_seen else 'N/A'}")
        print(f"  Phases: {', '.join(sorted(phases_seen)) if phases_seen else 'N/A'}")

    if errors:
        print(f"\nERRORS:")
        for e in errors:
            print(f"  {e}")

    final_event = events[-1] if events else {}
    final_data = final_event.get("data", {}) if isinstance(final_event.get("data"), dict) else {}

    synthesis = final_data.get("synthesis", final_data.get("final_synthesis", ""))
    confidence = final_data.get("confidence", final_data.get("confidence_score", ""))
    verdict = final_data.get("debate_verdict", "")

    if synthesis:
        preview = synthesis[:300] if isinstance(synthesis, str) else str(synthesis)[:300]
        print(f"\nSynthesis preview: {preview}...")
    if confidence:
        print(f"Confidence: {confidence}")
    if verdict:
        print(f"Verdict: {str(verdict)[:200]}")

    print(f"\n{'='*80}\n")

    return {
        "question": question,
        "total_time": total_time,
        "stages": stages,
        "events_count": len(events),
        "debate_turns": len(debate_turns),
        "debate_agents": list(set(t["agent"] for t in debate_turns if t["agent"])),
        "errors": errors,
        "has_synthesis": bool(synthesis),
        "confidence": confidence,
        "has_verdict": bool(verdict),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/e2e_monitor.py '<question>' [debate_depth]")
        print("       python scripts/e2e_monitor.py --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        questions = [
            ("What is the current Qatarization rate in the private sector?", "standard"),
            ("Compare Qatar's healthcare workforce attrition with UAE and Saudi Arabia", "standard"),
            ("Can Qatar achieve 50% Qatarization in IT by 2030?", "standard"),
        ]
        results = []
        for q, depth in questions:
            r = stream_question(q, depth)
            results.append(r)

        print("\n" + "=" * 80)
        print("OVERALL E2E RESULTS")
        print("=" * 80)
        all_passed = True
        for r in results:
            status = "PASS" if r["has_synthesis"] and not r["errors"] else "FAIL"
            if status == "FAIL":
                all_passed = False
            print(f"  [{status}] {r['question'][:60]}...")
            print(f"       Time: {r['total_time']:.0f}s | Events: {r['events_count']} | Debate turns: {r['debate_turns']} | Errors: {len(r['errors'])}")
        print(f"\nFinal: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    else:
        question = sys.argv[1]
        depth = sys.argv[2] if len(sys.argv) > 2 else "standard"
        stream_question(question, depth)


if __name__ == "__main__":
    main()
