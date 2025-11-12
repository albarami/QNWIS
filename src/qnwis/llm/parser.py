"""
LLM response parser for QNWIS.

Parses LLM responses into structured AgentFinding objects
and validates numbers against source data.
"""

import json
import re
import logging
from typing import List, Set, Optional
from pydantic import BaseModel, Field, validator

from src.qnwis.llm.exceptions import LLMParseError

logger = logging.getLogger(__name__)


class AgentFinding(BaseModel):
    """
    Structured output from agent LLM.
    
    This is the canonical format for agent findings after LLM processing.
    """
    
    title: str = Field(..., description="Brief finding title")
    summary: str = Field(..., description="2-3 sentence executive summary")
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Key metrics extracted from data"
    )
    analysis: str = Field(..., description="Detailed analysis paragraph")
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)"
    )
    citations: list[str] = Field(
        default_factory=list,
        description="Query IDs cited"
    )
    data_quality_notes: str = Field(
        default="",
        description="Notes about data quality or limitations"
    )
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    @validator('metrics')
    def validate_metrics(cls, v):
        """Ensure all metric values are numeric."""
        for key, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Metric '{key}' must be numeric, got {type(value)}")
        return v


class LLMResponseParser:
    """
    Parse and validate LLM responses.
    
    Handles JSON extraction, structured parsing, and number validation.
    """
    
    def parse_agent_response(self, text: str) -> AgentFinding:
        """
        Parse LLM response into AgentFinding.
        
        Args:
            text: Raw LLM response (may contain JSON embedded in text)
            
        Returns:
            Parsed AgentFinding
            
        Raises:
            LLMParseError: If response cannot be parsed
        """
        # Try to extract JSON from response
        json_str = self._extract_json(text)
        
        if not json_str:
            raise LLMParseError("No JSON found in LLM response")
        
        try:
            data = json.loads(json_str)
            return AgentFinding(**data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in LLM response: {e}")
            logger.debug(f"JSON string: {json_str[:500]}")
            raise LLMParseError(f"Invalid JSON: {e}") from e
        except Exception as e:
            logger.error(f"Failed to parse AgentFinding: {e}")
            raise LLMParseError(f"Failed to parse response: {e}") from e
    
    def _extract_json(self, text: str) -> Optional[str]:
        """
        Extract JSON object from text.
        
        Handles cases where JSON is embedded in markdown code blocks
        or surrounded by explanatory text.
        
        Args:
            text: Text potentially containing JSON
            
        Returns:
            JSON string or None
        """
        # Try to find JSON in code blocks first
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        
        # Try to find raw JSON object
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        # Return the longest match (most likely to be complete)
        if matches:
            return max(matches, key=len)
        
        return None
    
    def extract_numbers(self, text: str) -> List[float]:
        """
        Extract all numbers from text.
        
        Args:
            text: Text containing numbers
            
        Returns:
            List of extracted numbers
        """
        # Match integers and floats, including with commas
        pattern = r'\b\d+(?:,\d{3})*(?:\.\d+)?\b'
        matches = re.findall(pattern, text)
        
        numbers = []
        for match in matches:
            # Remove commas and convert to float
            clean = match.replace(',', '')
            try:
                numbers.append(float(clean))
            except ValueError:
                continue
        
        return numbers
    
    def validate_numbers(
        self,
        finding: AgentFinding,
        allowed_numbers: Set[float],
        tolerance: float = 0.01
    ) -> tuple[bool, List[str]]:
        """
        Validate that all numbers in finding exist in allowed set.
        
        This prevents LLM hallucination by ensuring all metrics
        come from actual data.
        
        Args:
            finding: Parsed finding to validate
            allowed_numbers: Set of valid numbers from QueryResults
            tolerance: Relative tolerance for floating point comparison
            
        Returns:
            (is_valid, list_of_violations)
        """
        violations = []
        
        # Check metrics
        for key, value in finding.metrics.items():
            if not self._number_exists(value, allowed_numbers, tolerance):
                violations.append(
                    f"Metric '{key}' has value {value} not found in source data"
                )
        
        # Check analysis text for numbers
        analysis_numbers = self.extract_numbers(finding.analysis)
        for num in analysis_numbers:
            if not self._number_exists(num, allowed_numbers, tolerance):
                violations.append(
                    f"Analysis contains number {num} not found in source data"
                )
        
        # Check summary text for numbers
        summary_numbers = self.extract_numbers(finding.summary)
        for num in summary_numbers:
            if not self._number_exists(num, allowed_numbers, tolerance):
                violations.append(
                    f"Summary contains number {num} not found in source data"
                )
        
        is_valid = len(violations) == 0
        
        if not is_valid:
            logger.warning(
                f"Number validation failed for finding '{finding.title}': "
                f"{len(violations)} violations"
            )
            for violation in violations[:3]:  # Log first 3
                logger.warning(f"  - {violation}")
        
        return is_valid, violations
    
    def _number_exists(
        self,
        number: float,
        allowed: Set[float],
        tolerance: float = 0.01
    ) -> bool:
        """
        Check if number exists in allowed set with tolerance.
        
        Uses relative tolerance to handle floating point precision.
        
        Args:
            number: Number to check
            allowed: Set of allowed numbers
            tolerance: Relative tolerance (default 1%)
            
        Returns:
            True if number exists in allowed set
        """
        for allowed_num in allowed:
            # Handle exact matches
            if number == allowed_num:
                return True
            
            # Handle relative tolerance
            denominator = max(abs(allowed_num), abs(number), 1.0)
            relative_diff = abs(number - allowed_num) / denominator
            
            if relative_diff < tolerance:
                return True
        
        return False
    
    def extract_numbers_from_query_results(
        self,
        query_results: dict
    ) -> Set[float]:
        """
        Extract all numbers from QueryResult objects.
        
        Args:
            query_results: Dictionary of {key: QueryResult}
            
        Returns:
            Set of all numbers found in query results
        """
        numbers = set()
        
        for query_result in query_results.values():
            # Extract from rows
            for row in query_result.rows:
                for value in row.data.values():
                    if isinstance(value, (int, float)):
                        numbers.add(float(value))
            
            # Extract from metadata if present
            if hasattr(query_result, 'metadata') and query_result.metadata:
                for value in query_result.metadata.values():
                    if isinstance(value, (int, float)):
                        numbers.add(float(value))
        
        return numbers
