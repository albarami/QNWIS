import React from 'react'

export interface Tab {
  id: string
  label: string
  icon: string
  badge?: number | string
  isLive?: boolean
}

interface TabNavigationProps {
  tabs: Tab[]
  activeTab: string
  onTabChange: (tabId: string) => void
}

export const TabNavigation: React.FC<TabNavigationProps> = ({
  tabs,
  activeTab,
  onTabChange,
}) => {
  return (
    <div className="flex items-center gap-1 bg-slate-800/50 rounded-xl p-1">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id
        
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              isActive 
                ? 'bg-slate-700 text-white shadow-lg' 
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <span className="text-lg">{tab.icon}</span>
            <span>{tab.label}</span>
            
            {/* Badge */}
            {tab.badge && (
              <span className={`px-1.5 py-0.5 text-xs rounded-full ${
                isActive 
                  ? 'bg-cyan-500/30 text-cyan-300' 
                  : 'bg-slate-600 text-slate-300'
              }`}>
                {tab.badge}
              </span>
            )}
            
            {/* Live indicator */}
            {tab.isLive && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

export default TabNavigation
