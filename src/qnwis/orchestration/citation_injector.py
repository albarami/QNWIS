"""
Citation Injector - Post-process LLM output to inject [Per extraction: ...] citations.

Since LLMs systematically resist the citation format (it looks like "clutter" in clean JSON),
we inject citations programmatically by matching numbers in the text to source data.

This is a pragmatic solution that accepts LLM limitations and works around them.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


class CitationInjector:
    """
    Post-process LLM output to inject [Per extraction: ...] citations.

    This class builds a comprehensive map of numbers to their source data,
    then injects inline citations next to every number in the analysis text.
    """

    def __init__(self):
        self.number_to_source: Dict[str, Tuple[str, str, str]] = {}

    def build_source_map(self, source_data: Dict[str, Any]) -> None:
        """
        Build a map of number → (source, period, query_id).

        Args:
            source_data: Dictionary of query_id → QueryResult objects
        """
        self.number_to_source.clear()

        for query_id, result in source_data.items():
            if not result or not hasattr(result, 'rows'):
                continue

            # Extract provenance
            source = "Unknown"
            period = "Unknown"

            if hasattr(result, 'provenance') and result.provenance:
                source = result.provenance.source or "Unknown"

            if hasattr(result, 'freshness') and result.freshness:
                period = result.freshness.asof_date or "Unknown"

            # Extract all numbers from this query's data
            for row in result.rows:
                if not hasattr(row, 'data'):
                    continue

                for key, value in row.data.items():
                    if isinstance(value, (int, float)):
                        # Store multiple formats
                        formats = self._generate_number_formats(value)
                        for fmt in formats:
                            self.number_to_source[fmt] = (source, period, query_id)

                    elif isinstance(value, str):
                        # Try to extract numbers from string values
                        nums = re.findall(r'\d+\.?\d*', value)
                        for num in nums:
                            self.number_to_source[num] = (source, period, query_id)

        logger.info(f"Citation map built: {len(self.number_to_source)} numbers mapped to sources")

    def _generate_number_formats(self, value: float) -> List[str]:
        """
        Generate multiple string formats for a number to maximize matching.

        Examples:
            0.10 → ["0.10", "0.1", "10.0", "10.00", "10", "0.10%"]
            88.7 → ["88.7", "88.70", "88.7%"]
        """
        formats = []

        # Raw formats
        formats.append(str(value))
        formats.append(f"{value:.1f}")
        formats.append(f"{value:.2f}")

        # Percentage formats (if value < 1, likely a decimal percentage)
        if value < 1:
            # Decimal-as-percentage (e.g., 0.10 → 10.0)
            percent = value * 100
            formats.append(f"{percent:.0f}")
            formats.append(f"{percent:.1f}")
            formats.append(f"{percent:.2f}")
            formats.append(f"{percent:.0f}%")
            formats.append(f"{percent:.1f}%")
            formats.append(f"{percent:.2f}%")
            
            # Also include decimal-with-percent (e.g., 0.10%)
            formats.append(f"{value:.1f}%")
            formats.append(f"{value:.2f}%")
        else:
            # Already a percentage
            formats.append(f"{value:.0f}%")
            formats.append(f"{value:.1f}%")
            formats.append(f"{value:.2f}%")

        # Integer formats
        if value == int(value):
            formats.append(str(int(value)))

        return list(set(formats))  # Remove duplicates

    def inject_citations(
        self,
        text: str,
        source_data: Dict[str, Any],
        aggressive: bool = True
    ) -> str:
        """
        Find all numbers in text and add citations.

        Args:
            text: Original LLM output
            source_data: Dictionary of QueryResult objects
            aggressive: If True, cite even numbers without exact matches

        Returns:
            Text with [Per extraction: ...] citations injected
        """
        if not text:
            return text

        # Build source map
        self.build_source_map(source_data)

        if not self.number_to_source:
            logger.warning("No source data available for citation injection")
            return text

        # Track already cited positions to avoid double-citing
        cited_positions = set()

        def replace_number(match):
            number = match.group(0)
            start_pos = match.start()
            end_pos = match.end()

            # Skip if this position is already cited
            if any(start_pos <= p <= end_pos for p in cited_positions):
                return number

            # Check if already cited (look for nearby [Per extraction: ...])
            before = text[max(0, start_pos - 100):start_pos]
            after = text[end_pos:min(len(text), end_pos + 100)]

            if "[Per extraction:" in before or "[Per extraction:" in after:
                cited_positions.add(start_pos)
                return number  # Already cited

            # Find matching source
            if number in self.number_to_source:
                source, period, query_id = self.number_to_source[number]
                citation = f" [Per extraction: '{number}' from {source} {period}]"
                cited_positions.add(start_pos)
                return f"{number}{citation}"

            elif aggressive:
                # Try fuzzy matching (e.g., "0.1" matches "0.10")
                for stored_num, (source, period, query_id) in self.number_to_source.items():
                    if self._fuzzy_match(number, stored_num):
                        citation = f" [Per extraction: '{stored_num}' from {source} {period}]"
                        cited_positions.add(start_pos)
                        return f"{number}{citation}"

                # Number not in source data - flag it
                logger.warning(f"Number '{number}' not found in source data")
                cited_positions.add(start_pos)
                return f"{number} [UNVERIFIED]"

            return number

        # Replace all numbers with cited versions
        # Pattern: enforce a boundary so the optional % stays with the match
        pattern = r'(?<![\d.])\d+(?:\.\d+)?%?'
        cited_text = re.sub(pattern, replace_number, text)

        injected_count = len(cited_positions)
        logger.info(f"Injected {injected_count} citations into text")

        return cited_text

    def _fuzzy_match(self, num1: str, num2: str, tolerance: float = 0.01) -> bool:
        """
        Check if two number strings represent approximately the same value.

        Examples:
            "0.1" ≈ "0.10" → True
            "10" ≈ "10.0" → True
            "0.1%" ≈ "0.10%" → True
        """
        try:
            # Strip % signs
            clean1 = num1.rstrip('%')
            clean2 = num2.rstrip('%')

            val1 = float(clean1)
            val2 = float(clean2)

            return abs(val1 - val2) < tolerance
        except ValueError:
            return False

    def inject_citations_in_findings(
        self,
        findings: List[Dict[str, Any]],
        source_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Inject citations into all findings in a list.

        Args:
            findings: List of finding dicts with 'analysis', 'summary', etc.
            source_data: Dictionary of QueryResult objects

        Returns:
            Updated findings with citations injected
        """
        updated_findings = []

        for finding in findings:
            updated_finding = finding.copy()

            # Inject into analysis field
            if 'analysis' in updated_finding:
                updated_finding['analysis'] = self.inject_citations(
                    updated_finding['analysis'],
                    source_data
                )

            # Inject into summary field
            if 'summary' in updated_finding:
                updated_finding['summary'] = self.inject_citations(
                    updated_finding['summary'],
                    source_data
                )

            # Inject into recommendations (list of strings)
            if 'recommendations' in updated_finding and isinstance(updated_finding['recommendations'], list):
                updated_finding['recommendations'] = [
                    self.inject_citations(rec, source_data)
                    for rec in updated_finding['recommendations']
                ]

            updated_findings.append(updated_finding)

        return updated_findings
