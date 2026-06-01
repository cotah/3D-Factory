"""Unit tests for password hashing and JWT helpers."""

from __future__ import annotations

import time

import jwt
import pytest

from app.core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext():
    hashed = hash_password("my-secret")
    assert hashed != "my-secret"
    assert hashed.startswith("$2")  # bcrypt prefix


def test_verify_password_roundtrip():
    hashed = hash_password("correct-horse")
    assert verify_password("correct-horse", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_handles_invalid_hash():
    assert verify_password("anything", "not-a-real-hash") is False


def test_hash_password_handles_long_input():
    # bcrypt truncates above 72 bytes; this must not raise.
    long_pw = "a" * 200
    hashed = hash_password(long_pw)
    assert verify_password(long_pw, hashed) is True


def test_access_token_contains_expected_claims():
    token = create_access_token(42)
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == TOKEN_TYPE_ACCESS


def test_refresh_token_type():
    token = create_refresh_token(7)
    payload = decode_token(token)
    assert payload["sub"] == "7"
    assert payload["type"] == TOKEN_TYPE_REFRESH


def test_decode_invalid_token_raises():
    with pytest.raises(jwt.PyJWTError):
        decode_token("clearly.not.a.jwt")


def test_decode_tampered_token_raises():
    token = create_access_token(1)
    tampered = token[:-3] + "abc"
    with pytest.raises(jwt.PyJWTError):
        decode_token(tampered)
