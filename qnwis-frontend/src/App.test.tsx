import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

vi.mock('./hooks/useWorkflowStream', () => {
  return {
    useWorkflowStream: () => ({
      state: {
        connectionStatus: 'connected',
        isStreaming: false,
        error: null,
        currentStage: 'agents',
        completedStages: new Set(['classify', 'prefetch', 'rag', 'agent_selection']),
        question: 'Test question',
        classification: null,
        prefetchFacts: [],
        ragContext: null,
        selectedAgents: ['LabourEconomist'],
        agentStatuses: new Map([
          [
            'LabourEconomist',
            {
              name: 'LabourEconomist',
              status: 'running',
              report: { narrative: 'Analyzing labour trends' },
            },
          ],
        ]),
        debateResults: null,
        critiqueResults: null,
        verification: null,
        synthesis: '',
        startTime: new Date().toISOString(),
        stageTiming: new Map(),
        reasoningChain: [],
        finalState: null,
      },
      connect: vi.fn(),
      cancel: vi.fn(),
    }),
  }
})

describe('App', () => {
  it('renders workflow dashboard shell', () => {
    render(<App />)

    expect(screen.getByText(/QNWIS Enterprise Frontend/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Ministerial Question/i)).toBeInTheDocument()
    expect(screen.getByTestId('workflow-progress')).toBeInTheDocument()
    expect(screen.getByTestId('agent-grid')).toBeInTheDocument()
  })
})
