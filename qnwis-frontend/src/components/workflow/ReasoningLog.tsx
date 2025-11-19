interface ReasoningLogProps {
  chain: string[]
}

export function ReasoningLog({ chain }: ReasoningLogProps) {
  if (!chain.length) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 text-slate-400">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Reasoning Chain</p>
        <p className="mt-2 text-sm">Waiting for cognitive steps...</p>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-400">Cognitive Trail</p>
          <p className="text-sm text-slate-300">Step-by-step reasoning logic</p>
        </div>
        <span className="text-xs text-slate-500">{chain.length} steps</span>
      </div>
      
      <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 h-48 overflow-y-auto font-mono text-xs text-slate-300 space-y-2">
        {chain.map((step, i) => (
          <div key={i} className="flex gap-3">
            <span className="text-slate-600 select-none">{(i + 1).toString().padStart(2, '0')}</span>
            <span>{step}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
