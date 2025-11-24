import { Scenario, ScenarioResult, MetaSynthesis } from '../../types/workflow'

interface ParallelScenariosProps {
  scenarios: Scenario[]
  scenarioResults: ScenarioResult[]
  metaSynthesis: MetaSynthesis | null
}

export function ParallelScenarios({ scenarios, scenarioResults, metaSynthesis }: ParallelScenariosProps) {
  if (scenarios.length === 0 && !metaSynthesis) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Scenarios Overview */}
      {scenarios.length > 0 && (
        <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-cyan-400 mb-4">
            🎯 Parallel Scenario Analysis ({scenarios.length} scenarios)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {scenarios.map((scenario, idx) => (
              <div key={idx} className="bg-slate-900/50 rounded p-4 border border-slate-600">
                <div className="font-medium text-white mb-2">{scenario.name}</div>
                <div className="text-sm text-slate-300">{scenario.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Meta-Synthesis Results */}
      {metaSynthesis && (
        <div className="bg-gradient-to-br from-purple-900/30 to-blue-900/30 rounded-lg p-6 border border-purple-500/50">
          <h3 className="text-xl font-bold text-purple-300 mb-4">
            🎓 Cross-Scenario Meta-Synthesis
          </h3>

          {/* Robust Recommendations */}
          {metaSynthesis.robust_recommendations && metaSynthesis.robust_recommendations.length > 0 && (
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-green-400 mb-3">
                ✅ Robust Recommendations (Work in ALL Scenarios)
              </h4>
              <ul className="space-y-2">
                {metaSynthesis.robust_recommendations.map((rec, idx) => (
                  <li key={idx} className="text-slate-200 pl-4 border-l-2 border-green-500">
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Scenario-Dependent Strategies */}
          {metaSynthesis.scenario_dependent_strategies && metaSynthesis.scenario_dependent_strategies.length > 0 && (
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-yellow-400 mb-3">
                ⚡ Scenario-Dependent Strategies (IF-THEN Logic)
              </h4>
              <ul className="space-y-2">
                {metaSynthesis.scenario_dependent_strategies.map((strategy, idx) => (
                  <li key={idx} className="text-slate-200 pl-4 border-l-2 border-yellow-500">
                    {strategy}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Key Uncertainties */}
          {metaSynthesis.key_uncertainties && metaSynthesis.key_uncertainties.length > 0 && (
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-orange-400 mb-3">
                ⚠️ Key Uncertainties
              </h4>
              <ul className="space-y-2">
                {metaSynthesis.key_uncertainties.map((uncertainty, idx) => (
                  <li key={idx} className="text-slate-200 pl-4 border-l-2 border-orange-500">
                    {uncertainty}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Early Warning Indicators */}
          {metaSynthesis.early_warning_indicators && metaSynthesis.early_warning_indicators.length > 0 && (
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-red-400 mb-3">
                🚨 Early Warning Indicators
              </h4>
              <ul className="space-y-2">
                {metaSynthesis.early_warning_indicators.map((indicator, idx) => (
                  <li key={idx} className="text-slate-200 pl-4 border-l-2 border-red-500">
                    {indicator}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Final Strategic Guidance */}
          {metaSynthesis.final_strategic_guidance && (
            <div className="bg-slate-900/50 rounded p-4 border border-purple-400">
              <h4 className="text-lg font-semibold text-purple-300 mb-3">
                🎯 Final Strategic Guidance
              </h4>
              <div className="text-slate-200 whitespace-pre-wrap">
                {metaSynthesis.final_strategic_guidance}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Individual Scenario Results */}
      {scenarioResults.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-cyan-400">
            📊 Individual Scenario Findings
          </h3>
          {scenarioResults.map((result, idx) => (
            <details key={idx} className="bg-slate-800/30 rounded-lg border border-slate-600">
              <summary className="p-4 cursor-pointer hover:bg-slate-700/30 transition-colors">
                <span className="font-medium text-white">{result.scenario?.name || `Scenario ${idx + 1}`}</span>
                <span className="ml-4 text-sm text-slate-400">
                  Confidence: {((result.confidence || 0) * 100).toFixed(0)}%
                </span>
              </summary>
              <div className="p-4 pt-0 space-y-3">
                {result.key_findings && result.key_findings.length > 0 && (
                  <div>
                    <h5 className="font-medium text-slate-300 mb-2">Key Findings:</h5>
                    <ul className="list-disc list-inside space-y-1 text-sm text-slate-400">
                      {result.key_findings.map((finding, fidx) => (
                        <li key={fidx}>{finding}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.synthesis && (
                  <div className="text-sm text-slate-300 whitespace-pre-wrap mt-3">
                    {result.synthesis}
                  </div>
                )}
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  )
}

