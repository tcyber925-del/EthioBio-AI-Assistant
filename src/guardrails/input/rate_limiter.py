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



class TieredRateLimiter:
    def __init__(self, redis_url: str = ""):
        self._redis_url = redis_url
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url or settings.redis_url)
        return self._redis

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
        if not settings.rate_limit_enabled:
            return True, {}

        redis = await self._get_redis()
        tier = self.resolve_tier(path, method)
        rule = RATE_LIMIT_TIERS[tier]
        now = time.time()
        window_start = now - rule.window_seconds
        redis_key = f"ratelimit:{tier}:{key}"

        await redis.zremrangebyscore(redis_key, 0, window_start)
        count = await redis.zcard(redis_key)

        remaining = max(0, rule.max_requests - count)
        reset_time = int(now + rule.window_seconds)

        if count >= rule.max_requests:
            return False, {
                "X-RateLimit-Limit": str(rule.max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(rule.window_seconds),
            }

        await redis.zadd(redis_key, {str(now): now})
        await redis.expire(redis_key, rule.window_seconds * 2)

        return True, {
            "X-RateLimit-Limit": str(rule.max_requests),
            "X-RateLimit-Remaining": str(remaining - 1),
            "X-RateLimit-Reset": str(reset_time),
        }
