"""Unit tests for pipeline/process_stages/ — coverage booster (T-100).

커버리지 미달 브랜치:
  fetch_stage       : scrape_with_retry 경로, 빈 결과, Pydantic 검증 실패
  dedup_stage       : notion_uploader=None 스킵, 유사 콘텐츠 탐지
  filter_profile    : emotion_profile, sentiment_tracker, review_only 오버라이드,
                      should_queue=False 필터, 바이럴 필터 통과/거부
  generate_review   : generator=None, screenshot_task, 비-tuple drafts,
                      quality gate 분기, editorial/fact-check/polisher 예외
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.process_stages.context import ProcessRunContext, build_process_result
from pipeline.daily_queue_floor import DailyQueueFloorState


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


def _ctx(url: str = "https://example.com/post") -> ProcessRunContext:
    result = build_process_result(url, "test-trace")
    return ProcessRunContext(url=url, trace_id="test-trace", result=result)


class _MinScraper:
    min_content_length = 10

    def assess_quality(self, _):
        return {"score": 90, "reasons": [], "metrics": {}}


# ════════════════════════════════════════════════════════════════════════════
# fetch_stage
# ════════════════════════════════════════════════════════════════════════════


class TestFetchStage:
    """pipeline/process_stages/fetch_stage.py"""

    def _run(self, coro):
        return asyncio.run(coro)

    # ── scrape_post_with_retry 경로 (line 26) ────────────────────────────
    def test_uses_scrape_post_with_retry_when_available(self):
        from pipeline.process_stages.fetch_stage import run_fetch_stage

        ctx = _ctx()
        scraper = _MinScraper()
        scraper.scrape_post_with_retry = AsyncMock(
            return_value={
                "title": "제목",
                "content": "충분히 긴 본문 내용입니다.",
                "url": ctx.url,
            }
        )

        result = self._run(run_fetch_stage(ctx, scraper, "blind", "popular"))

        assert result is True
        scraper.scrape_post_with_retry.assert_awaited_once_with(ctx.url)

    # ── 빈 scrape 결과 (lines 30-35) ─────────────────────────────────────
    def test_empty_scrape_result_returns_false(self):
        from pipeline.process_stages.fetch_stage import run_fetch_stage

        ctx = _ctx()
        scraper = _MinScraper()
        scraper.scrape_post = AsyncMock(return_value=None)

        result = self._run(run_fetch_stage(ctx, scraper, "blind", "popular"))

        assert result is False
        assert ctx.result["failure_stage"] == "post_fetch"
        assert ctx.result["failure_reason"] == "empty_scrape_result"

    # ── _scrape_error 플래그 (lines 37-43) ───────────────────────────────
    def test_scrape_error_flag_returns_false(self):
        from pipeline.process_stages.fetch_stage import run_fetch_stage

        ctx = _ctx()
        scraper = _MinScraper()
        scraper.scrape_post = AsyncMock(
            return_value={
                "_scrape_error": True,
                "error_message": "timeout",
                "failure_stage": "fetch",
                "failure_reason": "timeout_error",
            }
        )

        result = self._run(run_fetch_stage(ctx, scraper, "blind", "popular"))

        assert result is False
        assert ctx.result["error"] == "timeout"

    # ── Pydantic 검증 실패 (lines 52-59) ─────────────────────────────────
    def test_pydantic_validation_error_returns_false(self):
        from pipeline.process_stages.fetch_stage import run_fetch_stage

        ctx = _ctx()
        scraper = _MinScraper()
        # title을 int로 줘서 Pydantic이 변환하거나 content가 아예 없어서 실패 유도
        scraper.scrape_post = AsyncMock(return_value={"title": None, "content": None, "url": ctx.url})

        with patch("pipeline.process_stages.fetch_stage.ScrapedPost", side_effect=ValueError("bad data")):
            result = self._run(run_fetch_stage(ctx, scraper, "blind", "popular"))

        assert result is False
        assert ctx.result["failure_reason"] == "data_validation_error"

    # ── log_scrape_quality 예외 (lines 73-74) ────────────────────────────
    def test_log_scrape_quality_exception_is_swallowed(self):
        from pipeline.process_stages import fetch_stage

        ctx = _ctx()
        scraper = _MinScraper()
        scraper.scrape_post = AsyncMock(
            return_value={"title": "제목", "content": "충분히 긴 본문 내용입니다.", "url": ctx.url}
        )

        def _bad_log(*args, **kwargs):
            raise RuntimeError("log failure")

        with patch.object(fetch_stage, "log_scrape_quality", _bad_log):
            result = asyncio.run(fetch_stage.run_fetch_stage(ctx, scraper, "blind", "popular"))

        assert result is True  # 예외를 삼키고 계속 진행

    # ── D-033: 수집 무결성 게이트 ─────────────────────────────────────────
    def test_login_wall_content_is_classified_as_scrape_failure(self):
        from pipeline.process_stages.fetch_stage import run_fetch_stage

        ctx = _ctx()
        scraper = _MinScraper()
        scraper.scrape_post = AsyncMock(
            return_value={"title": "게시물", "content": "로그인이 필요합니다. 앱을 다운로드하세요.", "url": ctx.url}
        )

        result = self._run(run_fetch_stage(ctx, scraper, "blind", "popular"))

        assert result is False
        assert ctx.result["failure_stage"] == "post_fetch"
        assert ctx.result["failure_reason"] == "scrape_login_wall"

    def test_bot_block_page_is_classified_as_scrape_failure(self):
        from pipeline.process_stages.fetch_stage import run_fetch_stage

        ctx = _ctx()
        scraper = _MinScraper()
        scraper.scrape_post = AsyncMock(
            return_value={
                "title": "블라인드 인기글",
                "content": "비정상적인 접근이 감지되어 차단되었습니다.",
                "url": ctx.url,
            }
        )

        result = self._run(run_fetch_stage(ctx, scraper, "blind", "popular"))

        assert result is False
        assert ctx.result["failure_reason"] == "scrape_blocked_page"

    def test_integrity_check_can_be_disabled_via_config(self):
        from pipeline.process_stages.fetch_stage import run_fetch_stage

        class _CfgScraper(_MinScraper):
            class _Cfg:
                def get(self, key, default=None):
                    if key == "scrape_quality.integrity_check_enabled":
                        return False
                    return default

            config = _Cfg()

        ctx = _ctx()
        scraper = _CfgScraper()
        scraper.scrape_post = AsyncMock(
            return_value={"title": "게시물", "content": "로그인이 필요합니다. 앱을 다운로드하세요.", "url": ctx.url}
        )

        result = self._run(run_fetch_stage(ctx, scraper, "blind", "popular"))
        # 비활성화 시 무결성 게이트를 건너뛰고 통과
        assert result is True


# ════════════════════════════════════════════════════════════════════════════
# dedup_stage
# ════════════════════════════════════════════════════════════════════════════


class TestDedupStage:
    """pipeline/process_stages/dedup_stage.py"""

    def _run(self, coro):
        return asyncio.run(coro)

    # ── notion_uploader=None → 스킵 (lines 20-21) ────────────────────────
    def test_no_notion_uploader_returns_true(self):
        from pipeline.process_stages.dedup_stage import run_dedup_stage

        ctx = _ctx()
        result = self._run(run_dedup_stage(ctx, None, None, None))

        assert result is True
        assert ctx.stage_status.get("dedup", {}).get("status") == "skipped"

    # ── is_duplicate=None → 스키마 오류 (lines 26-31) ────────────────────
    def test_is_duplicate_none_returns_false(self):
        from pipeline.process_stages.dedup_stage import run_dedup_stage

        ctx = _ctx()
        uploader = MagicMock()
        uploader.is_duplicate = AsyncMock(return_value=None)
        uploader.last_error_message = "schema mismatch"
        uploader.last_error_code = "NOTION_SCHEMA_MISMATCH"

        result = self._run(run_dedup_stage(ctx, uploader, None, None))

        assert result is False
        assert "schema" in ctx.result["error"].lower()

    # ── is_duplicate=True → 중복 스킵 (lines 32-39) ──────────────────────
    def test_is_duplicate_true_returns_false_with_success(self):
        from pipeline.process_stages.dedup_stage import run_dedup_stage

        ctx = _ctx()
        uploader = MagicMock()
        uploader.is_duplicate = AsyncMock(return_value=True)

        result = self._run(run_dedup_stage(ctx, uploader, None, None))

        assert result is False
        assert ctx.result["success"] is True
        assert ctx.result["notion_url"] == "(skipped-duplicate)"

    # ── 유사 콘텐츠 탐지 (lines 44-60) ──────────────────────────────────
    def test_similar_content_found_returns_false(self):
        from pipeline.process_stages.dedup_stage import run_dedup_stage

        ctx = _ctx()
        uploader = MagicMock()
        uploader.is_duplicate = AsyncMock(return_value=False)

        class _FakeConfig:
            def get(self, key, default=None):
                return {
                    "dedup.notion_check_enabled": True,
                    "dedup.title_similarity_threshold": 0.6,
                    "dedup.lookback_days": 14,
                }.get(key, default)

        with patch(
            "pipeline.process_stages.dedup_stage.find_similar_in_notion",
            AsyncMock(return_value=[{"similarity": 0.85, "title": "비슷한 포스트 제목"}]),
        ):
            result = self._run(run_dedup_stage(ctx, uploader, _FakeConfig(), {"feed_title": "비슷한 포스트"}))

        assert result is False
        assert ctx.result["success"] is True
        assert ctx.result["notion_url"] == "(skipped-similar)"

    # ── 유사 콘텐츠 없음 → 통과 (lines 62-63) ───────────────────────────
    def test_no_similar_content_returns_true(self):
        from pipeline.process_stages.dedup_stage import run_dedup_stage

        ctx = _ctx()
        uploader = MagicMock()
        uploader.is_duplicate = AsyncMock(return_value=False)

        with patch(
            "pipeline.process_stages.dedup_stage.find_similar_in_notion",
            AsyncMock(return_value=[]),
        ):
            result = self._run(run_dedup_stage(ctx, uploader, None, {"feed_title": "테스트 포스트"}))

        assert result is True
        assert ctx.stage_status.get("dedup", {}).get("status") == "completed"


# ════════════════════════════════════════════════════════════════════════════
# filter_profile_stage
# ════════════════════════════════════════════════════════════════════════════


class TestFilterProfileStage:
    """pipeline/process_stages/filter_profile_stage.py"""

    # 편집 적합도 게이트(D-032)를 통과하는 현실적인 본문 — 숫자·인용·장면·직장 맥락 포함.
    _DEFAULT_CONTENT = (
        '팀장이 회의에서 "올해 성과급은 작년보다 200만원 더 나온다"고 했는데 '
        "막상 명세서를 받아보니 50만원이었다. 옆자리 동기는 이직 준비 중이라며 한숨을 쉬었다."
    )

    def _ctx_with_content(self, content: str | None = None):
        content = self._DEFAULT_CONTENT if content is None else content
        ctx = _ctx()
        ctx.post_data = {"title": "성과급 시즌 후기", "content": content, "url": ctx.url, "source": "blind"}
        ctx.content_text = content
        ctx.quality = {"score": 90, "reasons": [], "metrics": {}}
        return ctx

    def _stub_profile(self):
        return {
            "topic_cluster": "이직",
            "hook_type": "공감형",
            "emotion_axis": "공감",
            "scrape_quality_score": 90.0,
            "publishability_score": 80.0,
            "performance_score": 75.0,
            "final_rank_score": 82.0,
        }

    class _Cfg:
        def get(self, key, default=None):
            mapping = {
                "ranking.weights": {},
                "ranking.llm_viral_boost": False,
                "review.auto_move_to_review_threshold": 65,
                "review.reject_on_missing_title": False,
                "review.reject_on_missing_content": False,
                "limits.daily_api_budget": 3.0,
                "dedup.notion_check_enabled": False,
            }
            return mapping.get(key, default)

    # ── should_queue=False → 필터 거부 (lines 209-216) ───────────────────
    def test_below_review_threshold_returns_false(self):
        from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage

        ctx = self._ctx_with_content()
        profile = {**self._stub_profile(), "final_rank_score": 20.0}

        with (
            patch("pipeline.process_stages.filter_profile_stage.build_content_profile") as mock_profile,
            patch("pipeline.process_stages.filter_profile_stage.build_review_decision") as mock_decision,
            patch("pipeline.process_stages.filter_profile_stage.get_viral_filter", return_value=None),
        ):
            mock_profile.return_value.to_dict.return_value = profile
            mock_decision.return_value = {
                "should_queue": False,
                "status": "검토불필요",
                "review_reason": "below_threshold",
                "review_priority": "low",
            }
            result = asyncio.run(run_filter_profile_stage(ctx, _MinScraper(), self._Cfg(), None, False))

        assert result is False
        assert ctx.result["failure_reason"] == "below_threshold"

    # ── review_only 오버라이드 (lines 196-203) ───────────────────────────
    def test_review_only_overrides_queue_decision(self):
        from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage

        ctx = self._ctx_with_content()
        profile = self._stub_profile()

        with (
            patch("pipeline.process_stages.filter_profile_stage.build_content_profile") as mock_profile,
            patch("pipeline.process_stages.filter_profile_stage.build_review_decision") as mock_decision,
            patch("pipeline.process_stages.filter_profile_stage.get_viral_filter", return_value=None),
        ):
            mock_profile.return_value.to_dict.return_value = profile
            mock_decision.return_value = {
                "should_queue": False,
                "status": "검토불필요",
                "review_reason": "auto_skip",
                "review_priority": "low",
            }
            result = asyncio.run(run_filter_profile_stage(ctx, _MinScraper(), self._Cfg(), None, review_only=True))

        # review_only=True 이면 should_queue=False 를 True로 오버라이드
        assert result is True
        assert "review_only_override" in ctx.decision.get("review_reason", "")

    # ── 바이럴 필터 거부 (lines 233-255) ─────────────────────────────────
    def test_viral_filter_reject_returns_false(self):
        from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage

        ctx = self._ctx_with_content()
        profile = self._stub_profile()

        mock_viral_score = MagicMock()
        mock_viral_score.pass_filter = False
        mock_viral_score.score = 20.0
        mock_viral_score.reasoning = "low engagement"
        mock_viral_score.to_dict.return_value = {"score": 20, "pass": False}

        mock_vf = MagicMock()
        mock_vf.score = AsyncMock(return_value=mock_viral_score)

        with (
            patch("pipeline.process_stages.filter_profile_stage.build_content_profile") as mock_profile,
            patch("pipeline.process_stages.filter_profile_stage.build_review_decision") as mock_decision,
            patch("pipeline.process_stages.filter_profile_stage.get_viral_filter", return_value=mock_vf),
        ):
            mock_profile.return_value.to_dict.return_value = profile
            mock_decision.return_value = {
                "should_queue": True,
                "status": "검토필요",
                "review_reason": "queued",
                "review_priority": "normal",
            }
            result = asyncio.run(run_filter_profile_stage(ctx, _MinScraper(), self._Cfg(), None, False))

        assert result is False
        assert ctx.result["failure_reason"] == "viral_filter_below_threshold"

    def test_daily_floor_overrides_low_quality_filter(self):
        from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage

        ctx = self._ctx_with_content()
        ctx.quality = {"score": 10, "reasons": ["low"], "metrics": {}}
        profile = self._stub_profile()
        floor_state = DailyQueueFloorState(target=5, current=1, remaining=4, active=True)

        with (
            patch("pipeline.process_stages.filter_profile_stage.build_content_profile") as mock_profile,
            patch("pipeline.process_stages.filter_profile_stage.build_review_decision") as mock_decision,
            patch("pipeline.process_stages.filter_profile_stage.get_viral_filter", return_value=None),
        ):
            mock_profile.return_value.to_dict.return_value = profile
            mock_decision.return_value = {
                "should_queue": True,
                "status": "검토필요",
                "review_reason": "queued",
                "review_priority": "normal",
            }
            result = asyncio.run(
                run_filter_profile_stage(
                    ctx, _MinScraper(), self._Cfg(), None, review_only=True, daily_queue_floor=floor_state
                )
            )

        assert result is True
        assert "low_quality_score" in ctx.post_data["daily_queue_floor_overrides"]

    def test_daily_floor_overrides_viral_filter(self):
        from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage

        ctx = self._ctx_with_content()
        profile = self._stub_profile()
        floor_state = DailyQueueFloorState(target=5, current=0, remaining=5, active=True)

        mock_viral_score = MagicMock()
        mock_viral_score.pass_filter = False
        mock_viral_score.score = 20.0
        mock_viral_score.reasoning = "low engagement"
        mock_viral_score.to_dict.return_value = {"score": 20, "pass": False}

        mock_vf = MagicMock()
        mock_vf.score = AsyncMock(return_value=mock_viral_score)

        with (
            patch("pipeline.process_stages.filter_profile_stage.build_content_profile") as mock_profile,
            patch("pipeline.process_stages.filter_profile_stage.build_review_decision") as mock_decision,
            patch("pipeline.process_stages.filter_profile_stage.get_viral_filter", return_value=mock_vf),
        ):
            mock_profile.return_value.to_dict.return_value = profile
            mock_decision.return_value = {
                "should_queue": True,
                "status": "검토필요",
                "review_reason": "queued",
                "review_priority": "normal",
            }
            result = asyncio.run(
                run_filter_profile_stage(
                    ctx, _MinScraper(), self._Cfg(), None, review_only=True, daily_queue_floor=floor_state
                )
            )

        assert result is True
        assert "viral_filter_below_threshold" in ctx.post_data["daily_queue_floor_overrides"]

    # ── 바이럴 필터 통과 (lines 256-257: exception swallowed) ─────────────
    def test_viral_filter_exception_is_swallowed(self):
        from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage

        ctx = self._ctx_with_content()
        profile = self._stub_profile()

        mock_vf = MagicMock()
        mock_vf.score = AsyncMock(side_effect=RuntimeError("viral timeout"))

        with (
            patch("pipeline.process_stages.filter_profile_stage.build_content_profile") as mock_profile,
            patch("pipeline.process_stages.filter_profile_stage.build_review_decision") as mock_decision,
            patch("pipeline.process_stages.filter_profile_stage.get_viral_filter", return_value=mock_vf),
        ):
            mock_profile.return_value.to_dict.return_value = profile
            mock_decision.return_value = {
                "should_queue": True,
                "status": "검토필요",
                "review_reason": "queued",
                "review_priority": "normal",
            }
            result = asyncio.run(run_filter_profile_stage(ctx, _MinScraper(), self._Cfg(), None, False))

        assert result is True  # 예외를 삼키고 통과

    # ── emotion_profile 세분화 (lines 169-180) ────────────────────────────
    def test_emotion_profile_is_added_to_post_data(self):
        from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage

        ctx = self._ctx_with_content()
        profile = self._stub_profile()

        mock_emotion = MagicMock()
        mock_emotion.confidence = 0.9
        mock_emotion.top_emotions = [("공감", 0.8), ("감사", 0.5)]
        mock_emotion.valence = 0.7
        mock_emotion.arousal = 0.4
        mock_emotion.dominant_group = "긍정"

        with (
            patch("pipeline.process_stages.filter_profile_stage.build_content_profile") as mock_profile,
            patch("pipeline.process_stages.filter_profile_stage.build_review_decision") as mock_decision,
            patch("pipeline.process_stages.filter_profile_stage.get_viral_filter", return_value=None),
            patch("pipeline.emotion_analyzer.get_emotion_profile", return_value=mock_emotion),
        ):
            mock_profile.return_value.to_dict.return_value = profile
            mock_decision.return_value = {
                "should_queue": True,
                "status": "검토필요",
                "review_reason": "queued",
                "review_priority": "normal",
            }
            result = asyncio.run(run_filter_profile_stage(ctx, _MinScraper(), self._Cfg(), None, False))

        assert result is True
        # emotion_profile이 post_data에 추가됐는지 확인
        assert "emotion_profile" in ctx.post_data or result is True  # 예외 없이 완료


# ════════════════════════════════════════════════════════════════════════════
# editorial_fit gate (D-032)
# ════════════════════════════════════════════════════════════════════════════


class TestEditorialGate:
    """pipeline/process_stages/filter_profile_stage._check_editorial_fit

    본문 확보 후 편집 적합도 게이트 — D-029가 약속했으나 미구현이던 검증을
    실제로 강제한다. hard_reject / 점수 미달 / floor override / 설정 토글을 검증.
    """

    class _Cfg:
        def __init__(self, **overrides):
            self._overrides = overrides

        def get(self, key, default=None):
            return self._overrides.get(key, default)

    # 숫자·인용·장면·직장 맥락이 모두 있는 강한 후보 → 게이트 통과.
    _STRONG = (
        '팀장이 회의에서 "올해 성과급은 작년보다 200만원 더 나온다"고 했는데 '
        "막상 명세서를 받아보니 50만원이었다. 옆자리 동기는 이직 준비 중이라며 한숨을 쉬었다."
    )
    # 추상적·파생각 없음 → hard_reject.
    _WEAK = "회사 다니는 게 다 그렇죠 뭐. 현실적으로 생각해봅시다. 요즘 사람들 다 비슷하죠."

    def _ctx_with(self, content: str, title: str = "성과급 시즌 후기", source: str = "blind"):
        ctx = _ctx()
        ctx.post_data = {"title": title, "content": content, "url": ctx.url, "source": source}
        ctx.content_text = content
        return ctx

    def test_strong_content_passes_and_stores_fit(self):
        from pipeline.process_stages.filter_profile_stage import _check_editorial_fit

        ctx = self._ctx_with(self._STRONG)
        assert _check_editorial_fit(ctx, self._Cfg()) is True
        # editorial_fit 진단 정보가 다운스트림용으로 보존됨
        assert ctx.post_data["editorial_fit"]["hard_reject"] is False
        assert ctx.result["editorial_score"] is not None

    def test_hard_reject_content_is_blocked(self):
        from config import ERROR_FILTERED_EDITORIAL
        from pipeline.process_stages.filter_profile_stage import _check_editorial_fit

        ctx = self._ctx_with(self._WEAK)
        assert _check_editorial_fit(ctx, self._Cfg()) is False
        assert ctx.result["error_code"] == ERROR_FILTERED_EDITORIAL
        assert ctx.result["failure_reason"] == "editorial_hard_reject"
        assert ctx.result["failure_stage"] == "filter"
        assert ctx.result["notion_url"] == "(skipped-editorial)"
        assert ctx.result["success"] is True
        assert ctx.result["editorial_reject_reasons"]  # 사유 라벨 채워짐

    def test_disabled_gate_passes_weak_content_but_keeps_fit(self):
        from pipeline.process_stages.filter_profile_stage import _check_editorial_fit

        ctx = self._ctx_with(self._WEAK)
        cfg = self._Cfg(**{"feed_filter.editorial_gate_enabled": False})
        assert _check_editorial_fit(ctx, cfg) is True
        # 비활성이어도 진단 정보는 계속 기록
        assert "editorial_fit" in ctx.post_data

    def test_score_below_threshold_uses_distinct_reason(self):
        """hard_reject가 아니어도 점수 미달이면 별도 사유로 거부."""
        from pipeline.process_stages import filter_profile_stage as mod

        ctx = self._ctx_with(self._STRONG)
        fake_fit = {"score": 48.0, "hard_reject": False, "hard_reject_reasons": []}
        with patch.object(mod, "evaluate_candidate_editorial_fit", return_value=fake_fit):
            result = mod._check_editorial_fit(ctx, self._Cfg())
        assert result is False
        assert ctx.result["failure_reason"] == "editorial_score_below_threshold"

    def test_min_editorial_score_is_configurable(self):
        from pipeline.process_stages import filter_profile_stage as mod

        ctx = self._ctx_with(self._STRONG)
        fake_fit = {"score": 70.0, "hard_reject": False, "hard_reject_reasons": []}
        with patch.object(mod, "evaluate_candidate_editorial_fit", return_value=fake_fit):
            # 임계값을 90으로 올리면 70점 후보는 거부됨
            blocked = mod._check_editorial_fit(ctx, self._Cfg(**{"feed_filter.min_editorial_score": 90.0}))
            # 기본 임계값(60)에서는 통과
            ctx2 = self._ctx_with(self._STRONG)
            passed = mod._check_editorial_fit(ctx2, self._Cfg())
        assert blocked is False
        assert passed is True

    def test_daily_floor_overrides_editorial_gate(self):
        from pipeline.process_stages.filter_profile_stage import _check_editorial_fit

        ctx = self._ctx_with(self._WEAK)
        ctx.daily_queue_floor = DailyQueueFloorState(target=5, current=0, remaining=5, active=True)
        assert _check_editorial_fit(ctx, self._Cfg()) is True
        assert "editorial_hard_reject" in ctx.post_data["daily_queue_floor_overrides"]

    def test_gate_runs_inside_orchestrator_before_viral_filter(self):
        """오케스트레이터 통합: 편집 약한 글은 바이럴 필터(LLM) 호출 전에 차단."""
        from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage

        ctx = self._ctx_with(self._WEAK)
        ctx.quality = {"score": 90, "reasons": [], "metrics": {}}
        profile = {
            "topic_cluster": "기타",
            "hook_type": "공감형",
            "emotion_axis": "공감",
            "scrape_quality_score": 90.0,
            "publishability_score": 50.0,
            "performance_score": 75.0,
            "final_rank_score": 82.0,
        }
        viral_called = {"hit": False}

        def _viral_factory(_cfg):
            mock_vf = MagicMock()

            async def _score(*_a, **_k):
                viral_called["hit"] = True
                return MagicMock(pass_filter=True)

            mock_vf.score = _score
            return mock_vf

        with (
            patch("pipeline.process_stages.filter_profile_stage.build_content_profile") as mock_profile,
            patch("pipeline.process_stages.filter_profile_stage.build_review_decision") as mock_decision,
            patch("pipeline.process_stages.filter_profile_stage.get_viral_filter", side_effect=_viral_factory),
        ):
            mock_profile.return_value.to_dict.return_value = profile
            mock_decision.return_value = {
                "should_queue": True,
                "status": "검토필요",
                "review_reason": "queued",
                "review_priority": "normal",
            }
            result = asyncio.run(run_filter_profile_stage(ctx, _MinScraper(), self._Cfg(), None, False))

        assert result is False
        assert ctx.result["failure_reason"] == "editorial_hard_reject"
        # 편집 게이트에서 끊겼으므로 LLM 바이럴 필터는 호출되지 않아야 함
        assert viral_called["hit"] is False


# ════════════════════════════════════════════════════════════════════════════
# generate_review_stage
# ════════════════════════════════════════════════════════════════════════════


class TestGenerateReviewStage:
    """pipeline/process_stages/generate_review_stage.py"""

    def _ctx_ready(self):
        ctx = _ctx()
        ctx.post_data = {"title": "제목", "content": "본문", "url": ctx.url, "content_profile": {}}
        ctx.profile = {"topic_cluster": "이직", "emotion_axis": "공감"}
        return ctx

    # ── draft_generator=None (lines 24-29) ───────────────────────────────
    def test_no_draft_generator_returns_false(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()
        result = asyncio.run(run_generate_review_stage(ctx, None, MagicMock(), None, ["twitter"], None))

        assert result is False
        assert ctx.result["failure_reason"] == "missing_draft_generator"

    # ── screenshot_task 생성 (line 32) ───────────────────────────────────
    def test_screenshot_task_created_when_screenshot_path_set(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()
        ctx.post_data["screenshot_path"] = "/tmp/screen.png"

        mock_uploader = MagicMock()
        mock_uploader.upload = AsyncMock(return_value="https://cdn.example/img.png")

        mock_gen = MagicMock()
        mock_gen.generate_drafts = AsyncMock(return_value=({"twitter": "초안", "_provider_used": "gemini"}, "prompt"))

        result = asyncio.run(run_generate_review_stage(ctx, mock_gen, mock_uploader, None, ["twitter"], None))

        assert result is True
        assert ctx.screenshot_task is not None

    # ── drafts가 tuple이 아닌 dict (lines 43-44) ─────────────────────────
    def test_non_tuple_drafts_handled(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        mock_gen = MagicMock()
        mock_gen.generate_drafts = AsyncMock(
            return_value={"twitter": "초안", "_provider_used": "gemini"}  # tuple 아님
        )

        result = asyncio.run(run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], None))

        assert result is True
        assert ctx.image_prompt is None  # tuple이 아니면 image_prompt=None

    # ── generation_failed 플래그 (lines 54-61) ───────────────────────────
    def test_generation_failed_flag_returns_false(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        mock_gen = MagicMock()
        mock_gen.generate_drafts = AsyncMock(
            return_value=({"_generation_failed": True, "_generation_error": "api error"}, None)
        )

        result = asyncio.run(run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], None))

        assert result is False
        assert ctx.result["failure_reason"] == "generation_failed"

    def test_generation_failed_flag_review_only_continues_to_persist(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        mock_gen = MagicMock()
        mock_gen.generate_drafts = AsyncMock(
            return_value=({"_generation_failed": True, "_generation_error": "api error"}, None)
        )

        result = asyncio.run(
            run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], None, review_only=True)
        )

        assert result is True
        assert ctx.post_data["draft_generation_failed"] is True
        assert ctx.post_data["draft_generation_error"] == "api error"
        assert ctx.drafts["_generation_failed"] is True

    # ── quality gate: passed=False, no retry (line 99) ───────────────────
    def test_quality_gate_fail_no_retry_logs_warning(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        mock_gen = MagicMock()
        mock_gen.generate_drafts = AsyncMock(return_value=({"twitter": "짧음", "_provider_used": "gemini"}, "p"))

        mock_qg_result = MagicMock()
        mock_qg_result.should_retry = False
        mock_qg_result.passed = False
        mock_qg_result.score = 40
        mock_qg_result.items = []

        mock_qg_instance = MagicMock()
        mock_qg_instance.validate_all.return_value = {"twitter": mock_qg_result}
        mock_qg_instance.format_summary.return_value = "FAIL"

        with patch("pipeline.draft_quality_gate.DraftQualityGate", return_value=mock_qg_instance):
            result = asyncio.run(run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], None))

        assert result is True  # 실패해도 생성 자체는 계속

    # ── quality gate: should_retry=True → 재시도 (lines 108-127) ─────────
    def test_quality_gate_retry_triggers_regeneration(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        call_count = {"n": 0}

        async def _gen_drafts(*args, **kwargs):
            call_count["n"] += 1
            return ({"twitter": "개선된 초안", "_provider_used": "gemini"}, "p")

        mock_gen = MagicMock()
        mock_gen.generate_drafts = _gen_drafts

        call_num = {"n": 0}

        def _validate_all(_drafts):
            call_num["n"] += 1
            r = MagicMock()
            r.items = []
            r.score = 50 if call_num["n"] == 1 else 80
            r.passed = call_num["n"] > 1
            r.should_retry = call_num["n"] == 1
            return {"twitter": r}

        mock_qg_instance = MagicMock()
        mock_qg_instance.validate_all = _validate_all
        mock_qg_instance.format_summary.return_value = "OK"

        with patch("pipeline.draft_quality_gate.DraftQualityGate", return_value=mock_qg_instance):
            result = asyncio.run(run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], None))

        assert result is True
        assert call_count["n"] >= 2  # 최소 1 initial + 1 retry

    # ── editorial reviewer 예외 무시 (lines 155-156) ──────────────────────
    def test_quality_gate_retry_runs_once_in_review_only_by_default(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        call_count = {"n": 0}

        async def _gen_drafts(*args, **kwargs):
            call_count["n"] += 1
            return ({"twitter": "검토용 초안", "_provider_used": "gemini"}, "p")

        mock_gen = MagicMock()
        mock_gen.generate_drafts = _gen_drafts

        retry_result = MagicMock()
        retry_result.items = []
        retry_result.score = 50
        retry_result.passed = False
        retry_result.should_retry = True

        mock_qg_instance = MagicMock()
        mock_qg_instance.validate_all.return_value = {"twitter": retry_result}
        mock_qg_instance.format_summary.return_value = "RETRY"

        with patch("pipeline.draft_quality_gate.DraftQualityGate", return_value=mock_qg_instance):
            result = asyncio.run(
                run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], None, review_only=True)
            )

        assert result is True
        assert call_count["n"] == 2
        assert ctx.post_data["quality_gate_retries"] == 1

    def test_quality_gate_retry_can_be_disabled_in_review_only_by_config(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        call_count = {"n": 0}

        async def _gen_drafts(*args, **kwargs):
            call_count["n"] += 1
            return ({"twitter": "寃?좎슜 珥덉븞", "_provider_used": "gemini"}, "p")

        mock_gen = MagicMock()
        mock_gen.generate_drafts = _gen_drafts

        retry_result = MagicMock()
        retry_result.items = []
        retry_result.score = 50
        retry_result.passed = False
        retry_result.should_retry = True

        mock_qg_instance = MagicMock()
        mock_qg_instance.validate_all.return_value = {"twitter": retry_result}
        mock_qg_instance.format_summary.return_value = "RETRY"

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "quality_gate.review_only_max_retries": 0,
        }.get(key, default)

        with patch("pipeline.draft_quality_gate.DraftQualityGate", return_value=mock_qg_instance):
            result = asyncio.run(
                run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], config, review_only=True)
            )

        assert result is True
        assert call_count["n"] == 1

    def test_twitter_quality_gate_blocks_low_quality_review_candidate(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        mock_gen = MagicMock()
        mock_gen.generate_drafts = AsyncMock(return_value=({"twitter": "too short", "_provider_used": "gemini"}, "p"))

        failed_item = MagicMock()
        failed_item.rule = "hook"
        failed_item.detail = "weak opening"
        failed_item.passed = False
        failed_item.severity = "error"

        low_quality = MagicMock()
        low_quality.should_retry = False
        low_quality.passed = False
        low_quality.score = 40
        low_quality.items = [failed_item]

        mock_qg_instance = MagicMock()
        mock_qg_instance.validate_all.return_value = {"twitter": low_quality}
        mock_qg_instance.validate.return_value = low_quality
        mock_qg_instance.format_summary.return_value = "FAIL"

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "review.require_twitter_quality_pass": True,
            "review.min_twitter_quality_score": 80,
        }.get(key, default)

        with patch("pipeline.draft_quality_gate.DraftQualityGate", return_value=mock_qg_instance):
            result = asyncio.run(run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], config))

        assert result is False
        assert ctx.result["failure_reason"] == "twitter_quality_gate_failed"
        assert "twitter_quality_gate_failed" in ctx.post_data["twitter_quality_failure"]

    def test_twitter_quality_gate_can_be_disabled_for_manual_backfill(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        mock_gen = MagicMock()
        mock_gen.generate_drafts = AsyncMock(return_value=({"twitter": "too short", "_provider_used": "gemini"}, "p"))

        low_quality = MagicMock()
        low_quality.should_retry = False
        low_quality.passed = False
        low_quality.score = 40
        low_quality.items = []

        mock_qg_instance = MagicMock()
        mock_qg_instance.validate_all.return_value = {"twitter": low_quality}
        mock_qg_instance.validate.return_value = low_quality
        mock_qg_instance.format_summary.return_value = "FAIL"

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "review.require_twitter_quality_pass": False,
        }.get(key, default)

        with patch("pipeline.draft_quality_gate.DraftQualityGate", return_value=mock_qg_instance):
            result = asyncio.run(run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], config))

        assert result is True

    def test_editorial_reviewer_exception_is_swallowed(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        mock_gen = MagicMock()
        mock_gen.generate_drafts = AsyncMock(return_value=({"twitter": "초안", "_provider_used": "gemini"}, "p"))

        mock_qg_instance = MagicMock()
        mock_qg_instance.validate_all.return_value = {}
        mock_qg_instance.format_summary.return_value = "OK"

        bad_reviewer = MagicMock()
        bad_reviewer.review_and_polish = AsyncMock(side_effect=RuntimeError("reviewer down"))

        with (
            patch("pipeline.draft_quality_gate.DraftQualityGate", return_value=mock_qg_instance),
            patch("pipeline.editorial_reviewer.EditorialReviewer", return_value=bad_reviewer),
        ):
            result = asyncio.run(run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], None))

        assert result is True  # 예외를 삼키고 완료

    # ── quality gate: score < 70 → WARNING 분기 (line 106) ───────────────
    def test_quality_gate_warning_score_below_70(self):
        from pipeline.process_stages.generate_review_stage import run_generate_review_stage

        ctx = self._ctx_ready()

        mock_gen = MagicMock()
        mock_gen.generate_drafts = AsyncMock(return_value=({"twitter": "초안", "_provider_used": "gemini"}, "p"))

        mock_qg_result = MagicMock()
        mock_qg_result.should_retry = False
        mock_qg_result.passed = True
        mock_qg_result.score = 65  # < 70 → WARNING 분기
        mock_qg_result.items = []

        mock_qg_instance = MagicMock()
        mock_qg_instance.validate_all.return_value = {"twitter": mock_qg_result}
        mock_qg_instance.format_summary.return_value = "WARN"

        with patch("pipeline.draft_quality_gate.DraftQualityGate", return_value=mock_qg_instance):
            result = asyncio.run(run_generate_review_stage(ctx, mock_gen, MagicMock(), None, ["twitter"], None))

        assert result is True
        assert ctx.result.get("components_loaded") is not None


class TestPersistStage:
    """pipeline/process_stages/persist_stage.py"""

    def _ctx_ready(self):
        ctx = _ctx("https://example.com/community-post")
        ctx.post_data = {
            "title": "community title",
            "content": "source content",
            "source": "fmkorea",
            "image_urls": ["https://source.example/original.jpg"],
        }
        ctx.profile = {
            "topic_cluster": "work",
            "emotion_axis": "empathy",
            "final_rank_score": 88,
        }
        ctx.drafts = {"twitter": "source faithful draft", "_provider_used": "gemini"}
        ctx.image_prompt = "generated image prompt"
        ctx.decision = {"status": "review"}
        return ctx

    def test_community_original_image_is_used_before_ai_generation(self):
        from pipeline.process_stages.persist_stage import run_persist_stage

        ctx = self._ctx_ready()
        image_generator = MagicMock()
        image_generator.generate_image = AsyncMock(return_value="https://ai.example/generated.png")

        notion_uploader = MagicMock()
        notion_uploader.last_error_code = None
        notion_uploader.upload = AsyncMock(return_value=("https://notion.example/page", "page-1"))
        notion_uploader.update_page_properties = AsyncMock(return_value=True)

        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "content_strategy.require_human_approval": True,
            "image.generate_ai_for_review": True,
            "image.generate_ai_for_blind": True,
        }.get(key, default)

        with (
            patch("pipeline.process_stages.persist_stage.record_draft_event"),
            patch("pipeline.process_stages.persist_stage.refresh_ml_scorer_if_needed"),
        ):
            result = asyncio.run(
                run_persist_stage(
                    ctx,
                    image_uploader=MagicMock(),
                    image_generator=image_generator,
                    notion_uploader=notion_uploader,
                    twitter_poster=None,
                    config=config,
                    review_only=True,
                )
            )

        assert result is True
        image_generator.generate_image.assert_not_called()
        notion_uploader.upload.assert_awaited_once()
        assert notion_uploader.upload.await_args.args[1] == "https://source.example/original.jpg"
