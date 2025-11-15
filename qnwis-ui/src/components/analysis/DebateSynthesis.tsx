import type { DebateOutput } from '@/types/workflow'
import { Card } from '@/components/common/Card'

interface DebateSynthesisProps {
  debate?: DebateOutput
}

export const DebateSynthesis = ({ debate }: DebateSynthesisProps) => {
  if (!debate) return null

  return (
    <Card title="Debate Synthesis" className="space-y-4">
      <p className="text-gray-800 whitespace-pre-line">{debate.synthesis}</p>
      {debate.contradictions?.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm font-semibold text-gray-900">Contradictions monitored</p>
          {debate.contradictions.map((item, idx) => (
            <div key={idx} className="rounded-lg border border-gray-200 p-3 text-sm text-gray-700">
              <p className="font-medium text-gray-900">{item.topic}</p>
              <ul className="mt-2 list-disc list-inside">
                {item.perspectives.map((perspective, index) => (
                  <li key={index}>
                    <span className="font-semibold">{perspective.agent}:</span> {perspective.view}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-gray-500">Resolution: {item.resolution}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
