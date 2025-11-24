interface ParallelExecutionProgressProps {
  scenarios: any[]
  scenariosCompleted: number
  totalScenarios: number
  isActive: boolean
}

export function ParallelExecutionProgress({
  scenarios,
  scenariosCompleted,
  totalScenarios,
  isActive,
}: ParallelExecutionProgressProps) {
  if (!isActive && scenarios.length === 0) {
    return null
  }

  const progress = totalScenarios > 0 ? (scenariosCompleted / totalScenarios) * 100 : 0

  return (
    <div className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 rounded-lg p-6 border border-purple-500/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-purple-300">
          🚀 Parallel Scenario Execution (GPUs 0-5)
        </h3>
        <div className="text-sm text-slate-400">
          {scenariosCompleted}/{totalScenarios} scenarios complete
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-slate-400 mb-2">
          <span>Overall Progress</span>
          <span>{progress.toFixed(0)}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-3">
          <div
            className="bg-gradient-to-r from-purple-500 to-blue-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Scenario Cards */}
      {scenarios.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scenarios.map((scenario, idx) => {
            const gpuId = idx % 6
            return (
              <div
                key={idx}
                className="bg-slate-800/50 rounded-lg p-4 border border-slate-600"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-white">{scenario.name}</span>
                  <span className="text-xs text-slate-400">GPU {gpuId}</span>
                </div>
                <div className="text-sm text-slate-300 mb-3 line-clamp-2">
                  {scenario.description}
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      idx < scenariosCompleted
                        ? 'bg-green-500'
                        : isActive
                        ? 'bg-yellow-500 animate-pulse'
                        : 'bg-slate-500'
                    }`}
                  />
                  <span className="text-xs text-slate-400">
                    {idx < scenariosCompleted ? 'Complete' : isActive ? 'Running' : 'Pending'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {isActive && (
        <div className="mt-4 text-center text-sm text-slate-400">
          <div className="animate-pulse">Analyzing scenarios in parallel...</div>
        </div>
      )}
    </div>
  )
}

