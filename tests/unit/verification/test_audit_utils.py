"""
Unit tests for audit trail utility functions.

Tests canonical JSON generation, cryptographic digests, HMAC signatures,
PII redaction, and reproducibility snippets.
"""

import re

import pytest

from src.qnwis.verification.audit_utils import (
    canonical_json,
    compute_params_hash,
    hmac_sha256,
    redact_text,
    reproducibility_snippet,
    sha256_digest,
    slugify_filename,
)


class TestCanonicalJson:
    """Tests for canonical_json() function."""

    def test_canonical_json_stable_digest(self) -> None:
        """Test that canonical_json produces deterministic output."""
        obj1 = {"b": 2, "a": 1, "c": {"z": 26, "y": 25}}
        obj2 = {"c": {"y": 25, "z": 26}, "a": 1, "b": 2}

        json1 = canonical_json(obj1)
        json2 = canonical_json(obj2)

        # Should be identical despite different insertion orders
        assert json1 == json2
        assert json1 == '{"a":1,"b":2,"c":{"y":25,"z":26}}'

    def test_canonical_json_no_whitespace(self) -> None:
        """Test that canonical JSON has no extra whitespace."""
        obj = {"key": "value", "nested": {"inner": 123}}
        result = canonical_json(obj)

        # Should have no spaces
        assert " " not in result
        assert "\n" not in result
        assert "\t" not in result

    def test_canonical_json_unicode_preserved(self) -> None:
        """Test that Unicode characters are preserved (not escaped)."""
        obj = {"greeting": "مرحبا", "city": "الدوحة"}
        result = canonical_json(obj)

        # Unicode should be preserved, not \u escaped
        assert "مرحبا" in result
        assert "الدوحة" in result


class TestSha256Digest:
    """Tests for sha256_digest() function."""

    def test_sha256_and_hmac_generation(self) -> None:
        """Test SHA-256 digest generation."""
        text = "deterministic input"
        digest = sha256_digest(text)

        # Should be 64-character hex string
        assert len(digest) == 64
        assert re.match(r"^[a-f0-9]{64}$", digest)

        # Should be deterministic
        assert sha256_digest(text) == digest

    def test_sha256_different_inputs(self) -> None:
        """Test that different inputs produce different digests."""
        d1 = sha256_digest("input1")
        d2 = sha256_digest("input2")

        assert d1 != d2


class TestHmacSha256:
    """Tests for hmac_sha256() function."""

    def test_hmac_with_valid_key(self) -> None:
        """Test HMAC generation with valid key."""
        text = "message to sign"
        key = b"secret_key_12345"

        signature = hmac_sha256(text, key)

        # Should be 64-character hex string
        assert len(signature) == 64
        assert re.match(r"^[a-f0-9]{64}$", signature)

        # Should be deterministic
        assert hmac_sha256(text, key) == signature

    def test_hmac_empty_key_raises(self) -> None:
        """Test that empty key raises ValueError."""
        with pytest.raises(ValueError, match="HMAC key must not be empty"):
            hmac_sha256("message", b"")

    def test_hmac_different_keys(self) -> None:
        """Test that different keys produce different signatures."""
        text = "message"
        sig1 = hmac_sha256(text, b"key1")
        sig2 = hmac_sha256(text, b"key2")

        assert sig1 != sig2


class TestRedactText:
    """Tests for redact_text() function."""

    def test_redaction_applied_to_summaries(self) -> None:
        """Test that PII patterns are redacted."""
        text = (
            "John Smith worked at john.smith@example.com. "
            "His employee ID is 1234567890123."
        )
        redacted = redact_text(text)

        # Names should be redacted
        assert "John Smith" not in redacted
        assert "[REDACTED_NAME]" in redacted

        # Email should be redacted
        assert "john.smith@example.com" not in redacted
        assert "[REDACTED_EMAIL]" in redacted

        # ID should be redacted
        assert "1234567890123" not in redacted
        assert "[REDACTED_ID]" in redacted

    def test_redact_preserves_non_pii(self) -> None:
        """Test that non-PII text is preserved."""
        text = "The unemployment rate is 3.5% in Qatar."
        redacted = redact_text(text)

        # Should be unchanged
        assert redacted == text

    def test_redact_multiple_names(self) -> None:
        """Test redacting multiple names in text."""
        text = "John Smith and Jane Doe attended the meeting."
        redacted = redact_text(text)

        assert "John Smith" not in redacted
        assert "Jane Doe" not in redacted
        # Should have 2 replacements
        assert redacted.count("[REDACTED_NAME]") == 2


class TestSlugifyFilename:
    """Tests for slugify_filename() function."""

    def test_slugify_basic(self) -> None:
        """Test basic slugification."""
        assert slugify_filename("Hello World") == "hello_world"
        assert slugify_filename("Test-File.json") == "test-file.json"

    def test_slugify_special_characters(self) -> None:
        """Test handling of special characters."""
        assert slugify_filename("file@#$%name!") == "file_name"
        assert slugify_filename("مرحبا") == "artifact"  # Non-ASCII to default

    def test_slugify_empty_string(self) -> None:
        """Test handling of empty string."""
        assert slugify_filename("") == "artifact"
        assert slugify_filename("", default="custom") == "custom"

    def test_slugify_preserves_safe_chars(self) -> None:
        """Test that safe characters are preserved."""
        assert slugify_filename("file_name-123.txt") == "file_name-123.txt"


class TestReproducibilitySnippet:
    """Tests for reproducibility_snippet() function."""

    def test_reproducibility_snippet_contains_query_ids_and_version(self) -> None:
        """Test that snippet includes query IDs and registry version."""
        query_ids = ["labor_supply", "unemployment_by_nationality", "wage_trends"]
        registry_version = "v1.2.3-abc123"

        snippet = reproducibility_snippet(query_ids, registry_version)

        # Should contain all query IDs
        for qid in query_ids:
            assert qid in snippet

        # Should contain registry version
        assert registry_version in snippet

        # Should be valid Python (basic check)
        assert "from src.qnwis.data.deterministic.api import DataAPI" in snippet
        assert "api = DataAPI" in snippet
        assert "query_ids = [" in snippet

    def test_reproducibility_snippet_is_executable_python(self) -> None:
        """Test that snippet is syntactically valid Python."""
        query_ids = ["query1", "query2"]
        registry_version = "v1.0.0"

        snippet = reproducibility_snippet(query_ids, registry_version)

        # Should compile without syntax errors
        try:
            compile(snippet, "<string>", "exec")
        except SyntaxError as exc:
            pytest.fail(f"Snippet has syntax error: {exc}")


class TestComputeParamsHash:
    """Tests for compute_params_hash() function."""

    def test_compute_params_hash_deterministic(self) -> None:
        """Test that params hash is deterministic."""
        params1 = {"query": "unemployment", "region": "Qatar", "year": 2023}
        params2 = {"year": 2023, "region": "Qatar", "query": "unemployment"}

        hash1 = compute_params_hash(params1)
        hash2 = compute_params_hash(params2)

        # Should be identical despite different key order
        assert hash1 == hash2
        assert len(hash1) == 64
        assert re.match(r"^[a-f0-9]{64}$", hash1)

    def test_compute_params_hash_different_values(self) -> None:
        """Test that different params produce different hashes."""
        params1 = {"key": "value1"}
        params2 = {"key": "value2"}

        hash1 = compute_params_hash(params1)
        hash2 = compute_params_hash(params2)

        assert hash1 != hash2
