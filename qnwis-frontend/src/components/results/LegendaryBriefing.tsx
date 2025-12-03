import React, { useState, useMemo } from 'react'

interface LegendaryBriefingProps {
  synthesis: string
  confidence?: number
  stats?: {
    n_facts?: number
    n_scenarios?: number
    n_turns?: number
    n_experts?: number
    n_challenges?: number
    n_consensus?: number
  }
}

// Parse the briefing into structured sections
const parseLegendaryBriefing = (text: string) => {
  if (!text) return { sections: [], verdict: '', ministerCard: '' }
  
  // CRITICAL FIX: Strip LLM preambles like "Certainly." or "Below is..."
  // LLMs often add conversational text before the actual structured content
  let cleanText = text
  
  // Common LLM preamble patterns to strip
  const preamblePatterns = [
    /^(Certainly|Sure|Absolutely|Of course|Here is|Below is)[^═#]*?(?=═|##?\s*I\.)/is,
    /^[^═#]*?(?=═{10,})/s,  // Strip everything before the first separator line
  ]
  
  for (const pattern of preamblePatterns) {
    const match = cleanText.match(pattern)
    if (match && match[0].length < 500) {  // Don't strip too much
      cleanText = cleanText.slice(match[0].length).trim()
      break
    }
  }
  
  text = cleanText
  
  const sections: { id: string; title: string; icon: string; content: string; priority: number }[] = []
  
  // Extract Minister's Briefing Card (special handling)
  const ministerCardMatch = text.match(/MINISTER'S BRIEFING CARD[\s\S]*?═{50,}/g)
  const ministerCard = ministerCardMatch ? ministerCardMatch[ministerCardMatch.length - 1] : ''
  
  // Extract verdict
  const verdictMatch = text.match(/\*\*VERDICT:\s*([A-Z]+)\*\*/i)
  const verdict = verdictMatch ? verdictMatch[1] : ''
  
  // Section definitions with visual metadata
  const sectionDefs = [
    { pattern: /##?\s*I\.?\s*STRATEGIC VERDICT/i, id: 'verdict', title: 'Strategic Verdict', icon: '⚡', priority: 1 },
    { pattern: /##?\s*II\.?\s*THE QUESTION DECONSTRUCTED/i, id: 'question', title: 'Question Analysis', icon: '🔍', priority: 2 },
    { pattern: /##?\s*III\.?\s*EVIDENCE FOUNDATION/i, id: 'evidence', title: 'Evidence Foundation', icon: '📊', priority: 3 },
    { pattern: /##?\s*IV\.?\s*SCENARIO ANALYSIS/i, id: 'scenarios', title: 'Scenario Analysis', icon: '🔮', priority: 4 },
    { pattern: /##?\s*V\.?\s*EXPERT DELIBERATION/i, id: 'deliberation', title: 'Expert Deliberation', icon: '🎓', priority: 5 },
    { pattern: /##?\s*VI\.?\s*RISK INTELLIGENCE/i, id: 'risks', title: 'Risk Intelligence', icon: '⚠️', priority: 6 },
    { pattern: /##?\s*VII\.?\s*STRATEGIC RECOMMENDATIONS/i, id: 'recommendations', title: 'Strategic Recommendations', icon: '🎯', priority: 7 },
    { pattern: /##?\s*VIII\.?\s*CONFIDENCE ASSESSMENT/i, id: 'confidence', title: 'Confidence Assessment', icon: '📈', priority: 8 },
    { pattern: /##?\s*IX\.?\s*MINISTER'S BRIEFING CARD/i, id: 'minister', title: "Minister's Card", icon: '📋', priority: 9 },
  ]
  
  // Find section boundaries
  const boundaries: { def: typeof sectionDefs[0]; start: number }[] = []
  for (const def of sectionDefs) {
    const match = text.match(def.pattern)
    if (match && match.index !== undefined) {
      boundaries.push({ def, start: match.index })
    }
  }
  
  // Sort by position
  boundaries.sort((a, b) => a.start - b.start)
  
  // Extract section contents
  for (let i = 0; i < boundaries.length; i++) {
    const current = boundaries[i]
    const next = boundaries[i + 1]
    const endPos = next ? next.start : text.length
    const content = text.slice(current.start, endPos).trim()
    
    sections.push({
      id: current.def.id,
      title: current.def.title,
      icon: current.def.icon,
      content,
      priority: current.def.priority,
    })
  }
  
  return { sections, verdict, ministerCard }
}

// Format content with rich styling
const FormatContent: React.FC<{ content: string; sectionId: string }> = ({ content, sectionId: _sectionId }) => {
  // sectionId reserved for future section-specific formatting
  void _sectionId
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []
  
  lines.forEach((line, idx) => {
    const trimmed = line.trim()
    if (!trimmed) {
      elements.push(<div key={idx} className="h-2" />)
      return
    }
    
    // Skip section headers (already shown in accordion)
    if (trimmed.match(/^##?\s*[IVX]+\./)) return
    
    // Verdict highlight
    if (trimmed.startsWith('**VERDICT:')) {
      const verdictWord = trimmed.match(/VERDICT:\s*([A-Z]+)/)?.[1] || ''
      const verdictColors: Record<string, string> = {
        'APPROVE': 'from-green-500 to-emerald-600',
        'ACCELERATE': 'from-green-500 to-emerald-600',
        'INCREASE': 'from-green-500 to-emerald-600',
        'HOLD': 'from-amber-500 to-yellow-600',
        'PIVOT': 'from-amber-500 to-orange-600',
        'DECREASE': 'from-orange-500 to-red-600',
        'REJECT': 'from-red-500 to-red-700',
      }
      const gradientClass = verdictColors[verdictWord] || 'from-cyan-500 to-blue-600'
      
      elements.push(
        <div key={idx} className="my-6 text-center">
          <span className={`inline-block px-8 py-4 text-3xl font-black tracking-wider text-white bg-gradient-to-r ${gradientClass} rounded-xl shadow-lg transform hover:scale-105 transition-transform`}>
            VERDICT: {verdictWord}
          </span>
        </div>
      )
      return
    }
    
    // Box decorations (═══)
    if (trimmed.match(/^[═─┌┐└┘├┤│┬┴┼]{3,}$/)) {
      elements.push(<hr key={idx} className="border-slate-600 my-4" />)
      return
    }
    
    // Table rows with │
    if (trimmed.includes('│') && !trimmed.startsWith('├') && !trimmed.startsWith('└')) {
      const cells = trimmed.split('│').filter(c => c.trim())
      if (cells.length >= 2) {
        elements.push(
          <div key={idx} className="grid grid-cols-2 md:grid-cols-4 gap-2 py-2 border-b border-slate-700/50">
            {cells.map((cell, i) => (
              <span key={i} className={`text-sm ${i === 0 ? 'text-white font-medium' : 'text-slate-400'}`}>
                {cell.trim()}
              </span>
            ))}
          </div>
        )
        return
      }
    }
    
    // Headers (**, ###)
    if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
      const text = trimmed.replace(/\*\*/g, '')
      elements.push(
        <h4 key={idx} className="text-lg font-bold text-cyan-300 mt-6 mb-3 flex items-center gap-2">
          <span className="w-1 h-6 bg-cyan-400 rounded-full" />
          {text}
        </h4>
      )
      return
    }
    
    if (trimmed.startsWith('###')) {
      const text = trimmed.replace(/^#+\s*/, '')
      elements.push(
        <h5 key={idx} className="text-base font-semibold text-slate-200 mt-4 mb-2">
          {text}
        </h5>
      )
      return
    }
    
    // Bullet points
    if (trimmed.startsWith('•') || trimmed.startsWith('-') || trimmed.startsWith('*')) {
      const text = trimmed.replace(/^[•\-*]\s*/, '')
      elements.push(
        <div key={idx} className="flex gap-3 ml-4 my-2">
          <span className="text-cyan-400 mt-1">•</span>
          <span className="text-slate-300 leading-relaxed">{formatInline(text)}</span>
        </div>
      )
      return
    }
    
    // Numbered items
    if (/^\d+\./.test(trimmed)) {
      const text = trimmed.replace(/^\d+\.\s*/, '')
      const num = trimmed.match(/^\d+/)?.[0]
      elements.push(
        <div key={idx} className="flex gap-3 ml-4 my-2">
          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-500/20 text-amber-300 text-sm font-bold flex items-center justify-center">
            {num}
          </span>
          <span className="text-slate-300 leading-relaxed">{formatInline(text)}</span>
        </div>
      )
      return
    }
    
    // Citations [Fact #X], [Turn Y], etc.
    if (trimmed.includes('[') && trimmed.includes(']')) {
      elements.push(
        <p key={idx} className="text-slate-300 my-2 leading-relaxed">
          {formatInline(trimmed)}
        </p>
      )
      return
    }
    
    // Regular paragraph
    elements.push(
      <p key={idx} className="text-slate-300 my-2 leading-relaxed">
        {formatInline(trimmed)}
      </p>
    )
  })
  
  return <>{elements}</>
}

// Format inline text with citations and styling
const formatInline = (text: string): React.ReactNode => {
  // Split by citations, bold, and other markers
  const parts = text.split(/(\*\*[^*]+\*\*|\[[^\]]+\])/g)
  
  return parts.map((part, idx) => {
    // Bold text
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx} className="text-white font-semibold">{part.slice(2, -2)}</strong>
    }
    
    // Citations
    if (part.startsWith('[') && part.endsWith(']')) {
      const citation = part.slice(1, -1)
      let bgColor = 'bg-slate-700'
      let textColor = 'text-slate-300'
      
      if (citation.includes('Fact')) {
        bgColor = 'bg-blue-900/50'
        textColor = 'text-blue-300'
      } else if (citation.includes('Turn') || citation.includes('Consensus')) {
        bgColor = 'bg-purple-900/50'
        textColor = 'text-purple-300'
      } else if (citation.includes('Scenario')) {
        bgColor = 'bg-amber-900/50'
        textColor = 'text-amber-300'
      } else if (citation.includes('Risk') || citation.includes('Red Flag')) {
        bgColor = 'bg-red-900/50'
        textColor = 'text-red-300'
      }
      
      return (
        <span key={idx} className={`${bgColor} ${textColor} text-xs px-1.5 py-0.5 rounded mx-0.5 font-medium`}>
          {citation}
        </span>
      )
    }
    
    return part
  })
}

// Stats display component
const StatsBar: React.FC<{ stats: LegendaryBriefingProps['stats'] }> = ({ stats }) => {
  if (!stats) return null
  
  const items = [
    { label: 'Facts', value: stats.n_facts || 0, icon: '📊' },
    { label: 'Scenarios', value: stats.n_scenarios || 0, icon: '🔮' },
    { label: 'Debate Turns', value: stats.n_turns || 0, icon: '💬' },
    { label: 'Experts', value: stats.n_experts || 0, icon: '🎓' },
    { label: 'Challenges', value: stats.n_challenges || 0, icon: '⚔️' },
    { label: 'Consensus', value: stats.n_consensus || 0, icon: '🤝' },
  ]
  
  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-2 p-4 bg-slate-800/50 rounded-xl border border-slate-700">
      {items.map(item => (
        <div key={item.label} className="text-center">
          <div className="text-xl">{item.icon}</div>
          <div className="text-2xl font-bold text-white">{item.value}</div>
          <div className="text-xs text-slate-500 uppercase tracking-wider">{item.label}</div>
        </div>
      ))}
    </div>
  )
}

export function LegendaryBriefing({ synthesis, confidence = 0.75, stats }: LegendaryBriefingProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['verdict']))
  const [showMinisterCard, setShowMinisterCard] = useState(false)
  
  const { sections, verdict, ministerCard } = useMemo(
    () => parseLegendaryBriefing(synthesis),
    [synthesis]
  )
  
  const toggleSection = (id: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  
  const expandAll = () => {
    setExpandedSections(new Set(sections.map(s => s.id)))
  }
  
  const collapseAll = () => {
    setExpandedSections(new Set(['verdict']))
  }
  
  if (!synthesis) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-12 text-center">
        <div className="animate-pulse">
          <span className="text-6xl mb-6 block">🏛️</span>
          <h3 className="text-xl font-bold text-white mb-3">Generating Strategic Intelligence Briefing</h3>
          <p className="text-slate-400 mb-4">Synthesizing {stats?.n_facts || 0} facts, {stats?.n_turns || 0} debate turns...</p>
          <div className="w-48 h-2 bg-slate-700 rounded-full mx-auto overflow-hidden">
            <div className="h-full bg-gradient-to-r from-cyan-500 to-amber-500 rounded-full animate-pulse" style={{ width: '60%' }} />
          </div>
        </div>
      </div>
    )
  }
  
  const confPercent = typeof confidence === 'number' && confidence <= 1 ? Math.round(confidence * 100) : confidence
  
  return (
    <div className="legendary-briefing">
      {/* Header */}
      <div className="rounded-t-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border border-amber-500/30 overflow-hidden">
        {/* Top Banner */}
        <div className="bg-gradient-to-r from-amber-900/60 via-amber-800/40 to-amber-900/60 px-6 py-2 border-b border-amber-500/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 bg-red-500/30 text-red-300 text-xs font-bold rounded uppercase tracking-wider">
                Confidential
              </span>
              <span className="text-xs text-amber-300/70">MINISTERIAL BRIEFING</span>
            </div>
            <div className="text-xs text-amber-300/70">
              QNWIS-{new Date().toISOString().slice(0,10).replace(/-/g, '')}
            </div>
          </div>
        </div>
        
        {/* Main Header */}
        <div className="px-6 py-6">
          <div className="flex items-start justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500/30 to-amber-600/10 flex items-center justify-center border border-amber-400/30 shadow-lg shadow-amber-500/20">
                <span className="text-4xl">🏛️</span>
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-black text-white tracking-tight">
                  STRATEGIC INTELLIGENCE BRIEFING
                </h1>
                <p className="text-amber-200/70 mt-1">
                  Qatar Ministry of Labour • {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
              </div>
            </div>
            
            {/* Confidence Gauge */}
            <div className="text-center bg-slate-800/60 rounded-xl px-6 py-3 border border-slate-700">
              <div className="relative w-20 h-20 mx-auto">
                <svg className="w-20 h-20 transform -rotate-90">
                  <circle cx="40" cy="40" r="35" stroke="#1e293b" strokeWidth="6" fill="none" />
                  <circle 
                    cx="40" cy="40" r="35" 
                    stroke="url(#confidence-gradient)" 
                    strokeWidth="6" 
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray={`${confPercent * 2.2} 220`}
                  />
                  <defs>
                    <linearGradient id="confidence-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#f59e0b" />
                      <stop offset="100%" stopColor="#22c55e" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-2xl font-bold text-white">{confPercent}%</span>
                </div>
              </div>
              <div className="text-xs text-slate-400 uppercase tracking-wider mt-1">Confidence</div>
            </div>
          </div>
          
          {/* Stats Bar */}
          <div className="mt-6">
            <StatsBar stats={stats} />
          </div>
          
          {/* Quick Actions */}
          <div className="flex items-center gap-3 mt-4">
            <button
              onClick={() => setShowMinisterCard(!showMinisterCard)}
              className="px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              📋 Minister&apos;s Card
            </button>
            <button onClick={expandAll} className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm transition-colors">
              Expand All
            </button>
            <button onClick={collapseAll} className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm transition-colors">
              Collapse
            </button>
          </div>
        </div>
      </div>
      
      {/* Minister's Card Modal */}
      {showMinisterCard && ministerCard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={() => setShowMinisterCard(false)}>
          <div 
            className="max-w-2xl w-full bg-slate-900 rounded-2xl border border-amber-500/30 shadow-2xl p-6 max-h-[90vh] overflow-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-amber-300">📋 Minister&apos;s Briefing Card</h3>
              <button onClick={() => setShowMinisterCard(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono bg-slate-800/50 p-4 rounded-lg">
              {ministerCard}
            </pre>
          </div>
        </div>
      )}
      
      {/* Sections */}
      <div className="border-x border-b border-amber-500/30 rounded-b-2xl bg-slate-900/80 divide-y divide-slate-700/50">
        {sections.length > 0 ? (
          sections.map(section => (
            <div key={section.id} className="transition-all">
              {/* Section Header */}
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors group"
              >
                <div className="flex items-center gap-4">
                  <span className="text-2xl group-hover:scale-110 transition-transform">{section.icon}</span>
                  <div className="text-left">
                    <span className="font-bold text-white text-lg">{section.title}</span>
                    {section.id === 'verdict' && verdict && (
                      <span className={`ml-3 px-2 py-0.5 text-xs font-bold rounded ${
                        ['APPROVE', 'ACCELERATE', 'INCREASE'].includes(verdict) ? 'bg-green-500/20 text-green-300' :
                        ['REJECT', 'DECREASE'].includes(verdict) ? 'bg-red-500/20 text-red-300' :
                        'bg-amber-500/20 text-amber-300'
                      }`}>
                        {verdict}
                      </span>
                    )}
                  </div>
                </div>
                <svg 
                  className={`w-5 h-5 text-slate-400 transition-transform duration-300 ${
                    expandedSections.has(section.id) ? 'rotate-180' : ''
                  }`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              
              {/* Section Content */}
              {expandedSections.has(section.id) && (
                <div className="px-6 pb-6 animate-fadeIn">
                  <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                    <FormatContent content={section.content} sectionId={section.id} />
                  </div>
                </div>
              )}
            </div>
          ))
        ) : (
          /* FALLBACK: Show raw synthesis when no sections detected */
          <div className="p-6">
            <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
              <div className="prose prose-invert prose-sm max-w-none">
                <pre className="whitespace-pre-wrap text-sm text-slate-300 font-sans leading-relaxed">
                  {synthesis}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="mt-4 text-center text-xs text-slate-500">
        <p>Generated by QNWIS Enterprise Intelligence System • Qatar Ministry of Labour</p>
        <p className="mt-1">
          Analysis equivalent to 8-12 weeks of consulting engagement • 
          {synthesis.split(/\s+/).length.toLocaleString()} words
        </p>
      </div>
    </div>
  )
}

export default LegendaryBriefing

