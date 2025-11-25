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

// Stage descriptions for ministerial context
const STAGE_DESCRIPTIONS: Record<WorkflowStage, { label: string; description: string; icon: string }> = {
  classify: { label: 'Classification', description: 'Analyzing query complexity and routing strategy', icon: '🎯' },
  prefetch: { label: 'Fact Extraction', description: 'Gathering deterministic data from official sources', icon: '📊' },
  rag: { label: 'Context Retrieval', description: 'Retrieving relevant historical context and precedents', icon: '📚' },
  scenario_gen: { label: 'Scenario Generation', description: 'Creating diverse economic scenarios for analysis', icon: '🔮' },
  parallel_exec: { label: 'Parallel Analysis', description: 'Running scenarios across multiple GPUs simultaneously', icon: '🚀' },
  meta_synthesis: { label: 'Meta-Synthesis', description: 'Synthesizing cross-scenario insights and recommendations', icon: '🎓' },
  agent_selection: { label: 'Agent Selection', description: 'Choosing specialized experts for this query', icon: '🤖' },
  agents: { label: 'Agent Execution', description: 'PhD-level economists analyzing the policy question', icon: '🧠' },
  debate: { label: 'Multi-Agent Debate', description: 'Experts challenging and refining each other\'s analyses', icon: '🔥' },
  critique: { label: 'Critical Review', description: 'Devil\'s advocate examining potential weaknesses', icon: '⚖️' },
  verify: { label: 'Verification', description: 'Fact-checking all claims against authoritative sources', icon: '✅' },
  synthesize: { label: 'Final Synthesis', description: 'Composing ministerial-grade strategic guidance', icon: '📝' },
  done: { label: 'Complete', description: 'Analysis complete and ready for review', icon: '🏆' },
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

  // Get current stage info
  const currentStageInfo = currentStage ? STAGE_DESCRIPTIONS[currentStage] : null
  
  return (
    <div className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900/40 p-6" data-testid="workflow-progress">
      {/* Header with time info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-[0.3em] text-slate-400">Workflow Progress</span>
          {startTime && elapsedMs > 0 && (
            <span className="text-xs text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded">
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
          <span className="text-sm font-bold text-cyan-400">
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
      
      {/* Current Stage Card */}
      {currentStageInfo && !completedStages.has('done') && (
        <div className="bg-gradient-to-r from-cyan-500/10 to-purple-500/10 rounded-xl p-4 border border-cyan-500/30">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{currentStageInfo.icon}</span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-white">{currentStageInfo.label}</span>
                <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
              </div>
              <p className="text-sm text-slate-400 mt-0.5">{currentStageInfo.description}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-cyan-400">{Math.round(progress)}%</p>
              <p className="text-xs text-slate-500">complete</p>
            </div>
          </div>
        </div>
      )}
      
      {/* Completed State */}
      {completedStages.has('done') && (
        <div className="bg-gradient-to-r from-emerald-500/10 to-green-500/10 rounded-xl p-4 border border-emerald-500/30">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🏆</span>
            <div className="flex-1">
              <span className="font-semibold text-emerald-400">Analysis Complete</span>
              <p className="text-sm text-slate-400 mt-0.5">
                All {stageOrder.length} stages processed in {formatDuration(elapsedMs)}
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-emerald-400">100%</p>
            </div>
          </div>
        </div>
      )}

      {/* Stage pills - flex wrap view */}
      <div className="flex flex-wrap gap-1.5">
        {stageOrder.map((stage) => {
          const isComplete = completedStages.has(stage)
          const isCurrent = currentStage === stage
          const stageInfo = STAGE_DESCRIPTIONS[stage]
          
          // Short labels for compact display
          const shortLabels: Record<WorkflowStage, string> = {
            classify: 'classify',
            prefetch: 'prefetch',
            rag: 'rag',
            scenario_gen: 'scenario gen',
            parallel_exec: 'parallel exec',
            meta_synthesis: 'meta synthesis',
            agent_selection: 'agent selection',
            agents: 'agents',
            debate: 'debate',
            critique: 'critique',
            verify: 'verify',
            synthesize: 'synthesize',
            done: 'done',
          }

          return (
            <div
              key={stage}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all whitespace-nowrap ${
                isComplete 
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' 
                  : isCurrent 
                    ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.3)]' 
                    : 'bg-slate-800/50 text-slate-500 border border-slate-700/50'
              }`}
              data-testid={`stage-${stage}`}
              data-status={isComplete ? 'complete' : isCurrent ? 'current' : 'pending'}
              title={`${stageInfo.label}: ${stageInfo.description}`}
            >
              {isComplete && <span className="mr-0.5">✓</span>}
              {isCurrent && <span className="mr-0.5 animate-pulse">●</span>}
              {shortLabels[stage]}
            </div>
          )
        })}
      </div>
    </div>
  )
}
