"""Tests for citation enforcement engine."""

from __future__ import annotations

import pytest

from src.qnwis.data.deterministic.models import (
    Freshness,
    Provenance,
    QueryResult,
    Row,
)
from src.qnwis.verification.citation_enforcer import (
    enforce_citations,
    extract_numeric_spans,
    find_citation_context,
    map_sources_to_queryresults,
    validate_context_has_source_and_qid,
)
from src.qnwis.verification.schemas import CitationRules


@pytest.fixture
def default_rules() -> CitationRules:
    """Create default citation rules."""
    return CitationRules(
        allowed_prefixes=[
            "Per LMIS:",
            "According to GCC-STAT:",
            "According to World Bank:",
        ],
        require_query_id=True,
        ignore_years=True,
        ignore_numbers_below=1.0,
        ignore_tokens=["ISO-3166", "NOC", "PO Box"],
        source_mapping={
            "Per LMIS:": ["LMIS", "lmis"],
            "According to GCC-STAT:": ["GCC-STAT", "gcc_stat"],
            "According to World Bank:": ["WorldBank", "world_bank", "WB"],
        },
        missing_qid_severity="error",
        strict_qid_keywords=[],
        strict_qid_severity="error",
        source_synonyms={
            "According to GCC-STAT:": ["According to GCCSTAT:", "According to GCC STAT:"]
        },
        adjacent_bullet_window=1,
    )


@pytest.fixture
def sample_query_result() -> QueryResult:
    """Create sample query result."""
    return QueryResult(
        query_id="lmis_test_001",
        rows=[Row(data={"value": 100})],
        unit="count",
        provenance=Provenance(
            source="csv",
            dataset_id="LMIS_retention",
            locator="/data/lmis.csv",
            fields=["value"],
        ),
        freshness=Freshness(asof_date="2024-01-01"),
    )


class TestExtractNumericSpans:
    """Tests for extracting numeric spans."""

    def test_simple_number(self, default_rules):
        """Test extracting simple number."""
        text = "The count is 1234 items."
        spans = extract_numeric_spans(text, default_rules)
        assert len(spans) == 1
        start, end, token = spans[0]
        assert token == "1234"

    def test_percentage(self, default_rules):
        """Test extracting percentage."""
        text = "The rate is 87.5% overall."
        spans = extract_numeric_spans(text, default_rules)
        assert len(spans) == 1
        start, end, token = spans[0]
        assert token == "87.5%"

    def test_ignore_year(self, default_rules):
        """Test that years are ignored."""
        text = "In 2023, the count was 100."
        spans = extract_numeric_spans(text, default_rules)
        assert len(spans) == 1
        # Should only get 100, not 2023
        assert spans[0][2] == "100"

    def test_ignore_historical_years(self, default_rules):
        """Test that legacy years like 2019/2020 are ignored."""
        text = "Between 2019 and 2020 the rate peaked at 4.5%."
        spans = extract_numeric_spans(text, default_rules)
        assert len(spans) == 1
        assert spans[0][2].endswith("%")

    def test_ignore_small_numbers(self, default_rules):
        """Test ignoring numbers below threshold."""
        default_rules.ignore_numbers_below = 10.0
        text = "Values: 5, 8, and 20."
        spans = extract_numeric_spans(text, default_rules)
        # Should only get 20
        assert len(spans) == 1
        assert spans[0][2] == "20"

    def test_ignore_tokens(self, default_rules):
        """Test ignoring configured tokens."""
        text = "ISO-3166 code QA has 100 entities."
        spans = extract_numeric_spans(text, default_rules)
        # ISO-3166's "-3166" should be filtered by hyphen check
        # Should only get 100
        assert len(spans) >= 1
        # Last span should be 100
        assert spans[-1][2] == "100"

    def test_ignore_identifier_tokens(self, default_rules):
        """Ensure ID-like tokens are not treated as claims."""
        text = "Record ID 2020 references the value 45%."
        spans = extract_numeric_spans(text, default_rules)
        assert len(spans) == 1
        assert spans[0][2] == "45%"

    def test_multiple_numbers(self, default_rules):
        """Test extracting multiple numbers."""
        text = "Values: 10, 20.5%, and 1,000 QAR."
        spans = extract_numeric_spans(text, default_rules)
        assert len(spans) == 3


class TestFindCitationContext:
    """Tests for finding citation context."""

    def test_simple_sentence(self):
        """Test extracting sentence context."""
        text = "The rate is 87.5% in Q3. Another sentence."
        pos = text.index("87.5")
        ctx = find_citation_context(text, pos, window=200)
        assert "87.5%" in ctx
        assert "Q3" in ctx

    def test_multi_line_context(self):
        """Test context across line breaks."""
        text = "Per LMIS: The retention rate\nis 87.5% in Q3 2024."
        pos = text.index("87.5")
        ctx = find_citation_context(text, pos, window=200)
        assert "Per LMIS:" in ctx
        assert "87.5%" in ctx

    def test_window_limiting(self):
        """Test that context is limited by window size."""
        text = "A" * 500 + " 100 " + "B" * 500
        pos = text.index("100")
        ctx = find_citation_context(text, pos, window=50)
        assert len(ctx) <= 150  # Window on both sides + number

    def test_sentence_boundary(self):
        """Test expansion to sentence boundaries."""
        text = "First sentence. Per LMIS: The rate is 87.5%. Third sentence."
        pos = text.index("87.5")
        ctx = find_citation_context(text, pos, window=200)
        # Should expand to full sentence
        assert "Per LMIS:" in ctx
        assert "Third sentence" not in ctx


class TestValidateContext:
    """Tests for validating citation context."""

    def test_valid_citation_with_qid(self, default_rules):
        """Test valid citation with source and QID."""
        ctx = "Per LMIS: The rate is 87.5% (QID: lmis_ret_001)."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert ctx_eval.has_source
        assert ctx_eval.has_qid
        assert ctx_eval.matched_prefix == "Per LMIS:"

    def test_valid_citation_gcc_stat(self, default_rules):
        """Test valid GCC-STAT citation."""
        ctx = "According to GCC-STAT: Growth is 12% (QID: gcc_emp_001)."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert ctx_eval.has_source
        assert ctx_eval.has_qid
        assert ctx_eval.matched_prefix == "According to GCC-STAT:"

    def test_missing_source(self, default_rules):
        """Test context without source prefix."""
        ctx = "The rate is 87.5% (QID: test_001)."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert not ctx_eval.has_source
        assert ctx_eval.has_qid  # QID present but source missing
        assert ctx_eval.matched_prefix == ""

    def test_missing_qid(self, default_rules):
        """Test context with source but no QID."""
        ctx = "Per LMIS: The rate is 87.5%."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert ctx_eval.has_source
        assert not ctx_eval.has_qid
        assert ctx_eval.matched_prefix == "Per LMIS:"
        assert ctx_eval.missing_qid_severity == "error"

    def test_qid_not_required(self, default_rules):
        """Test when QID is not required."""
        default_rules.require_query_id = False
        ctx = "Per LMIS: The rate is 87.5%."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert ctx_eval.has_source
        assert ctx_eval.has_qid  # Marked as present when not required
        assert ctx_eval.matched_prefix == "Per LMIS:"

    def test_case_insensitive_source(self, default_rules):
        """Test case-insensitive source matching."""
        ctx = "per lmis: The rate is 87.5% (QID: test_001)."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert ctx_eval.has_source
        assert ctx_eval.matched_prefix == "Per LMIS:"  # Returns canonical form

    def test_query_id_equals_format(self, default_rules):
        """Test query_id= format is recognized."""
        ctx = "Per LMIS: Rate is 54% (query_id = lmis_ret_001)."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert ctx_eval.has_qid

    def test_synonym_normalization(self, default_rules):
        """Test GCC-STAT synonym normalizes to canonical prefix."""
        ctx = "According to GCCSTAT: Employment rose 3% (QID: gcc_emp_001)."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert ctx_eval.has_source
        assert ctx_eval.matched_prefix == "According to GCC-STAT:"

    def test_missing_qid_warning_severity(self, default_rules):
        """Missing QIDs adopt configured severity."""
        default_rules.missing_qid_severity = "warning"
        ctx = "Per LMIS: Rate is 87.5%."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert ctx_eval.missing_qid_severity == "warning"

    def test_strict_metric_requires_qid_even_when_optional(self, default_rules):
        """Strict keywords force QID enforcement."""
        default_rules.require_query_id = False
        default_rules.strict_qid_keywords = ["attrition"]
        default_rules.strict_qid_severity = "error"
        ctx = "Per LMIS: Attrition rose to 12%."
        ctx_eval = validate_context_has_source_and_qid(ctx, default_rules)
        assert ctx_eval.qid_required is True
        assert ctx_eval.strict_keyword == "attrition"
        assert ctx_eval.missing_qid_severity == "error"


class TestMapSourcesToQueryResults:
    """Tests for mapping sources to query results."""

    def test_valid_mapping_lmis(self, default_rules, sample_query_result):
        """Test valid LMIS source mapping."""
        result = map_sources_to_queryresults(
            "Per LMIS:", [sample_query_result], default_rules
        )
        assert result is True

    def test_no_mapping_defined(self, default_rules, sample_query_result):
        """Test source with no mapping (should accept)."""
        result = map_sources_to_queryresults(
            "Unknown Source:", [sample_query_result], default_rules
        )
        # No mapping = accept any
        assert result is True

    def test_empty_query_results(self, default_rules):
        """Test with no query results."""
        result = map_sources_to_queryresults("Per LMIS:", [], default_rules)
        assert result is False

    def test_multiple_query_results(self, default_rules, sample_query_result):
        """Test matching with multiple query results."""
        qr2 = QueryResult(
            query_id="gcc_test_001",
            rows=[Row(data={"value": 200})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="GCC-STAT_employment",
                locator="/data/gcc.csv",
                fields=["value"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        # Should match first result (LMIS)
        result = map_sources_to_queryresults(
            "Per LMIS:", [sample_query_result, qr2], default_rules
        )
        assert result is True
        # Should match second result (GCC-STAT)
        result = map_sources_to_queryresults(
            "According to GCC-STAT:", [sample_query_result, qr2], default_rules
        )
        assert result is True

    def test_world_bank_mapping(self, default_rules):
        """Test World Bank mapping."""
        qb = QueryResult(
            query_id="wb_test_001",
            rows=[Row(data={"value": 80})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="WorldBank_employment",
                locator="/data/wb.csv",
                fields=["value"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        assert map_sources_to_queryresults(
            "According to World Bank:", [qb], default_rules
        )


class TestEnforceCitations:
    """Tests for full citation enforcement."""

    def test_valid_citations_pass(self, default_rules, sample_query_result):
        """Test that valid citations pass enforcement."""
        text = "Per LMIS: The retention rate is 87.5% in Q3 (QID: lmis_ret_001)."
        report = enforce_citations(text, [sample_query_result], default_rules)

        assert report.ok is True
        assert report.total_numbers == 1
        assert report.cited_numbers == 1
        assert len(report.uncited) == 0
        assert len(report.missing_qid) == 0
        assert len(report.malformed) == 0
        assert report.sources_used == {"Per LMIS:": 1}

    def test_uncited_number_fails(self, default_rules, sample_query_result):
        """Test that uncited numbers are detected."""
        text = "The retention rate is 87.5% in Q3."
        report = enforce_citations(text, [sample_query_result], default_rules)

        assert report.ok is False
        assert report.total_numbers == 1
        assert report.cited_numbers == 0
        assert len(report.uncited) == 1
        assert report.uncited[0].code == "UNCITED_NUMBER"
        assert "87.5%" in report.uncited[0].value_text

    def test_missing_qid_fails(self, default_rules, sample_query_result):
        """Test that missing QID is detected."""
        text = "Per LMIS: The retention rate is 87.5% in Q3."
        report = enforce_citations(text, [sample_query_result], default_rules)

        assert report.ok is False
        assert len(report.missing_qid) == 1
        assert report.missing_qid[0].code == "MISSING_QID"

    def test_unknown_source_fails(self, default_rules):
        """Test that unknown sources are detected."""
        # Create query result with non-matching source
        qr = QueryResult(
            query_id="other_001",
            rows=[Row(data={"value": 100})],
            unit="count",
            provenance=Provenance(
                source="csv",
                dataset_id="OTHER_data",
                locator="/data/other.csv",
                fields=["value"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        text = "Per LMIS: The rate is 87.5% (QID: test_001)."
        report = enforce_citations(text, [qr], default_rules)

        assert report.ok is False
        assert len(report.malformed) == 1
        assert report.malformed[0].code == "UNKNOWN_SOURCE"

    def test_multiple_citations(self, default_rules, sample_query_result):
        """Test multiple valid citations."""
        text = (
            "Per LMIS: Rate is 87.5% (QID: lmis_ret_001). "
            "Per LMIS: Count is 1,234 (QID: lmis_count_001)."
        )
        report = enforce_citations(text, [sample_query_result], default_rules)

        assert report.ok is True
        assert report.total_numbers == 2
        assert report.cited_numbers == 2
        assert report.sources_used == {"Per LMIS:": 2}

    def test_mixed_citations(self, default_rules, sample_query_result):
        """Test mix of valid and invalid citations."""
        text = (
            "Per LMIS: Valid rate is 87.5% (QID: lmis_001). "
            "Invalid rate is 45.2% without citation."
        )
        report = enforce_citations(text, [sample_query_result], default_rules)

        assert report.ok is False
        assert report.total_numbers == 2
        assert report.cited_numbers == 1
        assert len(report.uncited) == 1

    def test_ignore_years(self, default_rules, sample_query_result):
        """Test that years are ignored."""
        text = "Per LMIS: In 2023, rate was 87.5% (QID: lmis_001)."
        report = enforce_citations(text, [sample_query_result], default_rules)

        # Should only detect 87.5%, not 2023
        assert report.total_numbers == 1
        assert report.cited_numbers == 1

    def test_empty_text(self, default_rules, sample_query_result):
        """Test enforcement on empty text."""
        text = ""
        report = enforce_citations(text, [sample_query_result], default_rules)

        assert report.ok is True
        assert report.total_numbers == 0
        assert report.cited_numbers == 0

    def test_no_numbers(self, default_rules, sample_query_result):
        """Test text with no numbers."""
        text = "Per LMIS: This text has no numeric claims (QID: lmis_001)."
        report = enforce_citations(text, [sample_query_result], default_rules)

        assert report.ok is True
        assert report.total_numbers == 0

    def test_synonym_prefix_passes(self, default_rules, sample_query_result):
        """Synonym prefixes (GCCSTAT) should normalize to canonical form."""
        gcc_result = QueryResult(
            query_id="gcc_synonym_001",
            rows=[Row(data={"value": 120})],
            unit="percent",
            provenance=Provenance(
                source="csv",
                dataset_id="GCC-STAT_employment",
                locator="/data/gcc.csv",
                fields=["value"],
            ),
            freshness=Freshness(asof_date="2024-01-01"),
        )
        text = "According to GCCSTAT: Growth is 12% (QID: gcc_synonym_001)."
        report = enforce_citations(text, [gcc_result], default_rules)
        assert report.ok is True
        assert report.sources_used.get("According to GCC-STAT:") == 1

    def test_adjacent_bullet_lines_are_linked(self, default_rules, sample_query_result):
        """Treat adjacent bullet citations as valid."""
        text = (
            "- Employment jumped 12% in Q2.\n"
            "- Per LMIS: Underlying survey (QID: lmis_test_001)."
        )
        report = enforce_citations(text, [sample_query_result], default_rules)
        assert report.ok is True
        assert report.cited_numbers == 1

    def test_missing_qid_warning_allows_workflow(
        self, default_rules, sample_query_result
    ):
        """Warnings should not fail report."""
        default_rules.missing_qid_severity = "warning"
        text = "Per LMIS: Rate is 87.5%."
        report = enforce_citations(text, [sample_query_result], default_rules)
        assert report.ok is True
        assert report.missing_qid
        assert report.missing_qid[0].severity == "warning"

    def test_performance_runtime_under_20ms(
        self, default_rules, sample_query_result
    ):
        """Benchmark runtime remains below 20ms for realistic reports."""
        snippets = [
            f"Per LMIS: Metric {i} is {50 + i}% (QID: lmis_test_001)."
            for i in range(1, 6)
        ]
        text = " ".join(snippets)
        report = enforce_citations(text, [sample_query_result], default_rules)
        assert report.runtime_ms is not None
        assert report.runtime_ms < 20.0
