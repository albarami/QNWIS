import { ALL_STAGES, WorkflowStage } from '../../types/workflow'

interface StageTimelineProps {
  stageTiming: Map<WorkflowStage, number>
  completedStages: Set<WorkflowStage>
  currentStage: WorkflowStage | null
}

export function StageTimeline({ stageTiming, completedStages, currentStage }: StageTimelineProps) {
  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 space-y-4" data-testid="stage-timeline">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Stage Timeline</p>
          <p className="text-sm text-slate-300">Latency budget · classify→done</p>
        </div>
        <span className="text-xs text-slate-500">{completedStages.size}/{ALL_STAGES.length} complete</span>
      </div>

      <ol className="space-y-3">
        {ALL_STAGES.map((stage) => {
          const isComplete = completedStages.has(stage)
          const isCurrent = currentStage === stage
          const latency = stageTiming.get(stage) ?? 0

          return (
            <li key={stage} className="flex items-start gap-3">
              <div
                className={`mt-1 h-3 w-3 rounded-full border ${
                  isComplete
                    ? 'bg-emerald-400/90 border-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.8)]'
                    : isCurrent
                      ? 'bg-cyan-400 border-cyan-200 animate-pulse'
                      : 'bg-slate-700 border-slate-600'
                }`}
              />
              <div className="flex-1">
                <div className="flex items-center justify-between text-sm">
                  <p className="font-semibold text-slate-100 capitalize">{stage.replace('_', ' ')}</p>
                  <span className="text-xs text-slate-400">{latency ? `${latency.toFixed(0)} ms` : '—'}</span>
                </div>
                <div className="relative mt-2 h-2 rounded-full bg-slate-800">
                  <div
                    className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${
                      isComplete ? 'bg-emerald-400' : isCurrent ? 'bg-cyan-400' : 'bg-slate-700'
                    }`}
                    style={{ width: isComplete ? '100%' : isCurrent ? '50%' : '15%' }}
                  />
                </div>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
