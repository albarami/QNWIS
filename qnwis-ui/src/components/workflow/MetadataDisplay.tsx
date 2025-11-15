import type { WorkflowState } from '@/types/workflow'
import { Card } from '@/components/common/Card'

interface MetadataDisplayProps {
  state: WorkflowState
}

export const MetadataDisplay = ({ state }: MetadataDisplayProps) => {
  if (!state.execution_time_ms && !state.llm_calls && !state.cost_usd) {
    return null
  }

  return (
    <Card title="Execution Metrics">
      <div className="grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
        <div>
          <p className="text-gray-500">Execution time</p>
          <p className="text-gray-900 font-semibold">
            {state.execution_time_ms ? (state.execution_time_ms / 1000).toFixed(1) : '—'}s
          </p>
        </div>
        <div>
          <p className="text-gray-500">LLM calls</p>
          <p className="text-gray-900 font-semibold">{state.llm_calls ?? '—'}</p>
        </div>
        <div>
          <p className="text-gray-500">Estimated cost</p>
          <p className="text-gray-900 font-semibold">
            {state.cost_usd ? `$${state.cost_usd.toFixed(3)}` : '—'}
          </p>
        </div>
      </div>
    </Card>
  )
}
