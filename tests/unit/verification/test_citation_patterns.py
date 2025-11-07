"""Tests for citation pattern matching utilities."""

from __future__ import annotations

from src.qnwis.verification.citation_patterns import (
    NUMBER,
    YEAR,
    extract_number_value,
    extract_qid,
    extract_source_prefix,
    is_ignorable,
    is_year,
)


class TestNumberPattern:
    """Tests for NUMBER regex pattern."""

    def test_integer(self):
        """Test matching simple integers."""
        text = "The count is 1234 items."
        matches = list(NUMBER.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(0) == "1234"

    def test_decimal(self):
        """Test matching decimal numbers."""
        text = "The rate is 87.5% overall."
        matches = list(NUMBER.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(0) == "87.5%"

    def test_currency(self):
        """Test matching currency values."""
        text = "Salary: 5000 QAR per month."
        matches = list(NUMBER.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(0) == "5000 QAR"

    def test_basis_points(self):
        """Test matching basis points."""
        text = "Margin widened by 125 bps year over year."
        matches = list(NUMBER.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(0).lower().startswith("125")

    def test_percentage(self):
        """Test matching percentages."""
        text = "Growth of 12.3 percent expected."
        matches = list(NUMBER.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(0) == "12.3 percent"

    def test_thousand_separator(self):
        """Test matching numbers with thousand separators."""
        text = "Total: 1,234,567 employees."
        matches = list(NUMBER.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(0) == "1,234,567"

    def test_negative_number(self):
        """Test matching negative numbers."""
        text = "Deficit of -5.2% reported."
        matches = list(NUMBER.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(0) == "-5.2%"

    def test_multiple_numbers(self):
        """Test matching multiple numbers in text."""
        text = "Values: 10, 20.5%, and 1,000 QAR."
        matches = list(NUMBER.finditer(text))
        assert len(matches) == 3


class TestYearPattern:
    """Tests for YEAR regex pattern."""

    def test_2000s_year(self):
        """Test matching 2000s years."""
        assert is_year("2023")
        assert is_year("2024")
        assert is_year("2000")

    def test_1900s_year(self):
        """Test matching 1900s years."""
        assert is_year("1990")
        assert is_year("1999")

    def test_not_year(self):
        """Test non-year numbers."""
        assert not is_year("123")
        assert not is_year("3000")
        assert not is_year("1800")

    def test_year_in_context(self):
        """Test year detection in text."""
        text = "In 2023, the rate was 75%."
        matches = list(YEAR.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(0) == "2023"


class TestQIDPattern:
    """Tests for QID regex pattern."""

    def test_qid_colon(self):
        """Test QID: format."""
        text = "Source: QID: abc123def"
        qid = extract_qid(text)
        assert qid == "abc123def"

    def test_qid_equals(self):
        """Test QID= format."""
        text = "Reference QID=xyz789ghi"
        qid = extract_qid(text)
        assert qid == "xyz789ghi"

    def test_query_id_param(self):
        """Test query_id= format."""
        text = "Data from query_id = lmis_retention_001"
        qid = extract_qid(text)
        assert qid == "lmis_retention_001"

    def test_qid_with_underscores(self):
        """Test QID with underscores."""
        text = "QID: lmis_qat_2024_q2"
        qid = extract_qid(text)
        assert qid == "lmis_qat_2024_q2"

    def test_qid_with_hyphens(self):
        """Test QID with hyphens."""
        text = "QID: gcc-stat-emp-001"
        qid = extract_qid(text)
        assert qid == "gcc-stat-emp-001"

    def test_no_qid(self):
        """Test text without QID."""
        text = "No query ID present here."
        qid = extract_qid(text)
        assert qid is None

    def test_short_qid_rejected(self):
        """Test that short QIDs (<8 chars) are rejected."""
        text = "QID: abc"
        qid = extract_qid(text)
        assert qid is None


class TestSourcePrefixPattern:
    """Tests for SOURCE_PREFIX regex pattern."""

    def test_per_lmis(self):
        """Test 'Per LMIS:' prefix."""
        text = "Per LMIS: The rate is 58%."
        prefix = extract_source_prefix(text)
        assert prefix == "Per LMIS:"

    def test_gcc_stat(self):
        """Test 'According to GCC-STAT:' prefix."""
        text = "According to GCC-STAT: Growth is 12%."
        prefix = extract_source_prefix(text)
        assert prefix == "According to GCC-STAT:"

    def test_world_bank(self):
        """Test 'According to World Bank:' prefix."""
        text = "According to World Bank: GDP is 2.8%."
        prefix = extract_source_prefix(text)
        assert prefix == "According to World Bank:"

    def test_gccstat_synonym(self):
        """Test GCC-STAT synonym without hyphen."""
        text = "According to GCCSTAT: Employment grew 3%."
        prefix = extract_source_prefix(text)
        assert prefix == "According to GCC-STAT:"

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        text = "per lmis: The count is 100."
        prefix = extract_source_prefix(text)
        assert prefix.lower() == "per lmis:"

    def test_no_prefix(self):
        """Test text without source prefix."""
        text = "The rate is 75% overall."
        prefix = extract_source_prefix(text)
        assert prefix is None

    def test_mid_sentence_prefix(self):
        """Test prefix in middle of text."""
        text = "The data shows that Per LMIS: rate is 58%."
        # Should only match at start of line
        prefix = extract_source_prefix(text)
        assert prefix is None


class TestIgnorableTokens:
    """Tests for ignorable token detection."""

    def test_iso_code(self):
        """Test ISO-3166 country codes."""
        assert is_ignorable("ISO-3166")
        assert is_ignorable("ISO-3166-1")

    def test_noc_code(self):
        """Test NOC codes."""
        assert is_ignorable("NOC 2021")

    def test_po_box(self):
        """Test PO Box identifiers."""
        assert is_ignorable("PO Box 12345")

    def test_rfc_number(self):
        """Test RFC document numbers."""
        assert is_ignorable("RFC 8259")

    def test_id_pattern(self):
        """Test generic ID patterns."""
        assert is_ignorable("ID 123456")

    def test_not_ignorable(self):
        """Test normal numbers are not ignored."""
        assert not is_ignorable("The count is 1234")
        assert not is_ignorable("87.5%")


class TestExtractNumberValue:
    """Tests for extracting numeric values from matches."""

    def test_positive_integer(self):
        """Test extracting positive integer."""
        match = NUMBER.search("Value: 1234")
        value = extract_number_value(match)
        assert value == 1234.0

    def test_negative_number(self):
        """Test extracting negative number."""
        match = NUMBER.search("Deficit: -5.2%")
        value = extract_number_value(match)
        assert value == -5.2

    def test_decimal(self):
        """Test extracting decimal number."""
        match = NUMBER.search("Rate: 87.5%")
        value = extract_number_value(match)
        assert value == 87.5

    def test_thousand_separator(self):
        """Test extracting number with separators."""
        match = NUMBER.search("Total: 1,234,567")
        value = extract_number_value(match)
        assert value == 1234567.0
