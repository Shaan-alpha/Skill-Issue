from __future__ import annotations

import base64
import os
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class InvalidEncKey(Exception):
    """Raised when SESSION_TOKEN_ENC_KEY is missing, malformed, or wrong length."""


def load_enc_key() -> bytes:
    """Load the 32-byte AES-GCM key from SESSION_TOKEN_ENC_KEY (base64 url-safe).

    Fails fast at boot — better to refuse to start than to encrypt with a weak key.
    """
    raw = os.environ.get("SESSION_TOKEN_ENC_KEY")
    if not raw:
        raise InvalidEncKey("SESSION_TOKEN_ENC_KEY env var is required")
    try:
        key = base64.urlsafe_b64decode(raw)
    except Exception as exc:
        raise InvalidEncKey(f"SESSION_TOKEN_ENC_KEY is not valid base64: {exc}") from exc
    if len(key) != 32:
        raise InvalidEncKey(f"SESSION_TOKEN_ENC_KEY must decode to 32 bytes, got {len(key)}")
    return key


def encrypt_access_token(key: bytes, plaintext: str) -> tuple[bytes, bytes]:
    """Return (ciphertext, nonce). Caller persists both."""
    nonce = secrets.token_bytes(12)
    aes = AESGCM(key)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return ct, nonce


def decrypt_access_token(key: bytes, ct: bytes, nonce: bytes) -> str:
    aes = AESGCM(key)
    try:
        plaintext = aes.decrypt(nonce, ct, associated_data=None)
    except InvalidTag as exc:
        raise InvalidEncKey("AES-GCM tag check failed (wrong key, ct, or nonce)") from exc
    return plaintext.decode("utf-8")
