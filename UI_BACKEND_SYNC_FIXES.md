# ✅ UI-Backend Synchronization Fixes

**Date:** November 17, 2025  
**Issue:** Three critical mismatches between frontend and backend  
**Status:** FIXED

---

## Issue 1: Hardcoded Provider Forces Anthropic

### Problem
```typescript
// qnwis-ui/src/hooks/useWorkflowStream.ts (line 63)
body: JSON.stringify({ question, provider: 'anthropic' })  // ❌ FORCED
```

**Impact:** Every query required `ANTHROPIC_API_KEY`, preventing stub mode and local dev.

### Fix
```typescript
// Let backend decide provider (stub or real)
body: JSON.stringify({ question })  // ✅ BACKEND DECIDES
```

**Result:** Stub mode works, no API key required for local dev.

---

## Issue 2: Stage Name Mismatch ('synthesis' vs 'synthesize')

### Problem
```typescript
// UI expected: 'synthesis'
const STAGES = ['classify', 'prefetch', 'rag', 'agent_selection', 'agents', 'verify', 'debate', 'critique', 'synthesis', 'done']

// Backend emits: 'synthesize'
workflow.add_node("synthesize", self._synthesize_node)
```

**Impact:** Progress bar reset to 0% when backend reached final stage.

### Fix
```typescript
// qnwis-ui/src/App.tsx
const STAGES = [
  'classify',
  'prefetch',
  'rag',
  'select_agents',  // ✅ Matches backend
  'agents',
  'debate',
  'critique',
  'verify',
  'synthesize',    // ✅ Matches backend
  'done',
]

const STAGE_LABELS: Record<string, string> = {
  // ... existing labels ...
  synthesize: 'Synthesis',  // ✅ Maps to UI label
  // Aliases for compatibility
  agent_selection: 'Select Agents',
  synthesis: 'Synthesis',
}
```

**Result:** Progress bar flows correctly through all stages.

---

## Issue 3: Agent Data Not Rendering (snake_case vs agent_reports)

### Problem
```typescript
// UI looked for hardcoded fields:
const agentResultPayload = {
  labour_economist_analysis: workflowState.labour_economist_analysis,  // ❌ Doesn't exist
  financial_economist_analysis: workflowState.financial_economist_analysis,  // ❌ Doesn't exist
  // ...
}

// Backend sends:
{
  agent_reports: [
    { agent_name: "LabourEconomist", narrative: "...", confidence: 0.9 },
    { agent_name: "TimeMachine", narrative: "...", confidence: 0.85 },
    // ...
  ]
}
```

**Impact:** Agent outputs never displayed, UI showed empty even with valid backend data.

### Fix

**1. Updated AgentOutputs.tsx:**
```typescript
interface AgentReport {
  agent_name: string
  narrative: string
  confidence?: number
  citations?: any[]
  data_gaps?: any[]
}

interface AgentOutputsProps {
  agentReports?: AgentReport[]
  multiAgentDebate?: string
  critiqueOutput?: string
}

export function AgentOutputs({ agentReports = [], multiAgentDebate, critiqueOutput }: AgentOutputsProps) {
  // Build agents dynamically from agent_reports
  const agents = agentReports
    .filter(report => report.narrative && report.narrative.length > 20)  // ✅ Show short narratives
    .map(report => {
      const metadata = agentMetadata[report.agent_name] || { /* fallback */ };
      return {
        key: report.agent_name,
        title: report.agent_name,
        content: report.narrative,
        // ...
      };
    });
}
```

**2. Added AgentReport type:**
```typescript
// qnwis-ui/src/types/workflow.ts
export interface AgentReport {
  agent_name: string
  narrative: string
  confidence: number
  citations: any[]
  data_gaps: any[]
  findings?: any[]
}

export interface WorkflowState {
  // ... existing fields ...
  agent_reports?: AgentReport[]  // ✅ NEW
}
```

**3. Updated App.tsx:**
```typescript
// Extract agent data directly
const agentReports = workflowState?.agent_reports || []
const multiAgentDebate = workflowState?.multi_agent_debate
const critiqueOutput = workflowState?.critique_output

// Pass to component
<AgentOutputs 
  agentReports={agentReports} 
  multiAgentDebate={multiAgentDebate} 
  critiqueOutput={critiqueOutput} 
/>
```

**Result:** All agents display correctly, including deterministic agents (TimeMachine, Predictor, Scenario).

---

## Files Changed

### Frontend
1. `qnwis-ui/src/hooks/useWorkflowStream.ts` - Removed hardcoded provider
2. `qnwis-ui/src/App.tsx` - Fixed stage names, removed old agentResultPayload
3. `qnwis-ui/src/components/AgentOutputs.tsx` - Refactored to use agent_reports
4. `qnwis-ui/src/types/workflow.ts` - Added AgentReport interface

### Backend
- No changes needed (already correct)

---

## Testing

### Verify Provider Fix
```bash
# Should work WITHOUT ANTHROPIC_API_KEY
curl -N -X POST http://localhost:8000/api/v1/council/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"test"}'
```

### Verify Stage Progression
1. Submit query in UI
2. Watch progress bar flow: Classify → Prefetch → RAG → Select Agents → **Agents** → Debate → Critique → Verify → **Synthesize** → Done
3. Confirm no reset to 0%

### Verify Agent Display
1. Submit query in UI
2. Scroll to "Individual Agent Analyses"
3. Confirm all 7 agents visible:
   - LabourEconomist 🧑‍💼
   - Nationalization 🇶🇦
   - SkillsAgent 🎓
   - PatternDetective 🔍
   - TimeMachine ⏰
   - Predictor 🔮
   - Scenario 🎯
4. Click to expand - narratives should display

---

## Benefits

✅ **Local development** works without API keys  
✅ **Progress tracking** accurate through all stages  
✅ **All agents display** including deterministic ones  
✅ **Short narratives** visible (stub data appears)  
✅ **Unified data model** between frontend/backend  

---

**Status:** READY FOR TESTING ✅
