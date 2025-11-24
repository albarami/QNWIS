import { useState, useEffect } from 'react'
import { ALL_STAGES, WorkflowStage } from '../../types/workflow'
import { formatDuration } from '../../utils/formatters'

interface StageProgressProps {
  currentStage: WorkflowStage | null
  completedStages: Set<WorkflowStage>
  startTime?: string | null
}

const stageOrder = ALL_STAGES

// Estimated duration per stage (in ms) for time prediction
const STAGE_ESTIMATED_DURATION: Partial<Record<WorkflowStage, number>> = {
  classify: 2000,
  prefetch: 5000,
  rag: 3000,
  scenario_gen: 5000,
  parallel_exec: 120000, // 2 minutes
  meta_synthesis: 30000,
  agent_selection: 3000,
  agents: 60000, // 1 minute
  debate: 90000, // 1.5 minutes
  critique: 30000,
  verify: 10000,
  synthesize: 20000,
  done: 0,
}

export function StageProgress({ currentStage, completedStages, startTime }: StageProgressProps) {
  const [elapsedMs, setElapsedMs] = useState(0)
  
  // Update elapsed time every second while streaming
  useEffect(() => {
    if (!startTime || completedStages.has('done')) {
      return
    }
    
    const interval = setInterval(() => {
      const start = new Date(startTime).getTime()
      setElapsedMs(Date.now() - start)
    }, 1000)
    
    return () => clearInterval(interval)
  }, [startTime, completedStages])
  
  // Calculate estimated total time
  const estimatedTotalMs = Object.values(STAGE_ESTIMATED_DURATION).reduce((sum, d) => sum + (d || 0), 0)
  
  // Calculate estimated remaining based on completed stages
  const completedDuration = stageOrder
    .filter(stage => completedStages.has(stage))
    .reduce((sum, stage) => sum + (STAGE_ESTIMATED_DURATION[stage] || 0), 0)
  const estimatedRemainingMs = Math.max(0, estimatedTotalMs - completedDuration)
  
  const progress = (completedStages.size / stageOrder.length) * 100

  return (
    <div className="space-y-4" data-testid="workflow-progress">
      {/* Header with time info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-[0.3em] text-slate-400">Workflow Progress</span>
          {startTime && elapsedMs > 0 && (
            <span className="text-xs text-cyan-400">
              ⏱️ {formatDuration(elapsedMs)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {estimatedRemainingMs > 0 && !completedStages.has('done') && (
            <span className="text-xs text-slate-500">
              ~{formatDuration(estimatedRemainingMs)} remaining
            </span>
          )}
          <span className="text-sm font-medium text-cyan-400">
            {completedStages.size}/{stageOrder.length} stages
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="relative h-3 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
        {/* Animated pulse for active */}
        {currentStage && !completedStages.has('done') && (
          <div 
            className="absolute inset-y-0 bg-white/20 animate-pulse"
            style={{ 
              left: `${progress}%`, 
              width: `${100 / stageOrder.length}%`,
              maxWidth: '100px'
            }}
          />
        )}
      </div>

      {/* Stage pills - show condensed view */}
      <div className="flex flex-wrap gap-2">
        {stageOrder.map((stage) => {
          const isComplete = completedStages.has(stage)
          const isCurrent = currentStage === stage
          const isPending = !isComplete && !isCurrent

          return (
            <span
              key={stage}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                isComplete 
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' 
                  : isCurrent 
                    ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-400 animate-pulse shadow-[0_0_10px_rgba(34,211,238,0.3)]' 
                    : 'bg-slate-800/50 text-slate-500 border border-slate-700'
              }`}
              data-testid={`stage-${stage}`}
              data-status={isComplete ? 'complete' : isCurrent ? 'current' : 'pending'}
            >
              {isComplete && '✓ '}
              {isCurrent && '● '}
              {isPending && '○ '}
              {stage.replace('_', ' ')}
            </span>
          )
        })}
      </div>
    </div>
  )
}
