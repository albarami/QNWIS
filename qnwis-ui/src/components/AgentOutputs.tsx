import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './AgentOutputs.css';

interface AgentOutputsProps {
  result: {
    labour_economist_analysis?: string;
    financial_economist_analysis?: string;
    market_economist_analysis?: string;
    operations_expert_analysis?: string;
    research_scientist_analysis?: string;
    multi_agent_debate?: string;
    critique_output?: string;
  };
}

export function AgentOutputs({ result }: AgentOutputsProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    labour: false,
    financial: false,
    market: false,
    operations: false,
    research: false,
    debate: false,
    critique: false,
  });

  const toggle = (section: string) => {
    setExpanded(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const agents = [
    {
      key: 'labour',
      icon: '🧑‍💼',
      title: 'Labour Economist',
      subtitle: 'Supply-demand modeling & workforce transitions',
      content: result.labour_economist_analysis,
      color: '#3b82f6',
    },
    {
      key: 'financial',
      icon: '💰',
      title: 'Financial Economist',
      subtitle: 'GDP impact, FDI sensitivity & cost-benefit analysis',
      content: result.financial_economist_analysis,
      color: '#10b981',
    },
    {
      key: 'market',
      icon: '🌍',
      title: 'Market Economist',
      subtitle: 'Regional competition & game theory',
      content: result.market_economist_analysis,
      color: '#8b5cf6',
    },
    {
      key: 'operations',
      icon: '⚙️',
      title: 'Operations Expert',
      subtitle: 'Implementation reality & execution feasibility',
      content: result.operations_expert_analysis,
      color: '#f59e0b',
    },
    {
      key: 'research',
      icon: '🔬',
      title: 'Research Scientist',
      subtitle: 'Evidence grading & precedent analysis',
      content: result.research_scientist_analysis,
      color: '#ec4899',
    },
  ];

  const hasAnyAgent = agents.some(agent => agent.content && agent.content.length > 100);
  const hasDebate = Boolean(
    result.multi_agent_debate &&
      !result.multi_agent_debate.startsWith('⚠️') &&
      result.multi_agent_debate.length > 100
  );
  const hasCritique = Boolean(
    result.critique_output &&
      !result.critique_output.startsWith('⚠️') &&
      result.critique_output.length > 100
  );

  if (!hasAnyAgent && !hasDebate && !hasCritique) {
    return null;
  }

  return (
    <div className="agent-outputs-container">
      {hasAnyAgent && (
        <div className="section">
          <h2 className="section-title">🤖 Individual Agent Analyses</h2>
          <p className="section-description">
            Expand each expert's analysis to see methodology, citations, and conclusions
          </p>

          <div className="agents-grid">
            {agents.map(agent =>
              agent.content && agent.content.length > 100 ? (
                <div key={agent.key} className="agent-card">
                  <div
                    className="agent-header"
                    style={{ borderLeftColor: agent.color }}
                    onClick={() => toggle(agent.key)}
                  >
                    <div className="agent-title-section">
                      <span className="agent-icon">{agent.icon}</span>
                      <div>
                        <h3 className="agent-title">{agent.title}</h3>
                        <p className="agent-subtitle">{agent.subtitle}</p>
                      </div>
                    </div>
                    <button className="expand-btn" style={{ backgroundColor: agent.color }}>
                      {expanded[agent.key] ? '▼ Collapse' : '▶ Expand'}
                    </button>
                  </div>

                  {expanded[agent.key] && (
                    <div className="agent-content">
                      <div className="markdown-content">
                        <ReactMarkdown>{agent.content}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              ) : null
            )}
          </div>
        </div>
      )}

      {hasDebate && (
        <div className="section debate-section">
          <div className="special-header debate-header" onClick={() => toggle('debate')}>
            <div className="special-title-section">
              <span className="special-icon">💬</span>
              <div>
                <h2 className="special-title">Multi-Agent Debate</h2>
                <p className="special-subtitle">Cross-examination revealing contradictions</p>
              </div>
            </div>
            <button className="expand-btn debate-btn">
              {expanded.debate ? '▼ Collapse' : '▶ Expand'}
            </button>
          </div>

          {expanded.debate && (
            <div className="special-content">
              <div className="markdown-content debate-content">
                <ReactMarkdown>{result.multi_agent_debate ?? ''}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}

      {hasCritique && (
        <div className="section critique-section">
          <div className="special-header critique-header" onClick={() => toggle('critique')}>
            <div className="special-title-section">
              <span className="special-icon">😈</span>
              <div>
                <h2 className="special-title">Devil's Advocate Critique</h2>
                <p className="special-subtitle">Challenges assumptions & surfaces fatal risks</p>
              </div>
            </div>
            <button className="expand-btn critique-btn">
              {expanded.critique ? '▼ Collapse' : '▶ Expand'}
            </button>
          </div>

          {expanded.critique && (
            <div className="special-content">
              <div className="markdown-content critique-content">
                <ReactMarkdown>{result.critique_output ?? ''}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
