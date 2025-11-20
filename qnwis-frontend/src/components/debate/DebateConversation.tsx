import React, { useEffect, useRef } from 'react'
import { ConversationTurn } from '../../types/workflow'

interface DebateConversationProps {
  turns: ConversationTurn[]
}

export const DebateConversation: React.FC<DebateConversationProps> = ({ turns }) => {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [turns])

  if (!turns || turns.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg">
        Waiting for debate to start...
      </div>
    )
  }

  const getTurnColor = (type: ConversationTurn['type']) => {
    switch (type) {
      case 'opening_statement':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
      case 'challenge':
        return 'border-red-500 bg-red-50 dark:bg-red-900/20'
      case 'response':
        return 'border-green-500 bg-green-50 dark:bg-green-900/20'
      case 'contribution':
        return 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
      case 'resolution':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20'
      case 'consensus':
        return 'border-teal-500 bg-teal-50 dark:bg-teal-900/20'
      case 'edge_case_analysis':
        return 'border-orange-500 bg-orange-50 dark:bg-orange-900/20'
      case 'risk_identification':
        return 'border-rose-500 bg-rose-50 dark:bg-rose-900/20'
      case 'risk_assessment':
        return 'border-pink-500 bg-pink-50 dark:bg-pink-900/20'
      case 'consensus_synthesis':
        return 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
      case 'final_position':
        return 'border-cyan-500 bg-cyan-50 dark:bg-cyan-900/20'
      default:
        return 'border-gray-300 bg-gray-50 dark:bg-gray-800'
    }
  }

  const getTurnIcon = (type: ConversationTurn['type']) => {
    switch (type) {
      case 'opening_statement': return '📢'
      case 'challenge': return '⚔️'
      case 'response': return '🛡️'
      case 'contribution': return '💡'
      case 'resolution': return '⚖️'
      case 'consensus': return '🤝'
      case 'edge_case_analysis': return '🧪'
      case 'risk_identification': return '⚠️'
      case 'risk_assessment': return '🔍'
      case 'consensus_synthesis': return '📝'
      case 'final_position': return '🏁'
      default: return '💬'
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Live Debate Feed
        </h3>
        <span className="px-2 py-1 text-sm font-medium text-blue-600 bg-blue-100 rounded-full dark:bg-blue-900 dark:text-blue-200">
          {turns.length} turns
        </span>
      </div>
      
      <div 
        ref={scrollRef}
        className="space-y-4 max-h-[600px] overflow-y-auto p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
      >
        {turns.map((turn, index) => (
          <div 
            key={index} 
            className={`p-4 rounded-lg border-l-4 ${getTurnColor(turn.type)} transition-all duration-300 ease-in-out`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-xl" role="img" aria-label={turn.type}>
                  {getTurnIcon(turn.type)}
                </span>
                <div>
                  <p className="font-bold text-gray-900 dark:text-white">
                    {turn.agent}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {turn.type.replace(/_/g, ' ')}
                  </p>
                </div>
              </div>
              <span className="text-xs text-gray-400 dark:text-gray-500">
                Turn {turn.turn} • {new Date(turn.timestamp).toLocaleTimeString()}
              </span>
            </div>
            
            <div className="mt-2 text-gray-700 dark:text-gray-300 prose dark:prose-invert max-w-none text-sm">
              <p className="whitespace-pre-wrap">{turn.message}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

