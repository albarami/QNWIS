import type { AgentOutput } from '@/types/workflow'
import { Card } from '@/components/common/Card'

interface ConfidenceBreakdownCardProps {
  agentOutputs: AgentOutput[]
  overallConfidence?: number
}

export const ConfidenceBreakdownCard = ({ agentOutputs, overallConfidence }: ConfidenceBreakdownCardProps) => {
  if (!agentOutputs || agentOutputs.length === 0) {
    return (
      <Card title="Confidence Profile">
        <p className="text-sm text-gray-500">Confidence metrics appear once the council returns agent reports.</p>
      </Card>
    )
  }

  return (
    <Card
      title="Confidence Profile"
      subtitle="Agent certainty across the council"
      className="space-y-4"
    >
      {overallConfidence !== undefined && (
        <div className="rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3">
          <p className="text-xs uppercase text-indigo-600">Overall consensus</p>
          <p className="text-3xl font-bold text-indigo-800">{Math.round(overallConfidence * 100)}%</p>
        </div>
      )}

      <div className="space-y-3">
        {agentOutputs.map((agent) => (
          <div key={agent.agent_name} className="rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-900">{agent.agent_name}</p>
                <p className="text-xs uppercase text-gray-500">{agent.agent}</p>
              </div>
              <p className="text-sm font-semibold text-gray-700">
                {(agent.confidence * 100).toFixed(0)}%
              </p>
            </div>
            <div className="mt-2 h-2 w-full rounded bg-gray-100">
              <div
                className="h-2 rounded bg-gradient-to-r from-indigo-500 to-purple-500"
                style={{ width: `${Math.min(100, Math.max(0, agent.confidence * 100))}%` }}
              />
            </div>
            {agent.warnings && agent.warnings.length > 0 && (
              <p className="mt-2 text-xs text-red-600">
                ⚠️ {agent.warnings[0]}
              </p>
            )}
          </div>
        ))}
      </div>
    </Card>
  )
}
