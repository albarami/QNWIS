import type { AgentStatus } from '../../types/workflow'

interface AgentCardProps {
  agent: AgentStatus
}

const statusStyles: Record<AgentStatus['status'], { pill: string; text: string }> = {
  pending: {
    pill: 'bg-slate-700/60 text-slate-200 border-slate-600',
    text: 'Awaiting execution',
  },
  running: {
    pill: 'bg-cyan-500/20 text-cyan-200 border-cyan-400 animate-pulse',
    text: 'Running agent playbook',
  },
  complete: {
    pill: 'bg-emerald-500/20 text-emerald-200 border-emerald-400',
    text: 'Agent execution complete',
  },
  error: {
    pill: 'bg-red-500/20 text-red-200 border-red-400',
    text: 'Agent failed - see errors',
  },
}

export function AgentCard({ agent }: AgentCardProps) {
  const styles = statusStyles[agent.status]

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/50 p-4 space-y-3" data-testid={`agent-${agent.name}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Agent</p>
          <p className="text-xl font-semibold text-white">{agent.name}</p>
        </div>
        <span className={`text-xs font-semibold px-3 py-1 rounded-full border ${styles.pill}`}>
          {agent.status}
        </span>
      </div>

      <p className="text-sm text-slate-300">{styles.text}</p>

      {agent.report?.narrative && (
        <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3 text-sm text-slate-200 max-h-48 overflow-y-auto">
          <p className="font-semibold text-cyan-300 text-xs mb-2">Agent Analysis:</p>
          <p className="whitespace-pre-wrap">{agent.report.narrative}</p>
        </div>
      )}

      {agent.error && (
        <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
          <p className="font-semibold text-xs mb-1">Error:</p>
          <p className="text-xs">{agent.error}</p>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Latency: {agent.latency_ms ? `${agent.latency_ms.toFixed(0)} ms` : '—'}</span>
        <span>{agent.report?.confidence ? `Confidence ${Math.round(agent.report.confidence * 100)}%` : ''}</span>
      </div>
    </div>
  )
}
