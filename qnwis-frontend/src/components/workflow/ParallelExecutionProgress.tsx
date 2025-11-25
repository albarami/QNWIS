import { ScenarioProgress, ScenarioResult } from '../../types/workflow'

interface ParallelExecutionProgressProps {
  scenarios: any[]
  scenariosCompleted: number
  totalScenarios: number
  isActive: boolean
  scenarioProgress?: Map<string, ScenarioProgress>
  scenarioResults?: ScenarioResult[]
  agentsExpected?: number
  agentsRunning?: boolean
}

// Scenario type detection based on name
function getScenarioType(name: string): { label: string; color: string; icon: string } {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('base') || nameLower.includes('current')) {
    return { label: 'BASE CASE', color: '#3B82F6', icon: '📊' }
  }
  if (nameLower.includes('optimistic') || nameLower.includes('best') || nameLower.includes('high')) {
    return { label: 'BEST CASE', color: '#22C55E', icon: '📈' }
  }
  if (nameLower.includes('pessimistic') || nameLower.includes('worst') || nameLower.includes('low')) {
    return { label: 'WORST CASE', color: '#EF4444', icon: '📉' }
  }
  return { label: 'ALTERNATIVE', color: '#8B5CF6', icon: '🔄' }
}

export function ParallelExecutionProgress({
  scenarios,
  scenariosCompleted,
  totalScenarios,
  isActive,
  scenarioProgress,
  scenarioResults = [],
}: ParallelExecutionProgressProps) {
  if (!isActive && scenarios.length === 0) {
    return null
  }
  
  // Helper to get result for a scenario
  const getScenarioResult = (scenarioName: string): ScenarioResult | undefined => {
    return scenarioResults.find(r => r.scenario?.name === scenarioName)
  }

  // Use scenarios.length as fallback if totalScenarios is 0
  const total = totalScenarios > 0 ? totalScenarios : Math.max(scenarios.length, scenarioProgress?.size || 0)
  
  // Calculate overall progress based on individual scenario progress
  let overallProgress = 0
  if (scenarioProgress && scenarioProgress.size > 0) {
    const progressValues = Array.from(scenarioProgress.values())
    overallProgress = progressValues.reduce((sum, sp) => sum + sp.progress, 0) / progressValues.length
  } else if (total > 0 && scenariosCompleted > 0) {
    overallProgress = (scenariosCompleted / total) * 100
  } else if (isActive) {
    // Show minimum progress when active but no specific data yet
    overallProgress = 5
  }
  
  // Debug log
  console.log('📊 ParallelExecutionProgress:', { 
    total, 
    scenariosCompleted, 
    overallProgress, 
    scenarioProgressSize: scenarioProgress?.size,
    isActive 
  })

  // Get scenario status from scenarioProgress map
  const getScenarioStatus = (scenarioId: string, idx: number): { status: string; progress: number } => {
    if (scenarioProgress) {
      // Try exact match first
      if (scenarioProgress.has(scenarioId)) {
        const sp = scenarioProgress.get(scenarioId)!
        return { status: sp.status, progress: sp.progress }
      }
      // Try underscore format (scenario_0, scenario_1, etc.)
      const underscoreId = `scenario_${idx}`
      if (scenarioProgress.has(underscoreId)) {
        const sp = scenarioProgress.get(underscoreId)!
        return { status: sp.status, progress: sp.progress }
      }
      // Try dash format (scenario-0, scenario-1, etc.)
      const dashId = `scenario-${idx}`
      if (scenarioProgress.has(dashId)) {
        const sp = scenarioProgress.get(dashId)!
        return { status: sp.status, progress: sp.progress }
      }
    }
    // Fallback based on index
    if (idx < scenariosCompleted) {
      return { status: 'complete', progress: 100 }
    }
    if (isActive) {
      return { status: 'running', progress: 50 }
    }
    return { status: 'queued', progress: 0 }
  }

  return (
    <div className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 rounded-lg p-6 border border-purple-500/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-purple-300">
          🚀 Parallel Scenario Analysis
        </h3>
        <div className="text-sm text-slate-400">
          {scenariosCompleted}/{total} Complete
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-slate-400 mb-2">
          <span>Overall Progress</span>
          <span className="font-semibold text-white">{Math.round(overallProgress)}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
          <div
            className="bg-gradient-to-r from-purple-500 to-cyan-400 h-3 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${Math.max(overallProgress, isActive ? 5 : 0)}%` }}
          />
        </div>
      </div>

      {/* Scenario Cards */}
      {scenarios.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scenarios.map((scenario, idx) => {
            // Use underscore format to match backend
            const scenarioId = scenario.id || `scenario_${idx}`
            const { status, progress } = getScenarioStatus(scenarioId, idx)
            const typeInfo = getScenarioType(scenario.name)
            const result = getScenarioResult(scenario.name)
            
            return (
              <div
                key={idx}
                className={`rounded-lg p-4 border-t-3 transition-all duration-300 ${
                  status === 'complete' 
                    ? 'bg-slate-800/70 border border-emerald-500/50' 
                    : status === 'running'
                    ? 'bg-slate-800/50 border border-cyan-400/50 shadow-[0_0_15px_rgba(0,212,170,0.15)]'
                    : 'bg-slate-800/30 border border-slate-600/50 opacity-60'
                }`}
                style={{ borderTopColor: typeInfo.color, borderTopWidth: '3px' }}
              >
                {/* Header with type label */}
                <div className="flex items-center justify-between mb-2">
                  <span 
                    className="text-xs font-bold uppercase tracking-wider"
                    style={{ color: typeInfo.color }}
                  >
                    {typeInfo.icon} {typeInfo.label}
                  </span>
                  {status === 'running' && (
                    <span className="text-xs text-cyan-400 animate-pulse">● RUNNING</span>
                  )}
                  {status === 'complete' && (
                    <span className="text-xs text-emerald-400">✓ COMPLETE</span>
                  )}
                  {status === 'queued' && (
                    <span className="text-xs text-slate-500">○ QUEUED</span>
                  )}
                </div>
                
                {/* Scenario name */}
                <h4 className="font-medium text-white mb-1 text-sm">{scenario.name}</h4>
                
                {/* Description */}
                <p className="text-xs text-slate-400 mb-3 line-clamp-2">
                  {scenario.description}
                </p>
                
                {/* Individual progress bar for running scenarios */}
                {status === 'running' && (
                  <div className="mt-2">
                    <div className="w-full bg-slate-700 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-cyan-400 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-500 mt-1">{progress}%</span>
                  </div>
                )}
                
                {/* Results Preview for complete scenarios */}
                {status === 'complete' && result && (
                  <div className="mt-3 pt-3 border-t border-slate-700 space-y-2">
                    {/* Confidence Score */}
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">Confidence</span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                          <div 
                            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400"
                            style={{ width: `${(result.confidence || 0) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-emerald-400 font-medium">
                          {((result.confidence || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    
                    {/* Key Findings Preview */}
                    {result.key_findings && result.key_findings.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-slate-500 mb-1">Key Finding:</p>
                        <p className="text-xs text-slate-300 line-clamp-2">
                          {result.key_findings[0]}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {isActive && (
        <div className="mt-4 text-center text-sm text-slate-400">
          <div className="flex items-center justify-center gap-2">
            <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
            <span>Analyzing scenarios in parallel...</span>
          </div>
        </div>
      )}
    </div>
  )
}

