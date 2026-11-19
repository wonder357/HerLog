"""皮肤分析的短时暂存：Redis 按会员 + 随机 analysis_id 存一张图和观察，TTL 10 分钟。"""

from __future__ import annotations

import json
import time
from typing import Any, Protocol

from app.core.config import settings


class PendingStore(Protocol):
    def put(self, customer_id: str, analysis_id: str, payload: dict[str, Any], ttl: int) -> None: ...

    def get(self, customer_id: str, analysis_id: str) -> dict[str, Any] | None: ...

    def delete(self, customer_id: str, analysis_id: str) -> None: ...


class MemoryPendingStore:
    """单进程后备实现，测试与无 Redis 的本地演示使用。"""

    def __init__(self, max_per_member: int) -> None:
        self._items: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
        self._max = max_per_member

    def put(self, customer_id: str, analysis_id: str, payload: dict[str, Any], ttl: int) -> None:
        now = time.time()
        self._items = {key: value for key, value in self._items.items() if value[0] > now}
        owned = [key for key in self._items if key[0] == customer_id]
        if len(owned) >= self._max:
            oldest = min(owned, key=lambda key: self._items[key][0])
            del self._items[oldest]
        self._items[(customer_id, analysis_id)] = (now + ttl, payload)

    def get(self, customer_id: str, analysis_id: str) -> dict[str, Any] | None:
        item = self._items.get((customer_id, analysis_id))
        if item is None:
            return None
        expires_at, payload = item
        if expires_at <= time.time():
            self._items.pop((customer_id, analysis_id), None)
            return None
        return payload

    def delete(self, customer_id: str, analysis_id: str) -> None:
        self._items.pop((customer_id, analysis_id), None)


class RedisPendingStore:
    PREFIX = "herlog:pending:"

    def __init__(self, client: Any, max_per_member: int) -> None:
        self._client = client
        self._max = max_per_member

    def _key(self, customer_id: str, analysis_id: str) -> str:
        return f"{self.PREFIX}{customer_id}:{analysis_id}"

    def _index(self, customer_id: str) -> str:
        return f"{self.PREFIX}index:{customer_id}"

    def put(self, customer_id: str, analysis_id: str, payload: dict[str, Any], ttl: int) -> None:
        key = self._key(customer_id, analysis_id)
        self._client.setex(key, ttl, json.dumps(payload, ensure_ascii=False))
        index = self._index(customer_id)
        self._client.zadd(index, {analysis_id: time.time()})
        self._client.expire(index, ttl * 2)
        overflow = self._client.zrange(index, 0, -(self._max + 1))
        for stale in overflow:
            name = stale.decode() if isinstance(stale, bytes) else stale
            self._client.delete(self._key(customer_id, name))
            self._client.zrem(index, name)

    def get(self, customer_id: str, analysis_id: str) -> dict[str, Any] | None:
        raw = self._client.get(self._key(customer_id, analysis_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def delete(self, customer_id: str, analysis_id: str) -> None:
        self._client.delete(self._key(customer_id, analysis_id))
        self._client.zrem(self._index(customer_id), analysis_id)


def build_pending_store() -> PendingStore:
    if settings.REDIS_ENABLED:
        import redis

        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            socket_timeout=2,
        )
        client.ping()
        return RedisPendingStore(client, settings.PENDING_MAX_PER_MEMBER)
    return MemoryPendingStore(settings.PENDING_MAX_PER_MEMBER)


_memory_store = MemoryPendingStore(settings.PENDING_MAX_PER_MEMBER)


def get_pending_store() -> PendingStore:
    """FastAPI 依赖；未启用 Redis 时退化为进程内暂存。"""

    if settings.REDIS_ENABLED:
        return build_pending_store()
    return _memory_store
