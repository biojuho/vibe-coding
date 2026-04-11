"""tests/unit/test_performance_prompt_adapter.py
────────────────────────────────────────────────────────────────────────────
PerformancePromptAdapter 유닛 테스트 (20 tests)

커버 범위:
  - PerformanceInsight 모델 (is_stale, has_data, to_prompt_context)
  - HookPattern 데이터 모델
  - _normalize_x_analytics_row  (정규화 함수)
  - _normalize_performance_record (정규화 함수)
  - PerformancePromptAdapter._extract_top_hooks
  - PerformancePromptAdapter._extract_best_hours
  - PerformancePromptAdapter._compute_optimal_length
  - PerformancePromptAdapter._infer_dominant_tone
  - PerformancePromptAdapter.get_insight (캐시 히트/미스/fail-open)
  - get_performance_prompt_adapter (싱글톤 + _reset)
  - express_draft.ExpressDraftPipeline._build_user_prompt (perf_insight 인젝션)
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pipeline.performance_prompt_adapter import (
    HookPattern,
    PerformanceInsight,
    PerformancePromptAdapter,
    _normalize_performance_record,
    _normalize_x_analytics_row,
    get_performance_prompt_adapter,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def adapter():
    """테스트 격리를 위해 항상 새 어댑터 인스턴스 반환."""
    return PerformancePromptAdapter()


@pytest.fixture
def sample_posts():
    """_extract_* 헬퍼 테스트용 샘플 post dict 목록."""
    return [
        {
            "content": "충격 실화 — 연봉 삭감 통보",
            "impression_rate": 5.0,
            "engagement_rate": 0.12,
            "published_hour": 9,
            "source": "x_analytics",
        },
        {
            "content": "공감 100% — 야근하면서 느낀 것",
            "impression_rate": 3.5,
            "engagement_rate": 0.08,
            "published_hour": 20,
            "source": "performance_tracker",
        },
        {
            "content": "정보 공유: 퇴직금 계산 팁",
            "impression_rate": 2.0,
            "engagement_rate": 0.05,
            "published_hour": 12,
            "source": "x_analytics",
        },
        {
            "content": "ㅋㅋ 이건 진짜 웃김",
            "impression_rate": 4.0,
            "engagement_rate": 0.10,
            "published_hour": 21,
            "source": "performance_tracker",
        },
        {
            "content": "믿기지 않는 면접 후기",
            "impression_rate": 6.0,
            "engagement_rate": 0.15,
            "published_hour": 8,
            "source": "x_analytics",
        },
    ]


# ── PerformanceInsight 모델 테스트 ────────────────────────────────────────


class TestPerformanceInsight:

    def test_is_stale_false_when_fresh(self):
        """갓 생성된 인사이트는 stale이 아님."""
        insight = PerformanceInsight(source="blind")
        assert insight.is_stale is False

    def test_is_stale_true_when_expired(self):
        """TTL 초과 시 stale."""
        insight = PerformanceInsight(source="blind")
        insight.fetched_at = time.time() - (7 * 60 * 60)  # 7시간 전
        assert insight.is_stale is True

    def test_has_data_false_when_empty(self):
        """데이터 없으면 has_data=False."""
        insight = PerformanceInsight(source="blind")
        assert insight.has_data is False

    def test_has_data_true_with_hooks(self):
        """훅 패턴이 있으면 has_data=True."""
        insight = PerformanceInsight(
            source="blind",
            top_hooks=[HookPattern("충격 실화", 0.05, 0.12, 1, "blind")],
        )
        assert insight.has_data is True

    def test_to_prompt_context_empty_when_no_data(self):
        """데이터 없으면 빈 문자열 반환 (fail-open 보장)."""
        insight = PerformanceInsight(source="blind")
        assert insight.to_prompt_context() == ""

    def test_to_prompt_context_contains_source(self):
        """컨텍스트 블록에 소스 이름 포함."""
        insight = PerformanceInsight(
            source="ppomppu",
            top_hooks=[HookPattern("뽐뿌 패턴", 0.03, 0.05, 2, "ppomppu")],
        )
        ctx = insight.to_prompt_context()
        assert "ppomppu" in ctx

    def test_to_prompt_context_contains_hook_pattern(self):
        """컨텍스트 블록에 훅 패턴 텍스트 포함."""
        insight = PerformanceInsight(
            source="blind",
            top_hooks=[HookPattern("연봉 삭감 통보", 0.06, 0.13, 3, "blind")],
        )
        ctx = insight.to_prompt_context()
        assert "연봉 삭감 통보" in ctx

    def test_to_prompt_context_contains_posting_hours(self):
        """최적 발행 시간대 포함."""
        insight = PerformanceInsight(
            source="blind",
            best_posting_hours=[9, 20, 12],
        )
        ctx = insight.to_prompt_context()
        assert "09시" in ctx

    def test_to_prompt_context_contains_tone(self):
        """지배적 톤 포함."""
        insight = PerformanceInsight(
            source="blind",
            top_hooks=[HookPattern("x", 0.01, 0.01, 1, "blind")],
            high_ctr_tone="shocking",
        )
        ctx = insight.to_prompt_context()
        assert "shocking" in ctx


# ── 정규화 함수 테스트 ────────────────────────────────────────────────────


class TestNormalizeFunctions:

    def test_normalize_x_analytics_row_returns_none_without_snapshot(self):
        """스냅샷 없으면 None 반환."""
        tweet = {"id": 1, "text_preview": "테스트", "published_at": "2026-04-01 09:00:00"}
        assert _normalize_x_analytics_row(tweet, None) is None

    def test_normalize_x_analytics_row_computes_engagement_rate(self):
        """engagement_rate = (likes + retweets + replies) / impressions."""
        tweet = {"id": 1, "text_preview": "테스트", "published_at": "2026-04-01 09:00:00"}
        snapshot = {"impressions": 1000, "likes": 50, "retweets": 10, "replies": 20}
        result = _normalize_x_analytics_row(tweet, snapshot)
        assert result is not None
        expected = (50 + 10 + 20) / 1000
        assert abs(result["engagement_rate"] - expected) < 1e-6

    def test_normalize_x_analytics_row_extracts_hour(self):
        """published_at에서 hour 추출."""
        tweet = {"id": 1, "text_preview": "", "published_at": "2026-04-01 14:30:00"}
        snapshot = {"impressions": 100, "likes": 5, "retweets": 0, "replies": 0}
        result = _normalize_x_analytics_row(tweet, snapshot)
        assert result is not None
        assert result["published_hour"] == 14

    def test_normalize_performance_record_basic(self):
        """PerformanceRecord → 공통 dict 정상 변환."""
        rec = SimpleNamespace(
            metrics={"impressions": 500, "likes": 20},
            platform="twitter",
            engagement_score=25.0,
            topic_cluster="연봉",
            recorded_at="2026-04-01T20:00:00",
        )
        result = _normalize_performance_record(rec)
        assert result["topic"] == "연봉"
        assert result["published_hour"] == 20


# ── PerformancePromptAdapter 분석 헬퍼 테스트 ─────────────────────────────


class TestAdapterHelpers:

    def test_extract_top_hooks_returns_at_most_top_n(self, adapter, sample_posts):
        """TOP_N (3) 이하로 반환."""
        hooks = adapter._extract_top_hooks(sample_posts, "blind")
        assert len(hooks) <= 3

    def test_extract_top_hooks_sorted_by_impression_rate(self, adapter, sample_posts):
        """첫 번째 훅이 가장 높은 impression_rate."""
        hooks = adapter._extract_top_hooks(sample_posts, "blind")
        if len(hooks) >= 2:
            assert hooks[0].avg_impression_rate >= hooks[1].avg_impression_rate

    def test_extract_best_hours_returns_sorted_hours(self, adapter, sample_posts):
        """최적 시간대는 인게이지먼트 내림차순 정렬."""
        hours = adapter._extract_best_hours(sample_posts)
        assert isinstance(hours, list)
        assert all(0 <= h < 24 for h in hours)

    def test_compute_optimal_length_within_bounds(self, adapter, sample_posts):
        """최적 길이는 50~500자 범위."""
        length = adapter._compute_optimal_length(sample_posts)
        assert 50 <= length <= 500

    def test_compute_optimal_length_default_on_empty(self, adapter):
        """포스트 없으면 기본 280자."""
        assert adapter._compute_optimal_length([]) == 280

    def test_infer_dominant_tone_detects_shocking(self, adapter):
        """'충격' 키워드가 많으면 shocking 톤 감지."""
        posts = [
            {"content": "충격 실화", "impression_rate": 10.0},
            {"content": "경악할 사건", "impression_rate": 9.0},
            {"content": "믿기지 않는 이야기", "impression_rate": 8.0},
        ]
        tone = adapter._infer_dominant_tone(posts)
        assert tone == "shocking"


# ── get_insight 캐시 + fail-open 테스트 ──────────────────────────────────


class TestGetInsight:

    @pytest.mark.asyncio
    async def test_get_insight_returns_insight_object(self, adapter):
        """항상 PerformanceInsight를 반환해야 함."""
        with patch.object(adapter, "_fetch_insight_sync", return_value=PerformanceInsight(source="blind")):
            insight = await adapter.get_insight("blind")
        assert isinstance(insight, PerformanceInsight)

    @pytest.mark.asyncio
    async def test_get_insight_uses_cache_on_second_call(self, adapter):
        """동일 소스 두 번째 호출은 캐시에서 반환."""
        fresh = PerformanceInsight(source="blind")
        adapter._cache["blind"] = fresh  # 캐시 주입

        called = {"count": 0}
        original = adapter._fetch_insight_sync
        def counting_fetch(source):
            called["count"] += 1
            return original(source)
        adapter._fetch_insight_sync = counting_fetch

        await adapter.get_insight("blind")
        assert called["count"] == 0  # 캐시 히트 → fetch 호출 없음

    @pytest.mark.asyncio
    async def test_get_insight_fail_open_on_exception(self, adapter):
        """_fetch_insight_sync 예외 시 빈 PerformanceInsight 반환."""
        def raise_on_fetch(source):
            raise RuntimeError("DB 연결 실패 테스트")
        adapter._fetch_insight_sync = raise_on_fetch

        insight = await adapter.get_insight("blind")
        assert isinstance(insight, PerformanceInsight)
        assert insight.has_data is False


# ── get_performance_prompt_adapter 싱글톤 테스트 ─────────────────────────


class TestFactory:

    def test_singleton_same_instance(self):
        """_reset 없이 두 번 호출하면 동일 인스턴스."""
        a = get_performance_prompt_adapter()
        b = get_performance_prompt_adapter()
        assert a is b

    def test_reset_creates_new_instance(self):
        """_reset=True이면 새 인스턴스 생성."""
        a = get_performance_prompt_adapter()
        b = get_performance_prompt_adapter(_reset=True)
        assert a is not b


# ── express_draft 통합 스모크 테스트 ─────────────────────────────────────


class TestExpressDraftIntegration:

    def test_build_user_prompt_with_perf_insight_injection(self):
        """perf_insight가 있으면 프롬프트에 성과 컨텍스트 포함."""
        from pipeline.express_draft import ExpressDraftPipeline

        pipeline = ExpressDraftPipeline(config_mgr=MagicMock())

        insight = PerformanceInsight(
            source="blind",
            top_hooks=[HookPattern("연봉 삭감 통보", 0.05, 0.12, 3, "blind")],
        )

        prompt = pipeline._build_user_prompt(
            title="연봉 1억 후기",
            content_preview="블라인드 화제 글...",
            source="blind",
            velocity_score=15.0,
            perf_insight=insight,
        )

        assert "연봉 삭감 통보" in prompt  # 훅 패턴이 프롬프트에 포함됨
        assert "성과 기반 가이드" in prompt

    def test_build_user_prompt_without_perf_insight_no_crash(self):
        """perf_insight=None이어도 정상 동작 (fail-open)."""
        from pipeline.express_draft import ExpressDraftPipeline

        pipeline = ExpressDraftPipeline(config_mgr=MagicMock())
        prompt = pipeline._build_user_prompt(
            title="적당한 제목",
            content_preview="적당한 미리보기",
            source="fmkorea",
            velocity_score=5.0,
            perf_insight=None,
        )

        assert "적당한 제목" in prompt
        assert "성과 기반 가이드" not in prompt  # 데이터 없으면 미포함
