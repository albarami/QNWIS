"""
Integration tests using routing_samples.jsonl.

Validates classification against expected results for 40 sample queries.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.qnwis.orchestration.classifier import QueryClassifier


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


@pytest.fixture
def routing_samples() -> list[dict]:
    """Load routing samples from JSONL file."""
    base_dir = Path(__file__).parent.parent.parent / "src" / "qnwis" / "orchestration"
    samples_file = base_dir / "examples" / "routing_samples.jsonl"

    samples = []
    with open(samples_file, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    return samples


class TestRoutingSamples:
    """Test classification against routing samples."""

    def test_all_samples_classify(self, classifier: QueryClassifier, routing_samples: list[dict]) -> None:
        """Test that all samples can be classified."""
        for sample in routing_samples:
            query = sample["query"]
            result = classifier.classify_text(query)

            # Should produce a classification
            assert result is not None
            assert isinstance(result.intents, list)
            assert isinstance(result.complexity, str)
            assert 0.0 <= result.confidence <= 1.0

    def test_intent_matching(self, classifier: QueryClassifier, routing_samples: list[dict]) -> None:
        """Test that expected intents are matched (at least one)."""
        matched = 0
        total = 0

        for sample in routing_samples:
            query = sample["query"]
            expected_intents = sample["expected_intents"]

            if not expected_intents:
                continue  # Skip samples with no expected intents

            result = classifier.classify_text(query)
            total += 1

            # Check if at least one expected intent is in results
            if any(intent in result.intents for intent in expected_intents):
                matched += 1

        # Should match most samples (allow some tolerance)
        match_rate = matched / total if total > 0 else 0
        assert match_rate >= 0.75, f"Only {matched}/{total} samples matched expected intents"

    def test_complexity_reasonable(self, classifier: QueryClassifier, routing_samples: list[dict]) -> None:
        """Test that complexity is reasonably classified."""
        for sample in routing_samples:
            query = sample["query"]
            expected_complexity = sample["complexity"]
            result = classifier.classify_text(query)

            # Allow one level of difference (e.g., medium classified as simple or complex is OK)
            complexity_levels = ["simple", "medium", "complex", "crisis"]
            expected_idx = complexity_levels.index(expected_complexity)
            actual_idx = complexity_levels.index(result.complexity)

            # Allow ±1 level difference
            assert abs(expected_idx - actual_idx) <= 1, \
                f"Query: {query}\nExpected: {expected_complexity}, Got: {result.complexity}"

    def test_entity_extraction_sectors(self, classifier: QueryClassifier, routing_samples: list[dict]) -> None:
        """Test that sectors are extracted from samples."""
        total_with_sectors = 0
        correctly_extracted = 0

        for sample in routing_samples:
            query = sample["query"]
            expected_sectors = sample["entities"].get("sectors", [])

            if not expected_sectors:
                continue

            total_with_sectors += 1
            result = classifier.classify_text(query)

            # Check if at least one expected sector is extracted
            if any(sector in result.entities.sectors for sector in expected_sectors):
                correctly_extracted += 1

        # Should extract sectors reasonably well
        if total_with_sectors > 0:
            extraction_rate = correctly_extracted / total_with_sectors
            assert extraction_rate >= 0.70, \
                f"Only {correctly_extracted}/{total_with_sectors} samples had sectors extracted"

    def test_entity_extraction_metrics(self, classifier: QueryClassifier, routing_samples: list[dict]) -> None:
        """Test that metrics are extracted from samples."""
        total_with_metrics = 0
        correctly_extracted = 0

        for sample in routing_samples:
            query = sample["query"]
            expected_metrics = sample["entities"].get("metrics", [])

            if not expected_metrics:
                continue

            total_with_metrics += 1
            result = classifier.classify_text(query)

            # Check if at least one expected metric is extracted
            if any(metric in result.entities.metrics for metric in expected_metrics):
                correctly_extracted += 1

        # Should extract metrics reasonably well
        if total_with_metrics > 0:
            extraction_rate = correctly_extracted / total_with_metrics
            assert extraction_rate >= 0.70, \
                f"Only {correctly_extracted}/{total_with_metrics} samples had metrics extracted"

    def test_crisis_detection(self, classifier: QueryClassifier, routing_samples: list[dict]) -> None:
        """Test that crisis-level queries are detected."""
        crisis_samples = [s for s in routing_samples if s["complexity"] == "crisis"]

        for sample in crisis_samples:
            query = sample["query"]
            result = classifier.classify_text(query)

            # Should classify as crisis or at least complex
            assert result.complexity in ["crisis", "complex"], \
                f"Crisis query not detected: {query}"

    def test_simple_queries(self, classifier: QueryClassifier, routing_samples: list[dict]) -> None:
        """Test that simple queries are classified appropriately."""
        simple_samples = [s for s in routing_samples if s["complexity"] == "simple"]

        for sample in simple_samples:
            query = sample["query"]
            result = classifier.classify_text(query)

            # Should be simple or medium (not complex/crisis)
            assert result.complexity in ["simple", "medium"], \
                f"Simple query over-classified: {query} -> {result.complexity}"

    def test_confidence_scores(self, classifier: QueryClassifier, routing_samples: list[dict]) -> None:
        """Test that confidence scores are reasonable."""
        high_confidence_count = 0

        for sample in routing_samples:
            query = sample["query"]

            # Skip samples with no expected intents
            if not sample["expected_intents"]:
                continue

            result = classifier.classify_text(query)

            # Samples with clear intents should have decent confidence
            if result.confidence >= 0.4:
                high_confidence_count += 1

        # Most samples with expected intents should have reasonable confidence
        # Note: Keyword-based matching won't be perfect, 50% is reasonable
        samples_with_intents = len([s for s in routing_samples if s["expected_intents"]])
        confidence_rate = high_confidence_count / samples_with_intents if samples_with_intents > 0 else 0

        assert confidence_rate >= 0.50, \
            f"Only {high_confidence_count}/{samples_with_intents} samples had confidence >= 0.4"


class TestSpecificSamples:
    """Test specific important samples in detail."""

    def test_anomaly_simple(self, classifier: QueryClassifier) -> None:
        """Test simple anomaly detection query."""
        query = "Detect salary spikes in Healthcare sector"
        result = classifier.classify_text(query)

        assert "pattern.anomalies" in result.intents
        assert "Healthcare" in result.entities.sectors
        assert "salary" in result.entities.metrics
        assert result.complexity in ["simple", "medium"]

    def test_correlation_query(self, classifier: QueryClassifier) -> None:
        """Test correlation query."""
        query = "Is there a correlation between salary and retention?"
        result = classifier.classify_text(query)

        assert "pattern.correlation" in result.intents
        assert "salary" in result.entities.metrics
        assert any("retention" in m for m in result.entities.metrics)

    def test_urgent_crisis(self, classifier: QueryClassifier) -> None:
        """Test urgent crisis query."""
        query = "Urgent: sudden spike in turnover in Hospitality now"
        result = classifier.classify_text(query)

        assert result.complexity == "crisis"
        assert "Hospitality" in result.entities.sectors
        assert "turnover" in result.entities.metrics

    def test_multi_sector_complex(self, classifier: QueryClassifier) -> None:
        """Test complex multi-sector query."""
        query = "Identify outliers in employee attrition across Finance, Healthcare, and IT"
        result = classifier.classify_text(query)

        assert result.complexity in ["medium", "complex"]
        assert len(result.entities.sectors) >= 2  # Should extract multiple sectors

    def test_gcc_benchmark(self, classifier: QueryClassifier) -> None:
        """Test GCC benchmark query."""
        query = "How does Qatar wage growth compare to UAE?"
        result = classifier.classify_text(query)

        assert "strategy.gcc_benchmark" in result.intents
        assert "wage" in result.entities.metrics

    def test_vision2030(self, classifier: QueryClassifier) -> None:
        """Test Vision 2030 query."""
        query = "Qatarization progress toward Vision 2030 targets"
        result = classifier.classify_text(query)

        assert "strategy.vision2030" in result.intents
        assert "qatarization" in result.entities.metrics
