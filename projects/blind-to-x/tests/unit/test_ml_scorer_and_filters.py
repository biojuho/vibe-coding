"""Tests for MLScorer.predict_score() and filter_profile_stage individual filters.

타겟 1 — pipeline.ml_scorer.MLScorer.predict_score()
  커버하는 버그 경로:
    - _bundle=None 시 heuristic fallback 메타데이터 오염
    - binary vs continuous 스케일 계산 혼동
    - continuous 점수 클램핑(0·100 경계) 미적용
    - predict_raw 예외 → 침묵 fallback 검증
    - final_rank_score 파라미터 누락 전달

타겟 2 — pipeline.process_stages.filter_profile_stage
  커버하는 버그 경로:
    - _check_length: 경계값 +/-1, 시각 콘텐츠 완화 미적용
    - _check_spam: title=None 처리, 본문-전용 키워드 scope 혼동
    - _check_quality: 경계값, empty-reasons 기본값, 시각 콘텐츠 -20 완화
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.process_stages.context import ProcessRunContext, build_process_result


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────


def _ctx(url: str = "https://example.com/post") -> ProcessRunContext:
    result = build_process_result(url, "test-trace")
    return ProcessRunContext(url=url, trace_id="test-trace", result=result)


# ═════════════════════════════════════════════════════════════════════════════
# 1. MLScorer.predict_score()
# ═════════════════════════════════════════════════════════════════════════════


class TestMLScorerPredictScore:
    """pipeline.ml_scorer.MLScorer.predict_score()

    전략: _load_training_data 를 ([], 0) 으로 패치해 무거운 sklearn/joblib 없이
    MLScorer 를 인스턴스화. 테스트별로 _bundle 을 직접 주입.
    """

    # ── 픽스처 ────────────────────────────────────────────────────────────────

    def _make_scorer(self):
        """모델 학습·로드 없이 빈 MLScorer 반환."""
        with patch("pipeline.ml_scorer._load_training_data", return_value=([], 0)):
            from pipeline.ml_scorer import MLScorer

            scorer = MLScorer()
        return scorer

    def _mock_bundle(
        self,
        target_type: str = "binary",
        model_tier: str = "gradient",
        training_rows: int = 120,
    ):
        bundle = MagicMock()
        bundle.target_type = target_type
        bundle.model_tier = model_tier
        bundle.training_rows = training_rows
        return bundle

    # ── heuristic fallback ─────────────────────────────────────────────────

    def test_heuristic_fallback_returns_zero_score(self):
        """bundle=None 이면 점수 0.0, method=heuristic 반환."""
        scorer = self._make_scorer()
        assert scorer._bundle is None

        with patch("pipeline.ml_scorer._load_training_data", return_value=([], 5)):
            score, meta = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert score == 0.0
        assert meta["method"] == "heuristic"
        assert meta["model_tier"] == "heuristic"

    def test_heuristic_fallback_reason_includes_cached_count(self):
        """fallback reason 에 캐시된 row 수가 포함돼야 디버깅이 가능하다."""
        scorer = self._make_scorer()
        # 캐시된 row count 를 직접 설정 (DB 재조회 없이 캐시 사용)
        scorer._heuristic_row_count = 7

        _, meta = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert "7" in meta["reason"]

    # ── binary model ───────────────────────────────────────────────────────

    def test_binary_probability_scaled_to_100(self):
        scorer = self._make_scorer()
        bundle = self._mock_bundle(target_type="binary")
        bundle.predict_raw.return_value = 0.75
        scorer._bundle = bundle

        score, meta = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert score == 75.0
        assert meta["method"] == "ml"
        assert meta["target_type"] == "binary"
        assert meta["raw_prediction"] == 0.75

    def test_binary_raw_zero_gives_score_zero(self):
        scorer = self._make_scorer()
        bundle = self._mock_bundle(target_type="binary")
        bundle.predict_raw.return_value = 0.0
        scorer._bundle = bundle

        score, _ = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert score == 0.0

    def test_binary_raw_one_gives_score_hundred(self):
        scorer = self._make_scorer()
        bundle = self._mock_bundle(target_type="binary")
        bundle.predict_raw.return_value = 1.0
        scorer._bundle = bundle

        score, _ = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert score == 100.0

    # ── continuous model ────────────────────────────────────────────────────

    def test_continuous_midpoint_maps_to_approximately_50(self):
        """log(50000+1) ≈ 10.82 가 ceiling. 절반이면 점수 ≈ 50."""
        scorer = self._make_scorer()
        bundle = self._mock_bundle(target_type="continuous", model_tier="gradient")
        _LOG_VIEWS_MAX = 10.82
        bundle.predict_raw.return_value = _LOG_VIEWS_MAX / 2
        scorer._bundle = bundle

        score, meta = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert abs(score - 50.0) < 0.5
        assert meta["target_type"] == "continuous"

    def test_continuous_above_ceiling_clamped_to_100(self):
        """천장 초과 raw 값은 100.0 으로 클램프돼야 한다."""
        scorer = self._make_scorer()
        bundle = self._mock_bundle(target_type="continuous")
        bundle.predict_raw.return_value = 999.0
        scorer._bundle = bundle

        score, _ = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert score == 100.0

    def test_continuous_negative_raw_clamped_to_zero(self):
        """음수 raw 값은 0.0 으로 클램프돼야 한다."""
        scorer = self._make_scorer()
        bundle = self._mock_bundle(target_type="continuous")
        bundle.predict_raw.return_value = -5.0
        scorer._bundle = bundle

        score, _ = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert score == 0.0

    # ── exception handling ────────────────────────────────────────────────

    def test_predict_raw_exception_returns_heuristic_fallback(self):
        """predict_raw 예외는 침묵 처리되고 heuristic fallback 반환."""
        scorer = self._make_scorer()
        bundle = self._mock_bundle()
        bundle.predict_raw.side_effect = RuntimeError("model corrupted")
        scorer._bundle = bundle

        score, meta = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert score == 0.0
        assert meta["method"] == "heuristic"
        assert "prediction_error" in meta["reason"]
        assert "model corrupted" in meta["reason"]

    # ── is_active() ────────────────────────────────────────────────────────

    def test_is_active_false_when_no_bundle(self):
        scorer = self._make_scorer()
        assert scorer.is_active() is False

    def test_is_active_true_when_bundle_set(self):
        scorer = self._make_scorer()
        scorer._bundle = self._mock_bundle()
        assert scorer.is_active() is True

    # ── metadata propagation ───────────────────────────────────────────────

    def test_logistic_tier_meta_propagated_correctly(self):
        scorer = self._make_scorer()
        bundle = self._mock_bundle(target_type="binary", model_tier="logistic", training_rows=45)
        bundle.predict_raw.return_value = 0.6
        scorer._bundle = bundle

        score, meta = scorer.predict_score("이직", "공감형", "공감", "공감형")

        assert meta["model_tier"] == "logistic"
        assert meta["trained_on"] == 45

    def test_final_rank_score_forwarded_to_predict_raw(self):
        """final_rank_score 값이 predict_raw 에 그대로 전달되는지 확인."""
        scorer = self._make_scorer()
        bundle = self._mock_bundle()
        bundle.predict_raw.return_value = 0.8
        scorer._bundle = bundle

        scorer.predict_score("이직", "공감형", "공감", "공감형", final_rank_score=88.5)

        bundle.predict_raw.assert_called_once_with(
            topic_cluster="이직",
            hook_type="공감형",
            emotion_axis="공감",
            draft_style="공감형",
            final_rank_score=88.5,
        )


# ═════════════════════════════════════════════════════════════════════════════
# 2. _build_feature_matrix
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildFeatureMatrix:
    """pipeline.ml_scorer._build_feature_matrix — one-hot 피처 생성 로직."""

    def _rows(self):
        return [
            {
                "topic_cluster": "이직",
                "hook_type": "공감형",
                "emotion_axis": "공감",
                "draft_style": "공감형",
                "final_rank_score": 80.0,
                "published": 1,
                "yt_views": 5000,
            },
            {
                "topic_cluster": "연봉",
                "hook_type": "논쟁형",
                "emotion_axis": "분노",
                "draft_style": "논쟁형",
                "final_rank_score": 65.0,
                "published": 0,
                "yt_views": 0,
            },
        ]

    def test_feature_vector_length_equals_categories_plus_numeric(self):
        from pipeline.ml_scorer import _build_feature_matrix

        rows = self._rows()
        X, _, feature_names, cat_sorted = _build_feature_matrix(rows)

        expected = (
            len(cat_sorted["topic_cluster"])
            + len(cat_sorted["hook_type"])
            + len(cat_sorted["emotion_axis"])
            + len(cat_sorted["draft_style"])
            + 1  # final_rank_score
        )
        assert len(feature_names) == expected
        assert all(len(x) == expected for x in X)

    def test_binary_target_values_match_published_field(self):
        from pipeline.ml_scorer import _build_feature_matrix

        _, y, _, _ = _build_feature_matrix(self._rows(), use_views=False)
        assert y == [1, 0]

    def test_continuous_target_uses_log1p_of_yt_views(self):
        from pipeline.ml_scorer import _build_feature_matrix

        _, y, _, _ = _build_feature_matrix(self._rows(), use_views=True)
        assert abs(y[0] - math.log1p(5000.0)) < 1e-9
        assert abs(y[1] - math.log1p(0.0)) < 1e-9

    def test_none_categorical_values_become_unknown(self):
        """None 값이 'unknown' 카테고리로 대체돼야 OOV 크래시 없이 학습 가능."""
        from pipeline.ml_scorer import _build_feature_matrix

        rows = [
            {
                "topic_cluster": None,
                "hook_type": None,
                "emotion_axis": None,
                "draft_style": None,
                "final_rank_score": None,
                "published": 1,
                "yt_views": 0,
            }
        ]
        X, _, _, cat_sorted = _build_feature_matrix(rows)

        for col in ["topic_cluster", "hook_type", "emotion_axis", "draft_style"]:
            assert "unknown" in cat_sorted[col], f"{col} 에 'unknown' 없음"
        assert X[0][-1] == 0.0  # None final_rank_score → 0.0

    def test_feature_names_are_deterministic_across_calls(self):
        """같은 데이터를 두 번 처리해도 피처 순서가 동일해야 모델 재사용 가능."""
        from pipeline.ml_scorer import _build_feature_matrix

        rows = self._rows()
        _, _, names1, _ = _build_feature_matrix(rows)
        _, _, names2, _ = _build_feature_matrix(rows)
        assert names1 == names2


# ═════════════════════════════════════════════════════════════════════════════
# 3. _check_length
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckLength:
    """pipeline.process_stages.filter_profile_stage._check_length"""

    class _Scraper:
        def __init__(self, min_length: int = 10):
            self.min_content_length = min_length

    def _ctx_with(self, content: str = "", post_data: dict | None = None) -> ProcessRunContext:
        ctx = _ctx()
        ctx.content_text = content
        ctx.post_data = post_data or {}
        return ctx

    def test_passes_when_content_meets_min_length(self):
        from pipeline.process_stages.filter_profile_stage import _check_length

        ctx = self._ctx_with("a" * 10)
        assert _check_length(ctx, self._Scraper(min_length=10)) is True

    def test_fails_one_char_below_min_length(self):
        """경계값: min_length=10 일 때 9자는 거부돼야 한다."""
        from pipeline.process_stages.filter_profile_stage import _check_length

        ctx = self._ctx_with("a" * 9)
        result = _check_length(ctx, self._Scraper(min_length=10))

        assert result is False
        assert ctx.result["error_code"] == "FILTERED_SHORT"
        assert ctx.result["failure_reason"] == "content_too_short"
        assert ctx.result["success"] is True  # 필터 거부도 '정상 처리'로 표기

    def test_screenshot_path_bypasses_length_filter(self):
        """시각 콘텐츠(screenshot_path) 는 길이 제한을 0 으로 완화한다."""
        from pipeline.process_stages.filter_profile_stage import _check_length

        ctx = self._ctx_with("", post_data={"screenshot_path": "/tmp/img.png"})
        assert _check_length(ctx, self._Scraper(min_length=50)) is True

    def test_images_field_bypasses_length_filter(self):
        """시각 콘텐츠(images) 도 길이 제한 완화 대상이다."""
        from pipeline.process_stages.filter_profile_stage import _check_length

        ctx = self._ctx_with("", post_data={"images": ["https://img.example/1.jpg"]})
        assert _check_length(ctx, self._Scraper(min_length=50)) is True

    def test_zero_min_length_allows_empty_content(self):
        from pipeline.process_stages.filter_profile_stage import _check_length

        ctx = self._ctx_with("")
        assert _check_length(ctx, self._Scraper(min_length=0)) is True

    def test_stage_status_skipped_on_failure(self):
        from pipeline.process_stages.filter_profile_stage import _check_length

        ctx = self._ctx_with("짧음")
        _check_length(ctx, self._Scraper(min_length=100))

        assert ctx.stage_status.get("filter_profile", {}).get("status") == "skipped"


# ═════════════════════════════════════════════════════════════════════════════
# 4. _check_spam
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckSpam:
    """pipeline.process_stages.filter_profile_stage._check_spam"""

    def _ctx_with(self, title: str = "", content: str = "") -> ProcessRunContext:
        ctx = _ctx()
        ctx.content_text = content
        ctx.post_data = {"title": title, "content": content}
        return ctx

    def test_clean_content_passes(self):
        from pipeline.process_stages.filter_profile_stage import _check_spam

        ctx = self._ctx_with("직장인 연봉 협상 팁", "실질적인 연봉 협상 방법을 공유합니다.")
        assert _check_spam(ctx) is True

    def test_inappropriate_keyword_in_title_rejected(self):
        """부적절 키워드가 제목에 포함되면 즉시 거부."""
        from pipeline.process_stages.filter_profile_stage import _check_spam

        ctx = self._ctx_with("몰카 조심하세요", "일반 본문 내용")
        result = _check_spam(ctx)

        assert result is False
        assert ctx.result["failure_reason"] == "inappropriate_content"
        assert ctx.result["error_code"] == "FILTERED_SPAM"
        assert "몰카" in ctx.result["error"]

    def test_spam_title_keyword_rejected(self):
        """스팸 제목 키워드(카톡상담 등) 거부."""
        from pipeline.process_stages.filter_profile_stage import _check_spam

        ctx = self._ctx_with("카톡상담 무료로 해드립니다", "일반 본문")
        result = _check_spam(ctx)

        assert result is False
        assert ctx.result["failure_reason"] == "spam_keywords_detected"

    def test_spam_body_keyword_rejected(self):
        """본문에만 스팸 키워드가 있어도 거부."""
        from pipeline.process_stages.filter_profile_stage import _check_spam

        ctx = self._ctx_with("정상 제목", "부업 문의는 DM으로 주세요")
        result = _check_spam(ctx)

        assert result is False
        assert ctx.result["failure_reason"] == "spam_keywords_detected"

    def test_missing_title_key_treated_as_empty_string(self):
        """title 키 자체가 없으면 빈 문자열로 처리 → 스팸 거부 없음."""
        from pipeline.process_stages.filter_profile_stage import _check_spam

        ctx = _ctx()
        ctx.content_text = "정상 본문입니다."
        ctx.post_data = {"content": "정상 본문입니다."}  # title 키 없음
        assert _check_spam(ctx) is True

    def test_inappropriate_keyword_in_body_only_does_not_trigger_inappropriate_filter(self):
        """INAPPROPRIATE_TITLE_KEYWORDS 는 제목만 검사한다.
        본문에 동일 키워드가 있어도 inappropriate 거부가 발생하지 않아야 한다.
        (본문은 SPAM_KEYWORDS 목록만 대상)
        """
        from pipeline.process_stages.filter_profile_stage import _check_spam

        ctx = self._ctx_with("정상 제목", "불법촬영 관련 처벌 강화 뉴스입니다.")
        # "불법촬영"은 INAPPROPRIATE_TITLE_KEYWORDS이지만 title에 없으므로 통과
        result = _check_spam(ctx)
        assert result is True

    def test_spam_error_code_is_filtered_spam(self):
        from pipeline.process_stages.filter_profile_stage import _check_spam

        ctx = self._ctx_with("리퍼럴 이벤트 진행 중", "")
        _check_spam(ctx)

        assert ctx.result["error_code"] == "FILTERED_SPAM"

    def test_notion_url_set_to_skipped_filtered_on_reject(self):
        from pipeline.process_stages.filter_profile_stage import _check_spam

        ctx = self._ctx_with("추천인 코드 공유", "")
        _check_spam(ctx)

        assert ctx.result["notion_url"] == "(skipped-filtered)"


# ═════════════════════════════════════════════════════════════════════════════
# 5. _check_quality
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckQuality:
    """pipeline.process_stages.filter_profile_stage._check_quality"""

    _THRESHOLD = 55  # config.QUALITY_SCORE_THRESHOLD

    def _ctx_q(
        self,
        score: int,
        reasons: list | None = None,
        post_data: dict | None = None,
    ) -> ProcessRunContext:
        ctx = _ctx()
        ctx.post_data = post_data or {}
        ctx.quality = {"score": score, "reasons": reasons or [], "metrics": {}}
        return ctx

    class _Cfg:
        pass  # _check_quality 는 config 미사용

    def test_passes_at_exact_threshold(self):
        """score == QUALITY_SCORE_THRESHOLD 는 통과 (< 가 아닌 <)."""
        from pipeline.process_stages.filter_profile_stage import _check_quality

        ctx = self._ctx_q(self._THRESHOLD)
        assert _check_quality(ctx, self._Cfg()) is True

    def test_fails_one_point_below_threshold(self):
        """score = threshold - 1 은 거부."""
        from pipeline.process_stages.filter_profile_stage import _check_quality

        ctx = self._ctx_q(self._THRESHOLD - 1)
        result = _check_quality(ctx, self._Cfg())

        assert result is False
        assert ctx.result["error_code"] == "FILTERED_LOW_QUALITY"
        assert ctx.result["failure_stage"] == "filter"

    def test_empty_reasons_defaults_to_low_quality_score(self):
        """reasons 리스트가 비어 있으면 기본 failure_reason 사용."""
        from pipeline.process_stages.filter_profile_stage import _check_quality

        ctx = self._ctx_q(self._THRESHOLD - 10, reasons=[])
        _check_quality(ctx, self._Cfg())

        assert ctx.result["failure_reason"] == "low_quality_score"

    def test_first_reason_used_as_failure_reason(self):
        """reasons[0] 이 있으면 그것이 failure_reason 이 돼야 한다."""
        from pipeline.process_stages.filter_profile_stage import _check_quality

        ctx = self._ctx_q(self._THRESHOLD - 10, reasons=["blurry_image", "no_text"])
        _check_quality(ctx, self._Cfg())

        assert ctx.result["failure_reason"] == "blurry_image"

    def test_visual_content_lowers_threshold_by_20(self):
        """시각 콘텐츠는 임계값을 -20 완화해 저품질 이미지 포스트를 수용한다."""
        from pipeline.process_stages.filter_profile_stage import _check_quality

        effective = self._THRESHOLD - 20  # 35
        ctx = self._ctx_q(effective, post_data={"screenshot_path": "/tmp/img.png"})
        assert _check_quality(ctx, self._Cfg()) is True

    def test_visual_content_still_fails_below_reduced_threshold(self):
        """시각 콘텐츠라도 완화된 임계값(threshold-20) 미만이면 거부."""
        from pipeline.process_stages.filter_profile_stage import _check_quality

        effective = self._THRESHOLD - 20  # 35
        ctx = self._ctx_q(effective - 1, post_data={"screenshot_path": "/tmp/img.png"})
        assert _check_quality(ctx, self._Cfg()) is False

    def test_images_field_also_triggers_visual_content_leniency(self):
        """images 키도 시각 콘텐츠로 인식해 임계값 -20 완화가 적용된다."""
        from pipeline.process_stages.filter_profile_stage import _check_quality

        effective = self._THRESHOLD - 20
        ctx = self._ctx_q(effective, post_data={"images": ["https://img.example/x.png"]})
        assert _check_quality(ctx, self._Cfg()) is True

    def test_high_quality_always_passes(self):
        """점수 100 은 어떤 조건에서도 통과."""
        from pipeline.process_stages.filter_profile_stage import _check_quality

        ctx = self._ctx_q(100)
        assert _check_quality(ctx, self._Cfg()) is True
