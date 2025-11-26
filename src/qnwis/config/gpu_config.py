"""
GPU Configuration for Multi-GPU Deep Analysis Architecture.

Loads and validates configuration from config/gpu_config.yaml with
environment variable overrides.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class EmbeddingConfig(BaseModel):
    """Configuration for embedding model."""
    gpu_id: int = Field(6, description="GPU ID for embeddings")
    model: str = Field("all-mpnet-base-v2", description="Embedding model (production-stable)")
    dimensions: int = Field(768, description="Embedding dimensions")
    memory_limit_gb: float = Field(2.0, description="Memory limit in GB")
    shared_with: List[str] = Field(default_factory=list, description="Shared with other components")
    fallback_to_cpu: bool = Field(True, description="Fallback to CPU if GPU unavailable")


class FactVerificationConfig(BaseModel):
    """Configuration for fact verification."""
    gpu_id: int = Field(6, description="GPU ID for verification")
    model: str = Field("all-mpnet-base-v2", description="Verification model (production-stable)")
    max_documents: int = Field(500_000, description="Maximum documents to index")
    enable: bool = Field(True, description="Enable fact verification")
    verification_threshold: float = Field(0.75, description="Similarity threshold for verification")
    memory_limit_gb: float = Field(2.0, description="Memory limit in GB")


class ParallelScenariosConfig(BaseModel):
    """Configuration for parallel scenario execution."""
    enable: bool = Field(True, description="Enable parallel scenarios")
    num_scenarios: int = Field(6, description="Number of scenarios to generate")
    num_parallel: int = Field(6, description="Number to execute simultaneously")
    gpu_range: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5], description="GPUs for scenarios")
    overflow_gpu: int = Field(7, description="GPU for overflow scenarios")
    
    @field_validator('num_scenarios')
    @classmethod
    def validate_num_scenarios(cls, v):
        if v < 4 or v > 8:
            raise ValueError("num_scenarios must be between 4 and 8")
        return v


class ModelsConfig(BaseModel):
    """Configuration for LLM models."""
    primary_llm: str = Field("claude-sonnet-4-20250514", description="Primary LLM for reasoning")
    rate_limit_per_minute: int = Field(50, description="API rate limit")
    rate_limit_semaphore: int = Field(20, description="Concurrent request limit")
    embedding_model: str = Field("all-mpnet-base-v2", description="Embedding model (production-stable)")
    embedding_dimensions: int = Field(768, description="Embedding dimensions")


class QualityConfig(BaseModel):
    """Configuration for quality settings."""
    parallel_scenario_threshold: str = Field("complex", description="When to use parallel scenarios")
    verification_enabled: bool = Field(True, description="Enable fact verification")
    target_document_count: int = Field(70000, description="Target number of documents")


class PerformanceConfig(BaseModel):
    """Configuration for performance targets."""
    target_parallel_time_seconds: int = Field(90, description="Target time for 6 scenarios")
    expected_speedup: float = Field(3.0, description="Expected parallel speedup")
    max_verification_overhead_ms: int = Field(500, description="Max verification overhead per turn")
    target_gpu_utilization_percent: int = Field(70, description="Target GPU utilization")


class GPUConfig(BaseModel):
    """
    Complete GPU configuration for multi-GPU deep analysis.
    
    Loads from config/gpu_config.yaml with environment variable overrides.
    """
    embeddings: EmbeddingConfig
    fact_verification: FactVerificationConfig
    parallel_scenarios: ParallelScenariosConfig
    models: ModelsConfig
    quality: QualityConfig
    performance: PerformanceConfig
    
    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> "GPUConfig":
        """
        Load configuration from YAML file with environment overrides.
        
        Args:
            config_path: Path to config file (default: config/gpu_config.yaml)
            
        Returns:
            Validated GPUConfig instance
        """
        if config_path is None:
            # Default path
            config_path = Path("config/gpu_config.yaml")
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls._default_config()
        
        try:
            # Load YAML
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Apply environment overrides
            config_data = cls._apply_env_overrides(config_data)
            
            # Parse and validate with Pydantic
            config = cls(
                embeddings=EmbeddingConfig(**config_data.get('gpu_allocation', {}).get('embeddings', {})),
                fact_verification=FactVerificationConfig(**config_data.get('gpu_allocation', {}).get('fact_verification', {})),
                parallel_scenarios=ParallelScenariosConfig(**config_data.get('gpu_allocation', {}).get('parallel_scenarios', {})),
                models=ModelsConfig(**config_data.get('models', {})),
                quality=QualityConfig(**config_data.get('quality', {})),
                performance=PerformanceConfig(**config_data.get('performance', {}))
            )
            
            logger.info(f"✅ GPU configuration loaded from {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load GPU config: {e}", exc_info=True)
            logger.warning("Using default configuration")
            return cls._default_config()
    
    @classmethod
    def _default_config(cls) -> "GPUConfig":
        """
        Create default configuration.
        
        Returns:
            GPUConfig with default values
        """
        return cls(
            embeddings=EmbeddingConfig(),
            fact_verification=FactVerificationConfig(),
            parallel_scenarios=ParallelScenariosConfig(),
            models=ModelsConfig(),
            quality=QualityConfig(),
            performance=PerformanceConfig()
        )
    
    @classmethod
    def _apply_env_overrides(cls, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Args:
            config_data: Configuration dictionary from YAML
            
        Returns:
            Configuration with environment overrides applied
        """
        # Parallel scenarios enable
        if os.getenv('QNWIS_ENABLE_PARALLEL_SCENARIOS'):
            value = os.getenv('QNWIS_ENABLE_PARALLEL_SCENARIOS').lower() in ('true', '1', 'yes')
            config_data.setdefault('gpu_allocation', {}).setdefault('parallel_scenarios', {})['enable'] = value
        
        # Fact verification enable
        if os.getenv('QNWIS_ENABLE_FACT_VERIFICATION'):
            value = os.getenv('QNWIS_ENABLE_FACT_VERIFICATION').lower() in ('true', '1', 'yes')
            config_data.setdefault('gpu_allocation', {}).setdefault('fact_verification', {})['enable'] = value
        
        # Claude rate limit
        if os.getenv('QNWIS_CLAUDE_RATE_LIMIT'):
            value = int(os.getenv('QNWIS_CLAUDE_RATE_LIMIT'))
            config_data.setdefault('models', {})['rate_limit_per_minute'] = value
        
        # GPU device override
        if os.getenv('QNWIS_GPU_DEVICE'):
            value = int(os.getenv('QNWIS_GPU_DEVICE'))
            config_data.setdefault('gpu_allocation', {}).setdefault('embeddings', {})['gpu_id'] = value
            config_data.setdefault('gpu_allocation', {}).setdefault('fact_verification', {})['gpu_id'] = value
        
        return config_data


# Global configuration instance
_global_config: Optional[GPUConfig] = None


def load_gpu_config(config_path: Optional[Path] = None) -> GPUConfig:
    """
    Load GPU configuration (singleton).
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        GPUConfig instance
    """
    global _global_config
    
    if _global_config is None:
        _global_config = GPUConfig.from_yaml(config_path)
    
    return _global_config


def get_gpu_config() -> GPUConfig:
    """
    Get current GPU configuration.
    
    Returns:
        GPUConfig instance (loads default if not yet loaded)
    """
    if _global_config is None:
        return load_gpu_config()
    
    return _global_config

