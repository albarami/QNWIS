/**
 * Value Formatting Utilities for QNWIS Frontend
 * 
 * Provides consistent formatting for numbers, percentages, currency,
 * and other values in the ministerial UI.
 */

/**
 * Format a large number with abbreviations (K, M, B, T)
 */
export function formatLargeNumber(value: number, decimals: number = 1): string {
  if (value === 0) return '0'
  
  const absValue = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  
  if (absValue >= 1e12) {
    return `${sign}${(absValue / 1e12).toFixed(decimals)}T`
  }
  if (absValue >= 1e9) {
    return `${sign}${(absValue / 1e9).toFixed(decimals)}B`
  }
  if (absValue >= 1e6) {
    return `${sign}${(absValue / 1e6).toFixed(decimals)}M`
  }
  if (absValue >= 1e3) {
    return `${sign}${(absValue / 1e3).toFixed(decimals)}K`
  }
  
  return `${sign}${absValue.toFixed(decimals)}`
}

/**
 * Format a number as currency (USD by default)
 */
export function formatCurrency(
  value: number, 
  currency: string = 'USD', 
  options: { abbreviated?: boolean; decimals?: number } = {}
): string {
  const { abbreviated = true, decimals = 1 } = options
  
  const symbols: Record<string, string> = {
    USD: '$',
    QAR: 'QAR ',
    EUR: '€',
    GBP: '£',
  }
  
  const symbol = symbols[currency] || `${currency} `
  
  if (abbreviated) {
    return `${symbol}${formatLargeNumber(value, decimals)}`
  }
  
  return `${symbol}${value.toLocaleString('en-US', { 
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals 
  })}`
}

/**
 * Format a value as a percentage
 */
export function formatPercentage(
  value: number, 
  options: { decimals?: number; includeSign?: boolean } = {}
): string {
  const { decimals = 1, includeSign = false } = options
  
  // If value is already a percentage (e.g., 45.5 for 45.5%)
  const formattedValue = value.toFixed(decimals)
  const sign = includeSign && value > 0 ? '+' : ''
  
  return `${sign}${formattedValue}%`
}

/**
 * Format a decimal as a percentage (e.g., 0.455 -> 45.5%)
 */
export function formatDecimalAsPercentage(
  value: number,
  options: { decimals?: number; includeSign?: boolean } = {}
): string {
  return formatPercentage(value * 100, options)
}

/**
 * Format a number with thousands separators
 */
export function formatNumber(value: number, decimals: number = 0): string {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/**
 * Smart format a value based on its characteristics
 * Automatically detects and formats percentages, currencies, large numbers
 */
export function smartFormat(
  value: string | number | boolean, 
  unit?: string
): string {
  // Handle booleans
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  
  // Handle strings
  if (typeof value === 'string') {
    // Check if it's a number in string form
    const numValue = parseFloat(value)
    if (!isNaN(numValue)) {
      return smartFormat(numValue, unit)
    }
    return value
  }
  
  // Handle numbers
  const numValue = value
  
  // If unit is provided, format accordingly
  if (unit) {
    const unitLower = unit.toLowerCase()
    
    if (unitLower === '%' || unitLower.includes('percent')) {
      return formatPercentage(numValue)
    }
    
    if (unitLower === 'usd' || unitLower.includes('dollar')) {
      return formatCurrency(numValue, 'USD')
    }
    
    if (unitLower === 'qar' || unitLower.includes('riyal')) {
      return formatCurrency(numValue, 'QAR')
    }
    
    // Format with unit suffix
    return `${formatLargeNumber(numValue)} ${unit}`
  }
  
  // Auto-detect percentage (values between 0 and 1 that look like ratios)
  if (numValue > 0 && numValue < 1 && numValue !== Math.floor(numValue)) {
    return formatDecimalAsPercentage(numValue)
  }
  
  // Auto-detect percentage (values that look like percentages already)
  if (numValue >= 0 && numValue <= 100 && numValue !== Math.floor(numValue)) {
    // Could be a percentage - format as such if it has decimals
    return formatPercentage(numValue)
  }
  
  // Large numbers get abbreviated
  if (Math.abs(numValue) >= 1000) {
    return formatLargeNumber(numValue)
  }
  
  // Regular numbers
  return formatNumber(numValue, numValue === Math.floor(numValue) ? 0 : 2)
}

/**
 * Format a duration in milliseconds to human-readable string
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`
  }
  
  if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`
  }
  
  if (ms < 3600000) {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.floor((ms % 60000) / 1000)
    return `${minutes}m ${seconds}s`
  }
  
  const hours = Math.floor(ms / 3600000)
  const minutes = Math.floor((ms % 3600000) / 60000)
  return `${hours}h ${minutes}m`
}

/**
 * Format elapsed time with estimated remaining
 */
export function formatTimeRemaining(
  elapsedMs: number, 
  estimatedTotalMs: number
): string {
  const remainingMs = Math.max(0, estimatedTotalMs - elapsedMs)
  
  if (remainingMs === 0) {
    return 'Complete'
  }
  
  return `~${formatDuration(remainingMs)} remaining`
}

/**
 * Format a date relative to now (e.g., "2 minutes ago")
 */
export function formatRelativeTime(date: Date | string): string {
  const now = new Date()
  const then = typeof date === 'string' ? new Date(date) : date
  const diffMs = now.getTime() - then.getTime()
  
  if (diffMs < 0) {
    return 'just now'
  }
  
  if (diffMs < 60000) {
    const seconds = Math.floor(diffMs / 1000)
    return seconds <= 1 ? 'just now' : `${seconds}s ago`
  }
  
  if (diffMs < 3600000) {
    const minutes = Math.floor(diffMs / 60000)
    return `${minutes}m ago`
  }
  
  if (diffMs < 86400000) {
    const hours = Math.floor(diffMs / 3600000)
    return `${hours}h ago`
  }
  
  const days = Math.floor(diffMs / 86400000)
  return `${days}d ago`
}

/**
 * Format confidence score (0-1 or 0-100) to display string
 */
export function formatConfidence(value: number): string {
  // Normalize to 0-100 range
  const normalized = value <= 1 ? value * 100 : value
  
  if (normalized >= 90) {
    return `${normalized.toFixed(0)}% (High)`
  }
  if (normalized >= 70) {
    return `${normalized.toFixed(0)}% (Medium)`
  }
  if (normalized >= 50) {
    return `${normalized.toFixed(0)}% (Low)`
  }
  return `${normalized.toFixed(0)}% (Very Low)`
}

