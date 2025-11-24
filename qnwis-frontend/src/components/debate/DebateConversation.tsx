import React, { useEffect, useRef, useState } from 'react'
import { ConversationTurn } from '../../types/workflow'
import { getAgentProfile, AgentProfile } from '../../utils/agentProfiles'

interface DebateConversationProps {
  turns: ConversationTurn[]
  isStreaming?: boolean
  activeAgent?: string
}

// Turn type to descriptive label mapping
const TURN_TYPE_LABELS: Record<string, string> = {
  opening_statement: 'Opening Statement',
  challenge: 'Challenge',
  response: 'Response',
  contribution: 'Contribution',
  resolution: 'Resolution',
  consensus: 'Consensus Reached',
  edge_case_analysis: 'Edge Case Analysis',
  risk_identification: 'Risk Identified',
  risk_assessment: 'Risk Assessment',
  consensus_synthesis: 'Final Synthesis',
  final_position: 'Final Position',
  data_quality_warning: 'Data Warning',
  moderator: 'Moderator',
}

// Message component with chat bubble style
const DebateMessage = ({ turn, index }: { turn: ConversationTurn; index: number }) => {
  const profile = getAgentProfile(turn.agent)
  const turnLabel = TURN_TYPE_LABELS[turn.type] || turn.type.replace(/_/g, ' ')
  
  return (
    <div 
      className="debate-message animate-slideIn"
      style={{ 
        borderLeftColor: profile.color,
        animationDelay: `${index * 50}ms`
      }}
    >
      {/* Message Header */}
      <div className="flex items-center gap-3 mb-3">
        <span 
          className="text-2xl w-10 h-10 flex items-center justify-center rounded-full"
          style={{ backgroundColor: `${profile.color}20` }}
        >
          {profile.icon}
        </span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white">{profile.name}</span>
            <span 
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ 
                backgroundColor: `${profile.color}20`,
                color: profile.color 
              }}
            >
              {turnLabel}
            </span>
          </div>
          <span className="text-xs text-slate-500">{profile.title}</span>
        </div>
        <div className="text-right">
          <span className="text-xs text-slate-600">Turn {turn.turn}</span>
          <br />
          <span className="text-xs text-slate-600">
            {new Date(turn.timestamp).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </span>
        </div>
      </div>
      
      {/* Message Content */}
      <div className="text-slate-200 leading-relaxed pl-13 ml-13">
        <p className="whitespace-pre-wrap text-sm">{turn.message}</p>
      </div>
    </div>
  )
}

// Typing indicator component
const TypingIndicator = ({ profile }: { profile: AgentProfile }) => (
  <div 
    className="debate-message animate-pulse"
    style={{ borderLeftColor: profile.color }}
  >
    <div className="flex items-center gap-3">
      <span 
        className="text-2xl w-10 h-10 flex items-center justify-center rounded-full"
        style={{ backgroundColor: `${profile.color}20` }}
      >
        {profile.icon}
      </span>
      <div>
        <span className="font-semibold text-white">{profile.name}</span>
        <div className="flex items-center gap-1 mt-1">
          <span className="text-sm text-slate-400">is analyzing</span>
          <span className="typing-dots flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
        </div>
      </div>
    </div>
  </div>
)

export const DebateConversation: React.FC<DebateConversationProps> = ({ 
  turns, 
  isStreaming = false,
  activeAgent 
}) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [consensusPoints, setConsensusPoints] = useState<number>(0)
  const [activeDebates, setActiveDebates] = useState<number>(0)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [turns])

  // Calculate consensus and debate metrics
  useEffect(() => {
    // Consensus indicators: consensus_synthesis, final_position with agreement language, resolution
    const consensus = turns.filter(t => 
      t.type === 'consensus_synthesis' || 
      t.type === 'final_position' ||
      t.type === 'resolution' ||
      (t.message && t.message.toLowerCase().includes('consensus'))
    ).length
    
    // Active debates: challenges, risk identification, responses to challenges
    const debates = turns.filter(t => 
      t.type === 'challenge' || 
      t.type === 'risk_identification' ||
      t.type === 'response'
    ).length
    
    setConsensusPoints(consensus)
    setActiveDebates(debates)
  }, [turns])

  // Get current debate topic from recent messages
  const getCurrentTopic = (): string => {
    const recentChallenge = [...turns].reverse().find(t => t.type === 'challenge')
    if (recentChallenge) {
      // Extract first sentence or first 100 chars
      const firstSentence = recentChallenge.message.split('.')[0]
      return firstSentence.length > 100 ? firstSentence.slice(0, 100) + '...' : firstSentence
    }
    return 'Multi-agent deliberation in progress...'
  }

  // Estimate total turns based on pattern
  const estimatedTotalTurns = Math.max(turns.length + 3, 10)

  if (!turns || turns.length === 0) {
    return (
      <div className="debate-container-empty">
        <div className="text-center py-8">
          <span className="text-4xl mb-4 block">🔥</span>
          <p className="text-slate-400">Waiting for multi-agent deliberation to begin...</p>
          <p className="text-xs text-slate-600 mt-2">Agents will debate to resolve contradictions and reach consensus</p>
        </div>
      </div>
    )
  }

  const activeProfile = activeAgent ? getAgentProfile(activeAgent) : null

  return (
    <div className="debate-container">
      {/* Debate Header */}
      <div className="debate-header flex items-center justify-between mb-4 pb-3 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🔥</span>
          <div>
            <h3 className="text-lg font-semibold text-white">MULTI-AGENT DELIBERATION</h3>
            <p className="text-xs text-slate-500">Real-time expert analysis and debate</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-xs text-slate-500">Turn</span>
            <p className="text-lg font-bold text-cyan-400">{turns.length} <span className="text-sm text-slate-500">of ~{estimatedTotalTurns}</span></p>
          </div>
        </div>
      </div>

      {/* Current Topic */}
      <div className="current-topic bg-slate-800/50 rounded-lg px-4 py-3 mb-4">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">DEBATING:</span>
        <p className="text-sm text-slate-300 mt-1">{getCurrentTopic()}</p>
      </div>
      
      {/* Messages Container */}
      <div 
        ref={scrollRef}
        className="messages-container space-y-4 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar"
      >
        {turns.map((turn, index) => (
          <DebateMessage key={`${turn.agent}-${turn.turn}-${index}`} turn={turn} index={index} />
        ))}
        
        {/* Typing Indicator */}
        {isStreaming && activeProfile && (
          <TypingIndicator profile={activeProfile} />
        )}
      </div>

      {/* Consensus Tracker Footer */}
      <div className="consensus-footer flex items-center justify-between mt-4 pt-3 border-t border-slate-700">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-green-400">✓</span>
            <span className="text-sm text-slate-400">Points of Agreement: <strong className="text-green-400">{consensusPoints}</strong></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-amber-400">⚡</span>
            <span className="text-sm text-slate-400">Active Debates: <strong className="text-amber-400">{activeDebates}</strong></span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Agent avatars showing who's participated */}
          <span className="text-xs text-slate-500">Participants:</span>
          <div className="flex -space-x-2">
            {Array.from(new Set(turns.map(t => t.agent))).slice(0, 5).map((agent, idx) => {
              const p = getAgentProfile(agent)
              return (
                <span 
                  key={agent}
                  className="w-6 h-6 rounded-full flex items-center justify-center text-xs border-2 border-slate-800"
                  style={{ backgroundColor: `${p.color}30`, zIndex: 5 - idx }}
                  title={p.name}
                >
                  {p.icon}
                </span>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DebateConversation
