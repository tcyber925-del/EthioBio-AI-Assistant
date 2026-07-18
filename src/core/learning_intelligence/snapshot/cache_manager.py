import json

from redis.asyncio import Redis

from src.config import settings


class CacheManager:
    KEY_PREFIX = "learner_snapshot:"

    def __init__(
        self,
        redis_url: str | None = None,
        default_ttl: int = 300,
    ):
        self._redis: Redis | None = None
        self._redis_url = redis_url or settings.redis_url
        self.default_ttl = default_ttl

    async def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    def _key(self, user_id: str) -> str:
        return f"{self.KEY_PREFIX}{user_id}"

    async def get(self, user_id: str) -> dict | None:
        client = await self._client()
        raw = await client.get(self._key(user_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, user_id: str, data: dict, ttl: int | None = None) -> None:
        client = await self._client()
        await client.set(
            self._key(user_id),
            json.dumps(data, default=str),
            ex=ttl or self.default_ttl,
        )

    async def delete(self, user_id: str) -> None:
        client = await self._client()
        await client.delete(self._key(user_id))

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
