import { Badge } from '@/components/common/Badge'
import { Spinner } from '@/components/common/Spinner'
import { cn } from '@/utils/cn'

interface StageIndicatorProps {
  stages: readonly string[]
  stageLabels: Record<string, string>
  currentStage: string
  isStreaming: boolean
}

export const StageIndicator = ({
  stages,
  stageLabels,
  currentStage,
  isStreaming,
}: StageIndicatorProps) => {
  const displayStage = stageLabels[currentStage] ?? currentStage.replace('agent:', 'Agent: ')
  const currentIdx = stages.indexOf(currentStage)

  return (
    <div className="bg-white rounded-xl shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs uppercase text-gray-500">Current stage</p>
          <p className="text-xl font-semibold text-gray-900">{displayStage}</p>
        </div>
        {isStreaming && (
          <Badge tone="info" className="flex items-center gap-2 text-sm">
            <Spinner /> Streaming
          </Badge>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-5">
        {stages.map((stage, idx) => {
          const status = idx < currentIdx ? 'complete' : idx === currentIdx ? 'current' : 'pending'
          const label = stageLabels[stage] ?? stage.replace('agent:', 'Agent: ')
          return (
            <div
              key={stage}
              className={cn(
                'rounded-lg border px-3 py-2 text-center',
                status === 'complete' &&
                  'border-green-200 bg-green-50 text-green-700 dark:border-green-300',
                status === 'current' && 'border-blue-200 bg-blue-50 text-blue-700',
                status === 'pending' && 'border-gray-200 bg-gray-50 text-gray-500',
              )}
            >
              <p className="text-xs font-medium uppercase tracking-wide">{label}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
