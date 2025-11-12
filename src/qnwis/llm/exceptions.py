"""
LLM-specific exceptions.
"""


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    pass


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""
    pass


class LLMProviderError(LLMError):
    """LLM provider error (API down, invalid key, etc.)."""
    pass


class LLMParseError(LLMError):
    """Failed to parse LLM response."""
    pass


class LLMValidationError(LLMError):
    """LLM response failed validation."""
    pass
