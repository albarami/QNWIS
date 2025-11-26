# 🎯 QNWIS Enterprise Frontend - Complete Type Definitions

**Source**: Backend code analysis (graph_llm.py, base.py, council_llm.py)  
**Purpose**: TypeScript interfaces that match backend EXACTLY

---

## SSE Event Structure

```typescript
// Base event structure from backend
interface WorkflowEvent {
  stage: string
  status: 'running' | 'streaming' | 'complete' | 'error'
  payload?: Record<string, any>
  latency_ms?: number
  timestamp?: string
}

// Specific stage types
type WorkflowStage =
  | 'classify'
  | 'prefetch'
  | 'rag'
  | 'agent_selection'
  | 'agents'
  | 'debate'
  | 'critique'
  | 'verify'
  | 'synthesize'
  | 'done'
```

---

## Classification

```typescript
interface Classification {
  intent: string
  complexity: 'simple' | 'complex' | 'critical'
  confidence: number
  entities: Record<string, any>
  route_to: string | null
  topics?: string[]
}
```

---

## Prefetch

```typescript
interface ExtractedFact {
  metric: string
  value: string | number | boolean
  source: string
  confidence: number
  raw_text: string
}

interface PrefetchResult {
  extracted_facts: ExtractedFact[]
  fact_count: number
}
```

---

## RAG

```typescript
interface RAGContext {
  snippets_retrieved: number
  sources: string[]
}
```

---

## Agent Selection

```typescript
interface AgentSelectionResult {
  selected_agents: string[]
  selected_count: number
  total_available: number
  mode: 'INTELLIGENT_SELECTION' | 'LEGENDARY_DEPTH'
  explanation: {
    selected_count: number
    total_available: number
    savings: string
    intent: string
    complexity: string
    agents: Record<string, {
      description: string
      reasons: string[]
    }>
  }
}
```

---

## Agent Execution

```typescript
interface AgentReport {
  agent: string
  agent_name?: string
  narrative: string
  confidence: number
  findings?: Insight[]
  insights?: Insight[]
  warnings: string[]
  derived_results?: any[]
  metadata: Record<string, any>
  citations?: Citation[]
  citations_count?: number
  data_gaps_count?: number
}

interface Insight {
  finding: string
  confidence_score: number
  warnings: string[]
}

interface Citation {
  text: string
  source: string
  query_id?: string
}

// Agent status tracking
interface AgentStatus {
  name: string
  status: 'pending' | 'running' | 'complete' | 'error'
  startTime?: number
  endTime?: number
  latency_ms?: number
  report?: AgentReport
}
```

---

## Debate

```typescript
interface DebateResults {
  contradictions_found: number
  resolved: number
  flagged_for_review: number
  consensus_narrative: string
  latency_ms: number
  status: 'complete' | 'skipped'
  contradictions?: Contradiction[]
  resolutions?: Resolution[]
}

interface Contradiction {
  metric_name: string
  agent1_name: string
  agent1_value: number
  agent1_value_str: string
  agent1_citation: string
  agent1_confidence: number
  agent2_name: string
  agent2_value: number
  agent2_value_str: string
  agent2_citation: string
  agent2_confidence: number
  severity: 'high' | 'medium' | 'low'
}

interface Resolution {
  resolution: 'agent1_correct' | 'agent2_correct' | 'both_valid' | 'neither_valid'
  explanation: string
  recommended_value: number | null
  recommended_citation: string | null
  confidence: number
  action: 'use_agent1' | 'use_agent2' | 'use_both' | 'flag_for_review'
}
```

---

## Critique

```typescript
interface CritiqueResults {
  critiques: CritiqueItem[]
  overall_assessment: string
  confidence_adjustments: Record<string, number>
  red_flags: string[]
  strengthened_by_critique: boolean
  latency_ms: number
  status: 'complete' | 'skipped'
}

interface CritiqueItem {
  agent_name: string
  weakness_found: string
  counter_argument: string
  severity: 'high' | 'medium' | 'low'
  robustness_score: number
}
```

---

## Verification

```typescript
interface VerificationResult {
  status: 'complete'
  warnings: string[]
  warning_count: number
  error_count: number
  missing_citations: number
  citation_violations: CitationViolation[]
  number_violations: NumberViolation[]
  fabricated_numbers: number
}

interface CitationViolation {
  agent: string
  issue: string
  narrative_snippet: string
}

interface NumberViolation {
  agent: string
  number: string
  issue: string
  context: string
}
```

---

## Synthesis

```typescript
interface SynthesisResult {
  synthesis: string
  confidence_score?: number
  sources_integrated: number
}
```

---

## Final State

```typescript
interface FinalWorkflowState {
  question: string
  classification: Classification
  prefetch: PrefetchResult
  rag_context: RAGContext
  selected_agents: string[]
  agent_reports: AgentReport[]
  debate_results?: DebateResults
  critique_results?: CritiqueResults
  verification: VerificationResult
  synthesis: string
  metadata: {
    start_time: string
    total_latency_ms: number
  }
  reasoning_chain: string[]
  error?: string
}
```

---

## Frontend State

```typescript
interface AppState {
  // Connection
  connectionStatus: 'idle' | 'connecting' | 'connected' | 'error'
  isStreaming: boolean
  error: string | null
  
  // Workflow
  currentStage: WorkflowStage | null
  completedStages: Set<WorkflowStage>
  
  // Data (accumulates as events arrive)
  question: string
  classification: Classification | null
  prefetchFacts: ExtractedFact[]
  ragContext: RAGContext | null
  selectedAgents: string[]
  agentStatuses: Map<string, AgentStatus>
  debateResults: DebateResults | null
  critiqueResults: CritiqueResults | null
  verification: VerificationResult | null
  synthesis: string
  
  // Metadata
  startTime: string | null
  stageTiming: Map<WorkflowStage, number>
  reasoningChain: string[]
  
  // Final
  finalState: FinalWorkflowState | null
}
```

---

## Request/Response

```typescript
interface CouncilRequest {
  question: string
  provider: 'stub' | 'anthropic' | 'openai'
  model?: string
}

interface StreamEventResponse {
  stage: string
  status: string
  payload: Record<string, any>
  latency_ms?: number
  timestamp?: string
  message?: string
}
```

---

## Type Guards

```typescript
// Validate event structure
function isValidWorkflowEvent(event: any): event is WorkflowEvent {
  return (
    typeof event === 'object' &&
    typeof event.stage === 'string' &&
    typeof event.status === 'string'
  )
}

// Check if stage is final
function isFinalStage(stage: string): stage is 'done' {
  return stage === 'done'
}

// Check if agent event
function isAgentEvent(stage: string): boolean {
  return stage.startsWith('agent:')
}
```

---

**These types are FROZEN - match backend exactly. No modifications without backend changes.**
