import { useCallback, useMemo, useRef, useState } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import {
  AppState,
  WorkflowEvent,
  WorkflowStage,
  WorkflowStatus,
  isAgentStage,
} from '../types/workflow'
import { createInitialState, resetState } from '../state/initialState'
import { safeParseWorkflowEvent } from '../utils/eventParser'

interface ConnectParams {
  question: string
  provider?: 'anthropic' | 'openai'
}

interface UseWorkflowStreamResult {
  state: AppState
  connect: (params: ConnectParams) => Promise<void>
  cancel: () => void
}

const API_BASE_URL = (import.meta.env.VITE_QNWIS_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
const SSE_ENDPOINT = `${API_BASE_URL}/api/v1/council/stream`

function updateStageTiming(state: AppState, stage: WorkflowStage, latency?: number) {
  if (typeof latency === 'number') {
    state.stageTiming.set(stage, latency)
  }
  state.completedStages.add(stage)
}

function handleAgentEvent(state: AppState, event: WorkflowEvent) {
  const agentName = event.stage.replace('agent:', '')
  const existing = state.agentStatuses.get(agentName) ?? {
    name: agentName,
    status: 'pending' as const,
  }

  if (event.status === 'running') {
    state.agentStatuses.set(agentName, {
      ...existing,
      status: 'running',
      startTime: Date.now(),
    })
    return state
  }

  if (event.status === 'complete') {
    state.agentStatuses.set(agentName, {
      ...existing,
      status: 'complete',
      endTime: Date.now(),
      latency_ms: event.latency_ms,
      report: event.payload as any,
    })
  }

  if (event.status === 'error') {
    const errorMsg = (event.payload as any)?.error || event.message || 'Agent execution failed'
    state.agentStatuses.set(agentName, {
      ...existing,
      status: 'error',
      error: errorMsg,
    })
  }

  return state
}

function reduceEvent(state: AppState, event: WorkflowEvent): AppState {
  const next: AppState = {
    ...state,
    completedStages: new Set(state.completedStages),
    stageTiming: new Map(state.stageTiming),
    agentStatuses: new Map(state.agentStatuses),
    debateTurns: [...state.debateTurns],
    scenarioProgress: new Map(state.scenarioProgress),
  }

  if (isAgentStage(event.stage)) {
    return handleAgentEvent(next, event)
  }

  // Handle debate turn events (streaming conversation)
  if (event.stage.startsWith('debate:turn') && event.status === 'streaming') {
    console.log('🎯 DEBATE TURN RECEIVED:', event.stage, event.payload)
    next.debateTurns.push(event.payload)
    
    // Extract agent name and track it
    const payload = event.payload as any
    const agentName = payload.speaker || payload.agent || 'Unknown'
    if (agentName && !next.agentStatuses.has(agentName)) {
      next.agentStatuses.set(agentName, {
        name: agentName,
        status: 'running'
      })
    }
    
    return next
  }

  if (event.stage === 'classify' && event.payload) {
    next.classification = event.payload as any
  }

  // Generic reasoning chain handler
  if (event.payload && Array.isArray((event.payload as any).reasoning_chain)) {
    next.reasoningChain = (event.payload as any).reasoning_chain
  }

  if (event.stage === 'prefetch' && event.payload) {
    next.prefetchFacts = (event.payload as any).extracted_facts ?? []
  }

  if (event.stage === 'rag' && event.payload) {
    next.ragContext = event.payload as any
  }

  if (event.stage === 'agent_selection' && event.payload) {
    next.selectedAgents = (event.payload as any).selected_agents ?? []
    next.agentsExpected = next.selectedAgents.length
    next.agentsRunning = true
    next.agentStatuses = new Map(
      next.selectedAgents.map((name) => [name, { name, status: 'pending' as const }])
    )
  }

  // Track agents stage to know when agents are being processed
  if (event.stage === 'agents') {
    if (event.status === 'running') {
      next.agentsRunning = true
    } else if (event.status === 'complete') {
      next.agentsRunning = false
    }
  }

  if (event.stage === 'debate' && event.status === 'complete') {
    next.debateResults = event.payload as any
  }

  if (event.stage === 'critique' && event.status === 'complete') {
    next.critiqueResults = event.payload as any
  }

  // Handle parallel scenario events
  if (event.stage === 'scenario_gen' && event.payload) {
    next.scenarios = (event.payload as any).scenarios ?? []
    if (next.scenarios.length > 0) {
      next.parallelExecutionActive = true
      next.totalScenarios = next.scenarios.length
      // Set selected agents to estimated total (6 scenarios × 5 agents = 30)
      next.selectedAgents = ['MicroEconomist', 'MacroEconomist', 'Nationalization', 'SkillsAgent', 'PatternDetective']
    }
  }

  if (event.stage === 'parallel_exec') {
    if (event.status === 'started' && event.payload) {
      // Set total scenarios when parallel execution starts
      const payload = event.payload as any
      next.totalScenarios = payload.total_scenarios ?? next.scenarios.length
      next.scenariosCompleted = 0
      next.parallelExecutionActive = true
    } else if (event.status === 'running' && event.payload) {
      // Track progress during execution
      const payload = event.payload as any
      if (payload.completed !== undefined) {
        next.scenariosCompleted = payload.completed
      }
      if (payload.total !== undefined) {
        next.totalScenarios = payload.total
      }
      // Also track scenario-level progress if provided
      if (payload.scenario_progress) {
        next.scenarioProgress = payload.scenario_progress
      }
    } else if (event.status === 'complete' && event.payload) {
      next.scenarioResults = (event.payload as any).scenario_results ?? []
      next.parallelExecutionActive = false
      next.scenariosCompleted = next.totalScenarios
    }
  }

  if (event.stage === 'parallel_progress' && event.payload) {
    // Track overall progress - THIS IS KEY!
    const payload = event.payload as any
    next.scenariosCompleted = payload.completed ?? next.scenariosCompleted
    next.totalScenarios = payload.total ?? next.totalScenarios
  }

  if (event.stage.startsWith('scenario:') && event.payload) {
    // Individual scenario events
    const scenarioId = event.stage.split(':')[1]
    const payload = event.payload as any
    
    if (event.status === 'started' || event.status === 'running') {
      // Track scenario starting/running
      const scenarioName = payload.scenario_name || payload.name || `Scenario ${scenarioId}`
      next.scenarioProgress.set(scenarioId, {
        scenarioId,
        name: scenarioName,
        status: 'running',
        progress: payload.progress ?? 10, // Default to 10% when started
        gpuId: payload.gpu_id,
      })
      if (event.status === 'started') {
        next.reasoningChain.push(`Starting ${scenarioName} on GPU ${payload.gpu_id}`)
      }
    } else if (event.status === 'complete') {
      // Track scenario completion
      const scenarioName = payload.scenario_name || payload.name || `Scenario ${scenarioId}`
      next.scenarioProgress.set(scenarioId, {
        scenarioId,
        name: scenarioName,
        status: 'complete',
        progress: 100,
        gpuId: payload.gpu_id,
      })
      next.reasoningChain.push(`Completed ${scenarioName} (${payload.duration_seconds}s)`)
      // Increment completed count immediately
      next.scenariosCompleted = next.scenariosCompleted + 1
    } else if (event.status === 'error') {
      const scenarioName = payload.scenario_name || payload.name || `Scenario ${scenarioId}`
      next.scenarioProgress.set(scenarioId, {
        scenarioId,
        name: scenarioName,
        status: 'error',
        progress: 0,
        gpuId: payload.gpu_id,
      })
    }
  }

  if (event.stage === 'meta_synthesis' && event.payload) {
    next.metaSynthesis = (event.payload as any).meta_synthesis ?? null
    // Meta-synthesis often includes final synthesis
    if ((event.payload as any).final_synthesis) {
      next.synthesis = (event.payload as any).final_synthesis
    }
  }

  if (event.stage === 'verify' && event.payload) {
    next.verification = event.payload as any
  }

  if (event.stage === 'synthesize' && event.payload) {
    if (event.status === 'streaming') {
      const token = (event.payload as any).token || ''
      next.synthesis = `${next.synthesis}${token}`
    } else {
      next.synthesis = (event.payload as any).text ?? (event.payload as any).final_synthesis ?? next.synthesis
    }
  }

  if (event.stage === 'done' && event.payload) {
    next.finalState = event.payload as any
    // Ensure we have synthesis even in done event
    if ((event.payload as any).final_synthesis && !next.synthesis) {
      next.synthesis = (event.payload as any).final_synthesis
    }
    if ((event.payload as any).meta_synthesis && !next.metaSynthesis) {
      next.metaSynthesis = (event.payload as any).meta_synthesis
    }
  }

  if ('stage' in event && 'status' in event) {
    next.currentStage = event.stage as WorkflowStage
    
    if (event.stage === 'error') {
      const errorPayload = event.payload as any
      const errorMessage = errorPayload?.error || errorPayload?.message || 'Workflow execution failed'
      next.error = errorMessage
      next.connectionStatus = 'error'
      next.isStreaming = false
    }

    if (event.status === 'complete' && next.currentStage && event.stage !== 'error') {
      updateStageTiming(next, next.currentStage, event.latency_ms)
    }
  }

  return next
}

export function useWorkflowStream(): UseWorkflowStreamResult {
  const [state, setState] = useState<AppState>(() => createInitialState())
  const controllerRef = useRef<AbortController | null>(null)

  const cancel = useCallback(() => {
    controllerRef.current?.abort()
    controllerRef.current = null
    setState((prev) => ({ ...prev, connectionStatus: 'idle', isStreaming: false }))
  }, [])

  const connect = useCallback(async ({ question, provider = 'anthropic' }: ConnectParams) => {
    if (!question.trim()) {
      throw new Error('Question is required')
    }

    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    setState((prev) => ({
      ...resetState(prev),
      question,
      connectionStatus: 'connecting',
      isStreaming: true,
      error: null,
      startTime: new Date().toISOString(),
    }))

    await fetchEventSource(SSE_ENDPOINT, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question, provider }),
      async onopen(response) {
        if (!response.ok) {
          let errorMsg = `Connection failed: ${response.status} ${response.statusText}`
          try {
            const errorBody = await response.json()
            if (errorBody.detail?.debug_error) {
              errorMsg = `${errorMsg} - ${errorBody.detail.debug_error}`
            } else if (errorBody.detail?.message) {
              errorMsg = `${errorMsg} - ${errorBody.detail.message}`
            }
          } catch {
            // Could not parse error body, use status text
          }
          throw new Error(errorMsg)
        }
        setState((prev) => ({ ...prev, connectionStatus: 'connected' as WorkflowStatus }))
      },
      onmessage(event) {
        setState((prev) => {
          const parsed = safeParseWorkflowEvent(event.data)
          if (!parsed) {
            // Skip malformed events silently - workflow continues
            return prev
          }
          return reduceEvent(prev, parsed)
        })
      },
      onclose() {
        setState((prev) => ({
          ...prev,
          connectionStatus: 'idle',
          isStreaming: false,
        }))
      },
      onerror(err) {
        setState((prev) => ({
          ...prev,
          connectionStatus: 'error',
          error: err instanceof Error ? err.message : String(err),
          isStreaming: false,
        }))
        throw err
      },
      openWhenHidden: true,
    })
  }, [])

  return useMemo(() => ({ state, connect, cancel }), [state, connect, cancel])
}
