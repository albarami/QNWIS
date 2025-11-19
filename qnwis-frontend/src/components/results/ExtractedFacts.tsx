import type { ExtractedFact } from '../../types/workflow'

interface ExtractedFactsProps {
  facts: ExtractedFact[]
}

export function ExtractedFacts({ facts }: ExtractedFactsProps) {
  if (!facts.length) {
    return null
  }

  return (
    <section className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 space-y-3" data-testid="extracted-facts">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Deterministic facts</p>
          <p className="text-sm text-slate-300">Prefetch evidence injected into workflow</p>
        </div>
        <span className="text-xs text-slate-500">{facts.length} facts</span>
      </div>
      <ul className="space-y-2 text-sm text-slate-200">
        {facts.map((fact, index) => (
          <li key={`${fact.metric}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <p className="font-semibold text-white">{fact.metric}</p>
            <p className="text-slate-300">Value: {String(fact.value)}</p>
            <p className="text-xs text-slate-500 mt-1">Source: {fact.source}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
