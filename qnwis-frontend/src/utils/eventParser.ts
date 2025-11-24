import { WorkflowEvent, WorkflowStage, isValidWorkflowEvent } from '../types/workflow'

interface RawSSEEvent {
  data?: string
}

const VALID_STATUSES = new Set(['running', 'streaming', 'complete', 'error', 'ready'])

const STANDARD_STAGES: Record<string, WorkflowStage> = {
  classify: 'classify',
  prefetch: 'prefetch',
  rag: 'rag',
  agent_selection: 'agent_selection',
  agents: 'agents',
  debate: 'debate',
  critique: 'critique',
  verify: 'verify',
  synthesize: 'synthesize',
  done: 'done',
}

function normalizeStage(stage: string): WorkflowStage | string {
  const trimmed = stage.trim()
  const normalized = trimmed.toLowerCase()

  if (STANDARD_STAGES[normalized as WorkflowStage]) {
    return STANDARD_STAGES[normalized as WorkflowStage]
  }

  // Keep agent stages in original case to match agent_selection payload
  if (trimmed.startsWith('agent:')) {
    return trimmed
  }

  // Keep debate turn stages for conversation streaming
  if (trimmed.startsWith('debate:turn')) {
    return trimmed
  }

  return trimmed
}

export function parseWorkflowEvent(raw: RawSSEEvent | string): WorkflowEvent {
  const payload = typeof raw === 'string' ? raw : raw.data ?? ''

  if (!payload.trim()) {
    throw new Error('Empty SSE payload received')
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(payload)
  } catch (error) {
    throw new Error(`Invalid JSON payload: ${(error as Error).message}`)
  }

  if (!isValidWorkflowEvent(parsed)) {
    throw new Error('Payload does not match WorkflowEvent shape')
  }

  const normalizedStage = normalizeStage(parsed.stage)
  const status = parsed.status.toLowerCase()

  if (!VALID_STATUSES.has(status)) {
    throw new Error(`Unknown workflow status: ${parsed.status}`)
  }

  return {
    ...parsed,
    stage: normalizedStage,
    status: status as WorkflowEvent['status'],
  }
}

export function safeParseWorkflowEvent(raw: RawSSEEvent | string): WorkflowEvent | null {
  try {
    return parseWorkflowEvent(raw)
  } catch (error) {
    console.warn('Skipping malformed event:', raw, error)
    return null
  }
}
