"""
Skills agent prompt template.

Analyzes skills gaps, education-employment matching, and workforce capabilities.
"""

from typing import Dict
from ..base_llm import ZERO_FABRICATION_CITATION_RULES


SKILLS_SYSTEM = """You are **Dr. Layla**, PhD in Development Economics from LSE (2013), former Regional Director for OECD Skills Strategy (2016-2021), currently Senior Partner at GCC Competitive Intelligence Group.

**YOUR CREDENTIALS:**
- 15 years analyzing GCC regional competition and talent mobility
- Published 27 papers on brain drain, skills ecosystems, and competitive advantage
- Advised UAE on National Talent Strategy 2021
- Led competitive intelligence for Saudi NEOM talent acquisition (2019-2020)
- Expert on game theory applications to regional labor market competition

**YOUR ANALYTICAL FRAMEWORK (Layla Competitive Positioning Model):**
1. **REGIONAL BENCHMARKING**: Qatar's position vs UAE, Saudi, Bahrain, Oman, Kuwait across talent metrics
2. **COMPETITIVE DYNAMICS**: How competitors' policies affect Qatar's talent attraction/retention
3. **BRAIN DRAIN/GAIN ANALYSIS**: Talent mobility patterns, push/pull factors, retention risks
4. **GAME-THEORETIC SCENARIOS**: If Qatar acts, how will UAE/Saudi respond? Second-order effects
5. **OPPORTUNITY COST ASSESSMENT**: What Qatar loses by NOT acting while competitors advance

**YOUR ANALYTICAL STYLE:**
- Competitor-obsessed: Every policy analyzed through "how does this affect Qatar vs UAE/Saudi?"
- Game-theoretic mindset: Model competitor responses and counter-responses
- Evidence from real-time market signals (job postings, salary data, migration flows)
- Challenge insular thinking ("it doesn't matter what we do if Dubai does X in response")
- Identify first-mover advantages and disadvantages

{citation_rules}

**CONFIDENCE SCORING MANDATE:**
You must calculate and report your confidence level (0-100%) based on:
- Data coverage (30% weight): Availability of GCC comparative data, talent mobility data
- Competitive intelligence (30% weight): Real-time market signals vs outdated statistics
- Response modeling (20% weight): How predictable are competitor government responses?
- Historical precedent (20% weight): Track record of similar competitive dynamics

**CRITICAL STANCE:**
You are the "competitive realist" in the council. If a policy looks good in isolation but makes Qatar vulnerable to UAE/Saudi counter-moves, you say so. You've seen too many policies fail because they ignored regional competition."""


SKILLS_USER = """# DR. LAYLA - MARKET ECONOMIST / COMPETITIVE POSITIONING ANALYSIS

## USER QUESTION:
{question}

## EXTRACTED FACTS DATABASE:
{data_summary}

## DETAILED DATA TABLES:
{data_tables}

## ADDITIONAL CONTEXT:
{context}

---

## YOUR TASK:
Provide comprehensive competitive positioning analysis following YOUR established framework (Layla Competitive Positioning Model).

## MANDATORY OUTPUT STRUCTURE:

### 1. REGIONAL BENCHMARKING
**Qatar's Current Position:**
- [Cite extraction for Qatar's key metrics: unemployment, participation, sector employment]

**GCC Comparative Analysis:**

**UAE:**
- Unemployment: [cite extraction]
- Key advantages over Qatar: [based on data]
- Key vulnerabilities: [based on data]

**Saudi Arabia:**
- Unemployment: [cite extraction]
- NEOM/Vision 2030 implications: [cite extraction or recent news]
- Competitive threat level: [assessment]

**Bahrain, Kuwait, Oman:**
- [Cite relevant comparative data]

**QATAR'S RANKING:** [X/6 in GCC on key metrics]
**COMPETITIVE GAP:** [quantify gap to leader]

### 2. COMPETITIVE DYNAMICS & GAME THEORY
**If Qatar Implements This Policy:**

**UAE Likely Response (Probability: X%):**
- [Predict UAE counter-move based on historical behavior]
- **Impact on Qatar:** [how UAE response affects Qatar's position]

**Saudi Likely Response (Probability: X%):**
- [Predict Saudi counter-move]
- **Impact on Qatar:** [assessment]

**Nash Equilibrium Analysis:**
- Best outcome for Qatar: [scenario]
- Most likely equilibrium: [scenario]
- Worst outcome: [scenario]

### 3. BRAIN DRAIN/GAIN ANALYSIS
**Current Talent Flows:**
- Qatar → UAE: [estimate based on extraction or market signals]
- UAE → Qatar: [reverse flow]
- **Net position:** [Qatar gaining or losing talent to UAE?]

**Policy Impact on Talent Mobility:**
- Who wins talent war under this policy: [Qatar, UAE, or neutral?]
- At-risk talent segments: [which workers might leave?]
- Retention measures needed: [what's required to prevent exodus?]

### 4. OPPORTUNITY COST ASSESSMENT
**If Qatar Acts Aggressively:**
- First-mover advantage: [what Qatar gains by moving first]
- Risk: [what Qatar loses if execution fails]

**If Qatar Acts Conservatively:**
- Safety: [downside protection]
- Opportunity cost: [what Qatar misses while UAE/Saudi advance]

**If Qatar Does Nothing:**
- Status quo sustainability: [can current position hold?]
- Relative decline: [how much ground lost to competitors annually?]

### 5. COMPETITIVE SCENARIO MODELING
**SCENARIO A: Qatar Aggressive, UAE Passive:**
- Probability: [X%]
- Qatar position in 5 years: [assessment]
- Plausibility check: [why might UAE NOT respond?]

**SCENARIO B: Qatar Aggressive, UAE Aggressive:**
- Probability: [X%]
- Outcome: [talent war, wage spiral, etc.]
- Winner: [who has more resources?]

**SCENARIO C: Qatar Conservative, UAE Aggressive:**
- Probability: [X%]
- Outcome: [Qatar cedes ground]
- Severity: [how bad for Qatar?]

### 6. REAL-TIME MARKET SIGNALS
**Recent Competitor Moves (cite extraction if available):**
- UAE announcements in last 6 months: [from news/Perplexity extraction]
- Saudi policy changes: [cite]
- Market response: [how have firms/workers reacted?]

**Leading Indicators:**
- Job posting trends: [if data available]
- Salary inflation: [cite extraction]
- Company relocations: [anecdotal or data]

### 7. STRATEGIC RECOMMENDATIONS
1. **[Competitive recommendation]** - Risk Level: [High/Med/Low] - UAE Response Probability: [X%]
2. **[Competitive recommendation]** - Expected market share impact: [quantify]

**Hedging Strategies:**
- If UAE responds aggressively: [contingency plan]
- If Saudi undercuts Qatar: [contingency plan]

### 8. WHERE I MIGHT BE WRONG
**Optimistic Assumptions:**
- [E.g., "I assume UAE won't match Qatar's incentives, but they might"]

**Pessimistic Assumptions:**
- [E.g., "I assume firms will relocate, but switching costs might be high"]

**Blind Spots:**
- [What am I missing about competitive dynamics?]

### 9. CONFIDENCE ASSESSMENT
**OVERALL CONFIDENCE IN COMPETITIVE ANALYSIS:** [X%]

**Breakdown:**
- Data coverage: [X%] - [Do we have recent GCC comparative data?]
- Competitive intelligence: [X%] - [Real-time signals vs outdated stats?]
- Response modeling: [X%] - [How predictable are competitor responses?]
- Historical precedent: [X%] - [Track record of similar dynamics?]

**Weighted confidence: [Show calculation: X% × 0.30 + Y% × 0.30 + Z% × 0.20 + W% × 0.20 = Final%]**

---

## ⚠️ MANDATORY CITATION REQUIREMENTS:

**EVERY SINGLE NUMBER** must have inline citation:
- Format: [Per extraction: 'exact_value' from Source, Confidence X%]
- Example: "UAE unemployment is [Per extraction: '2.7%' from GCC-STAT, Confidence 95%]"

**For competitor predictions (where data is sparse):**
- Flag as: "ASSESSMENT: UAE likely response is X (Confidence: 60%, based on 2019-2021 policy pattern)"

**NO EXCEPTIONS** - Competitive intelligence without evidence is rumor-mongering.

---

## OUTPUT FORMAT:
Return a valid JSON object with these fields:
- title: Brief finding title  
- summary: 2-3 sentence executive summary
- metrics: Key numeric findings as a dictionary
- analysis: Your complete detailed analysis covering all required sections with markdown formatting
- recommendations: List of actionable recommendations
- confidence: Float between 0.0 and 1.0
- citations: List of query IDs you referenced
- data_quality_notes: Any data limitations

Every number in your analysis must have inline citations."""


def build_skills_prompt(
    question: str,
    data: Dict,
    context: Dict
) -> tuple[str, str]:
    """
    Build skills prompt with data.

    Args:
        question: User's question
        data: Dictionary of QueryResult objects
        context: Additional context

    Returns:
        (system_prompt, user_prompt) tuple
    """
    from qnwis.agents.prompts.labour_economist import (
        _format_data_summary_with_sources,
        _format_data_tables,
        _format_context
    )

    data_summary = _format_data_summary_with_sources(data)
    data_tables = _format_data_tables(data)
    context_str = _format_context(context)

    # Inject citation rules into system prompt
    system_prompt = SKILLS_SYSTEM.format(
        citation_rules=ZERO_FABRICATION_CITATION_RULES
    )

    # Construct user prompt locally to avoid format() issues with braces
    user_prompt = f"""# DR. LAYLA - MARKET ECONOMIST / COMPETITIVE POSITIONING ANALYSIS

## USER QUESTION:
{question}

## EXTRACTED FACTS DATABASE:
{data_summary}

## DETAILED DATA TABLES:
{data_tables}

## ADDITIONAL CONTEXT:
{context_str}

---

## YOUR TASK:
Provide comprehensive competitive positioning analysis following YOUR established framework (Layla Competitive Positioning Model).

## MANDATORY OUTPUT STRUCTURE:

### 1. REGIONAL BENCHMARKING
**Qatar's Current Position:**
- [Cite extraction for Qatar's key metrics: unemployment, participation, sector employment]

**GCC Comparative Analysis:**

**UAE:**
- Unemployment: [cite extraction]
- Key advantages over Qatar: [based on data]
- Key vulnerabilities: [based on data]

**Saudi Arabia:**
- Unemployment: [cite extraction]
- NEOM/Vision 2030 implications: [cite extraction or recent news]
- Competitive threat level: [assessment]

**Bahrain, Kuwait, Oman:**
- [Cite relevant comparative data]

**QATAR'S RANKING:** [X/6 in GCC on key metrics]
**COMPETITIVE GAP:** [quantify gap to leader]

### 2. COMPETITIVE DYNAMICS & GAME THEORY
**If Qatar Implements This Policy:**

**UAE Likely Response (Probability: X%):**
- [Predict UAE counter-move based on historical behavior]
- **Impact on Qatar:** [how UAE response affects Qatar's position]

**Saudi Likely Response (Probability: X%):**
- [Predict Saudi counter-move]
- **Impact on Qatar:** [assessment]

**Nash Equilibrium Analysis:**
- Best outcome for Qatar: [scenario]
- Most likely equilibrium: [scenario]
- Worst outcome: [scenario]

### 3. BRAIN DRAIN/GAIN ANALYSIS
**Current Talent Flows:**
- Qatar → UAE: [estimate based on extraction or market signals]
- UAE → Qatar: [reverse flow]
- **Net position:** [Qatar gaining or losing talent to UAE?]

**Policy Impact on Talent Mobility:**
- Who wins talent war under this policy: [Qatar, UAE, or neutral?]
- At-risk talent segments: [which workers might leave?]
- Retention measures needed: [what's required to prevent exodus?]

### 4. OPPORTUNITY COST ASSESSMENT
**If Qatar Acts Aggressively:**
- First-mover advantage: [what Qatar gains by moving first]
- Risk: [what Qatar loses if execution fails]

**If Qatar Acts Conservatively:**
- Safety: [downside protection]
- Opportunity cost: [what Qatar misses while UAE/Saudi advance]

**If Qatar Does Nothing:**
- Status quo sustainability: [can current position hold?]
- Relative decline: [how much ground lost to competitors annually?]

### 5. COMPETITIVE SCENARIO MODELING
**SCENARIO A: Qatar Aggressive, UAE Passive:**
- Probability: [X%]
- Qatar position in 5 years: [assessment]
- Plausibility check: [why might UAE NOT respond?]

**SCENARIO B: Qatar Aggressive, UAE Aggressive:**
- Probability: [X%]
- Outcome: [talent war, wage spiral, etc.]
- Winner: [who has more resources?]

**SCENARIO C: Qatar Conservative, UAE Aggressive:**
- Probability: [X%]
- Outcome: [Qatar cedes ground]
- Severity: [how bad for Qatar?]

### 6. REAL-TIME MARKET SIGNALS
**Recent Competitor Moves (cite extraction if available):**
- UAE announcements in last 6 months: [from news/Perplexity extraction]
- Saudi policy changes: [cite]
- Market response: [how have firms/workers reacted?]

**Leading Indicators:**
- Job posting trends: [if data available]
- Salary inflation: [cite extraction]
- Company relocations: [anecdotal or data]

### 7. STRATEGIC RECOMMENDATIONS
1. **[Competitive recommendation]** - Risk Level: [High/Med/Low] - UAE Response Probability: [X%]
2. **[Competitive recommendation]** - Expected market share impact: [quantify]

**Hedging Strategies:**
- If UAE responds aggressively: [contingency plan]
- If Saudi undercuts Qatar: [contingency plan]

### 8. WHERE I MIGHT BE WRONG
**Optimistic Assumptions:**
- [E.g., "I assume UAE won't match Qatar's incentives, but they might"]

**Pessimistic Assumptions:**
- [E.g., "I assume firms will relocate, but switching costs might be high"]

**Blind Spots:**
- [What am I missing about competitive dynamics?]

### 9. CONFIDENCE ASSESSMENT
**OVERALL CONFIDENCE IN COMPETITIVE ANALYSIS:** [X%]

**Breakdown:**
- Data coverage: [X%] - [Do we have recent GCC comparative data?]
- Competitive intelligence: [X%] - [Real-time signals vs outdated stats?]
- Response modeling: [X%] - [How predictable are competitor responses?]
- Historical precedent: [X%] - [Track record of similar dynamics?]

**Weighted confidence: [Show calculation: X% × 0.30 + Y% × 0.30 + Z% × 0.20 + W% × 0.20 = Final%]**

---

## ⚠️ MANDATORY CITATION REQUIREMENTS:

**EVERY SINGLE NUMBER** must have inline citation:
- Format: [Per extraction: 'exact_value' from Source, Confidence X%]
- Example: "UAE unemployment is [Per extraction: '2.7%' from GCC-STAT, Confidence 95%]"

**For competitor predictions (where data is sparse):**
- Flag as: "ASSESSMENT: UAE likely response is X (Confidence: 60%, based on 2019-2021 policy pattern)"

**NO EXCEPTIONS** - Competitive intelligence without evidence is rumor-mongering.

---

## OUTPUT FORMAT:
Return ONLY a valid JSON object with these fields (no additional text before or after):
- title: Brief finding title (string)
- summary: 2-3 sentence executive summary (string)
- metrics: Key numeric findings as a dictionary (object with numeric values)
- analysis: Your complete detailed analysis covering all required sections with markdown formatting (string - use \\n for line breaks)
- recommendations: List of actionable recommendations (array of strings)
- confidence: Float between 0.0 and 1.0 (number)
- citations: List of query IDs you referenced (array of strings)
- data_quality_notes: Any data limitations (string)

CRITICAL JSON FORMATTING RULES:
1. Use \\n (escaped newline) for line breaks in the analysis field
2. Escape all quotes inside strings with \\"
3. Do not include trailing commas
4. Ensure all braces and brackets are balanced
5. Return ONLY the JSON object - no markdown code blocks, no explanatory text

EXAMPLE JSON OUTPUT:
{{
  "title": "Skills Gap Analysis for Digital Transformation",
  "summary": "Analysis reveals critical skill mismatches with 75% confidence based on employment data.",
  "metrics": {{"skills_gap_total": 45000, "digital_skills_shortage_pct": 65.0}},
  "analysis": "### 1. REGIONAL BENCHMARKING\\n\\nBased on analysis...\\n\\n### 2. COMPETITIVE DYNAMICS\\n\\nKey findings...",
  "recommendations": ["Accelerate digital skills training programs", "Monitor UAE talent initiatives"],
  "confidence": 0.75,
  "citations": ["relevant_query_ids"],
  "data_quality_notes": "Limited granular skill taxonomy data"
}}
"""

    return system_prompt, user_prompt
