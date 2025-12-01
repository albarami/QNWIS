import React from 'react'
import { 
  VerdictData, 
  VerdictType,
  getVerdictColor, 
  getRiskColor, 
  getTrendIcon 
} from '../../types/engineB'

interface VerdictCardProps {
  verdict: VerdictData | null
  isLoading?: boolean
  isAnalyzing?: boolean
  analysisProgress?: number
}

// Robustness dots component
const RobustnessDots: React.FC<{ passed: number; total: number }> = ({ passed, total }) => {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={`w-3 h-3 rounded-full ${
            i < passed 
              ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' 
              : 'bg-slate-600'
          }`}
        />
      ))}
    </div>
  )
}

// Success rate bar component
const SuccessRateBar: React.FC<{ rate: number; animate?: boolean }> = ({ rate, animate = true }) => {
  const getBarColor = (rate: number) => {
    if (rate >= 70) return 'from-emerald-500 to-green-400'
    if (rate >= 50) return 'from-amber-500 to-yellow-400'
    if (rate >= 35) return 'from-orange-500 to-amber-400'
    return 'from-red-500 to-rose-400'
  }

  return (
    <div className="w-full">
      <div className="relative h-8 bg-slate-700/50 rounded-full overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 bg-gradient-to-r ${getBarColor(rate)} rounded-full transition-all ${
            animate ? 'duration-1000 ease-out' : ''
          }`}
          style={{ width: `${rate}%` }}
        />
        {/* Percentage text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-black text-white drop-shadow-lg">
            {rate.toFixed(0)}%
          </span>
        </div>
      </div>
    </div>
  )
}

// Verdict badge component
const VerdictBadge: React.FC<{ verdict: VerdictType }> = ({ verdict }) => {
  const labels: Record<VerdictType, string> = {
    APPROVE: 'APPROVE',
    PROCEED_WITH_CAUTION: 'PROCEED WITH CAUTION',
    RECONSIDER: 'RECONSIDER',
    REJECT: 'REJECT',
  }

  return (
    <span
      className={`inline-block px-6 py-2 text-lg font-black tracking-wider text-white bg-gradient-to-r ${getVerdictColor(
        verdict
      )} rounded-xl shadow-lg`}
    >
      {labels[verdict]}
    </span>
  )
}

// Loading skeleton
const VerdictSkeleton: React.FC = () => (
  <div className="animate-pulse">
    <div className="h-6 w-3/4 bg-slate-700 rounded mb-4" />
    <div className="h-8 w-full bg-slate-700 rounded-full mb-6" />
    <div className="grid grid-cols-3 gap-4">
      <div className="h-20 bg-slate-700 rounded-xl" />
      <div className="h-20 bg-slate-700 rounded-xl" />
      <div className="h-20 bg-slate-700 rounded-xl" />
    </div>
  </div>
)

// Analyzing state
const AnalyzingState: React.FC<{ progress: number }> = ({ progress }) => (
  <div className="text-center py-8">
    <div className="inline-flex items-center gap-3 mb-4">
      <span className="text-4xl animate-bounce">🔮</span>
      <span className="text-xl font-semibold text-white">Analyzing Your Question</span>
    </div>
    <div className="max-w-md mx-auto">
      <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="text-sm text-slate-400 mt-2">
        Running Monte Carlo simulations across 6 scenarios...
      </p>
    </div>
  </div>
)

export const VerdictCard: React.FC<VerdictCardProps> = ({
  verdict,
  isLoading = false,
  isAnalyzing = false,
  analysisProgress = 0,
}) => {
  if (isLoading) {
    return (
      <div className="rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 p-8">
        <VerdictSkeleton />
      </div>
    )
  }

  if (isAnalyzing || !verdict) {
    return (
      <div className="rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 p-8">
        <AnalyzingState progress={analysisProgress} />
      </div>
    )
  }

  return (
    <div className="rounded-2xl bg-gradient-to-br from-slate-800 via-slate-900 to-slate-800 border border-slate-600 overflow-hidden shadow-2xl">
      {/* Question Banner */}
      <div className="bg-slate-950/50 px-6 py-4 border-b border-slate-700">
        <p className="text-lg text-slate-200 font-medium leading-relaxed">
          &ldquo;{verdict.question}&rdquo;
        </p>
      </div>

      {/* Main Content */}
      <div className="p-8">
        {/* Success Rate - THE HERO */}
        <div className="mb-8">
          <p className="text-sm uppercase tracking-widest text-slate-400 mb-3 text-center">
            Success Probability
          </p>
          <SuccessRateBar rate={verdict.successRate} />
          <p className="text-xs text-slate-500 mt-2 text-center">
            Based on 10,000 Monte Carlo simulations × {verdict.robustness.total} scenarios
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {/* Robustness */}
          <div className="bg-slate-800/50 rounded-xl p-4 text-center border border-slate-700/50">
            <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">Robustness</p>
            <div className="flex justify-center mb-2">
              <RobustnessDots passed={verdict.robustness.passed} total={verdict.robustness.total} />
            </div>
            <p className="text-lg font-bold text-white">
              {verdict.robustness.passed}/{verdict.robustness.total} pass
            </p>
          </div>

          {/* Confidence */}
          <div className="bg-slate-800/50 rounded-xl p-4 text-center border border-slate-700/50">
            <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">Confidence</p>
            <p className="text-3xl font-bold text-white mb-1">{verdict.confidence}%</p>
            <p className={`text-sm ${getRiskColor(verdict.riskLevel)}`}>
              {verdict.riskLevel.charAt(0).toUpperCase() + verdict.riskLevel.slice(1)} Risk
            </p>
          </div>

          {/* Trend */}
          <div className="bg-slate-800/50 rounded-xl p-4 text-center border border-slate-700/50">
            <p className="text-xs uppercase tracking-wider text-slate-400 mb-2">Trend</p>
            <p className="text-4xl mb-1">{getTrendIcon(verdict.trend)}</p>
            <p className="text-sm text-white capitalize">{verdict.trend}</p>
          </div>
        </div>

        {/* Vulnerabilities Warning */}
        {verdict.robustness.vulnerabilities.length > 0 && (
          <div className="bg-amber-900/20 border border-amber-500/30 rounded-xl p-4 mb-6">
            <div className="flex items-start gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="text-sm font-semibold text-amber-300 mb-1">Vulnerable To</p>
                <p className="text-slate-300 text-sm">
                  {verdict.robustness.vulnerabilities.join(', ')}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Top Driver */}
        <div className="bg-cyan-900/20 border border-cyan-500/30 rounded-xl p-4 mb-6">
          <div className="flex items-start gap-3">
            <span className="text-2xl">🎯</span>
            <div>
              <p className="text-sm font-semibold text-cyan-300 mb-1">Top Success Driver</p>
              <p className="text-slate-300 text-sm">{verdict.topDriver}</p>
            </div>
          </div>
        </div>

        {/* Verdict Badge */}
        <div className="text-center">
          <VerdictBadge verdict={verdict.verdict} />
          {verdict.recommendation && (
            <p className="text-slate-400 text-sm mt-3 max-w-lg mx-auto">
              {verdict.recommendation}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default VerdictCard
