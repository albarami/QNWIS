"""Deep content quality analysis of E2E pipeline output."""

import json
import re

with open("d:/lmis_int/e2e_full_output.json", "r", encoding="utf-8") as f:
    events = json.load(f)

print(f"Total events: {len(events)}\n")

# 1. CLASSIFICATION
print("=" * 80)
print("1. CLASSIFICATION")
print("=" * 80)
for e in events:
    if e.get("stage") == "classify" and e.get("status") == "complete":
        p = e.get("payload", {})
        print(f"  Complexity: {p.get('complexity')}")
        print(f"  Question type: {p.get('question_type')}")
        print(f"  Reasoning: {p.get('reasoning')}")
        break

# 2. DATA EXTRACTION FACTS
print("\n" + "=" * 80)
print("2. DATA EXTRACTION — REAL FACTS FROM SOURCES")
print("=" * 80)
for e in events:
    if e.get("stage") == "prefetch" and e.get("status") == "complete":
        p = e.get("payload", {})
        facts = p.get("extracted_facts", [])
        print(f"  Total facts extracted: {len(facts)}")
        sources = set()
        for f_item in facts:
            if isinstance(f_item, dict):
                src = f_item.get("source", "unknown")
                sources.add(src)
        print(f"  Unique sources: {len(sources)}")
        for s in sorted(sources):
            count = sum(1 for f_item in facts if isinstance(f_item, dict) and f_item.get("source") == s)
            print(f"    {s}: {count} facts")

        print("\n  Sample facts (first 10):")
        for i, fact in enumerate(facts[:10]):
            if isinstance(fact, dict):
                metric = fact.get("metric", fact.get("indicator_name", "?"))
                value = fact.get("value", "?")
                year = fact.get("year", "?")
                source = fact.get("source", "?")
                country = fact.get("country", fact.get("country_name", ""))
                print(f"    [{i+1}] {metric} = {value} ({year}) [{source}] {country}")
        break

# 3. SCENARIOS
print("\n" + "=" * 80)
print("3. SCENARIOS GENERATED")
print("=" * 80)
for e in events:
    if e.get("stage") == "scenario_gen" and e.get("status") == "complete":
        p = e.get("payload", {})
        scenarios = p.get("scenarios", [])
        print(f"  Scenarios: {len(scenarios) if isinstance(scenarios, list) else p.get('scenarios_count', '?')}")
        if isinstance(scenarios, list):
            for s in scenarios[:6]:
                if isinstance(s, dict):
                    print(f"    - {s.get('name', s.get('id', '?'))}")
                    desc = s.get("description", "")
                    if desc:
                        print(f"      {desc[:150]}")
        break

# 4. DEBATE — AGENT BY AGENT
print("\n" + "=" * 80)
print("4. DEBATE — AGENT CONTRIBUTIONS")
print("=" * 80)
debate_turns = [e for e in events if e.get("stage", "").startswith("debate:turn")]
agents_content = {}
for dt in debate_turns:
    p = dt.get("payload", {})
    agent = p.get("agent", "unknown")
    turn = p.get("turn", "?")
    msg = p.get("message", "")
    phase = p.get("phase", p.get("type", ""))

    if agent not in agents_content:
        agents_content[agent] = []
    agents_content[agent].append({
        "turn": turn,
        "phase": phase,
        "message": msg,
        "length": len(msg),
    })

print(f"  Total debate turn events: {len(debate_turns)}")
print(f"  Agents participating: {len(agents_content)}")
print()

for agent, turns in sorted(agents_content.items()):
    total_chars = sum(t["length"] for t in turns)
    print(f"  AGENT: {agent}")
    print(f"    Turns: {len(turns)} | Total output: {total_chars} chars")

    # Check for data citations in this agent's turns
    all_text = " ".join(t["message"] for t in turns)
    fact_citations = len(re.findall(r"\[FACT \d+\]", all_text))
    pct_mentions = len(re.findall(r"\d+\.?\d*%", all_text))
    source_refs = []
    for src_name in ["World Bank", "IMF", "ILO", "Ministry of Labour", "GCC-STAT",
                      "Vision 2030", "Perplexity", "Qatar", "LMIS", "MoL", "NDS"]:
        if src_name.lower() in all_text.lower():
            source_refs.append(src_name)

    print(f"    [FACT N] citations: {fact_citations}")
    print(f"    Percentage data points: {pct_mentions}")
    print(f"    Sources referenced: {', '.join(source_refs) if source_refs else 'NONE'}")

    # Show preview of first turn
    if turns:
        preview = turns[0]["message"][:250]
        print(f"    First turn preview: {preview}...")
    print()

# 5. DEBATE PHASES
print("=" * 80)
print("5. DEBATE PHASES")
print("=" * 80)
phase_events = [e for e in events if e.get("stage", "").startswith("debate:") and e.get("stage") != "debate:turn"]
for pe in phase_events:
    stage = pe.get("stage", "")
    status = pe.get("status", "")
    p = pe.get("payload", {})
    msg = p.get("message", "")
    print(f"  {stage} [{status}]: {msg[:200]}")

# 6. FINAL SYNTHESIS CONTENT
print("\n" + "=" * 80)
print("6. FINAL SYNTHESIS — CONTENT QUALITY")
print("=" * 80)
synthesis = ""
confidence = None
for e in events:
    if e.get("stage") == "done" and e.get("status") == "complete":
        p = e.get("payload", {})
        synthesis = p.get("final_synthesis", "")
        confidence = p.get("confidence")
        break

if not synthesis:
    for e in events:
        if e.get("stage") == "synthesize" and e.get("status") == "complete":
            p = e.get("payload", {})
            synthesis = p.get("text", p.get("synthesis", p.get("final_synthesis", "")))
            break

if synthesis:
    print(f"  Total length: {len(synthesis)} chars")
    print(f"  Confidence: {confidence}")

    # Section detection
    sections = re.findall(r"##\s+[IVX]+\.\s+(.+)", synthesis)
    print(f"  Sections found: {len(sections)}")
    for s in sections:
        print(f"    - {s}")

    # Data quality checks
    fact_refs = re.findall(r"\[FACT \d+\]", synthesis)
    pct_claims = re.findall(r"(\d+\.?\d*%)", synthesis)
    source_mentions = set()
    for src in ["World Bank", "IMF", "ILO", "Ministry of Labour", "GCC-STAT",
                 "Vision 2030", "Perplexity", "LMIS", "MoL", "NDS3", "Brave",
                 "Semantic Scholar", "Qatar Open Data", "FAO", "UNWTO"]:
        if src.lower() in synthesis.lower():
            source_mentions.add(src)

    print(f"\n  Data quality:")
    print(f"    [FACT N] citations: {len(fact_refs)}")
    print(f"    Percentage claims: {len(pct_claims)}")
    print(f"    Sources referenced: {sorted(source_mentions)}")

    # Check for fabrication red flags
    print(f"\n  Fabrication red flags:")
    vague_phrases = sum(1 for p in ["approximately", "roughly", "around", "about"]
                        if p in synthesis.lower())
    hedging = sum(1 for p in ["it is believed", "sources suggest", "reportedly"]
                  if p in synthesis.lower())
    specific_numbers = re.findall(r"(?:QAR|USD|\$)\s*[\d,.]+", synthesis)
    print(f"    Vague quantifiers: {vague_phrases}")
    print(f"    Hedging phrases: {hedging}")
    print(f"    Specific monetary values: {len(specific_numbers)}")
    if specific_numbers:
        print(f"    Sample values: {specific_numbers[:5]}")

    # Print the actual synthesis sections
    print("\n  --- FULL SYNTHESIS (first 2000 chars) ---")
    print(synthesis[:2000])
    print("\n  --- END OF PREVIEW ---")
else:
    print("  NO SYNTHESIS FOUND!")
