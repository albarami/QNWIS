import type { DebateResults } from '../../types/workflow'

interface DebatePanelProps {
  debate: DebateResults | null
}

export function DebatePanel({ debate }: DebatePanelProps) {
  if (!debate) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 text-slate-400" data-testid="debate-panel">
        Debate telemetry will appear here once contradictions are detected.
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-purple-400/40 bg-slate-900/50 p-6 space-y-4" data-testid="debate-panel">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-purple-300">Multi-agent debate</p>
          <p className="text-sm text-slate-300">
            {debate.contradictions_found} contradictions · {debate.resolved} resolved · {debate.flagged_for_review} flagged
          </p>
        </div>
        <span className="text-xs text-slate-500">{(debate.latency_ms / 1000).toFixed(1)}s</span>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200 whitespace-pre-wrap">
        {debate.consensus_narrative}
      </div>

      {debate.contradictions?.length ? (
        <div className="space-y-3">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Active contradictions</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {debate.contradictions.map((item, index) => (
              <div key={`${item.metric_name}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-xs text-slate-200">
                <p className="font-semibold text-sm text-white">{item.metric_name}</p>
                <p className="mt-1">{item.agent1_name}: {item.agent1_value_str}</p>
                <p>{item.agent2_name}: {item.agent2_value_str}</p>
                <p className="text-slate-400 mt-1">Severity: {item.severity}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
