"""
LLM wrapper with rate limiting and hybrid model routing.

ALL LLM calls must go through this wrapper to enforce rate limits.
This prevents 429 errors from Claude API during parallel scenario execution.

Hybrid Model Routing (2025-11-27):
- GPT-4o: Fast tasks (extraction, verification, classification)
- GPT-5: Reasoning tasks (debate, synthesis, scenarios, analysis)
"""

import logging
from typing import Any, Optional, Dict
from .rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


async def call_llm_with_rate_limit(llm: Any, prompt: Any) -> Any:
    """
    Call LLM with rate limiting.
    
    This is the ONLY way LLM calls should be made in the system.
    Wraps individual llm.ainvoke() calls with rate limiting to prevent
    429 errors during parallel scenario execution.
    
    Args:
        llm: LLM instance (e.g., ChatAnthropic)
        prompt: Prompt to send to LLM (string or messages)
        
    Returns:
        LLM response
        
    Example:
        ```python
        from qnwis.orchestration.llm_wrapper import call_llm_with_rate_limit
        
        llm = ChatAnthropic(model="claude-sonnet-4.5-20250514")
        response = await call_llm_with_rate_limit(llm, "Your prompt here")
        ```
    """
    rate_limiter = get_rate_limiter()
    return await rate_limiter.execute_with_rate_limit(
        llm.ainvoke,  # Individual LLM call
        prompt
    )


async def call_llm_with_routing(
    prompt: str,
    *,
    task_type: str = "general",
    system_prompt: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: int = 300,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Call LLM with hybrid model routing and rate limiting.
    
    Routes requests to optimal model based on task type:
    - GPT-4o (fast): extraction, verification, classification, citation_check, fact_check
    - GPT-5 (primary): debate, synthesis, scenario_generation, agent_analysis, etc.
    
    Args:
        prompt: The user prompt
        task_type: Type of task for routing (e.g., "extraction", "debate", "synthesis")
        system_prompt: Optional system prompt
        max_tokens: Max tokens (uses model config default if not specified)
        temperature: Temperature (uses model config default: 0.1 for fast, 0.3 for primary)
        timeout: Request timeout in seconds
        metadata: Optional metadata for metrics
        
    Returns:
        Generated response string
        
    Example:
        ```python
        from qnwis.orchestration.llm_wrapper import call_llm_with_routing
        
        # Uses GPT-4o (fast, deterministic)
        facts = await call_llm_with_routing(
            prompt="Extract key facts from this text...",
            task_type="extraction",
            system_prompt="You are a fact extraction specialist."
        )
        
        # Uses GPT-5 (reasoning)
        synthesis = await call_llm_with_routing(
            prompt="Synthesize these agent reports...",
            task_type="final_synthesis",
            system_prompt="You are a ministerial advisor."
        )
        ```
    """
    from ..llm.client import LLMClient
    
    rate_limiter = get_rate_limiter()
    
    # Create a temporary client for routing
    # Note: The actual model selection happens inside generate_with_routing
    client = LLMClient()
    
    async def _call():
        return await client.generate_with_routing(
            prompt=prompt,
            task_type=task_type,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            metadata=metadata,
        )
    
    logger.debug(f"call_llm_with_routing: task_type={task_type}")
    return await rate_limiter.execute_with_rate_limit(_call)

