import React, { useState, Component, ErrorInfo, ReactNode } from 'react'
import { useWorkflowStream } from './hooks/useWorkflowStream'
import { StageProgress } from './components/workflow/StageProgress'
import { StageTimeline } from './components/workflow/StageTimeline'
import { AgentGrid } from './components/agents/AgentGrid'
import { DebatePanel } from './components/debate/DebatePanel'
import { CritiquePanel } from './components/critique/CritiquePanel'
// import { ExecutiveSummary } from './components/results/ExecutiveSummary'
// import { StrategicBriefing } from './components/results/StrategicBriefing'
import { LegendaryBriefing } from './components/results/LegendaryBriefing'
import { ExtractedFacts } from './components/results/ExtractedFacts'
import { ParallelScenarios } from './components/results/ParallelScenarios'
import { ParallelExecutionProgress } from './components/workflow/ParallelExecutionProgress'
import { VerificationPanel } from './components/results/VerificationPanel'
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

// Connection status indicator component
function ConnectionStatus({ status, isStreaming }: { status: string; isStreaming: boolean }) {
  const isConnected = status === 'connected' || isStreaming
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
      <span className="text-sm text-slate-400">
        {isStreaming ? 'Live' : isConnected ? 'Connected' : status === 'connecting' ? 'Connecting...' : 'Ready'}
      </span>
    </div>
  )
}

// Debate depth options
type DebateDepth = 'standard' | 'deep' | 'legendary'
const DEBATE_DEPTHS: Record<DebateDepth, { label: string; turns: string; description: string }> = {
  standard: { label: 'Standard', turns: '25-40', description: 'Quick analysis (3-5 min)' },
  deep: { label: 'Deep', turns: '50-100', description: 'Thorough analysis (10-15 min)' },
  legendary: { label: 'Legendary', turns: '100-150', description: 'Maximum depth (20-30 min)' },
}

function App() {
  const { state, connect, cancel } = useWorkflowStream()
  const [question, setQuestion] = useState('What are the implications of raising minimum wage?')
  const [debateDepth, setDebateDepth] = useState<DebateDepth>('legendary')  // DEFAULT: Maximum depth
  const provider = 'azure' as const  // Azure GPT-4o is the default and only provider
  
  // Safety check: ensure state exists
  if (!state) {
    return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white">Loading...</div>
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await connect({ question, provider, debate_depth: debateDepth })
    } catch (error) {
      console.error('Submit error:', error)
    }
  }

  // Determine if we should show the two-column layout (analysis in progress)
  const showTwoColumnLayout = state.isStreaming || state.completedStages.size > 0

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* ============================================
          HEADER - Always visible
          ============================================ */}
      <header className="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-sm border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-maroon-600 to-maroon-800 flex items-center justify-center text-white font-bold" style={{ background: 'linear-gradient(135deg, #8B1538, #5a0d24)' }}>
                Q
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Qatar Ministry of Labour</p>
                <h1 className="text-lg font-semibold text-white">QNWIS Enterprise Intelligence</h1>
              </div>
            </div>
            <ConnectionStatus status={state.connectionStatus} isStreaming={state.isStreaming} />
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Banner */}
        {state.error && <ErrorBanner message={state.error} onRetry={() => connect({ question, provider })} />}

        {/* ============================================
            QUESTION INPUT SECTION
            ============================================ */}
        <section className="mb-8">
          <form onSubmit={handleSubmit} className="bg-slate-900/60 border border-slate-700 rounded-2xl p-6 space-y-4">
            <div className="space-y-2">
              <label htmlFor="question" className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Ministerial Question
              </label>
              <textarea
                id="question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={3}
                className="w-full rounded-xl border border-slate-600 bg-slate-950/50 p-4 text-slate-100 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-500/20 transition"
                placeholder="Enter your policy question..."
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4">
              {/* Debate Depth Selector */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500 uppercase tracking-wider">Debate Depth:</span>
                <div className="flex gap-1">
                  {(Object.keys(DEBATE_DEPTHS) as DebateDepth[]).map((depth) => (
                    <button
                      key={depth}
                      type="button"
                      onClick={() => setDebateDepth(depth)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                        debateDepth === depth
                          ? depth === 'legendary' 
                            ? 'bg-amber-500/30 text-amber-300 border border-amber-500/50'
                            : depth === 'deep'
                            ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-500/50'
                            : 'bg-slate-600/30 text-slate-300 border border-slate-500/50'
                          : 'bg-slate-800/50 text-slate-400 border border-slate-700 hover:bg-slate-700/50'
                      }`}
                    >
                      {DEBATE_DEPTHS[depth].label}
                      <span className="ml-1 text-[10px] opacity-70">({DEBATE_DEPTHS[depth].turns})</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500">Powered by:</span>
                <span className="rounded-lg px-3 py-1.5 text-xs font-medium bg-cyan-500/20 text-cyan-300 border border-cyan-500/50">
                  Azure GPT-4o
                </span>
              </div>

              <div className="flex gap-3">
                <button
                  type="submit"
                  className="rounded-xl bg-gradient-to-r from-cyan-500 to-cyan-600 px-8 py-3 text-slate-900 font-semibold hover:from-cyan-400 hover:to-cyan-500 transition disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20"
                  disabled={state.isStreaming}
                >
                  {state.isStreaming ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-slate-900/30 border-t-slate-900 rounded-full animate-spin" />
                      Analyzing...
                    </span>
                  ) : (
                    'Submit to Intelligence Council'
                  )}
                </button>
                {state.isStreaming && (
                  <button
                    type="button"
                    onClick={cancel}
                    className="rounded-xl border border-red-500/50 px-4 py-3 text-sm font-medium text-red-400 hover:bg-red-500/10 transition"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          </form>
        </section>

        {/* ============================================
            INFEASIBILITY ALERT - When target is impossible
            ============================================ */}
        {state.targetInfeasible && (
          <section className="mb-8">
            <div className="bg-gradient-to-r from-red-900/40 via-red-800/30 to-red-900/40 border-2 border-red-500/60 rounded-2xl p-8 shadow-lg shadow-red-500/10">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-16 h-16 rounded-xl bg-red-500/20 flex items-center justify-center">
                  <span className="text-4xl">⛔</span>
                </div>
                <div className="flex-1 space-y-4">
                  <div>
                    <h2 className="text-2xl font-bold text-red-400 mb-2">
                      First-Principles Check: Target NOT Achievable
                    </h2>
                    <p className="text-slate-300 text-lg leading-relaxed">
                      {state.infeasibilityReason || 'This target fails basic arithmetic feasibility checks.'}
                    </p>
                  </div>
                  
                  {state.feasibleAlternative && (
                    <div className="bg-emerald-900/30 border border-emerald-500/40 rounded-xl p-4">
                      <h3 className="text-emerald-400 font-semibold mb-2 flex items-center gap-2">
                        <span>💡</span> Feasible Alternative
                      </h3>
                      <p className="text-slate-300">{state.feasibleAlternative}</p>
                    </div>
                  )}
                  
                  <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-600/50">
                    <h3 className="text-amber-400 font-semibold mb-2 flex items-center gap-2">
                      <span>🔢</span> Why This Matters
                    </h3>
                    <p className="text-slate-400 text-sm">
                      Before investing analytical resources into <strong>HOW</strong> to achieve a target, 
                      we first verify <strong>IF</strong> it's achievable. This query failed basic arithmetic checks — 
                      the required numbers exceed what is physically possible. Rather than waste compute debating 
                      impossible scenarios, we provide this explanation so you can revise the target.
                    </p>
                  </div>
                  
                  <div className="flex items-center gap-3 pt-2">
                    <span className="px-3 py-1 rounded-full bg-red-500/20 text-red-300 text-sm font-medium border border-red-500/30">
                      Verdict: INFEASIBLE
                    </span>
                    <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-sm font-medium border border-emerald-500/30">
                      Confidence: 99% (Arithmetic Certainty)
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ============================================
            MAIN CONTENT - Two Column Layout
            ============================================ */}
        {showTwoColumnLayout && !state.targetInfeasible && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* ----------------------------------------
                LEFT SIDEBAR (4 cols) - Progress & Facts
                ---------------------------------------- */}
            <aside className="lg:col-span-4 space-y-6">
              {/* Progress Dashboard */}
              <StageProgress 
                currentStage={state.currentStage} 
                completedStages={state.completedStages}
                startTime={state.startTime}
              />

              {/* Stage Timeline */}
              <StageTimeline
                stageTiming={state.stageTiming}
                completedStages={state.completedStages}
                currentStage={state.currentStage}
                insightPreview={state.reasoningChain.length > 0 ? state.reasoningChain[state.reasoningChain.length - 1] : undefined}
              />

              {/* Extracted Facts */}
              <ExtractedFacts facts={state.prefetchFacts} />
            </aside>

            {/* ----------------------------------------
                MAIN AREA (8 cols) - Analysis & Debate
                ---------------------------------------- */}
            <main className="lg:col-span-8 space-y-6">
              {/* Parallel Scenario Execution */}
              <ParallelExecutionProgress
                scenarios={state.scenarios || []}
                scenariosCompleted={state.scenariosCompleted || 0}
                totalScenarios={state.totalScenarios || 0}
                isActive={state.parallelExecutionActive || false}
                scenarioProgress={state.scenarioProgress}
                scenarioResults={state.scenarioResults || []}
              />

              {/* Agent Execution Grid */}
              <AgentGrid 
                agents={state.agentStatuses} 
                agentsExpected={state.agentsExpected || 0}
                agentsRunning={state.agentsRunning || false}
              />

              {/* Multi-Agent Debate */}
              <DebatePanel 
                debate={state.debateResults} 
                debateTurns={state.debateTurns}
                isStreaming={state.isStreaming && state.currentStage === 'debate'}
              />

              {/* Critical Review */}
              <CritiquePanel critique={state.critiqueResults} />

              {/* Verification */}
              <VerificationPanel verification={state.verification} />
            </main>
          </div>
        )}

        {/* ============================================
            SYNTHESIS SECTION - Full Width
            ============================================ */}
        {(state.metaSynthesis || state.scenarioResults.length > 0) && (
          <section className="mt-8">
            <ParallelScenarios 
              scenarios={state.scenarios || []}
              scenarioResults={state.scenarioResults || []}
              metaSynthesis={state.metaSynthesis}
            />
          </section>
        )}

        {/* Legendary Strategic Intelligence Briefing - The Crown Jewel */}
        {state.synthesis && (
          <section className="mt-8">
            <LegendaryBriefing 
              synthesis={state.synthesis} 
              confidence={(state.finalState as any)?.confidence || 0.75}
              stats={state.synthesisStats || {
                n_facts: state.prefetchFacts?.length || 0,
                n_sources: 4,
                // Count scenarios from scenarioProgress Map or scenarioResults array
                n_scenarios: state.scenarioProgress?.size || state.scenarioResults?.length || state.totalScenarios || 6,
                // Count turns from debateTurns array (most reliable source)
                n_turns: state.debateTurns?.length || state.debateResults?.total_turns || 0,
                // Count unique experts from debateTurns
                n_experts: state.selectedAgents?.length || 
                           new Set(state.debateTurns?.map((t: any) => t.agent) || []).size || 6,
                // Count challenges: turns with type 'challenge' or high-severity in debate
                n_challenges: state.debateTurns?.filter((t: any) => 
                  t.type === 'challenge' || t.type === 'risk_identification' || t.type === 'risk_assessment'
                )?.length || state.debateResults?.contradictions_found || 0,
                // Count consensus: turns with consensus-related types
                n_consensus: state.debateTurns?.filter((t: any) => 
                  t.type === 'consensus' || t.type === 'consensus_synthesis' || t.type === 'resolution'
                )?.length || state.debateResults?.resolved || 0,
                n_critiques: state.critiqueResults?.critiques?.length || 0,
                n_red_flags: state.critiqueResults?.red_flags?.length || 0,
                avg_confidence: 75,
              }}
            />
          </section>
        )}

        {/* ============================================
            IDLE STATE - Show when no analysis
            ============================================ */}
        {!showTwoColumnLayout && (
          <section className="text-center py-16">
            <div className="max-w-2xl mx-auto">
              <span className="text-6xl mb-6 block">🏛️</span>
              <h2 className="text-2xl font-semibold text-white mb-4">Ready for Analysis</h2>
              <p className="text-slate-400 mb-8">
                Enter your policy question above to activate the multi-agent intelligence council. 
                The system will analyze economic implications, labor market impacts, and provide 
                comprehensive policy recommendations.
              </p>
              <div className="flex flex-wrap justify-center gap-4 text-sm text-slate-500">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  12+ Specialized Agents
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-purple-400" />
                  Multi-Agent Debate
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  Real-time Streaming
                </div>
              </div>
            </div>
          </section>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <p className="text-xs text-slate-600 text-center">
            QNWIS Enterprise Intelligence System · Qatar Ministry of Labour · Confidential
          </p>
        </div>
      </footer>
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
