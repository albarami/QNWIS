"""
Unit tests for audit trail utility functions.

Tests cryptographic digest computation, HMAC signatures, PII redaction,
and JSON canonicalization.
"""

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
    """Tests for deterministic JSON canonicalization."""

    def test_canonical_json_sorted_keys(self):
        """Keys should be sorted alphabetically."""
        obj = {"z": 1, "a": 2, "m": 3}
        result = canonical_json(obj)
        assert result == '{"a":2,"m":3,"z":1}'

    def test_canonical_json_no_whitespace(self):
        """No whitespace should be present."""
        obj = {"key": "value", "nested": {"inner": 123}}
        result = canonical_json(obj)
        assert " " not in result
        assert "\n" not in result
        assert "\t" not in result

    def test_canonical_json_nested_objects(self):
        """Nested objects should also have sorted keys."""
        obj = {"outer": {"z": 1, "a": 2}, "first": 3}
        result = canonical_json(obj)
        assert result == '{"first":3,"outer":{"a":2,"z":1}}'

    def test_canonical_json_arrays_preserved(self):
        """Array order should be preserved."""
        obj = {"arr": [3, 1, 2]}
        result = canonical_json(obj)
        assert result == '{"arr":[3,1,2]}'

    def test_canonical_json_unicode(self):
        """Unicode characters should be preserved."""
        obj = {"arabic": "مرحبا", "emoji": "🔒"}
        result = canonical_json(obj)
        assert "مرحبا" in result
        assert "🔒" in result

    def test_canonical_json_deterministic(self):
        """Multiple calls should produce identical output."""
        obj = {"z": 1, "a": 2, "m": 3}
        result1 = canonical_json(obj)
        result2 = canonical_json(obj)
        assert result1 == result2


class TestSha256Digest:
    """Tests for SHA-256 digest computation."""

    def test_sha256_digest_known_value(self):
        """Test against known SHA-256 hash."""
        text = "hello world"
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert sha256_digest(text) == expected

    def test_sha256_digest_empty_string(self):
        """Empty string should have known hash."""
        text = ""
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert sha256_digest(text) == expected

    def test_sha256_digest_utf8(self):
        """UTF-8 characters should be encoded correctly."""
        text = "\u0627\u062e\u062a\u0628\u0627\u0631"
        result = sha256_digest(text)
        assert len(result) == 64  # SHA-256 produces 64 hex characters
        assert all(c in "0123456789abcdef" for c in result)

    def test_sha256_digest_deterministic(self):
        """Same input should always produce same digest."""
        text = "test input"
        result1 = sha256_digest(text)
        result2 = sha256_digest(text)
        assert result1 == result2

    def test_sha256_digest_different_inputs(self):
        """Different inputs should produce different digests."""
        result1 = sha256_digest("input1")
        result2 = sha256_digest("input2")
        assert result1 != result2


class TestHmacSha256:
    """Tests for HMAC-SHA256 signature generation."""

    def test_hmac_sha256_valid_key(self):
        """Valid key and text should produce signature."""
        text = "message"
        key = b"secret"
        result = hmac_sha256(text, key)
        assert len(result) == 64  # HMAC-SHA256 produces 64 hex characters
        assert all(c in "0123456789abcdef" for c in result)

    def test_hmac_sha256_empty_key_raises(self):
        """Empty key should raise ValueError."""
        with pytest.raises(ValueError, match="HMAC key must not be empty"):
            hmac_sha256("message", b"")

    def test_hmac_sha256_deterministic(self):
        """Same key and text should produce same signature."""
        text = "message"
        key = b"secret"
        result1 = hmac_sha256(text, key)
        result2 = hmac_sha256(text, key)
        assert result1 == result2

    def test_hmac_sha256_different_keys(self):
        """Different keys should produce different signatures."""
        text = "message"
        result1 = hmac_sha256(text, b"key1")
        result2 = hmac_sha256(text, b"key2")
        assert result1 != result2

    def test_hmac_sha256_different_texts(self):
        """Different texts should produce different signatures."""
        key = b"secret"
        result1 = hmac_sha256("message1", key)
        result2 = hmac_sha256("message2", key)
        assert result1 != result2


class TestRedactText:
    """Tests for PII redaction rules."""

    def test_redact_text_names(self):
        """Capitalized first and last names should be redacted."""
        text = "John Smith works here"
        result = redact_text(text)
        assert "John Smith" not in result
        assert "[REDACTED_NAME]" in result

    def test_redact_text_emails(self):
        """Email addresses should be redacted."""
        text = "Contact us at john.smith@example.com"
        result = redact_text(text)
        assert "john.smith@example.com" not in result
        assert "[REDACTED_EMAIL]" in result

    def test_redact_text_ids(self):
        """Numeric IDs with 10+ digits should be redacted."""
        text = "ID: 1234567890123"
        result = redact_text(text)
        assert "1234567890123" not in result
        assert "[REDACTED_ID]" in result

    def test_redact_text_short_ids_preserved(self):
        """IDs with <10 digits should not be redacted."""
        text = "ID: 123456789"
        result = redact_text(text)
        assert "123456789" in result

    def test_redact_text_multiple_patterns(self):
        """Multiple PII patterns should all be redacted."""
        text = "John Smith (john@example.com) - ID: 1234567890123"
        result = redact_text(text)
        assert "John Smith" not in result
        assert "john@example.com" not in result
        assert "1234567890123" not in result
        assert "[REDACTED_NAME]" in result
        assert "[REDACTED_EMAIL]" in result
        assert "[REDACTED_ID]" in result

    def test_redact_text_no_pii(self):
        """Text without PII should remain unchanged."""
        text = "This is a normal sentence with no PII."
        result = redact_text(text)
        assert result == text


class TestReproducibilitySnippet:
    """Tests for reproducibility Python snippet generation."""

    def test_reproducibility_snippet_structure(self):
        """Snippet should contain required components."""
        query_ids = ["qid_abc123", "qid_def456"]
        registry_version = "v1.0.0"

        snippet = reproducibility_snippet(query_ids, registry_version)

        assert "from src.qnwis.data.deterministic.api import DataAPI" in snippet
        assert f'registry_version="{registry_version}"' in snippet
        assert "qid_abc123" in snippet
        assert "qid_def456" in snippet
        assert "api.fetch(qid)" in snippet

    def test_reproducibility_snippet_empty_query_ids(self):
        """Snippet should handle empty query ID list."""
        query_ids = []
        registry_version = "v1.0.0"

        snippet = reproducibility_snippet(query_ids, registry_version)

        assert "query_ids = [" in snippet
        assert "DataAPI" in snippet

    def test_reproducibility_snippet_many_query_ids(self):
        """Snippet should handle many query IDs."""
        query_ids = [f"qid_{i:06d}" for i in range(100)]
        registry_version = "v1.0.0"

        snippet = reproducibility_snippet(query_ids, registry_version)

        for qid in query_ids[:10]:  # Check first 10
            assert qid in snippet


class TestComputeParamsHash:
    """Tests for parameter dictionary hashing."""

    def test_compute_params_hash_deterministic(self):
        """Same parameters should produce same hash."""
        params = {"key1": "value1", "key2": 123}
        hash1 = compute_params_hash(params)
        hash2 = compute_params_hash(params)
        assert hash1 == hash2

    def test_compute_params_hash_order_independent(self):
        """Dictionary order should not affect hash."""
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "a": 1, "b": 2}
        hash1 = compute_params_hash(params1)
        hash2 = compute_params_hash(params2)
        assert hash1 == hash2

    def test_compute_params_hash_different_values(self):
        """Different values should produce different hashes."""
        params1 = {"key": "value1"}
        params2 = {"key": "value2"}
        hash1 = compute_params_hash(params1)
        hash2 = compute_params_hash(params2)
        assert hash1 != hash2

    def test_compute_params_hash_empty_dict(self):
        """Empty dictionary should produce valid hash."""
        params = {}
        result = compute_params_hash(params)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestSlugifyFilename:
    """Tests for filename slugification helper."""

    def test_slugify_preserves_safe_characters(self):
        """Alphanumeric, dash, underscore should be preserved."""
        assert slugify_filename("Dataset-01_v2") == "dataset-01_v2"

    def test_slugify_replaces_spaces(self):
        """Spaces and punctuation should be replaced with underscores."""
        assert slugify_filename("My Source (Final)") == "my_source_final"

    def test_slugify_handles_empty_input(self):
        """Empty strings should fall back to default."""
        assert slugify_filename("", default="source") == "source"
