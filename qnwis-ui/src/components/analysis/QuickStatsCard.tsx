import type { WorkflowState } from '@/types/workflow'
import { Card } from '@/components/common/Card'

interface QuickStatsCardProps {
  state: WorkflowState
}

const formatCost = (value?: number) => {
  if (value === undefined) return '—'
  if (value < 1) return `$${value.toFixed(2)}`
  return `$${value.toFixed(1)}`
}

const formatTime = (value?: number) => {
  if (!value) return '—'
  return `${(value / 1000).toFixed(1)}s`
}

export const QuickStatsCard = ({ state }: QuickStatsCardProps) => {
  const agentCount = state.agents_invoked?.length ?? state.agent_outputs?.length ?? 0
  const avgConfidence = state.agent_outputs?.length
    ? state.agent_outputs.reduce((sum, agent) => sum + agent.confidence, 0) / state.agent_outputs.length
    : undefined

  return (
    <Card title="Mission Telemetry" subtitle="Key indicators from the council">
      <div className="grid grid-cols-2 gap-4">
        <StatBox label="Agents" icon="🤖" value={`${agentCount}/5`} accent="from-indigo-500 to-purple-500" />
        <StatBox
          label="Facts"
          icon="📊"
          value={state.extracted_facts?.length ?? 0}
          accent="from-blue-500 to-cyan-500"
        />
        <StatBox label="Cost" icon="💰" value={formatCost(state.cost_usd)} accent="from-emerald-500 to-lime-500" />
        <StatBox
          label="Runtime"
          icon="⏱️"
          value={formatTime(state.execution_time_ms)}
          accent="from-rose-500 to-orange-500"
        />
        <StatBox
          label="LLM Calls"
          icon="🧠"
          value={state.llm_calls ?? '—'}
          accent="from-slate-500 to-gray-500"
        />
        <StatBox
          label="Avg Confidence"
          icon="🎯"
          value={
            avgConfidence !== undefined ? `${Math.round(avgConfidence * 100)}%` : '—'
          }
          accent="from-amber-500 to-yellow-500"
        />
      </div>
    </Card>
  )
}

const StatBox = ({ label, icon, value, accent }: { label: string; icon: string; value: string | number; accent: string }) => (
  <div className={`rounded-xl border border-gray-100 bg-gradient-to-br ${accent} p-4 text-white shadow`}>
    <div className="flex items-center justify-between">
      <span className="text-2xl" role="img" aria-hidden>
        {icon}
      </span>
      <span className="text-xs uppercase tracking-wide">{label}</span>
    </div>
    <p className="mt-3 text-2xl font-bold">{value}</p>
  </div>
)
