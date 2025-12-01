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
    # DeepSeek endpoints - 8 ExLlamaV2 INSTANCES (one per GPU)
    # GPU 0 -> Port 8001, GPU 1 -> Port 8002, etc.
    # 24 scenarios ÷ 8 instances = 3 scenarios each
    vllm_base_urls: List[str] = field(default_factory=lambda: [
        "http://localhost:8001",  # Instance 1: GPU 0
        "http://localhost:8002",  # Instance 2: GPU 1
        "http://localhost:8003",  # Instance 3: GPU 2
        "http://localhost:8004",  # Instance 4: GPU 3
        "http://localhost:8005",  # Instance 5: GPU 4
        "http://localhost:8006",  # Instance 6: GPU 5
        "http://localhost:8007",  # Instance 7: GPU 6
        "http://localhost:8008",  # Instance 8: GPU 7
    ])
    
    # Model settings
    model_name: str = "deepseek-exllama"  # ExLlamaV2 4-bit quantized model
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    
    # FIX 1 (UPDATED): Stronger repetition penalty to prevent garbage output ({{{, ***, \\\)
    # Increased from 1.15 to 1.25 after observing continued garbage in logs
    repetition_penalty: float = 1.25
    frequency_penalty: float = 0.4   # Penalize repeated tokens in output
    presence_penalty: float = 0.2    # Encourage vocabulary diversity
    stop_sequences: List[str] = field(default_factory=lambda: [
        "###", 
        "---END---", 
        "```\n\n\n",
        "\n\n\n\n\n",   # Stop on 5+ consecutive newlines
        "****",         # Stop on repeated asterisks  
        "{{{{",         # Stop on repeated braces
    ])
    
    # Timeout and retry
    timeout_seconds: float = 7200.0  # 2 hours for full E2E runs
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
    
    def _get_healthy_instance(self) -> int:
        """
        FIX 6: Get a healthy instance, avoiding known-bad ones.
        
        Tracks consecutive failures per GPU instance and skips
        instances that have failed too many times recently.
        
        Returns:
            Instance ID of a healthy (or least-bad) instance
        """
        MAX_CONSECUTIVE_FAILURES = 3
        
        # Try to find an instance with low error count
        for _ in range(len(self.config.vllm_base_urls)):
            instance_id = self._get_next_instance()
            
            if self._instance_errors[instance_id] < MAX_CONSECUTIVE_FAILURES:
                return instance_id
            else:
                logger.warning(
                    f"Skipping GPU instance {instance_id} with "
                    f"{self._instance_errors[instance_id]} consecutive failures"
                )
        
        # All instances have high errors - reset and try anyway
        logger.warning("All GPU instances have high error counts, resetting counters")
        self._instance_errors = [0] * len(self.config.vllm_base_urls)
        return self._get_next_instance()
    
    def _record_instance_success(self, instance_id: int) -> None:
        """Record successful request - reset error count for instance."""
        self._instance_errors[instance_id] = 0
    
    def _record_instance_failure(self, instance_id: int) -> None:
        """Record failed request - increment error count for instance."""
        self._instance_errors[instance_id] += 1
        logger.debug(
            f"GPU instance {instance_id} failure count: {self._instance_errors[instance_id]}"
        )
    
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
    
    def _validate_output(self, content: str) -> bool:
        """
        FIX 2: Validate output quality - reject degenerate/garbage output.
        
        Detects patterns like:
        - Repeated characters: {{{{, ****, \\\\\\
        - Empty or too-short responses
        - Excessive symbol repetition
        
        Args:
            content: Raw response content
            
        Returns:
            True if output is valid, False if garbage detected
        """
        if not content or len(content) < 100:
            logger.warning("Output too short: %d chars", len(content) if content else 0)
            return False
        
        # Detect repeated characters (15+)
        if re.search(r'(.)\1{15,}', content):
            logger.warning("Repeated character pattern detected")
            return False
        
        # Detect repeated symbols - garbage patterns from DeepSeek (tightened thresholds)
        brace_count = content.count('{')
        asterisk_count = content.count('*')
        backslash_count = content.count('\\')
        
        if brace_count > 20 or asterisk_count > 40 or backslash_count > 20:
            logger.warning("Excessive symbol repetition: { x%d, * x%d, \\ x%d",
                          brace_count, asterisk_count, backslash_count)
            return False
        
        # Additional: Check ratio of symbols to content (garbage has high ratio)
        total_symbols = brace_count + asterisk_count + backslash_count
        if len(content) > 0 and total_symbols / len(content) > 0.05:  # >5% symbols is garbage
            logger.warning("High symbol ratio: %d symbols in %d chars (%.1f%%)",
                          total_symbols, len(content), 100 * total_symbols / len(content))
            return False
        
        # Detect repeated short patterns (e.g., "| { | { | {")
        if re.search(r'(\|\s*\{\s*){5,}', content):
            logger.warning("Repeated pipe-brace pattern detected")
            return False
        
        # Must have reasonable word count
        words = content.split()
        if len(words) < 30:
            logger.warning("Output has too few words: %d", len(words))
            return False
        
        return True
    
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
            # FIX 1 (UPDATED): Stronger repetition control to prevent garbage output
            "repetition_penalty": kwargs.get("repetition_penalty", self.config.repetition_penalty),
            "frequency_penalty": kwargs.get("frequency_penalty", self.config.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.config.presence_penalty),
            "stop": kwargs.get("stop", self.config.stop_sequences),
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
        
        # FIX 2: Validate output quality - reject garbage
        if not self._validate_output(raw_content):
            raise ValueError(f"Degenerate output detected: {raw_content[:100]}...")
        
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
        instance_id: int = None,
        **kwargs,
    ) -> DeepSeekResponse:
        """
        Async chat completion with load balancing and retry.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            instance_id: Specific instance to use (0=port 8001, 1=port 8002). None=auto-select.
            **kwargs: Additional parameters (max_tokens, temperature, etc.)
            
        Returns:
            DeepSeekResponse with content and optional thinking block
        """
        if self.mode == InferenceMode.MOCK:
            return self._mock_response(messages, **kwargs)
        
        last_error = None
        # FIX 6: Use healthy instance selection instead of simple round-robin
        if instance_id is None:
            instance_id = self._get_healthy_instance()
        elif instance_id >= len(self.config.vllm_base_urls):
            logger.warning(f"Instance {instance_id} doesn't exist, using healthy instance")
            instance_id = self._get_healthy_instance()
        
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
                
                # FIX 6: Record success - reset error count for this instance
                self._record_instance_success(instance_id)
                
                return response
                
            except Exception as e:
                last_error = e
                # FIX 6: Record failure with helper method
                self._record_instance_failure(instance_id)
                logger.warning(
                    f"DeepSeek instance {instance_id} failed (attempt {attempt + 1}): {e}"
                )
                
                # FIX 6: Try to get a healthy instance instead of just incrementing
                instance_id = self._get_healthy_instance()
                
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
                    timeout=7200.0,  # 2 hours
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

