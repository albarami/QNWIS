import type { CritiqueOutput } from '@/types/workflow'
import { Card } from '@/components/common/Card'
import { cn } from '@/utils/cn'

interface CritiquePanelProps {
  critique?: CritiqueOutput
}

export const CritiquePanel = ({ critique }: CritiquePanelProps) => {
  if (!critique) return null

  return (
    <Card title="Critical Review" className="space-y-4">
      {critique.challenges?.map((challenge, idx) => (
        <div
          key={idx}
          className={cn(
            'rounded-lg border-l-4 p-3 text-sm',
            challenge.severity === 'high' && 'border-red-500 bg-red-50',
            challenge.severity === 'medium' && 'border-yellow-500 bg-yellow-50',
            challenge.severity === 'low' && 'border-blue-500 bg-blue-50',
          )}
        >
          <p className="font-semibold text-gray-900">{challenge.claim}</p>
          <p className="text-gray-700">{challenge.challenge}</p>
          <p className="text-xs text-gray-500 mt-1">Resolution: {challenge.resolution}</p>
        </div>
      ))}

      {critique.assumptions_audited?.length > 0 && (
        <div>
          <p className="text-xs uppercase text-gray-500 mb-1">Assumptions audited</p>
          <ul className="list-disc list-inside text-sm text-gray-700">
            {critique.assumptions_audited.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  )
}
