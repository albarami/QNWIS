import React, { useEffect, useRef, useState, useMemo } from 'react'
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
  weigh_in: 'Analysis',
  refocus: 'Refocus',
  resolution: 'Resolution',
  consensus: 'Consensus',
  edge_case_analysis: 'Edge Case',
  risk_identification: 'Risk Alert',
  risk_assessment: 'Risk Assessment',
  consensus_synthesis: 'Final Synthesis',
  final_position: 'Final Position',
  data_quality_warning: '⚠️ Data Warning',
  moderator: 'Moderator',
  completion: 'Complete',
}

// Turn type colors for visual categorization
const TURN_TYPE_COLORS: Record<string, string> = {
  opening_statement: '#3B82F6', // blue
  challenge: '#F59E0B', // amber
  response: '#10B981', // green
  weigh_in: '#8B5CF6', // purple
  refocus: '#EC4899', // pink
  resolution: '#22C55E', // green
  consensus: '#22C55E', // green
  consensus_synthesis: '#22C55E', // green
  final_position: '#06B6D4', // cyan
  risk_identification: '#EF4444', // red
  risk_assessment: '#F97316', // orange
  data_quality_warning: '#EF4444', // red
}

// Format message content with better markdown-like rendering
const formatMessageContent = (message: string): React.ReactNode => {
  if (!message) return null
  
  // Split into paragraphs
  const paragraphs = message.split(/\n\n+/)
  
  return paragraphs.map((para, idx) => {
    // Handle headers (lines starting with # or **)
    if (para.startsWith('**') && para.endsWith('**')) {
      return (
        <h4 key={idx} className="font-semibold text-white mt-3 mb-2">
          {para.replace(/\*\*/g, '')}
        </h4>
      )
    }
    
    // Handle bullet points
    if (para.includes('\n-') || para.startsWith('-')) {
      const lines = para.split('\n')
      return (
        <ul key={idx} className="list-disc list-inside space-y-1 my-2 text-slate-300">
          {lines.map((line, lineIdx) => {
            const content = line.replace(/^[-•]\s*/, '').trim()
            if (!content) return null
            return <li key={lineIdx}>{formatInlineText(content)}</li>
          })}
        </ul>
      )
    }
    
    // Handle numbered lists
    if (/^\d+\./.test(para)) {
      const lines = para.split('\n')
      return (
        <ol key={idx} className="list-decimal list-inside space-y-1 my-2 text-slate-300">
          {lines.map((line, lineIdx) => {
            const content = line.replace(/^\d+\.\s*/, '').trim()
            if (!content) return null
            return <li key={lineIdx}>{formatInlineText(content)}</li>
          })}
        </ol>
      )
    }
    
    // Regular paragraph
    return (
      <p key={idx} className="my-2 text-slate-300 leading-relaxed">
        {formatInlineText(para)}
      </p>
    )
  })
}

// Format inline text (bold, citations, etc.)
const formatInlineText = (text: string): React.ReactNode => {
  // Handle **bold** text
  const parts = text.split(/(\*\*[^*]+\*\*|\[Per extraction:[^\]]+\])/g)
  
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx} className="text-white font-semibold">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('[Per extraction:')) {
      return (
        <span key={idx} className="text-cyan-400 text-xs bg-cyan-900/30 px-1 rounded">
          {part}
        </span>
      )
    }
    return part
  })
}

// Expandable message component
const DebateMessage = ({ turn, index, isExpanded, onToggle }: { 
  turn: ConversationTurn
  index: number
  isExpanded: boolean
  onToggle: () => void
}) => {
  const profile = getAgentProfile(turn.agent)
  const turnLabel = TURN_TYPE_LABELS[turn.type] || turn.type.replace(/_/g, ' ')
  const turnColor = TURN_TYPE_COLORS[turn.type] || profile.color
  
  const isLongMessage = turn.message && turn.message.length > 500
  const shouldTruncate = isLongMessage && !isExpanded
  const displayMessage = shouldTruncate 
    ? turn.message.slice(0, 500) + '...'
    : turn.message
  
  return (
    <div 
      className="debate-message animate-slideIn bg-slate-800/50 rounded-lg p-4 border-l-4 transition-all duration-300 hover:bg-slate-800/70"
      style={{ 
        borderLeftColor: profile.color,
        animationDelay: `${Math.min(index * 30, 500)}ms`
      }}
    >
      {/* Message Header */}
      <div className="flex items-start gap-3 mb-3">
        <div 
          className="flex-shrink-0 text-2xl w-12 h-12 flex items-center justify-center rounded-xl shadow-lg"
          style={{ backgroundColor: `${profile.color}20`, border: `2px solid ${profile.color}40` }}
        >
          {profile.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-bold text-white text-base">{profile.name}</span>
            <span 
              className="text-xs px-2.5 py-1 rounded-full font-medium uppercase tracking-wider"
              style={{ 
                backgroundColor: `${turnColor}20`,
                color: turnColor,
                border: `1px solid ${turnColor}40`
              }}
            >
              {turnLabel}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-slate-500">{profile.title}</span>
            <span className="text-slate-600">•</span>
            <span className="text-xs text-slate-600">Turn {turn.turn}</span>
            {turn.timestamp && (
              <>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-600">
                  {new Date(turn.timestamp).toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
      
      {/* Message Content */}
      <div className="pl-15 ml-15">
        <div className="text-sm leading-relaxed">
          {formatMessageContent(displayMessage)}
        </div>
        
        {/* Expand/Collapse Button */}
        {isLongMessage && (
          <button
            onClick={onToggle}
            className="mt-3 text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
          >
            {isExpanded ? (
              <>
                <span>Show Less</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
              </>
            ) : (
              <>
                <span>Show Full Analysis ({turn.message.length} chars)</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}

// Typing indicator component
const TypingIndicator = ({ profile }: { profile: AgentProfile }) => (
  <div 
    className="debate-message bg-slate-800/30 rounded-lg p-4 border-l-4 animate-pulse"
    style={{ borderLeftColor: profile.color }}
  >
    <div className="flex items-center gap-3">
      <div 
        className="text-2xl w-12 h-12 flex items-center justify-center rounded-xl"
        style={{ backgroundColor: `${profile.color}20` }}
      >
        {profile.icon}
      </div>
      <div>
        <span className="font-bold text-white">{profile.name}</span>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-sm text-slate-400">analyzing</span>
          <span className="flex gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
        </div>
      </div>
    </div>
  </div>
)

// Phase indicator
const PhaseIndicator = ({ phase }: { phase: string }) => {
  const phaseLabels: Record<string, { label: string; color: string; icon: string }> = {
    opening_statements: { label: 'Opening Statements', color: '#3B82F6', icon: '📢' },
    challenge_defense: { label: 'Challenge & Defense', color: '#F59E0B', icon: '⚔️' },
    edge_cases: { label: 'Edge Case Analysis', color: '#8B5CF6', icon: '🔍' },
    risk_analysis: { label: 'Risk Assessment', color: '#EF4444', icon: '⚠️' },
    consensus_building: { label: 'Building Consensus', color: '#10B981', icon: '🤝' },
    final_synthesis: { label: 'Final Synthesis', color: '#22C55E', icon: '✨' },
  }
  
  const info = phaseLabels[phase] || { label: phase, color: '#64748B', icon: '📋' }
  
  return (
    <div 
      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium"
      style={{ backgroundColor: `${info.color}15`, color: info.color }}
    >
      <span>{info.icon}</span>
      <span>{info.label}</span>
    </div>
  )
}

export const DebateConversation: React.FC<DebateConversationProps> = ({ 
  turns, 
  isStreaming = false,
  activeAgent 
}) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set())
  const [expandAll, setExpandAll] = useState(false)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [turns])

  // Calculate metrics
  const metrics = useMemo(() => {
    const consensus = turns.filter(t => 
      t.type === 'consensus_synthesis' || 
      t.type === 'final_position' ||
      t.type === 'resolution' ||
      t.type === 'consensus' ||
      (t.message && (
        t.message.toLowerCase().includes('we agree') ||
        t.message.toLowerCase().includes('consensus reached') ||
        t.message.toLowerCase().includes('common ground')
      ))
    ).length
    
    const debates = turns.filter(t => 
      t.type === 'challenge' || 
      t.type === 'risk_identification' ||
      t.type === 'response'
    ).length
    
    const uniqueAgents = new Set(turns.map(t => t.agent)).size
    
    // Estimate current phase
    let currentPhase = 'opening_statements'
    const lastTurn = turns[turns.length - 1]
    if (lastTurn) {
      if (lastTurn.type === 'final_position' || lastTurn.type === 'consensus_synthesis') {
        currentPhase = 'consensus_building'
      } else if (lastTurn.type === 'risk_identification' || lastTurn.type === 'risk_assessment') {
        currentPhase = 'risk_analysis'
      } else if (lastTurn.type === 'edge_case_analysis') {
        currentPhase = 'edge_cases'
      } else if (lastTurn.type === 'challenge' || lastTurn.type === 'response') {
        currentPhase = 'challenge_defense'
      }
    }
    
    return { consensus, debates, uniqueAgents, currentPhase }
  }, [turns])

  const toggleMessage = (index: number) => {
    setExpandedMessages(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const toggleExpandAll = () => {
    if (expandAll) {
      setExpandedMessages(new Set())
    } else {
      setExpandedMessages(new Set(turns.map((_, i) => i)))
    }
    setExpandAll(!expandAll)
  }

  if (!turns || turns.length === 0) {
    return (
      <div className="bg-slate-900/50 rounded-xl border border-slate-700 p-8">
        <div className="text-center">
          <span className="text-5xl mb-4 block">🔥</span>
          <h3 className="text-lg font-semibold text-white mb-2">Multi-Agent Deliberation</h3>
          <p className="text-slate-400">Waiting for expert agents to begin analysis...</p>
          <p className="text-xs text-slate-600 mt-2">
            PhD-level economists will debate to identify risks, resolve contradictions, and build consensus
          </p>
        </div>
      </div>
    )
  }

  const activeProfile = activeAgent ? getAgentProfile(activeAgent) : null

  return (
    <div className="bg-slate-900/50 rounded-xl border border-slate-700 overflow-hidden">
      {/* Debate Header */}
      <div className="debate-header px-6 py-4 bg-gradient-to-r from-slate-800 to-slate-900 border-b border-slate-700">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <span className="text-3xl">🔥</span>
              <div>
                <h3 className="text-xl font-bold text-white tracking-tight">EXPERT DELIBERATION</h3>
                <p className="text-xs text-slate-500">Real-time PhD-level economic analysis</p>
              </div>
            </div>
            <PhaseIndicator phase={metrics.currentPhase} />
          </div>
          
          <div className="flex items-center gap-6">
            {/* Stats */}
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-2xl">💬</span>
                <div>
                  <p className="text-lg font-bold text-white">{turns.length}</p>
                  <p className="text-xs text-slate-500">turns</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xl">👥</span>
                <div>
                  <p className="text-lg font-bold text-white">{metrics.uniqueAgents}</p>
                  <p className="text-xs text-slate-500">experts</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-amber-400 text-xl">⚔️</span>
                <div>
                  <p className="text-lg font-bold text-amber-400">{metrics.debates}</p>
                  <p className="text-xs text-slate-500">challenges</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-400 text-xl">🤝</span>
                <div>
                  <p className="text-lg font-bold text-green-400">{metrics.consensus}</p>
                  <p className="text-xs text-slate-500">consensus</p>
                </div>
              </div>
            </div>
            
            {/* Expand All Toggle */}
            <button
              onClick={toggleExpandAll}
              className="px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
            >
              {expandAll ? 'Collapse All' : 'Expand All'}
            </button>
          </div>
        </div>
        
        {/* Consensus Progress Bar */}
        {turns.length > 0 && (
          <div className="mt-4 px-2">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span>Debate Progress</span>
              <span>
                {metrics.debates > 0 && metrics.consensus > 0 
                  ? `${metrics.consensus} consensus points from ${metrics.debates} challenges`
                  : metrics.debates > 0 
                    ? `${metrics.debates} active challenges` 
                    : 'Opening statements'}
              </span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden flex">
              {/* Challenges portion (amber) */}
              <div 
                className="bg-gradient-to-r from-amber-500 to-amber-400 transition-all duration-500"
                style={{ width: `${Math.min((metrics.debates / Math.max(turns.length, 1)) * 100, 60)}%` }}
              />
              {/* Consensus portion (green) */}
              <div 
                className="bg-gradient-to-r from-emerald-500 to-green-400 transition-all duration-500"
                style={{ width: `${Math.min((metrics.consensus / Math.max(turns.length, 1)) * 100, 40)}%` }}
              />
            </div>
          </div>
        )}
      </div>
      
      {/* Messages Container */}
      <div 
        ref={scrollRef}
        className="messages-container space-y-3 p-4 max-h-[700px] overflow-y-auto custom-scrollbar"
      >
        {turns.map((turn, index) => (
          <DebateMessage 
            key={`${turn.agent}-${turn.turn}-${index}`} 
            turn={turn} 
            index={index}
            isExpanded={expandedMessages.has(index) || expandAll}
            onToggle={() => toggleMessage(index)}
          />
        ))}
        
        {/* Typing Indicator */}
        {isStreaming && activeProfile && (
          <TypingIndicator profile={activeProfile} />
        )}
      </div>

      {/* Footer with Participants */}
      <div className="px-6 py-3 bg-slate-800/50 border-t border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Participating Experts:</span>
            <div className="flex -space-x-2">
              {Array.from(new Set(turns.map(t => t.agent))).map((agent, idx) => {
                const p = getAgentProfile(agent)
                return (
                  <div 
                    key={agent}
                    className="w-8 h-8 rounded-full flex items-center justify-center text-sm border-2 border-slate-800 shadow-lg cursor-pointer hover:scale-110 transition-transform"
                    style={{ backgroundColor: `${p.color}30`, zIndex: 10 - idx }}
                    title={`${p.name} - ${p.title}`}
                  >
                    {p.icon}
                  </div>
                )
              })}
            </div>
          </div>
          
          {isStreaming && (
            <div className="flex items-center gap-2 text-cyan-400 text-sm">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>Live</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DebateConversation
