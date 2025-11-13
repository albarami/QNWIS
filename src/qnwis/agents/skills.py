"""
Skills Agent - Skills pipeline analysis through gender distribution.

This agent uses LLM reasoning to analyze gender distribution in employment
and provide insights on skills pipeline and workforce composition.
"""

from __future__ import annotations
from typing import Dict

from .base import DataClient
from .base_llm import LLMAgent
from .prompts.skills import build_skills_prompt
from ..llm.client import LLMClient

SKILLS_QUERY = "syn_employment_share_by_gender_latest"


class SkillsAgent(LLMAgent):
    """
    Agent focused on skills pipeline through gender distribution metrics.

    Uses LLM reasoning to analyze employment gender distribution
    and provide insights on skills availability and workforce composition.
    """

    def __init__(self, client: DataClient, llm: LLMClient) -> None:
        """
        Initialize the Skills Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
            llm: LLM client for reasoning
        """
        super().__init__(client, llm)

    async def _fetch_data(self, question: str, context: Dict) -> Dict:
        """
        Fetch skills and employment data from deterministic layer.
        
        Args:
            question: User's question
            context: Additional context
            
        Returns:
            Dictionary of QueryResults
        """
        # Fetch employment gender distribution data
        skills_data = self.client.run(SKILLS_QUERY)
        
        return {
            "employment_gender": skills_data
        }
    
    def _build_prompt(self, question: str, data: Dict, context: Dict) -> tuple[str, str]:
        """
        Build skills prompt with data.
        
        Args:
            question: User's question
            data: Dictionary of QueryResults
            context: Additional context
            
        Returns:
            (system_prompt, user_prompt) tuple
        """
        return build_skills_prompt(question, data, context)
