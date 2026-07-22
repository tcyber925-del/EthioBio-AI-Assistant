import time
from dataclasses import dataclass

import structlog
from redis.asyncio import Redis

from src.config import settings

logger = structlog.get_logger()


@dataclass
class RateLimitRule:
    window_seconds: int
    max_requests: int


RATE_LIMIT_TIERS: dict[str, RateLimitRule] = {
    "auth":     RateLimitRule(window_seconds=60,   max_requests=5),
    "otp":      RateLimitRule(window_seconds=300,  max_requests=3),
    "chat":     RateLimitRule(window_seconds=60,   max_requests=20),
    "write":    RateLimitRule(window_seconds=60,   max_requests=30),
    "read":     RateLimitRule(window_seconds=60,   max_requests=100),
    "internal": RateLimitRule(window_seconds=60,   max_requests=500),
}


class RateLimiter:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._enabled = settings.rate_limit_enabled

    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        if not self._enabled:
            return True

        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"

        await self.redis.zremrangebyscore(redis_key, 0, window_start)
        count = await self.redis.zcard(redis_key)

        if count >= max_requests:
            return False

        await self.redis.zadd(redis_key, {str(now): now})
        await self.redis.expire(redis_key, window_seconds * 2)
        return True

    async def get_remaining(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> int:
        if not self._enabled:
            return max_requests

        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"

        await self.redis.zremrangebyscore(redis_key, 0, window_start)
        count = await self.redis.zcard(redis_key)
        return max(0, max_requests - count)


class TieredRateLimiter:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._enabled = settings.rate_limit_enabled

    def resolve_tier(self, path: str, method: str) -> str:
        if path.startswith("/internal/"):
            return "internal"
        if path in ("/auth/request-otp", "/auth/verify-otp"):
            return "otp"
        if path.startswith("/auth/"):
            return "auth"
        if path.startswith("/chat/"):
            return "chat"
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            return "write"
        return "read"

    async def check_and_get_headers(
        self, key: str, path: str, method: str
    ) -> tuple[bool, dict[str, str]]:
        if not self._enabled:
            return True, {}

        tier = self.resolve_tier(path, method)
        rule = RATE_LIMIT_TIERS[tier]
        now = time.time()
        window_start = now - rule.window_seconds
        redis_key = f"ratelimit:{tier}:{key}"

        await self.redis.zremrangebyscore(redis_key, 0, window_start)
        count = await self.redis.zcard(redis_key)

        remaining = max(0, rule.max_requests - count)

        if count >= rule.max_requests:
            return False, {
                "X-RateLimit-Limit": str(rule.max_requests),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(rule.window_seconds),
            }

        await self.redis.zadd(redis_key, {str(now): now})
        await self.redis.expire(redis_key, rule.window_seconds * 2)

        return True, {
            "X-RateLimit-Limit": str(rule.max_requests),
            "X-RateLimit-Remaining": str(remaining - 1),
        }
