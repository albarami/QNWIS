# STEP 39 Remaining Work

**Current Status**: Foundation complete, need to finish implementation

---

## ✅ COMPLETED (11 files)

### LLM Infrastructure
1. ✅ `src/qnwis/llm/__init__.py`
2. ✅ `src/qnwis/llm/config.py`
3. ✅ `src/qnwis/llm/exceptions.py`
4. ✅ `src/qnwis/llm/client.py`
5. ✅ `src/qnwis/llm/parser.py`

### Agent Base
6. ✅ `src/qnwis/agents/base_llm.py`

### Agent Prompts
7. ✅ `src/qnwis/agents/prompts/__init__.py`
8. ✅ `src/qnwis/agents/prompts/labour_economist.py`
9. ✅ `src/qnwis/agents/prompts/nationalization.py`
10. ✅ `src/qnwis/agents/prompts/skills.py`
11. ✅ `src/qnwis/agents/prompts/pattern_detective.py`
12. ✅ `src/qnwis/agents/prompts/national_strategy.py`

### Verification Fixes
13. ✅ `src/qnwis/verification/units.py`
14. ✅ `src/qnwis/verification/checks.py`

---

## 🔄 REMAINING (Critical Files)

### Rebuild Agents (5 files) - HIGH PRIORITY
These need to inherit from LLMAgent and use the new prompts:

1. ⏳ `src/qnwis/agents/labour_economist.py` - Rebuild with LLMAgent
2. ⏳ `src/qnwis/agents/nationalization.py` - Rebuild with LLMAgent
3. ⏳ `src/qnwis/agents/skills.py` - Rebuild with LLMAgent
4. ⏳ `src/qnwis/agents/pattern_detective.py` - Rebuild with LLMAgent
5. ⏳ `src/qnwis/agents/national_strategy.py` - Rebuild with LLMAgent

### LangGraph Orchestration (2 files) - HIGH PRIORITY
6. ⏳ `src/qnwis/orchestration/graph_llm.py` - LangGraph workflow
7. ⏳ `src/qnwis/orchestration/streaming.py` - Streaming adapter

### Synthesis Engine (1 file) - HIGH PRIORITY
8. ⏳ `src/qnwis/synthesis/engine.py` - LLM-based synthesis

### Chainlit UI Update (1 file) - HIGH PRIORITY
9. ⏳ `src/qnwis/ui/chainlit_app.py` - Update for streaming

### Tests (Multiple files) - MEDIUM PRIORITY
10. ⏳ `tests/unit/test_llm_client.py`
11. ⏳ `tests/unit/test_llm_parser.py`
12. ⏳ `tests/unit/test_verification_fixes.py`
13. ⏳ `tests/integration/test_llm_agents.py`

### Documentation (1 file) - REQUIRED
14. ⏳ `docs/reviews/step39_review.md`

---

## 📋 Implementation Strategy

### Next Immediate Steps:

**STEP 1**: Rebuild the 5 agents (most critical)
- Each agent needs to:
  - Inherit from `LLMAgent`
  - Implement `_fetch_data()` method
  - Implement `_build_prompt()` method
  - Use the prompt builders from `src/qnwis/agents/prompts/`

**STEP 2**: Create LangGraph workflow
- Define `WorkflowState` TypedDict
- Build graph with nodes: classify → prefetch → agents → verify → synthesize
- Implement streaming

**STEP 3**: Create synthesis engine
- LLM-based synthesis of multi-agent findings
- Streaming support

**STEP 4**: Update Chainlit UI
- Stream agent outputs
- Display LLM reasoning
- Show verification results

**STEP 5**: Write tests
- Unit tests for LLM client
- Unit tests for parser
- Integration tests for agents
- End-to-end workflow tests

**STEP 6**: Documentation
- Create step39_review.md
- Document all changes
- Provide test evidence

---

## 🎯 Critical Path

The critical path to get a working system:

1. **Rebuild 5 agents** (2-3 hours)
2. **LangGraph workflow** (1 hour)
3. **Synthesis engine** (30 min)
4. **Update Chainlit UI** (1 hour)
5. **Basic tests** (1 hour)
6. **Documentation** (30 min)

**Total**: ~6-7 hours of focused work

---

## ⚠️ Important Notes

- All agents MUST use the deterministic data layer (DataClient)
- All agents MUST validate numbers against QueryResults
- All agents MUST stream their output
- Chainlit UI MUST use Markdown (no raw HTML)
- All timestamps MUST use UTC wall-clock
- Percent values MUST be normalized correctly
- Sum-to-one validation MUST use correct formula

---

**Ready to continue with agent rebuild?**
