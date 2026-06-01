from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.learning_intelligence.snapshot.cache_manager import CacheManager


@pytest.fixture
def cache():
    return CacheManager(redis_url="redis://localhost:6379/0", default_ttl=300)


async def test_cache_key_format(cache):
    uid = str(uuid4())
    assert cache._key(uid) == f"learner_snapshot:{uid}"


async def test_cache_miss_returns_none(cache):
    cache._client = AsyncMock()
    cache._client.return_value.get = AsyncMock(return_value=None)

    result = await cache.get(str(uuid4()))
    assert result is None


async def test_cache_hit_returns_parsed_data(cache):
    uid = str(uuid4())
    expected = {"user_id": uid, "weak_topics": ["Genetics"]}

    cache._client = AsyncMock()
    cache._client.return_value.get = AsyncMock(
        return_value=f'{{"user_id": "{uid}", "weak_topics": ["Genetics"]}}'
    )

    result = await cache.get(uid)
    assert result == expected


async def test_cache_set_stores_serialized(cache):
    uid = str(uuid4())
    data = {"user_id": uid, "weak_topics": ["Genetics"]}

    mock_redis = AsyncMock()
    cache._client = AsyncMock(return_value=mock_redis)

    await cache.set(uid, data)
    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert args[0] == f"learner_snapshot:{uid}"


async def test_cache_delete_removes_key(cache):
    uid = str(uuid4())

    mock_redis = AsyncMock()
    cache._client = AsyncMock(return_value=mock_redis)

    await cache.delete(uid)
    mock_redis.delete.assert_called_once_with(f"learner_snapshot:{uid}")
