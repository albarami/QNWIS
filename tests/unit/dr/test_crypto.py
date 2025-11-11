"""Unit tests for DR crypto module."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.qnwis.dr.crypto import (
    DeterministicNonceGenerator,
    EnvelopeEncryptor,
    KMSStub,
    redact_manifest,
)
from src.qnwis.dr.models import EncryptionAlgorithm
from src.qnwis.utils.clock import ManualClock


def test_kms_stub_wrap_unwrap():
    """Test KMS stub key wrapping and unwrapping."""
    kms = KMSStub()
    plaintext_key = b"test_key_32_bytes_long_exactly!!"

    # Wrap key
    wrapped = kms.wrap_key(plaintext_key)
    assert len(wrapped) > len(plaintext_key)

    # Unwrap key
    unwrapped = kms.unwrap_key(wrapped)
    assert unwrapped == plaintext_key


def test_kms_stub_unwrap_invalid():
    """Test KMS stub rejects invalid wrapped keys."""
    kms = KMSStub()

    with pytest.raises(ValueError, match="invalid tag"):
        kms.unwrap_key(b"invalid_wrapped_key_data")


def test_kms_stub_deterministic():
    """Test KMS stub produces deterministic results with same master key."""
    master_key = b"master_key_32_bytes_long_test!!"
    kms1 = KMSStub(master_key)
    kms2 = KMSStub(master_key)

    plaintext_key = b"test_key_32_bytes_long_exactly!!"

    wrapped1 = kms1.wrap_key(plaintext_key)
    wrapped2 = kms2.wrap_key(plaintext_key)

    assert wrapped1 == wrapped2


def test_deterministic_nonce_generator():
    """Test deterministic nonce generation."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    nonce_gen = DeterministicNonceGenerator(clock)

    # Generate nonces
    nonce1 = nonce_gen.generate("context1")
    nonce2 = nonce_gen.generate("context2")

    # Should be 12 bytes
    assert len(nonce1) == 12
    assert len(nonce2) == 12

    # Should be different for different contexts
    assert nonce1 != nonce2


def test_deterministic_nonce_generator_reproducible():
    """Test nonce generation is reproducible with same clock state."""
    clock1 = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    clock2 = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))

    nonce_gen1 = DeterministicNonceGenerator(clock1, seed="test")
    nonce_gen2 = DeterministicNonceGenerator(clock2, seed="test")

    nonce1 = nonce_gen1.generate("context")
    nonce2 = nonce_gen2.generate("context")

    assert nonce1 == nonce2


def test_deterministic_nonce_generator_advances():
    """Test nonce changes as clock advances."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    nonce_gen = DeterministicNonceGenerator(clock)

    nonce1 = nonce_gen.generate("context")
    clock.advance(1.0)
    nonce2 = nonce_gen.generate("context")

    assert nonce1 != nonce2


def test_envelope_encryptor_generate_key():
    """Test key generation."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    kms = KMSStub()
    encryptor = EnvelopeEncryptor(clock, kms)

    key_material = encryptor.generate_key()

    assert key_material.key_id is not None
    assert key_material.algorithm == EncryptionAlgorithm.AES_256_GCM
    assert key_material.wrapped_key is not None
    assert key_material.kms_key_id == kms.kms_key_id


def test_envelope_encryptor_encrypt_decrypt():
    """Test encryption and decryption."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    kms = KMSStub()
    encryptor = EnvelopeEncryptor(clock, kms)

    key_material = encryptor.generate_key()
    plaintext = b"Test data to encrypt"

    # Encrypt
    ciphertext = encryptor.encrypt(plaintext, key_material, "test_context")
    assert ciphertext != plaintext
    assert len(ciphertext) > len(plaintext)

    # Decrypt
    decrypted = encryptor.decrypt(ciphertext, key_material)
    assert decrypted == plaintext


def test_envelope_encryptor_deterministic():
    """Test encryption is deterministic with same clock state."""
    master_key = b"master_key_32_bytes_long_test!!"

    clock1 = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    kms1 = KMSStub(master_key)
    encryptor1 = EnvelopeEncryptor(clock1, kms1)

    clock2 = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    kms2 = KMSStub(master_key)
    encryptor2 = EnvelopeEncryptor(clock2, kms2)

    # Generate same key
    key1 = encryptor1.generate_key()
    key2 = encryptor2.generate_key()

    plaintext = b"Test data"

    # Encrypt with same context
    ciphertext1 = encryptor1.encrypt(plaintext, key1, "context")
    ciphertext2 = encryptor2.encrypt(plaintext, key2, "context")

    # Should be identical (deterministic nonces)
    assert ciphertext1 == ciphertext2


def test_envelope_encryptor_different_contexts():
    """Test different contexts produce different ciphertexts."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    kms = KMSStub()
    encryptor = EnvelopeEncryptor(clock, kms)

    key_material = encryptor.generate_key()
    plaintext = b"Test data"

    ciphertext1 = encryptor.encrypt(plaintext, key_material, "context1")
    ciphertext2 = encryptor.encrypt(plaintext, key_material, "context2")

    assert ciphertext1 != ciphertext2


def test_envelope_encryptor_none_algorithm():
    """Test NONE algorithm bypasses encryption."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    kms = KMSStub()
    encryptor = EnvelopeEncryptor(clock, kms, EncryptionAlgorithm.NONE)

    # Should raise error when generating key
    with pytest.raises(ValueError, match="Cannot generate key for NONE algorithm"):
        encryptor.generate_key()


def test_envelope_encryptor_decrypt_invalid():
    """Test decryption fails with wrong key."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    kms = KMSStub()
    encryptor = EnvelopeEncryptor(clock, kms)

    key1 = encryptor.generate_key()
    key2 = encryptor.generate_key()

    plaintext = b"Test data"
    ciphertext = encryptor.encrypt(plaintext, key1)

    # Try to decrypt with wrong key
    with pytest.raises(Exception):  # cryptography raises various exceptions
        encryptor.decrypt(ciphertext, key2)


def test_redact_manifest():
    """Test manifest redaction."""
    manifest = {
        "snapshot_id": "snap-001",
        "key_material": {
            "key_id": "key-001",
            "algorithm": "aes_256_gcm",
            "wrapped_key": "secret_key_data",
        },
        "storage_target": {
            "backend": "object_store",
            "options": {
                "bucket": "my-bucket",
                "access_key": "AKIAIOSFODNN7EXAMPLE",
                "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            },
        },
    }

    redacted = redact_manifest(manifest)

    # Key material should be redacted
    assert redacted["key_material"]["wrapped_key"] == "***REDACTED***"
    assert redacted["key_material"]["key_id"] == "key-001"  # ID preserved

    # Storage credentials should be redacted
    assert redacted["storage_target"]["options"]["access_key"] == "***REDACTED***"
    assert redacted["storage_target"]["options"]["secret_key"] == "***REDACTED***"
    assert redacted["storage_target"]["options"]["bucket"] == "my-bucket"  # Non-secret preserved


def test_redact_manifest_no_secrets():
    """Test redaction with no secrets."""
    manifest = {
        "snapshot_id": "snap-001",
        "tag": "daily",
    }

    redacted = redact_manifest(manifest)

    assert redacted == manifest


def test_envelope_encryptor_large_data():
    """Test encryption of large data."""
    clock = ManualClock(start=datetime(2024, 1, 1, tzinfo=UTC))
    kms = KMSStub()
    encryptor = EnvelopeEncryptor(clock, kms)

    key_material = encryptor.generate_key()
    plaintext = b"X" * 1024 * 1024  # 1MB

    ciphertext = encryptor.encrypt(plaintext, key_material)
    decrypted = encryptor.decrypt(ciphertext, key_material)

    assert decrypted == plaintext
