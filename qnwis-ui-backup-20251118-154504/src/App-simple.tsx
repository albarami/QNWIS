import { useState } from 'react'

function App() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setResult('')

    try {
      const payload = { 
        question: query.trim(), 
        provider: 'anthropic',
        model: 'claude-sonnet-4-20250514'
      }
      console.log('Sending request:', payload)
      
      const response = await fetch('/api/v1/council/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('API Error:', errorText)
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        let streamComplete = false
        
        while (!streamComplete) {
          const { done, value } = await reader.read()
          if (done) {
            console.log('Stream ended by server')
            break
          }
          
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data.trim()) {
                try {
                  const event = JSON.parse(data)
                  console.log('Received event:', event.stage, event.status)
                  setResult(prev => prev + '\n' + JSON.stringify(event, null, 2))
                  
                  // Check if workflow is complete
                  if (event.stage === 'done' && event.status === 'complete') {
                    console.log('Workflow complete, closing stream')
                    streamComplete = true
                    break
                  }
                } catch (e) {
                  console.error('Parse error:', e, 'Data:', data)
                }
              }
            }
          }
        }
        
        // Close the reader
        await reader.cancel()
      }
    } catch (error) {
      setResult('Error: ' + (error as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto', fontFamily: 'system-ui' }}>
      <div style={{ background: 'white', borderBottom: '1px solid #e5e7eb', padding: '20px', marginBottom: '20px' }}>
        <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>
          QNWIS Intelligence System
        </h1>
        <p style={{ margin: '5px 0 0 0', color: '#666' }}>
          Qatar Ministry of Labour – 5-Agent Strategic Council
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about Qatar's labor market, policies, or economic trends..."
            style={{
              flex: 1,
              padding: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '16px'
            }}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '12px 24px',
              background: loading ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: '500'
            }}
          >
            {loading ? 'Analyzing...' : 'Ask Council'}
          </button>
        </div>
      </form>

      {loading && (
        <div style={{ 
          padding: '20px', 
          background: '#eff6ff', 
          borderRadius: '8px',
          border: '1px solid #3b82f6'
        }}>
          <p style={{ margin: 0, color: '#1e40af', fontWeight: '500' }}>
            🤖 5 PhD-level agents analyzing your query...
          </p>
          <p style={{ margin: '5px 0 0 0', fontSize: '14px', color: '#3b82f6' }}>
            This takes 90-120 seconds for legendary depth
          </p>
        </div>
      )}

      {result && (
        <div style={{
          marginTop: '20px',
          padding: '20px',
          background: '#f9fafb',
          borderRadius: '8px',
          border: '1px solid #e5e7eb'
        }}>
          <h3 style={{ marginTop: 0 }}>Results:</h3>
          <pre style={{
            whiteSpace: 'pre-wrap',
            fontSize: '12px',
            lineHeight: '1.5',
            maxHeight: '600px',
            overflow: 'auto'
          }}>
            {result}
          </pre>
        </div>
      )}

      <div style={{ 
        marginTop: '40px', 
        padding: '20px', 
        background: '#fef3c7',
        borderRadius: '8px',
        border: '1px solid #f59e0b'
      }}>
        <h3 style={{ marginTop: 0, color: '#92400e' }}>💡 Try These Queries:</h3>
        <ul style={{ margin: '10px 0', color: '#78350f' }}>
          <li style={{ marginBottom: '8px' }}>
            Is 70% Qatarization in Qatar's financial sector by 2030 feasible?
          </li>
          <li style={{ marginBottom: '8px' }}>
            What are the implications of raising the minimum wage for Qatari nationals to QR 20,000?
          </li>
          <li>
            Compare Qatar's unemployment rates with other GCC countries
          </li>
        </ul>
      </div>
    </div>
  )
}

export default App
