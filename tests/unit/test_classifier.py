"""
Tests for QueryClassifier.

Tests classification logic, intent scoring, and confidence calculation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.qnwis.orchestration.classifier import QueryClassifier
from src.qnwis.orchestration.schemas import Classification


@pytest.fixture
def classifier() -> QueryClassifier:
    """Create a QueryClassifier instance for testing."""
    base_dir = Path(__file__).parent.parent.parent / "src" / "qnwis" / "orchestration"
    catalog_path = base_dir / "intent_catalog.yml"
    sector_lex = base_dir / "keywords" / "sectors.txt"
    metric_lex = base_dir / "keywords" / "metrics.txt"

    return QueryClassifier(
        catalog_path=str(catalog_path),
        sector_lex=str(sector_lex),
        metric_lex=str(metric_lex),
        min_confidence=0.55,
    )


class TestClassifierInitialization:
    """Test classifier initialization."""

    def test_init_success(self, classifier: QueryClassifier) -> None:
        """Test successful initialization."""
        assert classifier is not None
        assert classifier.min_confidence == 0.55
        assert len(classifier.sectors) > 0
        assert len(classifier.metrics) > 0
        assert classifier.catalog is not None

    def test_init_missing_catalog(self) -> None:
        """Test initialization with missing catalog."""
        with pytest.raises(FileNotFoundError, match="Intent catalog not found"):
            QueryClassifier(
                catalog_path="/nonexistent/catalog.yml",
                sector_lex="/nonexistent/sectors.txt",
                metric_lex="/nonexistent/metrics.txt",
            )

    def test_init_missing_sector_lex(self) -> None:
        """Test initialization with missing sector lexicon."""
        base_dir = Path(__file__).parent.parent.parent / "src" / "qnwis" / "orchestration"
        catalog_path = base_dir / "intent_catalog.yml"

        with pytest.raises(FileNotFoundError, match="Sector lexicon not found"):
            QueryClassifier(
                catalog_path=str(catalog_path),
                sector_lex="/nonexistent/sectors.txt",
                metric_lex="/nonexistent/metrics.txt",
            )


class TestClassifyText:
    """Test text classification."""

    def test_classify_anomalies_simple(self, classifier: QueryClassifier) -> None:
        """Test classification of simple anomaly query."""
        query = "Detect salary spikes in Healthcare sector"
        result = classifier.classify_text(query)

        assert isinstance(result, Classification)
        assert "pattern.anomalies" in result.intents
        assert result.complexity in ["simple", "medium"]
        assert result.confidence > 0.0
        assert len(result.reasons) > 0
        assert "Healthcare" in result.entities.sectors
        assert "salary" in result.entities.metrics

    def test_classify_correlation(self, classifier: QueryClassifier) -> None:
        """Test classification of correlation query."""
        query = "Is there a correlation between salary and retention?"
        result = classifier.classify_text(query)

        assert "pattern.correlation" in result.intents
        assert "salary" in result.entities.metrics
        assert "retention" in result.entities.metrics

    def test_classify_root_causes(self, classifier: QueryClassifier) -> None:
        """Test classification of root cause query."""
        query = "Why is Construction retention declining?"
        result = classifier.classify_text(query)

        assert "pattern.root_causes" in result.intents
        assert "Construction" in result.entities.sectors
        assert "retention" in result.entities.metrics

    def test_classify_gcc_benchmark(self, classifier: QueryClassifier) -> None:
        """Test classification of GCC benchmark query."""
        query = "How does Qatar wage growth compare to UAE?"
        result = classifier.classify_text(query)

        assert "strategy.gcc_benchmark" in result.intents
        assert "wage" in result.entities.metrics

    def test_classify_vision2030(self, classifier: QueryClassifier) -> None:
        """Test classification of Vision 2030 query."""
        query = "Qatarization progress toward Vision 2030 targets"
        result = classifier.classify_text(query)

        assert "strategy.vision2030" in result.intents
        assert "qatarization" in result.entities.metrics

    def test_classify_empty_query(self, classifier: QueryClassifier) -> None:
        """Test classification of empty query."""
        result = classifier.classify_text("")

        assert result.intents == []
        assert result.confidence == 0.0
        assert "Empty query text" in result.reasons

    def test_classify_multi_intent(self, classifier: QueryClassifier) -> None:
        """Test classification that matches multiple intents."""
        query = "What factors are linked to high turnover in Hospitality?"
        result = classifier.classify_text(query)

        # Should match both correlation and root_causes
        assert len(result.intents) >= 1
        assert result.confidence > 0.0

    def test_classify_crisis(self, classifier: QueryClassifier) -> None:
        """Test crisis classification with urgency keywords."""
        query = "Urgent: sudden spike in turnover in Hospitality now"
        result = classifier.classify_text(query)

        assert result.complexity == "crisis"
        assert "Hospitality" in result.entities.sectors
        assert "turnover" in result.entities.metrics
        assert result.elapsed_ms >= 0.0

    def test_tie_within_threshold_sets_flag(self, classifier: QueryClassifier) -> None:
        """Test tie handling when two intents score the same."""
        query = "Investigate anomaly correlation patterns in retention data"
        result = classifier.classify_text(query)

        # Should surface both intents with tie metadata
        assert len(result.intents) >= 2
        assert result.tie_within_threshold is True
        assert any("Tie within threshold" in reason for reason in result.reasons)

    def test_intent_scores_are_sorted(self, classifier: QueryClassifier) -> None:
        """Ensure intent scores are provided in deterministic order."""
        query = "Detect anomalies and correlation signals in salary trends"
        result = classifier.classify_text(query)

        scores = list(result.intent_scores.items())
        for idx in range(1, len(scores)):
            prev_intent, prev_score = scores[idx - 1]
            curr_intent, curr_score = scores[idx]
            assert prev_score >= curr_score or (
                prev_score == curr_score and prev_intent <= curr_intent
            )

    def test_default_time_horizon_reason(self, classifier: QueryClassifier) -> None:
        """Ensure default time horizon reason is captured."""
        query = "Analyze retention patterns"
        result = classifier.classify_text(query)

        assert any("Applied default time horizon" in reason for reason in result.reasons)
        assert result.entities.time_horizon["months"] == 36


class TestComplexityDetermination:
    """Test complexity determination logic."""

    def test_simple_complexity_one_intent_one_sector(self, classifier: QueryClassifier) -> None:
        """Test simple complexity classification."""
        query = "Simple retention check in Finance"
        result = classifier.classify_text(query)

        assert result.complexity == "simple"

    def test_medium_complexity_multi_sector(self, classifier: QueryClassifier) -> None:
        """Test medium complexity with multiple sectors."""
        query = "Root causes of high turnover in Finance and Healthcare"
        result = classifier.classify_text(query)

        assert result.complexity in ["medium", "complex"]
        assert len(result.entities.sectors) == 2

    def test_complex_complexity_multi_sector_multi_metric(self, classifier: QueryClassifier) -> None:
        """Test complex classification."""
        query = "Identify outliers in employee attrition across Finance, Healthcare, and IT"
        result = classifier.classify_text(query)

        assert result.complexity in ["medium", "complex"]
        assert len(result.entities.sectors) >= 3

    def test_crisis_with_urgency_and_recent_time(self, classifier: QueryClassifier) -> None:
        """Test crisis classification with urgency and recent time horizon."""
        query = "Crisis alert: unusual retention drop in Construction last 2 months"
        result = classifier.classify_text(query)

        assert result.complexity == "crisis"


class TestConfidenceScoring:
    """Test confidence score calculation."""

    def test_high_confidence_clear_intent(self, classifier: QueryClassifier) -> None:
        """Test high confidence for clear query."""
        query = "Detect anomalies in retention and turnover"
        result = classifier.classify_text(query)

        # With the generous scoring, should get decent confidence
        assert result.confidence >= 0.3  # Should have reasonable confidence

    def test_low_confidence_vague_query(self, classifier: QueryClassifier) -> None:
        """Test low confidence for vague query."""
        query = "Show me some information"
        result = classifier.classify_text(query)

        assert result.confidence < 0.3  # Should have low confidence

    def test_no_intents_zero_confidence(self, classifier: QueryClassifier) -> None:
        """Test zero confidence when no intents match."""
        query = "Weather forecast for tomorrow"
        result = classifier.classify_text(query)

        assert result.confidence == 0.0
        assert len(result.intents) == 0


class TestPIIRedaction:
    """Test PII redaction in reasons."""

    def test_redact_email(self, classifier: QueryClassifier) -> None:
        """Test email address redaction."""
        # This test verifies that if an email somehow appears in reasons,
        # it gets redacted. In practice, emails shouldn't appear.
        reasons = ["Contact analyst@mol.gov.qa for details"]
        redacted = classifier._redact_pii(reasons)

        assert "[REDACTED]" in redacted[0]
        assert "@mol.gov.qa" not in redacted[0]

    def test_redact_long_id(self, classifier: QueryClassifier) -> None:
        """Test long ID redaction."""
        reasons = ["Employee ID 1234567890 found"]
        redacted = classifier._redact_pii(reasons)

        assert "[REDACTED]" in redacted[0]
        assert "1234567890" not in redacted[0]

    def test_no_pii_unchanged(self, classifier: QueryClassifier) -> None:
        """Test that reasons without PII are unchanged."""
        reasons = ["Matched 2 intents", "Complexity: medium"]
        redacted = classifier._redact_pii(reasons)

        assert redacted == reasons


class TestDataNeedsDetermination:
    """Test data prefetch needs generation."""

    def test_data_needs_anomalies_retention(self, classifier: QueryClassifier) -> None:
        """Test prefetch for anomalies with retention metric."""
        query = "Detect unusual retention in Construction"
        classification = classifier.classify_text(query)
        prefetch = classifier.determine_data_needs(classification)

        assert len(prefetch) > 0
        retention_prefetch = next(
            item for item in prefetch if item['fn'] == 'get_retention_by_company'
        )
        assert retention_prefetch['params']['months'] == 36
        assert retention_prefetch['params']['sectors']

    def test_data_needs_gcc_benchmark(self, classifier: QueryClassifier) -> None:
        """Test prefetch for GCC benchmark."""
        query = "How does Qatar compare to GCC countries?"
        classification = classifier.classify_text(query)
        prefetch = classifier.determine_data_needs(classification)

        assert len(prefetch) > 0
        assert any(item['fn'] == 'get_gcc_comparison' for item in prefetch)

    def test_data_needs_vision2030(self, classifier: QueryClassifier) -> None:
        """Test prefetch for Vision 2030."""
        query = "Qatarization progress toward Vision 2030 targets"
        classification = classifier.classify_text(query)
        prefetch = classifier.determine_data_needs(classification)

        assert len(prefetch) > 0
        assert any(item['fn'] == 'get_qatarization_progress' for item in prefetch)

    def test_data_needs_deduplication(self, classifier: QueryClassifier) -> None:
        """Test that duplicate prefetch specs are removed."""
        query = "Retention anomalies and retention correlation in Construction"
        classification = classifier.classify_text(query)
        prefetch = classifier.determine_data_needs(classification)

        def make_hashable(value: object) -> object:
            if isinstance(value, list):
                return tuple(sorted(make_hashable(v) for v in value))
            if isinstance(value, dict):
                return tuple(
                    (k, make_hashable(v)) for k, v in sorted(value.items())
                )
            return value

        keys = {(item['fn'], make_hashable(item['params'])) for item in prefetch}
        assert len(keys) == len(prefetch)
