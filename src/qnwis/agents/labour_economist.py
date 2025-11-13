"""
Labour Economist Agent - Employment trends and gender distribution analysis.

This agent uses LLM reasoning to analyze employment share data by gender
and provide contextual insights using only deterministic data sources.
"""

from __future__ import annotations
from typing import Dict

from .base import DataClient
from .base_llm import LLMAgent
from .prompts.labour_economist import build_labour_economist_prompt
from ..llm.client import LLMClient

EMPLOYMENT_QUERY = "syn_employment_share_by_gender_latest"


class LabourEconomistAgent(LLMAgent):
    """
    Agent focused on employment statistics and gender distribution.
    
    Uses LLM reasoning to analyze employment trends and provide
    contextual insights from deterministic data sources.
    """

    def __init__(self, client: DataClient, llm: LLMClient) -> None:
        """
        Initialize the Labour Economist Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
            llm: LLM client for reasoning
        """
        super().__init__(client, llm)

    async def _fetch_data(self, question: str, context: Dict) -> Dict:
        """
        Fetch employment data from deterministic layer.
        
        Args:
            question: User's question
            context: Additional context
            
        Returns:
            Dictionary of QueryResults
        """
        # Fetch employment share data
        employment_data = self.client.run(EMPLOYMENT_QUERY)
        
        return {
            "employment_share": employment_data
        }
    
    def _build_prompt(self, question: str, data: Dict, context: Dict) -> tuple[str, str]:
        """
        Build labour economist prompt with data.
        
        Args:
            question: User's question
            data: Dictionary of QueryResults
            context: Additional context
            
        Returns:
            (system_prompt, user_prompt) tuple
        """
        return build_labour_economist_prompt(question, data, context)
