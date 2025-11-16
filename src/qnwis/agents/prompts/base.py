"""
Shared anti-fabrication prompt utilities for all agents.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Any

ANTI_FABRICATION_RULES = """
═══════════════════════════════════════════════════
🚨 CRITICAL CITATION REQUIREMENTS 🚨
═══════════════════════════════════════════════════

RULE 1: CITE EVERY FACT
✅ CORRECT: "Per extraction: Qatar produces 347 tech graduates annually (MoL Education Data, confidence 70%)"
❌ WRONG: "Qatar produces approximately 800-1,200 tech graduates annually"

RULE 2: NEVER INVENT NUMBERS
✅ CORRECT: "NOT IN DATA - cannot estimate training infrastructure costs without Ministry of Education budget data"
❌ WRONG: "$2.5B investment in specialized tech education"

RULE 3: FLAG ALL ASSUMPTIONS
✅ CORRECT: "ASSUMPTION (confidence: 40%): 15% productivity differential between national and expatriate workers"
❌ WRONG: "Productivity differential: 15%"

RULE 4: SHOW YOUR CALCULATIONS
✅ CORRECT: "Required workforce: 7,440 (calculated as 60% × 12,400 [Per extraction: MoL LMIS])"
❌ WRONG: "Required workforce: approximately 7,500"

RULE 5: USE EXTRACTION OR ADMIT IGNORANCE
- If the data exists in EXTRACTED FACTS, cite it
- If the data is missing, write "NOT IN DATA - [explain what's missing]"
- DO NOT fill gaps with estimates unless explicitly labeled as ASSUMPTION

═══════════════════════════════════════════════════
VIOLATIONS = SYNTHESIS REJECTION
═══════════════════════════════════════════════════
"""


def format_extracted_facts(facts: Iterable[Mapping[str, Any]]) -> str:
    """
    Format deterministic fact records for inclusion in prompts.
    """
    formatted = ["EXTRACTED FACTS DATABASE:", "═" * 60, ""]
    
    for fact in facts:
        metric = str(fact.get("metric", "UNKNOWN METRIC"))
        value = fact.get("value", "N/A")
        source = fact.get("source", "UNKNOWN SOURCE")
        confidence = fact.get("confidence")
        
        formatted.append(f"• {metric}: {value}")
        formatted.append(f"  Source: {source}")
        if isinstance(confidence, (int, float)):
            formatted.append(f"  Confidence: {confidence * 100:.0f}%")
        else:
            formatted.append("  Confidence: N/A")
        
        raw_text = fact.get("raw_text")
        if raw_text:
            formatted.append(f"  Context: {str(raw_text)[:100]}...")
        
        formatted.append("")
    
    formatted.append("═" * 60)
    formatted.append("")
    return "\n".join(formatted)
