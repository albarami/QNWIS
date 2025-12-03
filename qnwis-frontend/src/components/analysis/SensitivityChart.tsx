import React from 'react'
import { SensitivityDriver } from '../../types/engineB'

interface SensitivityChartProps {
  drivers: SensitivityDriver[] | null  // null until Engine B provides data
  title?: string
  showInsight?: boolean
}

// Single bar in the tornado chart
const TornadoBar: React.FC<{
  driver: SensitivityDriver
  maxContribution: number
}> = ({ driver, maxContribution }) => {
  const widthPercent = (driver.contribution / maxContribution) * 100
  
  const getColor = (direction: 'positive' | 'negative' | 'mixed') => {
    switch (direction) {
      case 'positive':
        return 'from-cyan-500 to-cyan-400'
      case 'negative':
        return 'from-rose-500 to-rose-400'
      case 'mixed':
        return 'from-purple-500 to-purple-400'
    }
  }

  return (
    <div className="flex items-center gap-4">
      {/* Label */}
      <div className="w-40 text-right">
        <span className="text-sm text-slate-300">{driver.label}</span>
      </div>

      {/* Bar */}
      <div className="flex-1 flex items-center">
        <div className="w-full h-6 bg-slate-800 rounded-full overflow-hidden relative">
          <div
            className={`absolute inset-y-0 left-0 bg-gradient-to-r ${getColor(driver.direction)} rounded-full transition-all duration-700`}
            style={{ width: `${widthPercent}%` }}
          />
        </div>
      </div>

      {/* Percentage */}
      <div className="w-16 text-right">
        <span className="text-sm font-bold text-cyan-400">
          {(driver.contribution * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  )
}

export const SensitivityChart: React.FC<SensitivityChartProps> = ({
  drivers,
  title = "What Drives Success?",
  showInsight = true,
}) => {
  // Show waiting state until Engine B provides real data - NO FAKE DATA
  if (!drivers || drivers.length === 0) {
    return (
      <div className="rounded-xl bg-slate-900/50 border border-slate-700 p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">📈</span>
          <div>
            <h3 className="font-semibold text-white">{title}</h3>
            <p className="text-sm text-slate-500">Sensitivity Analysis</p>
          </div>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-slate-400 text-sm">Waiting for Engine B analysis...</p>
            <p className="text-slate-500 text-xs mt-1">Monte Carlo simulations in progress</p>
          </div>
        </div>
      </div>
    )
  }

  // Sort by contribution and take top 5
  const topDrivers = [...drivers]
    .sort((a, b) => b.contribution - a.contribution)
    .slice(0, 5)

  const maxContribution = topDrivers[0]?.contribution || 1

  // Generate insight
  const topDriver = topDrivers[0]
  const secondDriver = topDrivers[1]
  const ratio = topDriver && secondDriver 
    ? (topDriver.contribution / secondDriver.contribution).toFixed(1) 
    : null

  return (
    <div className="rounded-xl bg-slate-900/50 border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-slate-800/30 border-b border-slate-700">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <span>📈</span> {title}
        </h3>
        <p className="text-sm text-slate-400">
          Sensitivity analysis: Top factors affecting outcome
        </p>
      </div>

      {/* Chart */}
      <div className="p-6 space-y-3">
        {topDrivers.map((driver) => (
          <TornadoBar
            key={driver.driver}
            driver={driver}
            maxContribution={maxContribution}
          />
        ))}
      </div>

      {/* Insight */}
      {showInsight && topDriver && ratio && (
        <div className="px-6 pb-6">
          <div className="bg-cyan-900/20 border border-cyan-500/30 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <span className="text-xl">💡</span>
              <p className="text-sm text-slate-300">
                <strong className="text-cyan-300">Insight:</strong> Improving{' '}
                <span className="text-white font-medium">{topDriver.label.toLowerCase()}</span> has{' '}
                <span className="text-cyan-400 font-bold">{ratio}×</span> more impact than any other intervention.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SensitivityChart
