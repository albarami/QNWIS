"""
QNWIS Hybrid Model Router
=========================

Routes LLM requests to the optimal model based on task type.
Based on comprehensive evaluation results from 2025-11-27.

Model Assignment:
- GPT-4o: Fast/deterministic tasks (extraction, verification, classification)
- GPT-5: Reasoning tasks (analysis, debate, synthesis, scenarios)

Evaluation Results Summary:
- GPT-5: 137.21 (WINNER - best for reasoning)
- GPT-4o: 131.52 (best accuracy: 100%, fastest response times)
- GPT-5.1: 126.52 (EXCLUDED - reliability issues, failed 2/16 tests)
"""

import os
import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task types for model routing."""
    
    # GPT-4o tasks (fast, deterministic)
    EXTRACTION = "extraction"
    VERIFICATION = "verification"
    CLASSIFICATION = "classification"
    CITATION_CHECK = "citation_check"
    FACT_CHECK = "fact_check"
    
    # GPT-5 tasks (reasoning, analysis)
    FEASIBILITY_GATE = "feasibility_gate"
    SCENARIO_GENERATION = "scenario_generation"
    AGENT_ANALYSIS = "agent_analysis"
    DEBATE = "debate"
    CROSS_DOMAIN = "cross_domain"
    META_SYNTHESIS = "meta_synthesis"
    FINAL_SYNTHESIS = "final_synthesis"
    
    # Default
    GENERAL = "general"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    deployment: str
    api_version: str
    endpoint: str
    api_key: str
    system_role: str = "system"
    max_tokens: int = 4000
    temperature: float = 0.3


class ModelRouter:
    """
    Routes requests to the optimal model based on task type.
    
    Based on comprehensive evaluation (2025-11-27):
    - GPT-5: Best overall (137.21), excels at reasoning tasks
    - GPT-4o: Best accuracy (100%), fastest, best for deterministic tasks
    
    Usage:
        router = ModelRouter()
        config = router.get_model_config(TaskType.DEBATE)
        # Use config to make API call
    """
    
    # Task to model mapping based on evaluation results
    TASK_MODEL_MAP = {
        # Fast model (GPT-4o) - Speed and accuracy critical
        TaskType.EXTRACTION: "fast",
        TaskType.VERIFICATION: "fast",
        TaskType.CLASSIFICATION: "fast",
        TaskType.CITATION_CHECK: "fast",
        TaskType.FACT_CHECK: "fast",
        
        # Primary model (GPT-5) - Reasoning and analysis
        TaskType.FEASIBILITY_GATE: "primary",
        TaskType.SCENARIO_GENERATION: "primary",
        TaskType.AGENT_ANALYSIS: "primary",
        TaskType.DEBATE: "primary",
        TaskType.CROSS_DOMAIN: "primary",
        TaskType.META_SYNTHESIS: "primary",
        TaskType.FINAL_SYNTHESIS: "primary",
        
        # Default to primary for unknown tasks
        TaskType.GENERAL: "primary",
    }
    
    def __init__(self):
        """Initialize router with model configurations from environment."""
        self.hybrid_enabled = os.getenv("QNWIS_USE_HYBRID_ROUTING", "true").lower() == "true"
        
        # Primary model (GPT-5) - Best for reasoning
        # Temperature 0.3 for balanced reasoning
        self.primary_config = ModelConfig(
            deployment=os.getenv("QNWIS_PRIMARY_MODEL", "gpt-5-chat"),
            api_version=os.getenv("QNWIS_PRIMARY_API_VERSION", "2024-12-01-preview"),
            endpoint=os.getenv("QNWIS_PRIMARY_ENDPOINT", os.getenv("AZURE_OPENAI_ENDPOINT", "")),
            api_key=os.getenv("QNWIS_PRIMARY_API_KEY", os.getenv("API_KEY_5", os.getenv("AZURE_OPENAI_API_KEY", ""))),
            system_role="system",
            temperature=0.3,  # Balanced reasoning
        )
        
        # Fast model (GPT-4o) - Best for extraction/verification
        # Temperature 0.1 for deterministic output
        self.fast_config = ModelConfig(
            deployment=os.getenv("QNWIS_FAST_MODEL", "gpt-4o"),
            api_version=os.getenv("QNWIS_FAST_API_VERSION", "2024-08-01-preview"),
            endpoint=os.getenv("QNWIS_FAST_ENDPOINT", os.getenv("AZURE_OPENAI_ENDPOINT", "")),
            api_key=os.getenv("QNWIS_FAST_API_KEY", os.getenv("AZURE_OPENAI_API_KEY", "")),
            system_role="system",
            temperature=0.1,  # Deterministic for extraction/verification
        )
        
        # Usage tracking
        self.usage_stats: Dict[str, Dict[str, int]] = {
            "primary": {"calls": 0, "tokens": 0},
            "fast": {"calls": 0, "tokens": 0},
        }
        
        logger.info(f"ModelRouter initialized: hybrid_enabled={self.hybrid_enabled}")
        logger.info(f"  Primary model: {self.primary_config.deployment} (temp={self.primary_config.temperature})")
        logger.info(f"  Fast model: {self.fast_config.deployment} (temp={self.fast_config.temperature})")
    
    def get_model_config(self, task_type: TaskType) -> ModelConfig:
        """
        Get the optimal model configuration for a task type.
        
        Args:
            task_type: The type of task being performed
            
        Returns:
            ModelConfig for the optimal model
        """
        if not self.hybrid_enabled:
            # If hybrid routing disabled, use primary for everything
            logger.debug(f"Hybrid routing disabled, using primary model for {task_type.value}")
            return self.primary_config
        
        model_key = self.TASK_MODEL_MAP.get(task_type, "primary")
        
        if model_key == "fast":
            config = self.fast_config
        else:
            config = self.primary_config
        
        logger.debug(f"Task {task_type.value} -> {config.deployment}")
        return config
    
    def get_model_for_task(self, task_name: str) -> ModelConfig:
        """
        Get model config by task name string.
        
        Args:
            task_name: String name of the task (e.g., "extraction", "debate")
            
        Returns:
            ModelConfig for the optimal model
        """
        try:
            task_type = TaskType(task_name.lower())
        except ValueError:
            logger.warning(f"Unknown task type: {task_name}, using primary model")
            task_type = TaskType.GENERAL
        
        return self.get_model_config(task_type)
    
    def get_model_key_for_task(self, task_name: str) -> str:
        """
        Get the model key (primary/fast) for a task name.
        
        Args:
            task_name: String name of the task
            
        Returns:
            "primary" or "fast"
        """
        try:
            task_type = TaskType(task_name.lower())
        except ValueError:
            return "primary"
        
        return self.TASK_MODEL_MAP.get(task_type, "primary")
    
    def track_usage(self, model_key: str, tokens: int = 0):
        """
        Track model usage for monitoring.
        
        Args:
            model_key: "primary" or "fast"
            tokens: Number of tokens used
        """
        if model_key in self.usage_stats:
            self.usage_stats[model_key]["calls"] += 1
            self.usage_stats[model_key]["tokens"] += tokens
            logger.debug(f"Usage tracked: {model_key} +1 call, +{tokens} tokens")
    
    def get_usage_report(self) -> Dict[str, Any]:
        """
        Get usage statistics.
        
        Returns:
            Dictionary with usage stats per model
        """
        return {
            "primary_model": {
                "name": self.primary_config.deployment,
                "temperature": self.primary_config.temperature,
                **self.usage_stats["primary"]
            },
            "fast_model": {
                "name": self.fast_config.deployment,
                "temperature": self.fast_config.temperature,
                **self.usage_stats["fast"]
            },
            "hybrid_enabled": self.hybrid_enabled,
        }
    
    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.usage_stats = {
            "primary": {"calls": 0, "tokens": 0},
            "fast": {"calls": 0, "tokens": 0},
        }


# Global router instance
_router: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """Get or create the global ModelRouter instance."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def reset_router():
    """Reset the global router (useful for testing)."""
    global _router
    _router = None


def get_model_for_task(task: str) -> ModelConfig:
    """Convenience function to get model config for a task."""
    return get_router().get_model_for_task(task)


__all__ = [
    "TaskType",
    "ModelConfig", 
    "ModelRouter",
    "get_router",
    "reset_router",
    "get_model_for_task",
]

