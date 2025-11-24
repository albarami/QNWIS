import type { DebateResults } from '../../types/workflow'
import { DebateConversation } from './DebateConversation'

interface DebatePanelProps {
  debate: DebateResults | null
  debateTurns?: any[]
  isStreaming?: boolean
}

export function DebatePanel({ debate, debateTurns = [], isStreaming = false }: DebatePanelProps) {
  // Show live turns while streaming, even if debate isn't complete yet
  if (!debate && debateTurns.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 text-slate-400" data-testid="debate-panel">
        <div className="text-center py-4">
          <span className="text-3xl mb-3 block">🔥</span>
          <p>Multi-agent deliberation will begin once analysis is complete.</p>
          <p className="text-xs text-slate-500 mt-2">Agents will debate to resolve contradictions and reach consensus</p>
        </div>
      </div>
    )
  }

  // If streaming but not complete, show live turns with streaming indicator
  if (!debate && debateTurns.length > 0) {
    // Get the last agent for typing indicator
    const lastAgent = debateTurns.length > 0 ? debateTurns[debateTurns.length - 1].agent : undefined
    
    return (
      <div className="rounded-2xl border border-purple-400/40 bg-slate-900/50 p-6 space-y-4" data-testid="debate-panel">
        <DebateConversation 
          turns={debateTurns} 
          isStreaming={isStreaming}
          activeAgent={lastAgent}
        />
      </div>
    )
  }

  // If we get here, debate must be truthy (TypeScript needs explicit check)
  if (!debate) {
    return null
  }

  return (
    <div className="rounded-2xl border border-purple-400/40 bg-slate-900/50 p-6 space-y-4" data-testid="debate-panel">
      {/* Summary Stats Bar */}
      <div className="flex items-center justify-between bg-slate-800/50 rounded-lg px-4 py-3">
        <div className="flex items-center gap-6">
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-400">{debate.contradictions_found || 0}</p>
            <p className="text-xs text-slate-500">Contradictions</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-emerald-400">{debate.resolved || 0}</p>
            <p className="text-xs text-slate-500">Resolved</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-amber-400">{debate.flagged_for_review || 0}</p>
            <p className="text-xs text-slate-500">Flagged</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-cyan-400">{debate.total_turns || 0}</p>
            <p className="text-xs text-slate-500">Turns</p>
          </div>
        </div>
        {debate.latency_ms && (
          <span className="text-sm text-slate-400">
            ⏱️ {(debate.latency_ms / 1000).toFixed(1)}s
          </span>
        )}
      </div>

      {/* Debate Conversation */}
      <DebateConversation turns={debate.conversation_history || []} />

      {/* Consensus Narrative */}
      {debate.consensus_narrative && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-900/10 p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">🤝</span>
            <h4 className="font-semibold text-emerald-400">CONSENSUS REACHED</h4>
          </div>
          <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
            {debate.consensus_narrative}
          </p>
        </div>
      )}

      {/* Resolutions */}
      {debate.resolutions?.length ? (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <span>⚖️</span> Arbitration Decisions
          </h4>
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
                    {resolution.action?.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </div>
                <p className="text-sm text-slate-300 whitespace-pre-wrap">{resolution.explanation}</p>
                {resolution.recommended_value && (
                  <div className="text-xs text-slate-400 mt-2 pt-2 border-t border-slate-800">
                    Recommended: <strong className="text-cyan-400">{resolution.recommended_value}</strong> 
                    {resolution.confidence && ` (${(resolution.confidence * 100).toFixed(0)}% confidence)`}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : debate.contradictions?.length ? (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <span>⚠️</span> Active Contradictions
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {debate.contradictions.map((item, index) => (
              <div key={`${item.metric_name}-${index}`} className="rounded-xl border border-amber-500/30 bg-amber-900/10 p-3">
                <p className="font-semibold text-sm text-white mb-2">{item.metric_name}</p>
                <div className="space-y-1 text-xs">
                  <p className="text-slate-300">{item.agent1_name}: <strong>{item.agent1_value_str}</strong></p>
                  <p className="text-slate-300">{item.agent2_name}: <strong>{item.agent2_value_str}</strong></p>
                </div>
                <p className={`text-xs mt-2 ${
                  item.severity === 'high' ? 'text-red-400' :
                  item.severity === 'medium' ? 'text-amber-400' : 'text-slate-400'
                }`}>
                  Severity: {item.severity.toUpperCase()}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
