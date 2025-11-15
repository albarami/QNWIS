import type { AgentOutput } from '@/types/workflow'
import { Badge } from '@/components/common/Badge'

interface AgentCardProps {
  agent: AgentOutput
}

export const AgentCard = ({ agent }: AgentCardProps) => (
  <div className="rounded-lg border border-gray-200 p-4 space-y-3">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-semibold text-gray-900">{agent.agent_name}</p>
        <p className="text-xs uppercase text-gray-500">{agent.agent}</p>
      </div>
      <Badge tone="info">{(agent.confidence * 100).toFixed(0)}% confidence</Badge>
    </div>
    <p className="text-sm text-gray-700 whitespace-pre-line">{agent.analysis}</p>
    {agent.key_findings?.length > 0 && (
      <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
        {agent.key_findings.map((finding, idx) => (
          <li key={idx}>{finding}</li>
        ))}
      </ul>
    )}
  </div>
)
