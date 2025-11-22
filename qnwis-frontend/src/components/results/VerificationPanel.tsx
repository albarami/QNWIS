import type { VerificationResult } from '../../types/workflow'

interface VerificationPanelProps {
  verification: VerificationResult | null
}

export function VerificationPanel({ verification }: VerificationPanelProps) {
  if (!verification) {
    return null
  }

  return (
    <section className="rounded-2xl border border-emerald-400/30 bg-slate-900/40 p-6 space-y-4" data-testid="verification-panel">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-emerald-200">Verification & QA</p>
          <p className="text-sm text-emerald-100">
            {verification.warning_count} warnings · {verification.error_count} errors · {verification.missing_citations} missing citations
          </p>
        </div>
      </div>

      {verification.citation_violations && verification.citation_violations.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Citation Issues</p>
          <ul className="space-y-2 text-sm text-slate-200">
            {verification.citation_violations.map((issue, index) => (
              <li key={`${issue.agent}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                <p className="font-semibold">{issue.agent}</p>
                <p className="text-slate-300 text-sm">{issue.issue}</p>
                <p className="text-xs text-slate-500 mt-1">{issue.narrative_snippet}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
