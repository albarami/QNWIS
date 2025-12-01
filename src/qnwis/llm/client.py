"""
Unified LLM client for QNWIS.

Supports Anthropic Claude, OpenAI GPT, and Azure OpenAI with streaming,
bounded timeouts, jittered retries, and safe logging.

CRITICAL: Stub mode is DELETED. System requires real LLM.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import AsyncIterator, Optional, Dict, Any

import httpx

from src.qnwis.llm.config import LLMConfig, get_llm_config
from src.qnwis.llm.model_router import get_router, ModelConfig
from src.qnwis.llm.exceptions import (
    LLMTimeoutError,
    LLMRateLimitError,
    LLMProviderError,
)
from src.qnwis.observability.metrics import record_llm_call

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client supporting Anthropic, OpenAI, and Azure OpenAI.
    
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
            provider: "anthropic", "openai", or "azure" (default from config)
            model: Model name (default from config)
            timeout_s: Timeout in seconds
            config: LLMConfig instance (default: load from env)
        """
        self.config = config or get_llm_config()
        self.provider = (provider or self.config.provider).lower()
        self.model = model or self.config.get_model(self.provider)
        configured_timeout = self.config.timeout_seconds
        effective_timeout = timeout_s if timeout_s is not None else configured_timeout
        self.timeout_s = 7200  # 2 hours for full E2E runs
        self.max_retries = self.config.max_retries
        
        # Initialize provider client
        if self.provider == "anthropic":
            self._init_anthropic()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "azure":
            self._init_azure_openai()
        else:
            raise ValueError(
                f"Unknown provider: {self.provider}. "
                "Use 'anthropic', 'openai', or 'azure'."
            )
        
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
    
    def _init_azure_openai(self):
        """Initialize Azure OpenAI client."""
        try:
            from openai import AsyncAzureOpenAI

            api_key = self.config.get_api_key("azure")
            if not api_key:
                raise ValueError("AZURE_OPENAI_API_KEY not set")

            endpoint = self.config.azure_endpoint
            if not endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT not set")

            api_version = self.config.azure_api_version

            self.client = AsyncAzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint,
                timeout=self.timeout_s
            )

            logger.info(
                "Azure OpenAI client initialized (endpoint=%s, api_version=%s, model=%s)",
                endpoint[:50] + "..." if len(endpoint) > 50 else endpoint,
                api_version,
                self.model
            )
        except ImportError:
            raise LLMProviderError(
                "openai package not installed. "
                "Run: pip install openai"
            )

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
                
                # Check if this is a content filter error (Azure false positive)
                error_lower = str(exc).lower()
                if "content_filter" in error_lower or "400" in str(exc) or "jailbreak" in error_lower:
                    logger.warning(
                        "⚠️ Content filter triggered (provider=%s) - may be false positive for policy analysis",
                        self.provider
                    )
                    # Try to extract which filter category was triggered
                    try:
                        if hasattr(exc, 'response') and exc.response:
                            error_body = exc.response.json() if hasattr(exc.response, 'json') else {}
                            filter_result = error_body.get('error', {}).get('innererror', {}).get('content_filter_result', {})
                            for category, result in filter_result.items():
                                if isinstance(result, dict) and result.get('filtered'):
                                    logger.error(f"Content filter category triggered: {category}")
                    except Exception:
                        pass
                
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
        elif self.provider == "azure":
            async for token in self._stream_azure(
                prompt, system, temperature, max_tokens, stop, extra
            ):
                yield token
        else:
            raise ValueError(
                f"Unknown provider: {self.provider}. "
                "Use 'anthropic', 'openai', or 'azure'."
            )
    
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
    
    async def _stream_azure(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_tokens: int,
        stop: Optional[list[str]],
        extra: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """
        Stream from Azure OpenAI.
        
        Uses the same API as OpenAI but with Azure-specific endpoint.
        The model parameter is the Azure deployment name (e.g., 'gpt-5.1-chat').
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,  # This is the deployment name in Azure
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                stream=True,
                **extra
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            # Log Azure-specific error details
            logger.error(
                "Azure OpenAI streaming error (deployment=%s): %s",
                self.model,
                str(e)
            )
            raise
    
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
    
    async def generate_with_routing(
        self,
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
        Generate response using optimal model for the task type.
        
        Uses ModelRouter to select between:
        - GPT-4o (fast): extraction, verification, classification tasks
        - GPT-5 (primary): debate, synthesis, scenario, analysis tasks
        
        Args:
            prompt: The user prompt
            task_type: Type of task (extraction, debate, synthesis, etc.)
            system_prompt: Optional system prompt
            max_tokens: Max tokens (default from model config)
            temperature: Temperature (default from model config based on task)
            timeout: Request timeout in seconds
            metadata: Optional metadata for metrics
            
        Returns:
            Generated response string
        """
        start_time = time.time()
        
        # Get optimal model configuration
        router = get_router()
        config = router.get_model_for_task(task_type)
        model_key = router.get_model_key_for_task(task_type)
        
        # Use config defaults if not specified
        effective_temp = temperature if temperature is not None else config.temperature
        effective_max_tokens = max_tokens if max_tokens is not None else config.max_tokens
        
        # Build request
        endpoint = config.endpoint.rstrip("/")
        url = f"{endpoint}/openai/deployments/{config.deployment}/chat/completions?api-version={config.api_version}"
        
        messages = []
        if system_prompt:
            messages.append({"role": config.system_role, "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "messages": messages,
            "max_tokens": effective_max_tokens,
            "temperature": effective_temp,
        }
        
        headers = {
            "Content-Type": "application/json",
            "api-key": config.api_key,
        }
        
        logger.debug(
            "generate_with_routing: task=%s, model=%s, temp=%.2f",
            task_type, config.deployment, effective_temp
        )
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 429:
                    raise LLMRateLimitError(f"Rate limit exceeded for {config.deployment}")
                
                if response.status_code != 200:
                    raise LLMProviderError(f"HTTP {response.status_code}: {response.text[:500]}")
                
                data = response.json()
                
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("Empty choices in response")
                
                content = choices[0].get("message", {}).get("content", "")
                
                if not content or not content.strip():
                    raise LLMProviderError("Empty content in response")
                
                # Track usage
                latency_ms = (time.time() - start_time) * 1000
                usage = data.get("usage", {})
                total_tokens = usage.get("total_tokens", len(content) // 4)
                router.track_usage(model_key, total_tokens)
                
                # Record metrics
                record_llm_call(
                    model=config.deployment,
                    input_tokens=usage.get("prompt_tokens", len(prompt) // 4),
                    output_tokens=usage.get("completion_tokens", len(content) // 4),
                    latency_ms=latency_ms,
                    agent_name=metadata.get("agent") if metadata else task_type,
                    purpose=metadata.get("purpose") if metadata else task_type,
                )
                
                logger.debug(
                    "generate_with_routing complete: task=%s, model=%s, tokens=%d, latency=%.0fms",
                    task_type, config.deployment, total_tokens, latency_ms
                )
                
                return content
                
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Request timed out after {timeout}s") from exc
        except LLMRateLimitError:
            raise
        except LLMProviderError:
            raise
        except Exception as exc:
            logger.error(
                "generate_with_routing error: task=%s, model=%s, error=%s",
                task_type, config.deployment, str(exc)
            )
            raise LLMProviderError(f"Request failed: {exc}") from exc

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
        if any(term in message for term in ("timeout", "temporarily unavailable", "retry later", "overloaded", "overloaded_error")):
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
