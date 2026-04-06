"""Database backend abstraction for blind-to-x pipeline.

Provides a pluggable backend interface so the pipeline can switch between
SQLite (current, for local dev) and PostgreSQL/Redis (for 100x scale)
without changing any calling code.

Usage:
    # Current behavior (unchanged):
    from pipeline.cost_db import get_cost_db
    db = get_cost_db()  # Returns SQLite-backed CostDatabase

    # Future: Override via environment variable
    # BTX_DB_BACKEND=postgresql → PostgreSQL backend
    # BTX_CACHE_BACKEND=redis  → Redis-backed DraftCache
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ── Abstract Cache Protocol ──────────────────────────────────────────


@runtime_checkable
class CacheBackend(Protocol):
    """Cache backend interface for DraftCache and EmbeddingCache."""

    def get(self, key: str) -> Any | None:
        """캐시에서 값을 조회합니다. 없으면 None."""
        ...

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """캐시에 값을 저장합니다. ttl_seconds 후 만료."""
        ...

    def delete(self, key: str) -> None:
        """캐시에서 키를 삭제합니다."""
        ...

    def clear(self) -> None:
        """캐시를 초기화합니다."""
        ...


# ── Redis Cache Backend ──────────────────────────────────────────────


class RedisCacheBackend:
    """Redis-backed cache for draft cache and embedding cache.

    Requires: pip install redis
    환경 변수: BTX_REDIS_URL (기본: redis://localhost:6379/0)
    """

    def __init__(self, prefix: str = "btx", redis_url: str | None = None):
        import redis

        self._url = redis_url or os.environ.get("BTX_REDIS_URL", "redis://localhost:6379/0")
        self._prefix = prefix
        self._r = redis.from_url(self._url, decode_responses=True)
        logger.info("RedisCacheBackend initialized: prefix=%s, url=%s", prefix, self._url.split("@")[-1])

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Any | None:
        import json

        raw = self._r.get(self._key(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        import json

        serialized = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        if ttl_seconds:
            self._r.setex(self._key(key), ttl_seconds, serialized)
        else:
            self._r.set(self._key(key), serialized)

    def delete(self, key: str) -> None:
        self._r.delete(self._key(key))

    def clear(self) -> None:
        """PREFIX 기반 키만 삭제 (SCAN 사용, 안전)."""
        cursor = 0
        pattern = f"{self._prefix}:*"
        max_iters = 10_000  # [QA 수정] A-3: 무한 루프 방지
        for _ in range(max_iters):
            cursor, keys = self._r.scan(cursor, match=pattern, count=100)
            if keys:
                self._r.delete(*keys)
            if cursor == 0:
                break
        else:
            logger.warning("RedisCacheBackend.clear(): max iterations reached (%d)", max_iters)


# ── Distributed Rate Limiter ──────────────────────────────────────────


class DistributedRateLimiter:
    """Redis Token Bucket 기반 분산 Rate Limiter.

    프로바이더별 초당/분당 요청 수를 제어합니다.

    Usage:
        limiter = DistributedRateLimiter()
        if limiter.acquire("openai"):
            # API 호출 진행
        else:
            # 대기 또는 스킵
    """

    # 프로바이더별 기본 설정: tokens_per_sec, burst (최대 동시 토큰)
    DEFAULT_LIMITS: dict[str, dict[str, float]] = {
        "openai": {"tokens_per_sec": 50, "burst": 200},
        "gemini": {"tokens_per_sec": 10, "burst": 60},
        "notion": {"tokens_per_sec": 3, "burst": 10},
        "twitter": {"tokens_per_sec": 0.5, "burst": 5},
        "cloudinary": {"tokens_per_sec": 10, "burst": 50},
    }

    # Lua script: atomic token bucket implementation
    _LUA_ACQUIRE = """
    local key = KEYS[1]
    local rate = tonumber(ARGV[1])
    local burst = tonumber(ARGV[2])
    local cost = tonumber(ARGV[3])
    local now = tonumber(ARGV[4])

    local data = redis.call('HMGET', key, 'tokens', 'last')
    local tokens = tonumber(data[1]) or burst
    local last = tonumber(data[2]) or now

    local elapsed = now - last
    tokens = math.min(burst, tokens + elapsed * rate)

    if tokens >= cost then
        tokens = tokens - cost
        redis.call('HMSET', key, 'tokens', tokens, 'last', now)
        redis.call('EXPIRE', key, 120)
        return 1
    end
    return 0
    """

    def __init__(self, redis_url: str | None = None):
        import redis

        self._url = redis_url or os.environ.get("BTX_REDIS_URL", "redis://localhost:6379/0")
        self._r = redis.from_url(self._url)
        self._script = self._r.register_script(self._LUA_ACQUIRE)
        logger.info("DistributedRateLimiter initialized: %s", self._url.split("@")[-1])

    def acquire(self, provider: str, cost: int = 1) -> bool:
        """토큰 획득 시도. 허용되면 True, Rate Limit 초과 시 False."""
        import time

        limit = self.DEFAULT_LIMITS.get(provider, {"tokens_per_sec": 1, "burst": 5})
        key = f"ratelimit:{provider}"
        try:
            result = self._script(
                keys=[key],
                args=[limit["tokens_per_sec"], limit["burst"], cost, time.time()],
            )
            return bool(result)
        except Exception as exc:
            logger.warning("RateLimiter.acquire(%s) failed: %s — allowing", provider, exc)
            return True  # Redis 장애 시 허용 (fail-open)

    def wait_and_acquire(self, provider: str, cost: int = 1, max_wait: float = 30.0) -> bool:
        """토큰 획득할 때까지 대기. max_wait 초 초과 시 False."""
        import time

        deadline = time.time() + max_wait
        while time.time() < deadline:
            if self.acquire(provider, cost):
                return True
            time.sleep(0.1)
        return False


# ── Distributed Lock ──────────────────────────────────────────────────


class DistributedLock:
    """Redis 기반 분산 락.

    현재 파이프라인의 파일 기반 .running.lock을 대체합니다.
    """

    def __init__(self, redis_url: str | None = None):
        import redis

        self._url = redis_url or os.environ.get("BTX_REDIS_URL", "redis://localhost:6379/0")
        self._r = redis.from_url(self._url)

    def acquire(self, name: str = "btx:pipeline:lock", ttl: int = 3600) -> str | None:
        """락 획득 시도. 성공 시 lock_id 반환, 이미 잠겨있으면 None."""
        import uuid

        lock_id = str(uuid.uuid4())
        acquired = self._r.set(name, f"{os.getpid()}:{lock_id}", nx=True, ex=ttl)
        if acquired:
            logger.info("DistributedLock acquired: %s (ttl=%ds)", name, ttl)
            return lock_id
        logger.warning("DistributedLock NOT acquired: %s (already held)", name)
        return None

    def release(self, name: str = "btx:pipeline:lock", lock_id: str = "") -> bool:
        """락 해제. 자신이 보유한 락만 해제합니다."""
        lua = """
        local key = KEYS[1]
        local expected = ARGV[1]
        local val = redis.call('GET', key)
        if val and string.find(val, expected) then
            redis.call('DEL', key)
            return 1
        end
        return 0
        """
        try:
            result = self._r.eval(lua, 1, name, lock_id)
            return bool(result)
        except Exception as exc:
            logger.warning("DistributedLock.release(%s) failed: %s", name, exc)
            return False


# ── Backend Factory ──────────────────────────────────────────────────


def get_cache_backend(prefix: str = "btx") -> CacheBackend | None:
    """환경 변수 BTX_CACHE_BACKEND에 따라 캐시 백엔드 반환.

    - "redis" → RedisCacheBackend
    - 없거나 "sqlite" → None (기존 SQLite 캐시 사용)
    """
    backend = os.environ.get("BTX_CACHE_BACKEND", "sqlite").lower()
    if backend == "redis":
        try:
            return RedisCacheBackend(prefix=prefix)
        except Exception as exc:
            logger.warning("Failed to create Redis cache backend: %s — falling back to SQLite", exc)
            return None
    return None


def get_rate_limiter() -> DistributedRateLimiter | None:
    """환경 변수 BTX_CACHE_BACKEND=redis일 때만 Rate Limiter 반환."""
    backend = os.environ.get("BTX_CACHE_BACKEND", "sqlite").lower()
    if backend == "redis":
        try:
            return DistributedRateLimiter()
        except Exception as exc:
            logger.warning("Failed to create DistributedRateLimiter: %s", exc)
            return None
    return None
