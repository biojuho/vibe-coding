"""Unit tests for pipeline.spike_detector — SpikeDetector & _EngagementSnapshot."""

from __future__ import annotations

import time

import pytest

from pipeline.spike_detector import SpikeDetector, SpikeEvent, _EngagementSnapshot


# ── _EngagementSnapshot 테스트 ────────────────────────────────────────────


class TestEngagementSnapshot:
    """인메모리 스냅샷 저장소 단위 테스트."""

    def test_first_record_returns_none(self):
        snap = _EngagementSnapshot()
        result = snap.record("url1", likes=10, comments=5)
        assert result is None, "첫 스냅샷은 비교 대상이 없으므로 None"

    def test_second_record_returns_velocity(self):
        snap = _EngagementSnapshot()
        snap._store["url1"] = {"likes": 10, "comments": 5, "ts": time.time() - 120}
        result = snap.record("url1", likes=30, comments=15)
        assert result is not None
        assert "velocity_likes" in result
        assert "velocity_comments" in result
        assert result["velocity_likes"] > 0
        assert result["velocity_comments"] > 0
        assert result["elapsed_min"] > 0

    def test_too_short_interval_returns_none(self):
        snap = _EngagementSnapshot()
        snap._store["url1"] = {"likes": 10, "comments": 5, "ts": time.time() - 5}
        result = snap.record("url1", likes=30, comments=15)
        assert result is None, "30초 미만 간격은 무시"

    def test_velocity_calculation_accuracy(self):
        snap = _EngagementSnapshot()
        two_min_ago = time.time() - 120  # 2분 전
        snap._store["url1"] = {"likes": 10, "comments": 5, "ts": two_min_ago}

        result = snap.record("url1", likes=30, comments=15)
        assert result is not None
        # 2분 동안 likes 20개 증가 → ~10/분
        assert 8.0 <= result["velocity_likes"] <= 12.0
        # 2분 동안 comments 10개 증가 → ~5/분
        assert 4.0 <= result["velocity_comments"] <= 6.0

    def test_evict_stale_entries(self):
        snap = _EngagementSnapshot(ttl_seconds=60)
        old_ts = time.time() - 120  # TTL(60초) 초과
        snap._store["old_url"] = {"likes": 1, "comments": 1, "ts": old_ts}
        snap._store["fresh_url"] = {"likes": 1, "comments": 1, "ts": time.time()}

        snap.record("trigger", likes=1, comments=1)  # eviction 트리거
        assert "old_url" not in snap._store
        assert "fresh_url" in snap._store

    def test_max_entries_eviction(self):
        snap = _EngagementSnapshot(max_entries=3)
        now = time.time()
        for i in range(5):
            snap._store[f"url_{i}"] = {"likes": i, "comments": i, "ts": now + i}

        snap.record("new_url", likes=1, comments=1)
        assert len(snap._store) <= 4  # max_entries + new entry

    def test_negative_delta_treated_as_zero(self):
        snap = _EngagementSnapshot()
        snap._store["url1"] = {"likes": 50, "comments": 20, "ts": time.time() - 120}
        result = snap.record("url1", likes=30, comments=10)
        assert result is not None
        assert result["velocity_likes"] == 0.0, "감소는 0으로 처리"
        assert result["velocity_comments"] == 0.0


# ── SpikeDetector 테스트 ──────────────────────────────────────────────────


class _MockConfig:
    """스파이크 디텍터용 목 config."""

    def __init__(self, overrides=None):
        self._data = overrides or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


class TestSpikeDetector:
    """SpikeDetector 단위 테스트."""

    def _make_detector(self, threshold=5.0, min_likes=10):
        config = _MockConfig(
            {
                "escalation.velocity_threshold": threshold,
                "escalation.min_absolute_likes": min_likes,
            }
        )
        return SpikeDetector(config)

    @pytest.mark.asyncio
    async def test_no_candidates_returns_empty(self):
        detector = self._make_detector()
        spikes = await detector.scan(candidates=[])
        assert spikes == []

    @pytest.mark.asyncio
    async def test_first_scan_no_spikes(self):
        """첫 스캔은 스냅샷이 없으므로 스파이크 0."""
        detector = self._make_detector(min_likes=0)
        candidates = [
            {"url": "https://blind.com/1", "title": "테스트", "source": "blind", "likes": 100, "comments": 50},
        ]
        spikes = await detector.scan(candidates=candidates)
        assert len(spikes) == 0

    @pytest.mark.asyncio
    async def test_spike_detection_on_second_scan(self):
        """두 번째 스캔에서 velocity 돌파 시 스파이크 감지."""
        detector = self._make_detector(threshold=3.0, min_likes=5)

        # 1차 스캔: 스냅샷 등록
        candidates_t0 = [
            {"url": "https://blind.com/1", "title": "급등글", "source": "blind", "likes": 20, "comments": 10},
        ]
        await detector.scan(candidates=candidates_t0)

        # 스냅샷을 2분 전으로 조작
        key = "https://blind.com/1"
        if key in detector._snapshots._store:
            detector._snapshots._store[key]["ts"] -= 120

        # 2차 스캔: velocity 계산
        candidates_t1 = [
            {"url": "https://blind.com/1", "title": "급등글", "source": "blind", "likes": 50, "comments": 30},
        ]
        spikes = await detector.scan(candidates=candidates_t1)
        assert len(spikes) >= 1
        assert spikes[0].velocity_score > 0
        assert spikes[0].source == "blind"

    @pytest.mark.asyncio
    async def test_min_likes_filter(self):
        """최소 좋아요 미달은 스킵."""
        detector = self._make_detector(min_likes=50)
        candidates = [
            {"url": "https://blind.com/low", "title": "좋아요 적음", "source": "blind", "likes": 10, "comments": 5},
        ]
        spikes = await detector.scan(candidates=candidates)
        assert len(spikes) == 0

    @pytest.mark.asyncio
    async def test_spikes_sorted_by_velocity_desc(self):
        """결과가 velocity_score 내림차순 정렬."""
        detector = self._make_detector(threshold=1.0, min_likes=0)

        # 스냅샷 사전 등록 (2분 전)
        old_ts = time.time() - 120
        detector._snapshots._store["https://a.com/1"] = {"likes": 5, "comments": 2, "ts": old_ts}
        detector._snapshots._store["https://b.com/2"] = {"likes": 5, "comments": 2, "ts": old_ts}

        candidates = [
            {"url": "https://a.com/1", "title": "A", "source": "blind", "likes": 10, "comments": 5},
            {"url": "https://b.com/2", "title": "B", "source": "blind", "likes": 50, "comments": 30},
        ]
        spikes = await detector.scan(candidates=candidates)
        if len(spikes) >= 2:
            assert spikes[0].velocity_score >= spikes[1].velocity_score

    @pytest.mark.asyncio
    async def test_empty_url_skipped(self):
        detector = self._make_detector(min_likes=0)
        candidates = [
            {"url": "", "title": "빈URL", "source": "blind", "likes": 100, "comments": 50},
        ]
        spikes = await detector.scan(candidates=candidates)
        assert len(spikes) == 0


# ── SpikeEvent 테스트 ────────────────────────────────────────────────────


class TestSpikeEvent:
    def test_event_key_strips_query(self):
        event = SpikeEvent(
            url="https://blind.com/post/123?ref=trending",
            title="테스트",
            source="blind",
        )
        key = event.event_key
        assert "?" not in key, "쿼리 파라미터가 제거되어야 함"
        assert "ref=trending" not in key
        assert "123" in key

    def test_defaults(self):
        event = SpikeEvent(url="https://x.com", title="t", source="s")
        assert event.likes == 0
        assert event.velocity_score == 0.0
        assert event.category == "general"
        assert isinstance(event.raw_data, dict)
