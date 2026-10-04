"""Fixed-window attempt limiter for credential checks (login, PIN, parental re-auth)."""

import time
from typing import Protocol

from redis.asyncio import Redis


class AttemptLimiter(Protocol):
    async def is_blocked(self, key: str, limit: int) -> bool: ...
    async def record_failure(self, key: str, window_s: int) -> None: ...
    async def reset(self, key: str) -> None: ...


class RedisAttemptLimiter:
    def __init__(self, redis: Redis, prefix: str = "pf:attempts:") -> None:
        self._r = redis
        self._prefix = prefix

    async def is_blocked(self, key: str, limit: int) -> bool:
        value = await self._r.get(self._prefix + key)
        return value is not None and int(value) >= limit

    async def record_failure(self, key: str, window_s: int) -> None:
        k = self._prefix + key
        async with self._r.pipeline(transaction=True) as pipe:
            pipe.incr(k)
            pipe.expire(k, window_s, nx=True)  # window starts at the first failure
            await pipe.execute()

    async def reset(self, key: str) -> None:
        await self._r.delete(self._prefix + key)


class MemoryAttemptLimiter:
    """Single-process limiter for tests."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[int, float]] = {}

    def _get(self, key: str) -> int:
        count, expires = self._data.get(key, (0, 0.0))
        if expires and expires < time.monotonic():
            self._data.pop(key, None)
            return 0
        return count

    async def is_blocked(self, key: str, limit: int) -> bool:
        return self._get(key) >= limit

    async def record_failure(self, key: str, window_s: int) -> None:
        count = self._get(key)
        expires = self._data.get(key, (0, time.monotonic() + window_s))[1]
        self._data[key] = (count + 1, expires if count else time.monotonic() + window_s)

    async def reset(self, key: str) -> None:
        self._data.pop(key, None)
