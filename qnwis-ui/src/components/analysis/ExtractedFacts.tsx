import type { ExtractedFact } from '@/types/workflow'
import { Card } from '@/components/common/Card'

interface ExtractedFactsProps {
  facts?: ExtractedFact[]
}

export const ExtractedFacts = ({ facts }: ExtractedFactsProps) => {
  if (!facts || facts.length === 0) return null

  return (
    <Card title="Extracted Facts" className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        {facts.map((fact, idx) => (
          <div key={`${fact.metric}-${idx}`} className="rounded-lg border border-gray-200 p-4">
            <p className="text-xs uppercase text-gray-500">{fact.metric}</p>
            <p className="text-xl font-semibold text-gray-900 mt-1">{String(fact.value)}</p>
            <p className="text-xs text-gray-500 mt-2">
              {fact.source} • Confidence {(fact.confidence * 100).toFixed(0)}%
            </p>
          </div>
        ))}
      </div>
    </Card>
  )
}
