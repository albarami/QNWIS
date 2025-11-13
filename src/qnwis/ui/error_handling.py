"""
Production-grade error handling for Chainlit UI.

Provides graceful degradation, user-friendly error messages,
and automatic retry logic for transient failures.
"""

from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional

import chainlit as cl

logger = logging.getLogger(__name__)


class UIError(Exception):
    """Base exception for UI errors with user-friendly messages."""

    def __init__(self, user_message: str, technical_details: str = ""):
        self.user_message = user_message
        self.technical_details = technical_details
        super().__init__(user_message)


class LLMTimeoutError(UIError):
    """LLM request timed out."""
    pass


class LLMRateLimitError(UIError):
    """LLM rate limit exceeded."""
    pass


class DataUnavailableError(UIError):
    """Required data not available."""
    pass


def format_error_message(error: Exception) -> tuple[str, str]:
    """
    Format error into user-friendly message and technical details.

    Returns:
        (user_message, technical_details) tuple
    """
    if isinstance(error, UIError):
        return error.user_message, error.technical_details

    # LLM timeout errors
    if "timeout" in str(error).lower():
        return (
            "⏱️ The analysis is taking longer than expected. "
            "The system is processing complex workforce data. Please try again.",
            str(error)
        )

    # Rate limit errors
    if "rate limit" in str(error).lower() or "429" in str(error):
        return (
            "⚠️ The system is currently experiencing high demand. "
            "Please wait a moment and try again.",
            str(error)
        )

    # API key errors
    if "api key" in str(error).lower() or "authentication" in str(error).lower():
        return (
            "🔐 There is a configuration issue with the AI service. "
            "Please contact the system administrator.",
            str(error)
        )

    # Database errors
    if "database" in str(error).lower() or "connection" in str(error).lower():
        return (
            "💾 Unable to access workforce data. "
            "Please check your connection and try again.",
            str(error)
        )

    # Generic error
    return (
        "❌ An unexpected error occurred. "
        "The technical team has been notified. Please try again.",
        str(error)
    )


async def show_error_message(error: Exception):
    """
    Display user-friendly error message in Chainlit UI.

    Args:
        error: Exception that occurred
    """
    user_msg, technical = format_error_message(error)

    # Show user-friendly message
    await cl.Message(
        content=f"""
## Error Occurred

{user_msg}

---

**What you can try:**
- Simplify your question
- Try again in a few moments
- Contact support if the issue persists

**Error ID:** `{id(error)}`
""",
        author="System"
    ).send()

    # Log technical details
    logger.error(f"UI Error [ID:{id(error)}]: {technical}", exc_info=error)


def with_error_handling(show_ui_message: bool = True):
    """
    Decorator for graceful error handling in async functions.

    Args:
        show_ui_message: Whether to show error message in UI

    Example:
        @with_error_handling()
        async def query_handler(message: str):
            # Your code here
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Error in {func.__name__}")
                if show_ui_message:
                    await show_error_message(e)
                raise
        return wrapper
    return decorator


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplication factor for each retry
        exceptions: Tuple of exceptions to catch

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            last_exception = e

            if attempt < max_retries - 1:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"All {max_retries} attempts failed")

    raise last_exception


class ErrorRecovery:
    """Handles error recovery with fallback strategies."""

    @staticmethod
    async def try_with_fallback_model(
        primary_func: Callable,
        fallback_func: Callable,
        error_message: Optional[str] = None
    ) -> Any:
        """
        Try primary function, fall back to secondary if it fails.

        Args:
            primary_func: Primary async function
            fallback_func: Fallback async function
            error_message: Custom error message

        Returns:
            Result from primary or fallback function
        """
        try:
            return await primary_func()
        except Exception as e:
            logger.warning(f"Primary function failed: {e}. Trying fallback...")

            if error_message:
                await cl.Message(
                    content=f"⚠️ {error_message}",
                    author="System"
                ).send()

            return await fallback_func()

    @staticmethod
    async def partial_results_recovery(
        funcs: list[Callable],
        min_required: int = 1
    ) -> list[Any]:
        """
        Execute multiple functions, return partial results if some fail.

        Args:
            funcs: List of async functions to execute
            min_required: Minimum number of successful results required

        Returns:
            List of successful results

        Raises:
            Exception if fewer than min_required succeed
        """
        results = []
        errors = []

        for func in funcs:
            try:
                result = await func()
                results.append(result)
            except Exception as e:
                logger.warning(f"Function {func.__name__} failed: {e}")
                errors.append(e)

        if len(results) < min_required:
            raise Exception(
                f"Only {len(results)}/{len(funcs)} functions succeeded. "
                f"Required: {min_required}"
            )

        if errors:
            logger.warning(
                f"{len(errors)} functions failed, but continuing with "
                f"{len(results)} successful results"
            )

        return results
