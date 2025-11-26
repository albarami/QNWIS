# 🚨 CRITICAL: Architectural Mismatch Discovered

**Status:** ❌ **MISMATCH CONFIRMED**  
**Severity:** HIGH - Workflow will fail at runtime  
**Date:** November 17, 2025

---

## 🔍 The Problem

The workflow in `graph_llm.py` tries to call **module-level `analyze()` functions** that **DON'T EXIST** for most LLM agents.

### What the Workflow Expects

```python
# Line 705-742 in graph_llm.py
async def _invoke_agents_node(self, state: WorkflowState):
    # Import as MODULES
    from qnwis.agents import labour_economist, nationalization, skills
    
    agent_modules = {
        "labour_economist": labour_economist,
        "nationalization": nationalization,  # ← Expects module with .analyze()
        "skills": skills,                    # ← Expects module with .analyze()
    }
    
    # Call analyze() on each module
    tasks = [
        agent_modules[name].analyze(query_text, extracted_facts, self.llm_client) 
        for name in agents_to_invoke
    ]
```

### What Actually Exists

| Agent | Has Module-Level `analyze()`? | Has Class? | Status |
|-------|------------------------------|------------|--------|
| **labour_economist** | ✅ YES (line 114) | ✅ YES (LabourEconomistAgent) | ✅ WORKS |
| **nationalization** | ❌ NO | ✅ YES (NationalizationAgent) | ❌ **WILL FAIL** |
| **skills** | ❌ NO | ✅ YES (SkillsAgent) | ❌ **WILL FAIL** |

---

## 📊 Evidence

### 1. labour_economist.py - WORKS ✅

```python
# File: src/qnwis/agents/labour_economist.py

# Module-level function (line 114)
async def analyze(
    query: str,
    extracted_facts: List[Dict[str, Any]],
    llm_client: Any,
) -> dict[str, Any]:
    """Labour economist analysis (module-level function)"""
    # ... implementation
```

This ONE works because it has a module-level `analyze()` function.

### 2. nationalization.py - BROKEN ❌

```python
# File: src/qnwis/agents/nationalization.py

# Only has a CLASS - no module-level analyze()
class NationalizationAgent(LLMAgent):
    """Agent focused on nationalization policy"""
    
    def __init__(self, client: DataClient, llm: LLMClient):
        super().__init__(client, llm)
    
    async def _fetch_data(self, question: str, context: Dict) -> Dict:
        # Fetch GCC unemployment data
        pass
    
    def _build_prompt(self, question: str, data: Dict, context: Dict):
        pass

# NO module-level analyze() function!
```

When the workflow tries to call `nationalization.analyze()`, it will get:
```
AttributeError: module 'qnwis.agents.nationalization' has no attribute 'analyze'
```

### 3. skills.py - BROKEN ❌

```python
# File: src/qnwis/agents/skills.py

# Only has a CLASS - no module-level analyze()
class SkillsAgent(LLMAgent):
    """Agent focused on skills pipeline"""
    
    def __init__(self, client: DataClient, llm: LLMClient):
        super().__init__(client, llm)
    
    async def _fetch_data(self, question: str, context: Dict) -> Dict:
        # Fetch skills data
        pass
    
    def _build_prompt(self, question: str, data: Dict, context: Dict):
        pass

# NO module-level analyze() function!
```

Same error as nationalization.

---

## 🏗️ Additional Agents Not Being Used

### Deterministic Agents Available (but not in workflow)

From `__init__.py`:
- ✅ TimeMachineAgent - Currently used in `_route_deterministic_node`
- ✅ PredictorAgent - Available but NOT USED
- ✅ ScenarioAgent - Available but NOT USED
- ✅ PatternDetectiveAgent - Available but NOT USED
- ✅ PatternMinerAgent - Available but NOT USED
- ✅ NationalStrategyAgent - Available but NOT USED
- ✅ AlertCenterAgent - Available but NOT USED

**Currently in `_route_deterministic_node`:**
```python
# Line 164-167 in graph_llm.py
self.deterministic_agents = {
    "time_machine": TimeMachineAgent(self.data_client),
    "predictor": PredictorAgent(self.data_client),
    "scenario": ScenarioAgent(self.data_client),
}
```

**Missing from workflow:**
- PatternDetectiveAgent
- PatternMinerAgent
- NationalStrategyAgent
- AlertCenterAgent

### LLM Agents Available (but not in workflow)

From filesystem:
- ✅ LabourEconomistAgent (class) + labour_economist.analyze() (function) - USED ✅
- ✅ NationalizationAgent (class) - REFERENCED BUT BROKEN ❌
- ✅ SkillsAgent (class) - REFERENCED BUT BROKEN ❌
- ✅ PatternDetectiveLLMAgent (class) - NOT USED ❌
- ✅ NationalStrategyLLMAgent (class) - NOT USED ❌
- ✅ ResearchScientistAgent (class) - NOT USED ❌

**Old agents (legacy from module-level era):**
- financial_economist.py (file exists)
- market_economist.py (file exists)
- operations_expert.py (file exists)

---

## 🔧 AgentSelector Mismatch

### What AgentSelector Knows About

```python
# From agent_selector.py line 28-59
AGENT_EXPERTISE = {
    "LabourEconomist": {...},      # ← String name
    "Nationalization": {...},       # ← String name
    "SkillsAgent": {...},          # ← String name
    "PatternDetective": {...},     # ← String name
    "NationalStrategy": {...},     # ← String name
}
```

### What the Workflow Tries to Use

```python
# From graph_llm.py line 727-731
agent_modules = {
    "labour_economist": labour_economist,  # ← Module reference
    "nationalization": nationalization,     # ← Module reference
    "skills": skills,                       # ← Module reference
}
```

**MISMATCH:**
- AgentSelector returns: `["LabourEconomist", "Nationalization", "SkillsAgent"]`
- Workflow expects: `["labour_economist", "nationalization", "skills"]`
- These don't map to each other!

---

## 🎯 Root Cause Analysis

### The Architecture Was Never Fully Migrated

Based on git history and file structure, it appears:

1. **Phase 1: Original Architecture (Module-Level Functions)**
   - All agents were module-level `analyze()` functions
   - Workflow called them directly
   - Simple and working

2. **Phase 2: Migration to Class-Based (INCOMPLETE)**
   - Most agents migrated to `LLMAgent` base class
   - `NationalizationAgent(LLMAgent)`, `SkillsAgent(LLMAgent)` created
   - But module-level `analyze()` functions were REMOVED
   - labour_economist kept BOTH (transitional state)
   - **Workflow was NOT updated to match**

3. **Phase 3: Current State (BROKEN)**
   - Workflow still tries to call module-level functions
   - Most agents no longer have these functions
   - Only labour_economist works (has both patterns)
   - Runtime failures inevitable

---

## 🚨 Impact Assessment

### What Works ✅
- Classification → routing decision
- Deterministic path (uses TimeMachineAgent correctly as class)
- labour_economist agent (has module-level analyze())

### What's Broken ❌
- ❌ Calling `nationalization.analyze()` → AttributeError
- ❌ Calling `skills.analyze()` → AttributeError
- ❌ AgentSelector returns wrong names
- ❌ 4+ deterministic agents not integrated
- ❌ 3+ LLM agents not integrated
- ❌ MIN_AGENTS=2, MAX_AGENTS=4 not respected in `_invoke_agents_node`

### Runtime Error You'd See

```python
Traceback (most recent call last):
  File "graph_llm.py", line 742
    tasks = [agent_modules[name].analyze(query_text, extracted_facts, self.llm_client)]
AttributeError: module 'qnwis.agents.nationalization' has no attribute 'analyze'
```

---

## ✅ The Fix Options

### Option A: Finish the Class-Based Migration (RECOMMENDED)

**Update `_invoke_agents_node` to use classes properly:**

```python
async def _invoke_agents_node(self, state: WorkflowState):
    """Invoke LLM agent CLASSES (not module functions)"""
    
    # Import agent CLASSES
    from qnwis.agents import (
        LabourEconomistAgent,
        NationalizationAgent,
        SkillsAgent,
        PatternDetectiveLLMAgent,
        NationalStrategyLLMAgent
    )
    
    # Map agent classes
    agent_classes = {
        "LabourEconomist": LabourEconomistAgent,
        "Nationalization": NationalizationAgent,
        "SkillsAgent": SkillsAgent,
        "PatternDetective": PatternDetectiveLLMAgent,
        "NationalStrategy": NationalStrategyLLMAgent,
    }
    
    # Get selected agents from AgentSelector
    selected_agent_names = state.get("selected_agents", [])
    
    # Instantiate and run agents
    tasks = []
    for agent_name in selected_agent_names:
        if agent_name in agent_classes:
            agent_class = agent_classes[agent_name]
            agent = agent_class(self.data_client, self.llm_client)
            
            # Use run_stream() or run() method from LLMAgent base class
            tasks.append(agent.run(question=query_text, context={
                "extracted_facts": extracted_facts,
                "classification": state.get("classification")
            }))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results...
```

### Option B: Add Module-Level Functions (QUICK FIX)

Add `analyze()` functions to nationalization.py and skills.py:

```python
# In nationalization.py
async def analyze(query: str, extracted_facts: list, llm_client) -> dict:
    """Module-level wrapper for class-based agent"""
    agent = NationalizationAgent(DataClient(), llm_client)
    return await agent.run(query, {"extracted_facts": extracted_facts})

# In skills.py  
async def analyze(query: str, extracted_facts: list, llm_client) -> dict:
    """Module-level wrapper for class-based agent"""
    agent = SkillsAgent(DataClient(), llm_client)
    return await agent.run(query, {"extracted_facts": extracted_facts})
```

### Option C: Hybrid (MOST FLEXIBLE)

Keep both patterns:
- Module-level functions for simple cases
- Classes for complex streaming/stateful agents
- Update workflow to detect and handle both

---

## 📋 Action Items

### Immediate Fixes Required

1. ✅ **Fix agent invocation mismatch**
   - [ ] Update `_invoke_agents_node` to use agent classes
   - [ ] OR add module-level analyze() to nationalization.py and skills.py

2. ✅ **Align AgentSelector with workflow**
   - [ ] Make sure agent names match between selector and workflow
   - [ ] Update agent_modules dict to use selected_agents from selector

3. ✅ **Integrate missing deterministic agents**
   - [ ] Add PatternDetectiveAgent to `_route_deterministic_node`
   - [ ] Add PatternMinerAgent
   - [ ] Add NationalStrategyAgent
   - [ ] Add AlertCenterAgent

4. ✅ **Integrate missing LLM agents**
   - [ ] Add PatternDetectiveLLMAgent to workflow
   - [ ] Add NationalStrategyLLMAgent to workflow
   - [ ] Remove or migrate old agents (financial_economist, market_economist, operations_expert)

5. ✅ **Respect MIN_AGENTS=2, MAX_AGENTS=4**
   - [ ] Remove hardcoded "invoke ALL 3 agents" logic
   - [ ] Use AgentSelector results properly
   - [ ] Honor intelligent agent selection

---

## 🎯 Recommended Solution

**I recommend Option A: Complete the class-based migration**

This aligns with your architecture document showing:
- 7 deterministic agents (all classes)
- 4 LLM agents (all classes)
- AgentSelector orchestrating intelligent selection
- Proper separation of concerns

The workflow should:
1. Use AgentSelector to pick 2-4 agents based on query
2. Instantiate the selected agent classes
3. Call their `run()` or `run_stream()` method
4. Process AgentReport results

This is clean, maintainable, and matches the documented architecture.

---

## 📚 Files That Need Updates

1. **`src/qnwis/orchestration/graph_llm.py`**
   - Line 705-742: `_invoke_agents_node` - switch from modules to classes
   - Line 361-377: `_route_deterministic_node` - add missing deterministic agents
   - Line 655-663: Use AgentSelector results properly

2. **`src/qnwis/orchestration/agent_selector.py`**
   - Verify agent names match what workflow will use
   - Update AGENT_EXPERTISE to include all 11 agents

3. **Optional: Add wrapper functions**
   - `src/qnwis/agents/nationalization.py` - add module-level analyze()
   - `src/qnwis/agents/skills.py` - add module-level analyze()

---

**Status:** ❌ Architectural mismatch confirmed  
**Priority:** HIGH - System will fail at runtime  
**Recommendation:** Follow Option A to complete class-based migration
