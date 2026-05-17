import base64
import secrets

import pytest

from app.auth.crypto import (
    InvalidEncKey,
    decrypt_access_token,
    encrypt_access_token,
    load_enc_key,
)


def _key_b64() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def test_roundtrip_recovers_plaintext(monkeypatch):
    monkeypatch.setenv("SESSION_TOKEN_ENC_KEY", _key_b64())
    key = load_enc_key()
    ct, nonce = encrypt_access_token(key, "ghp_secret_token")
    assert isinstance(ct, bytes) and isinstance(nonce, bytes)
    assert len(nonce) == 12
    assert decrypt_access_token(key, ct, nonce) == "ghp_secret_token"


def test_each_encryption_has_unique_nonce(monkeypatch):
    monkeypatch.setenv("SESSION_TOKEN_ENC_KEY", _key_b64())
    key = load_enc_key()
    _, n1 = encrypt_access_token(key, "x")
    _, n2 = encrypt_access_token(key, "x")
    assert n1 != n2


def test_wrong_nonce_fails_decryption(monkeypatch):
    monkeypatch.setenv("SESSION_TOKEN_ENC_KEY", _key_b64())
    key = load_enc_key()
    ct, _ = encrypt_access_token(key, "x")
    with pytest.raises(InvalidEncKey):
        decrypt_access_token(key, ct, b"\x00" * 12)


def test_bad_key_length_fails_fast(monkeypatch):
    monkeypatch.setenv("SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(b"too-short").decode())
    with pytest.raises(InvalidEncKey):
        load_enc_key()


def test_missing_key_env_fails_fast(monkeypatch):
    monkeypatch.delenv("SESSION_TOKEN_ENC_KEY", raising=False)
    with pytest.raises(InvalidEncKey):
        load_enc_key()
