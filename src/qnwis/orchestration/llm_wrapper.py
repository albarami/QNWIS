"""
LLM wrapper with rate limiting.

ALL LLM calls must go through this wrapper to enforce rate limits.
This prevents 429 errors from Claude API during parallel scenario execution.
"""

import logging
from typing import Any
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

