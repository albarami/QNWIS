"""
Nationalization Agent - GCC unemployment comparison and ranking.

This agent uses LLM reasoning to analyze unemployment rates across GCC countries
and provide strategic insights on Qatar's competitive position.
"""

from __future__ import annotations
from typing import Dict

from .base import DataClient
from .base_llm import LLMAgent
from .prompts.nationalization import build_nationalization_prompt
from ..llm.client import LLMClient

UNEMPLOY_QUERY = "q_unemployment_rate_gcc_latest"


class NationalizationAgent(LLMAgent):
    """
    Agent focused on nationalization policy through GCC unemployment comparison.

    Uses LLM reasoning to analyze unemployment rates across GCC countries
    and provide strategic policy insights.
    """

    def __init__(self, client: DataClient, llm: LLMClient) -> None:
        """
        Initialize the Nationalization Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
            llm: LLM client for reasoning
        """
        super().__init__(client, llm)

    async def _fetch_data(self, question: str, context: Dict) -> Dict:
        """
        Fetch GCC unemployment data from deterministic layer.
        
        Args:
            question: User's question
            context: Additional context
            
        Returns:
            Dictionary of QueryResults
        """
        # Fetch GCC unemployment comparison data
        unemployment_data = self.client.run(UNEMPLOY_QUERY)
        
        return {
            "gcc_unemployment": unemployment_data
        }
    
    def _build_prompt(self, question: str, data: Dict, context: Dict) -> tuple[str, str]:
        """
        Build nationalization prompt with data.
        
        Args:
            question: User's question
            data: Dictionary of QueryResults
            context: Additional context
            
        Returns:
            (system_prompt, user_prompt) tuple
        """
        return build_nationalization_prompt(question, data, context)
