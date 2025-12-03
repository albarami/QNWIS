/**
 * Engine B Types - Monte Carlo, Sensitivity Analysis, Cross-Scenario Results
 * 
 * These types represent the quantitative foundation of the NSIC system.
 * Engine B runs GPU-accelerated computations for each scenario.
 */

export interface MonteCarloResult {
  successRate: number           // 0-1 (e.g., 0.684 = 68.4%)
  meanOutcome: number
  stdDev: number
  simulations: number           // e.g., 10000
  confidenceInterval: [number, number]  // [lower, upper] at 95%
  distribution?: number[]       // histogram bins for visualization
}

export interface SensitivityDriver {
  driver: string                // e.g., "training_pipeline"
  label: string                 // e.g., "Training Pipeline Capacity"
  contribution: number          // 0-1, percentage of variance
  direction: 'positive' | 'negative' | 'mixed'
}

export interface ForecastResult {
  trend: 'increasing' | 'stable' | 'decreasing'
  projection: number            // projected value at horizon
  horizon: string               // e.g., "2028"
}

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export interface ScenarioAssumptions {
  [key: string]: number         // e.g., { gdp: 0.5, risk: 0.7, workforce: 1.3 }
}

export interface EngineBScenarioResult {
  scenarioId: string
  scenarioName: string
  scenarioIcon: string          // e.g., "📉", "🏆", "🦠"
  description: string | null
  assumptions: ScenarioAssumptions | null
  
  monteCarlo: MonteCarloResult | null  // null until Engine B provides data
  sensitivity: SensitivityDriver[] | null
  forecast: ForecastResult | null
  
  riskLevel: RiskLevel | null
  isVulnerable: boolean         // successRate < 0.5
  isRecommended: boolean | null // base case or best performing
}

export interface CrossScenarioAnalysis {
  scenarios: EngineBScenarioResult[]
  
  robustness: {
    passedCount: number         // e.g., 4
    totalCount: number          // e.g., 6
    threshold: number           // e.g., 0.5 (50%)
    score: string               // e.g., "4/6"
  }
  
  vulnerabilities: {
    scenarioName: string
    successRate: number
    reason: string
  }[]
  
  bestCase: {
    scenarioName: string
    successRate: number | null
    icon: string
  } | null
  
  worstCase: {
    scenarioName: string
    successRate: number | null
    icon: string
  } | null
  
  overallSuccessRate: number    // weighted average across scenarios
  overallConfidence: number | null  // 0-1, null until Engine B provides
  overallTrend: 'increasing' | 'stable' | 'decreasing' | null
  
  topDrivers: SensitivityDriver[] | null  // null until Engine B provides
}

export type VerdictType = 'APPROVE' | 'PROCEED_WITH_CAUTION' | 'RECONSIDER' | 'REJECT'

export interface VerdictData {
  question: string
  verdict: VerdictType
  successRate: number           // 0-100
  robustness: {
    passed: number
    total: number
    vulnerabilities: string[]
  }
  confidence: number            // 0-100
  riskLevel: RiskLevel
  trend: 'increasing' | 'stable' | 'decreasing'
  topDriver: string | null      // null until Engine B provides, e.g., "Training pipeline (38%)"
  recommendation: string | null // null until Engine B provides
}

export interface DebateSummary {
  text: string                  // AI-generated summary
  consensusPoints: string[]
  activeDisagreements: string[]
  currentPhase: 'opening' | 'challenge' | 'deliberation' | 'consensus' | 'final'
  turnsCompleted: number
  totalTurns: number
  lastUpdatedTurn: number
}

// Helper function to determine verdict from success rate and robustness
export function determineVerdict(successRate: number, robustnessScore: number): VerdictType {
  if (successRate >= 70 && robustnessScore >= 0.67) {
    return 'APPROVE'
  }
  if (successRate >= 50 && robustnessScore >= 0.5) {
    return 'PROCEED_WITH_CAUTION'
  }
  if (successRate >= 35 || robustnessScore >= 0.33) {
    return 'RECONSIDER'
  }
  return 'REJECT'
}

// Helper to get verdict color
export function getVerdictColor(verdict: VerdictType): string {
  switch (verdict) {
    case 'APPROVE':
      return 'from-emerald-500 to-green-400'
    case 'PROCEED_WITH_CAUTION':
      return 'from-amber-500 to-yellow-400'
    case 'RECONSIDER':
      return 'from-orange-500 to-amber-400'
    case 'REJECT':
      return 'from-red-500 to-rose-400'
  }
}

// Helper to get risk level color
export function getRiskColor(risk: RiskLevel): string {
  switch (risk) {
    case 'low':
      return 'text-emerald-400'
    case 'medium':
      return 'text-amber-400'
    case 'high':
      return 'text-orange-400'
    case 'critical':
      return 'text-red-400'
  }
}

// Helper to get trend icon
export function getTrendIcon(trend: 'increasing' | 'stable' | 'decreasing'): string {
  switch (trend) {
    case 'increasing':
      return '↗'
    case 'stable':
      return '→'
    case 'decreasing':
      return '↘'
  }
}
