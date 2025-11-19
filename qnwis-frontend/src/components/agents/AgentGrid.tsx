import type { AgentStatus } from '../../types/workflow'
import { AgentCard } from './AgentCard'

interface AgentGridProps {
  agents: Map<string, AgentStatus>
}

export function AgentGrid({ agents }: AgentGridProps) {
  const items = Array.from(agents.values())

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 space-y-4" data-testid="agent-grid">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Agent Execution</p>
          <p className="text-sm text-slate-300">Live status of all selected agents</p>
        </div>
        <span className="text-xs text-slate-500">{items.length} agents</span>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center text-slate-400">
          Agents will appear here once selection completes.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      )}
    </div>
  )
}
