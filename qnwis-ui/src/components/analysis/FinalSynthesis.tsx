import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'

interface FinalSynthesisProps {
  synthesis?: string
  confidence?: number
}

export const FinalSynthesis = ({ synthesis, confidence }: FinalSynthesisProps) => {
  if (!synthesis) return null

  return (
    <Card
      title="Strategic Intelligence Summary"
      actions={
        typeof confidence === 'number' ? (
          <Badge tone={confidence >= 0.8 ? 'success' : confidence >= 0.6 ? 'warning' : 'danger'}>
            {(confidence * 100).toFixed(0)}% confidence
          </Badge>
        ) : null
      }
    >
      <p className="text-gray-800 whitespace-pre-line">{synthesis}</p>
    </Card>
  )
}
