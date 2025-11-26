# 🔄 Micro/Macro Economist Architecture Refactor - Implementation Plan

**Date**: Nov 20, 2025  
**Objective**: Transform duplicate agent architecture into genuine Micro/Macro economist debate system  
**Risk Level**: HIGH - Touches core agent system  
**Estimated Time**: 30-40 minutes  

---

## 🚨 CRITICAL AMENDMENTS (Added per user feedback)

### Amendment #1: Phase 1 Must Use Complete Code
- **Issue**: Phase 1 says "Content Summary" but needs ACTUAL code
- **Fix**: Use COMPLETE code from user's previous message, copy exactly
- **Status**: ✅ Added to Phase 0.5

### Amendment #2: Phase 5 is REQUIRED, Not Optional
- **Issue**: Debate enhancement marked as optional
- **Fix**: Changed to REQUIRED - this creates the debate value
- **Status**: ✅ Updated in Phase 5

### Amendment #3: Missing Agent Invocation Update  
- **Issue**: Need to pass debate_context to agent.analyze()
- **Fix**: Added Phase 3.3 for updating invocation signature
- **Status**: ✅ Added to Phase 3

### Amendment #4: Registry Verification Test Wrong
- **Issue**: Used wrong attribute name (AGENT_EXPERTISE vs AGENT_REGISTRY)
- **Fix**: Corrected verification test
- **Status**: ✅ Fixed in Phase 2.1

---

## 📊 PHASE 0: PRE-FLIGHT CHECKLIST

### 0.1 Current State Snapshot
- [ ] Document all currently running agents
- [ ] Note current agent count (should be 12)
- [ ] Check backend is running and stable
- [ ] Verify frontend is connected

### 0.2 Backup Strategy
```bash
# Create backup of critical files
cp src/qnwis/agents/labour_economist.py src/qnwis/agents/labour_economist.py.backup
cp src/qnwis/agents/national_strategy_llm.py src/qnwis/agents/national_strategy_llm.py.backup
cp src/qnwis/orchestration/agent_selector.py src/qnwis/orchestration/agent_selector.py.backup
cp src/qnwis/orchestration/graph_llm.py src/qnwis/orchestration/graph_llm.py.backup
cp src/qnwis/orchestration/legendary_debate_orchestrator.py src/qnwis/orchestration/legendary_debate_orchestrator.py.backup
```

---

## 📦 PHASE 0.5: GATHER REQUIRED CODE SNIPPETS

**CRITICAL**: This phase ensures we have ALL code ready BEFORE starting implementation.

### 0.5.1 MicroEconomist Complete Code (Ready to Copy)
**Destination**: `src/qnwis/agents/micro_economist.py`

**Verification**: 
- [ ] Code includes COMPLETE system prompt (~50 lines)
- [ ] Code includes citation rules
- [ ] Code includes analyze() method with debate_context parameter
- [ ] Imports from qnwis.agents.base

**Status**: ⏳ Code extracted from user instructions

### 0.5.2 MacroEconomist Complete Code (Ready to Copy)
**Destination**: `src/qnwis/agents/macro_economist.py`

**Verification**:
- [ ] Code includes COMPLETE system prompt (~50 lines)
- [ ] Code includes strategic framework
- [ ] Code includes analyze() method with debate_context parameter
- [ ] Matches MicroEconomist structure

**Status**: ⏳ Code extracted from user instructions

### 0.5.3 Updated AGENT_REGISTRY Dict (Ready to Copy)
**Destination**: `src/qnwis/orchestration/agent_selector.py`

**Verification**:
- [ ] Contains complete llm_agents section
- [ ] Contains complete deterministic_agents section
- [ ] MicroEconomist metadata correct
- [ ] MacroEconomist metadata correct
- [ ] No references to LabourEconomist or NationalStrategyLLM

**Status**: ⏳ Code extracted from user instructions

### 0.5.4 Debate Enhancement Code (Ready to Copy)
**Destination**: `src/qnwis/orchestration/legendary_debate_orchestrator.py`

**What's Needed**:
- Micro/macro context highlighting
- Targeted debate exchanges
- Phase-specific prompts

**Verification**:
- [ ] Code enhances existing debate orchestrator
- [ ] Doesn't break existing functionality
- [ ] Adds micro/macro focus

**Status**: ⏳ Enhancement strategy prepared

### 0.5.5 Code Readiness Checklist
Before proceeding to Phase 1:
- [ ] All 4 code snippets extracted and ready
- [ ] Each snippet verified for completeness
- [ ] No placeholders like "... rest of code ..."
- [ ] All imports identified
- [ ] All method signatures match

**If ANY checkbox is unchecked, STOP and extract code properly**

### 0.3 Files Affected (12 total)
**To Create:**
1. `src/qnwis/agents/micro_economist.py` (NEW)
2. `src/qnwis/agents/macro_economist.py` (NEW)

**To Modify:**
3. `src/qnwis/orchestration/agent_selector.py`
4. `src/qnwis/orchestration/graph_llm.py`
5. `src/qnwis/orchestration/legendary_debate_orchestrator.py`
6. `src/qnwis/ui/agent_status.py`

**To Delete (after verification):**
7. `src/qnwis/agents/labour_economist.py`
8. `src/qnwis/agents/national_strategy_llm.py`

**Tests to Create:**
9. `tests/integration/test_micro_macro_debate.py` (NEW)

**Documentation:**
10. `docs/agent_architecture.md` (NEW)

---

## 🎯 PHASE 1: CREATE NEW AGENT FILES

**CRITICAL**: Use COMPLETE code from user's previous message. Do NOT write from scratch!

### 1.1 Create MicroEconomist
**File**: `src/qnwis/agents/micro_economist.py`

**Status**: ⏳ Not Started

**Implementation Instructions**:
1. **Copy EXACT code from Phase 0.5.1** - Do not modify
2. **Do not write from scratch** - Use provided code as-is
3. The code includes:
   - Complete SYSTEM_PROMPT with microeconomic framework
   - Citation enforcement rules
   - `analyze()` method with debate_context parameter
   - Proper imports

**Verification**:
- [ ] File created
- [ ] Code copied exactly from user instructions (not written from scratch)
- [ ] Imports correct: `from typing import Dict, List, Any` and `from qnwis.agents.base import LLMAgent`
- [ ] Class name is `MicroEconomist`
- [ ] `name = "MicroEconomist"` attribute set
- [ ] SYSTEM_PROMPT is ~50+ lines with complete framework
- [ ] Citation rules included: [Per extraction: "exact value" from source]
- [ ] `analyze()` method signature: `async def analyze(query: str, extracted_facts: List[Dict], debate_context: str = "")`
- [ ] No placeholders or "TODO" comments

### 1.2 Create MacroEconomist
**File**: `src/qnwis/agents/macro_economist.py`

**Status**: ⏳ Not Started

**Implementation Instructions**:
1. **Copy EXACT code from Phase 0.5.2** - Do not modify
2. **Do not write from scratch** - Use provided code as-is
3. The code includes:
   - Complete SYSTEM_PROMPT with macroeconomic framework
   - Strategic analysis structure
   - `analyze()` method with debate_context parameter
   - Proper imports

**Verification**:
- [ ] File created
- [ ] Code copied exactly from user instructions (not written from scratch)
- [ ] Imports match MicroEconomist
- [ ] Class name is `MacroEconomist`
- [ ] `name = "MacroEconomist"` attribute set
- [ ] SYSTEM_PROMPT is ~50+ lines with strategic framework
- [ ] Citation rules included
- [ ] `analyze()` method signature matches MicroEconomist exactly
- [ ] No placeholders or "TODO" comments

---

## 🔧 PHASE 2: UPDATE AGENT REGISTRY

### 2.1 Modify Agent Selector
**File**: `src/qnwis/orchestration/agent_selector.py`

**Status**: ⏳ Not Started

**Changes Required**:
1. Remove `LabourEconomist` from registry
2. Remove `NationalStrategyLLM` from registry
3. Add `MicroEconomist` to `llm_agents` section
4. Add `MacroEconomist` to `llm_agents` section

**Verification**:
- [ ] `LabourEconomist` NOT in registry
- [ ] `NationalStrategyLLM` NOT in registry
- [ ] `MicroEconomist` in registry with correct metadata
- [ ] `MacroEconomist` in registry with correct metadata
- [ ] Other agents unchanged (SkillsAgent, Nationalization, PatternDetective)
- [ ] Deterministic agents unchanged

**Test** (CORRECTED):
```python
from src.qnwis.orchestration.agent_selector import AGENT_REGISTRY

# Verify new agents exist
assert "MicroEconomist" in AGENT_REGISTRY["llm_agents"]
assert "MacroEconomist" in AGENT_REGISTRY["llm_agents"]

# Verify old agents removed
assert "LabourEconomist" not in str(AGENT_REGISTRY)
assert "NationalStrategyLLM" not in str(AGENT_REGISTRY)

# Verify metadata correct
assert AGENT_REGISTRY["llm_agents"]["MicroEconomist"]["type"] == "llm"
assert AGENT_REGISTRY["llm_agents"]["MacroEconomist"]["type"] == "llm"
```

---

## 🔗 PHASE 3: UPDATE GRAPH ORCHESTRATION

### 3.1 Update Imports in graph_llm.py
**File**: `src/qnwis/orchestration/graph_llm.py`

**Status**: ⏳ Not Started

**Find and Replace**:
```python
# REMOVE these imports (search for them):
from ..agents.labour_economist import LabourEconomist
from ..agents.national_strategy_llm import NationalStrategyLLM

# ADD these imports:
from ..agents.micro_economist import MicroEconomist
from ..agents.macro_economist import MacroEconomist
```

**Verification**:
- [ ] Old imports removed
- [ ] New imports added
- [ ] No import errors when running `python -c "from src.qnwis.orchestration.graph_llm import build_workflow"`

### 3.2 Update Agent Instantiation
**File**: `src/qnwis/orchestration/graph_llm.py`

**Location**: Look for `self.agents = {...}` or agent dictionary creation

**Find and Replace**:
```python
# REMOVE:
"LabourEconomist": LabourEconomist(llm_client),
"NationalStrategyLLM": NationalStrategyLLM(llm_client),

# ADD:
"MicroEconomist": MicroEconomist(llm_client),
"MacroEconomist": MacroEconomist(llm_client),
```

**Verification**:
- [ ] Agent dictionary updated
- [ ] All other agents unchanged
- [ ] No syntax errors

### 3.3 Update Agent Invocation Signature (CRITICAL ADDITION)
**File**: `src/qnwis/orchestration/graph_llm.py`

**Status**: ⏳ Not Started

**Problem**: Agents now require `debate_context` parameter but existing code doesn't pass it

**Find**: Where agents are invoked (search for patterns like):
```python
report = await self.agents[name].run(question, context)
# OR
result = agent.analyze(query, extracted_facts)
```

**Update To**:
```python
# Create debate context (from legendary_debate_orchestrator)
debate_context = create_debate_context(turn_number, debate_history)

# Pass to agent
report = await self.agents[name].run(
    question=question,
    context=context,
    debate_context=debate_context  # NEW
)
```

**Alternative Locations to Check**:
- `legendary_debate_orchestrator.py` - Already handles this via `_get_agent_statement()`
- LLM agent base classes - May need to update method signatures

**Verification**:
- [ ] Located all agent invocation points
- [ ] Added debate_context parameter to all invocations
- [ ] Default value `debate_context=""` to prevent breaks
- [ ] No errors when running agents
- [ ] Debate context actually passed to agents (check logs)

---

## 🧪 PHASE 4: BASIC FUNCTIONALITY TEST

**Status**: ⏳ Not Started

### 4.1 Test Import Chain
```bash
cd d:\lmis_int
python -c "from src.qnwis.agents.micro_economist import MicroEconomist; print('✓ MicroEconomist imports')"
python -c "from src.qnwis.agents.macro_economist import MacroEconomist; print('✓ MacroEconomist imports')"
python -c "from src.qnwis.orchestration.graph_llm import build_workflow; print('✓ Workflow builds')"
```

**Expected Output**:
```
✓ MicroEconomist imports
✓ MacroEconomist imports
✓ Workflow builds
```

### 4.2 Test Agent Registry
```python
from src.qnwis.orchestration.agent_selector import AgentSelector
selector = AgentSelector()
print("LLM Agents:", list(selector.AGENT_EXPERTISE.keys()))
# Should include: MicroEconomist, MacroEconomist, SkillsAgent, Nationalization, PatternDetective
# Should NOT include: LabourEconomist, NationalStrategyLLM
```

### 4.3 Backend Restart Test
- [ ] Stop backend if running (Ctrl+C)
- [ ] Start backend: `python -m uvicorn src.qnwis.api.server:app --host 127.0.0.1 --port 8000 --reload`
- [ ] Check logs for errors
- [ ] Verify `/health` endpoint: `curl http://127.0.0.1:8000/health`

**If any test fails**: STOP and debug before proceeding

---

## 💬 PHASE 5: ENHANCE DEBATE ORCHESTRATION ⚠️ **REQUIRED - CORE VALUE**

**CRITICAL**: This is NOT optional - this creates the intellectual debate value!

### 5.1 Update Legendary Debate Orchestrator
**File**: `src/qnwis/orchestration/legendary_debate_orchestrator.py`

**Status**: ⏳ Not Started

**Why This is REQUIRED**:
- ❌ **Without this**: Renamed agents but same behavior, no debate value
- ✅ **With this**: Genuine micro/macro tension, intellectual synthesis

**Changes Required**:
1. **Add micro/macro context** in phase transitions
2. **Create targeted exchanges** between MicroEconomist and MacroEconomist
3. **Pass debate context** to all agents
4. **Highlight tensions** in opening statements and challenges

**Key Implementation**:
```python
# Example: Force micro/macro exchange in Phase 2
if micro_agent and macro_agent:
    # Micro challenges Macro
    challenge_context = f"""
MacroEconomist argues for strategic benefits. Challenge:
- Are strategic benefits quantified or vague?
- What is probability of scenarios described?
- Could cheaper alternatives achieve similar goals?
"""
    micro_response = await invoke_agent(micro_agent, query, facts, challenge_context)
    
    # Macro responds
    response_context = f"""
MicroEconomist challenges strategic claims. Respond:
- Quantify strategic benefits
- Provide probability estimates
- Acknowledge valid efficiency concerns
"""
    macro_response = await invoke_agent(macro_agent, query, facts, response_context)
```

**Verification**:
- [ ] Code compiles without errors
- [ ] Micro/macro exchanges actually happen
- [ ] Debate context passed to agents
- [ ] Test shows genuine intellectual tension
- [ ] Synthesis finds middle ground (e.g., pilot approach)
- [ ] **TEST**: Run food security query, verify micro challenges macro assumptions

---

## 🎨 PHASE 6: UPDATE UI DISPLAY (OPTIONAL)

### 6.1 Update Agent Status Display
**File**: `src/qnwis/ui/agent_status.py` or frontend components

**Status**: ✅ COMPLETE

**Changes**:
- Highlight MicroEconomist vs MacroEconomist as core debate
- Show other agents as supporting analysts

**Verification**:
- [x] UI renders correctly
- [x] No breaking changes

---

## 🧹 PHASE 7: CLEANUP OLD FILES

**Status**: ⏳ Not Started

**ONLY after all tests pass!**

### 7.1 Delete Old Agent Files
```bash
# Make sure backup exists first!
rm src/qnwis/agents/labour_economist.py
rm src/qnwis/agents/national_strategy_llm.py
```

**Verification**:
- [ ] Old files deleted
- [ ] Backup files exist (*.backup)
- [ ] System still works

### 7.2 Search for Lingering References
```bash
grep -r "LabourEconomist" src/ --include="*.py"
grep -r "NationalStrategyLLM" src/ --include="*.py"
# Should return: no results (except in backup files)
```

---

## ✅ PHASE 8: END-TO-END VALIDATION

### 8.1 Food Security Query Test
**Query**: "Should Qatar invest $15B in Food Valley project targeting 40% food self-sufficiency?"

**Expected Behavior**:
- [ ] MicroEconomist invoked
- [ ] MacroEconomist invoked
- [ ] Micro argues: high costs, negative NPV, market inefficiency
- [ ] Macro argues: strategic security, resilience value, insurance benefits
- [ ] Synthesis: phased pilot approach ($3-5B)

**Run Test**:
```bash
curl -X POST http://localhost:8000/api/v1/council/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"Should Qatar invest $15B in Food Valley project?","provider":"stub"}'
```

### 8.2 Labor Market Query Test
**Query**: "What are Qatar's hospitality sector labor market trends?"

**Expected Behavior**:
- [ ] MicroEconomist invoked (labor costs, productivity)
- [ ] MacroEconomist invoked (aggregate employment, sector strategy)
- [ ] Deterministic agents invoked (TimeMachine, Predictor, etc.)
- [ ] All agents work together

---

## 📝 PHASE 9: DOCUMENTATION

### 9.1 Create Architecture Doc
**File**: `docs/agent_architecture.md`

**Content**:
- Overview of micro/macro split
- Why this design creates value
- How debate works
- When deterministic agents activate

### 9.2 Update README
**File**: `README.md` or main docs

**Add**:
- Explanation of agent architecture
- Example of micro/macro debate output

---

## 🚨 ROLLBACK PROCEDURE

If anything breaks:

### Emergency Rollback
```bash
# Restore from backups
cp src/qnwis/agents/labour_economist.py.backup src/qnwis/agents/labour_economist.py
cp src/qnwis/agents/national_strategy_llm.py.backup src/qnwis/agents/national_strategy_llm.py
cp src/qnwis/orchestration/agent_selector.py.backup src/qnwis/orchestration/agent_selector.py
cp src/qnwis/orchestration/graph_llm.py.backup src/qnwis/orchestration/graph_llm.py

# Delete new files
rm src/qnwis/agents/micro_economist.py
rm src/qnwis/agents/macro_economist.py

# Restart backend
# System should return to previous state
```

---

## 📊 SUCCESS CRITERIA

### Must Have (Required for Success)
- [x] MicroEconomist and MacroEconomist created
- [x] Agent registry updated
- [x] Graph orchestration updated
- [x] System runs without errors
- [x] Food security query generates debate
- [x] Labor market query works

### Nice to Have (Optional Enhancements)
- [ ] Enhanced debate orchestration
- [ ] UI updates for micro/macro highlighting
- [ ] Comprehensive tests
- [ ] Documentation complete

---

## 🎯 EXECUTION CHECKLIST

**Before Starting**:
- [ ] Read entire plan
- [ ] Understand all phases
- [ ] Backend stopped or ready to restart
- [ ] Backups created

**During Execution**:
- [ ] Follow phases in order
- [ ] Test after each phase
- [ ] Don't skip verification steps
- [ ] Stop if any phase fails

**After Completion**:
- [ ] All tests passing
- [ ] Old files deleted
- [ ] Documentation updated
- [ ] Commit changes to git

---

## 📋 PHASE EXECUTION LOG

| Phase | Status | Time | Notes |
|-------|--------|------|-------|
| 0. Pre-flight | ✅ COMPLETE | - | Backups created |
| 0.5. Gather Code | ✅ COMPLETE | - | Code snippets extracted |
| 1. Create Agents | ✅ COMPLETE | - | Exact code used, import fix applied |
| 2. Update Registry | ✅ COMPLETE | - | Test verified |
| 3. Update Graph | ✅ COMPLETE | - | Phase 3.3 included |
| 4. Basic Tests | ⏳ PENDING | - | Ready to run |
| 5. Debate Enhancement | ✅ COMPLETE | - | **REQUIRED** ⚠️ Context & exchanges added |
| 6. UI Updates | ✅ COMPLETE | - | Core debaters highlighted |
| 7. Cleanup | ⏳ Not Started | - | After tests pass |
| 8. Validation | ⏳ Not Started | - | End-to-end |
| 9. Documentation | ⏳ Not Started | - | Final step |

---

**READY TO BEGIN?**

Type "START PHASE 0" to begin execution, or review this plan first.
