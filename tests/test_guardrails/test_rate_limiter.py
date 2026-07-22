from unittest.mock import AsyncMock, MagicMock

import pytest

from src.guardrails.input.rate_limiter import TieredRateLimiter


@pytest.mark.asyncio
async def test_tier_resolution():
    limiter = TieredRateLimiter(MagicMock())
    assert limiter.resolve_tier("/auth/login", "POST") == "auth"
    assert limiter.resolve_tier("/auth/request-otp", "POST") == "otp"
    assert limiter.resolve_tier("/auth/verify-otp", "POST") == "otp"
    assert limiter.resolve_tier("/chat/stream", "POST") == "chat"
    assert limiter.resolve_tier("/internal/health", "GET") == "internal"
    assert limiter.resolve_tier("/quiz/generate", "POST") == "write"
    assert limiter.resolve_tier("/quiz/list", "GET") == "read"


@pytest.mark.asyncio
async def test_rate_limit_allowed():
    mock_redis = AsyncMock()
    mock_redis.zremrangebyscore.return_value = 0
    mock_redis.zcard.return_value = 0
    mock_redis.zadd.return_value = 1

    limiter = TieredRateLimiter(mock_redis)
    allowed, headers = await limiter.check_and_get_headers("test_key", "/auth/login", "POST")
    assert allowed
    assert "X-RateLimit-Limit" in headers


@pytest.mark.asyncio
async def test_rate_limit_blocked():
    mock_redis = AsyncMock()
    mock_redis.zremrangebyscore.return_value = 0
    mock_redis.zcard.return_value = 5

    limiter = TieredRateLimiter(mock_redis)
    allowed, headers = await limiter.check_and_get_headers("test_key", "/auth/login", "POST")
    assert not allowed
    assert headers["X-RateLimit-Remaining"] == "0"
