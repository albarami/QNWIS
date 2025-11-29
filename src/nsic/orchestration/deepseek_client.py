"""
NSIC DeepSeek Client for Local LLM Inference

Supports:
- vLLM OpenAI-compatible API (Linux, production)
- HuggingFace Transformers (Windows, development)

Model: DeepSeek-R1-Distill-Llama-70B
- Built-in <think>...</think> chain-of-thought
- Superior mathematical reasoning
- Tensor-parallel across GPUs 2-3, 6-7

vLLM Memory Settings:
- gpu-memory-utilization: 0.85
- swap-space: 16GB
- max-model-len: 32768
"""

import logging
import re
import time
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, AsyncIterator
from enum import Enum

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


class InferenceMode(Enum):
    """Inference mode for DeepSeek client."""
    VLLM = "vllm"  # vLLM OpenAI-compatible API
    TRANSFORMERS = "transformers"  # HuggingFace Transformers
    MOCK = "mock"  # Mock mode for testing


@dataclass
class ThinkingBlock:
    """Represents a <think>...</think> chain-of-thought block."""
    content: str
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "duration_ms": self.duration_ms,
        }


@dataclass
class DeepSeekResponse:
    """Response from DeepSeek model."""
    content: str
    thinking: Optional[ThinkingBlock] = None
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_time_ms: float = 0.0
    instance_id: int = 0  # Which vLLM instance handled this
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "thinking": self.thinking.to_dict() if self.thinking else None,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_time_ms": self.total_time_ms,
            "instance_id": self.instance_id,
        }


@dataclass
class DeepSeekConfig:
    """Configuration for DeepSeek client."""
    # DeepSeek endpoints
    # Instance 1: GPUs 2,3,6,7 on port 8001 (DEPLOYED - FULL 70B FP16)
    # Note: Single instance uses all 4 GPUs for maximum quality
    vllm_base_urls: List[str] = field(default_factory=lambda: [
        "http://localhost:8001",  # GPUs 2,3,6,7 - DEPLOYED (70B FP16)
    ])
    
    # Model settings
    model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    
    # Timeout and retry
    timeout_seconds: float = 300.0  # 5 minutes for long generations
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Memory settings (for vLLM startup reference)
    gpu_memory_utilization: float = 0.85
    swap_space_gb: int = 16
    max_model_len: int = 32768


class DeepSeekClient:
    """
    Client for DeepSeek-R1-Distill-70B inference.
    
    Features:
    - Load balancing across two vLLM instances
    - Automatic <think>...</think> parsing
    - Retry with fallback to secondary instance
    - Async and sync interfaces
    """
    
    # Pattern to extract thinking blocks
    THINKING_PATTERN = re.compile(
        r'<think>(.*?)</think>',
        re.DOTALL | re.IGNORECASE
    )
    
    def __init__(
        self,
        config: Optional[DeepSeekConfig] = None,
        mode: InferenceMode = InferenceMode.VLLM,
    ):
        """
        Initialize DeepSeek client.
        
        Args:
            config: Configuration options
            mode: Inference mode (vLLM, transformers, or mock)
        """
        self.config = config or DeepSeekConfig()
        self.mode = mode
        
        # Instance tracking for load balancing
        self._current_instance = 0
        self._instance_counts = [0] * len(self.config.vllm_base_urls)
        self._instance_errors = [0] * len(self.config.vllm_base_urls)
        
        # Stats
        self._total_requests = 0
        self._total_tokens = 0
        self._total_time_ms = 0.0
        
        logger.info(
            f"DeepSeekClient initialized: mode={mode.value}, "
            f"instances={len(self.config.vllm_base_urls)}"
        )
    
    def _get_next_instance(self) -> int:
        """Get next instance for load balancing (round-robin)."""
        instance = self._current_instance
        self._current_instance = (self._current_instance + 1) % len(self.config.vllm_base_urls)
        return instance
    
    def _parse_thinking(self, content: str) -> Tuple[str, Optional[str]]:
        """
        Parse and extract <think>...</think> block from response.
        
        Args:
            content: Raw response content
            
        Returns:
            Tuple of (clean_content, thinking_content)
        """
        match = self.THINKING_PATTERN.search(content)
        if match:
            thinking_content = match.group(1).strip()
            clean_content = self.THINKING_PATTERN.sub('', content).strip()
            return clean_content, thinking_content
        return content, None
    
    async def _call_vllm_instance(
        self,
        instance_id: int,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> DeepSeekResponse:
        """Make async call to specific vLLM instance."""
        base_url = self.config.vllm_base_urls[instance_id]
        url = f"{base_url}/v1/chat/completions"
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
        }
        
        start_time = time.time()
        
        if HTTPX_AVAILABLE:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        elif AIOHTTP_AVAILABLE:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
        else:
            raise ImportError("Either httpx or aiohttp is required for async calls")
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Extract response
        choice = data["choices"][0]
        raw_content = choice["message"]["content"]
        
        # Parse thinking block
        clean_content, thinking_content = self._parse_thinking(raw_content)
        
        thinking = None
        if thinking_content:
            thinking = ThinkingBlock(
                content=thinking_content,
                duration_ms=elapsed_ms * 0.3,  # Estimate thinking time
            )
        
        # Usage stats
        usage = data.get("usage", {})
        
        return DeepSeekResponse(
            content=clean_content,
            thinking=thinking,
            model=data.get("model", self.config.model_name),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_time_ms=elapsed_ms,
            instance_id=instance_id,
        )
    
    def _mock_response(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> DeepSeekResponse:
        """Generate mock response for testing."""
        user_message = messages[-1]["content"] if messages else "test"
        
        # Simulate thinking
        thinking_content = f"Analyzing the request: '{user_message[:100]}...'\n"
        thinking_content += "Considering multiple perspectives...\n"
        thinking_content += "Formulating comprehensive response..."
        
        response_content = f"This is a mock response to: {user_message[:50]}..."
        
        return DeepSeekResponse(
            content=response_content,
            thinking=ThinkingBlock(content=thinking_content, duration_ms=10.0),
            model="mock-deepseek",
            prompt_tokens=len(user_message.split()),
            completion_tokens=20,
            total_time_ms=50.0,
            instance_id=0,
        )
    
    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> DeepSeekResponse:
        """
        Async chat completion with load balancing and retry.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (max_tokens, temperature, etc.)
            
        Returns:
            DeepSeekResponse with content and optional thinking block
        """
        if self.mode == InferenceMode.MOCK:
            return self._mock_response(messages, **kwargs)
        
        last_error = None
        instance_id = self._get_next_instance()
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self._call_vllm_instance(
                    instance_id,
                    messages,
                    **kwargs,
                )
                
                # Update stats
                self._total_requests += 1
                self._total_tokens += response.prompt_tokens + response.completion_tokens
                self._total_time_ms += response.total_time_ms
                self._instance_counts[instance_id] += 1
                
                return response
                
            except Exception as e:
                last_error = e
                self._instance_errors[instance_id] += 1
                logger.warning(
                    f"DeepSeek instance {instance_id} failed (attempt {attempt + 1}): {e}"
                )
                
                # Try different instance on retry
                instance_id = (instance_id + 1) % len(self.config.vllm_base_urls)
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)
        
        raise RuntimeError(
            f"All DeepSeek instances failed after {self.config.max_retries} attempts: {last_error}"
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> DeepSeekResponse:
        """
        Synchronous chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters
            
        Returns:
            DeepSeekResponse
        """
        if self.mode == InferenceMode.MOCK:
            response = self._mock_response(messages, **kwargs)
            # Update stats for mock mode too
            self._total_requests += 1
            self._total_tokens += response.prompt_tokens + response.completion_tokens
            self._total_time_ms += response.total_time_ms
            return response
        
        # Run async in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.chat_async(messages, **kwargs))
    
    async def generate_scenarios_parallel(
        self,
        prompts: List[str],
        system_prompt: str = "You are an expert scenario analyst.",
        max_concurrent: int = 4,
    ) -> List[DeepSeekResponse]:
        """
        Generate multiple scenarios in parallel using both instances.
        
        Args:
            prompts: List of scenario prompts
            system_prompt: System prompt for all scenarios
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of DeepSeekResponse objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_prompt(prompt: str) -> DeepSeekResponse:
            async with semaphore:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
                return await self.chat_async(messages)
        
        tasks = [process_prompt(prompt) for prompt in prompts]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        results = []
        for resp in responses:
            if isinstance(resp, Exception):
                logger.error(f"Parallel scenario generation failed: {resp}")
                results.append(None)
            else:
                results.append(resp)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        avg_time = self._total_time_ms / self._total_requests if self._total_requests > 0 else 0
        
        return {
            "mode": self.mode.value,
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "total_time_ms": self._total_time_ms,
            "avg_time_per_request_ms": avg_time,
            "instance_counts": self._instance_counts,
            "instance_errors": self._instance_errors,
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of vLLM instances."""
        if self.mode == InferenceMode.MOCK:
            return {"status": "healthy", "mode": "mock"}
        
        results = {"status": "unknown", "instances": []}
        
        for i, url in enumerate(self.config.vllm_base_urls):
            instance_status = {
                "id": i,
                "url": url,
                "healthy": False,
                "error": None,
            }
            
            try:
                import requests
                response = requests.get(
                    f"{url}/health",
                    timeout=5.0,
                )
                instance_status["healthy"] = response.status_code == 200
            except Exception as e:
                instance_status["error"] = str(e)
            
            results["instances"].append(instance_status)
        
        # Overall status
        healthy_count = sum(1 for inst in results["instances"] if inst["healthy"])
        if healthy_count == len(self.config.vllm_base_urls):
            results["status"] = "healthy"
        elif healthy_count > 0:
            results["status"] = "degraded"
        else:
            results["status"] = "unhealthy"
        
        return results


def create_deepseek_client(
    mode: str = "vllm",
    **config_kwargs,
) -> DeepSeekClient:
    """
    Factory function to create DeepSeek client.
    
    Args:
        mode: "vllm", "transformers", or "mock"
        **config_kwargs: Configuration overrides
        
    Returns:
        DeepSeekClient instance
    """
    mode_enum = InferenceMode(mode)
    config = DeepSeekConfig(**config_kwargs) if config_kwargs else None
    return DeepSeekClient(config=config, mode=mode_enum)


# vLLM startup commands for reference
VLLM_STARTUP_COMMANDS = """
# Instance 1: GPUs 2-3 (port 8001)
CUDA_VISIBLE_DEVICES=2,3 python -m vllm.entrypoints.openai.api_server \\
    --model deepseek-ai/DeepSeek-R1-Distill-Llama-70B \\
    --tensor-parallel-size 2 \\
    --port 8001 \\
    --gpu-memory-utilization 0.85 \\
    --swap-space 16 \\
    --max-model-len 32768

# Instance 2: GPUs 6-7 (port 8002)
CUDA_VISIBLE_DEVICES=6,7 python -m vllm.entrypoints.openai.api_server \\
    --model deepseek-ai/DeepSeek-R1-Distill-Llama-70B \\
    --tensor-parallel-size 2 \\
    --port 8002 \\
    --gpu-memory-utilization 0.85 \\
    --swap-space 16 \\
    --max-model-len 32768
"""

