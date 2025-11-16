import type { ReactNode } from 'react'
import { Card } from '@/components/common/Card'

interface ExecutiveSummaryCardProps {
  synthesis?: string
  confidence?: number
  status?: 'idle' | 'running' | 'complete' | 'error'
}

interface SummarySections {
  keyFinding?: string
  disagreement?: string
  devilAdvocate?: string
  recommendation?: string
  decision?: string
}

const confidenceTone = (value?: number) => {
  if (value === undefined || Number.isNaN(value)) return 'text-gray-500'
  if (value >= 0.7) return 'text-green-600'
  if (value >= 0.4) return 'text-yellow-600'
  return 'text-red-600'
}

const parseSynthesisSections = (synthesis: string): SummarySections => {
  const extract = (label: string) => {
    const regex = new RegExp(`\*\*${label}:\*\*\s*([^\n]+)`, 'i')
    const match = synthesis.match(regex)
    return match ? match[1].trim() : undefined
  }

  return {
    keyFinding: extract('Key Finding'),
    disagreement: extract('Critical Disagreement'),
    devilAdvocate: extract("Devil's Advocate Warning"),
    recommendation: extract('Recommendation'),
    decision: extract('Go/No-Go Decision'),
  }
}

const Section = ({ icon, title, children, variant }: { icon: string; title: string; children: ReactNode; variant?: 'warning' | 'danger' | 'info' }) => {
  const variantClasses = {
    warning: 'bg-orange-50 border-orange-300 text-orange-900',
    danger: 'bg-red-50 border-red-300 text-red-900',
    info: 'bg-blue-50 border-blue-200 text-blue-900',
  } as const

  return (
    <div className={`rounded-lg border px-4 py-3 ${variant ? variantClasses[variant] : 'bg-white border-gray-200 text-gray-900'}`}>
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide">
        <span>{icon}</span>
        {title}
      </h3>
      <p className="whitespace-pre-line text-gray-800">{children}</p>
    </div>
  )
}

export const ExecutiveSummaryCard = ({ synthesis, confidence, status }: ExecutiveSummaryCardProps) => {
  const isLoading = !synthesis && status === 'running'
  const sections = synthesis ? parseSynthesisSections(synthesis) : {}

  return (
    <Card
      title="Ministerial Brief"
      subtitle="Executive decision summary"
      className="space-y-4 bg-gradient-to-br from-blue-50 to-indigo-50 border border-indigo-100"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase text-indigo-600">Overall confidence</p>
          <p className={`text-3xl font-bold ${confidenceTone(confidence)}`}>
            {confidence !== undefined ? `${Math.round(confidence * 100)}%` : '—'}
          </p>
        </div>
        <span className="text-3xl" role="img" aria-label="brief">
          📋
        </span>
      </div>

      {isLoading && (
        <div className="space-y-3">
          <div className="h-4 animate-pulse rounded bg-indigo-100" />
          <div className="h-4 animate-pulse rounded bg-indigo-100" />
          <div className="h-4 animate-pulse rounded bg-indigo-100" />
        </div>
      )}

      {!isLoading && synthesis && (
        <div className="space-y-3">
          {sections.keyFinding && (
            <Section icon="🎯" title="Key Finding">
              {sections.keyFinding}
            </Section>
          )}

          {sections.disagreement && (
            <Section icon="⚖️" title="Critical Disagreement" variant="warning">
              {sections.disagreement}
            </Section>
          )}

          {sections.devilAdvocate && (
            <Section icon="😈" title="Devil's Advocate" variant="danger">
              {sections.devilAdvocate}
            </Section>
          )}

          {sections.recommendation && (
            <Section icon="💡" title="Recommendation" variant="info">
              {sections.recommendation}
            </Section>
          )}

          {sections.decision && (
            <div
              className={`rounded-lg border-2 px-4 py-3 text-center text-xl font-bold ${
                sections.decision.toLowerCase().includes('no')
                  ? 'border-red-300 bg-red-50 text-red-800'
                  : 'border-green-300 bg-green-50 text-green-800'
              }`}
            >
              {sections.decision}
            </div>
          )}
        </div>
      )}

      {!isLoading && !synthesis && (
        <p className="text-sm text-gray-600">Executive summary will appear once the council completes synthesis.</p>
      )}
    </Card>
  )
}
