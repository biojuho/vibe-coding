from __future__ import annotations

import sys
import time
import types
from unittest.mock import patch

import pytest

from pipeline import db_backend


class FakeScript:
    def __init__(self, client: "FakeRedisClient"):
        self._client = client

    def __call__(self, *, keys, args):
        self._client.script_calls.append({"keys": keys, "args": args})
        if self._client.script_exception is not None:
            raise self._client.script_exception
        return self._client.script_result


class FakeRedisClient:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.set_calls: list[dict] = []
        self.setex_calls: list[dict] = []
        self.delete_calls: list[tuple[str, ...]] = []
        self.scan_calls: list[dict] = []
        self.scan_responses: list[tuple[int, list[str]]] = []
        self.script_calls: list[dict] = []
        self.script_result = 1
        self.script_exception: Exception | None = None
        self.eval_calls: list[dict] = []
        self.eval_result = 1
        self.eval_exception: Exception | None = None

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        self.set_calls.append({"key": key, "value": value, "nx": nx, "ex": ex})
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def setex(self, key: str, ttl: int, value: str):
        self.setex_calls.append({"key": key, "ttl": ttl, "value": value})
        self.store[key] = value
        return True

    def delete(self, *keys: str):
        self.delete_calls.append(tuple(keys))
        for key in keys:
            self.store.pop(key, None)

    def scan(self, cursor: int, match: str | None = None, count: int | None = None):
        self.scan_calls.append({"cursor": cursor, "match": match, "count": count})
        if self.scan_responses:
            return self.scan_responses.pop(0)
        return 0, []

    def register_script(self, script: str):
        self.registered_script = script
        return FakeScript(self)

    def eval(self, script: str, numkeys: int, name: str, lock_id: str):
        self.eval_calls.append(
            {
                "script": script,
                "numkeys": numkeys,
                "name": name,
                "lock_id": lock_id,
            }
        )
        if self.eval_exception is not None:
            raise self.eval_exception
        return self.eval_result


@pytest.fixture
def fake_redis_client(monkeypatch: pytest.MonkeyPatch) -> FakeRedisClient:
    client = FakeRedisClient()
    redis_module = types.SimpleNamespace(
        from_url=lambda *args, **kwargs: client,
    )
    monkeypatch.setitem(sys.modules, "redis", redis_module)
    return client


def test_redis_cache_backend_round_trips_json_and_raw_values(fake_redis_client: FakeRedisClient):
    backend = db_backend.RedisCacheBackend(prefix="unit", redis_url="redis://fake")

    backend.set("json", {"topic": "career"}, ttl_seconds=30)
    backend.set("raw", "hello")
    fake_redis_client.store["unit:broken"] = "{oops"

    assert backend.get("json") == {"topic": "career"}
    assert backend.get("raw") == "hello"
    assert backend.get("broken") == "{oops"

    backend.delete("raw")

    assert fake_redis_client.setex_calls == [{"key": "unit:json", "ttl": 30, "value": '{"topic": "career"}'}]
    assert fake_redis_client.set_calls[-1] == {
        "key": "unit:raw",
        "value": "hello",
        "nx": False,
        "ex": None,
    }
    assert "unit:raw" not in fake_redis_client.store


def test_redis_cache_backend_clear_deletes_all_scanned_keys(fake_redis_client: FakeRedisClient):
    fake_redis_client.store.update(
        {
            "unit:a": "1",
            "unit:b": "2",
            "unit:c": "3",
        }
    )
    fake_redis_client.scan_responses = [
        (1, ["unit:a", "unit:b"]),
        (0, ["unit:c"]),
    ]
    backend = db_backend.RedisCacheBackend(prefix="unit", redis_url="redis://fake")

    backend.clear()

    assert fake_redis_client.scan_calls == [
        {"cursor": 0, "match": "unit:*", "count": 100},
        {"cursor": 1, "match": "unit:*", "count": 100},
    ]
    assert fake_redis_client.delete_calls == [("unit:a", "unit:b"), ("unit:c",)]
    assert fake_redis_client.store == {}


def test_distributed_rate_limiter_uses_provider_limits_and_script_result(
    fake_redis_client: FakeRedisClient,
):
    limiter = db_backend.DistributedRateLimiter(redis_url="redis://fake")

    with patch("time.time", return_value=123.5):
        allowed = limiter.acquire("gemini", cost=2)

    assert allowed is True
    assert fake_redis_client.script_calls == [{"keys": ["ratelimit:gemini"], "args": [10, 60, 2, 123.5]}]


def test_distributed_rate_limiter_fail_open_and_wait_retry(monkeypatch: pytest.MonkeyPatch):
    limiter = db_backend.DistributedRateLimiter.__new__(db_backend.DistributedRateLimiter)
    limiter._script = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("redis down"))  # type: ignore[attr-defined]

    assert db_backend.DistributedRateLimiter.acquire(limiter, "openai") is True

    retrying = db_backend.DistributedRateLimiter.__new__(db_backend.DistributedRateLimiter)
    attempts = {"count": 0}
    sleeps: list[float] = []
    clock = {"now": 0.0}

    def fake_acquire(provider: str, cost: int = 1) -> bool:
        attempts["count"] += 1
        return attempts["count"] >= 3

    def fake_time() -> float:
        current = clock["now"]
        clock["now"] += 0.05
        return current

    retrying.acquire = fake_acquire  # type: ignore[method-assign]
    monkeypatch.setattr(time, "time", fake_time)
    monkeypatch.setattr(time, "sleep", lambda seconds: sleeps.append(seconds))

    assert retrying.wait_and_acquire("gemini", max_wait=1.0) is True
    assert attempts["count"] == 3
    assert sleeps == [0.1, 0.1]


def test_distributed_lock_acquire_and_release(fake_redis_client: FakeRedisClient):
    lock = db_backend.DistributedLock(redis_url="redis://fake")

    lock_id = lock.acquire(name="btx:test:lock", ttl=15)
    released = lock.release(name="btx:test:lock", lock_id=lock_id or "")

    assert isinstance(lock_id, str) and lock_id
    assert fake_redis_client.set_calls[0]["key"] == "btx:test:lock"
    assert fake_redis_client.set_calls[0]["nx"] is True
    assert fake_redis_client.set_calls[0]["ex"] == 15
    assert released is True
    assert fake_redis_client.eval_calls[0]["name"] == "btx:test:lock"
    assert fake_redis_client.eval_calls[0]["lock_id"] == lock_id


def test_backend_factories_return_expected_objects_or_safe_none(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis_client: FakeRedisClient,
):
    monkeypatch.setenv("BTX_CACHE_BACKEND", "sqlite")
    assert db_backend.get_cache_backend() is None
    assert db_backend.get_rate_limiter() is None

    monkeypatch.setenv("BTX_CACHE_BACKEND", "redis")
    cache_backend = db_backend.get_cache_backend(prefix="factory")
    limiter = db_backend.get_rate_limiter()

    assert isinstance(cache_backend, db_backend.RedisCacheBackend)
    assert isinstance(limiter, db_backend.DistributedRateLimiter)
    assert cache_backend._prefix == "factory"

    monkeypatch.setattr(
        db_backend,
        "RedisCacheBackend",
        lambda prefix="btx": (_ for _ in ()).throw(RuntimeError("cache down")),
    )
    monkeypatch.setattr(
        db_backend,
        "DistributedRateLimiter",
        lambda: (_ for _ in ()).throw(RuntimeError("rate down")),
    )

    assert db_backend.get_cache_backend(prefix="broken") is None
    assert db_backend.get_rate_limiter() is None
