"""
Synthesis engine for multi-agent findings.

Uses LLM to synthesize agent reports into coherent, ministerial-quality answers.
"""

import logging
from typing import List, AsyncIterator

from src.qnwis.agents.base import AgentReport
from src.qnwis.llm.client import LLMClient

logger = logging.getLogger(__name__)


SYNTHESIS_SYSTEM_PROMPT = """You are a senior policy analyst for Qatar's Ministry of Labour.

Your role is to synthesize findings from multiple specialized agents into a coherent, 
ministerial-quality response that is:

1. **Executive-ready**: Clear, concise, actionable
2. **Evidence-based**: All claims supported by agent findings
3. **Contextual**: Considers Qatar's Vision 2030 and regional context
4. **Balanced**: Presents multiple perspectives when relevant
5. **Forward-looking**: Includes recommendations and implications

SYNTHESIS GUIDELINES:
- Start with a clear executive summary (2-3 sentences)
- Organize findings by theme, not by agent
- Highlight key insights and patterns across agents
- Include specific metrics and evidence
- Provide actionable recommendations
- Acknowledge data limitations or uncertainties
- Use professional, ministerial tone

CRITICAL: Only use information from the agent reports provided. Do not fabricate data."""


def _build_synthesis_prompt(question: str, reports: List[AgentReport]) -> str:
    """
    Build synthesis prompt from agent reports.
    
    Args:
        question: Original user question
        reports: List of agent reports
        
    Returns:
        Formatted user prompt
    """
    prompt_parts = [
        "TASK: Synthesize the following agent findings into a coherent answer.",
        "",
        f"USER QUESTION: {question}",
        "",
        "AGENT FINDINGS:",
        ""
    ]
    
    for report in reports:
        if not report.findings:
            continue
        
        prompt_parts.append(f"### {report.agent} Agent")
        prompt_parts.append("")
        
        # Add narrative if present
        if report.narrative:
            prompt_parts.append(f"**Analysis**: {report.narrative}")
            prompt_parts.append("")
        
        # Add findings
        for finding in report.findings:
            prompt_parts.append(f"**{finding.title}**")
            prompt_parts.append(f"{finding.summary}")
            
            # Add metrics
            if finding.metrics:
                prompt_parts.append("")
                prompt_parts.append("Key metrics:")
                for key, value in (finding.metrics or {}).items():
                    prompt_parts.append(f"- {key}: {value}")
            
            # Add warnings
            if finding.warnings:
                prompt_parts.append("")
                prompt_parts.append("⚠️ Warnings:")
                for warning in finding.warnings[:3]:  # Limit to 3
                    prompt_parts.append(f"- {warning}")
            
            prompt_parts.append("")
    
    prompt_parts.extend([
        "",
        "SYNTHESIS INSTRUCTIONS:",
        "1. Provide an executive summary (2-3 sentences)",
        "2. Synthesize key findings by theme",
        "3. Include specific metrics and evidence",
        "4. Provide actionable recommendations",
        "5. Note any data quality concerns",
        "",
        "Write your synthesis in clear, professional markdown format."
    ])
    
    return "\n".join(prompt_parts)


class SynthesisEngine:
    """
    Engine for synthesizing multi-agent findings.
    
    Uses LLM to create coherent, ministerial-quality responses
    from multiple agent reports.
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize synthesis engine.
        
        Args:
            llm_client: LLM client for generation
        """
        self.llm = llm_client
    
    async def synthesize_stream(
        self,
        question: str,
        reports: List[AgentReport]
    ) -> AsyncIterator[str]:
        """
        Synthesize agent findings with streaming.
        
        Args:
            question: Original user question
            reports: List of agent reports
            
        Yields:
            Synthesis text tokens
        """
        if not reports:
            yield "No agent findings available to synthesize."
            return
        
        # Build prompt
        user_prompt = _build_synthesis_prompt(question, reports)
        
        logger.info(f"Starting synthesis for {len(reports)} agent reports")
        
        try:
            # Stream synthesis
            async for token in self.llm.generate_stream(
                prompt=user_prompt,
                system=SYNTHESIS_SYSTEM_PROMPT,
                temperature=0.4,  # Slightly higher for more natural synthesis
                max_tokens=3000
            ):
                yield token
        
        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            # Fallback to simple concatenation
            yield "\n\n## Agent Findings\n\n"
            for report in reports:
                if report.narrative:
                    yield f"**{report.agent}**: {report.narrative}\n\n"
    
    async def synthesize(
        self,
        question: str,
        reports: List[AgentReport]
    ) -> str:
        """
        Synthesize agent findings (non-streaming).
        
        Args:
            question: Original user question
            reports: List of agent reports
            
        Returns:
            Complete synthesis text
        """
        synthesis = ""
        async for token in self.synthesize_stream(question, reports):
            synthesis += token
        return synthesis
