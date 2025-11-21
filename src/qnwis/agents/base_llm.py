"""
Base class for LLM-powered agents.

All agents inherit from this and implement:
- _fetch_data(): What data to retrieve
- _build_prompt(): How to format prompt for LLM
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Optional, List, Any
from datetime import datetime, timezone

from qnwis.agents.base import DataClient, AgentReport, Insight, evidence_from
from qnwis.llm.client import LLMClient
from qnwis.llm.parser import LLMResponseParser, AgentFinding
from qnwis.llm.exceptions import LLMError, LLMParseError

logger = logging.getLogger(__name__)


# Zero Fabrication Citation Requirement
ZERO_FABRICATION_CITATION_RULES = """
═══════════════════════════════════════════════════════════════════════
MANDATORY CITATION FORMAT - ZERO FABRICATION GUARANTEE
═══════════════════════════════════════════════════════════════════════

RULE 1: Every metric, number, percentage, or statistic MUST include inline citation.

RULE 2: Citation format is EXACTLY:
  [Per extraction: '{exact_value}' from {source} {period}]

RULE 3: Example formats:
  ✅ CORRECT: "Qatar unemployment was [Per extraction: '0.10%' from GCC-STAT Q1-2024]"
  ✅ CORRECT: "Employment reached [Per extraction: '2.3M workers' from LMIS Database 2024-Q1]"
  ✅ CORRECT: "Qatarization rate stands at [Per extraction: '23.5%' from Ministry Report 2024]"

  ❌ WRONG: "Qatar unemployment is 0.10%" (no citation)
  ❌ WRONG: "Qatar unemployment is very low" (vague, no number)
  ❌ WRONG: "According to data, unemployment is 0.10%" (citation not inline)

RULE 4: If metric NOT in provided extraction:
  Write EXACTLY: "NOT IN DATA - cannot provide {metric_name} figure"

  Example: "Youth unemployment: NOT IN DATA - cannot provide youth unemployment figure"

RULE 5: NEVER round, estimate, or approximate without showing:
  "Approximately [Per extraction: '0.098%' from source] rounds to 0.1%"

═══════════════════════════════════════════════════════════════════════
VIOLATION CONSEQUENCES:
- Response will be flagged
- Confidence score reduced by 30%
- May be rejected entirely
═══════════════════════════════════════════════════════════════════════
"""


class LLMAgent(ABC):
    """
    Base class for LLM-powered agents.
    
    Provides streaming execution with:
    - Data fetching from deterministic layer
    - LLM reasoning with structured output
    - Number validation against source data
    - Progress updates via streaming
    """
    
    def __init__(
        self,
        client: DataClient,
        llm: LLMClient
    ):
        """
        Initialize LLM agent.
        
        Args:
            client: Data client for deterministic queries
            llm: LLM client for generation
        """
        self.client = client
        self.llm = llm
        self.parser = LLMResponseParser()
        self.agent_name = self.__class__.__name__.replace("Agent", "")
    
    async def run_stream(
        self,
        question: str,
        context: Optional[Dict] = None,
        debate_context: str = ""
    ) -> AsyncIterator[dict]:
        """Run agent with streaming output and stage-level error events."""
        context = context or {}
        # Preserve existing context but ensure debate context is available downstream
        context.setdefault("debate_context", debate_context)
        start_time = datetime.now(timezone.utc)

        try:
            yield {"type": "stage", "stage": "data_fetch", "message": f"{self.agent_name} fetching data"}
            try:
                data = await self._fetch_data(question, context)
            except Exception as exc:
                logger.error("%s data fetch failed: %s", self.agent_name, exc, exc_info=True)
                yield {"type": "error", "content": f"Data fetch failed: {exc}"}
                return

            if not data:
                yield {"type": "warning", "content": f"?? {self.agent_name} found no relevant data"}
                empty_report = AgentReport(
                    agent=self.agent_name,
                    findings=[],
                    narrative="No relevant data found for this query."
                )
                latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                yield {"type": "complete", "report": empty_report, "latency_ms": latency_ms}
                return

            yield {"type": "stage", "stage": "prompt_build", "message": f"{self.agent_name} building prompt"}
            try:
                system_prompt, user_prompt = self._build_prompt(question, data, context)
            except Exception as exc:
                logger.error("%s prompt build failed: %s", self.agent_name, exc, exc_info=True)
                yield {"type": "error", "content": f"Prompt build failed: {exc}"}
                return

            yield {"type": "stage", "stage": "llm_call", "message": f"{self.agent_name} calling LLM"}
            response_text = ""
            token_count = 0
            try:
                async for token in self.llm.generate_stream(
                    prompt=user_prompt,
                    system=system_prompt,
                    temperature=0.3,
                    max_tokens=4096,  # Increased from 2000 to allow full analysis
                ):
                    response_text += token
                    token_count += 1
                    yield {"type": "token", "content": token}
            except LLMError as exc:
                logger.error("%s LLM call failed: %s", self.agent_name, exc, exc_info=True)
                yield {"type": "error", "content": f"LLM call failed: {exc}"}
                return

            logger.info("%s generated %d tokens in %.1fs", self.agent_name, token_count, (datetime.now(timezone.utc) - start_time).total_seconds())

            yield {"type": "stage", "stage": "parse", "message": f"{self.agent_name} parsing results"}
            try:
                finding = self.parser.parse_agent_response(response_text)
            except (LLMParseError, ValueError) as exc:
                logger.warning("%s JSON parse failed, falling back to raw text: %s", self.agent_name, exc)
                # Graceful degradation: Construct a finding from raw text
                # We assume the raw text contains the analysis in markdown
                finding = AgentFinding(
                     title=f"{self.agent_name} Analysis (Fallback)",
                     summary="Analysis provided below (JSON parse failed)",
                     metrics={},
                     analysis=response_text, # Raw text as narrative
                     recommendations=[],
                     confidence=0.5, # Low confidence due to parse failure
                     citations=[],
                     data_quality_notes=f"JSON parse failed - showing raw output. Error: {exc}"
                )
                yield {"type": "warning", "content": f"JSON parse failed - showing raw output"}

            allowed_numbers = self.parser.extract_numbers_from_query_results(data)
            is_valid, violations = self.parser.validate_numbers(finding, allowed_numbers, tolerance=0.02)

            if not is_valid:
                logger.debug("%s number validation: %d metric(s) inferred", self.agent_name, len(violations))

            insight = Insight(
                title=finding.title,
                summary=finding.summary,
                metrics=finding.metrics or {},
                evidence=[evidence_from(qr) for qr in data.values()],
                warnings=violations if not is_valid else [],
            )

            report = AgentReport(
                agent=self.agent_name,
                findings=[insight],
                narrative=finding.analysis,
            )

            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.info("%s completed in %.0fms (confidence: %.2f)", self.agent_name, latency_ms, finding.confidence)

            yield {"type": "complete", "report": report, "latency_ms": latency_ms}

        except Exception as exc:
            logger.error("%s unexpected error: %s", self.agent_name, exc, exc_info=True)
            yield {"type": "error", "content": f"{self.agent_name} error: {exc}"}

    async def run(
        self,
        question: str,
        context: Optional[Dict] = None,
        debate_context: str = ""
    ) -> AgentReport:
        """Run agent without streaming while surfacing detailed error context."""
        context = context or {}
        logger.info("%s starting run()", self.agent_name)

        report: Optional[AgentReport] = None
        error_messages: list[str] = []

        try:
            async for event in self.run_stream(question, context, debate_context):
                event_type = event.get("type")
                if event_type == "complete":
                    report = event["report"]
                    break
                if event_type == "error":
                    message = event.get("content", "Unknown error")
                    error_messages.append(str(message))
                    logger.error("%s error event: %s", self.agent_name, message)
        except Exception as exc:
            logger.error("%s run_stream exception: %s", self.agent_name, exc, exc_info=True)
            raise RuntimeError(f"{self.agent_name} failed: {exc}") from exc

        if report is None:
            details = {
                "question_preview": (question or "")[:120],
                "context_keys": sorted(context.keys()),
                "errors": error_messages,
            }
            raise RuntimeError(
                f"{self.agent_name} failed to produce report. Details: {json.dumps(details, ensure_ascii=False)}"
            )

        logger.info("%s completed run()", self.agent_name)
        return report
    
    @abstractmethod
    async def _fetch_data(
        self,
        question: str,
        context: Dict
    ) -> Dict:
        """
        Fetch data needed for analysis.
        
        Must return dictionary of {key: QueryResult} from deterministic layer.
        
        Args:
            question: User's question
            context: Additional context
            
        Returns:
            Dictionary of QueryResults
        """
        pass
    
    @abstractmethod
    def _build_prompt(
        self,
        question: str,
        data: Dict,
        context: Dict
    ) -> tuple[str, str]:
        """
        Build agent-specific prompt for LLM.
        
        Args:
            question: User's question
            data: Dictionary of QueryResults
            context: Additional context
            
        Returns:
            (system_prompt, user_prompt) tuple
        """
        pass

    # --- Legendary Debate Conversation Methods ---

    async def present_case(self, topic: str, context: list) -> str:
        """Present opening statement on a topic."""
        
        prompt = f"""{topic}

Based on your expertise as {self.agent_name}, analyze this query and present your position.

CRITICAL INSTRUCTIONS:
- Address the specific query mentioned above
- Use evidence from available data
- Be specific and cite sources when possible
- Focus on your domain of expertise
- Keep response concise (2-3 paragraphs)
- If the query is unclear, analyze what information IS available

Your expert analysis:"""
        
        return await self.llm.generate(
            prompt=prompt,
            system=f"You are {self.agent_name}, providing expert analysis on the given query.",
            temperature=0.3,
            max_tokens=500
        )

    async def challenge_position(
        self, 
        opponent_name: str,
        opponent_claim: str,
        conversation_history: list
    ) -> str:
        """Challenge another agent's position."""
        history_text = self._format_history(conversation_history[-5:])
        
        # Extract original query from conversation history if available
        original_query = "Policy analysis"
        if conversation_history and len(conversation_history) > 0:
            first_turn = conversation_history[0]
            if isinstance(first_turn, dict) and 'message' in first_turn:
                msg = first_turn['message']
                if 'QUERY BEING ANALYZED:' in msg:
                    lines = msg.split('\n')
                    for i, line in enumerate(lines):
                        if 'QUERY BEING ANALYZED:' in line and i + 1 < len(lines):
                            original_query = lines[i + 1].strip()
                            break
        
        prompt = f"""You are {self.agent_name}.

ORIGINAL QUERY: {original_query}

{opponent_name} stated: "{opponent_claim[:300]}..."

Recent conversation:
{history_text}

Challenge this position by:
- Pointing out potential weaknesses IN THEIR SPECIFIC CLAIMS
- Presenting alternative interpretations of the data
- Questioning assumptions related to the original query
- Citing conflicting evidence or perspectives

Your challenge:"""
        
        return await self.llm.generate(
            prompt=prompt,
            system=f"You are {self.agent_name}, critically examining claims about the query.",
            temperature=0.4,
            max_tokens=400
        )

    async def respond_to_challenge(
        self,
        challenger_name: str, 
        challenge: str,
        conversation_history: list
    ) -> str:
        """Respond to a challenge."""
        history_text = self._format_history(conversation_history[-5:])
        
        prompt = f"""You are {self.agent_name}.

{challenger_name} challenged you: "{challenge}"

Recent conversation:
{history_text}

Respond by:
- Defending your position with evidence
- Acknowledging valid points
- Clarifying misunderstandings
- Finding common ground where possible

Use phrases like "I acknowledge...", "However...", "We agree that..." when appropriate.

Your response:"""
        
        return await self.llm.generate(
            prompt=prompt,
            system=f"You are {self.agent_name}, responding to critique.",
            temperature=0.3,
            max_tokens=400
        )

    async def contribute_to_discussion(
        self,
        conversation_history: list
    ) -> str:
        """Contribute to ongoing discussion."""
        history_text = self._format_history(conversation_history[-8:])
        
        prompt = f"""You are {self.agent_name}.

Ongoing debate:
{history_text}

Contribute your perspective by:
- Offering insights both sides may have missed
- Presenting additional evidence
- Proposing synthesis or middle ground
- Highlighting implications

Your contribution:"""
        
        return await self.llm.generate(
            prompt=prompt,
            system=f"You are {self.agent_name}, contributing expertise.",
            temperature=0.4,
            max_tokens=400
        )

    async def analyze_edge_case(
        self, 
        scenario: Dict,
        conversation_history: List[Dict]
    ) -> str:
        """Analyze edge case scenario from domain perspective."""
        
        prompt = f"""You are {self.agent_name}.

Edge Case Scenario:
- Description: {scenario.get('description', 'Unknown')}
- Severity: {scenario.get('severity', 'Unknown')}
- Probability: {scenario.get('probability_pct', 'Unknown')}%

Based on your domain expertise and the debate so far, analyze:
1. How would this scenario impact your domain?
2. Would your recommendations still hold?
3. What contingency measures are needed?
4. What early warning indicators should we monitor?

Be specific with numbers and timelines."""
        
        return await self.llm.generate(prompt=prompt, temperature=0.4)

    async def identify_catastrophic_risks(
        self,
        conversation_history: List[Dict],
        mode: str = "pessimistic"
    ) -> str:
        """Identify worst-case catastrophic failure in your domain."""
        
        debate_summary = self._summarize_recent_debate(conversation_history)
        
        prompt = f"""You are {self.agent_name}.

Debate summary: {debate_summary}

You are now playing DEVIL'S ADVOCATE in {mode} mode.

Identify the WORST-CASE CATASTROPHIC FAILURE in your domain:
1. What is the 1% tail risk everyone is ignoring?
2. What hidden assumption, if wrong, causes total failure?
3. What is the nightmare scenario that keeps you awake?
4. What combination of factors creates a perfect storm?

Be paranoid. Be specific. Use data to support your worst case."""
        
        return await self.llm.generate(prompt=prompt, temperature=0.5)

    async def assess_risk_likelihood(
        self,
        risk_description: str,
        conversation_history: List[Dict]
    ) -> str:
        """Assess likelihood and impact of identified risk."""
        
        prompt = f"""You are {self.agent_name}.

Another agent identified this risk:
{risk_description}

Assess from your domain perspective:
1. Likelihood (% probability in next 2 years)
2. Impact severity if it occurs (1-10 scale)
3. Early warning indicators
4. Mitigation strategies
5. Your confidence in this assessment

Be objective but critical."""
        
        return await self.llm.generate(prompt=prompt, temperature=0.3)

    async def state_final_position(
        self,
        debate_history: List[Dict],
        confidence_level: bool = True
    ) -> str:
        """State final position after debate."""
        history_text = self._format_history(debate_history[-10:])
        
        prompt = f"""You are {self.agent_name}.

The debate is concluding.
Recent conversation:
{history_text}

State your final position:
1. Your core recommendation
2. Key caveats or risks
3. Your final confidence level (0-100%)
4. What would change your mind?

Be decisive."""
        
        return await self.llm.generate(prompt=prompt, temperature=0.3)

    def _format_history(self, history: list) -> str:
        """Format conversation history for prompts."""
        lines = []
        for turn in history:
            agent = turn.get("agent", "Unknown")
            message = turn.get("message", "")
            lines.append(f"{agent}: {message[:200]}...")
        return "\n".join(lines)

    def _should_contribute(self, conversation_history: list) -> bool:
        """Decide if this agent should contribute to discussion."""
        # Contribute if: relevant keywords in recent conversation
        # For MVP, use simple keyword matching
        history_text = self._format_history(conversation_history[-3:])
        keywords = self._get_agent_keywords()
        
        return any(keyword.lower() in history_text.lower() for keyword in keywords)

    def _get_agent_keywords(self) -> list:
        """Get keywords relevant to this agent."""
        # Override in subclasses for better relevance detection
        return [self.agent_name.lower()]

    def _summarize_recent_debate(self, history: list) -> str:
        """Summarize recent debate turns."""
        if not history:
            return "No prior debate."
        return self._format_history(history[-10:])
