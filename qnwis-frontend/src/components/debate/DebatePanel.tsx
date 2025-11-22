import type { DebateResults } from '../../types/workflow'
import { DebateConversation } from './DebateConversation'

interface DebatePanelProps {
  debate: DebateResults | null
  debateTurns?: any[]
}

export function DebatePanel({ debate, debateTurns = [] }: DebatePanelProps) {
  // Show live turns while streaming, even if debate isn't complete yet
  if (!debate && debateTurns.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 text-slate-400" data-testid="debate-panel">
        Debate telemetry will appear here once contradictions are detected.
      </div>
    )
  }

  // If streaming but not complete, show live turns
  if (!debate && debateTurns.length > 0) {
    return (
      <div className="rounded-2xl border border-purple-400/40 bg-slate-900/50 p-6 space-y-4" data-testid="debate-panel">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-purple-300">Multi-agent debate (streaming)</p>
            <p className="text-sm text-slate-300">
              {debateTurns.length} turns · In progress...
            </p>
          </div>
        </div>

        <div className="border-b border-slate-700 pb-4">
          <DebateConversation turns={debateTurns} />
        </div>
      </div>
    )
  }

  // If we get here, debate must be truthy (TypeScript needs explicit check)
  if (!debate) {
    return null
  }

  return (
    <div className="rounded-2xl border border-purple-400/40 bg-slate-900/50 p-6 space-y-4" data-testid="debate-panel">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-purple-300">Multi-agent debate</p>
          <p className="text-sm text-slate-300">
            {debate.contradictions_found} contradictions · {debate.resolved} resolved · {debate.flagged_for_review} flagged
          </p>
        </div>
        <span className="text-xs text-slate-500">{(debate.latency_ms / 1000).toFixed(1)}s</span>
      </div>

      <div className="border-b border-slate-700 pb-4">
        <DebateConversation turns={debate.conversation_history || []} />
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200 whitespace-pre-wrap">
        {debate.consensus_narrative}
      </div>

      {debate.resolutions?.length ? (
        <div className="space-y-3">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Debate Arbitration (LLM Analysis)</p>
          <div className="space-y-3">
            {debate.resolutions.map((resolution: any, index: number) => (
              <div key={index} className="rounded-xl border border-purple-400/30 bg-slate-900/70 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-purple-300">
                    Resolution {index + 1}
                  </span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    resolution.action === 'use_agent1' || resolution.action === 'use_agent2' ? 'bg-green-500/20 text-green-300' :
                    resolution.action === 'flag_for_review' ? 'bg-yellow-500/20 text-yellow-300' :
                    'bg-blue-500/20 text-blue-300'
                  }`}>
                    {resolution.action}
                  </span>
                </div>
                <div className="text-sm text-slate-200">
                  <p className="font-semibold mb-1">LLM Arbitration:</p>
                  <p className="text-slate-300 whitespace-pre-wrap">{resolution.explanation}</p>
                </div>
                {resolution.recommended_value && (
                  <div className="text-xs text-slate-400 mt-2 pt-2 border-t border-slate-800">
                    Recommended: {resolution.recommended_value} (confidence: {(resolution.confidence * 100).toFixed(0)}%)
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : debate.contradictions?.length ? (
        <div className="space-y-3">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Active contradictions</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {debate.contradictions.map((item, index) => (
              <div key={`${item.metric_name}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-xs text-slate-200">
                <p className="font-semibold text-sm text-white">{item.metric_name}</p>
                <p className="mt-1">{item.agent1_name}: {item.agent1_value_str}</p>
                <p>{item.agent2_name}: {item.agent2_value_str}</p>
                <p className="text-slate-400 mt-1">Severity: {item.severity}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
