import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { WorkflowState, WorkflowEvent } from '@/types/workflow'

interface RetryConfig {
  maxRetries: number
  initialDelay: number
  maxDelay: number
  backoffMultiplier: number
}

interface UseWorkflowStreamOptions {
  onComplete?: (state: WorkflowState) => void
  onError?: (error: string) => void
  retryConfig?: RetryConfig
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
}

export const useWorkflowStream = (options: UseWorkflowStreamOptions = {}) => {
  const [state, setState] = useState<WorkflowState | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [controller, setController] = useState<AbortController | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'connected' | 'error'>('idle')
  
  const retryConfig = options.retryConfig || DEFAULT_RETRY_CONFIG
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const calculateBackoff = useCallback((attemptNumber: number): number => {
    const delay = Math.min(
      retryConfig.initialDelay * Math.pow(retryConfig.backoffMultiplier, attemptNumber),
      retryConfig.maxDelay
    )
    // Add jitter: ±20%
    const jitter = delay * 0.2 * (Math.random() * 2 - 1)
    return Math.floor(delay + jitter)
  }, [retryConfig])

  const startStream = useCallback(
    async (question: string) => {
      setState(null)
      setError(null)
      setIsStreaming(true)
      setRetryCount(0)
      setConnectionStatus('connecting')

      const abortController = new AbortController()
      setController(abortController)

      try {
        await fetchEventSource('/api/v1/council/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ question, provider: 'anthropic' }),
          signal: abortController.signal,

          async onopen(response) {
            if (response.ok) {
              setConnectionStatus('connected')
              setRetryCount(0)  // Reset on successful connection
              console.info('Stream connection established')
            } else if (response.status >= 400 && response.status < 500) {
              // Client error - don't retry
              setConnectionStatus('error')
              throw new Error(`Client error: ${response.status}`)
            } else {
              // Server error - will retry
              setConnectionStatus('error')
              throw new Error(`Server error: ${response.status}`)
            }
          },

          onmessage(event) {
            if (!event.data) return

            try {
              const streamEvent: WorkflowEvent = JSON.parse(event.data)

              setState((prev) => {
                const next: WorkflowState = {
                  ...(prev ?? {
                    stage: 'classify',
                    query: question,
                    complexity: 'simple',
                    extracted_facts: [],
                    extraction_confidence: 0,
                    agent_outputs: [],
                    agents_invoked: [],
                    final_synthesis: '',
                    confidence_score: 0,
                    status: 'running',
                  }),
                  stage: streamEvent.stage as WorkflowState['stage'],
                  // CRITICAL FIX: Only set status to 'complete' if it's the FINAL 'done' event
                  // Individual stages completing should keep status as 'running'
                  status:
                    streamEvent.stage === 'done' && streamEvent.status === 'complete'
                      ? 'complete'
                      : streamEvent.status === 'error'
                        ? 'error'
                        : 'running',
                }

                if (streamEvent.payload) {
                  if (
                    streamEvent.stage === 'synthesize' &&
                    streamEvent.status === 'streaming' &&
                    typeof streamEvent.payload.token === 'string'
                  ) {
                    next.final_synthesis = `${prev?.final_synthesis ?? ''}${streamEvent.payload.token}`
                  } else {
                    // Handle classify stage: extract complexity from classification object
                    if (streamEvent.stage === 'classify' && streamEvent.payload.classification) {
                      const classification = streamEvent.payload.classification as any
                      next.complexity = classification.complexity || 'simple'
                      Object.assign(next, streamEvent.payload)
                    } else {
                      // CRITICAL FIX: Backend sends 'agent_reports', frontend expects 'agent_outputs'
                      const payload = { ...streamEvent.payload }
                      if (payload.agent_reports && !payload.agent_outputs) {
                        payload.agent_outputs = payload.agent_reports
                        
                        // ALSO extract individual agent analyses for AgentOutputs component
                        payload.agent_reports.forEach((report: any) => {
                          const agentKey = report.agent_name?.toLowerCase().replace(/ /g, '_')
                          if (agentKey) {
                            payload[`${agentKey}_analysis`] = report.narrative || report.analysis || ''
                          }
                        })
                      }
                      Object.assign(next, payload)
                    }
                  }
                }

                return next
              })

              if (streamEvent.status === 'complete') {
                setIsStreaming(false)
                if (options.onComplete && streamEvent.payload) {
                  options.onComplete(streamEvent.payload as WorkflowState)
                }
              }

              if (streamEvent.status === 'error') {
                const message =
                  (streamEvent.payload?.error as string) ??
                  streamEvent.payload?.message ??
                  'Unknown error'
                setError(message)
                setIsStreaming(false)
                if (options.onError) {
                  options.onError(message)
                }
              }
            } catch (err) {
              console.error('Failed to parse event:', err)
            }
          },

          onerror(err) {
            console.error('SSE Error:', err)
            setConnectionStatus('error')
            
            // Check if we should retry
            setRetryCount((currentCount) => {
              if (currentCount < retryConfig.maxRetries) {
                const delay = calculateBackoff(currentCount)
                console.log(
                  `Connection failed. Retrying in ${delay}ms (attempt ${currentCount + 1}/${retryConfig.maxRetries})`
                )
                
                // Clear any existing retry timeout
                if (retryTimeoutRef.current) {
                  clearTimeout(retryTimeoutRef.current)
                }
                
                // Return the delay to trigger reconnection
                // Note: fetchEventSource uses the return value as retry delay
                return currentCount + 1
              } else {
                // Max retries exceeded
                console.error('Max retries exceeded')
                setError('Connection failed after multiple attempts')
                setIsStreaming(false)
                if (options.onError) {
                  options.onError('Connection failed after multiple attempts')
                }
                throw new Error('Max retries exceeded')
              }
            })
            
            // Return the delay to trigger reconnection in fetchEventSource
            return calculateBackoff(retryCount)
          },

          onclose() {
            console.info('Stream connection closed')
            setIsStreaming(false)
          },
        })
      } catch (err) {
        console.error('Stream error:', err)
        setError(err instanceof Error ? err.message : 'Unknown error')
        setIsStreaming(false)
      }
    },
    [options],
  )

  const stopStream = useCallback(() => {
    if (controller) {
      controller.abort()
      setController(null)
      setIsStreaming(false)
    }
  }, [controller])

  useEffect(() => {
    return () => {
      if (controller) {
        controller.abort()
      }
    }
  }, [controller])

  return {
    state,
    isStreaming,
    error,
    connectionStatus,
    retryCount,
    startStream,
    stopStream,
  }
}
