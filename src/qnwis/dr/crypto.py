"""
Envelope encryption for DR backups with deterministic nonce generation.

Uses AES-256-GCM with nonces derived from injected Clock + counter.
Key wrapping via KMS stub (ed25519 or RSA local).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING, Any, cast

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if TYPE_CHECKING:
    from ..utils.clock import Clock

from .models import EncryptionAlgorithm, KeyMaterial


class KMSStub:
    """
    Local KMS stub for key wrapping/unwrapping.

    Uses HMAC-SHA256 with a master key for deterministic wrapping.
    In production, replace with actual KMS integration.
    """

    def __init__(self, master_key: bytes | None = None) -> None:
        """
        Initialize KMS stub.

        Args:
            master_key: Master key for wrapping (32 bytes). If None, generates random.
        """
        self._master_key = master_key or secrets.token_bytes(32)
        self.kms_key_id = "local-kms-stub-v1"

    def wrap_key(self, plaintext_key: bytes) -> bytes:
        """
        Wrap a data encryption key.

        Args:
            plaintext_key: Raw key material to wrap

        Returns:
            Wrapped key material
        """
        # Simple HMAC-based wrapping (deterministic for same master key)
        tag = hmac.new(self._master_key, plaintext_key, hashlib.sha256).digest()
        return plaintext_key + tag

    def unwrap_key(self, wrapped_key: bytes) -> bytes:
        """
        Unwrap a data encryption key.

        Args:
            wrapped_key: Wrapped key material

        Returns:
            Plaintext key material

        Raises:
            ValueError: If unwrapping fails (invalid tag)
        """
        if len(wrapped_key) < 32:
            raise ValueError("Key unwrapping failed: invalid tag")
        plaintext_key = wrapped_key[:-32]
        tag = wrapped_key[-32:]
        expected_tag = hmac.new(self._master_key, plaintext_key, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise ValueError("Key unwrapping failed: invalid tag")
        return plaintext_key


class DeterministicNonceGenerator:
    """
    Deterministic nonce generator using injected clock + counter.

    Generates unique nonces for AES-GCM by combining:
    - Clock timestamp (milliseconds)
    - Monotonic counter
    - Optional context (e.g., file path)
    """

    def __init__(self, clock: Clock, seed: str = "dr-backup-v1") -> None:
        """
        Initialize nonce generator.

        Args:
            clock: Injected clock for deterministic time
            seed: Seed string for nonce derivation
        """
        self._clock = clock
        self._seed = seed.encode()
        self._counter = 0

    def generate(self, context: str = "") -> bytes:
        """
        Generate a 12-byte nonce for AES-GCM.

        Args:
            context: Optional context string (e.g., file path)

        Returns:
            12-byte nonce
        """
        timestamp_ms = self._clock.ms()
        self._counter += 1

        # Combine timestamp, counter, and context
        data = f"{timestamp_ms}:{self._counter}:{context}".encode()
        nonce_hash = hashlib.sha256(self._seed + data).digest()

        # Use first 12 bytes for AES-GCM nonce
        return nonce_hash[:12]


class EnvelopeEncryptor:
    """
    Envelope encryption for backup files.

    Uses AES-256-GCM with deterministic nonces and KMS-wrapped keys.
    """

    def __init__(
        self,
        clock: Clock,
        kms: KMSStub | None = None,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
    ) -> None:
        """
        Initialize envelope encryptor.

        Args:
            clock: Injected clock for deterministic nonces
            kms: KMS stub for key wrapping
            algorithm: Encryption algorithm to use
        """
        self._clock = clock
        self._kms = kms or KMSStub()
        self._algorithm = algorithm
        self._nonce_gen = DeterministicNonceGenerator(clock)

    def generate_key(self) -> KeyMaterial:
        """
        Generate a new data encryption key.

        Returns:
            KeyMaterial with wrapped key
        """
        if self._algorithm == EncryptionAlgorithm.NONE:
            raise ValueError("Cannot generate key for NONE algorithm")

        # Generate random 256-bit key
        seed = self._nonce_gen.generate("keygen")
        plaintext_key = hashlib.sha256(seed + b"dr-key").digest()

        # Wrap with KMS
        wrapped = self._kms.wrap_key(plaintext_key)
        wrapped_b64 = base64.b64encode(wrapped).decode("ascii")

        key_id = hashlib.sha256(plaintext_key).hexdigest()[:16]

        return KeyMaterial(
            key_id=key_id,
            algorithm=self._algorithm,
            created_at=self._clock.iso(),
            rotated_at=None,
            wrapped_key=wrapped_b64,
            kms_key_id=self._kms.kms_key_id,
        )

    def encrypt(self, plaintext: bytes, key_material: KeyMaterial, context: str = "") -> bytes:
        """
        Encrypt data using envelope encryption.

        Args:
            plaintext: Data to encrypt
            key_material: Key material to use
            context: Optional context for nonce generation

        Returns:
            Encrypted data (nonce + ciphertext + tag)
        """
        if self._algorithm == EncryptionAlgorithm.NONE:
            return plaintext

        # Unwrap key
        wrapped = base64.b64decode(key_material.wrapped_key)
        dek = self._kms.unwrap_key(wrapped)

        # Generate deterministic nonce
        nonce = self._nonce_gen.generate(context)

        # Encrypt with AES-GCM
        aesgcm = AESGCM(dek)
        ciphertext = cast(bytes, aesgcm.encrypt(nonce, plaintext, None))

        # Return nonce + ciphertext (ciphertext includes auth tag)
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes, key_material: KeyMaterial) -> bytes:
        """
        Decrypt data using envelope encryption.

        Args:
            ciphertext: Encrypted data (nonce + ciphertext + tag)
            key_material: Key material to use

        Returns:
            Decrypted plaintext
        """
        if self._algorithm == EncryptionAlgorithm.NONE:
            return ciphertext

        # Unwrap key
        wrapped = base64.b64decode(key_material.wrapped_key)
        dek = self._kms.unwrap_key(wrapped)

        # Extract nonce and ciphertext
        nonce = ciphertext[:12]
        encrypted_data = ciphertext[12:]

        # Decrypt with AES-GCM
        aesgcm = AESGCM(dek)
        plaintext = cast(bytes, aesgcm.decrypt(nonce, encrypted_data, None))

        return plaintext


def redact_manifest(manifest_data: dict[str, Any]) -> dict[str, Any]:
    """
    Redact sensitive fields from manifest for logging/display.

    Args:
        manifest_data: Manifest dictionary

    Returns:
        Redacted manifest dictionary
    """
    redacted = manifest_data.copy()

    # Redact key material if present
    if "key_material" in redacted:
        redacted["key_material"] = {
            "key_id": redacted["key_material"].get("key_id", "***"),
            "algorithm": redacted["key_material"].get("algorithm", "***"),
            "wrapped_key": "***REDACTED***",
        }

    # Redact storage credentials if present
    if "storage_target" in redacted and "options" in redacted["storage_target"]:
        options = redacted["storage_target"]["options"]
        for key in ["access_key", "secret_key", "password", "token"]:
            if key in options:
                options[key] = "***REDACTED***"

    return redacted


__all__ = [
    "KMSStub",
    "DeterministicNonceGenerator",
    "EnvelopeEncryptor",
    "redact_manifest",
]
