import { ALL_STAGES, WorkflowStage } from '../../types/workflow'

interface StageProgressProps {
  currentStage: WorkflowStage | null
  completedStages: Set<WorkflowStage>
}

const stageOrder = ALL_STAGES

export function StageProgress({ currentStage, completedStages }: StageProgressProps) {
  return (
    <div className="space-y-4" data-testid="workflow-progress">
      <div className="flex items-center justify-between text-xs text-slate-400 uppercase tracking-[0.3em]">
        <span>Workflow Progress</span>
        <span>
          {completedStages.size}/{stageOrder.length} stages
        </span>
      </div>

      <div className="relative h-3 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-500"
          style={{ width: `${(completedStages.size / stageOrder.length) * 100}%` }}
        />
      </div>

      <ol className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
        {stageOrder.map((stage) => {
          const isComplete = completedStages.has(stage)
          const isCurrent = currentStage === stage

          return (
            <li
              key={stage}
              className={`rounded-2xl border px-3 py-2 text-center font-semibold transition ${isComplete ? 'border-emerald-500/50 text-emerald-300 bg-emerald-500/10' : isCurrent ? 'border-cyan-400 text-cyan-200 bg-cyan-500/10 animate-pulse' : 'border-slate-700 text-slate-400 bg-slate-900/40'}`}
              data-testid={`stage-${stage}`}
              data-status={isComplete ? 'complete' : isCurrent ? 'current' : 'pending'}
            >
              {stage.replace('_', ' ')}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
