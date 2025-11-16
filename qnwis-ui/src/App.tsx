import { useState } from 'react'
import './App.css'

interface AgentResult {
  agent: string
  narrative: string
  confidence: number
  status: 'analyzing' | 'complete'
}

interface WorkflowEvent {
  stage: string
  status: string
  payload: any
  latency_ms?: number
  timestamp?: string
}

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentStage, setCurrentStage] = useState('')
  const [agents, setAgents] = useState<AgentResult[]>([])
  const [synthesis, setSynthesis] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    // Reset state
    setLoading(true)
    setCurrentStage('Starting analysis...')
    setAgents([])
    setSynthesis('')
    setError('')

    try {
      const payload = { 
        question: query.trim(), 
        provider: 'anthropic',
        model: 'claude-sonnet-4-20250514'
      }
      
      const response = await fetch('/api/v1/council/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        let streamComplete = false
        
        while (!streamComplete) {
          const { done, value } = await reader.read()
          if (done) break
          
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data.trim()) {
                try {
                  const event: WorkflowEvent = JSON.parse(data)
                  
                  // Update UI based on event
                  if (event.stage === 'classify') {
                    setCurrentStage(' Classifying query complexity...')
                  } else if (event.stage === 'prefetch') {
                    setCurrentStage(' Gathering data from 19 sources...')
                  } else if (event.stage === 'rag') {
                    setCurrentStage(' Retrieving relevant context...')
                  } else if (event.stage === 'agent_selection') {
                    setCurrentStage(' Selecting specialist agents...')
                  } else if (event.stage === 'agents' && event.status === 'complete') {
                    // Agent completed
                    const agentData = event.payload
                    if (agentData && agentData.agent && agentData.narrative) {
                      setAgents(prev => {
                        const existing = prev.find(a => a.agent === agentData.agent)
                        if (existing) {
                          return prev.map(a => 
                            a.agent === agentData.agent 
                              ? { ...a, narrative: agentData.narrative, confidence: agentData.confidence, status: 'complete' }
                              : a
                          )
                        }
                        return [...prev, {
                          agent: agentData.agent,
                          narrative: agentData.narrative,
                          confidence: agentData.confidence || 0,
                          status: 'complete'
                        }]
                      })
                    }
                  } else if (event.stage === 'verify') {
                    setCurrentStage(' Verifying citations and data...')
                  } else if (event.stage === 'done' && event.status === 'complete') {
                    setCurrentStage(' Analysis complete!')
                    streamComplete = true
                    
                    // Extract synthesis from final state
                    if (event.payload && event.payload.synthesis) {
                      setSynthesis(event.payload.synthesis)
                    }
                    break
                  }
                } catch (e) {
                  console.error('Parse error:', e)
                }
              }
            }
          }
        }
        
        await reader.cancel()
      }
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const getAgentIcon = (agent: string) => {
    const icons: Record<string, string> = {
      'labour_economist': '',
      'financial_economist': '',
      'market_economist': '',
      'operations_expert': '',
      'research_scientist': ''
    }
    return icons[agent] || ''
  }

  const getAgentTitle = (agent: string) => {
    const titles: Record<string, string> = {
      'labour_economist': 'Labour Economist',
      'financial_economist': 'Financial Economist',
      'market_economist': 'Market Economist',
      'operations_expert': 'Operations Expert',
      'research_scientist': 'Research Scientist'
    }
    return titles[agent] || agent
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f3f4f6' }}>
      {/* Header */}
      <div style={{ 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        padding: '32px 20px',
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          <h1 style={{ margin: 0, fontSize: '32px', fontWeight: 'bold', marginBottom: '8px' }}>
            QNWIS Intelligence System
          </h1>
          <p style={{ margin: 0, fontSize: '18px', opacity: 0.95 }}>
            Qatar Ministry of Labour – Multi-Agent Strategic Council
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 20px' }}>
        
        {/* Query Input */}
        <div style={{ 
          background: 'white', 
          borderRadius: '12px', 
          padding: '24px',
          boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)',
          marginBottom: '24px'
        }}>
          <form onSubmit={handleSubmit}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '600', marginBottom: '8px', color: '#374151' }}>
              Ask Your Strategic Question
            </label>
            <div style={{ display: 'flex', gap: '12px' }}>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What are the implications of raising the minimum wage for Qatari nationals to QR 20,000?"
                style={{
                  flex: 1,
                  padding: '14px 16px',
                  fontSize: '16px',
                  border: '2px solid #e5e7eb',
                  borderRadius: '8px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                disabled={loading}
                onFocus={(e) => e.target.style.borderColor = '#667eea'}
                onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                style={{
                  padding: '14px 32px',
                  fontSize: '16px',
                  background: loading ? '#9ca3af' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontWeight: '600',
                  boxShadow: loading ? 'none' : '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  transition: 'all 0.2s'
                }}
              >
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          </form>
        </div>

        {/* Current Stage */}
        {loading && currentStage && (
          <div style={{ 
            background: 'white',
            border: '2px solid #667eea',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '24px',
            boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ 
                animation: 'spin 1s linear infinite',
                width: '24px',
                height: '24px',
                border: '3px solid #e5e7eb',
                borderTopColor: '#667eea',
                borderRadius: '50%'
              }} />
              <div>
                <div style={{ fontSize: '18px', fontWeight: '600', color: '#1f2937' }}>
                  {currentStage}
                </div>
                <div style={{ fontSize: '14px', color: '#6b7280', marginTop: '4px' }}>
                  Deep analysis in progress...
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Agent Results */}
        {agents.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <h2 style={{ fontSize: '24px', fontWeight: '700', marginBottom: '16px', color: '#1f2937' }}>
              Agent Analysis
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '16px' }}>
              {agents.map((agent, idx) => (
                <div 
                  key={idx}
                  style={{
                    background: 'white',
                    borderRadius: '12px',
                    padding: '20px',
                    boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)',
                    border: '1px solid #e5e7eb'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                    <div style={{ fontSize: '32px' }}>{getAgentIcon(agent.agent)}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '18px', fontWeight: '600', color: '#1f2937' }}>
                        {getAgentTitle(agent.agent)}
                      </div>
                      <div style={{ 
                        fontSize: '14px', 
                        color: agent.confidence >= 0.5 ? '#059669' : '#dc2626',
                        fontWeight: '500'
                      }}>
                        Confidence: {Math.round(agent.confidence * 100)}%
                      </div>
                    </div>
                  </div>
                  <div style={{
                    fontSize: '14px',
                    lineHeight: '1.6',
                    color: '#4b5563',
                    maxHeight: '300px',
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap'
                  }}>
                    {agent.narrative.substring(0, 500)}...
                    <button style={{
                      marginTop: '12px',
                      padding: '6px 12px',
                      background: '#f3f4f6',
                      border: '1px solid #d1d5db',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '13px',
                      fontWeight: '500',
                      color: '#4b5563'
                    }}>
                      Read Full Analysis →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Executive Summary */}
        {synthesis && (
          <div style={{
            background: 'white',
            borderRadius: '12px',
            padding: '32px',
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
            border: '2px solid #667eea'
          }}>
            <h2 style={{ fontSize: '28px', fontWeight: '700', marginBottom: '20px', color: '#1f2937', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span></span> Executive Summary
            </h2>
            <div style={{
              fontSize: '16px',
              lineHeight: '1.8',
              color: '#374151',
              whiteSpace: 'pre-wrap'
            }}>
              {synthesis}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{
            background: '#fef2f2',
            border: '2px solid #fca5a5',
            borderRadius: '12px',
            padding: '20px',
            color: '#991b1b'
          }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Suggested Queries */}
        {!loading && agents.length === 0 && (
          <div style={{ 
            background: 'white',
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)'
          }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px', color: '#1f2937' }}>
              Suggested Strategic Questions
            </h3>
            <div style={{ display: 'grid', gap: '12px' }}>
              {[
                'Is 70% Qatarization in Qatar financial sector by 2030 feasible?',
                'What are the implications of raising the minimum wage for Qatari nationals to QR 20,000?',
                'Compare Qatar unemployment rates with other GCC countries'
              ].map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => setQuery(q)}
                  style={{
                    padding: '16px',
                    background: '#f9fafb',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    fontSize: '15px',
                    color: '#374151',
                    transition: 'all 0.2s'
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.background = '#eff6ff'
                    e.currentTarget.style.borderColor = '#667eea'
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.background = '#f9fafb'
                    e.currentTarget.style.borderColor = '#e5e7eb'
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

export default App
