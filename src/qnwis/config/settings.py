"""
Application settings and configuration management.
Uses pydantic-settings for environment variable validation.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/qnwis",
        description="PostgreSQL connection URL",
    )
    db_pool_size: int = Field(default=20, description="Database connection pool size")
    db_max_overflow: int = Field(default=0, description="Maximum overflow connections")

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_max_connections: int = Field(default=50, description="Redis connection pool size")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="Number of API workers")
    api_reload: bool = Field(default=False, description="Enable auto-reload")
    api_debug: bool = Field(default=False, description="Enable debug mode")
    api_cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="CORS allowed origins",
    )

    # Application Settings
    environment: str = Field(default="development", description="Environment name")
    log_level: str = Field(default="INFO", description="Logging level")
    secret_key: str = Field(
        default="change_this_secret_key_in_production",
        description="Secret key for encryption",
    )

    # Agent Configuration
    agent_timeout_seconds: int = Field(default=5, description="Agent timeout in seconds")
    stage_a_timeout_ms: int = Field(default=50, description="Stage A timeout in milliseconds")
    stage_b_timeout_ms: int = Field(default=60, description="Stage B timeout in milliseconds")
    stage_c_timeout_ms: int = Field(default=40, description="Stage C timeout in milliseconds")

    # Skill Inference Settings
    skill_inference_ratio: float = Field(
        default=0.80,
        description="Ratio of inferred skills",
        ge=0.0,
        le=1.0,
    )
    skill_explicit_ratio: float = Field(
        default=0.20,
        description="Ratio of explicit skills",
        ge=0.0,
        le=1.0,
    )

    # Bias Mitigation
    bias_threshold_araweat: float = Field(
        default=0.15,
        description="AraWEAT bias threshold",
        ge=0.0,
        le=1.0,
    )
    bias_threshold_seat: float = Field(
        default=0.15,
        description="SEAT bias threshold",
        ge=0.0,
        le=1.0,
    )

    # Performance Metrics
    ndcg_target_min: float = Field(
        default=0.70,
        description="Minimum NDCG@10 target",
        ge=0.0,
        le=1.0,
    )
    ndcg_target_max: float = Field(
        default=0.80,
        description="Maximum NDCG@10 target",
        ge=0.0,
        le=1.0,
    )
    mrr_target: float = Field(
        default=0.75,
        description="MRR target",
        ge=0.0,
        le=1.0,
    )

    @field_validator("skill_inference_ratio", "skill_explicit_ratio")
    @classmethod
    def validate_skill_ratios(cls, v: float) -> float:
        """Validate skill ratio is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Skill ratio must be between 0.0 and 1.0")
        return v


# Global settings instance
settings = Settings()
