import type { AgentOutput } from '@/types/workflow'
import { Card } from '@/components/common/Card'
import { AgentCard } from './AgentCard'

interface AgentsPanelProps {
  agents?: AgentOutput[]
}

export const AgentsPanel = ({ agents }: AgentsPanelProps) => {
  if (!agents || agents.length === 0) return null

  return (
    <Card
      title="Agent Findings"
      subtitle="Specialized agents contributing to the briefing"
      className="space-y-4"
    >
      <div className="grid gap-4 md:grid-cols-2">
        {agents.map((agent) => (
          <AgentCard key={agent.agent_name} agent={agent} />
        ))}
      </div>
    </Card>
  )
}
