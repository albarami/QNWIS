"""
Unified LLM client for QNWIS.

Supports Anthropic Claude, OpenAI GPT, and a deterministic stub provider with
streaming, bounded timeouts, jittered retries, and safe logging.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import AsyncIterator, Optional, Dict, Any

from src.qnwis.llm.config import LLMConfig, get_llm_config
from src.qnwis.llm.exceptions import (
    LLMTimeoutError,
    LLMRateLimitError,
    LLMProviderError,
)
from src.qnwis.observability.metrics import record_llm_call

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client supporting Anthropic and OpenAI.
    
    Provides streaming generation with automatic retries,
    timeout handling, and fallback support.
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout_s: Optional[int] = None,
        config: Optional[LLMConfig] = None
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: "anthropic", "openai", or "stub" (default from config)
            model: Model name (default from config)
            timeout_s: Timeout in seconds
            config: LLMConfig instance (default: load from env)
        """
        self.config = config or get_llm_config()
        self.provider = (provider or self.config.provider).lower()
        self.model = model or self.config.get_model(self.provider)
        configured_timeout = self.config.timeout_seconds
        effective_timeout = timeout_s if timeout_s is not None else configured_timeout
        self.timeout_s = min(effective_timeout, 60)
        self.max_retries = self.config.max_retries
        self._stub_delay_s = self.config.stub_token_delay_ms / 1000.0
        
        # Initialize provider client
        if self.provider == "anthropic":
            self._init_anthropic()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "stub":
            self._init_stub()
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        
        logger.info(
            "Initialized LLM client (provider=%s, model=%s, timeout=%ss, max_retries=%s)",
            self.provider,
            self.model,
            self.timeout_s,
            self.max_retries,
        )
    
    def _init_anthropic(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import AsyncAnthropic
            
            api_key = self.config.get_api_key("anthropic")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            
            self.client = AsyncAnthropic(
                api_key=api_key,
                timeout=self.timeout_s
            )
        except ImportError:
            raise LLMProviderError(
                "anthropic package not installed. "
                "Run: pip install anthropic"
            )
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import AsyncOpenAI
            
            api_key = self.config.get_api_key("openai")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            
            self.client = AsyncOpenAI(
                api_key=api_key,
                timeout=self.timeout_s
            )
        except ImportError:
            raise LLMProviderError(
                "openai package not installed. "
                "Run: pip install openai"
            )
    
    def _init_stub(self):
        """Initialize stub client for testing."""
        self.client = None
        logger.info("Using stub LLM client (for testing)")
    
    async def generate_stream(
        self,
        *,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        stop: Optional[list[str]] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Stream LLM response token by token.
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            extra: Provider-specific extra parameters
            
        Yields:
            Generated text tokens
            
        Raises:
            LLMTimeoutError: Request timed out
            LLMRateLimitError: Rate limit exceeded
            LLMProviderError: Provider API error
        """
        extra = extra or {}
        attempts = 0
        
        while True:
            try:
                async for token in self._generate_once(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop,
                    extra=extra,
                ):
                    yield token
                return
            except asyncio.TimeoutError as exc:
                logger.warning(
                    "LLM request timed out (provider=%s, model=%s, timeout=%ss)",
                    self.provider,
                    self.model,
                    self.timeout_s,
                )
                raise LLMTimeoutError(
                    f"Request timed out after {self.timeout_s}s"
                ) from exc
            except Exception as exc:
                classification = self._classify_exception(exc)
                if classification in {"rate_limit", "retryable"} and attempts < self.max_retries:
                    attempts += 1
                    delay = self._retry_delay_seconds(attempts)
                    logger.warning(
                        "Retrying LLM request (attempt=%s/%s, delay=%.2fs, provider=%s)",
                        attempts,
                        self.max_retries,
                        delay,
                        self.provider,
                    )
                    await asyncio.sleep(delay)
                    continue
                
                safe_message = self._safe_error_message(exc)
                if classification == "rate_limit":
                    logger.error(
                        "Exhausted retries after rate limit (provider=%s): %s",
                        self.provider,
                        safe_message,
                    )
                    raise LLMRateLimitError(safe_message) from exc
                
                logger.error(
                    "LLM provider error (provider=%s, model=%s): %s",
                    self.provider,
                    self.model,
                    safe_message,
                    exc_info=True,
                )
                raise LLMProviderError(safe_message) from exc
    
    async def _generate_once(
        self,
        *,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        stop: Optional[list[str]],
        extra: Dict[str, Any],
    ) -> AsyncIterator[str]:
        if self.provider == "anthropic":
            async for token in self._stream_anthropic(
                prompt, system, temperature, max_tokens, stop, extra
            ):
                yield token
        elif self.provider == "openai":
            async for token in self._stream_openai(
                prompt, system, temperature, max_tokens, stop, extra
            ):
                yield token
        elif self.provider == "stub":
            async for token in self._stream_stub(prompt):
                yield token
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    async def _stream_anthropic(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        stop: Optional[list[str]],
        extra: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """Stream from Anthropic Claude."""
        messages = [{"role": "user", "content": prompt}]
        
        async with self.client.messages.stream(
            model=self.model,
            messages=messages,
            system=system or "",
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop or [],
            **extra
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def _stream_openai(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        stop: Optional[list[str]],
        extra: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """Stream from OpenAI GPT."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            stream=True,
            **extra
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def _stream_stub(self, prompt: str) -> AsyncIterator[str]:
        """Stub streaming for testing."""
        # Simulate streaming with realistic timing
        response = {
            "title": "Test Finding",
            "summary": "This is a test finding from the stub LLM.",
            "metrics": {"test_metric": 42.0},
            # Include a numeric unemployment value that should be cited
            # based on the synthetic deterministic data (0.10 → 10.0%).
            "analysis": "Detailed analysis would go here, including Qatar's unemployment rate of 0.10% compared to peers.",
            "recommendations": ["Test recommendation 1", "Test recommendation 2"],
            "confidence": 0.85,
            "citations": ["test_query_id"],
            "data_quality_notes": "Test data quality note"
        }
        
        response_text = json.dumps(response, indent=2)
        
        # Stream character by character with configurable delays for deterministic tests
        for char in response_text:
            yield char
            if self._stub_delay_s:
                await asyncio.sleep(self._stub_delay_s)
    
    async def generate(
        self,
        *,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        stop: Optional[list[str]] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate complete response (non-streaming).
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            stop: Stop sequences
            extra: Provider-specific parameters
            
        Returns:
            Complete generated text
        """
        response = ""
        async for token in self.generate_stream(
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            extra=extra
        ):
            response += token
        return response

    async def ainvoke(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        stop: Optional[list[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Compatibility wrapper aligning with LangChain-style ainvoke with metrics tracking.
        
        Args:
            prompt: User prompt
            system: System prompt
            temperature: Temperature setting
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            extra: Extra provider-specific parameters
            metadata: Metadata for metrics (agent, purpose, etc.)
            
        Returns:
            Generated text response
        """
        start_time = time.time()
        
        try:
            response = await self.generate(
                prompt=prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                extra=extra,
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
            # This is a fallback; ideally we'd get actual usage from the API
            input_text = prompt + (system or "")
            input_tokens = len(input_text) // 4
            output_tokens = len(response) // 4
            
            # Extract metadata
            agent_name = metadata.get("agent") if metadata else None
            purpose = metadata.get("purpose") if metadata else None
            
            # Record metrics
            record_llm_call(
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                agent_name=agent_name,
                purpose=purpose
            )
            
            return response
            
        except Exception as e:
            # Record failed call with minimal data
            latency_ms = (time.time() - start_time) * 1000
            record_llm_call(
                model=self.model,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                latency_ms=latency_ms,
                agent_name=metadata.get("agent") if metadata else "unknown",
                purpose="error"
            )
            raise
    
    async def list_models(self) -> Dict[str, Any]:
        """
        List available models for the provider.
        
        Returns:
            Dictionary with model information
        """
        return {
            "provider": self.provider,
            "current_model": self.model,
            "configured_models": self.config.configured_models(),
            "timeouts": {
                "seconds": self.timeout_s,
                "max_retries": self.max_retries,
            },
        }
    
    def _classify_exception(self, exc: Exception) -> str:
        """Return error classification for retry logic."""
        status_code = getattr(exc, "status_code", None)
        if not status_code:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
        if status_code == 429:
            return "rate_limit"
        if status_code and 500 <= int(status_code) < 600:
            return "retryable"
        
        message = str(exc).lower()
        if "rate limit" in message or "too many requests" in message:
            return "rate_limit"
        if any(term in message for term in ("timeout", "temporarily unavailable", "retry later")):
            return "retryable"
        return "fatal"
    
    def _retry_delay_seconds(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        base = min(2 ** attempt, 10)
        jitter = random.uniform(0.05, 0.30)
        return base + jitter
    
    @staticmethod
    def _safe_error_message(exc: Exception) -> str:
        """Return a sanitized error description."""
        status_code = getattr(exc, "status_code", None)
        if not status_code:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
        if status_code:
            return f"{exc.__class__.__name__} (status={status_code})"
        return exc.__class__.__name__


def get_client(*, provider: Optional[str] = None, **kwargs) -> LLMClient:
    """Factory helper for creating LLMClient instances."""
    return LLMClient(provider=provider, **kwargs)


__all__ = ["LLMClient", "get_client"]
