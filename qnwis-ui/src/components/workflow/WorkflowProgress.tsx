import type { WorkflowState } from '@/types/workflow'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'

interface WorkflowProgressProps {
  state: WorkflowState
}

const complexityTone = {
  simple: 'info',
  medium: 'warning',
  complex: 'danger',
  critical: 'danger',
} as const

export const WorkflowProgress = ({ state }: WorkflowProgressProps) => (
  <Card
    title="Workflow Status"
    subtitle="Live telemetry from the LangGraph council"
    className="space-y-4"
  >
    <div className="space-y-2">
      <p className="text-sm text-gray-500">Query</p>
      <p className="text-base font-medium text-gray-900">{state.query}</p>
      <Badge tone={complexityTone[state.complexity] ?? 'default'} className="mt-2">
        {state.complexity.toUpperCase()}
      </Badge>
    </div>

    <dl className="grid grid-cols-2 gap-4 text-sm">
      <div>
        <dt className="text-gray-500">Extracted facts</dt>
        <dd className="text-gray-900 font-semibold">{state.extracted_facts?.length ?? 0}</dd>
      </div>
      <div>
        <dt className="text-gray-500">Agents invoked</dt>
        <dd className="text-gray-900 font-semibold">{state.agents_invoked?.length ?? 0}</dd>
      </div>
      <div>
        <dt className="text-gray-500">Status</dt>
        <dd className="text-gray-900 font-semibold capitalize">{state.status}</dd>
      </div>
      <div>
        <dt className="text-gray-500">Confidence</dt>
        <dd className="text-gray-900 font-semibold">
          {(state.confidence_score * 100).toFixed(0)}%
        </dd>
      </div>
    </dl>
  </Card>
)
