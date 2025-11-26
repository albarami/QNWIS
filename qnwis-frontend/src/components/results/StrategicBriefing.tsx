import React, { useState } from 'react'

interface StrategicBriefingProps {
  synthesis: string
  confidence?: number
  timestamp?: string
}

// Parse sections from the strategic briefing
const parseBriefingSections = (text: string) => {
  const sections: { title: string; content: string; icon: string }[] = []
  
  if (!text) return sections
  
  // Define section markers and their icons
  const sectionMarkers = [
    { marker: "EXECUTIVE SUMMARY", icon: "📋" },
    { marker: "EVIDENCE FOUNDATION", icon: "📊" },
    { marker: "SCENARIO ANALYSIS", icon: "🔮" },
    { marker: "EXPERT DELIBERATION", icon: "🎓" },
    { marker: "RISK ASSESSMENT", icon: "⚠️" },
    { marker: "STRATEGIC RECOMMENDATIONS", icon: "🎯" },
    { marker: "DECISION FRAMEWORK", icon: "⚖️" },
    { marker: "CONFIDENCE ASSESSMENT", icon: "📈" },
    { marker: "APPENDICES", icon: "📎" },
    { marker: "MINISTER'S BRIEFING CARD", icon: "📇" },
    { marker: "BOTTOM LINE", icon: "💡" },
    { marker: "KEY NUMBERS", icon: "🔢" },
    { marker: "TOP 3 ACTIONS", icon: "✅" },
  ]
  
  // Split by common section patterns
  const lines = text.split('\n')
  let currentSection = { title: "Overview", content: "", icon: "📄" }
  
  for (const line of lines) {
    const trimmedLine = line.trim()
    
    // Check if this line is a section header
    let foundSection = false
    for (const { marker, icon } of sectionMarkers) {
      if (trimmedLine.toUpperCase().includes(marker) && 
          (trimmedLine.startsWith('#') || trimmedLine.startsWith('##') || 
           trimmedLine.startsWith('*') || trimmedLine.includes('═') ||
           trimmedLine.toUpperCase() === marker)) {
        // Save previous section
        if (currentSection.content.trim()) {
          sections.push({ ...currentSection })
        }
        // Start new section
        currentSection = { 
          title: marker.split(' ').map(w => w.charAt(0) + w.slice(1).toLowerCase()).join(' '),
          content: "", 
          icon 
        }
        foundSection = true
        break
      }
    }
    
    if (!foundSection) {
      currentSection.content += line + '\n'
    }
  }
  
  // Add final section
  if (currentSection.content.trim()) {
    sections.push(currentSection)
  }
  
  return sections
}

// Format content with better styling
const formatContent = (content: string): React.ReactNode => {
  if (!content) return null
  
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []
  
  lines.forEach((line, idx) => {
    const trimmed = line.trim()
    
    // Skip empty lines
    if (!trimmed) {
      elements.push(<div key={idx} className="h-2" />)
      return
    }
    
    // Headers (### or **)
    if (trimmed.startsWith('###') || (trimmed.startsWith('**') && trimmed.endsWith('**'))) {
      const text = trimmed.replace(/^#+\s*/, '').replace(/\*\*/g, '')
      elements.push(
        <h4 key={idx} className="text-lg font-semibold text-cyan-300 mt-4 mb-2">
          {text}
        </h4>
      )
      return
    }
    
    // Bullet points
    if (trimmed.startsWith('-') || trimmed.startsWith('•') || trimmed.startsWith('├') || trimmed.startsWith('└')) {
      const text = trimmed.replace(/^[-•├└─│]\s*/, '')
      elements.push(
        <div key={idx} className="flex gap-2 ml-4 my-1">
          <span className="text-cyan-400">•</span>
          <span className="text-slate-300">{formatInlineText(text)}</span>
        </div>
      )
      return
    }
    
    // Numbered items
    if (/^\d+\./.test(trimmed)) {
      const text = trimmed.replace(/^\d+\.\s*/, '')
      const num = trimmed.match(/^\d+/)?.[0]
      elements.push(
        <div key={idx} className="flex gap-3 ml-4 my-1">
          <span className="text-amber-400 font-semibold min-w-[1.5rem]">{num}.</span>
          <span className="text-slate-300">{formatInlineText(text)}</span>
        </div>
      )
      return
    }
    
    // Table rows (| separated)
    if (trimmed.includes('|') && !trimmed.startsWith('|---')) {
      const cells = trimmed.split('|').filter(c => c.trim())
      elements.push(
        <div key={idx} className="grid grid-cols-4 gap-2 text-sm py-1 border-b border-slate-700/50">
          {cells.map((cell, cellIdx) => (
            <span key={cellIdx} className={cellIdx === 0 ? "text-white font-medium" : "text-slate-400"}>
              {cell.trim()}
            </span>
          ))}
        </div>
      )
      return
    }
    
    // Box borders (═══)
    if (trimmed.includes('═') || trimmed.includes('───') || trimmed.includes('┌') || trimmed.includes('└')) {
      return // Skip decorative borders
    }
    
    // Key-value pairs (Key: Value)
    if (trimmed.includes(':') && !trimmed.startsWith('http')) {
      const [key, ...valueParts] = trimmed.split(':')
      const value = valueParts.join(':').trim()
      if (key.length < 30 && value) {
        elements.push(
          <div key={idx} className="flex gap-2 my-1">
            <span className="text-slate-400 font-medium">{key}:</span>
            <span className="text-white">{formatInlineText(value)}</span>
          </div>
        )
        return
      }
    }
    
    // Regular paragraph
    elements.push(
      <p key={idx} className="text-slate-300 my-2 leading-relaxed">
        {formatInlineText(trimmed)}
      </p>
    )
  })
  
  return elements
}

// Format inline text (bold, citations, etc.)
const formatInlineText = (text: string): React.ReactNode => {
  // Handle **bold** and [citations]
  const parts = text.split(/(\*\*[^*]+\*\*|\[Per extraction:[^\]]+\]|\[.*?\])/g)
  
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx} className="text-white font-semibold">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('[Per extraction:') || part.match(/^\[.*:.*\d{4}\]$/)) {
      return (
        <span key={idx} className="text-cyan-400 text-xs bg-cyan-900/30 px-1 rounded mx-1">
          {part}
        </span>
      )
    }
    return part
  })
}

export function StrategicBriefing({ synthesis, confidence = 0, timestamp }: StrategicBriefingProps) {
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([0]))
  
  if (!synthesis) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-8 text-center">
        <span className="text-4xl mb-4 block">📋</span>
        <h3 className="text-lg font-semibold text-white mb-2">Strategic Briefing</h3>
        <p className="text-slate-400">Awaiting synthesis completion...</p>
      </div>
    )
  }
  
  const sections = parseBriefingSections(synthesis)
  
  // If no sections parsed, show raw text
  if (sections.length === 0 || (sections.length === 1 && sections[0].title === "Overview")) {
    return (
      <div className="rounded-2xl border border-amber-400/30 bg-gradient-to-br from-slate-900 to-slate-800 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-amber-900/50 to-amber-800/30 px-6 py-4 border-b border-amber-400/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">📋</span>
              <div>
                <h2 className="text-xl font-bold text-amber-100">STRATEGIC INTELLIGENCE BRIEFING</h2>
                <p className="text-sm text-amber-200/70">Qatar Ministry of Labour • Confidential</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-amber-300">{Math.round(confidence * 100)}%</div>
              <div className="text-xs text-amber-200/70">Confidence</div>
            </div>
          </div>
        </div>
        
        {/* Content */}
        <div className="p-6">
          <div className="prose prose-invert max-w-none">
            <pre className="whitespace-pre-wrap text-slate-200 font-sans text-sm leading-relaxed bg-slate-800/50 rounded-xl p-6 border border-slate-700">
              {synthesis}
            </pre>
          </div>
        </div>
      </div>
    )
  }
  
  const toggleSection = (index: number) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }
  
  return (
    <div className="rounded-2xl border border-amber-400/30 bg-gradient-to-br from-slate-900 to-slate-800 overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="bg-gradient-to-r from-amber-900/50 via-amber-800/30 to-slate-900 px-6 py-5 border-b border-amber-400/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-amber-500/20 flex items-center justify-center border border-amber-400/30">
              <span className="text-3xl">🏛️</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 bg-red-500/20 text-red-300 rounded uppercase tracking-wider font-medium">
                  Confidential
                </span>
                <span className="text-xs text-slate-500">•</span>
                <span className="text-xs text-slate-400">QNWIS Enterprise Intelligence</span>
              </div>
              <h2 className="text-2xl font-bold text-white mt-1 tracking-tight">
                STRATEGIC INTELLIGENCE BRIEFING
              </h2>
              <p className="text-sm text-amber-200/70 mt-0.5">
                Qatar Ministry of Labour • {timestamp || new Date().toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="text-right bg-slate-800/50 rounded-xl px-4 py-3 border border-slate-700">
            <div className="text-3xl font-bold text-amber-300">{Math.round(confidence * 100)}%</div>
            <div className="text-xs text-slate-400 uppercase tracking-wider">Confidence Score</div>
          </div>
        </div>
        
        {/* Section navigation */}
        <div className="flex flex-wrap gap-2 mt-4">
          {sections.map((section, idx) => (
            <button
              key={idx}
              onClick={() => toggleSection(idx)}
              className={`px-3 py-1.5 text-xs rounded-lg transition-all ${
                expandedSections.has(idx)
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-400/30'
                  : 'bg-slate-700/50 text-slate-400 border border-slate-600 hover:bg-slate-700'
              }`}
            >
              {section.icon} {section.title}
            </button>
          ))}
        </div>
      </div>
      
      {/* Sections */}
      <div className="divide-y divide-slate-700/50">
        {sections.map((section, idx) => (
          <div key={idx} className="transition-all">
            <button
              onClick={() => toggleSection(idx)}
              className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{section.icon}</span>
                <span className="font-semibold text-white text-lg">{section.title}</span>
              </div>
              <svg 
                className={`w-5 h-5 text-slate-400 transition-transform ${expandedSections.has(idx) ? 'rotate-180' : ''}`}
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {expandedSections.has(idx) && (
              <div className="px-6 pb-6 animate-fadeIn">
                <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/50">
                  {formatContent(section.content)}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      {/* Footer */}
      <div className="px-6 py-4 bg-slate-800/50 border-t border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>🔒</span>
          <span>Generated by QNWIS Multi-Agent Intelligence System</span>
        </div>
        <div className="text-xs text-slate-500">
          Word count: {synthesis.split(/\s+/).length.toLocaleString()}
        </div>
      </div>
    </div>
  )
}

export default StrategicBriefing

