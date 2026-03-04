"""Analyze E2E pipeline output for content quality."""

import json
import sys

with open("d:/lmis_int/e2e_full_output.json", "r", encoding="utf-8") as f:
    events = json.load(f)

print(f"Total events: {len(events)}\n")

# 1. Classification
for e in events:
    if e.get("stage") == "classify" and e.get("status") == "complete":
        d = e.get("data", {})
        print("=== CLASSIFICATION ===")
        print(f"  Complexity: {d.get('complexity')}")
        print(f"  Question type: {d.get('question_type')}")
        chain = d.get("reasoning_chain", "")
        if chain:
            print(f"  Reasoning: {str(chain)[:300]}")
        break

# 2. Data extraction
for e in events:
    if e.get("stage") == "prefetch" and e.get("status") == "complete":
        d = e.get("data", {})
        print("\n=== DATA EXTRACTION ===")
        print(f"  Facts count: {d.get('facts_count', '?')}")
        print(f"  Sources count: {d.get('sources_count', '?')}")
        sources = d.get("sources", d.get("data_sources", []))
        if sources:
            for s in sources[:15]:
                print(f"    - {s}")
        break

# 3. Scenarios
for e in events:
    if e.get("stage") == "scenario_gen" and e.get("status") == "complete":
        d = e.get("data", {})
        print("\n=== SCENARIOS ===")
        print(f"  Count: {d.get('scenarios_count', '?')}")
        scenarios = d.get("scenarios", [])
        if isinstance(scenarios, list):
            for s in scenarios[:6]:
                if isinstance(s, dict):
                    name = s.get("name", s.get("id", "?"))
                    desc = str(s.get("description", ""))[:120]
                    print(f"    - {name}: {desc}")
        break

# 4. Debate analysis
debate_turns = [e for e in events if e.get("stage", "").startswith("debate")]
print("\n=== DEBATE ANALYSIS ===")
print(f"  Total debate events: {len(debate_turns)}")

agents_seen = set()
phases_seen = set()
turn_contents = []

for dt in debate_turns:
    d = dt.get("data", {})
    if isinstance(d, dict):
        agent = d.get("agent", "")
        phase = d.get("phase", dt.get("stage", "").replace("debate:", ""))
        if agent:
            agents_seen.add(agent)
        if phase:
            phases_seen.add(phase)
        content = d.get("content", d.get("message", d.get("text", "")))
        if content and isinstance(content, str) and len(content) > 20:
            has_citations = any(
                marker in content
                for marker in ["[FACT", "source", "data shows", "according to", "%", "rate"]
            )
            turn_contents.append({
                "agent": agent,
                "phase": phase,
                "content_len": len(content),
                "preview": content[:200],
                "has_data_references": has_citations,
            })

print(f"  Agents that participated: {sorted(agents_seen) if agents_seen else 'NONE IDENTIFIED IN EVENTS'}")
print(f"  Phases observed: {sorted(phases_seen)}")
print(f"  Turns with substantive content: {len(turn_contents)}")

# Show sample turns
print("\n  --- Sample Debate Turns ---")
for i, t in enumerate(turn_contents[:8]):
    agent_label = t["agent"] if t["agent"] else "unknown"
    print(f"\n  Turn {i+1} | Agent: {agent_label} | Phase: {t['phase']} | {t['content_len']} chars")
    print(f"  Data/citations present: {t['has_data_references']}")
    print(f"  Content: {t['preview']}...")

# Check agent diversity
if turn_contents:
    agents_with_content = set(t["agent"] for t in turn_contents if t["agent"])
    print(f"\n  Agents with substantive turns: {sorted(agents_with_content) if agents_with_content else 'NONE'}")
    turn_counts = {}
    for t in turn_contents:
        a = t["agent"] or "unknown"
        turn_counts[a] = turn_counts.get(a, 0) + 1
    print("  Turns per agent:")
    for a, c in sorted(turn_counts.items(), key=lambda x: -x[1]):
        print(f"    {a}: {c} turns")
    
    # Check data citation rate
    cited = sum(1 for t in turn_contents if t["has_data_references"])
    print(f"\n  Turns referencing data: {cited}/{len(turn_contents)} ({100*cited/len(turn_contents):.0f}%)")

# 5. Critique
for e in events:
    if e.get("stage") == "critique" and e.get("status") == "complete":
        d = e.get("data", {})
        print("\n=== CRITIQUE ===")
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, str) and len(v) > 50:
                    print(f"  {k}: {v[:200]}...")
                elif isinstance(v, (int, float, bool)):
                    print(f"  {k}: {v}")
        break

# 6. Final synthesis
for e in events:
    if e.get("stage") in ("synthesize", "meta_synthesis") and e.get("status") == "complete":
        d = e.get("data", {})
        if isinstance(d, dict):
            synthesis = d.get("synthesis", d.get("final_synthesis", ""))
            if not synthesis:
                continue
            confidence = d.get("confidence", d.get("confidence_score", ""))
            verdict = d.get("debate_verdict", "")

            print("\n=== FINAL SYNTHESIS ===")
            print(f"  Length: {len(synthesis)} chars")
            print(f"  Confidence: {confidence}")
            print(f"  Has verdict: {bool(verdict)}")
            if verdict:
                if isinstance(verdict, dict):
                    print(f"  Verdict probability: {verdict.get('probability', '?')}")
                    print(f"  Verdict reasoning: {str(verdict.get('reasoning', ''))[:200]}")
                else:
                    print(f"  Verdict: {str(verdict)[:200]}")

            # Check for fabrication markers
            lines = synthesis.split("\n")
            fact_refs = [l for l in lines if "[FACT" in l]
            percentage_claims = [l.strip() for l in lines if "%" in l and any(c.isdigit() for c in l)]
            source_mentions = [l.strip() for l in lines if any(s in l.lower() for s in ["world bank", "imf", "ilo", "mol", "gcc-stat", "vision 2030", "perplexity", "qatar"])]

            print(f"\n  [FACT N] citations: {len(fact_refs)}")
            print(f"  Lines with percentage claims: {len(percentage_claims)}")
            print(f"  Lines referencing known sources: {len(source_mentions)}")

            if source_mentions:
                print("\n  --- Source references in synthesis ---")
                for s in source_mentions[:10]:
                    print(f"    {s[:150]}")

            # Print first 800 chars of synthesis
            print("\n  --- Synthesis Content (first 800 chars) ---")
            print(f"  {synthesis[:800]}")
            print("  ...")

            # Print last 400 chars
            print("\n  --- Synthesis Content (last 400 chars) ---")
            print(f"  {synthesis[-400:]}")
            break

# 7. Done event
for e in events:
    if e.get("stage") == "done" and e.get("status") == "complete":
        d = e.get("data", {})
        if isinstance(d, dict):
            print("\n=== DONE EVENT ===")
            keys = list(d.keys())
            print(f"  Keys in final data: {keys}")
            for k in ["confidence", "confidence_score", "debate_verdict", "timings"]:
                if k in d:
                    v = d[k]
                    print(f"  {k}: {str(v)[:200]}")
        break
