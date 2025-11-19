import { WorkflowStage } from '../../types/workflow'

interface CurrentStageCardProps {
  stage: WorkflowStage | null
  status: string
  startedAt?: string | null
}

const STAGE_DESCRIPTIONS: Record<WorkflowStage, string> = {
  classify: 'Understanding question intent & complexity',
  prefetch: 'Extracting deterministic facts from registry',
  rag: 'Retrieving high-signal snippets for grounding',
  agent_selection: 'Selecting optimal agents for this question',
  agents: 'Agents executing in parallel with live telemetry',
  debate: 'Resolving contradictions via LangGraph debate',
  critique: "Devil's advocate stress test to find weaknesses",
  verify: 'Citation & statistic verification layer',
  synthesize: 'Building ministerial-grade narrative',
  done: 'Workflow complete with full dossier ready',
}

export function CurrentStageCard({ stage, status, startedAt }: CurrentStageCardProps) {
  if (!stage) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6">
        <p className="text-sm uppercase tracking-[0.3em] text-slate-400">Current Stage</p>
        <p className="text-xl font-semibold text-slate-200 mt-2">Awaiting submission</p>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-cyan-400/60 bg-slate-900/50 p-6" data-testid="current-stage-card">
      <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">Current Stage</p>
      <h3 className="text-2xl font-semibold text-white mt-2 capitalize">{stage.replace('_', ' ')}</h3>
      <p className="text-sm text-cyan-200 mt-1">{STAGE_DESCRIPTIONS[stage]}</p>
      <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
        <span>Status: {status}</span>
        {startedAt && <span>Started at {new Date(startedAt).toLocaleTimeString()}</span>}
      </div>
    </div>
  )
}
