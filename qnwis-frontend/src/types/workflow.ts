export type WorkflowStage =
  | 'classify'
  | 'prefetch'
  | 'rag'
  | 'scenario_gen'
  | 'parallel_exec'
  | 'meta_synthesis'
  | 'agent_selection'
  | 'agents'
  | 'debate'
  | 'critique'
  | 'verify'
  | 'synthesize'
  | 'done'

export type WorkflowStatus = 'idle' | 'connecting' | 'connected' | 'error'

export interface WorkflowEvent {
  stage: WorkflowStage | string
  status: 'ready' | 'running' | 'streaming' | 'complete' | 'error' | 'started' | 'update'
  payload?: Record<string, unknown>
  latency_ms?: number
  timestamp?: string
  message?: string
}

export interface Classification {
  intent: string
  complexity: 'simple' | 'complex' | 'critical'
  confidence: number
  entities: Record<string, unknown>
  route_to: string | null
  topics?: string[]
}

export interface ExtractedFact {
  metric: string
  value: string | number | boolean
  source: string
  confidence: number
  raw_text: string
}

export interface PrefetchResult {
  extracted_facts: ExtractedFact[]
  fact_count: number
}

export interface RAGContext {
  snippets_retrieved: number
  sources: string[]
}

export interface AgentSelectionResult {
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
    agents: Record<
      string,
      {
        description: string
        reasons: string[]
      }
    >
  }
}

export interface Insight {
  finding: string
  confidence_score: number
  warnings: string[]
}

export interface AgentReport {
  agent: string
  agent_name?: string
  narrative: string | null
  confidence?: number
  findings?: Insight[]
  insights?: Insight[]
  warnings: string[]
  derived_results?: unknown[]
  metadata: Record<string, unknown>
  citations?: Citation[]
  citations_count?: number
  data_gaps_count?: number
}

export interface Citation {
  text: string
  source: string
  query_id?: string
}

export interface AgentStatus {
  name: string
  status: 'pending' | 'running' | 'complete' | 'error'
  startTime?: number
  endTime?: number
  latency_ms?: number
  report?: AgentReport
  error?: string
}

export interface DebateResults {
  contradictions_found: number
  resolved: number
  flagged_for_review: number
  consensus_narrative: string
  latency_ms: number
  status: 'complete' | 'skipped' | 'running'
  contradictions?: Contradiction[]
  resolutions?: Resolution[]
  total_turns?: number
  conversation_history?: ConversationTurn[]
}

export interface ConversationTurn {
  agent: string
  turn: number
  type: 'opening_statement' | 'challenge' | 'response' | 'contribution' | 'final_position' | 'resolution' | 'consensus' | 'edge_case_analysis' | 'risk_identification' | 'risk_assessment' | 'consensus_synthesis'
  message: string
  timestamp: string
}

export interface Contradiction {
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

export interface Resolution {
  resolution: 'agent1_correct' | 'agent2_correct' | 'both_valid' | 'neither_valid'
  explanation: string
  recommended_value: number | null
  recommended_citation: string | null
  confidence: number
  action: 'use_agent1' | 'use_agent2' | 'use_both' | 'flag_for_review'
}

export interface CritiqueResults {
  critiques: CritiqueItem[]
  overall_assessment: string
  confidence_adjustments: Record<string, number>
  red_flags: string[]
  strengthened_by_critique: boolean
  latency_ms: number
  status: 'complete' | 'skipped'
}

export interface CritiqueItem {
  agent_name: string
  weakness_found: string
  counter_argument: string
  severity: 'high' | 'medium' | 'low'
  robustness_score: number
}

export interface VerificationResult {
  status: 'complete'
  warnings: string[]
  warning_count: number
  error_count: number
  missing_citations: number
  citation_violations: CitationViolation[]
  number_violations: NumberViolation[]
  fabricated_numbers: number
}

export interface CitationViolation {
  agent: string
  issue: string
  narrative_snippet: string
}

export interface NumberViolation {
  agent: string
  number: string
  issue: string
  context: string
}

export interface FinalWorkflowState {
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

export interface Scenario {
  name: string
  description: string
  assumptions: Record<string, any>
}

export interface ScenarioResult {
  scenario: Scenario
  synthesis: string
  confidence: number
  key_findings: string[]
}

export interface MetaSynthesis {
  robust_recommendations: string[]
  scenario_dependent_strategies: string[]
  key_uncertainties: string[]
  early_warning_indicators: string[]
  final_strategic_guidance: string
}

export interface ScenarioProgress {
  scenarioId: string
  name: string
  status: 'queued' | 'running' | 'complete' | 'error'
  progress: number // 0-100
  gpuId?: number
  results?: Record<string, unknown> // Scenario analysis results when complete
}

export interface AppState {
  connectionStatus: WorkflowStatus
  isStreaming: boolean
  error: string | null
  currentStage: WorkflowStage | null
  completedStages: Set<WorkflowStage>
  question: string
  classification: Classification | null
  prefetchFacts: ExtractedFact[]
  ragContext: RAGContext | null
  selectedAgents: string[]
  agentStatuses: Map<string, AgentStatus>
  debateTurns: any[]
  debateResults: DebateResults | null
  critiqueResults: CritiqueResults | null
  verification: VerificationResult | null
  synthesis: string
  startTime: string | null
  stageTiming: Map<WorkflowStage, number>
  reasoningChain: string[]
  finalState: FinalWorkflowState | null
  // Parallel scenario fields
  scenarios: Scenario[]
  scenarioResults: ScenarioResult[]
  metaSynthesis: MetaSynthesis | null
  parallelExecutionActive: boolean
  scenariosCompleted: number
  totalScenarios: number
  scenarioProgress: Map<string, ScenarioProgress>
  // Agent execution tracking
  agentsExpected: number
  agentsRunning: boolean
}

export const ALL_STAGES: WorkflowStage[] = [
  'classify',
  'prefetch',
  'rag',
  'scenario_gen',
  'parallel_exec',
  'agent_selection',  // Parallel scenarios select agents internally
  'agents',           // Agents run inside parallel scenarios
  'debate',           // Main debate across all scenarios
  'critique',         // Devil's advocate review
  'verify',           // Fact verification
  'meta_synthesis',   // Final cross-scenario synthesis (AFTER verify)
  'synthesize',       // Legendary briefing generation
  'done',
]

export function isValidWorkflowEvent(value: unknown): value is WorkflowEvent {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const maybeEvent = value as Partial<WorkflowEvent>
  return typeof maybeEvent.stage === 'string' && typeof maybeEvent.status === 'string'
}

export function isAgentStage(stage: string): boolean {
  return stage.startsWith('agent:')
}

export function isFinalStage(stage: string): stage is 'done' {
  return stage === 'done'
}
