# ✅ Proper Stub Mode Architecture - ROOT CAUSE FIX

**Date:** November 17, 2025  
**Issue:** System froze when querying  
**Root Cause:** Deterministic agents called in stub mode  
**Solution:** Architectural separation of concerns

---

## ROOT CAUSE ANALYSIS

### What Was Happening (WRONG):

```python
# __init__ (lines 158-163) - ALWAYS instantiated deterministic agents
self.deterministic_agents = {
    "time_machine": TimeMachineAgent(self.data_client),  # ❌ Tries to connect to DB
    "predictor": PredictorAgent(self.data_client),      # ❌ Tries to connect to DB
    "scenario": ScenarioAgent(self.data_client),        # ❌ Tries to connect to DB
}

# _select_agents_node (lines 649-651) - Selected them for complex queries
selected_agent_names = [
    "LabourEconomist", "Nationalization", "SkillsAgent", "PatternDetective",
    "time_machine", "predictor", "scenario"  # ❌ Selected even in stub mode
]

# _invoke_agents_node (lines 824-864) - Executed database queries
result_str = await asyncio.to_thread(agent.baseline_report, metric="unemployment_rate")
# ❌ This BLOCKED because:
#    1. Database connection was slow/hanging
#    2. Queries were synchronous
#    3. No data in database to query
```

### Why It Froze:

1. **Stub mode** was enabled for LLM agents (no Anthropic API)
2. **Deterministic agents** were still instantiated with real `DataClient`
3. When query came in, workflow selected **all 7 agents** (4 LLM + 3 deterministic)
4. **LLM agents** returned stub responses quickly ✅
5. **Deterministic agents** tried to query database... and **HUNG** ❌

---

## THE PROPER FIX

### Architectural Principle:

**Deterministic agents are fundamentally incompatible with stub mode.**

- **Deterministic agents** = Require real database with populated data
- **Stub mode** = Testing workflow logic without external dependencies
- **These two concepts cannot coexist**

### Implementation:

#### 1. Conditional Instantiation (lines 160-171)

```python
# Initialize deterministic agents ONLY if NOT in stub mode
if provider != "stub":
    logger.info("Initializing deterministic agents (TimeMachine, Predictor, Scenario)")
    self.deterministic_agents = {
        "time_machine": TimeMachineAgent(self.data_client),
        "predictor": PredictorAgent(self.data_client),
        "scenario": ScenarioAgent(self.data_client),
    }
else:
    logger.info("Stub mode: Deterministic agents DISABLED (require real database)")
    self.deterministic_agents = {}  # ✅ Empty in stub mode
```

#### 2. Conditional Selection (lines 646-665)

```python
# USE ALL AVAILABLE AGENTS for complex/critical queries
if complexity == "complex" or complexity == "critical":
    # LLM Agents (always available)
    selected_agent_names = [
        "LabourEconomist", "Nationalization", "SkillsAgent", "PatternDetective"
    ]
    
    # Add deterministic agents ONLY if available (not in stub mode)
    if self.deterministic_agents:  # ✅ Only if dict is not empty
        selected_agent_names.extend([
            "time_machine", "predictor", "scenario"
        ])
        print(f"ALL {len(selected_agent_names)} AGENTS (4 LLM + 3 Deterministic)")
    else:
        print(f"{len(selected_agent_names)} LLM AGENTS (deterministic agents disabled in stub mode)")
```

#### 3. Invocation (lines 820-864)

```python
elif agent_name in self.deterministic_agents:
    # This block will NEVER execute in stub mode
    # because self.deterministic_agents is empty {}
    agent = self.deterministic_agents[agent_name]
    # ... database queries ...
```

---

## BEHAVIOR COMPARISON

### Before (BROKEN):

```
Stub Mode Workflow:
1. Initialize: Create TimeMachine/Predictor with DataClient ❌
2. Query arrives: Select all 7 agents ❌
3. LLM agents: Return stub responses ✅
4. Deterministic agents: Try database queries... FREEZE ❌
```

### After (FIXED):

```
Stub Mode Workflow:
1. Initialize: self.deterministic_agents = {} ✅
2. Query arrives: Select only 4 LLM agents ✅
3. LLM agents: Return stub responses ✅
4. Deterministic agents: Not selected, not called ✅
Result: Fast, non-blocking, pure LLM workflow testing
```

---

## PRODUCTION MODE (With Real API & Database)

```bash
# Set environment variables
export QNWIS_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-your-real-key

# Start backend
python start_api.py
```

### Production Workflow:

```
1. Initialize: provider = "anthropic" ✅
2. Initialize: self.deterministic_agents = {time_machine, predictor, scenario} ✅
3. Query arrives: Select all 7 agents ✅
4. LLM agents: Call Anthropic API ✅
5. Deterministic agents: Execute real database queries ✅
6. Result: Full-depth analysis with all agents
```

---

## FILES CHANGED

### `src/qnwis/orchestration/graph_llm.py`

**Lines 155-171**: Conditional initialization
```python
self.provider = provider  # Store provider for later checks

if provider != "stub":
    self.deterministic_agents = { ... }  # Real agents
else:
    self.deterministic_agents = {}  # Empty dict
```

**Lines 646-665**: Conditional selection
```python
if self.deterministic_agents:
    selected_agent_names.extend(["time_machine", "predictor", "scenario"])
```

**Lines 820-864**: Clean invocation (no timeout hacks)
```python
elif agent_name in self.deterministic_agents:
    # Only executes if agent exists (not in stub mode)
```

---

## WHY THIS IS THE RIGHT SOLUTION

### ❌ Wrong Approaches (Quick Fixes):

1. **Add timeouts to deterministic agents** → Hides the problem, agents still try to connect
2. **Return stub data from deterministic agents** → Requires changing agent code, mixes concerns
3. **Catch exceptions in workflow** → Doesn't prevent blocking, just handles failure

### ✅ Right Approach (Architectural):

1. **Separate concerns**: Stub mode = LLM only, Production = LLM + Deterministic
2. **Fail early**: Don't instantiate agents that can't work
3. **Clear contract**: Empty dict communicates "not available"
4. **No hacks**: No timeouts, no try/catch, no stub data in real agents

---

## TESTING

### Test Stub Mode (No API Key Needed):

```bash
# Ensure stub mode
export QNWIS_LLM_PROVIDER=stub
# OR just don't set it (defaults to stub)

python start_api.py
```

**Expected Output:**
```
✅ LLM Workflow initialized successfully
   Provider: stub
   Model: default
Stub mode: Deterministic agents DISABLED (require real database)
```

**Query Test:**
```bash
curl -N -X POST http://localhost:8000/api/v1/council/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"What are unemployment trends?"}'
```

**Expected:** 4 LLM agent responses (LabourEconomist, Nationalization, SkillsAgent, PatternDetective) ✅

### Test Production Mode (API Key Required):

```bash
export QNWIS_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-your-actual-key

python start_api.py
```

**Expected Output:**
```
✅ LLM Workflow initialized successfully
   Provider: anthropic
   Model: claude-sonnet-4-20250514
   API Key: sk-ant-api03-xyz...
Initializing deterministic agents (TimeMachine, Predictor, Scenario)
```

**Expected:** 7 agent responses (4 LLM + 3 deterministic) ✅

---

## DEPLOYMENT MODES

### Local Development (Default):
```bash
# No environment variables needed
python start_api.py
# Uses stub mode, 4 LLM agents only
```

### QA/Staging (With Database, No Real API):
```bash
export QNWIS_LLM_PROVIDER=stub
# Database connection configured in .env
python start_api.py
# Still uses stub LLM, but could use deterministic agents if needed
```

### Production (Full Stack):
```bash
export QNWIS_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-production-key
python start_api.py
# All 7 agents fully operational
```

---

## LESSONS LEARNED

1. **Architecture over hacks**: Fix the design, not the symptoms
2. **Separation of concerns**: Different agent types have different requirements
3. **Fail fast, fail clear**: Don't instantiate what you can't use
4. **Stub mode purpose**: Test LLM workflow logic, not database logic
5. **Root cause analysis**: Understand WHY before implementing HOW

---

**Status:** PROPERLY FIXED ✅

The system now:
- ✅ Works in stub mode without freezing
- ✅ Uses only LLM agents when database unavailable
- ✅ Uses all agents when fully configured
- ✅ Has clear architectural boundaries
- ✅ No timeout hacks or workarounds
