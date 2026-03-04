"""
LLM-specific exceptions.
"""


class LLMError(Exception):
    """Base exception for LLM errors."""
    ...


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    ...


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""
    ...


class LLMProviderError(LLMError):
    """LLM provider error (API down, invalid key, etc.)."""
    ...


class LLMParseError(LLMError):
    """Failed to parse LLM response."""
    ...


class LLMValidationError(LLMError):
    """LLM response failed validation."""
    ...
