"""
Query Classification for QNWIS.

Deterministic, dependency-light classifier that maps natural language queries
to intents, complexity levels, and entities using lexicons and pattern matching.
No LLM calls, no database access, no HTTP requests.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional

import yaml

from .schemas import Classification, Complexity, Entities

logger = logging.getLogger(__name__)

# PII patterns to redact from reasons
PII_PATTERNS = [
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # emails
    re.compile(r'\b\d{10,}\b'),  # 10+ digit IDs
    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # SSN-like patterns
]

DEFAULT_HORIZON_MONTHS = 36
TIE_DELTA_THRESHOLD = 0.05


class QueryClassifier:
    """
    Deterministic, dependency-light classifier for QNWIS.

    Uses lexicons + intent_catalog.yml to map free text -> intents, complexity, entities.
    No direct DB/HTTP calls (classification does not read LMIS).

    Attributes:
        catalog: Loaded intent catalog with patterns and keywords
        sectors: Set of known sector terms
        metrics: Set of known metric terms
        min_confidence: Minimum confidence threshold for classification
    """

    def __init__(
        self,
        catalog_path: str,
        sector_lex: str,
        metric_lex: str,
        min_confidence: float = 0.55,
    ) -> None:
        """
        Initialize the classifier with lexicons and catalog.

        Args:
            catalog_path: Path to intent_catalog.yml
            sector_lex: Path to sectors.txt lexicon
            metric_lex: Path to metrics.txt lexicon
            min_confidence: Minimum confidence threshold (default 0.55)

        Raises:
            FileNotFoundError: If any required file is missing
            ValueError: If catalog is invalid
        """
        self.min_confidence = min_confidence

        # Load catalog
        catalog_file = Path(catalog_path)
        if not catalog_file.exists():
            raise FileNotFoundError(f"Intent catalog not found: {catalog_path}")

        with open(catalog_file, 'r', encoding='utf-8') as f:
            self.catalog = yaml.safe_load(f)

        if not self.catalog:
            raise ValueError(f"Invalid or empty catalog: {catalog_path}")

        # Load sector lexicon
        sector_file = Path(sector_lex)
        if not sector_file.exists():
            raise FileNotFoundError(f"Sector lexicon not found: {sector_lex}")

        with open(sector_file, 'r', encoding='utf-8') as f:
            self.sectors = {line.strip().lower() for line in f if line.strip()}

        # Load metric lexicon
        metric_file = Path(metric_lex)
        if not metric_file.exists():
            raise FileNotFoundError(f"Metric lexicon not found: {metric_lex}")

        with open(metric_file, 'r', encoding='utf-8') as f:
            self.metrics = {line.strip().lower() for line in f if line.strip()}

        # Compile time horizon patterns
        self._compile_time_patterns()

        # Compile urgency keywords
        self.urgency_keywords = {
            kw.lower() for kw in self.catalog.get('urgency_keywords', [])
        }

        logger.info(
            "QueryClassifier initialized: %d sectors, %d metrics, %d intents",
            len(self.sectors),
            len(self.metrics),
            len([k for k in self.catalog.keys() if '.' in k]),
        )

    def _compile_time_patterns(self) -> None:
        """Compile regex patterns for time horizon extraction."""
        self.time_patterns_relative = []
        self.time_patterns_absolute = []

        time_config = self.catalog.get('time_patterns', {})

        # Relative patterns
        for pattern_def in time_config.get('relative', []):
            compiled = re.compile(pattern_def['pattern'], re.IGNORECASE)
            entry = {
                'regex': compiled,
                'unit_group': pattern_def.get('unit_group'),
                'value_group': pattern_def.get('value_group'),
            }
            if 'unit_override' in pattern_def:
                entry['unit_override'] = pattern_def['unit_override']
            if 'value_multiplier' in pattern_def:
                entry['value_multiplier'] = pattern_def['value_multiplier']
            self.time_patterns_relative.append(entry)

        # Absolute patterns
        for pattern_def in time_config.get('absolute', []):
            compiled = re.compile(pattern_def['pattern'], re.IGNORECASE)
            entry = {'regex': compiled, 'type': pattern_def['type']}
            if 'months' in pattern_def:
                entry['months'] = pattern_def['months']
            if 'quarter_length_months' in pattern_def:
                entry['quarter_length_months'] = pattern_def['quarter_length_months']
            self.time_patterns_absolute.append(entry)

    def extract_entities(self, text: str) -> Entities:
        """
        Extract entities using dictionary+regex NER.

        Args:
            text: Input query text

        Returns:
            Entities object with sectors, metrics, and time horizon
        """
        text_lower = text.lower()

        # Extract sectors
        found_sectors = []
        for sector in self.sectors:
            if sector in text_lower:
                # Store original case if possible
                found_sectors.append(sector.title())

        # Extract metrics
        found_metrics = []
        for metric in self.metrics:
            if metric in text_lower:
                found_metrics.append(metric)

        # Extract time horizon
        time_horizon = self._extract_time_horizon(text)
        if time_horizon is None:
            time_horizon = {
                'type': 'default',
                'unit': 'month',
                'value': DEFAULT_HORIZON_MONTHS,
                'months': DEFAULT_HORIZON_MONTHS,
                'source': 'default',
            }

        return Entities(
            sectors=sorted(set(found_sectors)),
            metrics=sorted(set(found_metrics)),
            time_horizon=time_horizon,
        )

    def _extract_time_horizon(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract time horizon from text using regex patterns.

        Args:
            text: Input query text

        Returns:
            Dictionary with time horizon info or None
        """
        # Try relative patterns first
        for pattern_def in self.time_patterns_relative:
            match = pattern_def['regex'].search(text)
            if match:
                value_group = pattern_def.get('value_group')
                unit_group = pattern_def.get('unit_group')
                raw_value = int(match.group(value_group)) if value_group is not None else 0
                multiplier = pattern_def.get('value_multiplier', 1)
                value = raw_value * multiplier
                unit = pattern_def.get('unit_override') or (
                    match.group(unit_group) if unit_group is not None else 'month'
                )
                return {
                    'type': 'relative',
                    'value': value,
                    'unit': unit,
                    'months': self._convert_to_months(value, unit),
                }

        # Try absolute patterns
        for pattern_def in self.time_patterns_absolute:
            match = pattern_def['regex'].search(text)
            if match:
                if pattern_def['type'] == 'year_range':
                    start = int(match.group(1))
                    end = int(match.group(2))
                    return {
                        'type': 'absolute',
                        'start_year': start,
                        'end_year': end,
                        'months': (end - start + 1) * 12,
                    }
                elif pattern_def['type'] == 'year_start':
                    year = int(match.group(1))
                    return {
                        'type': 'absolute',
                        'start_year': year,
                        'end_year': None,
                    }
                elif pattern_def['type'] == 'year_single':
                    year = int(match.group(1))
                    return {
                        'type': 'absolute',
                        'year': year,
                        'months': 12,
                    }
                elif pattern_def['type'] == 'quarter':
                    quarter = int(match.group(1))
                    year = int(match.group(2))
                    months = pattern_def.get('quarter_length_months', 3)
                    return {
                        'type': 'absolute',
                        'year': year,
                        'quarter': quarter,
                        'months': months,
                    }
                elif pattern_def['type'] == 'year_single_plain':
                    year = int(match.group(1))
                    return {
                        'type': 'absolute',
                        'year': year,
                        'months': pattern_def.get('months', 12),
                    }

        return None

    def _convert_to_months(self, value: int, unit: str) -> int:
        """
        Convert time value to months.

        Args:
            value: Numeric value
            unit: Time unit (day, week, month, year)

        Returns:
            Approximate number of months
        """
        unit_lower = unit.lower()
        if 'year' in unit_lower:
            return value * 12
        elif 'month' in unit_lower:
            return value
        elif 'quarter' in unit_lower:
            return max(1, value * 3)
        elif 'week' in unit_lower:
            return max(1, value // 4)
        elif 'day' in unit_lower:
            return max(1, value // 30)
        return value

    def classify_text(self, text: str) -> Classification:
        """
        Classify query text into intents, complexity, and entities.

        Args:
            text: Natural language query

        Returns:
            Classification with intents, complexity, entities, confidence, reasons
        """
        start_time = perf_counter()

        if not text or not text.strip():
            empty_classification = Classification(
                intents=[],
                complexity="simple",
                entities=Entities(),
                confidence=0.0,
                reasons=["Empty query text"],
                intent_scores={},
                elapsed_ms=(perf_counter() - start_time) * 1000,
                tie_within_threshold=False,
            )
            logger.info(
                "Classified empty query: confidence=0.00 complexity=simple elapsed_ms=%.2f",
                empty_classification.elapsed_ms,
            )
            return empty_classification

        text_lower = text.lower()
        reasons = []

        # Extract entities first
        entities = self.extract_entities(text)
        if entities.time_horizon and entities.time_horizon.get('source') == 'default':
            reasons.append(f"Applied default time horizon of {DEFAULT_HORIZON_MONTHS} months")

        # Score each intent
        intent_scores: Dict[str, float] = {}

        for intent_id, intent_config in self.catalog.items():
            if '.' not in intent_id:
                continue  # Skip non-intent entries

            score = self._score_intent(text_lower, intent_config)
            if score > 0:
                intent_scores[intent_id] = score

        # Filter to top intents above threshold
        threshold = 0.3  # Individual intent threshold
        scored_intents = sorted(
            intent_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )
        matched_intents = [
            intent for intent, score in scored_intents if score >= threshold
        ]
        ordered_scores = {intent: score for intent, score in scored_intents}

        # Calculate overall confidence
        tie_within_threshold = False
        if matched_intents:
            # Confidence is normalized max score
            top_intent = matched_intents[0]
            max_score = ordered_scores[top_intent]
            # More generous confidence calculation: normalize assuming max ~3 keywords
            confidence = min(1.0, max_score / 3.0)
            # Boost confidence if entities are present
            if entities.sectors or entities.metrics:
                confidence = min(1.0, confidence * 1.2)
            reasons.append(f"Matched {len(matched_intents)} intent(s)")
            for intent in matched_intents[:3]:
                reasons.append(f"{intent}: {ordered_scores[intent]:.2f}")

            if len(matched_intents) >= 2:
                first_score = ordered_scores[matched_intents[0]]
                second_score = ordered_scores[matched_intents[1]]
                delta = abs(first_score - second_score)
                if delta <= TIE_DELTA_THRESHOLD:
                    tie_within_threshold = True
                    reasons.append(
                        f"Tie within threshold: {matched_intents[0]} vs {matched_intents[1]} (delta={delta:.2f})"
                    )
        else:
            confidence = 0.0
            reasons.append("No intents matched above threshold")

        # Determine complexity
        complexity = self._determine_complexity(
            text_lower, matched_intents, entities
        )
        reasons.append(f"Complexity: {complexity}")

        # Redact PII from reasons
        reasons = self._redact_pii(reasons)

        elapsed_ms = (perf_counter() - start_time) * 1000

        classification = Classification(
            intents=matched_intents,
            complexity=complexity,
            entities=entities,
            confidence=confidence,
            reasons=reasons,
            intent_scores=ordered_scores,
            elapsed_ms=elapsed_ms,
            tie_within_threshold=tie_within_threshold,
        )

        logger.info(
            "Classified query: intents=%s confidence=%.2f complexity=%s elapsed_ms=%.2f intent_scores=%s",
            classification.intents,
            classification.confidence,
            classification.complexity,
            classification.elapsed_ms,
            classification.intent_scores,
        )

        return classification

    def _score_intent(self, text_lower: str, intent_config: Dict[str, Any]) -> float:
        """
        Score how well text matches an intent.

        Args:
            text_lower: Lowercased query text
            intent_config: Intent configuration from catalog

        Returns:
            Score (higher is better match)
        """
        score = 0.0

        # Check keywords
        keywords = intent_config.get('keywords', [])
        for keyword in keywords:
            if keyword.lower() in text_lower:
                score += 1.0

        return score

    def _determine_complexity(
        self,
        text_lower: str,
        matched_intents: List[str],
        entities: Entities,
    ) -> Complexity:
        """
        Determine query complexity based on features.

        Rules:
        - simple: one intent, one sector, no external series, horizon <= 24 months
        - medium: <=3 intents or needs 2 LMIS datasets
        - complex: >=4 intents or multi-sector + synthesis
        - crisis: urgency lexicon + fresh horizon <= 3 months

        Args:
            text_lower: Lowercased query text
            matched_intents: List of matched intent IDs
            entities: Extracted entities

        Returns:
            Complexity level
        """
        # Check for urgency keywords (crisis)
        has_urgency = any(kw in text_lower for kw in self.urgency_keywords)

        # Check time horizon
        time_horizon = entities.time_horizon
        horizon_months = time_horizon.get('months', 24) if time_horizon else 24

        # Crisis detection
        if has_urgency and horizon_months <= 3:
            return "crisis"

        # Calculate complexity score
        score = 0

        # Intent count
        intent_count = len(matched_intents)
        if intent_count == 1:
            score += 10
        elif intent_count > 1:
            score += 20

        # Sector count
        sector_count = len(entities.sectors)
        if sector_count == 1:
            score += 5
        elif sector_count > 1:
            score += 15

        # Time horizon width
        if horizon_months <= 24:
            score += 5
        elif horizon_months <= 48:
            score += 10
        else:
            score += 15

        # Urgency
        if has_urgency:
            score += 30

        # Metric count
        metric_count = len(entities.metrics)
        if metric_count <= 2:
            score += 5
        elif metric_count <= 4:
            score += 10
        else:
            score += 15

        # Map score to complexity
        if score <= 20:
            return "simple"
        elif score <= 40:
            return "medium"
        elif score <= 60:
            return "complex"
        else:
            return "crisis"

    def _redact_pii(self, reasons: List[str]) -> List[str]:
        """
        Redact PII patterns from reason strings.

        Args:
            reasons: List of reason strings

        Returns:
            List with PII redacted
        """
        redacted = []
        for reason in reasons:
            for pattern in PII_PATTERNS:
                reason = pattern.sub('[REDACTED]', reason)
            redacted.append(reason)
        return redacted

    def _should_include_prefetch(
        self,
        entry: Dict[str, Any],
        classification: Classification,
    ) -> bool:
        """
        Determine if a prefetch entry should be included.

        Args:
            entry: Prefetch configuration entry
            classification: Classification result

        Returns:
            True if the prefetch entry should be used
        """
        metrics_lower = {m.lower() for m in classification.entities.metrics}
        sectors_present = bool(classification.entities.sectors)

        metrics_any = entry.get('when_metrics_any')
        if metrics_any:
            if not metrics_lower.intersection({m.lower() for m in metrics_any}):
                return False

        if entry.get('require_metrics') and not metrics_lower:
            return False

        if entry.get('require_sectors') and not sectors_present:
            return False

        min_confidence = entry.get('min_confidence')
        if isinstance(min_confidence, (int, float)):
            if classification.confidence < float(min_confidence):
                return False

        complexity_list = entry.get('when_complexity_in')
        if complexity_list:
            allowed = {level.lower() for level in complexity_list}
            if classification.complexity.lower() not in allowed:
                return False

        return True

    def _resolve_prefetch_params(
        self,
        template: Dict[str, Any],
        classification: Classification,
    ) -> Dict[str, Any]:
        """
        Resolve a param template into concrete values.

        Args:
            template: Template dictionary with optional tokens
            classification: Classification result

        Returns:
            Resolved params dictionary
        """
        resolved: Dict[str, Any] = {}
        for key, value in template.items():
            resolved[key] = self._resolve_prefetch_value(value, classification)
        return resolved

    def _resolve_prefetch_value(
        self,
        value: Any,
        classification: Classification,
    ) -> Any:
        """
        Resolve a single template value.

        Args:
            value: Template value
            classification: Classification result

        Returns:
            Resolved value
        """
        if isinstance(value, str) and value.startswith('@'):
            return self._prefetch_token(value[1:], classification)
        if isinstance(value, dict):
            return {
                key: self._resolve_prefetch_value(val, classification)
                for key, val in value.items()
            }
        if isinstance(value, list):
            return [
                self._resolve_prefetch_value(item, classification)
                for item in value
            ]
        return value

    def _prefetch_token(self, token: str, classification: Classification) -> Any:
        """
        Resolve a prefetch token to a concrete value.

        Args:
            token: Token name without prefix
            classification: Classification result

        Returns:
            Resolved value for the token
        """
        token_lower = token.lower()
        entities = classification.entities
        if token_lower == 'sectors':
            return entities.sectors
        if token_lower == 'metrics':
            return entities.metrics
        if token_lower in {'months', 'horizon_months'}:
            horizon = entities.time_horizon or {}
            months = horizon.get('months')
            return months if months is not None else DEFAULT_HORIZON_MONTHS
        if token_lower == 'primary_intent':
            return classification.intents[0] if classification.intents else None
        if token_lower == 'complexity':
            return classification.complexity
        if token_lower == 'confidence':
            return classification.confidence
        return None

    def determine_data_needs(self, classification: Classification) -> List[Dict[str, Any]]:
        """
        Translate classification into deterministic prefetch hints.

        Args:
            classification: Classification result

        Returns:
            List of prefetch specifications (function names + params)
        """
        prefetch: List[Dict[str, Any]] = []

        for intent in classification.intents:
            intent_config = self.catalog.get(intent, {})
            for entry in intent_config.get('prefetch', []):
                if 'fn' not in entry:
                    continue
                if not self._should_include_prefetch(entry, classification):
                    continue

                params_template = entry.get('params', {})
                resolved_params = self._resolve_prefetch_params(params_template, classification)

                prefetch_entry: Dict[str, Any] = {
                    'fn': entry['fn'],
                    'params': resolved_params,
                }
                if 'description' in entry:
                    prefetch_entry['description'] = entry['description']

                prefetch.append(prefetch_entry)

        # Deduplicate by fn+params (handle list values in params)
        seen = set()
        unique_prefetch = []
        for item in prefetch:
            # Convert params to hashable form
            def _make_hashable(value: Any) -> Any:
                if isinstance(value, list):
                    return tuple(_make_hashable(v) for v in value)
                if isinstance(value, dict):
                    return tuple(
                        (k, _make_hashable(v))
                        for k, v in sorted(value.items())
                    )
                return value

            hashable_params = tuple(
                (k, _make_hashable(v))
                for k, v in sorted(item['params'].items())
            )
            key = (item['fn'], hashable_params)
            if key not in seen:
                seen.add(key)
                unique_prefetch.append(item)

        return unique_prefetch
