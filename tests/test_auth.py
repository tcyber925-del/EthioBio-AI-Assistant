from uuid import uuid4

import pytest

from src.api.auth import (
    _create_access_token,
    _hash_password,
    _verify_password,
    decode_access_token,
)
from src.config import settings
from src.core.errors import AuthError


def test_hash_and_verify_password():
    password = "test-password-123"
    hashed = _hash_password(password)
    assert hashed != password
    assert _verify_password(password, hashed)
    assert not _verify_password("wrong-password", hashed)


def test_create_and_decode_token():
    user_id = str(uuid4())
    token = _create_access_token(user_id, "teacher")
    assert token

    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "teacher"
    assert "exp" in payload


def test_decode_invalid_token_raises():
    with pytest.raises(AuthError):
        decode_access_token("invalid.token.here")


def test_token_expiry():
    old_expire = settings.access_token_expire_minutes
    settings.access_token_expire_minutes = -1
    try:
        user_id = str(uuid4())
        token = _create_access_token(user_id, "teacher")
        with pytest.raises(AuthError):
            decode_access_token(token)
    finally:
        settings.access_token_expire_minutes = old_expire


def test_token_contains_role():
    user_id = str(uuid4())
    token = _create_access_token(user_id, "admin")
    payload = decode_access_token(token)
    assert payload["role"] == "admin"


def test_different_tokens_for_different_users():
    token_a = _create_access_token(str(uuid4()), "teacher")
    token_b = _create_access_token(str(uuid4()), "teacher")
    assert token_a != token_b


def test_otp_verify_rejects_missing_otp():
    pass


def test_otp_request_rejects_unknown_telegram_id():
    pass
