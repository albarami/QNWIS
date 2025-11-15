// Core workflow stages matching the LangGraph workflow plus dynamic agent stages
export type WorkflowStage =
  | 'heartbeat'
  | 'classify'
  | 'prefetch'
  | 'rag'
  | 'agent_selection'
  | 'verify'
  | 'debate'
  | 'critique'
  | 'synthesis'
  | 'complete'
  | `agent:${string}`
  | string

export type QueryComplexity = 'simple' | 'medium' | 'complex' | 'critical'

export interface ExtractedFact {
  metric: string
  value: unknown
  source: string
  source_priority: number
  confidence: number
  raw_text: string
  timestamp?: string
}

export interface Citation {
  text: string
  source: string
  source_type:
    | 'udc_report'
    | 'qatar_stats'
    | 'world_bank'
    | 'semantic_scholar'
    | 'news'
    | 'other'
  page?: number
  url?: string
  confidence: number
}

export interface AgentOutput {
  agent: 'financial' | 'market' | 'operations' | 'research'
  agent_name: string
  analysis: string
  key_findings: string[]
  citations: Citation[]
  confidence: number
  reasoning: string[]
  warnings?: string[]
}

export interface DebateOutput {
  synthesis: string
  contradictions: Array<{
    topic: string
    perspectives: Array<{
      agent: string
      view: string
      confidence: number
    }>
    resolution: string
  }>
  emergent_insights: string[]
}

export interface CritiqueOutput {
  challenges: Array<{
    claim: string
    challenge: string
    severity: 'low' | 'medium' | 'high'
    resolution: string
  }>
  assumptions_audited: string[]
  alternative_hypotheses: string[]
  confidence_adjustment: number
}

export interface WorkflowState {
  stage: WorkflowStage
  query: string
  complexity: QueryComplexity
  extracted_facts: ExtractedFact[]
  extraction_confidence: number
  agent_outputs: AgentOutput[]
  agents_invoked: string[]
  debate_synthesis?: DebateOutput
  critique?: CritiqueOutput
  final_synthesis: string
  confidence_score: number
  execution_time_ms?: number
  cost_usd?: number
  llm_calls?: number
  status: 'idle' | 'running' | 'complete' | 'error'
  error?: string
}

export interface WorkflowEvent {
  stage: WorkflowStage
  status: 'ready' | 'running' | 'complete' | 'streaming' | 'error'
  payload?: Record<string, any>
  latency_ms?: number
  timestamp?: string
}

export interface StreamUpdate {
  state: WorkflowState | null
  events: WorkflowEvent[]
  isStreaming: boolean
  error?: string
}
