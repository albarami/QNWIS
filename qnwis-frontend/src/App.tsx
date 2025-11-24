import React, { useState, useMemo, Component, ErrorInfo, ReactNode } from 'react'
import { useWorkflowStream } from './hooks/useWorkflowStream'
import { StageProgress } from './components/workflow/StageProgress'
import { CurrentStageCard } from './components/workflow/CurrentStageCard'
import { StageTimeline } from './components/workflow/StageTimeline'
import { AgentGrid } from './components/agents/AgentGrid'
import { DebatePanel } from './components/debate/DebatePanel'
import { CritiquePanel } from './components/critique/CritiquePanel'
import { ExecutiveSummary } from './components/results/ExecutiveSummary'
import { ExtractedFacts } from './components/results/ExtractedFacts'
import { RAGContextPanel } from './components/results/RAGContextPanel'
import { ParallelScenarios } from './components/results/ParallelScenarios'
import { ParallelExecutionProgress } from './components/workflow/ParallelExecutionProgress'
import { VerificationPanel } from './components/results/VerificationPanel'
import { ReasoningLog } from './components/workflow/ReasoningLog'
import { ErrorBanner } from './components/common/ErrorBanner'

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('React Error Boundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
          <div className="bg-red-900/20 border border-red-500 rounded-xl p-8 max-w-2xl">
            <h1 className="text-2xl font-bold text-red-400 mb-4">Application Error</h1>
            <p className="text-slate-300 mb-4">The application encountered an error:</p>
            <pre className="bg-slate-950 p-4 rounded text-red-300 text-sm overflow-auto">
              {this.state.error?.message || 'Unknown error'}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="mt-6 px-6 py-2 bg-cyan-500 text-slate-900 rounded-lg font-semibold hover:bg-cyan-400"
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

function App() {
  const { state, connect, cancel } = useWorkflowStream()
  const [question, setQuestion] = useState('What are the implications of raising minimum wage?')
  const [provider, setProvider] = useState<'anthropic' | 'openai'>('anthropic')
  
  // Safety check: ensure state exists
  if (!state) {
    return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white">Loading...</div>
  }
  
  const currentStageStatus = useMemo(() => {
    if (!state.currentStage) {
      return state.connectionStatus
    }
    if (state.completedStages.has(state.currentStage)) {
      return 'complete'
    }
    return state.isStreaming ? 'running' : 'pending'
  }, [state.connectionStatus, state.currentStage, state.completedStages, state.isStreaming])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await connect({ question, provider })
    } catch (error) {
      console.error('Submit error:', error)
      // Error is already handled by useWorkflowStream
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-slate-100">
      <div className="max-w-6xl mx-auto py-12 px-6 space-y-8">
        <header className="text-center space-y-2">
          <p className="text-sm uppercase tracking-[0.3em] text-slate-400">Qatar Ministry of Labour</p>
          <h1 className="text-4xl font-bold">QNWIS Enterprise Frontend</h1>
          <p className="text-slate-300">Phase 2 · Live workflow instrumentation</p>
        </header>

        {state.error && <ErrorBanner message={state.error} onRetry={() => connect({ question, provider })} />}

        <form
          onSubmit={handleSubmit}
          className="bg-slate-800/60 border border-slate-700 rounded-2xl p-6 space-y-4"
        >
          <div className="space-y-2">
            <label htmlFor="question" className="text-sm font-semibold text-slate-300">
              Ministerial Question
            </label>
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={4}
              className="w-full rounded-xl border border-slate-600 bg-slate-900/50 p-4 text-slate-100 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <label className="text-sm font-semibold text-slate-300">LLM Provider</label>
            <div className="flex gap-2">
              {['anthropic', 'openai'].map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setProvider(option as typeof provider)}
                  className={`rounded-full px-4 py-1.5 text-sm font-semibold transition border ${{
                    true: 'bg-cyan-500 text-slate-900 border-cyan-400',
                    false: 'border-slate-600 text-slate-200 hover:border-cyan-300',
                  }[String(provider === option) as 'true' | 'false']}`}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              className="flex-1 rounded-xl bg-cyan-500 px-6 py-3 text-slate-900 font-semibold hover:bg-cyan-400 transition disabled:opacity-40"
              disabled={state.isStreaming}
            >
              {state.isStreaming ? 'Streaming…' : 'Submit to Intelligence Council'}
            </button>
            <button
              type="button"
              onClick={cancel}
              className="rounded-xl border border-slate-600 px-4 py-3 text-sm font-semibold hover:border-cyan-300"
            >
              Cancel
            </button>
          </div>
        </form>

        <section className="space-y-6">
          <StageProgress currentStage={state.currentStage} completedStages={state.completedStages} />
          <CurrentStageCard stage={state.currentStage} status={currentStageStatus} startedAt={state.startTime} />
          <StageTimeline
            stageTiming={state.stageTiming}
            completedStages={state.completedStages}
            currentStage={state.currentStage}
          />
          
          <ReasoningLog chain={state.reasoningChain || []} />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <TelemetryCard label="Connection" value={state.connectionStatus} />
            <TelemetryCard label="Agents Selected" value={state.selectedAgents.length} />
            <TelemetryCard label="Errors" value={state.error ?? 'none'} isAlert={!!state.error} />
          </div>
        </section>

        <ParallelExecutionProgress
          scenarios={state.scenarios || []}
          scenariosCompleted={state.scenariosCompleted || 0}
          totalScenarios={state.totalScenarios || 0}
          isActive={state.parallelExecutionActive || false}
        />

        <AgentGrid agents={state.agentStatuses} />

        <DebatePanel debate={state.debateResults} debateTurns={state.debateTurns} />

        <CritiquePanel critique={state.critiqueResults} />

        <ParallelScenarios 
          scenarios={state.scenarios || []}
          scenarioResults={state.scenarioResults || []}
          metaSynthesis={state.metaSynthesis}
        />

        <ExecutiveSummary synthesis={state.synthesis} />

        <RAGContextPanel context={state.ragContext} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ExtractedFacts facts={state.prefetchFacts} />
          <VerificationPanel verification={state.verification} />
        </div>
      </div>
    </div>
  )
}

function TelemetryCard({ label, value, isAlert = false }: { label: string; value: string | number; isAlert?: boolean }) {
  return (
    <div className={`rounded-2xl border p-4 bg-slate-900/40 ${isAlert ? 'border-red-500/60 text-red-300' : 'border-slate-700'}`}>
      <p className="text-xs uppercase tracking-[0.3em] text-slate-500">{label}</p>
      <p className="text-lg font-semibold mt-1">{value}</p>
    </div>
  )
}

function AppWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  )
}

export default AppWithErrorBoundary
