import type { CritiqueResults } from '../../types/workflow'

interface CritiquePanelProps {
  critique: CritiqueResults | null
}

export function CritiquePanel({ critique }: CritiquePanelProps) {
  if (!critique) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 text-slate-400" data-testid="critique-panel">
        Critique telemetry will appear here once devil&apos;s advocate stage runs.
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-red-400/40 bg-slate-900/50 p-6 space-y-4" data-testid="critique-panel">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-red-300">Devil&apos;s advocate critique</p>
          <p className="text-sm text-slate-300">
            {critique.critiques.length} critiques · {critique.red_flags.length} red flags
          </p>
        </div>
        <span className="text-xs text-slate-500">{(critique.latency_ms / 1000).toFixed(1)}s</span>
      </div>

      {critique.red_flags.length > 0 && (
        <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-100">
          <p className="uppercase tracking-[0.2em] text-xs font-semibold">Red Flags</p>
          <ul className="mt-2 space-y-1 list-disc list-inside">
            {critique.red_flags.map((flag, index) => (
              <li key={`${flag}-${index}`}>{flag}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {critique.critiques.map((item, index) => (
          <div key={`${item.agent_name}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-white">{item.agent_name}</p>
              <span className="text-xs text-slate-400">Severity: {item.severity}</span>
            </div>
            <p className="text-slate-300">Weakness: {item.weakness_found}</p>
            <p className="text-slate-400 text-xs">Counter: {item.counter_argument}</p>
            <p className="text-xs text-slate-500">Robustness: {(item.robustness_score * 100).toFixed(0)}%</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-200">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Overall assessment</p>
        <p className="mt-2 text-slate-100">{critique.overall_assessment}</p>
        <p className="text-xs text-slate-500 mt-1">
          Strengthened by critique: {critique.strengthened_by_critique ? 'Yes' : 'No'}
        </p>
      </div>
    </div>
  )
}
