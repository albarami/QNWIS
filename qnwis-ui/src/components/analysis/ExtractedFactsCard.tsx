import type { ExtractedFact } from '@/types/workflow'
import { Card } from '@/components/common/Card'

interface ExtractedFactsCardProps {
  facts?: ExtractedFact[]
}

export const ExtractedFactsCard = ({ facts }: ExtractedFactsCardProps) => {
  if (!facts || facts.length === 0) {
    return (
      <Card title="Extracted Facts">
        <p className="text-sm text-gray-500">No ministerial-grade facts detected yet.</p>
      </Card>
    )
  }

  return (
    <Card title="Extracted Facts" subtitle="Validated signals powering the council">
      <div className="grid gap-4 md:grid-cols-2">
        {facts.map((fact, idx) => (
          <article
            key={`${fact.metric}-${idx}`}
            className="rounded-lg border border-gray-200 p-4 shadow-sm"
          >
            <p className="text-xs uppercase tracking-wide text-gray-500">{fact.metric}</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">
              {typeof fact.value === 'number' ? fact.value.toLocaleString() : String(fact.value)}
            </p>
            <p className="mt-2 text-xs text-gray-500">
              {fact.source} • Confidence {(fact.confidence * 100).toFixed(0)}%
            </p>
          </article>
        ))}
      </div>
    </Card>
  )
}
