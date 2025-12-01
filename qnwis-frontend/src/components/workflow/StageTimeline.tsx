import { ALL_STAGES, WorkflowStage } from '../../types/workflow'
import { formatDuration } from '../../utils/formatters'

interface StageTimelineProps {
  stageTiming: Map<WorkflowStage, number>
  completedStages: Set<WorkflowStage>
  currentStage: WorkflowStage | null
  insightPreview?: string
}

// Human-readable stage names
const STAGE_NAMES: Record<WorkflowStage, string> = {
  classify: 'Classification',
  prefetch: 'Fact Extraction',
  rag: 'Context Retrieval',
  scenario_gen: 'Scenario Generation',
  parallel_exec: 'Parallel Analysis',
  meta_synthesis: 'Meta-Synthesis',
  agent_selection: 'Agent Selection',
  agents: 'Agent Execution',
  debate: 'Multi-Agent Debate',
  critique: 'Critical Review',
  verify: 'Verification',
  synthesize: 'Final Synthesis',
  done: 'Complete',
}

export function StageTimeline({ stageTiming, completedStages, currentStage, insightPreview }: StageTimelineProps) {
  const completedList = ALL_STAGES.filter(s => completedStages.has(s))
  const activeList = ALL_STAGES.filter(s => currentStage === s && !completedStages.has(s))
  const pendingList = ALL_STAGES.filter(s => !completedStages.has(s) && currentStage !== s)
  
  // Total latency
  const totalLatency = Array.from(stageTiming.values()).reduce((sum, v) => sum + v, 0)

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 space-y-4" data-testid="stage-timeline">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Stage Timeline</p>
          <p className="text-sm text-slate-300">Analysis pipeline progress</p>
        </div>
        <div className="text-right">
          <span className="text-lg font-semibold text-cyan-400">{completedStages.size}/{ALL_STAGES.length}</span>
          <p className="text-xs text-slate-500">
            {totalLatency > 0 ? formatDuration(totalLatency) : '--'}
          </p>
        </div>
      </div>

      {/* Three-column layout */}
      <div className="grid grid-cols-3 gap-4">
        {/* Completed Column */}
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Completed ({completedList.length})
          </h4>
          <div className="space-y-1">
            {completedList.length === 0 ? (
              <p className="text-xs text-slate-600 italic">None yet</p>
            ) : (
              completedList.map(stage => {
                const latency = stageTiming.get(stage) || 0
                return (
                  <div 
                    key={stage} 
                    className="flex items-center justify-between text-xs bg-emerald-500/10 rounded px-2 py-1.5"
                  >
                    <span className="text-emerald-300 flex items-center gap-1">
                      <span className="text-emerald-400">✓</span>
                      {STAGE_NAMES[stage]}
                    </span>
                    {latency > 0 && (
                      <span className="text-slate-500">{formatDuration(latency)}</span>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Active Column */}
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            Active ({activeList.length})
          </h4>
          <div className="space-y-1">
            {activeList.length === 0 ? (
              <p className="text-xs text-slate-600 italic">
                {completedStages.has('done') ? 'Analysis complete' : 'Waiting...'}
              </p>
            ) : (
              activeList.map(stage => (
                <div 
                  key={stage} 
                  className="flex items-center gap-2 text-xs bg-cyan-500/10 rounded px-2 py-1.5 border border-cyan-500/30"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                  <span className="text-cyan-300">{STAGE_NAMES[stage]}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Pending Column */}
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-slate-600" />
            Pending ({pendingList.length})
          </h4>
          <div className="space-y-1">
            {pendingList.length === 0 ? (
              <p className="text-xs text-slate-600 italic">All stages processed</p>
            ) : (
              pendingList.slice(0, 5).map(stage => (
                <div 
                  key={stage} 
                  className="flex items-center gap-2 text-xs text-slate-500 px-2 py-1"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                  {STAGE_NAMES[stage]}
                </div>
              ))
            )}
            {pendingList.length > 5 && (
              <p className="text-xs text-slate-600 px-2">+{pendingList.length - 5} more...</p>
            )}
          </div>
        </div>
      </div>

      {/* Emerging Insight Preview */}
      {insightPreview && (
        <div className="mt-4 pt-4 border-t border-slate-700">
          <div className="bg-gradient-to-r from-purple-500/10 to-cyan-500/10 rounded-lg p-4 border border-purple-500/20">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">💡</span>
              <h4 className="text-sm font-semibold text-purple-300">EMERGING INSIGHT</h4>
            </div>
            <p className="text-sm text-slate-300 italic">&ldquo;{insightPreview}&rdquo;</p>
          </div>
        </div>
      )}
    </div>
  )
}
