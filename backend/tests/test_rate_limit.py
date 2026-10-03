import os
import uuid

import pytest
from redis.asyncio import Redis

from app.services.rate_limit import MemoryAttemptLimiter, RedisAttemptLimiter

REDIS_URL = os.environ.get("POLYFLOW_TEST_REDIS_URL")


async def _exercise(limiter, key: str) -> None:
    assert not await limiter.is_blocked(key, 2)
    await limiter.record_failure(key, 60)
    assert not await limiter.is_blocked(key, 2)
    await limiter.record_failure(key, 60)
    assert await limiter.is_blocked(key, 2)
    await limiter.reset(key)
    assert not await limiter.is_blocked(key, 2)


async def test_memory_limiter():
    await _exercise(MemoryAttemptLimiter(), "k")


@pytest.mark.skipif(not REDIS_URL, reason="POLYFLOW_TEST_REDIS_URL not set")
async def test_redis_limiter():
    redis = Redis.from_url(REDIS_URL)
    try:
        await _exercise(RedisAttemptLimiter(redis), f"test:{uuid.uuid4()}")
    finally:
        await redis.aclose()
