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
    debateTurns: [],
    debateResults: null,
    critiqueResults: null,
    verification: null,
    synthesis: '',
    startTime: null,
    stageTiming: new Map(ALL_STAGES.map((stage) => [stage, 0])),
    reasoningChain: [],
    finalState: null,
    // Parallel scenario fields
    scenarios: [],
    scenarioResults: [],
    metaSynthesis: null,
    parallelExecutionActive: false,
    scenariosCompleted: 0,
    totalScenarios: 0,
    scenarioProgress: new Map(),
    // Agent execution tracking
    agentsExpected: 0,
    agentsRunning: false,
  }
}

export function resetState(existing: AppState): AppState {
  const base = createInitialState()
  base.question = existing.question
  return base
}
