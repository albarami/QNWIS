import React, { useState } from 'react'
import { 
  EngineBScenarioResult, 
  CrossScenarioAnalysis,
  RiskLevel,
  getTrendIcon 
} from '../../types/engineB'

interface CrossScenarioTableProps {
  analysis: CrossScenarioAnalysis | null
  isLoading?: boolean
  onScenarioClick?: (scenario: EngineBScenarioResult) => void
}

// Risk level indicator dots
const RiskDots: React.FC<{ level: RiskLevel | null }> = ({ level }) => {
  if (!level) return <span className="text-slate-500 text-xs">—</span>
  const levels = { low: 1, medium: 2, high: 3, critical: 4 }
  const count = levels[level]
  const colors = {
    low: 'bg-emerald-400',
    medium: 'bg-amber-400',
    high: 'bg-orange-400',
    critical: 'bg-red-400',
  }

  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className={`w-2 h-2 rounded-full ${i <= count ? colors[level] : 'bg-slate-600'}`}
        />
      ))}
    </div>
  )
}

// Success rate bar (inline)
const SuccessBar: React.FC<{ rate: number }> = ({ rate }) => {
  const getColor = (rate: number) => {
    if (rate >= 70) return 'bg-emerald-500'
    if (rate >= 50) return 'bg-amber-500'
    if (rate >= 35) return 'bg-orange-500'
    return 'bg-red-500'
  }

  return (
    <div className="flex items-center gap-3">
      <div className="w-28 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${getColor(rate)} transition-all duration-500`}
          style={{ width: `${rate}%` }}
        />
      </div>
      <span className={`text-sm font-bold ${rate >= 50 ? 'text-emerald-400' : 'text-amber-400'}`}>
        {rate.toFixed(1)}%
      </span>
    </div>
  )
}

// Status badge
const StatusBadge: React.FC<{ isVulnerable: boolean; isRecommended: boolean | null }> = ({
  isVulnerable,
  isRecommended,
}) => {
  if (isRecommended === true) {
    return (
      <span className="px-2 py-0.5 text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded">
        ✓ BEST
      </span>
    )
  }
  if (isVulnerable) {
    return (
      <span className="px-2 py-0.5 text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded">
        ⚠ RISK
      </span>
    )
  }
  return (
    <span className="px-2 py-0.5 text-xs font-bold bg-slate-500/20 text-slate-300 border border-slate-500/30 rounded">
      ✓ PASS
    </span>
  )
}

// Scenario row component
const ScenarioRow: React.FC<{
  scenario: EngineBScenarioResult
  isExpanded: boolean
  onToggle: () => void
}> = ({ scenario, isExpanded, onToggle }) => {
  return (
    <div 
      className={`border-b border-slate-700/50 transition-colors ${
        isExpanded ? 'bg-slate-800/50' : 'hover:bg-slate-800/30'
      }`}
    >
      {/* Main row */}
      <div 
        className="grid grid-cols-12 gap-4 px-4 py-4 cursor-pointer"
        onClick={onToggle}
      >
        {/* Scenario name */}
        <div className="col-span-4 flex items-center gap-3">
          <span className="text-2xl">{scenario.scenarioIcon}</span>
          <div>
            <p className="font-medium text-white">{scenario.scenarioName}</p>
            <p className="text-xs text-slate-500 line-clamp-1">{scenario.description}</p>
          </div>
        </div>

        {/* Success Rate */}
        <div className="col-span-3 flex items-center">
          {scenario.monteCarlo ? (
            <SuccessBar rate={scenario.monteCarlo.successRate * 100} />
          ) : (
            <span className="text-slate-500 text-sm">Awaiting Engine B...</span>
          )}
        </div>

        {/* Risk Level */}
        <div className="col-span-2 flex items-center gap-2">
          <RiskDots level={scenario.riskLevel} />
          <span className="text-xs text-slate-400 uppercase">{scenario.riskLevel || '—'}</span>
        </div>

        {/* Trend */}
        <div className="col-span-1 flex items-center justify-center">
          {scenario.forecast ? (
            <span className={`text-xl ${
              scenario.forecast.trend === 'increasing' ? 'text-emerald-400' :
              scenario.forecast.trend === 'decreasing' ? 'text-red-400' :
              'text-slate-400'
            }`}>
              {getTrendIcon(scenario.forecast.trend)}
            </span>
          ) : (
            <span className="text-slate-500">—</span>
          )}
        </div>

        {/* Status */}
        <div className="col-span-2 flex items-center justify-end">
          <StatusBadge 
            isVulnerable={scenario.isVulnerable} 
            isRecommended={scenario.isRecommended} 
          />
        </div>
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-700/30">
          <div className="grid grid-cols-3 gap-4">
            {/* Assumptions */}
            <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50">
              <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">Assumptions</p>
              {scenario.assumptions ? (
                <div className="space-y-1">
                  {Object.entries(scenario.assumptions).slice(0, 3).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-slate-400">{key.replace(/_/g, ' ')}</span>
                      <span className="text-white font-mono">{(value as number).toFixed(1)}×</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 text-sm">Awaiting data...</p>
              )}
            </div>

            {/* Monte Carlo */}
            <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50">
              <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">Monte Carlo</p>
              {scenario.monteCarlo ? (
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Simulations</span>
                    <span className="text-white">{scenario.monteCarlo.simulations?.toLocaleString() || '—'}</span>
                  </div>
                  {scenario.monteCarlo.confidenceInterval && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">95% CI</span>
                      <span className="text-white">
                        {(scenario.monteCarlo.confidenceInterval[0] * 100).toFixed(0)}% - {(scenario.monteCarlo.confidenceInterval[1] * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-slate-500 text-sm">Awaiting Engine B...</p>
              )}
            </div>

            {/* Top Drivers */}
            <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50">
              <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">Top Driver</p>
              {scenario.sensitivity && scenario.sensitivity[0] ? (
                <div className="space-y-1">
                  <p className="text-sm text-white">{scenario.sensitivity[0].label}</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-cyan-500 rounded-full"
                        style={{ width: `${scenario.sensitivity[0].contribution * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-cyan-400 font-bold">
                      {(scenario.sensitivity[0].contribution * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-slate-500 text-sm">Awaiting sensitivity analysis...</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Robustness summary card
const RobustnessSummary: React.FC<{ analysis: CrossScenarioAnalysis }> = ({ analysis }) => {
  const { robustness, bestCase, worstCase } = analysis

  return (
    <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 mt-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Robustness dots */}
          <div className="flex items-center gap-1">
            {Array.from({ length: robustness.totalCount }).map((_, i) => (
              <span
                key={i}
                className={`w-4 h-4 rounded-full ${
                  i < robustness.passedCount 
                    ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' 
                    : 'bg-slate-600'
                }`}
              />
            ))}
          </div>
          <div>
            <p className="text-white font-semibold">
              Policy succeeds in {robustness.passedCount}/{robustness.totalCount} scenarios
            </p>
            <p className="text-xs text-slate-400">
              (&gt;{(robustness.threshold * 100).toFixed(0)}% success rate threshold)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Best case */}
          {bestCase && (
            <div className="text-right">
              <p className="text-xs text-slate-400">Best Case</p>
              <p className="text-sm text-emerald-400 font-semibold">
                {bestCase.icon} {bestCase.scenarioName} {bestCase.successRate != null ? `(${(bestCase.successRate * 100).toFixed(0)}%)` : ''}
              </p>
            </div>
          )}

          {/* Worst case */}
          {worstCase && (
            <div className="text-right">
              <p className="text-xs text-slate-400">Worst Case</p>
              <p className="text-sm text-red-400 font-semibold">
                {worstCase.icon} {worstCase.scenarioName} {worstCase.successRate != null ? `(${(worstCase.successRate * 100).toFixed(0)}%)` : ''}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Loading skeleton
const TableSkeleton: React.FC = () => (
  <div className="animate-pulse space-y-3">
    {[1, 2, 3, 4, 5, 6].map((i) => (
      <div key={i} className="h-16 bg-slate-800/50 rounded-lg" />
    ))}
  </div>
)

export const CrossScenarioTable: React.FC<CrossScenarioTableProps> = ({
  analysis,
  isLoading = false,
  onScenarioClick,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="rounded-2xl bg-slate-900/60 border border-slate-700 p-6">
        <div className="h-8 w-64 bg-slate-700 rounded mb-4 animate-pulse" />
        <TableSkeleton />
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="rounded-2xl bg-slate-900/60 border border-slate-700 p-8 text-center">
        <span className="text-4xl mb-4 block">📊</span>
        <p className="text-slate-400">Cross-scenario analysis will appear here</p>
        <p className="text-sm text-slate-500 mt-1">
          Engine B computes success rates across 6 possible futures
        </p>
      </div>
    )
  }

  // FIX RUN 7: Group scenarios by strategic option
  const aiKeywords = ['ai', 'tech', 'digital', 'automation', 'policy', 'base case', 'competitive', 'shock', 'disruption', 'gradual', 'acceleration']
  const tourismKeywords = ['tourism', 'sustainable', 'destination', 'hospitality', 'travel']
  
  const aiScenarios = analysis.scenarios.filter(s => 
    aiKeywords.some(kw => (s.scenarioName || '').toLowerCase().includes(kw)) &&
    !tourismKeywords.some(kw => (s.scenarioName || '').toLowerCase().includes(kw))
  )
  const tourismScenarios = analysis.scenarios.filter(s => 
    tourismKeywords.some(kw => (s.scenarioName || '').toLowerCase().includes(kw))
  )
  const otherScenarios = analysis.scenarios.filter(s => 
    !aiScenarios.includes(s) && !tourismScenarios.includes(s)
  )
  
  // Calculate option-level metrics
  const calcOptionMetrics = (scenarios: typeof analysis.scenarios) => {
    if (scenarios.length === 0) return null
    const rates = scenarios.map(s => s.monteCarlo?.successRate || 0)
    const avg = rates.reduce((a, b) => a + b, 0) / rates.length
    const passed = scenarios.filter(s => (s.monteCarlo?.successRate || 0) > 0.5).length
    const best = Math.max(...rates)
    const worst = Math.min(...rates)
    return { avg, passed, total: scenarios.length, best, worst }
  }
  
  const aiMetrics = calcOptionMetrics(aiScenarios)
  const tourismMetrics = calcOptionMetrics(tourismScenarios)
  
  return (
    <div className="rounded-2xl bg-slate-900/60 border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-slate-800/50 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <span>📊</span> Cross-Scenario Analysis
            </h3>
            <p className="text-sm text-slate-400">
              How does each strategic option perform across different futures?
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-white">
              {(analysis.overallSuccessRate * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-slate-400">overall success</p>
          </div>
        </div>
      </div>

      {/* FIX RUN 7: Option Comparison Summary */}
      {(aiMetrics || tourismMetrics) && (
        <div className="px-4 py-3 border-b border-slate-700/50 bg-gradient-to-r from-slate-800/30 to-slate-800/10">
          <div className="grid grid-cols-2 gap-4">
            {/* AI Hub Option */}
            {aiMetrics && (
              <div className="bg-cyan-900/20 border border-cyan-500/30 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">🤖</span>
                  <span className="text-sm font-bold text-cyan-300">AI & Technology Hub</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <p className="text-slate-400">Average</p>
                    <p className="text-white font-bold">{(aiMetrics.avg * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Robustness</p>
                    <p className="text-emerald-400 font-bold">{aiMetrics.passed}/{aiMetrics.total} pass</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Range</p>
                    <p className="text-slate-300">{(aiMetrics.worst * 100).toFixed(0)}% - {(aiMetrics.best * 100).toFixed(0)}%</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Tourism Option */}
            {tourismMetrics && (
              <div className="bg-amber-900/20 border border-amber-500/30 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">🏖️</span>
                  <span className="text-sm font-bold text-amber-300">Sustainable Tourism</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <p className="text-slate-400">Average</p>
                    <p className="text-white font-bold">{(tourismMetrics.avg * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Robustness</p>
                    <p className="text-emerald-400 font-bold">{tourismMetrics.passed}/{tourismMetrics.total} pass</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Scenarios</p>
                    <p className="text-slate-300">{tourismMetrics.total} tested</p>
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* Risk-adjusted recommendation note */}
          {aiMetrics && tourismMetrics && aiMetrics.total > tourismMetrics.total && (
            <p className="text-xs text-slate-400 mt-2 italic">
              💡 AI Hub is tested across {aiMetrics.total} scenarios vs Tourism's {tourismMetrics.total} — more robust stress-testing.
            </p>
          )}
        </div>
      )}

      {/* Table header */}
      <div className="grid grid-cols-12 gap-4 px-4 py-3 bg-slate-800/30 text-xs uppercase tracking-wider text-slate-400">
        <div className="col-span-4">Scenario</div>
        <div className="col-span-3">Success Rate</div>
        <div className="col-span-2">Risk</div>
        <div className="col-span-1 text-center">Trend</div>
        <div className="col-span-2 text-right">Status</div>
      </div>

      {/* Table body - grouped by option */}
      <div className="divide-y divide-slate-700/30">
        {/* AI Hub scenarios */}
        {aiScenarios.length > 0 && (
          <>
            <div className="px-4 py-2 bg-cyan-900/10 border-l-4 border-cyan-500">
              <span className="text-xs font-semibold text-cyan-400">🤖 AI & Technology Hub Path</span>
            </div>
            {aiScenarios.map((scenario) => (
              <ScenarioRow
                key={scenario.scenarioId}
                scenario={scenario}
                isExpanded={expandedId === scenario.scenarioId}
                onToggle={() => {
                  setExpandedId(expandedId === scenario.scenarioId ? null : scenario.scenarioId)
                  onScenarioClick?.(scenario)
                }}
              />
            ))}
          </>
        )}
        
        {/* Tourism scenarios */}
        {tourismScenarios.length > 0 && (
          <>
            <div className="px-4 py-2 bg-amber-900/10 border-l-4 border-amber-500">
              <span className="text-xs font-semibold text-amber-400">🏖️ Sustainable Tourism Path</span>
            </div>
            {tourismScenarios.map((scenario) => (
              <ScenarioRow
                key={scenario.scenarioId}
                scenario={scenario}
                isExpanded={expandedId === scenario.scenarioId}
                onToggle={() => {
                  setExpandedId(expandedId === scenario.scenarioId ? null : scenario.scenarioId)
                  onScenarioClick?.(scenario)
                }}
              />
            ))}
          </>
        )}
        
        {/* Other scenarios */}
        {otherScenarios.length > 0 && otherScenarios.map((scenario) => (
          <ScenarioRow
            key={scenario.scenarioId}
            scenario={scenario}
            isExpanded={expandedId === scenario.scenarioId}
            onToggle={() => {
              setExpandedId(expandedId === scenario.scenarioId ? null : scenario.scenarioId)
              onScenarioClick?.(scenario)
            }}
          />
        ))}
      </div>

      {/* Robustness summary */}
      <div className="px-4 pb-4">
        <RobustnessSummary analysis={analysis} />
      </div>
    </div>
  )
}

export default CrossScenarioTable
