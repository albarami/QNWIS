import type { AgentOutput } from '@/types/workflow'
import { Card } from '@/components/common/Card'

interface LiveDebateTimelineProps {
  agentOutputs?: AgentOutput[]
  debate?: string | null
  critique?: string | null
  synthesis?: string
}

interface TimelineEntry {
  type: 'agent' | 'debate' | 'critique'
  title: string
  icon: string
  accent: string
  content: string
  confidence?: number
}

const AGENT_META: Record<string, { icon: string; accent: string; label: string }> = {
  labour: { icon: '👔', accent: 'border-blue-200 bg-blue-50', label: 'Labour Economist' },
  financial: { icon: '💰', accent: 'border-green-200 bg-green-50', label: 'Financial Economist' },
  market: { icon: '📊', accent: 'border-purple-200 bg-purple-50', label: 'Market Economist' },
  operations: { icon: '⚙️', accent: 'border-orange-200 bg-orange-50', label: 'Operations Expert' },
  research: { icon: '🔬', accent: 'border-pink-200 bg-pink-50', label: 'Research Scientist' },
}

const buildTimeline = (outputs?: AgentOutput[], debate?: string | null, critique?: string | null): TimelineEntry[] => {
  const entries: TimelineEntry[] = []

  outputs?.forEach((output) => {
    const meta = AGENT_META[output.agent] ?? { icon: '🤖', accent: 'border-gray-200 bg-gray-50', label: output.agent_name }
    entries.push({
      type: 'agent',
      title: meta.label || output.agent_name,
      icon: meta.icon,
      accent: meta.accent,
      content: output.analysis,
      confidence: output.confidence,
    })
  })

  if (debate && debate.trim().length > 0) {
    entries.push({
      type: 'debate',
      title: 'Multi-Agent Debate',
      icon: '⚖️',
      accent: 'border-yellow-200 bg-yellow-50',
      content: debate,
    })
  }

  if (critique && critique.trim().length > 0) {
    entries.push({
      type: 'critique',
      title: "Devil's Advocate",
      icon: '😈',
      accent: 'border-red-200 bg-red-50',
      content: critique,
    })
  }

  return entries
}

export const LiveDebateTimeline = ({ agentOutputs, debate, critique }: LiveDebateTimelineProps) => {
  const entries = buildTimeline(agentOutputs, debate, critique)

  return (
    <Card
      title="Live Council Debate"
      subtitle="Real-time conversation across the five specialist agents"
      className="space-y-4"
    >
      {entries.length === 0 && (
        <p className="text-sm text-gray-500">Debate will appear once the council begins streaming.</p>
      )}

      <div className="space-y-4">
        {entries.map((entry, idx) => (
          <article
            key={`${entry.title}-${idx}`}
            className={`rounded-xl border px-4 py-3 ${entry.accent} transition hover:shadow-md`}
          >
            <header className="mb-2 flex items-center justify-between">
              <div className="flex items-center gap-2 text-base font-semibold text-gray-900">
                <span className="text-2xl" role="img" aria-label={entry.type}>
                  {entry.icon}
                </span>
                {entry.title}
              </div>
              {entry.confidence !== undefined && (
                <span className="text-sm font-medium text-gray-600">
                  Confidence {(entry.confidence * 100).toFixed(0)}%
                </span>
              )}
            </header>
            <p className="text-sm text-gray-700 whitespace-pre-line">
              {entry.content.length > 600 ? `${entry.content.slice(0, 600)}…` : entry.content}
            </p>
          </article>
        ))}
      </div>
    </Card>
  )
}
