# React Migration - Complete Code Files

This document contains all the code files you need to create for the React migration.

---

## File 1: `qnwis-ui/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
```

---

## File 2: `qnwis-ui/src/types/workflow.ts`

```typescript
// Core workflow stages matching your LangGraph implementation
export type WorkflowStage = 
  | 'classify'
  | 'prefetch' 
  | 'financial_agent'
  | 'market_agent'
  | 'operations_agent'
  | 'research_agent'
  | 'debate'
  | 'critique'
  | 'synthesis'
  | 'complete';

export type QueryComplexity = 'simple' | 'medium' | 'complex' | 'critical';

export interface ExtractedFact {
  metric: string;
  value: any;
  source: string;
  source_priority: number;
  confidence: number;
  raw_text: string;
  timestamp?: string;
}

export interface Citation {
  text: string;
  source: string;
  source_type: 'udc_report' | 'qatar_stats' | 'world_bank' | 'semantic_scholar' | 'news' | 'other';
  page?: number;
  url?: string;
  confidence: number;
}

export interface AgentOutput {
  agent: 'financial' | 'market' | 'operations' | 'research';
  agent_name: string;
  analysis: string;
  key_findings: string[];
  citations: Citation[];
  confidence: number;
  reasoning: string[];
  warnings?: string[];
}

export interface DebateOutput {
  synthesis: string;
  contradictions: Array<{
    topic: string;
    perspectives: Array<{
      agent: string;
      view: string;
      confidence: number;
    }>;
    resolution: string;
  }>;
  emergent_insights: string[];
}

export interface CritiqueOutput {
  challenges: Array<{
    claim: string;
    challenge: string;
    severity: 'low' | 'medium' | 'high';
    resolution: string;
  }>;
  assumptions_audited: string[];
  alternative_hypotheses: string[];
  confidence_adjustment: number;
}

export interface WorkflowState {
  stage: WorkflowStage;
  query: string;
  complexity: QueryComplexity;
  
  // Data layer
  extracted_facts: ExtractedFact[];
  extraction_confidence: number;
  
  // Agent outputs
  agent_outputs: AgentOutput[];
  agents_invoked: string[];
  
  // Debate & Critique
  debate_synthesis?: DebateOutput;
  critique?: CritiqueOutput;
  
  // Final output
  final_synthesis: string;
  reasoning_chain: string[];
  confidence_score: number;
  
  // Metadata
  timestamp: string;
  execution_time_ms: number;
  cost_usd: number;
  llm_calls: number;
  
  // Error handling
  errors?: Array<{
    stage: string;
    error: string;
    retry_count: number;
  }>;
}

export interface StreamEvent {
  event: 'stage_start' | 'stage_complete' | 'stage_update' | 'error' | 'complete';
  stage: WorkflowStage;
  data: Partial<WorkflowState>;
  timestamp: string;
  message?: string;
}
```

---

## File 3: `qnwis-ui/src/hooks/useWorkflowStream.ts`

```typescript
import { useState, useEffect, useCallback } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { WorkflowState, StreamEvent } from '@/types/workflow';

interface UseWorkflowStreamOptions {
  onComplete?: (state: WorkflowState) => void;
  onError?: (error: string) => void;
}

export const useWorkflowStream = (options: UseWorkflowStreamOptions = {}) => {
  const [state, setState] = useState<WorkflowState | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [controller, setController] = useState<AbortController | null>(null);

  const startStream = useCallback(async (query: string) => {
    // Reset state
    setState(null);
    setError(null);
    setIsStreaming(true);

    // Create abort controller for cancellation
    const abortController = new AbortController();
    setController(abortController);

    try {
      await fetchEventSource('/api/v1/council/llm/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
        signal: abortController.signal,
        
        onopen(response) {
          if (response.ok) {
            console.log('Stream connection established');
          } else {
            throw new Error(`Failed to connect: ${response.status}`);
          }
        },

        onmessage(event) {
          try {
            const streamEvent: StreamEvent = JSON.parse(event.data);
            
            // Update state based on event
            setState(prevState => ({
              ...prevState,
              ...streamEvent.data,
              stage: streamEvent.stage,
            } as WorkflowState));

            // Handle completion
            if (streamEvent.event === 'complete') {
              setIsStreaming(false);
              if (options.onComplete && streamEvent.data) {
                options.onComplete(streamEvent.data as WorkflowState);
              }
            }

            // Handle errors
            if (streamEvent.event === 'error') {
              const errorMsg = streamEvent.message || 'Unknown error';
              setError(errorMsg);
              setIsStreaming(false);
              if (options.onError) {
                options.onError(errorMsg);
              }
            }
          } catch (err) {
            console.error('Failed to parse event:', err);
          }
        },

        onerror(err) {
          console.error('SSE Error:', err);
          setError('Connection error occurred');
          setIsStreaming(false);
          if (options.onError) {
            options.onError('Connection error occurred');
          }
          throw err; // Stops retry
        },

        onclose() {
          console.log('Stream connection closed');
          setIsStreaming(false);
        },
      });
    } catch (err) {
      console.error('Stream error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsStreaming(false);
    }
  }, [options]);

  const stopStream = useCallback(() => {
    if (controller) {
      controller.abort();
      setController(null);
      setIsStreaming(false);
    }
  }, [controller]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (controller) {
        controller.abort();
      }
    };
  }, [controller]);

  return {
    state,
    isStreaming,
    error,
    startStream,
    stopStream,
  };
};
```

---

## File 4: `qnwis-ui/tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

---

## File 5: `qnwis-ui/src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gray-50 text-gray-900;
  }
}

@layer components {
  .prose {
    @apply text-gray-700;
  }
  
  .prose p {
    @apply mb-4;
  }
  
  .prose ul {
    @apply list-disc list-inside mb-4;
  }
  
  .prose strong {
    @apply font-semibold text-gray-900;
  }
}
```

---

## File 6: `qnwis-ui/src/App.tsx` (Part 1 - Imports and Component Start)

```typescript
import { useState } from 'react';
import { useWorkflowStream } from './hooks/useWorkflowStream';
import { WorkflowState } from './types/workflow';

function App() {
  const [query, setQuery] = useState('');
  const [queryHistory, setQueryHistory] = useState<string[]>([]);
  
  const { state, isStreaming, error, startStream, stopStream } = useWorkflowStream({
    onComplete: (finalState) => {
      console.log('Workflow complete:', finalState);
      setQueryHistory(prev => [...prev, query]);
    },
    onError: (error) => {
      console.error('Workflow error:', error);
    }
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isStreaming) return;
    
    await startStream(query);
  };

  const handleStop = () => {
    stopStream();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            QNWIS Intelligence System
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Multi-Agent Strategic Analysis
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Query Input */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <form onSubmit={handleSubmit}>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter Strategic Query
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={isStreaming}
                placeholder="e.g., How is UDC's financial situation?"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              {!isStreaming ? (
                <button
                  type="submit"
                  disabled={!query.trim()}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
                >
                  Analyze
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleStop}
                  className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium"
                >
                  Stop
                </button>
              )}
            </div>
          </form>

          {/* Query History */}
          {queryHistory.length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">Recent Queries:</p>
              <div className="flex flex-wrap gap-2">
                {queryHistory.slice(-3).map((q, i) => (
                  <button
                    key={i}
                    onClick={() => setQuery(q)}
                    disabled={isStreaming}
                    className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 disabled:opacity-50"
                  >
                    {q.length > 50 ? q.slice(0, 50) + '...' : q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <h3 className="text-red-800 font-medium mb-1">Error</h3>
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* Workflow Display */}
        {state && (
          <div className="space-y-6">
            {/* Current Stage Indicator */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">
                  Analysis Progress
                </h2>
                {isStreaming && (
                  <span className="flex items-center text-sm text-blue-600">
                    <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Processing...
                  </span>
                )}
              </div>

              {/* Stage Indicators */}
              <div className="flex items-center space-x-2">
                {['classify', 'prefetch', 'agents', 'debate', 'critique', 'synthesis'].map((stage, idx) => (
                  <div key={stage} className="flex items-center">
                    <div className={`
                      w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium
                      ${state.stage === stage ? 'bg-blue-600 text-white' : 
                        getStageIndex(state.stage) > idx ? 'bg-green-500 text-white' : 
                        'bg-gray-200 text-gray-500'}
                    `}>
                      {idx + 1}
                    </div>
                    {idx < 5 && (
                      <div className={`w-8 h-1 ${getStageIndex(state.stage) > idx ? 'bg-green-500' : 'bg-gray-200'}`} />
                    )}
                  </div>
                ))}
              </div>
              
              <p className="mt-4 text-sm text-gray-600">
                Current Stage: <span className="font-medium">{formatStageName(state.stage)}</span>
              </p>
              
              {state.complexity && (
                <p className="text-sm text-gray-600">
                  Query Complexity: <span className="font-medium capitalize">{state.complexity}</span>
                </p>
              )}
            </div>

            {/* Extracted Facts */}
            {state.extracted_facts && state.extracted_facts.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Data Extraction ({state.extracted_facts.length} facts)
                </h3>
                <div className="space-y-2">
                  {state.extracted_facts.slice(0, 5).map((fact, idx) => (
                    <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2 bg-blue-50">
                      <p className="text-sm font-medium text-gray-900">
                        {fact.metric}: {String(fact.value)}
                      </p>
                      <p className="text-xs text-gray-600">
                        Source: {fact.source} | Confidence: {(fact.confidence * 100).toFixed(0)}%
                      </p>
                    </div>
                  ))}
                  {state.extracted_facts.length > 5 && (
                    <p className="text-sm text-gray-500">
                      + {state.extracted_facts.length - 5} more facts
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Agent Outputs */}
            {state.agent_outputs && state.agent_outputs.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Specialist Agent Analysis
                </h3>
                <div className="space-y-4">
                  {state.agent_outputs.map((agent, idx) => (
                    <div key={idx} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-900 capitalize">
                          {agent.agent_name || agent.agent}
                        </h4>
                        <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">
                          {(agent.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">
                        {agent.analysis.slice(0, 300)}
                        {agent.analysis.length > 300 ? '...' : ''}
                      </p>
                      {agent.key_findings && agent.key_findings.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-gray-700 mb-1">Key Findings:</p>
                          <ul className="text-xs text-gray-600 space-y-1 list-disc list-inside">
                            {agent.key_findings.slice(0, 3).map((finding, i) => (
                              <li key={i}>{finding}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Debate Synthesis */}
            {state.debate_synthesis && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Multi-Agent Debate Synthesis
                </h3>
                <p className="text-sm text-gray-700 whitespace-pre-wrap mb-4">
                  {state.debate_synthesis.synthesis}
                </p>
                {state.debate_synthesis.emergent_insights && state.debate_synthesis.emergent_insights.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-sm font-medium text-gray-900 mb-2">Emergent Insights:</p>
                    <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                      {state.debate_synthesis.emergent_insights.map((insight, i) => (
                        <li key={i}>{insight}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Critique */}
            {state.critique && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Critical Analysis & Devil's Advocate
                </h3>
                {state.critique.challenges && state.critique.challenges.length > 0 && (
                  <div className="space-y-3">
                    {state.critique.challenges.map((challenge, idx) => (
                      <div key={idx} className={`
                        border-l-4 pl-4 py-2
                        ${challenge.severity === 'high' ? 'border-red-500 bg-red-50' :
                          challenge.severity === 'medium' ? 'border-yellow-500 bg-yellow-50' :
                          'border-blue-500 bg-blue-50'}
                      `}>
                        <p className="text-sm font-medium text-gray-900">
                          Claim: {challenge.claim}
                        </p>
                        <p className="text-sm text-gray-700 mt-1">
                          Challenge: {challenge.challenge}
                        </p>
                        <p className="text-sm text-gray-600 mt-1">
                          Resolution: {challenge.resolution}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Final Synthesis */}
            {state.final_synthesis && (
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg shadow-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-gray-900">
                    Strategic Intelligence Summary
                  </h3>
                  {state.confidence_score && (
                    <span className={`
                      px-3 py-1 rounded-full text-sm font-medium
                      ${state.confidence_score >= 0.8 ? 'bg-green-100 text-green-800' :
                        state.confidence_score >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'}
                    `}>
                      {(state.confidence_score * 100).toFixed(0)}% Confidence
                    </span>
                  )}
                </div>
                <div className="prose prose-sm max-w-none">
                  <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
                    {state.final_synthesis}
                  </p>
                </div>
              </div>
            )}

            {/* Metadata */}
            {state.execution_time_ms && (
              <div className="bg-gray-100 rounded-lg p-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Execution Time</p>
                    <p className="font-medium">{(state.execution_time_ms / 1000).toFixed(1)}s</p>
                  </div>
                  <div>
                    <p className="text-gray-600">LLM Calls</p>
                    <p className="font-medium">{state.llm_calls || 0}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Cost</p>
                    <p className="font-medium">${state.cost_usd?.toFixed(3) || '0.000'}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Agents Invoked</p>
                    <p className="font-medium">{state.agents_invoked?.length || 0}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

// Helper functions
function getStageIndex(stage: string): number {
  const stages = ['classify', 'prefetch', 'agents', 'debate', 'critique', 'synthesis'];
  return stages.indexOf(stage);
}

function formatStageName(stage: string): string {
  return stage.split('_').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
}

export default App;
```

---

## Next Steps

1. **Run Phase 1A Script:**
   ```powershell
   cd d:\lmis_int
   .\scripts\migrate_to_react.ps1 -Phase 1A
   ```

2. **Create the files above manually** in the locations specified

3. **Test the application:**
   ```bash
   cd qnwis-ui
   npm run dev
   ```

4. **Verify:**
   - React app loads at http://localhost:3000
   - Can submit a query
   - SSE streaming works
   - UI displays properly

5. **Commit your work** using the commit messages in the plan

---

## Troubleshooting

See `REACT_MIGRATION_PLAN.md` for common issues and solutions.
