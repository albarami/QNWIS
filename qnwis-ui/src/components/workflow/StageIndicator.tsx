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
  const progress = ((currentIdx + 1) / stages.length) * 100

  return (
    <div className="bg-white rounded-2xl shadow-lg border-2 border-slate-200 p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-2">Workflow Progress</p>
          <p className="text-3xl font-bold text-slate-900">{displayStage}</p>
          <p className="text-sm text-slate-600 mt-1">{currentIdx + 1} of {stages.length} stages</p>
        </div>
        {isStreaming && (
          <div className="flex items-center gap-3 rounded-xl bg-amber-100 border-2 border-amber-300 px-5 py-3">
            <Spinner className="h-5 w-5 text-amber-600" />
            <span className="text-sm font-bold text-amber-900">STREAMING</span>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="h-3 w-full rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-amber-500 to-amber-600 transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-right text-xs text-slate-500 mt-1 font-semibold">{Math.round(progress)}% Complete</p>
      </div>

      {/* Stage Pills */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {stages.map((stage, idx) => {
          const status = idx < currentIdx ? 'complete' : idx === currentIdx ? 'current' : 'pending'
          const label = stageLabels[stage] ?? stage.replace('agent:', 'Agent: ')
          return (
            <div
              key={stage}
              className={cn(
                'rounded-xl border-2 px-4 py-3 text-center font-semibold transition-all',
                status === 'complete' &&
                  'border-green-300 bg-green-50 text-green-800 shadow-sm',
                status === 'current' && 'border-amber-400 bg-amber-50 text-amber-900 shadow-md ring-4 ring-amber-100',
                status === 'pending' && 'border-slate-200 bg-slate-50 text-slate-400',
              )}
            >
              {status === 'complete' && <span className="text-lg">✓</span>}
              {status === 'current' && <span className="text-lg animate-pulse">⟳</span>}
              <p className="text-xs font-bold uppercase tracking-wide mt-1">{label}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
