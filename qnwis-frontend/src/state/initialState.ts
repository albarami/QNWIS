import { AppState, ALL_STAGES, WorkflowStage } from '../types/workflow'

export function createInitialState(): AppState {
  return {
    connectionStatus: 'idle',
    isStreaming: false,
    error: null,
    currentStage: null,
    completedStages: new Set<WorkflowStage>(),
    question: '',
    classification: null,
    prefetchFacts: [],
    ragContext: null,
    selectedAgents: [],
    agentStatuses: new Map(),
    debateResults: null,
    critiqueResults: null,
    verification: null,
    synthesis: '',
    startTime: null,
    stageTiming: new Map(ALL_STAGES.map((stage) => [stage, 0])),
    reasoningChain: [],
    finalState: null,
  }
}

export function resetState(existing: AppState): AppState {
  const base = createInitialState()
  base.question = existing.question
  return base
}
