/**
 * Agent Profiles for QNWIS Multi-Agent System
 * 
 * Uses first names only for cultural sensitivity in Qatari ministerial context.
 * Maps technical agent identifiers to user-friendly display profiles.
 */

export interface AgentProfile {
  name: string
  title: string
  icon: string
  color: string
  description: string
}

/**
 * Agent profiles with Arabic first names for cultural appropriateness.
 * Colors are distinct for visual differentiation in the debate view.
 */
export const AGENT_PROFILES: Record<string, AgentProfile> = {
  // LLM-powered analysis agents
  micro_economist: {
    name: 'Dr. Fatima',
    title: 'Microeconomic Analysis',
    icon: '📊',
    color: '#3B82F6', // blue
    description: 'Project-level efficiency and market dynamics specialist',
  },
  MicroEconomist: {
    name: 'Dr. Fatima',
    title: 'Microeconomic Analysis',
    icon: '📊',
    color: '#3B82F6',
    description: 'Project-level efficiency and market dynamics specialist',
  },
  macro_economist: {
    name: 'Dr. Hassan',
    title: 'Macroeconomic Strategy',
    icon: '📈',
    color: '#10B981', // green
    description: 'National economic policy and strategic planning expert',
  },
  MacroEconomist: {
    name: 'Dr. Hassan',
    title: 'Macroeconomic Strategy',
    icon: '📈',
    color: '#10B981',
    description: 'National economic policy and strategic planning expert',
  },
  skills_agent: {
    name: 'Dr. Mariam',
    title: 'Workforce Development',
    icon: '🎓',
    color: '#8B5CF6', // purple
    description: 'Skills training and human capital development specialist',
  },
  SkillsAgent: {
    name: 'Dr. Mariam',
    title: 'Workforce Development',
    icon: '🎓',
    color: '#8B5CF6',
    description: 'Skills training and human capital development specialist',
  },
  nationalization_agent: {
    name: 'Dr. Khalid',
    title: 'Qatarization Policy',
    icon: '🏛️',
    color: '#F59E0B', // amber
    description: 'National workforce integration and Qatarization expert',
  },
  NationalizationAgent: {
    name: 'Dr. Khalid',
    title: 'Qatarization Policy',
    icon: '🏛️',
    color: '#F59E0B',
    description: 'National workforce integration and Qatarization expert',
  },
  Nationalization: {
    name: 'Dr. Khalid',
    title: 'Qatarization Policy',
    icon: '🏛️',
    color: '#F59E0B',
    description: 'National workforce integration and Qatarization expert',
  },
  pattern_detective: {
    name: 'Dr. Noura',
    title: 'Pattern Analysis',
    icon: '🔍',
    color: '#EC4899', // pink
    description: 'Data patterns and anomaly detection specialist',
  },
  PatternDetective: {
    name: 'Dr. Noura',
    title: 'Pattern Analysis',
    icon: '🔍',
    color: '#EC4899',
    description: 'Data patterns and anomaly detection specialist',
  },
  PatternDetectiveLLM: {
    name: 'Dr. Noura',
    title: 'Pattern Analysis',
    icon: '🔍',
    color: '#EC4899',
    description: 'Data patterns and anomaly detection specialist',
  },
  
  // Deterministic analysis agents
  sector_analysis: {
    name: 'Dr. Ahmed',
    title: 'Sector Analysis',
    icon: '🏭',
    color: '#06B6D4', // cyan
    description: 'Industry sector trends and comparative analysis',
  },
  SectorAnalysis: {
    name: 'Dr. Ahmed',
    title: 'Sector Analysis',
    icon: '🏭',
    color: '#06B6D4',
    description: 'Industry sector trends and comparative analysis',
  },
  wage_analysis: {
    name: 'Dr. Layla',
    title: 'Wage Analysis',
    icon: '💰',
    color: '#84CC16', // lime
    description: 'Compensation structures and wage policy specialist',
  },
  WageAnalysis: {
    name: 'Dr. Layla',
    title: 'Wage Analysis',
    icon: '💰',
    color: '#84CC16',
    description: 'Compensation structures and wage policy specialist',
  },
  regional_comparison: {
    name: 'Dr. Omar',
    title: 'Regional Comparison',
    icon: '🌍',
    color: '#F97316', // orange
    description: 'GCC and international benchmarking expert',
  },
  RegionalComparison: {
    name: 'Dr. Omar',
    title: 'Regional Comparison',
    icon: '🌍',
    color: '#F97316',
    description: 'GCC and international benchmarking expert',
  },
  labor_market: {
    name: 'Dr. Sara',
    title: 'Labor Market',
    icon: '👥',
    color: '#14B8A6', // teal
    description: 'Employment trends and labor market dynamics',
  },
  LaborMarket: {
    name: 'Dr. Sara',
    title: 'Labor Market',
    icon: '👥',
    color: '#14B8A6',
    description: 'Employment trends and labor market dynamics',
  },
  demographic_analysis: {
    name: 'Dr. Yusuf',
    title: 'Demographics',
    icon: '📋',
    color: '#6366F1', // indigo
    description: 'Population trends and demographic analysis',
  },
  DemographicAnalysis: {
    name: 'Dr. Yusuf',
    title: 'Demographics',
    icon: '📋',
    color: '#6366F1',
    description: 'Population trends and demographic analysis',
  },
  economic_indicators: {
    name: 'Dr. Maha',
    title: 'Economic Indicators',
    icon: '📉',
    color: '#EF4444', // red
    description: 'Macroeconomic indicators and trend analysis',
  },
  EconomicIndicators: {
    name: 'Dr. Maha',
    title: 'Economic Indicators',
    icon: '📉',
    color: '#EF4444',
    description: 'Macroeconomic indicators and trend analysis',
  },
  energy_sector: {
    name: 'Dr. Rashid',
    title: 'Energy Sector',
    icon: '⚡',
    color: '#FBBF24', // yellow
    description: 'Oil, gas, and energy sector specialist',
  },
  EnergySector: {
    name: 'Dr. Rashid',
    title: 'Energy Sector',
    icon: '⚡',
    color: '#FBBF24',
    description: 'Oil, gas, and energy sector specialist',
  },
  
  // Backend workflow agents
  financial: {
    name: 'Dr. Fatima',
    title: 'Financial Analysis',
    icon: '💹',
    color: '#3B82F6',
    description: 'Financial modeling and investment analysis specialist',
  },
  market: {
    name: 'Dr. Hassan',
    title: 'Market Analysis',
    icon: '📈',
    color: '#10B981',
    description: 'Market trends and competitive analysis expert',
  },
  operations: {
    name: 'Dr. Ahmed',
    title: 'Operations Analysis',
    icon: '🏭',
    color: '#06B6D4',
    description: 'Operational efficiency and process optimization',
  },
  research: {
    name: 'Dr. Mariam',
    title: 'Research Analysis',
    icon: '🔬',
    color: '#8B5CF6',
    description: 'Research methodology and evidence synthesis',
  },
  
  // Special debate roles
  DataValidator: {
    name: 'Data Validator',
    title: 'Quality Assurance',
    icon: '✅',
    color: '#22C55E',
    description: 'Data quality and integrity verification',
  },
  Moderator: {
    name: 'Moderator',
    title: 'Debate Facilitator',
    icon: '⚖️',
    color: '#64748B',
    description: 'Debate coordination and consensus building',
  },
}

/**
 * Get agent profile by technical name.
 * Returns a default profile if agent is not found.
 */
export function getAgentProfile(agentName: string): AgentProfile {
  // Try direct lookup
  if (AGENT_PROFILES[agentName]) {
    return AGENT_PROFILES[agentName]
  }
  
  // Try case-insensitive lookup
  const normalizedName = agentName.toLowerCase().replace(/[_\s]/g, '')
  for (const [key, profile] of Object.entries(AGENT_PROFILES)) {
    if (key.toLowerCase().replace(/[_\s]/g, '') === normalizedName) {
      return profile
    }
  }
  
  // Return default profile for unknown agents
  return {
    name: agentName.split(/[_\s]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
    title: 'Analysis Agent',
    icon: '🤖',
    color: '#64748B', // slate
    description: 'Specialized analysis agent',
  }
}

/**
 * Get a consistent color for an agent based on their index in a list.
 * Useful when displaying multiple agents in sequence.
 */
export const AGENT_COLORS = [
  '#3B82F6', // blue
  '#10B981', // green
  '#8B5CF6', // purple
  '#F59E0B', // amber
  '#EC4899', // pink
  '#06B6D4', // cyan
  '#84CC16', // lime
  '#F97316', // orange
  '#14B8A6', // teal
  '#6366F1', // indigo
  '#EF4444', // red
  '#FBBF24', // yellow
]

export function getAgentColorByIndex(index: number): string {
  return AGENT_COLORS[index % AGENT_COLORS.length]
}

