"""
Tests for hybrid model routing.

Tests the ModelRouter class that routes LLM requests to optimal models
based on task type (GPT-4o for fast/deterministic, GPT-5 for reasoning).
"""

import os
import pytest
from unittest.mock import patch

from src.qnwis.llm.model_router import (
    ModelRouter,
    TaskType,
    ModelConfig,
    get_router,
    reset_router,
    get_model_for_task,
)


@pytest.fixture(autouse=True)
def reset_router_fixture():
    """Reset the global router before each test."""
    reset_router()
    yield
    reset_router()


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "QNWIS_PRIMARY_MODEL": "gpt-5-chat",
        "QNWIS_PRIMARY_API_VERSION": "2024-12-01-preview",
        "QNWIS_PRIMARY_ENDPOINT": "https://test-endpoint.openai.azure.com",
        "QNWIS_PRIMARY_API_KEY": "test-primary-key",
        "QNWIS_FAST_MODEL": "gpt-4o",
        "QNWIS_FAST_API_VERSION": "2024-08-01-preview",
        "QNWIS_FAST_ENDPOINT": "https://test-endpoint.openai.azure.com",
        "QNWIS_FAST_API_KEY": "test-fast-key",
        "QNWIS_USE_HYBRID_ROUTING": "true",
        "AZURE_OPENAI_ENDPOINT": "https://fallback-endpoint.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "fallback-key",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


class TestModelRouterInitialization:
    """Tests for router initialization."""
    
    def test_router_initialization_with_defaults(self, mock_env_vars):
        """Test router initializes with correct models from environment."""
        router = ModelRouter()
        
        assert router.primary_config.deployment == "gpt-5-chat"
        assert router.fast_config.deployment == "gpt-4o"
        assert router.hybrid_enabled is True
    
    def test_router_primary_model_temperature(self, mock_env_vars):
        """Primary model should have temperature 0.3 for balanced reasoning."""
        router = ModelRouter()
        assert router.primary_config.temperature == 0.3
    
    def test_router_fast_model_temperature(self, mock_env_vars):
        """Fast model should have temperature 0.1 for deterministic output."""
        router = ModelRouter()
        assert router.fast_config.temperature == 0.1
    
    def test_router_api_versions(self, mock_env_vars):
        """Test API versions are set correctly."""
        router = ModelRouter()
        
        assert router.primary_config.api_version == "2024-12-01-preview"
        assert router.fast_config.api_version == "2024-08-01-preview"


class TestTaskToModelMapping:
    """Tests for task-to-model routing logic."""
    
    def test_extraction_uses_fast_model(self, mock_env_vars):
        """Extraction tasks should use GPT-4o (fast)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.EXTRACTION)
        
        assert config.deployment == "gpt-4o"
        assert config.temperature == 0.1
    
    def test_verification_uses_fast_model(self, mock_env_vars):
        """Verification tasks should use GPT-4o (fast)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.VERIFICATION)
        
        assert config.deployment == "gpt-4o"
    
    def test_classification_uses_fast_model(self, mock_env_vars):
        """Classification tasks should use GPT-4o (fast)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.CLASSIFICATION)
        
        assert config.deployment == "gpt-4o"
    
    def test_citation_check_uses_fast_model(self, mock_env_vars):
        """Citation check tasks should use GPT-4o (fast)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.CITATION_CHECK)
        
        assert config.deployment == "gpt-4o"
    
    def test_fact_check_uses_fast_model(self, mock_env_vars):
        """Fact check tasks should use GPT-4o (fast)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.FACT_CHECK)
        
        assert config.deployment == "gpt-4o"
    
    def test_debate_uses_primary_model(self, mock_env_vars):
        """Debate tasks should use GPT-5 (primary)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.DEBATE)
        
        assert config.deployment == "gpt-5-chat"
        assert config.temperature == 0.3
    
    def test_synthesis_uses_primary_model(self, mock_env_vars):
        """Final synthesis tasks should use GPT-5 (primary)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.FINAL_SYNTHESIS)
        
        assert config.deployment == "gpt-5-chat"
    
    def test_scenario_generation_uses_primary_model(self, mock_env_vars):
        """Scenario generation should use GPT-5 (primary)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.SCENARIO_GENERATION)
        
        assert config.deployment == "gpt-5-chat"
    
    def test_agent_analysis_uses_primary_model(self, mock_env_vars):
        """Agent analysis should use GPT-5 (primary)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.AGENT_ANALYSIS)
        
        assert config.deployment == "gpt-5-chat"
    
    def test_cross_domain_uses_primary_model(self, mock_env_vars):
        """Cross-domain reasoning should use GPT-5 (primary)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.CROSS_DOMAIN)
        
        assert config.deployment == "gpt-5-chat"
    
    def test_meta_synthesis_uses_primary_model(self, mock_env_vars):
        """Meta-synthesis should use GPT-5 (primary)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.META_SYNTHESIS)
        
        assert config.deployment == "gpt-5-chat"
    
    def test_feasibility_gate_uses_primary_model(self, mock_env_vars):
        """Feasibility gate should use GPT-5 (primary)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.FEASIBILITY_GATE)
        
        assert config.deployment == "gpt-5-chat"
    
    def test_general_uses_primary_model(self, mock_env_vars):
        """General/unknown tasks should use GPT-5 (primary)."""
        router = ModelRouter()
        config = router.get_model_config(TaskType.GENERAL)
        
        assert config.deployment == "gpt-5-chat"


class TestStringTaskRouting:
    """Tests for routing by string task name."""
    
    def test_string_extraction_routing(self, mock_env_vars):
        """Test routing 'extraction' string to GPT-4o."""
        config = get_model_for_task("extraction")
        assert config.deployment == "gpt-4o"
    
    def test_string_debate_routing(self, mock_env_vars):
        """Test routing 'debate' string to GPT-5."""
        config = get_model_for_task("debate")
        assert config.deployment == "gpt-5-chat"
    
    def test_string_verification_routing(self, mock_env_vars):
        """Test routing 'verification' string to GPT-4o."""
        config = get_model_for_task("verification")
        assert config.deployment == "gpt-4o"
    
    def test_string_final_synthesis_routing(self, mock_env_vars):
        """Test routing 'final_synthesis' string to GPT-5."""
        config = get_model_for_task("final_synthesis")
        assert config.deployment == "gpt-5-chat"
    
    def test_unknown_task_uses_primary(self, mock_env_vars):
        """Unknown tasks should default to primary model (GPT-5)."""
        router = ModelRouter()
        config = router.get_model_for_task("unknown_task_xyz")
        
        assert config.deployment == "gpt-5-chat"
    
    def test_case_insensitive_routing(self, mock_env_vars):
        """Task names should be case-insensitive."""
        router = ModelRouter()
        
        config_lower = router.get_model_for_task("extraction")
        config_upper = router.get_model_for_task("EXTRACTION")
        config_mixed = router.get_model_for_task("ExTrAcTiOn")
        
        assert config_lower.deployment == config_upper.deployment == config_mixed.deployment == "gpt-4o"


class TestHybridRoutingToggle:
    """Tests for enabling/disabling hybrid routing."""
    
    def test_hybrid_routing_disabled_uses_primary(self, mock_env_vars):
        """When hybrid routing disabled, all tasks use primary model."""
        with patch.dict(os.environ, {"QNWIS_USE_HYBRID_ROUTING": "false"}):
            reset_router()
            router = ModelRouter()
            
            # Even fast tasks should use primary when hybrid disabled
            config = router.get_model_config(TaskType.EXTRACTION)
            assert config.deployment == "gpt-5-chat"
    
    def test_hybrid_routing_enabled_by_default(self, mock_env_vars):
        """Hybrid routing should be enabled by default."""
        router = ModelRouter()
        assert router.hybrid_enabled is True


class TestUsageTracking:
    """Tests for usage statistics tracking."""
    
    def test_track_usage_primary(self, mock_env_vars):
        """Test tracking usage for primary model."""
        router = ModelRouter()
        
        router.track_usage("primary", 100)
        router.track_usage("primary", 200)
        
        report = router.get_usage_report()
        assert report["primary_model"]["calls"] == 2
        assert report["primary_model"]["tokens"] == 300
    
    def test_track_usage_fast(self, mock_env_vars):
        """Test tracking usage for fast model."""
        router = ModelRouter()
        
        router.track_usage("fast", 50)
        
        report = router.get_usage_report()
        assert report["fast_model"]["calls"] == 1
        assert report["fast_model"]["tokens"] == 50
    
    def test_reset_usage_stats(self, mock_env_vars):
        """Test resetting usage statistics."""
        router = ModelRouter()
        
        router.track_usage("primary", 100)
        router.track_usage("fast", 50)
        router.reset_usage_stats()
        
        report = router.get_usage_report()
        assert report["primary_model"]["calls"] == 0
        assert report["fast_model"]["tokens"] == 0
    
    def test_usage_report_includes_model_names(self, mock_env_vars):
        """Usage report should include model deployment names."""
        router = ModelRouter()
        report = router.get_usage_report()
        
        assert report["primary_model"]["name"] == "gpt-5-chat"
        assert report["fast_model"]["name"] == "gpt-4o"


class TestGlobalRouterSingleton:
    """Tests for global router singleton pattern."""
    
    def test_get_router_returns_same_instance(self, mock_env_vars):
        """get_router() should return the same instance."""
        router1 = get_router()
        router2 = get_router()
        
        assert router1 is router2
    
    def test_reset_router_clears_instance(self, mock_env_vars):
        """reset_router() should clear the global instance."""
        router1 = get_router()
        reset_router()
        router2 = get_router()
        
        assert router1 is not router2


class TestModelConfigDataclass:
    """Tests for ModelConfig dataclass."""
    
    def test_model_config_defaults(self):
        """Test ModelConfig default values."""
        config = ModelConfig(
            deployment="test-model",
            api_version="2024-01-01",
            endpoint="https://test.openai.azure.com",
            api_key="test-key"
        )
        
        assert config.system_role == "system"
        assert config.max_tokens == 4000
        assert config.temperature == 0.3
    
    def test_model_config_custom_values(self):
        """Test ModelConfig with custom values."""
        config = ModelConfig(
            deployment="test-model",
            api_version="2024-01-01",
            endpoint="https://test.openai.azure.com",
            api_key="test-key",
            system_role="developer",
            max_tokens=8000,
            temperature=0.5
        )
        
        assert config.system_role == "developer"
        assert config.max_tokens == 8000
        assert config.temperature == 0.5


class TestGetModelKeyForTask:
    """Tests for get_model_key_for_task method."""
    
    def test_get_model_key_for_fast_task(self, mock_env_vars):
        """Fast tasks should return 'fast' key."""
        router = ModelRouter()
        
        assert router.get_model_key_for_task("extraction") == "fast"
        assert router.get_model_key_for_task("verification") == "fast"
    
    def test_get_model_key_for_primary_task(self, mock_env_vars):
        """Primary tasks should return 'primary' key."""
        router = ModelRouter()
        
        assert router.get_model_key_for_task("debate") == "primary"
        assert router.get_model_key_for_task("final_synthesis") == "primary"
    
    def test_get_model_key_for_unknown_task(self, mock_env_vars):
        """Unknown tasks should return 'primary' key."""
        router = ModelRouter()
        
        assert router.get_model_key_for_task("unknown_xyz") == "primary"

