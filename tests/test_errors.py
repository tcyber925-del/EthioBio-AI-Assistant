import pytest
from src.core.errors import AppError, AuthError, RateLimitError


def test_app_error_serialization():
    err = AppError(code="test_error", detail="Something broke", status=400, context={"key": "val"})
    d = err.to_dict()
    assert d["error"]["code"] == "test_error"
    assert d["error"]["detail"] == "Something broke"
    assert err.status == 400


def test_auth_error_subclass():
    err = AuthError("token_expired", "Token expired")
    assert err.status == 401
    assert err.code == "auth_token_expired"


def test_rate_limit_error_subclass():
    err = RateLimitError("chat", 30)
    assert err.status == 429
    assert "rate_limit_exceeded" in err.code
