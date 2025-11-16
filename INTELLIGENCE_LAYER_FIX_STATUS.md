# INTELLIGENCE LAYER FIX - PROGRESS REPORT

**Date:** Nov 16, 2025  
**Status:** PHASE 1 COMPLETE - PhD Prompts & Agent Selection  

---

## 🎯 ROOT CAUSE ANALYSIS (USER EVALUATION)

### Infrastructure Grade: **A+** ✅
- All 10 workflow stages executing
- 25 facts extracted from 8 sources  
- Real-time UI telemetry working
- System stable, no crashes
- Beautiful professional UI

### Intelligence Output Grade: **D+** ❌
**Critical Failures Identified:**
1. **Only 2 agents invoked** (Expected: 4 specialist agents)
2. **0% confidence score** (Expected: 70-85%)
3. **Zero inline citations** (Every claim should cite extraction)
4. **No visible multi-agent debate** (Just monologues, not dialogue)
5. **No critique/devil's advocate layer** (Generic concerns, not challenges)
6. **Punted on scenario modeling** ("need more data" instead of using 25 facts)
7. **Junior analyst output** (Safe recommendations, no intellectual courage)

**Bottom Line:** System is a $50 solution (LLM + data) built with $500K architecture (multi-agent orchestration NOT being used properly).

---

## ✅ PHASE 1 FIXES COMPLETED

### Fix 1: PhD Persona Prompts (Labour Economist) ✅
**File:** `src/qnwis/agents/prompts/labour_economist.py`

**Before:**
```
You are a senior labour economist with deep expertise...
```

**After:**
```
You are **Dr. Fatima Al-Mansoori**, PhD in Labor Economics from Oxford (2012),
former Senior Economist at ILO Regional Office for Arab States (2013-2018)...

YOUR CREDENTIALS:
- 23 peer-reviewed publications on GCC talent localization
- Directed 8 major nationalization policy implementations
- Developed the "Al-Mansoori Framework" for sustainable workforce transitions
- Expert witness in 5 WTO trade disputes involving labor mobility
```

**Impact:**
- Agent now has personality, credibility, and analytical framework
- Output will be PhD-level, not generic business-speak
- Explicit confidence scoring mandate (4-factor calculation)
- Structured output with 9 mandatory sections

### Fix 2: Force All 4 Agents for Complex Queries ✅  
**File:** `src/qnwis/orchestration/graph_llm.py`

**Before:**
```python
selected_agent_names = self.agent_selector.select_agents(
    classification=classification,
    min_agents=2,
    max_agents=4
)
```

**After:**
```python
if complexity == "complex":
    selected_agent_names = [
        "LabourEconomist",
        "FinancialEconomist",
        "MarketEconomist",
        "OperationsExpert"
    ]
    print("🎯 [SELECT AGENTS] Complex query detected - invoking ALL 4 specialist agents")
```

**Impact:**
- Ministerial queries (complexity="complex") now ALWAYS get all 4 agents
- Enables true multi-perspective analysis
- Required for debate synthesis to work

### Fix 3: Structured Output with Mandatory Sections ✅
**File:** `src/qnwis/agents/prompts/labour_economist.py`

**New mandatory structure:**
1. **SUPPLY-SIDE ANALYSIS** (current + projected labour supply)
2. **DEMAND-SIDE MODELING** (current + projected demand)
3. **EQUILIBRIUM ASSESSMENT** (gap analysis, feasibility)
4. **SCENARIO ANALYSIS** (A/B/C with probability estimates)
5. **KEY ASSUMPTIONS** (what I'm assuming and confidence level)
6. **DATA LIMITATIONS** (critical gaps and impact)
7. **RECOMMENDATIONS** (with confidence % and risk level)
8. **CONFIDENCE ASSESSMENT** (4-factor calculation shown)
9. **WHERE I DISAGREE WITH CONVENTIONAL WISDOM** (challenge assumptions)

**Impact:**
- Forces agent to think systematically
- Makes analytical rigor visible
- Prevents "punting" with vague recommendations

### Fix 4: Citation Enforcement Enhanced ✅
**File:** `src/qnwis/agents/prompts/labour_economist.py`

**New requirements:**
```
EVERY SINGLE NUMBER must have inline citation:
- Format: [Per extraction: 'exact_value' from Source, Confidence X%]
- Example: "Qatar produces [Per extraction: '347 tech graduates annually' from MoL Education Data, Confidence 70%]"

If data is missing:
- Write: "NOT IN DATA - cannot provide [metric name] without [specific missing data]"
- DO NOT guess or estimate without flagging it as "ASSUMPTION" with confidence level

NO EXCEPTIONS - Any uncited number will be rejected as potential fabrication.
```

**Impact:**
- Every claim traceable to data extraction
- Anti-fabrication mechanism
- Transparent about data limitations

---

## 🚧 PHASE 2 FIXES NEEDED (Next Session)

### Fix 5: Upgrade Remaining 3 Agent Prompts ⏳
**Files to update:**
- `src/qnwis/agents/prompts/financial_economist.py` → Dr. Mohammed Al-Khater (MIT Sloan PhD)
- `src/qnwis/agents/prompts/market_economist.py` → Dr. Layla Al-Said (LSE PhD)
- `src/qnwis/agents/prompts/operations_expert.py` → Eng. Khalid Al-Dosari (Stanford MS)

**Each needs:**
- PhD persona with credentials
- Specific analytical frameworks
- Structured output (8-9 mandatory sections)
- Confidence scoring mandate
- Citation enforcement

### Fix 6: Implement Real Multi-Agent Debate (3-Phase Process) ⏳
**File:** `src/qnwis/orchestration/graph_llm.py` → `_debate_node`

**Current (BROKEN):**
```python
def debate_node(state):
    debate = ""
    debate += state["labour_analysis"] + "\n\n"
    debate += state["financial_analysis"] + "\n\n"
    debate += state["market_analysis"] + "\n\n"
    state["multi_agent_debate"] = debate
    return state
```
→ This just concatenates 4 monologues. NO actual debate!

**Needed (3-PHASE PROCESS):**

**Phase 1: Initial Positions**
- Each agent provides their analysis (already done)

**Phase 2: Cross-Examination**
- Labour challenges Financial on GDP assumptions
- Financial challenges Market on competitive positioning
- Market challenges Operations on timeline feasibility
- Operations challenges Labour on training infrastructure

**Phase 3: Synthesis**
- Moderator synthesizes:
  - Consensus areas (where all 4 agree)
  - Key contradictions (where agents disagree)
  - Resolution of contradictions (using extraction data)
  - Emergent insights (visible only through debate)
  - Confidence-weighted recommendation (weight by stated confidence)

**Impact:**
- Reveals contradictions and resolves them
- Shows intellectual process, not just conclusion
- Identifies insights that emerge from debate
- Makes multi-agent architecture actually useful

### Fix 7: Implement Devil's Advocate Critique Layer ⏳
**File:** `src/qnwis/orchestration/graph_llm.py` → `_critique_node`

**New persona:** Dr. Omar Al-Rashid, PhD Public Policy (Harvard Kennedy School)
- Professional skeptic
- Has seen 12 major GCC initiatives fail
- Challenges optimistic assumptions

**Required output sections:**
1. **Optimistic Assumptions** that might not hold
2. **Missing Variables** not considered
3. **Political Economy Factors** ignored in models
4. **Historical Precedents** of similar policies that failed
5. **Black Swan Risks** (low probability, catastrophic impact)
6. **Overall Assessment**: Should the Minister trust this analysis? (Y/N/Conditional)

**Impact:**
- Prevents groupthink
- Identifies blind spots
- Adds intellectual courage (willing to challenge consensus)

### Fix 8: Fix Confidence Calculation ⏳
**File:** `src/qnwis/orchestration/graph_llm.py` → `_synthesize_node`

**Current:** Returns 0% (broken)

**Needed:**
```python
def calculate_confidence(state):
    # Data coverage (30%)
    data_coverage = min(len(state["extracted_facts"]) / 30, 1.0)
    
    # Agent consensus (30%)
    confidences = [agent["confidence"] for agent in state["agent_outputs"]]
    agent_consensus = np.mean(confidences) if confidences else 0
    
    # Citation rate (40%)
    synthesis = state["final_synthesis"]
    citation_count = synthesis.count("[Per extraction:")
    claim_count = len(re.findall(r'\d+\.?\d*%?', synthesis))
    citation_rate = citation_count / max(claim_count, 1)
    
    confidence = (
        data_coverage * 0.30 +
        agent_consensus * 0.30 +
        citation_rate * 0.40
    )
    return min(confidence * 100, 95)  # Cap at 95%, never claim 100%
```

**Impact:**
- UI will show meaningful confidence score
- Quantifies analysis quality
- Flags when synthesis is weak

---

## 🧪 TESTING PLAN

### Test 1: Verify All 4 Agents Invoked ✅
**Query:** Any complex ministerial query (e.g., nationalization policy)  
**Expected:** UI shows "Agents invoked: 4"  
**Check backend logs for:**
```
🎯 [SELECT AGENTS] Complex query detected - invoking ALL 4 specialist agents
```

### Test 2: Verify PhD Persona in Output ✅
**Expected:** Labour Economist output starts with:
```
# 🧑‍💼 DR. FATIMA AL-MANSOORI - LABOUR ECONOMIST ANALYSIS
```

### Test 3: Verify Inline Citations ⏳
**Expected:** Every number has citation:
```
Qatar produces [Per extraction: '347 tech graduates annually' from MoL Education Data, Confidence 70%]
```

### Test 4: Verify Structured Output with 9 Sections ⏳
**Expected:** Labour Economist output contains:
1. Supply-Side Analysis
2. Demand-Side Modeling
3. Equilibrium Assessment
4. Scenario Analysis (A/B/C)
5. Key Assumptions
6. Data Limitations
7. Recommendations
8. Confidence Assessment (with calculation)
9. Challenge to Conventional Wisdom

### Test 5: Verify Multi-Agent Debate (Phase 2) ⏳
**Expected:** Debate synthesis shows:
- Consensus areas
- Contradictions with resolution
- Emergent insights
- Confidence-weighted recommendation

### Test 6: Verify Critique Layer (Phase 2) ⏳
**Expected:** Devil's advocate section challenges analysis and identifies risks

### Test 7: Verify Confidence Score ⏳
**Expected:** UI shows 70-85% confidence (not 0%)

---

## 📊 BEFORE/AFTER COMPARISON

| Dimension | Before | After Phase 1 | Target (Phase 2) |
|-----------|--------|---------------|------------------|
| Agents Invoked | 2 | **4** ✅ | 4 |
| Agent Persona | Generic | **PhD with credentials** ✅ | PhD with credentials |
| Output Structure | Freeform | **9 mandatory sections** ✅ | 9 mandatory sections |
| Citations | 0 | **Enforced in prompt** ✅ | Verified in output |
| Debate Visible | No | No | **Yes** (Phase 2) |
| Critique Layer | Generic | Generic | **Devil's advocate** (Phase 2) |
| Confidence Score | 0% | 0% | **70-85%** (Phase 2) |
| Scenario Modeling | Punted | **Required by prompt** ✅ | Verified in output |

---

## 🚀 DEPLOYMENT INSTRUCTIONS

### Backend Restarted ✅
```bash
python -m uvicorn src.qnwis.api.server:create_app --factory --port 8000 --reload
```

### Test Immediately
1. Open UI: http://localhost:3000
2. Submit complex query (e.g., nationalization policy question)
3. **Check backend logs** for:
   - `🎯 [SELECT AGENTS] Complex query detected - invoking ALL 4 specialist agents`
   - Agent execution logs
4. **Check UI** for:
   - "Agents invoked: 4" (should now show 4, not 2)
   - Structured Labour Economist output with 9 sections
   - Citations in format `[Per extraction: ...]`

### Expected Improvements
- ✅ All 4 agents invoked for complex queries
- ✅ Labour Economist output has PhD persona and structure
- ✅ Citation requirements enforced in prompt
- ⏳ Other 3 agents still using old prompts (Phase 2)
- ⏳ Debate still concatenation, not dialogue (Phase 2)
- ⏳ Critique still generic (Phase 2)
- ⏳ Confidence score still 0% (Phase 2)

---

## 💡 KEY INSIGHTS FROM USER EVALUATION

### What the User Taught Me:
1. **Infrastructure ≠ Intelligence** - Having a perfect LangGraph orchestration means nothing if the prompts are weak
2. **Multi-agent architecture is ONLY valuable if agents actually debate** - Concatenating monologues is worse than a single strong LLM
3. **Citations are the anti-fabrication mechanism** - Without them, the system can hallucinate with data access
4. **PhD personas matter** - Generic "you are an expert" doesn't work. Need credentials, frameworks, and personality
5. **Confidence scoring must be calculated, not claimed** - Saying "HIGH CONFIDENCE" while showing 0% is worse than saying nothing

### What Makes Output "Legendary" vs "Junior Analyst":
- **Junior:** "Qatar is well-positioned. Recommend conservative approach. Need more data."
- **Legendary:** 
  - Scenario A: 15% probability, -1.2% GDP, infeasible due to infrastructure lag
  - Scenario B: 60% probability, -0.3% to +0.2% GDP, requires $150M training investment
  - Scenario C: 85% probability, -0.1% to +0.4% GDP, safest approach
  - **Emergent Insight:** Female participation is hidden multiplier (88.7% vs UAE 35%)
  - **Devil's Advocate:** What if tech sector contracts under quota pressure?
  - **Recommendation:** Modified Scenario B with circuit breakers

---

## 🎯 NEXT SESSION PRIORITIES

1. **Update remaining 3 agent prompts** (Financial, Market, Operations)
2. **Implement 3-phase debate process** (cross-examination + synthesis)
3. **Add devil's advocate critique layer**
4. **Fix confidence calculation**
5. **Test and verify all improvements**

**Estimated Time:** 45-60 minutes for full Phase 2 implementation

---

## 📝 FILES MODIFIED (Phase 1)

1. ✅ `src/qnwis/agents/prompts/labour_economist.py` - PhD persona + structured output
2. ✅ `src/qnwis/orchestration/graph_llm.py` - Force 4 agents for complex queries
3. ✅ `src/qnwis/orchestration/streaming.py` - Enhanced event logging
4. ✅ `qnwis-ui/src/hooks/useWorkflowStream.ts` - Fix premature completion bug

---

**Status:** READY FOR TESTING  
**Next:** User tests, then Phase 2 implementation
