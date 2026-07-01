import time

import structlog
from redis.asyncio import Redis

from src.config import settings

logger = structlog.get_logger()


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
