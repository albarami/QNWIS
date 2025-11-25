import { useCallback, useMemo, useRef, useState } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import {
  AppState,
  WorkflowEvent,
  WorkflowStage,
  WorkflowStatus,
  ALL_STAGES,
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

function handleAgentEvent(state: AppState, event: WorkflowEvent) {
  const agentName = event.stage.replace('agent:', '')
  console.log('🤖 AGENT EVENT:', agentName, event.status, event.payload)
  
  const existing = state.agentStatuses.get(agentName) ?? {
    name: agentName,
    status: 'pending' as const,
  }

  // Track that we have agents running
  state.agentsRunning = true
  
  // If this is a new agent we haven't seen, increment expected count
  if (!state.agentStatuses.has(agentName) && state.agentsExpected === 0) {
    state.agentsExpected = state.agentStatuses.size + 1
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
    // Extract report from payload
    const payload = event.payload as any
    const report = payload?.report || payload?.analysis || payload
    
    state.agentStatuses.set(agentName, {
      ...existing,
      status: 'complete',
      endTime: Date.now(),
      latency_ms: event.latency_ms,
      report: report,
    })
    
    // Check if all agents are complete
    const allComplete = Array.from(state.agentStatuses.values()).every(
      a => a.status === 'complete' || a.status === 'error'
    )
    if (allComplete && state.agentStatuses.size > 0) {
      state.agentsRunning = false
      // Mark 'agents' stage as complete
      state.completedStages.add('agents')
    }
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
  if (event.stage.startsWith('debate:turn')) {
    console.log('🎯 DEBATE TURN RECEIVED:', event.stage, event.status, event.payload)
    next.debateTurns.push(event.payload)
    
    // Only mark debate as current stage if NOT in parallel execution mode
    // (Parallel scenarios have their own internal debates which shouldn't
    // change the main workflow stage display)
    if (!next.parallelExecutionActive) {
      next.currentStage = 'debate'
    }
    
    return next
  }

  if (event.stage === 'classify') {
    const payload = event.payload as any
    next.classification = payload
    if (event.status === 'complete') {
      next.completedStages.add('classify')
      if (event.latency_ms) {
        next.stageTiming.set('classify', event.latency_ms)
      }
    }
    // Extract reasoning from classification
    if (payload?.reasoning) {
      next.reasoningChain.push(payload.reasoning)
    }
  }

  // Generic reasoning chain handler
  if (event.payload && Array.isArray((event.payload as any).reasoning_chain)) {
    next.reasoningChain = (event.payload as any).reasoning_chain
  }

  if (event.stage === 'prefetch') {
    const payload = event.payload as any
    next.prefetchFacts = payload?.extracted_facts ?? []
    if (event.status === 'complete') {
      next.completedStages.add('prefetch')
      if (event.latency_ms) {
        next.stageTiming.set('prefetch', event.latency_ms)
      }
    }
  }

  if (event.stage === 'rag') {
    const payload = event.payload as any
    next.ragContext = payload
    if (event.status === 'complete') {
      next.completedStages.add('rag')
      if (event.latency_ms) {
        next.stageTiming.set('rag', event.latency_ms)
      }
    }
  }

  if (event.stage === 'agent_selection' && event.payload) {
    const payload = event.payload as any
    console.log('🤖 AGENT_SELECTION event received:', payload)
    
    next.selectedAgents = payload.selected_agents ?? payload.agents ?? []
    next.agentsExpected = next.selectedAgents.length
    next.agentsRunning = true
    
    console.log('🤖 Selected agents:', next.selectedAgents, 'Expected:', next.agentsExpected)
    
    // Initialize agent statuses for all selected agents as pending
    next.agentStatuses = new Map(
      next.selectedAgents.map((name: string) => [name, { name, status: 'pending' as const }])
    )
    
    // Mark agent_selection as complete
    next.completedStages.add('agent_selection')
    if (event.latency_ms) {
      next.stageTiming.set('agent_selection', event.latency_ms)
    }
  }

  // Track agents stage to know when agents are being processed
  if (event.stage === 'agents') {
    if (event.status === 'running') {
      next.agentsRunning = true
    } else if (event.status === 'complete') {
      next.agentsRunning = false
      next.completedStages.add('agents')
      if (event.latency_ms) {
        next.stageTiming.set('agents', event.latency_ms)
      }
    }
  }

  if (event.stage === 'debate') {
    if (event.status === 'running') {
      next.currentStage = 'debate'
    } else if (event.status === 'complete') {
      const payload = event.payload as any
      next.debateResults = payload
      next.completedStages.add('debate')
      if (event.latency_ms) {
        next.stageTiming.set('debate', event.latency_ms)
      }
      // Extract conversation history if available
      if (payload?.conversation_history && Array.isArray(payload.conversation_history)) {
        // Add any remaining turns from the conversation history
        payload.conversation_history.forEach((turn: any) => {
          const exists = next.debateTurns.some(
            (t: any) => t.turn === turn.turn && t.agent === turn.agent
          )
          if (!exists) {
            next.debateTurns.push(turn)
          }
        })
      }
    }
  }

  if (event.stage === 'critique') {
    if (event.status === 'running') {
      next.currentStage = 'critique'
    } else if (event.status === 'complete') {
      const payload = event.payload as any
      next.critiqueResults = payload?.critique || payload?.critique_report || payload
      next.completedStages.add('critique')
      if (event.latency_ms) {
        next.stageTiming.set('critique', event.latency_ms)
      }
    }
  }

  // Handle parallel scenario events
  if (event.stage === 'scenario_gen') {
    const payload = event.payload as any
    next.scenarios = payload?.scenarios ?? []
    if (next.scenarios.length > 0) {
      next.parallelExecutionActive = true
      next.totalScenarios = next.scenarios.length
      next.scenariosCompleted = 0
      
      // Initialize scenario progress for each scenario
      next.scenarios.forEach((scenario: any, idx: number) => {
        const scenarioId = scenario.id || `scenario-${idx}`
        next.scenarioProgress.set(scenarioId, {
          scenarioId,
          name: scenario.name || `Scenario ${idx + 1}`,
          status: 'queued',
          progress: 0,
        })
      })
    }
    // Mark scenario_gen as complete
    if (event.status === 'complete') {
      next.completedStages.add('scenario_gen')
      if (event.latency_ms) {
        next.stageTiming.set('scenario_gen', event.latency_ms)
      }
    }
  }

  // Handle individual scenario progress events (scenario:{id})
  if (event.stage.startsWith('scenario:')) {
    const payload = event.payload as any
    const scenarioId = payload?.scenario_id || event.stage.replace('scenario:', '')
    
    if (event.status === 'started') {
      const existing = next.scenarioProgress.get(scenarioId) || {
        scenarioId,
        name: payload?.scenario_name || scenarioId,
        status: 'queued' as const,
        progress: 0,
      }
      next.scenarioProgress.set(scenarioId, {
        ...existing,
        status: 'running',
        progress: 33,
        gpuId: payload?.gpu_id,
      })
    } else if (event.status === 'complete') {
      const existing = next.scenarioProgress.get(scenarioId)
      if (existing) {
        next.scenarioProgress.set(scenarioId, {
          ...existing,
          status: 'complete',
          progress: 100,
        })
        // Update scenariosCompleted count
        const completedCount = Array.from(next.scenarioProgress.values()).filter(
          sp => sp.status === 'complete'
        ).length
        next.scenariosCompleted = completedCount
      }
    }
    return next
  }

  // Handle parallel_progress updates
  if (event.stage === 'parallel_progress') {
    const payload = event.payload as any
    
    // Update completed count
    if (payload?.completed !== undefined) {
      next.scenariosCompleted = payload.completed
    }
    if (payload?.total !== undefined) {
      next.totalScenarios = payload.total
    }
    
    // Calculate progress based on completed scenarios
    if (next.totalScenarios > 0) {
      const progressPercent = (next.scenariosCompleted / next.totalScenarios) * 100
      
      // Update all scenarios with estimated progress
      let completedSoFar = 0
      next.scenarioProgress.forEach((sp, id) => {
        if (completedSoFar < next.scenariosCompleted) {
          // This scenario is complete
          next.scenarioProgress.set(id, { ...sp, status: 'complete', progress: 100 })
          completedSoFar++
        } else if (sp.status !== 'complete') {
          // Running scenario - estimate progress based on overall
          const runningProgress = Math.min(80, 20 + progressPercent * 0.6)
          next.scenarioProgress.set(id, { ...sp, status: 'running', progress: runningProgress })
        }
      })
    }
    
    return next
  }

  if (event.stage === 'parallel_exec') {
    const payload = event.payload as any
    
    // Handle both 'running' and 'started' status (backend uses 'started')
    if (event.status === 'running' || event.status === 'started') {
      next.parallelExecutionActive = true
      // Initialize scenarios from payload if available
      if (payload?.scenarios && Array.isArray(payload.scenarios)) {
        next.totalScenarios = payload.scenarios.length
        payload.scenarios.forEach((scenario: any, idx: number) => {
          // Use consistent ID format: scenario-{idx} (with dash)
          const scenarioId = scenario.id || `scenario-${idx}`
          next.scenarioProgress.set(scenarioId, {
            scenarioId,
            name: scenario.name || `Scenario ${idx + 1}`,
            status: 'running',
            progress: 10, // Starting
          })
        })
      } else {
        // Mark existing scenarios as running with incremental progress
        let idx = 0
        next.scenarioProgress.forEach((sp, id) => {
          next.scenarioProgress.set(id, { ...sp, status: 'running', progress: 20 + (idx * 5) })
          idx++
        })
      }
    } else if (event.status === 'complete') {
      // Backend sends complete with scenario_results
      next.scenarioResults = payload?.scenario_results ?? []
      next.parallelExecutionActive = false
      next.scenariosCompleted = next.totalScenarios > 0 ? next.totalScenarios : next.scenarioResults.length
      
      // Update totalScenarios if we have results but no total yet
      if (next.totalScenarios === 0 && next.scenarioResults.length > 0) {
        next.totalScenarios = next.scenarioResults.length
      }
      
      // Mark all scenarios as complete
      next.scenarioProgress.forEach((sp, id) => {
        next.scenarioProgress.set(id, { ...sp, status: 'complete', progress: 100 })
      })
      
      // Mark parallel_exec as complete
      next.completedStages.add('parallel_exec')
      if (event.latency_ms) {
        next.stageTiming.set('parallel_exec', event.latency_ms)
      }
    }
  }

  if (event.stage === 'meta_synthesis') {
    const payload = event.payload as any
    next.metaSynthesis = payload?.meta_synthesis ?? null
    // Meta-synthesis often includes final synthesis
    if (payload?.final_synthesis) {
      next.synthesis = payload.final_synthesis
    }
    if (event.status === 'complete') {
      next.completedStages.add('meta_synthesis')
      if (event.latency_ms) {
        next.stageTiming.set('meta_synthesis', event.latency_ms)
      }
    }
  }

  if (event.stage === 'verify') {
    const payload = event.payload as any
    next.verification = payload?.verification || payload?.fact_check_results || payload
    if (event.status === 'complete') {
      next.completedStages.add('verify')
      if (event.latency_ms) {
        next.stageTiming.set('verify', event.latency_ms)
      }
    }
  }

  if (event.stage === 'synthesize') {
    const payload = event.payload as any
    if (event.status === 'streaming') {
      const token = payload?.token || ''
      next.synthesis = `${next.synthesis}${token}`
    } else if (event.status === 'complete') {
      next.synthesis = payload?.text ?? payload?.final_synthesis ?? next.synthesis
      next.completedStages.add('synthesize')
      if (event.latency_ms) {
        next.stageTiming.set('synthesize', event.latency_ms)
      }
    }
  }

  if (event.stage === 'done') {
    const payload = event.payload as any
    next.finalState = payload
    next.isStreaming = false
    
    // Ensure we have synthesis even in done event
    if (payload?.final_synthesis && !next.synthesis) {
      next.synthesis = payload.final_synthesis
    }
    if (payload?.meta_synthesis && !next.metaSynthesis) {
      next.metaSynthesis = payload.meta_synthesis
    }
    
    // Mark done stage as complete
    next.completedStages.add('done')
    if (event.latency_ms) {
      next.stageTiming.set('done', event.latency_ms)
    }
  }

  // Update current stage for any valid workflow stage
  if ('stage' in event && 'status' in event) {
    const stageStr = event.stage as string
    
    // Only update currentStage for main workflow stages (not agent: or debate:turn)
    if (ALL_STAGES.includes(stageStr as WorkflowStage)) {
      next.currentStage = stageStr as WorkflowStage
    }
    
    if (stageStr === 'error') {
      const errorPayload = event.payload as any
      const errorMessage = errorPayload?.error || errorPayload?.message || 'Workflow execution failed'
      next.error = errorMessage
      next.connectionStatus = 'error'
      next.isStreaming = false
    }

    // For generic stage completion, ensure we mark it complete
    if (event.status === 'complete' && ALL_STAGES.includes(stageStr as WorkflowStage)) {
      next.completedStages.add(stageStr as WorkflowStage)
      if (event.latency_ms) {
        next.stageTiming.set(stageStr as WorkflowStage, event.latency_ms)
      }
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
