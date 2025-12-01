"""
NSIC LLM Client - Wraps the existing QNWIS Azure LLM client.

NO MOCKS. Uses the REAL Azure GPT-5 and GPT-4o deployment.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass

# Import the REAL QNWIS LLM client
from src.qnwis.llm.client import LLMClient, get_client
from src.qnwis.llm.model_router import ModelRouter, TaskType, get_router

logger = logging.getLogger(__name__)


@dataclass
class NSICResponse:
    """Response from NSIC LLM."""
    content: str
    model: str
    task_type: str
    tokens_used: int = 0
    latency_ms: float = 0.0


class NSICLLMClient:
    """
    NSIC LLM Client - Uses REAL Azure GPT-5/GPT-4o.
    
    Wraps the existing QNWIS LLM infrastructure.
    
    Models available:
    - GPT-5 (gpt-5-chat): Best for reasoning, debate, synthesis
    - GPT-4o: Best for extraction, verification, deterministic tasks
    """
    
    def __init__(self):
        """Initialize with real Azure connections."""
        self.router = get_router()
        self._stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_latency_ms": 0.0,
        }
        
        # Verify we have real API keys
        primary = self.router.primary_config
        fast = self.router.fast_config
        
        if not primary.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY or API_KEY_5 not configured!")
        
        logger.info(
            f"NSICLLMClient initialized with REAL Azure connections: "
            f"primary={primary.deployment}, fast={fast.deployment}"
        )
    
    async def generate_async(
        self,
        prompt: str,
        system: str = "",
        task_type: TaskType = TaskType.GENERAL,
        max_tokens: int = 2000,
        temperature: Optional[float] = None,
    ) -> NSICResponse:
        """
        Generate response using Azure GPT-5/GPT-4o.
        
        Args:
            prompt: User prompt
            system: System prompt
            task_type: Type of task (determines which model to use)
            max_tokens: Maximum tokens
            temperature: Override temperature
            
        Returns:
            NSICResponse with content and metadata
        """
        import time
        start_time = time.time()
        
        # Get model config for task type
        config = self.router.get_model_config(task_type)
        
        # Create client with specific model
        client = get_client(
            provider="azure",
            model=config.deployment,
        )
        
        # Override temperature if specified
        temp = temperature if temperature is not None else config.temperature
        
        # Collect streamed response
        content_parts = []
        async for chunk in client.generate_stream(
            prompt=prompt,
            system=system,
            temperature=temp,
            max_tokens=max_tokens,
        ):
            content_parts.append(chunk)
        
        content = "".join(content_parts)
        latency_ms = (time.time() - start_time) * 1000
        
        # Update stats
        self._stats["total_requests"] += 1
        self._stats["total_latency_ms"] += latency_ms
        
        return NSICResponse(
            content=content,
            model=config.deployment,
            task_type=task_type.value,
            latency_ms=latency_ms,
        )
    
    async def stream_async(
        self,
        prompt: str,
        system: str = "",
        task_type: TaskType = TaskType.GENERAL,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """
        Stream response tokens.
        
        Args:
            prompt: User prompt
            system: System prompt
            task_type: Task type
            max_tokens: Maximum tokens
            
        Yields:
            Response tokens
        """
        config = self.router.get_model_config(task_type)
        
        client = get_client(
            provider="azure",
            model=config.deployment,
        )
        
        async for chunk in client.generate_stream(
            prompt=prompt,
            system=system,
            temperature=config.temperature,
            max_tokens=max_tokens,
        ):
            yield chunk
    
    def generate_sync(
        self,
        prompt: str,
        system: str = "",
        task_type: TaskType = TaskType.GENERAL,
        max_tokens: int = 2000,
    ) -> NSICResponse:
        """Synchronous version of generate_async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.generate_async(prompt, system, task_type, max_tokens)
        )
    
    async def analyze_scenario(
        self,
        scenario: str,
        context: str = "",
        depth: str = "comprehensive",
    ) -> NSICResponse:
        """
        Analyze a scenario using GPT-5 (best for reasoning).
        
        Args:
            scenario: Scenario description
            context: Additional context
            depth: Analysis depth
            
        Returns:
            NSICResponse with analysis
        """
        system = f"""You are an expert economic analyst for Qatar's National Strategic Intelligence Center (NSIC).
Provide {depth} analysis with:
- Causal chain reasoning
- Cross-domain impacts
- Quantified estimates where possible
- Uncertainty acknowledgment
- Policy recommendations

Use the provided context from the knowledge graph and database."""
        
        prompt = f"""## Context from NSIC Knowledge Base:
{context}

## Scenario to Analyze:
{scenario}

Provide your analysis:"""
        
        return await self.generate_async(
            prompt=prompt,
            system=system,
            task_type=TaskType.AGENT_ANALYSIS,  # Use primary model for deep reasoning
            max_tokens=4000,
        )
    
    async def verify_claim(
        self,
        claim: str,
        evidence: str,
    ) -> NSICResponse:
        """
        Verify a claim against evidence using GPT-4o (deterministic).
        
        Args:
            claim: Claim to verify
            evidence: Evidence to check against
            
        Returns:
            NSICResponse with verification result
        """
        system = """You are a fact-checker for NSIC. Verify claims strictly against evidence.
Output JSON:
{
  "verdict": "SUPPORTED" | "CONTRADICTED" | "INSUFFICIENT_EVIDENCE",
  "confidence": 0.0-1.0,
  "reasoning": "explanation"
}"""
        
        prompt = f"""Claim: {claim}

Evidence: {evidence}

Verify:"""
        
        return await self.generate_async(
            prompt=prompt,
            system=system,
            task_type=TaskType.EXTRACTION,  # Use fast model for deterministic task
            max_tokens=500,
        )
    
    async def synthesize_insights(
        self,
        engine_a_output: str,
        engine_b_output: str,
    ) -> NSICResponse:
        """
        Synthesize outputs from both engines into final insight.
        
        FIX 6: Updated with McKinsey-grade financial requirements.
        
        Args:
            engine_a_output: Output from Azure GPT-5 (deep analysis)
            engine_b_output: Output from local model (broad exploration)
            
        Returns:
            NSICResponse with synthesized insight including NPV/IRR
        """
        system = """You are the Meta-Synthesizer for NSIC's dual-engine ensemble.

REQUIRED OUTPUT FORMAT (McKinsey-Grade):

## 1. EXECUTIVE RECOMMENDATION
[Clear choice: Option A or Option B]
Confidence: [X%] with justification

## 2. FINANCIAL COMPARISON TABLE

| Metric | Option A | Option B | Source |
|--------|----------|----------|--------|
| NPV (10yr, 8%) | QAR X B | QAR Y B | NSIC Model |
| IRR | X% | Y% | NSIC Model |
| GDP Impact | +X% | +Y% | Engine A |
| Jobs Created | X,XXX | Y,YYY | Engine B |
| Payback Period | X years | Y years | NSIC Model |

## 3. KEY DEBATE FINDINGS
- Consensus points from both engines
- Contested points with resolution

## 4. RISK MATRIX

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
(Top 5 risks)

## 5. IMPLEMENTATION ROADMAP
Phase 1 (0-6 months): ...
Phase 2 (6-18 months): ...
Phase 3 (18-36 months): ...
Phase 4 (36-60 months): ...

## 6. DISSENTING VIEW
[Summary of strongest counter-argument]

CITATION REQUIREMENT: Every number must have [Source] tag.
"""
        
        prompt = f"""## Engine A (Deep Analysis - 6 scenarios, 600 turns):
{engine_a_output}

## Engine B (Broad Exploration - 24 scenarios, 600 turns):
{engine_b_output}

## Synthesized Ministerial Brief:"""
        
        return await self.generate_async(
            prompt=prompt,
            system=system,
            task_type=TaskType.FINAL_SYNTHESIS,  # Use primary model for synthesis
            max_tokens=6000,  # Increased for full brief
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        avg_latency = (
            self._stats["total_latency_ms"] / self._stats["total_requests"]
            if self._stats["total_requests"] > 0
            else 0
        )
        return {
            **self._stats,
            "avg_latency_ms": avg_latency,
            "models": {
                "primary": self.router.primary_config.deployment,
                "fast": self.router.fast_config.deployment,
            }
        }


def get_nsic_llm_client() -> NSICLLMClient:
    """Factory function to get NSIC LLM client."""
    return NSICLLMClient()

