import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import { useWorkflowStream } from './hooks/useWorkflowStream'
import { StageIndicator } from './components/workflow/StageIndicator'
import { WorkflowProgress } from './components/workflow/WorkflowProgress'
import { MetadataDisplay } from './components/workflow/MetadataDisplay'
import { AgentOutputs } from './components/AgentOutputs'
import { DebateSynthesis } from './components/analysis/DebateSynthesis'
import { ExecutiveSummaryCard } from './components/analysis/ExecutiveSummaryCard'
import { LiveDebateTimeline } from './components/analysis/LiveDebateTimeline'
import { ExtractedFactsCard } from './components/analysis/ExtractedFactsCard'
import { ConfidenceBreakdownCard } from './components/analysis/ConfidenceBreakdownCard'
import { QuickStatsCard } from './components/analysis/QuickStatsCard'
import type { WorkflowState } from './types/workflow'

const INITIAL_WORKFLOW_STATE: WorkflowState = {
  stage: 'classify',
  query: 'Awaiting ministerial question…',
  complexity: 'complex',
  extracted_facts: [],
  extraction_confidence: 0,
  agent_outputs: [],
  agents_invoked: [],
  final_synthesis: '',
  confidence_score: 0,
  status: 'idle',
}

const STAGES = [
  'classify',
  'prefetch',
  'rag',
  'select_agents',
  'agents',
  'debate',
  'critique',
  'verify',
  'synthesize',
  'done',
] as const

const STAGE_LABELS: Record<string, string> = {
  classify: 'Classify',
  prefetch: 'Prefetch',
  rag: 'Retrieve',
  select_agents: 'Select Agents',
  agents: 'Agent Analyses',
  debate: 'Debate',
  critique: 'Critique',
  verify: 'Verify',
  synthesize: 'Synthesis',
  done: 'Complete',
  // Aliases for compatibility
  agent_selection: 'Select Agents',
  synthesis: 'Synthesis',
}

const queryExamples = [
  'Is 70% Qatarization in Qatar financial sector by 2030 feasible?',
  'What are the implications of raising the minimum wage for Qatari nationals to QR 20,000?',
  'Compare Qatar unemployment rates with other GCC countries',
]

const DEFAULT_PROMPT =
  'What are the implications of raising the minimum wage for Qatari nationals to QR 20,000?'

function App() {
  const [question, setQuestion] = useState('')
  const { state, isStreaming, error, startStream } = useWorkflowStream()

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const sanitized = question.trim()
    if (!sanitized) return
    void startStream(sanitized)
  }

  const workflowState: WorkflowState | null = state
  const effectiveState = workflowState ?? INITIAL_WORKFLOW_STATE
  const hasResults = Boolean(workflowState)

  const agentReports = workflowState?.agent_reports || []
  const multiAgentDebate = workflowState?.multi_agent_debate
  const critiqueOutput = workflowState?.critique_output

  const overallError = error || workflowState?.error || null

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white shadow-2xl border-b-4 border-amber-500">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-2xl font-bold text-slate-900">
                  QN
                </div>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">Qatar National Workforce Intelligence System</h1>
                  <p className="text-amber-200 text-sm font-medium tracking-wide">
                    QNWIS · Ministry of Labour Strategic Intelligence Council
                  </p>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs uppercase tracking-widest text-slate-400 mb-1">Classification</div>
              <div className="text-sm font-bold text-amber-400">MINISTERIAL BRIEFING</div>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8">
        <section className="mb-8 rounded-2xl bg-white shadow-xl border border-slate-200">
          <div className="border-b border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100 px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Strategic Query Interface</h2>
                <p className="text-sm text-slate-600">Submit policy questions for multi-agent analysis</p>
              </div>
              {isStreaming && (
                <div className="flex items-center gap-2 rounded-full bg-amber-100 px-4 py-2 text-sm font-semibold text-amber-800">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-amber-600"></div>
                  Live Analysis in Progress
                </div>
              )}
            </div>
          </div>
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            <div className="space-y-3">
              <label htmlFor="question" className="block text-sm font-bold uppercase tracking-wide text-slate-700">
                Ministerial Question
              </label>
              <textarea
                id="question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={DEFAULT_PROMPT}
                rows={4}
                className="w-full rounded-xl border-2 border-slate-300 px-5 py-4 text-lg font-medium text-slate-900 shadow-sm transition placeholder:text-slate-400 focus:border-amber-500 focus:ring-4 focus:ring-amber-100 focus:outline-none disabled:bg-slate-50 disabled:text-slate-500"
                disabled={isStreaming}
              />
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>{question.length} characters</span>
                <span>Maximum 5,000 characters</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <button
                type="submit"
                disabled={!question.trim() || isStreaming}
                className="rounded-xl bg-gradient-to-r from-slate-900 to-slate-700 px-10 py-4 text-base font-bold text-white shadow-lg transition hover:from-slate-800 hover:to-slate-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:from-slate-900"
              >
                {isStreaming ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Analyzing via 7-Agent Council
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                    Submit to Intelligence Council
                  </span>
                )}
              </button>
              <div className="text-sm text-slate-600">
                <span className="font-semibold">Expected response time:</span> 5-20 minutes
              </div>
            </div>
          </form>

          <div className="border-t border-slate-200 bg-slate-50 px-6 py-4">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-700 mb-3">Sample Strategic Queries</p>
            <div className="flex flex-wrap gap-2">
              {queryExamples.map((sample) => (
                <button
                  key={sample}
                  type="button"
                  onClick={() => setQuestion(sample)}
                  className="rounded-lg border-2 border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-amber-400 hover:bg-amber-50 hover:text-amber-900"
                >
                  {sample}
                </button>
              ))}
            </div>
          </div>

          {overallError && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {overallError}
            </div>
          )}
        </section>

        <section className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <StageIndicator
              stages={STAGES}
              stageLabels={STAGE_LABELS}
              currentStage={effectiveState.stage}
              isStreaming={isStreaming}
            />

            <LiveDebateTimeline
              agentOutputs={workflowState?.agent_outputs ?? []}
              debate={workflowState?.multi_agent_debate}
              critique={workflowState?.critique_output}
              synthesis={workflowState?.final_synthesis}
            />

            {hasResults && <AgentOutputs agentReports={agentReports} multiAgentDebate={multiAgentDebate} critiqueOutput={critiqueOutput} />}

            {hasResults && workflowState?.debate_synthesis && (
              <DebateSynthesis debate={workflowState.debate_synthesis} />
            )}
          </div>

          <div className="space-y-6">
            <WorkflowProgress state={effectiveState} />
            <QuickStatsCard state={effectiveState} />
            <MetadataDisplay state={effectiveState} />
            <ExecutiveSummaryCard
              synthesis={workflowState?.final_synthesis}
              confidence={workflowState?.confidence_score}
              status={effectiveState.status}
            />
            <ExtractedFactsCard facts={workflowState?.extracted_facts ?? []} />
            <ConfidenceBreakdownCard
              agentOutputs={workflowState?.agent_outputs ?? []}
              overallConfidence={workflowState?.confidence_score}
            />
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
