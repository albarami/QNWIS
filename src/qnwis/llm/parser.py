"""
LLM response parser for QNWIS.

Parses LLM responses into structured AgentFinding objects
and validates numbers against source data.
"""

import json
import re
import logging
from typing import List, Set, Optional, Union
from pydantic import BaseModel, Field, field_validator

from src.qnwis.llm.exceptions import LLMParseError

logger = logging.getLogger(__name__)


class AgentFinding(BaseModel):
    """
    Structured output from agent LLM.
    
    This is the canonical format for agent findings after LLM processing.
    """
    
    title: str = Field(..., description="Brief finding title")
    summary: str = Field(..., description="2-3 sentence executive summary")
    metrics: dict[str, Union[float, int, str]] = Field(
        default_factory=dict,
        description="Key metrics extracted from data (accepts numbers and strings for ranges/comparatives)"
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

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @field_validator('metrics')
    @classmethod
    def validate_metrics(cls, v):
        """Accept numeric values and strings (for ranges like '0.10% - 4.90%')."""
        for key, value in v.items():
            if not isinstance(value, (int, float, str)):
                raise ValueError(f"Metric '{key}' must be numeric or string, got {type(value)}")
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
            logger.error(f"JSON string (first 1000 chars): {json_str[:1000]}")
            logger.error(f"JSON string (last 500 chars): {json_str[-500:]}")
            # Debug: show characters around error position
            if hasattr(e, 'pos'):
                start = max(0, e.pos - 20)
                end = min(len(json_str), e.pos + 20)
                context = json_str[start:end]
                logger.error(f"Error context (pos {e.pos}): {repr(context)}")
                logger.error(f"Character codes: {[ord(c) for c in json_str[:10]]}")
            raise LLMParseError(f"Invalid JSON: {e}") from e
        except Exception as e:
            logger.error(f"Failed to parse AgentFinding: {e}")
            raise LLMParseError(f"Failed to parse response: {e}") from e
    
    def _repair_json(self, json_str: str) -> str:
        """Attempt to repair common JSON syntax errors from LLM output.

        The main issue: LLMs include literal newlines INSIDE string values,
        which is invalid JSON. We need to escape those but NOT the formatting newlines.
        """

        # Strategy: Walk through the string and escape control characters only when inside quotes
        result = []
        in_string = False
        escape_next = False

        for i, char in enumerate(json_str):
            # Handle escape sequences
            if escape_next:
                result.append(char)
                escape_next = False
                continue

            if char == '\\':
                result.append(char)
                escape_next = True
                continue

            # Track whether we're inside a string
            if char == '"':
                in_string = not in_string
                result.append(char)
                continue

            # Escape control characters ONLY inside strings
            if in_string:
                if char == '\n':
                    result.append('\\n')
                elif char == '\r':
                    result.append('\\r')
                elif char == '\t':
                    result.append('\\t')
                else:
                    result.append(char)
            else:
                result.append(char)

        json_str = ''.join(result)

        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        return json_str

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
        # Try to find JSON in code blocks first (with or without 'json' language tag)
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            return self._repair_json(match.group(1))
        
        # Try to find raw JSON object with balanced braces
        try:
            start_idx = text.find('{')
            if start_idx == -1:
                return None
            
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(text)):
                char = text[i]
                
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return self._repair_json(text[start_idx:i+1])
            
            # Fallback: If strict balancing failed (e.g. bad escaping), try outermost braces
            last_idx = text.rfind('}')
            if last_idx > start_idx:
                return self._repair_json(text[start_idx:last_idx+1])
                
            return None
        except Exception:
            # Ultimate fallback: outermost braces
            try:
                s = text.find('{')
                e = text.rfind('}')
                if s != -1 and e > s:
                    return self._repair_json(text[s:e+1])
            except:
                pass
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
        for key, value in (finding.metrics or {}).items():
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
            logger.debug(
                f"Number validation failed for finding '{finding.title}': "
                f"{len(violations)} violations (first 3: {violations[:3]})"
            )
        
        return is_valid, violations
    
    def _number_exists(
        self,
        number: float,
        allowed: Set[float],
        tolerance: float = 0.01
    ) -> bool:
        """Check if ``number`` exists in ``allowed`` within a relative tolerance.

        The caller may pass metrics as strings (e.g. "0.10%" or "0.10 - 0.20").
        This helper now defensively coerces common numeric-like strings to
        floats and treats non-numeric strings as simply not present rather than
        raising a ``TypeError`` during ``abs()``.

        Args:
            number: Number (or numeric-like string) to check.
            allowed: Set of allowed numeric values.
            tolerance: Relative tolerance (default 1%).

        Returns:
            True if the value exists in ``allowed`` within the given tolerance.
        """

        # Coerce strings like "0.10%" or "1,234.5" to float when possible.
        if not isinstance(number, (int, float)):
            if isinstance(number, str):
                candidate = number.strip().replace(",", "")
                # Drop trailing percent sign if present.
                if candidate.endswith("%"):
                    candidate = candidate[:-1]
                try:
                    number_val = float(candidate)
                except ValueError:
                    # Non-numeric string: treat as not found.
                    logger.debug("_number_exists: non-numeric value '%s'", number)
                    return False
            else:
                # Unsupported type (e.g. list/dict) – cannot be validated numerically.
                logger.debug("_number_exists: unsupported type %s", type(number))
                return False
        else:
            number_val = float(number)

        for allowed_num in allowed:
            # Handle exact matches
            if number_val == allowed_num:
                return True

            # Handle relative tolerance
            denominator = max(abs(allowed_num), abs(number_val), 1.0)
            relative_diff = abs(number_val - allowed_num) / denominator

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
