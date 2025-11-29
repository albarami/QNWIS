"""
Phase 4 Tests: DeepSeek vLLM Client

Tests:
- Configuration dataclass
- Response parsing with thinking blocks
- Mock inference mode
- Load balancing across instances
- Retry logic
- Statistics tracking
"""

import pytest
import asyncio
from typing import Dict, Any


class TestDataclasses:
    """Test DeepSeek data structures."""
    
    def test_thinking_block_creation(self):
        """ThinkingBlock should store content and timing."""
        from src.nsic.orchestration.deepseek_client import ThinkingBlock
        
        block = ThinkingBlock(
            content="Analyzing the problem...",
            duration_ms=150.0,
        )
        
        assert block.content == "Analyzing the problem..."
        assert block.duration_ms == 150.0
    
    def test_thinking_block_to_dict(self):
        """ThinkingBlock.to_dict() should return all fields."""
        from src.nsic.orchestration.deepseek_client import ThinkingBlock
        
        block = ThinkingBlock(content="thinking", duration_ms=100.0)
        d = block.to_dict()
        
        assert d["content"] == "thinking"
        assert d["duration_ms"] == 100.0
    
    def test_deepseek_response_creation(self):
        """DeepSeekResponse should store all fields."""
        from src.nsic.orchestration.deepseek_client import (
            DeepSeekResponse,
            ThinkingBlock,
        )
        
        thinking = ThinkingBlock("reasoning...", 50.0)
        response = DeepSeekResponse(
            content="Final answer",
            thinking=thinking,
            model="deepseek-r1",
            prompt_tokens=100,
            completion_tokens=50,
            total_time_ms=200.0,
            instance_id=1,
        )
        
        assert response.content == "Final answer"
        assert response.thinking is not None
        assert response.thinking.content == "reasoning..."
        assert response.model == "deepseek-r1"
        assert response.prompt_tokens == 100
        assert response.completion_tokens == 50
        assert response.instance_id == 1
    
    def test_deepseek_response_to_dict(self):
        """DeepSeekResponse.to_dict() should include thinking."""
        from src.nsic.orchestration.deepseek_client import DeepSeekResponse
        
        response = DeepSeekResponse(
            content="answer",
            thinking=None,
            model="model",
            total_time_ms=100.0,
        )
        
        d = response.to_dict()
        
        assert d["content"] == "answer"
        assert d["thinking"] is None
        assert d["model"] == "model"


class TestDeepSeekConfig:
    """Test configuration options."""
    
    def test_default_config(self):
        """Default config should have sensible values."""
        from src.nsic.orchestration.deepseek_client import DeepSeekConfig
        
        config = DeepSeekConfig()
        
        # Single instance on port 8001 (70B FP16 on GPUs 2,3,6,7)
        assert len(config.vllm_base_urls) == 1
        assert config.vllm_base_urls[0] == "http://localhost:8001"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.gpu_memory_utilization == 0.85
        assert config.swap_space_gb == 16
        assert config.max_model_len == 32768
    
    def test_custom_config(self):
        """Config should accept custom values."""
        from src.nsic.orchestration.deepseek_client import DeepSeekConfig
        
        config = DeepSeekConfig(
            vllm_base_urls=["http://localhost:9001"],
            max_tokens=8192,
            temperature=0.5,
        )
        
        assert len(config.vllm_base_urls) == 1
        assert config.max_tokens == 8192
        assert config.temperature == 0.5


class TestThinkingParsing:
    """Test <think>...</think> parsing."""
    
    def test_parse_with_thinking(self):
        """Should extract thinking block from response."""
        from src.nsic.orchestration.deepseek_client import DeepSeekClient, InferenceMode
        
        client = DeepSeekClient(mode=InferenceMode.MOCK)
        
        content = "<think>Let me analyze this step by step...</think>\nThe answer is 42."
        clean, thinking = client._parse_thinking(content)
        
        assert thinking == "Let me analyze this step by step..."
        assert clean == "The answer is 42."
    
    def test_parse_without_thinking(self):
        """Should handle response without thinking block."""
        from src.nsic.orchestration.deepseek_client import DeepSeekClient, InferenceMode
        
        client = DeepSeekClient(mode=InferenceMode.MOCK)
        
        content = "Simple answer without thinking."
        clean, thinking = client._parse_thinking(content)
        
        assert thinking is None
        assert clean == "Simple answer without thinking."
    
    def test_parse_multiline_thinking(self):
        """Should handle multiline thinking blocks."""
        from src.nsic.orchestration.deepseek_client import DeepSeekClient, InferenceMode
        
        client = DeepSeekClient(mode=InferenceMode.MOCK)
        
        content = """<think>
        First, I consider option A.
        Then, I evaluate option B.
        Finally, I decide on C.
        </think>
        
        My recommendation is option C."""
        
        clean, thinking = client._parse_thinking(content)
        
        assert "option A" in thinking
        assert "option B" in thinking
        assert "decide on C" in thinking  # The thinking block says "decide on C"
        assert "recommendation" in clean


class TestMockMode:
    """Test mock inference mode."""
    
    def test_mock_chat_sync(self):
        """Mock mode should return valid response synchronously."""
        from src.nsic.orchestration.deepseek_client import DeepSeekClient, InferenceMode
        
        client = DeepSeekClient(mode=InferenceMode.MOCK)
        
        messages = [
            {"role": "user", "content": "What is 2+2?"},
        ]
        
        response = client.chat(messages)
        
        assert response is not None
        assert response.content != ""
        assert response.model == "mock-deepseek"
        assert response.thinking is not None
    
    @pytest.mark.asyncio
    async def test_mock_chat_async(self):
        """Mock mode should work asynchronously."""
        from src.nsic.orchestration.deepseek_client import DeepSeekClient, InferenceMode
        
        client = DeepSeekClient(mode=InferenceMode.MOCK)
        
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Explain quantum computing."},
        ]
        
        response = await client.chat_async(messages)
        
        assert response is not None
        assert response.content != ""
        assert response.total_time_ms > 0


class TestLoadBalancing:
    """Test instance load balancing."""
    
    def test_round_robin(self):
        """Client should distribute requests across instances."""
        from src.nsic.orchestration.deepseek_client import DeepSeekClient, InferenceMode
        
        client = DeepSeekClient(mode=InferenceMode.MOCK)
        
        # Get sequence of instances
        instances = [client._get_next_instance() for _ in range(6)]
        
        # Single instance (port 8001) - all requests go to instance 0
        assert instances == [0, 0, 0, 0, 0, 0]
    
    def test_stats_tracking(self):
        """Client should track request statistics."""
        from src.nsic.orchestration.deepseek_client import DeepSeekClient, InferenceMode
        
        client = DeepSeekClient(mode=InferenceMode.MOCK)
        
        # Initial stats
        stats = client.get_stats()
        assert stats["total_requests"] == 0
        
        # After requests
        client.chat([{"role": "user", "content": "test1"}])
        client.chat([{"role": "user", "content": "test2"}])
        
        stats = client.get_stats()
        assert stats["total_requests"] == 2
        assert stats["total_tokens"] > 0


class TestParallelGeneration:
    """Test parallel scenario generation."""
    
    @pytest.mark.asyncio
    async def test_parallel_scenarios(self):
        """Should generate multiple scenarios in parallel."""
        from src.nsic.orchestration.deepseek_client import DeepSeekClient, InferenceMode
        
        client = DeepSeekClient(mode=InferenceMode.MOCK)
        
        prompts = [
            "Scenario 1: Oil price shock",
            "Scenario 2: Policy change",
            "Scenario 3: Market volatility",
        ]
        
        responses = await client.generate_scenarios_parallel(prompts)
        
        assert len(responses) == 3
        for resp in responses:
            assert resp is not None
            assert resp.content != ""


class TestHealthCheck:
    """Test health check functionality."""
    
    def test_health_check_mock_mode(self):
        """Health check should work in mock mode."""
        from src.nsic.orchestration.deepseek_client import DeepSeekClient, InferenceMode
        
        client = DeepSeekClient(mode=InferenceMode.MOCK)
        
        health = client.health_check()
        
        assert health["status"] == "healthy"
        assert health["mode"] == "mock"


class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_mock_client(self):
        """Factory should create mock client."""
        from src.nsic.orchestration.deepseek_client import create_deepseek_client
        
        client = create_deepseek_client(mode="mock")
        
        assert client is not None
        response = client.chat([{"role": "user", "content": "test"}])
        assert response.model == "mock-deepseek"
    
    def test_create_with_config(self):
        """Factory should accept config overrides."""
        from src.nsic.orchestration.deepseek_client import (
            create_deepseek_client,
            InferenceMode,
        )
        
        client = create_deepseek_client(
            mode="mock",
            max_tokens=2048,
            temperature=0.3,
        )
        
        assert client.config.max_tokens == 2048
        assert client.config.temperature == 0.3


class TestInferenceModeEnum:
    """Test inference mode enumeration."""
    
    def test_mode_values(self):
        """InferenceMode should have correct values."""
        from src.nsic.orchestration.deepseek_client import InferenceMode
        
        assert InferenceMode.VLLM.value == "vllm"
        assert InferenceMode.TRANSFORMERS.value == "transformers"
        assert InferenceMode.MOCK.value == "mock"
    
    def test_mode_from_string(self):
        """Should be able to create mode from string."""
        from src.nsic.orchestration.deepseek_client import InferenceMode
        
        mode = InferenceMode("mock")
        assert mode == InferenceMode.MOCK


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

