"""
Verified Fact Validator - Ensures agents cite real data

This module validates that agent claims match extracted facts.
Prevents fabrication by rejecting claims that don't match source data.

Domain-agnostic: Works with any extracted fact structure.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class FactValidationResult:
    """Result of validating an agent claim."""
    valid: bool
    claim_text: str
    claimed_value: Optional[str]
    closest_fact: Optional[Dict[str, Any]]
    discrepancy: Optional[str]
    confidence: float  # 0-1, how confident we are in the validation


class FactValidator:
    """
    Validates agent claims against extracted facts.
    
    Prevents data fabrication by:
    1. Tracking all verified facts from extraction
    2. Parsing agent claims to extract metrics and values
    3. Comparing claims against known facts
    4. Flagging discrepancies or fabrications
    """
    
    def __init__(self, extracted_facts: List[Dict[str, Any]] = None):
        """Initialize with extracted facts."""
        self.facts = {}
        self.fact_index = {}  # For fast lookup
        
        if extracted_facts:
            self.load_facts(extracted_facts)
    
    def load_facts(self, facts: List[Dict[str, Any]]) -> int:
        """
        Load and index extracted facts.
        
        Args:
            facts: List of fact dicts with metric, value, source, year
            
        Returns:
            Number of facts loaded
        """
        count = 0
        for fact in facts:
            if isinstance(fact, dict):
                # Extract key fields
                metric = fact.get("metric", fact.get("indicator", ""))
                value = fact.get("value", "")
                source = fact.get("source", "")
                year = fact.get("year", fact.get("period", ""))
                
                if metric and value:
                    fact_id = f"{metric}_{year}".lower().replace(" ", "_")
                    self.facts[fact_id] = {
                        "metric": metric,
                        "value": value,
                        "source": source,
                        "year": year,
                        "original": fact
                    }
                    
                    # Index by keywords for fast lookup
                    keywords = self._extract_keywords(metric)
                    for kw in keywords:
                        if kw not in self.fact_index:
                            self.fact_index[kw] = []
                        self.fact_index[kw].append(fact_id)
                    
                    count += 1
        
        logger.info(f"Loaded {count} verified facts for validation")
        return count
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for indexing."""
        # Remove common words
        stopwords = {"the", "a", "an", "of", "in", "for", "to", "and", "or", "is", "are", "was", "were"}
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in stopwords and len(w) > 2]
    
    def validate_claim(self, claim_text: str) -> FactValidationResult:
        """
        Validate a claim made by an agent.
        
        Args:
            claim_text: The agent's claim (e.g., "ICT employment is 4.8% among nationals")
            
        Returns:
            FactValidationResult with validation status
        """
        # Extract claimed value
        claimed_value = self._extract_value_from_claim(claim_text)
        
        # Find closest matching fact
        closest_fact, similarity = self._find_closest_fact(claim_text)
        
        # Determine if valid
        if closest_fact is None:
            return FactValidationResult(
                valid=False,
                claim_text=claim_text,
                claimed_value=claimed_value,
                closest_fact=None,
                discrepancy="No matching fact found in extracted data",
                confidence=0.5
            )
        
        # Compare values
        if claimed_value:
            fact_value = str(closest_fact.get("value", ""))
            value_match = self._values_match(claimed_value, fact_value)
            
            if not value_match:
                return FactValidationResult(
                    valid=False,
                    claim_text=claim_text,
                    claimed_value=claimed_value,
                    closest_fact=closest_fact,
                    discrepancy=f"Claimed '{claimed_value}' but fact shows '{fact_value}'",
                    confidence=similarity
                )
        
        return FactValidationResult(
            valid=True,
            claim_text=claim_text,
            claimed_value=claimed_value,
            closest_fact=closest_fact,
            discrepancy=None,
            confidence=similarity
        )
    
    def _extract_value_from_claim(self, text: str) -> Optional[str]:
        """Extract numeric/percentage value from claim text."""
        # Percentages
        pct_match = re.search(r'(\d+\.?\d*)\s*%', text)
        if pct_match:
            return f"{pct_match.group(1)}%"
        
        # Currency amounts
        currency_match = re.search(r'[\$£€QR]\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(billion|million|B|M)?', text, re.IGNORECASE)
        if currency_match:
            return currency_match.group(0)
        
        # Plain numbers
        num_match = re.search(r'\b(\d{1,3}(?:,\d{3})+|\d+)\b', text)
        if num_match:
            return num_match.group(1)
        
        return None
    
    def _find_closest_fact(self, claim_text: str) -> Tuple[Optional[Dict], float]:
        """Find the fact most similar to the claim."""
        claim_keywords = self._extract_keywords(claim_text)
        
        # Find candidate facts via keyword index
        candidates = set()
        for kw in claim_keywords:
            if kw in self.fact_index:
                candidates.update(self.fact_index[kw])
        
        if not candidates:
            # Fall back to all facts
            candidates = set(self.facts.keys())
        
        # Find best match by text similarity
        best_fact = None
        best_similarity = 0.0
        
        for fact_id in candidates:
            fact = self.facts.get(fact_id, {})
            fact_text = f"{fact.get('metric', '')} {fact.get('value', '')}"
            similarity = SequenceMatcher(None, claim_text.lower(), fact_text.lower()).ratio()
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_fact = fact
        
        return best_fact, best_similarity
    
    def _values_match(self, claimed: str, actual: str) -> bool:
        """Check if claimed value matches actual value (with tolerance)."""
        # Clean values
        claimed_clean = re.sub(r'[^\d.]', '', claimed)
        actual_clean = re.sub(r'[^\d.]', '', actual)
        
        try:
            claimed_num = float(claimed_clean)
            actual_num = float(actual_clean)
            
            # Allow 10% tolerance
            if actual_num == 0:
                return claimed_num == 0
            
            diff_pct = abs(claimed_num - actual_num) / actual_num
            return diff_pct < 0.10  # 10% tolerance
        except (ValueError, ZeroDivisionError):
            # String comparison
            return claimed_clean == actual_clean
    
    def validate_agent_turn(self, turn_content: str) -> List[FactValidationResult]:
        """
        Validate all claims in an agent's turn.
        
        Returns list of validation results for each claim found.
        """
        results = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]', turn_content)
        
        for sentence in sentences:
            # Check if sentence contains a numeric claim
            if self._extract_value_from_claim(sentence):
                result = self.validate_claim(sentence.strip())
                results.append(result)
        
        return results
    
    def get_validation_summary(self, results: List[FactValidationResult]) -> Dict[str, Any]:
        """Generate summary of validation results."""
        total = len(results)
        valid = sum(1 for r in results if r.valid)
        invalid = total - valid
        
        return {
            "total_claims": total,
            "valid_claims": valid,
            "invalid_claims": invalid,
            "fabrication_rate": invalid / total if total > 0 else 0,
            "discrepancies": [
                {"claim": r.claim_text, "issue": r.discrepancy}
                for r in results if not r.valid
            ]
        }
    
    def generate_fact_injection_prompt(self, max_facts: int = 50) -> str:
        """
        Generate a prompt section listing verified facts for agents.
        
        This is injected into agent prompts to give them the ONLY
        facts they're allowed to cite.
        """
        lines = [
            "## VERIFIED FACTS DATABASE",
            "You may ONLY cite statistics from this list. Do NOT invent numbers.",
            ""
        ]
        
        for i, (fact_id, fact) in enumerate(list(self.facts.items())[:max_facts]):
            metric = fact.get("metric", "Unknown metric")
            value = fact.get("value", "N/A")
            source = fact.get("source", "Unknown source")
            year = fact.get("year", "")
            
            lines.append(f"[FACT {i+1}] {metric}: {value} ({year}) — Source: {source}")
        
        lines.append("")
        lines.append("CITATION RULE: When citing a fact, reference it as [FACT N]")
        
        return "\n".join(lines)

