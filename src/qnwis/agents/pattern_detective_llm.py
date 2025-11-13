"""
Pattern Detective Agent (LLM-powered) - Data consistency and pattern analysis.

This agent uses LLM reasoning to validate data consistency, detect anomalies,
and identify patterns in Qatar's workforce data.
"""

from __future__ import annotations
from typing import Dict

from .base import DataClient
from .base_llm import LLMAgent
from .prompts.pattern_detective import build_pattern_detective_prompt
from ..llm.client import LLMClient

EMPLOYMENT_QUERY = "syn_employment_share_by_gender_latest"


class PatternDetectiveLLMAgent(LLMAgent):
    """
    LLM-powered agent focused on data consistency validation and pattern detection.

    Uses LLM reasoning to analyze data quality, validate consistency,
    and identify interesting patterns in workforce data.
    """

    def __init__(self, client: DataClient, llm: LLMClient) -> None:
        """
        Initialize the Pattern Detective Agent.

        Args:
            client: DataClient instance for accessing deterministic queries
            llm: LLM client for reasoning
        """
        super().__init__(client, llm)

    async def _fetch_data(self, question: str, context: Dict) -> Dict:
        """
        Fetch employment data for consistency validation.
        
        Args:
            question: User's question
            context: Additional context
            
        Returns:
            Dictionary of QueryResults
        """
        # Fetch employment gender distribution for validation
        employment_data = self.client.run(EMPLOYMENT_QUERY)
        
        return {
            "employment_gender": employment_data
        }
    
    def _build_prompt(self, question: str, data: Dict, context: Dict) -> tuple[str, str]:
        """
        Build pattern detective prompt with data.
        
        Args:
            question: User's question
            data: Dictionary of QueryResults
            context: Additional context
            
        Returns:
            (system_prompt, user_prompt) tuple
        """
        return build_pattern_detective_prompt(question, data, context)
