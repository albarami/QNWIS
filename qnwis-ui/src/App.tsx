import { useState } from 'react'
import { useWorkflowStream } from '@/hooks/useWorkflowStream'
import type { WorkflowState } from '@/types/workflow'
import { Layout } from '@/components/layout/Layout'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { QueryInput } from '@/components/workflow/QueryInput'
import { StageIndicator } from '@/components/workflow/StageIndicator'
import { WorkflowProgress } from '@/components/workflow/WorkflowProgress'
import { MetadataDisplay } from '@/components/workflow/MetadataDisplay'
import { ExtractedFacts } from '@/components/analysis/ExtractedFacts'
import { FinalSynthesis } from '@/components/analysis/FinalSynthesis'
import { AgentOutputs } from '@/components/AgentOutputs'

const STAGE_ORDER = [
  'classify',
  'prefetch',
  'rag',
  'agent_selection',
  'agents',
  'debate',
  'critique',
  'verify',
  'synthesize',
  'done',
] as const

type StageStep = (typeof STAGE_ORDER)[number]
const STAGE_SET = new Set<StageStep>(STAGE_ORDER)

const STAGE_LABEL: Record<string, string> = {
  classify: 'Classify',
  prefetch: 'Prefetch',
  rag: 'Data Retrieval',
  agent_selection: 'Agent Selection',
  agents: 'Agents',
  debate: 'Debate',
  critique: 'Critique',
  verify: 'Verification',
  synthesize: 'Synthesis',
  done: 'Complete',
}

const normalizeStage = (stage: WorkflowState['stage']): StageStep =>
  stage.startsWith('agent:')
    ? 'agents'
    : STAGE_SET.has(stage as StageStep)
      ? (stage as StageStep)
      : 'agents'

function App() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<string[]>([])

  const { state, isStreaming, error, startStream, stopStream } = useWorkflowStream({
    onComplete: () => {
      setHistory((prev) => {
        const candidates = [question.trim(), ...prev.filter((q) => q !== question.trim())]
        return candidates.filter(Boolean).slice(0, 3)
      })
    },
    onError: (err) => console.error('Workflow error:', err),
  })

  const handleSubmit = async (value: string) => {
    await startStream(value)
  }

  const currentStage = state ? normalizeStage(state.stage) : STAGE_ORDER[0]

  return (
    <Layout headerSubtitle="FastAPI streaming council powering the new React intelligence console">
      <ErrorBoundary>
        <QueryInput
          value={question}
          onChange={setQuestion}
          onSubmit={handleSubmit}
          onStop={stopStream}
          isStreaming={isStreaming}
          history={history}
        />
      </ErrorBoundary>

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      {state && (
        <div className="mt-6 space-y-6">
          <StageIndicator
            stages={STAGE_ORDER}
            stageLabels={STAGE_LABEL}
            currentStage={currentStage}
            isStreaming={isStreaming}
          />

          <WorkflowProgress state={state} />

          <ExtractedFacts facts={state.extracted_facts} />

          <FinalSynthesis synthesis={state.final_synthesis} confidence={state.confidence_score} />

          <AgentOutputs result={state} />

          <MetadataDisplay state={state} />
        </div>
      )}
    </Layout>
  )
}

export default App
