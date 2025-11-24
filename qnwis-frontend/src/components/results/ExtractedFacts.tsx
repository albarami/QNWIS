import { useState } from 'react'
import type { ExtractedFact } from '../../types/workflow'
import { 
  getIndicatorLabel, 
  categorizeFacts,
  CATEGORY_CONFIG,
  getSourceLabel,
  type FactCategory 
} from '../../utils/indicatorLabels'
import { smartFormat } from '../../utils/formatters'

interface ExtractedFactsProps {
  facts: ExtractedFact[]
}

// Fact item component
const FactItem = ({ fact }: { fact: ExtractedFact }) => {
  const label = getIndicatorLabel(fact.metric)
  const formattedValue = smartFormat(fact.value)
  const sourceLabel = getSourceLabel(fact.source)
  
  return (
    <div className="fact-item bg-slate-900/60 rounded-lg p-3 border border-slate-700/50 hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate" title={label}>
            {label}
          </p>
          <p className="text-xs text-slate-500 mt-0.5" title={fact.metric}>
            {fact.metric !== label && fact.metric.length < 30 ? fact.metric : ''}
          </p>
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold text-cyan-400">{formattedValue}</p>
        </div>
      </div>
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800">
        <span className="text-xs text-slate-500">{sourceLabel}</span>
        {fact.confidence !== undefined && (
          <span className={`text-xs px-1.5 py-0.5 rounded ${
            fact.confidence >= 0.8 ? 'bg-emerald-500/20 text-emerald-400' :
            fact.confidence >= 0.5 ? 'bg-amber-500/20 text-amber-400' :
            'bg-red-500/20 text-red-400'
          }`}>
            {Math.round(fact.confidence * 100)}%
          </span>
        )}
      </div>
    </div>
  )
}

// Category section component
const CategorySection = ({ 
  category, 
  facts, 
  isExpanded, 
  onToggle 
}: { 
  category: FactCategory
  facts: ExtractedFact[]
  isExpanded: boolean
  onToggle: () => void
}) => {
  const config = CATEGORY_CONFIG[category]
  const [showAll, setShowAll] = useState(false)
  const displayFacts = showAll ? facts : facts.slice(0, 4)
  const hasMore = facts.length > 4
  
  return (
    <div className="category-section">
      <button 
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-800/50 transition-colors facts-category-header"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{config.icon}</span>
          <span className="font-medium text-slate-200">{config.label}</span>
          <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
            {facts.length}
          </span>
        </div>
        <span className="text-slate-400 text-sm">
          {isExpanded ? '▼' : '▶'}
        </span>
      </button>
      
      {isExpanded && (
        <div className="mt-2 space-y-2 pl-2">
          {displayFacts.map((fact, index) => (
            <FactItem key={`${fact.metric}-${index}`} fact={fact} />
          ))}
          
          {hasMore && (
            <button 
              onClick={() => setShowAll(!showAll)}
              className="w-full text-center text-xs text-cyan-400 hover:text-cyan-300 py-2"
            >
              {showAll ? 'Show less' : `Show ${facts.length - 4} more...`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export function ExtractedFacts({ facts }: ExtractedFactsProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<FactCategory>>(
    new Set(['economic', 'labor'])
  )
  
  if (!facts.length) {
    return null
  }
  
  // Categorize facts
  const categorizedFacts = categorizeFacts(facts)
  
  // Get unique sources
  const sources = Array.from(new Set(facts.map(f => getSourceLabel(f.source))))
  
  // Toggle category expansion
  const toggleCategory = (category: FactCategory) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(category)) {
      newExpanded.delete(category)
    } else {
      newExpanded.add(category)
    }
    setExpandedCategories(newExpanded)
  }
  
  // Calculate category order by fact count
  const sortedCategories = (Object.keys(CATEGORY_CONFIG) as FactCategory[])
    .filter(cat => categorizedFacts[cat].length > 0)
    .sort((a, b) => categorizedFacts[b].length - categorizedFacts[a].length)

  return (
    <section className="rounded-2xl border border-slate-700 bg-slate-900/40 p-6 space-y-4" data-testid="extracted-facts">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📊</span>
          <div>
            <h3 className="text-lg font-semibold text-white">EVIDENCE BASE</h3>
            <p className="text-xs text-slate-500">Deterministic facts grounding the analysis</p>
          </div>
        </div>
        <span className="text-sm font-medium text-cyan-400 bg-cyan-500/10 px-3 py-1 rounded-full">
          {facts.length} facts
        </span>
      </div>
      
      {/* Category sections */}
      <div className="space-y-3">
        {sortedCategories.map(category => (
          <CategorySection
            key={category}
            category={category}
            facts={categorizedFacts[category]}
            isExpanded={expandedCategories.has(category)}
            onToggle={() => toggleCategory(category)}
          />
        ))}
      </div>
      
      {/* Source summary */}
      <div className="pt-3 border-t border-slate-700">
        <div className="flex items-center flex-wrap gap-2">
          <span className="text-xs text-slate-500">Sources:</span>
          {sources.map(source => (
            <span 
              key={source} 
              className="text-xs bg-slate-800 text-slate-400 px-2 py-1 rounded"
            >
              {source}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
