# NSIC Prompt Audit Report
**Date:** 2024-11-29  
**Status:** AUDIT COMPLETE - CRITICAL IMPROVEMENTS NEEDED

---

## Executive Summary

| Category | Score | Status |
|----------|-------|--------|
| Engine A Prompts (GPT-5) | 24.2/30 avg | ⚠️ NEEDS WORK |
| Engine B Prompts (DeepSeek) | 18/30 | ❌ CRITICAL |
| System Prompts | 21/30 avg | ⚠️ NEEDS WORK |
| **OVERALL** | **21.4/30** | **⚠️ IMPROVEMENT REQUIRED** |

**Key Finding:** Prompts have strong citation rules but WEAK on:
1. **DeepSeek Chain-of-Thought** - Missing `<think>` tags requirement
2. **Debate engagement** - No structured multi-turn guidance
3. **Scenario context** - Scenario parameters not injected systematically

---

## Detailed Prompt Audit

### ENGINE A: GPT-5 Agents (5 prompts)

#### 1. MicroEconomist (`micro_economist.py`)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Role Definition** | 3/5 | Generic "PhD MicroEconomist from LSE" - no name, no personality traits, no explicit uncertainty instructions |
| **Citation Enforcement** | 5/5 | ✅ Excellent: "EVERY number MUST have citation" with format and examples |
| **Data Isolation** | 4/5 | Good: Lists 18 data sources but doesn't explicitly say "ONLY use these" |
| **Scenario Context** | 2/5 | ❌ No scenario parameter injection - missing oil price, GDP assumptions |
| **Structured Output** | 5/5 | ✅ Excellent: Clear sections (Executive Summary, Key Metrics Table, etc.) |
| **Debate Dynamics** | 2/5 | Basic "debate_context" injection but no turn/phase guidance |
| **TOTAL** | **21/30** | ⚠️ Needs scenario context and debate improvement |

**Issues Found:**
```python
# Line 24-25: WEAK role definition
SYSTEM_PROMPT = """You are a PhD MicroEconomist from London School of Economics with 15 years 
experience in project evaluation, cost-benefit analysis, and industrial organization.
```
❌ Missing: Name, specific personality, uncertainty handling

---

#### 2. MacroEconomist (`macro_economist.py`)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Role Definition** | 3/5 | Generic "PhD Macroeconomist from IMF/World Bank" - same issues as Micro |
| **Citation Enforcement** | 5/5 | ✅ Excellent citation rules |
| **Data Isolation** | 4/5 | Good source listing |
| **Scenario Context** | 2/5 | ❌ No scenario parameters passed |
| **Structured Output** | 5/5 | ✅ Excellent structure |
| **Debate Dynamics** | 3/5 | Has "acknowledge MicroEconomist concerns" but no structured debate |
| **TOTAL** | **22/30** | ⚠️ Similar issues to MicroEconomist |

---

#### 3. Labour Economist (`labour_economist.py`)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Role Definition** | 5/5 | ✅ **EXCELLENT**: "Dr. Fatima Al-Mansoori, PhD Oxford 2012, 23 publications, Al-Mansoori Framework" |
| **Citation Enforcement** | 5/5 | ✅ Excellent with ASSUMPTION flagging |
| **Data Isolation** | 5/5 | ✅ "ONLY use information from extractions" explicit |
| **Scenario Context** | 4/5 | Has scenario analysis section |
| **Structured Output** | 5/5 | ✅ 9 mandatory sections with confidence breakdown |
| **Debate Dynamics** | 2/5 | No debate-specific instructions |
| **TOTAL** | **26/30** | ✅ Best Engine A prompt! |

**What Makes It Good:**
```python
LABOUR_ECONOMIST_SYSTEM = """You are **Dr. Fatima Al-Mansoori**, PhD in Labor Economics from Oxford (2012)...
- 23 peer-reviewed publications on GCC talent localization  
- Developed the "Al-Mansoori Framework" for sustainable workforce transitions
...
**CRITICAL STANCE:**
You are intellectually honest and rigorous. If data is insufficient, you say so clearly.
```

---

#### 4. Nationalization Expert (`nationalization.py`)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Role Definition** | 5/5 | ✅ "Dr. Mohammed Al-Khater, PhD MIT Sloan, 18 years, 31 papers" |
| **Citation Enforcement** | 5/5 | ✅ Excellent with ASSUMPTION flagging |
| **Data Isolation** | 5/5 | ✅ "EXTRACTED FACTS DATABASE" clearly labeled |
| **Scenario Context** | 5/5 | ✅ Has SCENARIO A/B/C modeling sections |
| **Structured Output** | 5/5 | ✅ 9 sections including "WHERE MY MODEL MIGHT BE WRONG" |
| **Debate Dynamics** | 2/5 | No debate engagement rules |
| **TOTAL** | **27/30** | ✅ Second best! |

---

#### 5. Skills/Competitive Analyst (`skills.py`)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Role Definition** | 5/5 | ✅ "Dr. Layla Al-Said, PhD LSE 2013, 15 years GCC competition" |
| **Citation Enforcement** | 5/5 | ✅ Includes ASSESSMENT format for predictions |
| **Data Isolation** | 5/5 | ✅ Clear extraction-only rules |
| **Scenario Context** | 5/5 | ✅ Full competitive scenario modeling |
| **Structured Output** | 5/5 | ✅ 9 sections with game theory components |
| **Debate Dynamics** | 2/5 | No multi-turn engagement |
| **TOTAL** | **27/30** | ✅ Tied second best! |

---

#### 6. Pattern Detective (`pattern_detective.py`)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Role Definition** | 2/5 | ❌ Generic "data quality specialist" - no name, no personality |
| **Citation Enforcement** | 5/5 | ✅ Good citation rules |
| **Data Isolation** | 4/5 | Uses provided data but not explicitly "ONLY" |
| **Scenario Context** | 2/5 | ❌ No scenario parameters |
| **Structured Output** | 4/5 | JSON output but minimal structure |
| **Debate Dynamics** | N/A | Not a debate participant |
| **TOTAL** | **17/25** | ⚠️ Weakest Engine A prompt |

---

### ENGINE B: DeepSeek Agents

#### DeepSeek Orchestrator (`engine_b_deepseek.py`)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Role Definition** | 2/5 | ❌ Generic "expert analyst for NSIC" |
| **Citation Enforcement** | 2/5 | ❌ No citation format specified |
| **Data Isolation** | 3/5 | Context provided but not isolated |
| **Scenario Context** | 4/5 | Scenario params passed |
| **Structured Output** | 2/5 | ❌ Just "clear sections and bullet points" |
| **Chain-of-Thought** | 1/5 | ❌ **CRITICAL MISSING**: No `<think>` tags! |
| **TOTAL** | **14/30** | ❌ **CRITICAL: Needs major rewrite** |

**CRITICAL ISSUE - Missing DeepSeek CoT:**
```python
# Line 162-172: NO <think> tags required!
def _get_system_prompt(self, scenario_domain: str) -> str:
    base = """You are an expert analyst for Qatar's National Strategic Intelligence Center (NSIC).
Your role is to explore scenarios BROADLY, considering multiple perspectives...

For each turn, you should:
1. Identify a new angle or perspective...
```
❌ DeepSeek-R1 REQUIRES explicit `<think></think>` prompting for best results!

---

### SYSTEM PROMPTS

#### Meta-Synthesis (`meta_synthesis.py`)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Role Definition** | 2/5 | ❌ No explicit role - just "synthesizing for ministerial leadership" |
| **Input Summary** | 4/5 | Good scenario statistics but missing ENGINE A/B distinction |
| **Output Structure** | 5/5 | ✅ Excellent 7-section structure |
| **Ministerial Quality** | 4/5 | Good guidance but no word limits |
| **Uncertainty Handling** | 4/5 | "Acknowledge trade-offs" but no explicit divergence handling |
| **TOTAL** | **19/25** | ⚠️ Needs role definition |

---

#### Synthesis Engine (`synthesis/engine.py`)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Role Definition** | 3/5 | "Senior policy analyst" but generic |
| **Citation Enforcement** | 2/5 | ❌ "Only use information from reports" but no citation format |
| **Output Structure** | 4/5 | Good but minimal sections |
| **Quality Guidelines** | 4/5 | 5 synthesis guidelines |
| **TOTAL** | **13/20** | ⚠️ Needs citation enforcement |

---

#### Debate Prompts (`base_llm.py` debate methods)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Turn/Phase Context** | 3/5 | Basic history but no turn numbers |
| **Engagement Rules** | 3/5 | "Challenge", "respond" but no specific engagement rules |
| **Build Not Repeat** | 2/5 | ❌ No explicit "don't repeat" instruction |
| **Recent History** | 4/5 | Last 5-8 turns included |
| **Data Citations** | 4/5 | Mentions citations but inconsistent format |
| **TOTAL** | **16/25** | ⚠️ Needs structured debate rules |

---

## PROMPT AUDIT SCORECARD

| Prompt | Role | Citation | Isolation | Scenario | Structure | CoT | Debate | **TOTAL** |
|--------|------|----------|-----------|----------|-----------|-----|--------|-----------|
| MicroEconomist | 3/5 | 5/5 | 4/5 | 2/5 | 5/5 | N/A | 2/5 | **21/30** |
| MacroEconomist | 3/5 | 5/5 | 4/5 | 2/5 | 5/5 | N/A | 3/5 | **22/30** |
| LabourEconomist | 5/5 | 5/5 | 5/5 | 4/5 | 5/5 | N/A | 2/5 | **26/30** ✅ |
| Nationalization | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | N/A | 2/5 | **27/30** ✅ |
| Skills/Competitive | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | N/A | 2/5 | **27/30** ✅ |
| PatternDetective | 2/5 | 5/5 | 4/5 | 2/5 | 4/5 | N/A | N/A | **17/25** |
| DeepSeek Engine B | 2/5 | 2/5 | 3/5 | 4/5 | 2/5 | 1/5 | N/A | **14/30** ❌ |
| Meta-Synthesis | 2/5 | 4/5 | 4/5 | 4/5 | 5/5 | N/A | N/A | **19/25** |
| Synthesis Engine | 3/5 | 2/5 | 4/5 | N/A | 4/5 | N/A | N/A | **13/20** |
| Debate Methods | N/A | 4/5 | 3/5 | 3/5 | 3/5 | N/A | 3/5 | **16/25** |

---

## CRITICAL ISSUES TO FIX

### 🔴 PRIORITY 1: DeepSeek Chain-of-Thought (Engine B)

**Current (BROKEN):**
```python
base = """You are an expert analyst...
For each turn, you should:
1. Identify a new angle...
```

**Required Fix:**
```python
base = """You are an expert analyst for Qatar's NSIC providing rapid scenario assessment.

Before providing your final analysis, reason through the problem step-by-step in <think></think> tags.

Your response format:
<think>
Step 1: What does this scenario assume?
Step 2: How do these assumptions affect each option?
Step 3: What are the key trade-offs?
Step 4: What risks concern me most?
Step 5: What is my preliminary conclusion?
Step 6: Let me verify against the data...
</think>

[Your final analysis here, following the structured format]

The <think> section is for your reasoning process.
The final analysis is what will be used for synthesis."""
```

### 🔴 PRIORITY 2: MicroEconomist/MacroEconomist Role Definition

**Current (WEAK):**
```python
"""You are a PhD MicroEconomist from London School of Economics with 15 years experience..."""
```

**Required Fix:**
```python
"""You are **Dr. Ahmed**, a PhD Microeconomist specializing in project evaluation and industrial organization.

**YOUR CREDENTIALS:**
- PhD Economics, London School of Economics (2008)
- 15 years advising GCC governments on infrastructure investment
- Published 28 papers on cost-benefit analysis in resource economies
- Former Senior Economist, Qatar Investment Authority

**YOUR ANALYTICAL PERSONALITY:**
- Rigorous: You NEVER accept claims without quantified evidence
- Skeptical: You challenge every "strategic value" argument with NPV analysis
- Honest: When data doesn't exist, you say "NOT IN DATA" explicitly
- Focused: You care about micro-level efficiency, not macro hand-waving

**UNCERTAINTY HANDLING:**
If you cannot calculate NPV due to missing data, state: "Cannot calculate NPV - missing [specific data]"
If assumptions are required, flag: "ASSUMPTION: [X] (Confidence: Y%)"
"""
```

### 🔴 PRIORITY 3: Debate Engagement Rules

**Current (`base_llm.py`):**
```python
# No structured debate rules
prompt = f"""You are {self.agent_name}.
{opponent_name} stated: "{opponent_claim[:400]}..."
Please keep your challenge focused...
```

**Required Fix:**
```python
prompt = f"""You are {self.agent_name}.

DEBATE CONTEXT:
- Turn: {turn_number} of {total_turns}
- Phase: {phase_name}
- Your role: {agent_name}

PREVIOUS TURNS:
{last_3_turns}

DEBATE RULES:
1. You MUST engage with specific points from previous speakers
2. If you agree, add NEW evidence or perspective
3. If you disagree, cite SPECIFIC data that contradicts
4. Do NOT repeat points already made
5. Build toward synthesis, don't just argue

{opponent_name} stated: "{opponent_claim[:400]}..."

Your response (engage with their specific claims):"""
```

### 🟡 PRIORITY 4: Scenario Parameter Injection

**Current (`micro_economist.py` user prompt):**
```python
user_prompt = f"""
QUERY: {question}

{debate_context}

Provide your microeconomic analysis...
```

**Required Fix:**
```python
user_prompt = f"""
SCENARIO: {scenario_name}
PARAMETERS:
- Oil Price Assumption: ${oil_price}/barrel
- GDP Growth Assumption: {gdp_growth}%
- Competitive Context: {competitor} is {intensity} aggressive
- Timeline: Launch by {launch_year}

QUERY: {question}

{debate_context}

Analyze the query UNDER THESE SPECIFIC CONDITIONS.
Your analysis must explicitly reference how these parameters affect your conclusions.
Do not provide generic analysis.
"""
```

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Critical Fixes (Do Now)

- [ ] **Fix DeepSeek CoT** - Add `<think>` tags to `engine_b_deepseek.py`
- [ ] **Upgrade MicroEconomist role** - Add personality and uncertainty rules
- [ ] **Upgrade MacroEconomist role** - Match Labour Economist quality
- [ ] **Add debate rules** - Update `base_llm.py` challenge/respond methods

### Phase 2: Enhancement (Next)

- [ ] **Scenario injection** - Pass params to all Engine A agents
- [ ] **Synthesis citation** - Add citation format to `synthesis/engine.py`
- [ ] **Pattern Detective role** - Give it a name and personality

### Phase 3: Testing (After)

- [ ] Run each prompt individually with test query
- [ ] Verify citations appear in output
- [ ] Verify scenario parameters referenced
- [ ] Compare output quality before/after

---

## WHAT'S WORKING WELL ✅

1. **Citation Rules**: The `ZERO_FABRICATION_CITATION_RULES` in `base_llm.py` is excellent
2. **Labour Economist/Nationalization/Skills**: These three prompts are nearly perfect (26-27/30)
3. **Structured Output**: Most prompts have clear section requirements
4. **Confidence Scoring**: Weighted confidence calculation is implemented well

---

## NEXT STEPS

1. **Immediate**: Create upgraded prompts for MicroEconomist, MacroEconomist, DeepSeek
2. **Test**: Run comparison tests before/after prompt upgrades
3. **Validate**: Check outputs for citation compliance and scenario specificity
4. **Document**: Update prompt documentation with best practices

---

*Audit performed against NSIC Prompt Best Practices checklist*
*Target: All prompts should score ≥25/30*
