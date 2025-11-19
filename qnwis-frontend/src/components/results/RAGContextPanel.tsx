import type { RAGContext } from '../../types/workflow'

interface RAGContextPanelProps {
  context: RAGContext | null
}

export function RAGContextPanel({ context }: RAGContextPanelProps) {
  if (!context || context.sources.length === 0) {
    return null
  }

  return (
    <section className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 space-y-3" data-testid="rag-context">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-emerald-400">Knowledge Base</p>
          <p className="text-sm text-slate-300">Retrieved documents for context</p>
        </div>
        <span className="text-xs text-slate-500">{context.snippets_retrieved} snippets</span>
      </div>
      <ul className="space-y-2 text-sm text-slate-200">
        {context.sources.map((source, index) => (
          <li key={`${source}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 flex items-start gap-2">
            <span className="text-emerald-500 mt-0.5">📄</span>
            <span className="text-slate-300 break-all">{source}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
