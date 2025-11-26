/**
 * Indicator Labels and Category Mappings for QNWIS Facts Panel
 * 
 * Maps technical indicator codes (e.g., from World Bank, IMF, Qatar PSA)
 * to human-readable labels for ministerial consumption.
 */

export type FactCategory = 'economic' | 'labor' | 'energy' | 'regional' | 'policy' | 'demographic'

export interface CategoryConfig {
  label: string
  icon: string
  color: string
  description: string
}

/**
 * Category configuration for grouping facts
 */
export const CATEGORY_CONFIG: Record<FactCategory, CategoryConfig> = {
  economic: {
    label: 'Economic Indicators',
    icon: '📊',
    color: '#3B82F6', // blue
    description: 'GDP, inflation, trade balance, and economic growth metrics',
  },
  labor: {
    label: 'Labor Market',
    icon: '👥',
    color: '#10B981', // green
    description: 'Employment, wages, workforce statistics',
  },
  energy: {
    label: 'Energy Sector',
    icon: '⚡',
    color: '#F59E0B', // amber
    description: 'Oil, gas, and energy production metrics',
  },
  regional: {
    label: 'Regional Comparison',
    icon: '🌍',
    color: '#8B5CF6', // purple
    description: 'GCC and international benchmarks',
  },
  policy: {
    label: 'Policy & Regulation',
    icon: '📜',
    color: '#EC4899', // pink
    description: 'Government policy and regulatory indicators',
  },
  demographic: {
    label: 'Demographics',
    icon: '📋',
    color: '#06B6D4', // cyan
    description: 'Population and demographic statistics',
  },
}

/**
 * World Bank indicator code to human label mappings
 */
export const WORLD_BANK_INDICATORS: Record<string, { label: string; category: FactCategory; unit?: string }> = {
  // GDP and Economic Output
  'NY.GDP.MKTP.CD': { label: 'GDP (Current USD)', category: 'economic', unit: 'USD' },
  'NY.GDP.MKTP.KD': { label: 'GDP (Constant 2015 USD)', category: 'economic', unit: 'USD' },
  'NY.GDP.MKTP.KD.ZG': { label: 'GDP Growth Rate', category: 'economic', unit: '%' },
  'NY.GDP.PCAP.CD': { label: 'GDP per Capita', category: 'economic', unit: 'USD' },
  'NY.GDP.PCAP.KD.ZG': { label: 'GDP per Capita Growth', category: 'economic', unit: '%' },
  
  // Sector Contributions
  'NV.IND.TOTL.ZS': { label: 'Industry Share of GDP', category: 'economic', unit: '%' },
  'NV.AGR.TOTL.ZS': { label: 'Agriculture Share of GDP', category: 'economic', unit: '%' },
  'NV.SRV.TOTL.ZS': { label: 'Services Share of GDP', category: 'economic', unit: '%' },
  'NV.IND.MANF.ZS': { label: 'Manufacturing Share of GDP', category: 'economic', unit: '%' },
  
  // Trade
  'NE.EXP.GNFS.ZS': { label: 'Exports of Goods & Services (% GDP)', category: 'economic', unit: '%' },
  'NE.IMP.GNFS.ZS': { label: 'Imports of Goods & Services (% GDP)', category: 'economic', unit: '%' },
  'BN.CAB.XOKA.CD': { label: 'Current Account Balance', category: 'economic', unit: 'USD' },
  
  // Labor Market
  'SL.UEM.TOTL.ZS': { label: 'Unemployment Rate', category: 'labor', unit: '%' },
  'SL.UEM.TOTL.NE.ZS': { label: 'Unemployment (National)', category: 'labor', unit: '%' },
  'SL.TLF.TOTL.IN': { label: 'Total Labor Force', category: 'labor' },
  'SL.TLF.CACT.ZS': { label: 'Labor Force Participation', category: 'labor', unit: '%' },
  'SL.TLF.CACT.FE.ZS': { label: 'Female Labor Participation', category: 'labor', unit: '%' },
  'SL.TLF.CACT.MA.ZS': { label: 'Male Labor Participation', category: 'labor', unit: '%' },
  'SL.EMP.TOTL.SP.ZS': { label: 'Employment to Population Ratio', category: 'labor', unit: '%' },
  
  // Demographics
  'SP.POP.TOTL': { label: 'Total Population', category: 'demographic' },
  'SP.POP.GROW': { label: 'Population Growth', category: 'demographic', unit: '%' },
  'SP.URB.TOTL.IN.ZS': { label: 'Urban Population (%)', category: 'demographic', unit: '%' },
  'SM.POP.NETM': { label: 'Net Migration', category: 'demographic' },
  
  // Energy
  'EG.USE.PCAP.KG.OE': { label: 'Energy Use per Capita', category: 'energy', unit: 'kg oil eq.' },
  'EG.ELC.ACCS.ZS': { label: 'Access to Electricity', category: 'energy', unit: '%' },
  'EN.ATM.CO2E.PC': { label: 'CO2 Emissions per Capita', category: 'energy', unit: 'metric tons' },
  
  // Inflation and Prices
  'FP.CPI.TOTL.ZG': { label: 'Inflation Rate (CPI)', category: 'economic', unit: '%' },
  'NY.GDP.DEFL.KD.ZG': { label: 'GDP Deflator', category: 'economic', unit: '%' },
}

/**
 * Qatar-specific indicator mappings
 */
export const QATAR_INDICATORS: Record<string, { label: string; category: FactCategory; unit?: string }> = {
  'qatarization_rate': { label: 'Qatarization Rate', category: 'policy', unit: '%' },
  'qatari_employment': { label: 'Qatari Employment', category: 'labor' },
  'expat_employment': { label: 'Expatriate Employment', category: 'labor' },
  'private_sector_qatarization': { label: 'Private Sector Qatarization', category: 'policy', unit: '%' },
  'public_sector_qatarization': { label: 'Public Sector Qatarization', category: 'policy', unit: '%' },
  'oil_production': { label: 'Oil Production', category: 'energy', unit: 'barrels/day' },
  'lng_production': { label: 'LNG Production', category: 'energy', unit: 'million tonnes' },
  'oil_price_brent': { label: 'Brent Oil Price', category: 'energy', unit: 'USD/barrel' },
  'minimum_wage': { label: 'Minimum Wage', category: 'policy', unit: 'QAR/month' },
}

/**
 * LMIS (Ministry of Labour) indicator mappings
 * Values from LMIS API are already percentages (e.g., 0.099 = 0.099%, NOT 9.9%)
 */
export const LMIS_INDICATORS: Record<string, { label: string; category: FactCategory; unit?: string; isAlreadyPercent?: boolean }> = {
  // Main indicators - CRITICAL: These are already percentages, not ratios!
  'Unemployment': { label: 'Qatar Unemployment Rate', category: 'labor', unit: '%', isAlreadyPercent: true },
  'unemployment': { label: 'Qatar Unemployment Rate', category: 'labor', unit: '%', isAlreadyPercent: true },
  'qatar_unemployment': { label: 'Qatar Unemployment Rate', category: 'labor', unit: '%', isAlreadyPercent: true },
  'qatar_unemployment_rate': { label: 'Qatar Unemployment Rate', category: 'labor', unit: '%', isAlreadyPercent: true },
  'Qatar_Female_Labor': { label: 'Qatar Female Labor Participation', category: 'labor', unit: '%', isAlreadyPercent: true },
  'Qatar_Internet_Usage': { label: 'Qatar Internet Usage', category: 'demographic', unit: '%', isAlreadyPercent: true },
  'Qatar_Health_Coverage': { label: 'Qatar Health Coverage', category: 'demographic', unit: '%', isAlreadyPercent: true },
  'Qatar_Out_Of_School': { label: 'Qatar Out of School Rate', category: 'demographic', unit: '%', isAlreadyPercent: true },
  'Qatar_Remittances': { label: 'Qatar Remittances (% GDP)', category: 'economic', unit: '%', isAlreadyPercent: true },
  'Qatar_Social_Protection': { label: 'Qatar Social Protection', category: 'policy', unit: '%', isAlreadyPercent: true },
  'Qatar_Population': { label: 'Qatar Population', category: 'demographic' },
  'GDP': { label: 'Qatar GDP', category: 'economic', unit: 'USD' },
  'GDP_Capita': { label: 'Qatar GDP per Capita', category: 'economic', unit: 'USD' },
  'CPI': { label: 'Consumer Price Index', category: 'economic' },
  'Exports': { label: 'Qatar Exports', category: 'economic', unit: 'USD' },
  'Imports': { label: 'Qatar Imports', category: 'economic', unit: 'USD' },
  'Total_Debt': { label: 'Qatar Total Debt (% GDP)', category: 'economic', unit: '%' },
  
  // GCC-STAT indicators - these are proper percentages
  'qatar_unemployment_rate': { label: 'Qatar Unemployment Rate', category: 'labor', unit: '%' },
  'bahrain_unemployment_rate': { label: 'Bahrain Unemployment Rate', category: 'regional', unit: '%' },
  'kuwait_unemployment_rate': { label: 'Kuwait Unemployment Rate', category: 'regional', unit: '%' },
  'uae_unemployment_rate': { label: 'UAE Unemployment Rate', category: 'regional', unit: '%' },
  'saudi_unemployment_rate': { label: 'Saudi Arabia Unemployment Rate', category: 'regional', unit: '%' },
  'oman_unemployment_rate': { label: 'Oman Unemployment Rate', category: 'regional', unit: '%' },
  'qatar_labour_force_participation': { label: 'Qatar Labour Force Participation', category: 'labor', unit: '%' },
  'qatar_gdp_usd': { label: 'Qatar GDP USD', category: 'economic', unit: 'B USD' },
}

/**
 * All indicator mappings combined
 */
export const ALL_INDICATORS = {
  ...WORLD_BANK_INDICATORS,
  ...QATAR_INDICATORS,
  ...LMIS_INDICATORS,
}

/**
 * Get human-readable label for an indicator code
 */
export function getIndicatorLabel(code: string): string {
  const indicator = ALL_INDICATORS[code]
  if (indicator) {
    return indicator.label
  }
  
  // Try to format unknown codes nicely
  return code
    .replace(/[._]/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .split(' ')
    .filter(word => word.length > 0)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

/**
 * Get category for an indicator code
 */
export function getIndicatorCategory(code: string): FactCategory {
  const indicator = ALL_INDICATORS[code]
  return indicator?.category || 'economic'
}

/**
 * Get unit for an indicator code
 */
export function getIndicatorUnit(code: string): string | undefined {
  return ALL_INDICATORS[code]?.unit
}

/**
 * Categorize a list of facts by their indicator codes
 */
export function categorizeFacts<T extends { metric: string }>(facts: T[]): Record<FactCategory, T[]> {
  const categorized: Record<FactCategory, T[]> = {
    economic: [],
    labor: [],
    energy: [],
    regional: [],
    policy: [],
    demographic: [],
  }
  
  for (const fact of facts) {
    const category = getIndicatorCategory(fact.metric)
    categorized[category].push(fact)
  }
  
  return categorized
}

/**
 * Source name mappings for cleaner display
 */
export const SOURCE_LABELS: Record<string, string> = {
  'world_bank': 'World Bank',
  'worldbank': 'World Bank',
  'wb': 'World Bank',
  'imf': 'IMF',
  'qatar_psa': 'Qatar PSA',
  'psa': 'Qatar PSA',
  'mol': 'Ministry of Labour',
  'qcb': 'Qatar Central Bank',
  'opec': 'OPEC',
  'gcc_stat': 'GCC Stat',
  'ilo': 'ILO',
}

/**
 * Get clean source name
 */
export function getSourceLabel(source: string): string {
  const normalized = source.toLowerCase().replace(/[_\s-]/g, '_')
  return SOURCE_LABELS[normalized] || source
}

