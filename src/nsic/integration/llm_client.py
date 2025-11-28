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
            task_type=TaskType.REASONING,
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
        
        Args:
            engine_a_output: Output from Azure GPT-5 (deep analysis)
            engine_b_output: Output from local model (broad exploration)
            
        Returns:
            NSICResponse with synthesized insight
        """
        system = """You are the Meta-Synthesizer for NSIC's dual-engine ensemble.
Combine insights from both engines:
- Identify consensus points
- Resolve contradictions
- Synthesize comprehensive insight
- Cite which engine contributed each point"""
        
        prompt = f"""## Engine A (Deep Analysis):
{engine_a_output}

## Engine B (Broad Exploration):
{engine_b_output}

## Synthesized Insight:"""
        
        return await self.generate_async(
            prompt=prompt,
            system=system,
            task_type=TaskType.SYNTHESIS,
            max_tokens=4000,
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

