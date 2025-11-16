/**
 * Metrics Display Component for QNWIS Workflow
 * 
 * Displays comprehensive query execution metrics including cost, latency,
 * token usage, and quality indicators.
 */

import React from 'react';
import './MetricsDisplay.css';

export interface QueryMetrics {
  query_id: string;
  query_text: string;
  total_latency_ms: number;
  total_cost_usd: number;
  llm_calls_count: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  cost_per_token: number;
  agents_invoked: string[];
  agent_count: number;
  complexity: string;
  confidence: number;
  citation_violations: number;
  facts_extracted: number;
  status: string;
}

interface MetricsDisplayProps {
  metrics: QueryMetrics;
  expanded?: boolean;
}

export const MetricsDisplay: React.FC<MetricsDisplayProps> = ({ 
  metrics, 
  expanded = false 
}) => {
  const [isExpanded, setIsExpanded] = React.useState(expanded);

  const formatLatency = (ms: number): string => {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatCost = (cost: number): string => {
    return `$${cost.toFixed(4)}`;
  };

  const formatTokens = (tokens: number): string => {
    if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(2)}M`;
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`;
    return tokens.toString();
  };

  const getComplexityColor = (complexity: string): string => {
    switch (complexity.toLowerCase()) {
      case 'simple': return 'green';
      case 'medium': return 'orange';
      case 'complex': return 'red';
      default: return 'gray';
    }
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'green';
    if (confidence >= 0.6) return 'orange';
    return 'red';
  };

  return (
    <div className="metrics-display">
      <div className="metrics-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h3>📊 Query Metrics</h3>
        <button className="expand-button">
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      <div className={`metrics-content ${isExpanded ? 'expanded' : 'collapsed'}`}>
        {/* Cost & Performance Section */}
        <div className="metrics-section">
          <h4>💰 Cost & Performance</h4>
          
          <div className="metric-row">
            <span className="label">Total Cost:</span>
            <span className="value highlight-cost">{formatCost(metrics.total_cost_usd)}</span>
          </div>
          
          <div className="metric-row">
            <span className="label">Latency:</span>
            <span className="value">{formatLatency(metrics.total_latency_ms)}</span>
          </div>
          
          <div className="metric-row">
            <span className="label">Cost per 1K Tokens:</span>
            <span className="value">${(metrics.cost_per_token * 1000).toFixed(3)}</span>
          </div>
        </div>

        {/* LLM Usage Section */}
        <div className="metrics-section">
          <h4>🤖 LLM Usage</h4>
          
          <div className="metric-row">
            <span className="label">LLM Calls:</span>
            <span className="value">{metrics.llm_calls_count}</span>
          </div>
          
          <div className="metric-row">
            <span className="label">Total Tokens:</span>
            <span className="value">{formatTokens(metrics.total_tokens)}</span>
          </div>
          
          <div className="metric-row sub-metric">
            <span className="label">Input:</span>
            <span className="value">{formatTokens(metrics.input_tokens)}</span>
          </div>
          
          <div className="metric-row sub-metric">
            <span className="label">Output:</span>
            <span className="value">{formatTokens(metrics.output_tokens)}</span>
          </div>
        </div>

        {/* Workflow Quality Section */}
        <div className="metrics-section">
          <h4>✨ Workflow Quality</h4>
          
          <div className="metric-row">
            <span className="label">Complexity:</span>
            <span className={`value badge badge-${getComplexityColor(metrics.complexity)}`}>
              {metrics.complexity}
            </span>
          </div>
          
          <div className="metric-row">
            <span className="label">Confidence:</span>
            <span className={`value badge badge-${getConfidenceColor(metrics.confidence)}`}>
              {(metrics.confidence * 100).toFixed(0)}%
            </span>
          </div>
          
          <div className="metric-row">
            <span className="label">Agents Invoked:</span>
            <span className="value">{metrics.agent_count}</span>
          </div>
          
          <div className="metric-row">
            <span className="label">Facts Extracted:</span>
            <span className="value">{metrics.facts_extracted}</span>
          </div>
          
          {metrics.citation_violations > 0 && (
            <div className="metric-row warning">
              <span className="label">⚠️ Citation Violations:</span>
              <span className="value">{metrics.citation_violations}</span>
            </div>
          )}
        </div>

        {/* Agents Details (Expandable) */}
        {isExpanded && metrics.agents_invoked.length > 0 && (
          <div className="metrics-section">
            <h4>👥 Agents Involved</h4>
            <div className="agents-list">
              {metrics.agents_invoked.map((agent, idx) => (
                <span key={idx} className="agent-badge">
                  {agent}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Debug Info (Very Expanded) */}
        {isExpanded && (
          <div className="metrics-section debug-info">
            <details>
              <summary>🔧 Debug Info</summary>
              <div className="debug-content">
                <div className="metric-row">
                  <span className="label">Query ID:</span>
                  <span className="value mono">{metrics.query_id}</span>
                </div>
                <div className="metric-row">
                  <span className="label">Status:</span>
                  <span className="value">{metrics.status}</span>
                </div>
              </div>
            </details>
          </div>
        )}
      </div>
    </div>
  );
};

// Summary component for compact display
export const MetricsSummary: React.FC<{ metrics: QueryMetrics }> = ({ metrics }) => {
  return (
    <div className="metrics-summary">
      <span className="summary-item">
        💰 {(metrics.total_cost_usd * 1000).toFixed(2)}¢
      </span>
      <span className="summary-item">
        ⚡ {(metrics.total_latency_ms / 1000).toFixed(1)}s
      </span>
      <span className="summary-item">
        🤖 {metrics.llm_calls_count} calls
      </span>
      <span className="summary-item">
        ✨ {(metrics.confidence * 100).toFixed(0)}%
      </span>
    </div>
  );
};

export default MetricsDisplay;
