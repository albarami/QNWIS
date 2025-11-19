import { useMemo, useState } from 'react'
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
import { VerificationPanel } from './components/results/VerificationPanel'
import { ReasoningLog } from './components/workflow/ReasoningLog'
import { ErrorBanner } from './components/common/ErrorBanner'

function App() {
  const { state, connect, cancel } = useWorkflowStream()
  const [question, setQuestion] = useState('What are the implications of raising minimum wage?')
  const [provider, setProvider] = useState<'stub' | 'anthropic' | 'openai'>('stub')
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
    await connect({ question, provider })
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
              {['stub', 'anthropic', 'openai'].map((option) => (
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

        <AgentGrid agents={state.agentStatuses} />

        <DebatePanel debate={state.debateResults} />

        <CritiquePanel critique={state.critiqueResults} />

        <ExecutiveSummary synthesis={state.synthesis} />

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

export default App
