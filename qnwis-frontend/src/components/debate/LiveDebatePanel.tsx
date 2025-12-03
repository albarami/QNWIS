import React, { useState, useEffect, useRef, useMemo } from 'react'
import { ConversationTurn } from '../../types/workflow'
import { DebateSummary } from '../../types/engineB'
import { getAgentProfile } from '../../utils/agentProfiles'

interface LiveDebatePanelProps {
  turns: ConversationTurn[]
  isLive: boolean
  currentSpeaker?: string
  totalExpectedTurns?: number
  summary?: DebateSummary | null
  onShowSummary?: () => void
}

// Turn type colors and labels
const TURN_TYPE_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  opening_statement: { label: 'OPENING', color: '#3B82F6', bgColor: 'bg-blue-500/10' },
  challenge: { label: 'CHALLENGE', color: '#F59E0B', bgColor: 'bg-amber-500/10' },
  response: { label: 'RESPONSE', color: '#10B981', bgColor: 'bg-emerald-500/10' },
  contribution: { label: 'CONTRIBUTION', color: '#8B5CF6', bgColor: 'bg-purple-500/10' },
  weigh_in: { label: 'ANALYSIS', color: '#06B6D4', bgColor: 'bg-cyan-500/10' },
  risk_identification: { label: 'RISK ALERT', color: '#EF4444', bgColor: 'bg-red-500/10' },
  risk_assessment: { label: 'RISK ASSESSMENT', color: '#F97316', bgColor: 'bg-orange-500/10' },
  consensus: { label: 'CONSENSUS', color: '#22C55E', bgColor: 'bg-green-500/10' },
  consensus_synthesis: { label: 'SYNTHESIS', color: '#22C55E', bgColor: 'bg-green-500/10' },
  final_position: { label: 'FINAL POSITION', color: '#6366F1', bgColor: 'bg-indigo-500/10' },
  resolution: { label: 'RESOLUTION', color: '#22C55E', bgColor: 'bg-green-500/10' },
}

// Extract data citations from message text
const extractDataCitations = (message: string): string[] => {
  const citations: string[] = []
  
  // Match patterns like [Base Case: 68.4%], [Oil Crash: 45.2%], etc.
  const bracketMatches = message.match(/\[[^\]]+:\s*[\d.]+%?\]/g) || []
  citations.push(...bracketMatches)
  
  // Match "Per extraction:" patterns
  const extractionMatches = message.match(/\[Per extraction:[^\]]+\]/g) || []
  citations.push(...extractionMatches)
  
  // Match scenario references
  const scenarioMatches = message.match(/\d+\.?\d*%\s*success/gi) || []
  citations.push(...scenarioMatches.map(m => `[${m}]`))
  
  return [...new Set(citations)].slice(0, 4) // Dedupe and limit
}

// Format message content with inline styling
const formatMessageContent = (message: string): React.ReactNode => {
  if (!message) return null
  
  // Split into paragraphs
  const paragraphs = message.split(/\n\n+/)
  
  return paragraphs.map((para, idx) => {
    // Handle bullet points
    if (para.includes('\n-') || para.startsWith('-')) {
      const lines = para.split('\n')
      return (
        <ul key={idx} className="list-disc list-inside space-y-1 my-2 text-slate-300">
          {lines.map((line, i) => {
            const content = line.replace(/^[-•]\s*/, '').trim()
            if (!content) return null
            return <li key={i}>{formatInlineText(content)}</li>
          })}
        </ul>
      )
    }
    
    // Regular paragraph
    return (
      <p key={idx} className="my-2 text-slate-200 leading-relaxed">
        {formatInlineText(para)}
      </p>
    )
  })
}

// Format inline text (bold, numbers)
const formatInlineText = (text: string): React.ReactNode => {
  const parts = text.split(/(\*\*[^*]+\*\*|\d+\.?\d*%)/g)
  
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx} className="text-white font-semibold">{part.slice(2, -2)}</strong>
    }
    if (/^\d+\.?\d*%$/.test(part)) {
      return <span key={idx} className="text-cyan-400 font-bold">{part}</span>
    }
    return part
  })
}

// Single message component
const DebateMessage: React.FC<{
  turn: ConversationTurn
  isNew?: boolean
  isTyping?: boolean
}> = ({ turn, isNew = false, isTyping = false }) => {
  const profile = getAgentProfile(turn.agent)
  const config = TURN_TYPE_CONFIG[turn.type] || { label: turn.type.toUpperCase(), color: '#64748B', bgColor: 'bg-slate-500/10' }
  const citations = extractDataCitations(turn.message || '')

  if (isTyping) {
    return (
      <div 
        className="rounded-xl p-4 border-l-4 bg-slate-800/30 animate-pulse"
        style={{ borderLeftColor: profile.color }}
      >
        <div className="flex items-center gap-3">
          <div 
            className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
            style={{ backgroundColor: `${profile.color}20` }}
          >
            {profile.icon}
          </div>
          <div>
            <span className="font-bold text-white">{profile.name}</span>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm text-slate-400">{profile.title}</span>
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
  }

  return (
    <div 
      className={`rounded-xl p-5 border-l-4 transition-all duration-500 ${config.bgColor} ${
        isNew ? 'ring-2 ring-cyan-400/50 shadow-lg shadow-cyan-500/10' : ''
      }`}
      style={{ borderLeftColor: config.color }}
    >
      {/* Header */}
      <div className="flex items-start gap-4 mb-3">
        <div 
          className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-2xl shadow-lg"
          style={{ backgroundColor: `${profile.color}20`, border: `2px solid ${profile.color}40` }}
        >
          {profile.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-bold text-white text-lg">{profile.name}</span>
            <span 
              className="px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wide"
              style={{ backgroundColor: `${config.color}20`, color: config.color, border: `1px solid ${config.color}40` }}
            >
              {config.label}
            </span>
            {isNew && (
              <span className="px-2 py-0.5 bg-cyan-500 text-white text-xs font-bold rounded-full animate-pulse">
                NEW
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1 text-sm text-slate-400">
            <span>{profile.title}</span>
            <span>•</span>
            <span>Turn {turn.turn}</span>
          </div>
        </div>
      </div>

      {/* Message content */}
      <div className="text-base leading-relaxed">
        {formatMessageContent(turn.message)}
      </div>

      {/* Data citations */}
      {citations.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-700/50">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-500">📊 References:</span>
            {citations.map((citation, i) => (
              <span 
                key={i}
                className="px-2 py-0.5 bg-cyan-900/30 text-cyan-300 text-xs rounded border border-cyan-500/30"
              >
                {citation}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Phase progress indicator
const PhaseProgress: React.FC<{ 
  currentPhase: string
  turnsCompleted: number
  totalTurns: number 
}> = ({ currentPhase, turnsCompleted, totalTurns }) => {
  const phases = ['opening', 'challenge', 'deliberation', 'consensus', 'final']
  const currentIndex = phases.indexOf(currentPhase) >= 0 ? phases.indexOf(currentPhase) : 1

  return (
    <div className="bg-slate-800/30 rounded-lg px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {phases.map((phase, i) => (
            <React.Fragment key={phase}>
              <span className={`text-xs font-medium uppercase ${
                i < currentIndex ? 'text-emerald-400' :
                i === currentIndex ? 'text-cyan-400' :
                'text-slate-500'
              }`}>
                {i < currentIndex && '✓ '}
                {phase}
              </span>
              {i < phases.length - 1 && (
                <span className={`text-xs ${i < currentIndex ? 'text-emerald-400' : 'text-slate-600'}`}>
                  ━━▶
                </span>
              )}
            </React.Fragment>
          ))}
        </div>
        <span className="text-sm text-slate-400">
          {turnsCompleted}/{totalTurns}
        </span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 rounded-full transition-all duration-500"
          style={{ width: `${(turnsCompleted / totalTurns) * 100}%` }}
        />
      </div>
    </div>
  )
}

// Optional summary card (collapsible)
const SummaryCard: React.FC<{ 
  summary: DebateSummary
  onClose: () => void 
}> = ({ summary, onClose }) => {
  return (
    <div className="bg-slate-800/50 border border-cyan-500/30 rounded-xl p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">📋</span>
          <span className="text-sm font-semibold text-cyan-300">Quick Summary</span>
          <span className="text-xs text-slate-500">(updated at turn {summary.lastUpdatedTurn})</span>
        </div>
        <button 
          onClick={onClose}
          className="text-slate-400 hover:text-white text-sm"
        >
          ✕
        </button>
      </div>
      
      <p className="text-sm text-slate-300 mb-3">{summary.text}</p>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-emerald-400 font-semibold mb-1">✓ AGREED</p>
          <ul className="text-xs text-slate-400 space-y-0.5">
            {summary.consensusPoints.slice(0, 3).map((point, i) => (
              <li key={i}>• {point}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs text-amber-400 font-semibold mb-1">⚡ DEBATING</p>
          <ul className="text-xs text-slate-400 space-y-0.5">
            {summary.activeDisagreements.slice(0, 3).map((point, i) => (
              <li key={i}>• {point}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

export const LiveDebatePanel: React.FC<LiveDebatePanelProps> = ({
  turns,
  isLive,
  currentSpeaker,
  totalExpectedTurns = 150,
  summary,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const latestMessageRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [showSummary, setShowSummary] = useState(false)
  const [newMessageCount, setNewMessageCount] = useState(0)
  const [lastSeenIndex, setLastSeenIndex] = useState(0)
  const [highlightedIndex, setHighlightedIndex] = useState<number | null>(null)

  // Detect current phase from last turns
  const currentPhase = useMemo(() => {
    const lastTurn = turns[turns.length - 1]
    if (!lastTurn) return 'opening'
    
    if (['consensus_synthesis', 'final_position', 'resolution'].includes(lastTurn.type)) {
      return 'consensus'
    }
    if (['risk_identification', 'risk_assessment'].includes(lastTurn.type)) {
      return 'deliberation'
    }
    if (lastTurn.type === 'challenge' || lastTurn.type === 'response') {
      return 'challenge'
    }
    if (turns.length > 100) return 'final'
    return 'opening'
  }, [turns])

  // Track new messages when auto-scroll is paused
  useEffect(() => {
    if (!autoScroll && turns.length > lastSeenIndex) {
      setNewMessageCount(turns.length - lastSeenIndex)
    }
  }, [turns.length, autoScroll, lastSeenIndex])

  // Auto-scroll with delay for readability - scrolls to START of new message
  useEffect(() => {
    if (autoScroll && turns.length > 0) {
      setHighlightedIndex(turns.length - 1)
      
      // Scroll to the START of the new message (not the bottom)
      const scrollDelay = setTimeout(() => {
        if (latestMessageRef.current) {
          latestMessageRef.current.scrollIntoView({
            behavior: 'smooth',
            block: 'start', // Show start of message, not end
          })
        }
      }, 500) // Reduced delay for better UX
      
      const highlightDelay = setTimeout(() => {
        setHighlightedIndex(null)
      }, 4000)
      
      setLastSeenIndex(turns.length)
      
      return () => {
        clearTimeout(scrollDelay)
        clearTimeout(highlightDelay)
      }
    }
  }, [turns.length, autoScroll])

  const jumpToLatest = () => {
    setAutoScroll(true)
    setNewMessageCount(0)
    setLastSeenIndex(turns.length)
    // Scroll to START of latest message
    if (latestMessageRef.current) {
      latestMessageRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    }
  }

  // Get participating experts
  const participants = useMemo(() => {
    const agents = new Set(turns.map(t => t.agent))
    return Array.from(agents).map(a => getAgentProfile(a))
  }, [turns])

  if (turns.length === 0 && !isLive) {
    return (
      <div className="rounded-2xl bg-slate-900/60 border border-slate-700 p-8 text-center">
        <span className="text-5xl mb-4 block">🔥</span>
        <h3 className="text-xl font-bold text-white mb-2">Multi-Agent Expert Debate</h3>
        <p className="text-slate-400 mb-2">
          Watch PhD-level economists debate your policy question in real-time
        </p>
        <p className="text-sm text-slate-500">
          12 specialized agents • 150 turns • Data-grounded discussion
        </p>
      </div>
    )
  }

  const currentSpeakerProfile = currentSpeaker ? getAgentProfile(currentSpeaker) : null

  return (
    <div className="rounded-2xl bg-slate-900/60 border border-purple-500/30 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-purple-900/30 to-slate-900 border-b border-purple-500/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-3xl">🔥</span>
            <div>
              <h3 className="text-xl font-bold text-white tracking-tight">
                LIVE EXPERT DEBATE
              </h3>
              <p className="text-sm text-slate-400">
                {participants.length} experts • {turns.length} turns
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Live indicator */}
            {isLive && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 border border-red-500/30 rounded-full">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span className="text-sm font-bold text-red-400">LIVE</span>
              </div>
            )}

            {/* Summary toggle */}
            {summary && (
              <button
                onClick={() => setShowSummary(!showSummary)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  showSummary 
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' 
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {showSummary ? 'Hide Summary' : 'Show Summary'}
              </button>
            )}

            {/* Auto-scroll toggle */}
            <button
              onClick={() => setAutoScroll(!autoScroll)}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1.5 ${
                autoScroll 
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' 
                  : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
              }`}
            >
              {autoScroll ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  Following
                </>
              ) : (
                <>⏸ Paused</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Optional Summary */}
      {showSummary && summary && (
        <div className="px-6 pt-4">
          <SummaryCard summary={summary} onClose={() => setShowSummary(false)} />
        </div>
      )}

      {/* THE MAIN EVENT: Conversation */}
      <div className="relative">
        <div 
          ref={scrollRef}
          className="p-6 space-y-4 overflow-y-auto"
          style={{ maxHeight: '700px', minHeight: '500px' }}
        >
          {turns.map((turn, index) => (
            <div 
              key={`${turn.agent}-${turn.turn}-${index}`}
              ref={index === turns.length - 1 ? latestMessageRef : null}
            >
              <DebateMessage 
                turn={turn}
                isNew={highlightedIndex === index}
              />
            </div>
          ))}

          {/* Typing indicator */}
          {isLive && currentSpeakerProfile && (
            <DebateMessage 
              turn={{ 
                agent: currentSpeaker!, 
                turn: turns.length + 1, 
                type: 'contribution',
                message: '',
                timestamp: new Date().toISOString()
              }}
              isTyping={true}
            />
          )}
        </div>

        {/* New messages indicator */}
        {!autoScroll && newMessageCount > 0 && (
          <button
            onClick={jumpToLatest}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-cyan-500 text-white rounded-full shadow-lg shadow-cyan-500/30 flex items-center gap-2 hover:bg-cyan-400 transition-all animate-bounce"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            <span className="font-medium">{newMessageCount} new message{newMessageCount > 1 ? 's' : ''}</span>
          </button>
        )}
      </div>

      {/* Phase Progress */}
      <div className="px-6 pb-4">
        <PhaseProgress 
          currentPhase={currentPhase}
          turnsCompleted={turns.length}
          totalTurns={totalExpectedTurns}
        />
      </div>

      {/* Footer: Participating Experts */}
      <div className="px-6 py-3 bg-slate-800/30 border-t border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">
              Participating Experts:
            </span>
            <div className="flex -space-x-2">
              {participants.slice(0, 8).map((profile, idx) => (
                <div 
                  key={profile.name}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sm border-2 border-slate-800 shadow-lg hover:scale-110 transition-transform cursor-pointer"
                  style={{ backgroundColor: `${profile.color}30`, zIndex: 10 - idx }}
                  title={`${profile.name} - ${profile.title}`}
                >
                  {profile.icon}
                </div>
              ))}
              {participants.length > 8 && (
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs bg-slate-700 border-2 border-slate-800">
                  +{participants.length - 8}
                </div>
              )}
            </div>
          </div>

          {isLive && currentSpeakerProfile && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <span>{currentSpeakerProfile.icon}</span>
              <span>{currentSpeakerProfile.name} is speaking...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default LiveDebatePanel
