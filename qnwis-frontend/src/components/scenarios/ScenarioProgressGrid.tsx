import React from 'react'

interface ScenarioProgress {
  name: string
  status: 'pending' | 'running' | 'complete' | 'queued' | 'error'
  progress: number
  icon?: string
}

interface ScenarioProgressGridProps {
  scenarios: Map<string, ScenarioProgress> | ScenarioProgress[]
  totalScenarios: number
  completedScenarios: number
  isActive: boolean
}

const ScenarioCard: React.FC<{ scenario: ScenarioProgress; index: number }> = ({ scenario, index }) => {
  const icons = ['📊', '📈', '🏆', '⚠️', '🌍', '🔮']
  const icon = scenario.icon || icons[index % icons.length]
  
  const statusColors: Record<string, string> = {
    pending: 'border-slate-600 bg-slate-800/30',
    queued: 'border-slate-600 bg-slate-800/30',
    running: 'border-cyan-500/50 bg-cyan-900/20 shadow-lg shadow-cyan-500/10',
    complete: 'border-emerald-500/50 bg-emerald-900/20',
    error: 'border-red-500/50 bg-red-900/20',
  }
  
  const statusBadge: Record<string, React.ReactNode> = {
    pending: <span className="px-2 py-0.5 text-xs rounded bg-slate-700 text-slate-400">Pending</span>,
    queued: <span className="px-2 py-0.5 text-xs rounded bg-slate-700 text-slate-400">Queued</span>,
    running: (
      <span className="px-2 py-0.5 text-xs rounded bg-cyan-500/20 text-cyan-300 flex items-center gap-1">
        <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" />
        Analyzing
      </span>
    ),
    complete: <span className="px-2 py-0.5 text-xs rounded bg-emerald-500/20 text-emerald-300">✓ Complete</span>,
    error: <span className="px-2 py-0.5 text-xs rounded bg-red-500/20 text-red-300">✗ Error</span>,
  }

  return (
    <div className={`rounded-xl border p-4 transition-all duration-300 ${statusColors[scenario.status]}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{icon}</span>
          <span className="font-medium text-white text-sm">{scenario.name || `Scenario ${index + 1}`}</span>
        </div>
        {statusBadge[scenario.status]}
      </div>
      
      {scenario.status === 'running' && (
        <div className="mt-3">
          <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400 rounded-full transition-all duration-500"
              style={{ width: `${scenario.progress}%` }}
            />
          </div>
          <p className="text-xs text-slate-500 mt-1">Monte Carlo simulation in progress...</p>
        </div>
      )}
      
      {scenario.status === 'complete' && (
        <p className="text-xs text-slate-400 mt-2">Analysis complete • Ready for debate</p>
      )}
    </div>
  )
}

export const ScenarioProgressGrid: React.FC<ScenarioProgressGridProps> = ({
  scenarios,
  totalScenarios,
  completedScenarios,
  isActive,
}) => {
  // Convert Map to array if needed
  const scenarioList: ScenarioProgress[] = scenarios instanceof Map 
    ? Array.from(scenarios.entries()).map(([id, s]) => ({ ...s, name: s.name || id }))
    : scenarios
  
  // If no scenarios yet, show placeholders
  const displayScenarios = scenarioList.length > 0 
    ? scenarioList 
    : Array.from({ length: totalScenarios || 6 }, (_, i) => ({
        name: `Scenario ${i + 1}`,
        status: 'pending' as const,
        progress: 0,
      }))

  const runningCount = displayScenarios.filter(s => s.status === 'running').length

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Scenario Analysis</p>
          <p className="text-sm text-slate-300">
            {runningCount > 0 ? (
              <span className="text-cyan-400">{runningCount} scenarios running</span>
            ) : completedScenarios > 0 ? (
              <span className="text-emerald-400">{completedScenarios} scenarios complete</span>
            ) : isActive ? (
              <span className="text-yellow-400">Generating scenarios...</span>
            ) : (
              'Policy scenarios for multi-path analysis'
            )}
          </p>
        </div>
        <span className="text-xs text-slate-500">
          {completedScenarios}/{totalScenarios || displayScenarios.length} complete
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {displayScenarios.map((scenario, idx) => (
          <ScenarioCard key={'scenarioId' in scenario ? String(scenario.scenarioId) : `scenario_${idx}`} scenario={scenario} index={idx} />
        ))}
      </div>
      
      {completedScenarios > 0 && completedScenarios === totalScenarios && (
        <div className="bg-emerald-900/20 border border-emerald-500/30 rounded-lg p-3 flex items-center gap-2">
          <span className="text-emerald-400">✓</span>
          <p className="text-sm text-emerald-300">
            All {totalScenarios} scenarios analyzed • Results ready for cross-scenario comparison
          </p>
        </div>
      )}
    </div>
  )
}

export default ScenarioProgressGrid
