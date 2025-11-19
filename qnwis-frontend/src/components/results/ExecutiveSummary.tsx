interface ExecutiveSummaryProps {
  synthesis: string
}

export function ExecutiveSummary({ synthesis }: ExecutiveSummaryProps) {
  if (!synthesis) {
    return null
  }

  return (
    <section className="rounded-2xl border border-amber-400/30 bg-slate-900/40 p-6" data-testid="executive-summary">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-amber-200">Ministerial synthesis</p>
          <p className="text-sm text-amber-100">Live report drafted by synthesis stage</p>
        </div>
        <span className="text-xs text-amber-200">Streaming</span>
      </div>
      <p className="whitespace-pre-wrap text-slate-100 leading-relaxed">{synthesis}</p>
    </section>
  )
}
