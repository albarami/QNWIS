"""
Base class for LLM-powered agents.

All agents inherit from this and implement:
- _fetch_data(): What data to retrieve
- _build_prompt(): How to format prompt for LLM
"""

import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Optional
from datetime import datetime, timezone

from src.qnwis.agents.base import DataClient, AgentReport, Insight, evidence_from
from src.qnwis.llm.client import LLMClient
from src.qnwis.llm.parser import LLMResponseParser, AgentFinding
from src.qnwis.llm.exceptions import LLMError, LLMParseError

logger = logging.getLogger(__name__)


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
        context: Optional[Dict] = None
    ) -> AsyncIterator[dict]:
        """
        Run agent with streaming output.
        
        Yields events:
        - {"type": "status", "content": "Status message"}
        - {"type": "token", "content": "LLM token"}
        - {"type": "warning", "content": "Warning message"}
        - {"type": "complete", "report": AgentReport, "latency_ms": float}
        - {"type": "error", "content": "Error message"}
        
        Args:
            question: User's question
            context: Additional context (classification, prefetch, etc.)
            
        Yields:
            Stream events
        """
        context = context or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            # 1. Fetch data from deterministic layer
            yield {
                "type": "status",
                "content": f"🔍 {self.agent_name} fetching data..."
            }
            
            data = await self._fetch_data(question, context)
            
            if not data:
                yield {
                    "type": "warning",
                    "content": f"⚠️ {self.agent_name} found no relevant data"
                }
                # Return empty report
                empty_report = AgentReport(
                    agent=self.agent_name,
                    findings=[],
                    narrative="No relevant data found for this query."
                )
                latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                yield {"type": "complete", "report": empty_report, "latency_ms": latency_ms}
                return
            
            # 2. Build prompt with data
            yield {
                "type": "status",
                "content": f"🤔 {self.agent_name} analyzing..."
            }
            
            system_prompt, user_prompt = self._build_prompt(question, data, context)
            
            # 3. Stream LLM response
            response_text = ""
            token_count = 0
            
            async for token in self.llm.generate_stream(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.3,
                max_tokens=2000
            ):
                response_text += token
                token_count += 1
                
                # Yield tokens for UI display
                yield {"type": "token", "content": token}
            
            logger.info(
                f"{self.agent_name} generated {token_count} tokens "
                f"in {(datetime.now(timezone.utc) - start_time).total_seconds():.1f}s"
            )
            
            # 4. Parse response
            yield {
                "type": "status",
                "content": f"✅ {self.agent_name} parsing results..."
            }
            
            try:
                finding = self.parser.parse_agent_response(response_text)
            except LLMParseError as e:
                logger.error(f"{self.agent_name} parse failed: {e}")
                yield {
                    "type": "error",
                    "content": f"❌ {self.agent_name} failed to parse LLM response: {e}"
                }
                # Return error report
                error_report = AgentReport(
                    agent=self.agent_name,
                    findings=[],
                    narrative=f"Failed to parse LLM response: {e}"
                )
                latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                yield {"type": "complete", "report": error_report, "latency_ms": latency_ms}
                return
            
            # 5. Validate numbers against source data
            allowed_numbers = self.parser.extract_numbers_from_query_results(data)
            is_valid, violations = self.parser.validate_numbers(
                finding,
                allowed_numbers,
                tolerance=0.02  # 2% tolerance for rounding
            )
            
            if not is_valid:
                logger.warning(
                    f"{self.agent_name} number validation failed: "
                    f"{len(violations)} violations"
                )
                yield {
                    "type": "warning",
                    "content": f"⚠️ {self.agent_name}: {len(violations)} number validation warnings"
                }
            
            # 6. Convert to AgentReport
            insight = Insight(
                title=finding.title,
                summary=finding.summary,
                metrics=finding.metrics,
                evidence=[evidence_from(qr) for qr in data.values()],
                warnings=violations if not is_valid else [],
                confidence_score=finding.confidence
            )
            
            report = AgentReport(
                agent=self.agent_name,
                findings=[insight],
                narrative=finding.analysis
            )
            
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            logger.info(
                f"{self.agent_name} completed in {latency_ms:.0f}ms "
                f"(confidence: {finding.confidence:.2f})"
            )
            
            yield {
                "type": "complete",
                "report": report,
                "latency_ms": latency_ms
            }
            
        except LLMError as e:
            logger.error(f"{self.agent_name} LLM error: {e}", exc_info=True)
            yield {
                "type": "error",
                "content": f"❌ {self.agent_name} LLM error: {str(e)}"
            }
            
        except Exception as e:
            logger.error(f"{self.agent_name} unexpected error: {e}", exc_info=True)
            yield {
                "type": "error",
                "content": f"❌ {self.agent_name} error: {str(e)}"
            }
    
    async def run(
        self,
        question: str,
        context: Optional[Dict] = None
    ) -> AgentReport:
        """
        Run agent without streaming (for backward compatibility).
        
        Args:
            question: User's question
            context: Additional context
            
        Returns:
            AgentReport
            
        Raises:
            RuntimeError: If agent fails to produce report
        """
        report = None
        
        async for event in self.run_stream(question, context):
            if event["type"] == "complete":
                report = event["report"]
                break
        
        if report is None:
            raise RuntimeError(f"{self.agent_name} failed to produce report")
        
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
