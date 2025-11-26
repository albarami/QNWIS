"""
Prompt Version Manager for QNWIS.

Provides versioned prompt storage with:
- Database persistence
- Version history
- Rollback capability
- A/B testing support
- Performance scoring
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Default storage path for prompts (file-based fallback)
PROMPT_STORAGE_PATH = Path("data/prompts")


@dataclass
class PromptVersion:
    """A versioned prompt with metadata."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    prompt_type: str = "system"  # 'system', 'user_template', 'few_shot'
    version: int = 1
    content: str = ""
    provider: str = "universal"  # 'anthropic', 'azure', 'openai', 'universal'
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = False
    performance_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptVersion":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class PromptVersionManager:
    """
    Manages versioned prompts with persistence.
    
    Supports both file-based and database storage.
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        use_database: bool = False
    ):
        """
        Initialize the prompt version manager.
        
        Args:
            storage_path: Path for file-based storage
            use_database: Whether to use PostgreSQL (if available)
        """
        self.storage_path = storage_path or PROMPT_STORAGE_PATH
        self.use_database = use_database
        self._cache: Dict[str, PromptVersion] = {}
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing prompts
        self._load_all_prompts()
        
        logger.info(
            "Prompt version manager initialized (storage=%s, prompts_loaded=%d)",
            self.storage_path,
            len(self._cache)
        )
    
    def _get_prompt_key(self, agent_name: str, prompt_type: str, provider: str) -> str:
        """Generate a unique key for a prompt."""
        return f"{agent_name}:{prompt_type}:{provider}"
    
    def _get_prompt_file(self, agent_name: str, prompt_type: str, provider: str) -> Path:
        """Get the file path for a prompt."""
        safe_name = f"{agent_name}_{prompt_type}_{provider}.json"
        return self.storage_path / safe_name
    
    def _load_all_prompts(self) -> None:
        """Load all prompts from storage."""
        if not self.storage_path.exists():
            return
        
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Load all versions, keep track of active one
                if isinstance(data, list):
                    for version_data in data:
                        version = PromptVersion.from_dict(version_data)
                        if version.is_active:
                            key = self._get_prompt_key(
                                version.agent_name,
                                version.prompt_type,
                                version.provider
                            )
                            self._cache[key] = version
                elif isinstance(data, dict):
                    version = PromptVersion.from_dict(data)
                    if version.is_active:
                        key = self._get_prompt_key(
                            version.agent_name,
                            version.prompt_type,
                            version.provider
                        )
                        self._cache[key] = version
                        
            except Exception as e:
                logger.warning("Failed to load prompt from %s: %s", file_path, e)
    
    def save_prompt_version(
        self,
        agent_name: str,
        prompt_type: str,
        content: str,
        provider: str = "universal",
        set_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptVersion:
        """
        Save a new version of a prompt.
        
        Args:
            agent_name: Name of the agent
            prompt_type: Type of prompt ('system', 'user_template', etc.)
            content: The prompt content
            provider: Target provider ('anthropic', 'azure', 'universal')
            set_active: Whether to make this the active version
            metadata: Additional metadata
            
        Returns:
            The saved PromptVersion
        """
        # Get existing versions to determine next version number
        existing = self.get_all_versions(agent_name, prompt_type, provider)
        next_version = max([v.version for v in existing], default=0) + 1
        
        # Create new version
        version = PromptVersion(
            agent_name=agent_name,
            prompt_type=prompt_type,
            version=next_version,
            content=content,
            provider=provider,
            is_active=set_active,
            metadata=metadata or {}
        )
        
        # If setting as active, deactivate previous active version
        if set_active:
            for v in existing:
                if v.is_active:
                    v.is_active = False
        
        # Save to file
        file_path = self._get_prompt_file(agent_name, prompt_type, provider)
        all_versions = existing + [version]
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([v.to_dict() for v in all_versions], f, indent=2)
        
        # Update cache
        if set_active:
            key = self._get_prompt_key(agent_name, prompt_type, provider)
            self._cache[key] = version
        
        logger.info(
            "Saved prompt version (agent=%s, type=%s, provider=%s, version=%d, active=%s)",
            agent_name, prompt_type, provider, next_version, set_active
        )
        
        return version
    
    def get_active_prompt(
        self,
        agent_name: str,
        prompt_type: str = "system",
        provider: str = "universal"
    ) -> Optional[PromptVersion]:
        """
        Get the currently active prompt for an agent.
        
        Falls back to 'universal' provider if specific provider not found.
        
        Args:
            agent_name: Name of the agent
            prompt_type: Type of prompt
            provider: Target provider
            
        Returns:
            Active PromptVersion or None
        """
        # Try exact match first
        key = self._get_prompt_key(agent_name, prompt_type, provider)
        if key in self._cache:
            return self._cache[key]
        
        # Fall back to universal
        if provider != "universal":
            universal_key = self._get_prompt_key(agent_name, prompt_type, "universal")
            if universal_key in self._cache:
                return self._cache[universal_key]
        
        return None
    
    def get_all_versions(
        self,
        agent_name: str,
        prompt_type: str,
        provider: str
    ) -> List[PromptVersion]:
        """
        Get all versions of a prompt.
        
        Args:
            agent_name: Name of the agent
            prompt_type: Type of prompt
            provider: Target provider
            
        Returns:
            List of all versions
        """
        file_path = self._get_prompt_file(agent_name, prompt_type, provider)
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return [PromptVersion.from_dict(v) for v in data]
            else:
                return [PromptVersion.from_dict(data)]
                
        except Exception as e:
            logger.warning("Failed to load versions from %s: %s", file_path, e)
            return []
    
    def rollback_prompt(
        self,
        agent_name: str,
        prompt_type: str,
        provider: str,
        target_version: int
    ) -> Optional[PromptVersion]:
        """
        Rollback to a previous version.
        
        Args:
            agent_name: Name of the agent
            prompt_type: Type of prompt
            provider: Target provider
            target_version: Version number to rollback to
            
        Returns:
            The activated version or None if not found
        """
        versions = self.get_all_versions(agent_name, prompt_type, provider)
        
        # Find target version
        target = None
        for v in versions:
            if v.version == target_version:
                target = v
                v.is_active = True
            else:
                v.is_active = False
        
        if not target:
            logger.warning(
                "Version %d not found for rollback (agent=%s, type=%s, provider=%s)",
                target_version, agent_name, prompt_type, provider
            )
            return None
        
        # Save updated versions
        file_path = self._get_prompt_file(agent_name, prompt_type, provider)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([v.to_dict() for v in versions], f, indent=2)
        
        # Update cache
        key = self._get_prompt_key(agent_name, prompt_type, provider)
        self._cache[key] = target
        
        logger.info(
            "Rolled back to version %d (agent=%s, type=%s, provider=%s)",
            target_version, agent_name, prompt_type, provider
        )
        
        return target
    
    def update_performance_score(
        self,
        agent_name: str,
        prompt_type: str,
        provider: str,
        version: int,
        score: float
    ) -> bool:
        """
        Update the performance score for a prompt version.
        
        Args:
            agent_name: Name of the agent
            prompt_type: Type of prompt
            provider: Target provider
            version: Version number
            score: Performance score (0.0 - 1.0)
            
        Returns:
            True if updated, False if version not found
        """
        versions = self.get_all_versions(agent_name, prompt_type, provider)
        
        updated = False
        for v in versions:
            if v.version == version:
                v.performance_score = score
                updated = True
                break
        
        if updated:
            file_path = self._get_prompt_file(agent_name, prompt_type, provider)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([v.to_dict() for v in versions], f, indent=2)
            
            logger.info(
                "Updated performance score: %.2f (agent=%s, type=%s, provider=%s, version=%d)",
                score, agent_name, prompt_type, provider, version
            )
        
        return updated
    
    def compare_versions(
        self,
        agent_name: str,
        prompt_type: str,
        provider: str
    ) -> List[Dict[str, Any]]:
        """
        Get comparison data for all versions of a prompt.
        
        Args:
            agent_name: Name of the agent
            prompt_type: Type of prompt
            provider: Target provider
            
        Returns:
            List of version comparison data
        """
        versions = self.get_all_versions(agent_name, prompt_type, provider)
        
        return [
            {
                "version": v.version,
                "created_at": v.created_at,
                "is_active": v.is_active,
                "performance_score": v.performance_score,
                "content_length": len(v.content),
                "metadata": v.metadata
            }
            for v in sorted(versions, key=lambda x: x.version, reverse=True)
        ]
    
    def list_all_prompts(self) -> List[Dict[str, Any]]:
        """
        List all prompts in the system.
        
        Returns:
            List of prompt summaries
        """
        prompts = []
        for key, version in self._cache.items():
            prompts.append({
                "agent_name": version.agent_name,
                "prompt_type": version.prompt_type,
                "provider": version.provider,
                "active_version": version.version,
                "performance_score": version.performance_score,
                "created_at": version.created_at
            })
        return prompts


# Global prompt manager instance
_prompt_manager: Optional[PromptVersionManager] = None


def get_prompt_manager() -> PromptVersionManager:
    """
    Get or create the global prompt version manager.
    
    Returns:
        PromptVersionManager instance
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptVersionManager()
    return _prompt_manager


__all__ = [
    "PromptVersion",
    "PromptVersionManager",
    "get_prompt_manager",
]

