"""
National Strategy Agent (LLM-powered) - Vision 2030 and strategic analysis.

This agent uses LLM reasoning to provide strategic insights on Qatar's
workforce development, GCC competitiveness, and Vision 2030 alignment.
"""

from __future__ import annotations
from typing import Dict

from .base import DataClient
from .base_llm import LLMAgent
from .prompts.national_strategy import build_national_strategy_prompt
from ..llm.client import LLMClient

EMPLOYMENT_QUERY = "syn_employment_share_by_gender_latest"
GCC_UNEMPLOYMENT_QUERY = "syn_unemployment_gcc_latest"


class NationalStrategyLLMAgent(LLMAgent):
    """
    LLM-powered agent focused on national strategy and Vision 2030 alignment.

    Uses LLM reasoning to analyze strategic workforce trends,
    GCC competitive positioning, and Vision 2030 progress.
    """

    def __init__(self, client: DataClient, llm: LLMClient) -> None:
        """
        Initialize the National Strategy Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
            llm: LLM client for reasoning
        """
        super().__init__(client, llm)

    async def _fetch_data(self, question: str, context: Dict) -> Dict:
        """
        Fetch employment and GCC data for strategic analysis.
        
        Args:
            question: User's question
            context: Additional context
            
        Returns:
            Dictionary of QueryResults
        """
        # Fetch employment and GCC unemployment data
        employment_data = self.client.run(EMPLOYMENT_QUERY)
        gcc_data = self.client.run(GCC_UNEMPLOYMENT_QUERY)
        
        return {
            "employment": employment_data,
            "gcc_unemployment": gcc_data
        }
    
    def _build_prompt(self, question: str, data: Dict, context: Dict) -> tuple[str, str]:
        """
        Build national strategy prompt with data.
        
        Args:
            question: User's question
            data: Dictionary of QueryResults
            context: Additional context
            
        Returns:
            (system_prompt, user_prompt) tuple
        """
        return build_national_strategy_prompt(question, data, context)
