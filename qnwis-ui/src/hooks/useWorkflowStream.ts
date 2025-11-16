import { useState, useEffect, useCallback } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { WorkflowState, WorkflowEvent } from '@/types/workflow'

interface UseWorkflowStreamOptions {
  onComplete?: (state: WorkflowState) => void
  onError?: (error: string) => void
}

export const useWorkflowStream = (options: UseWorkflowStreamOptions = {}) => {
  const [state, setState] = useState<WorkflowState | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [controller, setController] = useState<AbortController | null>(null)

  const startStream = useCallback(
    async (question: string) => {
      setState(null)
      setError(null)
      setIsStreaming(true)

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
            if (!response.ok) {
              throw new Error(`Failed to connect: ${response.status}`)
            }
            console.info('Stream connection established')
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
                      Object.assign(next, streamEvent.payload)
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
            setError('Connection error occurred')
            setIsStreaming(false)
            if (options.onError) {
              options.onError('Connection error occurred')
            }
            throw err
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
    startStream,
    stopStream,
  }
}
