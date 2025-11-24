import type { AgentStatus } from '../../types/workflow'
import { AgentCard } from './AgentCard'

interface AgentGridProps {
  agents: Map<string, AgentStatus>
  agentsExpected?: number
  agentsRunning?: boolean
}

export function AgentGrid({ agents, agentsExpected = 0, agentsRunning = false }: AgentGridProps) {
  const items = Array.from(agents.values())
  const completedCount = items.filter(a => a.status === 'complete').length
  const runningCount = items.filter(a => a.status === 'running').length

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 space-y-4" data-testid="agent-grid">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Agent Execution</p>
          <p className="text-sm text-slate-300">
            {runningCount > 0 ? (
              <span className="text-cyan-400">{runningCount} running</span>
            ) : completedCount > 0 ? (
              <span className="text-emerald-400">{completedCount} complete</span>
            ) : agentsRunning ? (
              <span className="text-yellow-400">Initializing agents...</span>
            ) : (
              'Live status of all selected agents'
            )}
          </p>
        </div>
        <span className="text-xs text-slate-500">
          {items.length > 0 ? `${completedCount}/${items.length}` : agentsExpected > 0 ? `0/${agentsExpected}` : '0'} agents
        </span>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center text-slate-400">
          {agentsRunning || agentsExpected > 0 ? (
            <div className="flex flex-col items-center gap-2">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
                <span>Preparing {agentsExpected} agents for analysis...</span>
              </div>
              <p className="text-xs text-slate-500">Agent reports will appear as they complete</p>
            </div>
          ) : (
            'Agents will appear here once selection completes.'
          )}
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
