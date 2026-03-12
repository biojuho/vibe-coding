"""test_engines_v2_extended.py — LayoutEngine v2 + ColorEngine v2 확장 테스트.

Phase 3에서 추가된 v2 엔진 메서드들의 유닛 테스트:
- LayoutEngine: numbered_list, image_text_overlay, metric_dashboard,
                step_by_step, quote_card, comparison_table
- ColorEngine: apply_lut, apply_role_grading, blend_presets, auto_correct
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_CHANNEL_CONFIG = {
    "palette": {
        "bg": "#0A0E1A",
        "primary": "#00D4FF",
        "accent": "#00FF88",
        "secondary": "#7C3AED",
    },
    "font_title": "Pretendard-ExtraBold",
    "font_body": "Pretendard-Regular",
}


# ── LayoutEngine v2 ────────────────────────────────────────────


class TestLayoutEngineV2:
    """LayoutEngine v2 새 메서드 테스트."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.layout_engine import LayoutEngine
        return LayoutEngine(_CHANNEL_CONFIG)

    def test_numbered_list_layout(self, engine, tmp_path):
        items = ["첫 번째 항목", "두 번째 항목", "세 번째 항목"]
        out = engine.numbered_list_layout(
            items, title="TOP 3", output_path=tmp_path / "numbered.png"
        )
        assert out.exists()
        img = Image.open(out)
        assert img.size == (1080, 1920)

    def test_numbered_list_no_title(self, engine, tmp_path):
        out = engine.numbered_list_layout(
            ["A", "B"], output_path=tmp_path / "no_title.png"
        )
        assert out.exists()

    def test_image_text_overlay_positions(self, engine, tmp_path):
        for pos in ("top", "center", "bottom"):
            out = engine.image_text_overlay(
                "테스트 오버레이 텍스트입니다",
                position=pos,
                output_path=tmp_path / f"overlay_{pos}.png",
            )
            assert out.exists()
            img = Image.open(out)
            assert img.mode == "RGBA"

    def test_metric_dashboard(self, engine, tmp_path):
        metrics = [
            {"label": "구독자", "value": "10만", "change": "+12%"},
            {"label": "조회수", "value": "500만", "change": "-3%"},
            {"label": "좋아요", "value": "2.5만", "change": "+25%"},
            {"label": "댓글", "value": "1,200"},
        ]
        out = engine.metric_dashboard(
            metrics, title="채널 KPI", cols=2,
            output_path=tmp_path / "dashboard.png",
        )
        assert out.exists()
        img = Image.open(out)
        assert img.size[0] == 1080

    def test_metric_dashboard_cols_clamped(self, engine, tmp_path):
        """cols가 범위 밖일 때 클램핑되는지 확인."""
        out = engine.metric_dashboard(
            [{"label": "X", "value": "1"}], cols=5,
            output_path=tmp_path / "clamped.png",
        )
        assert out.exists()

    def test_step_by_step_layout(self, engine, tmp_path):
        steps = [
            {"label": "STEP 1", "title": "준비", "desc": "재료를 준비합니다"},
            {"label": "STEP 2", "title": "조리", "desc": "센 불에 볶습니다"},
            {"label": "STEP 3", "title": "완성", "desc": "접시에 담습니다"},
        ]
        out = engine.step_by_step_layout(
            steps, title="요리 가이드",
            output_path=tmp_path / "steps.png",
        )
        assert out.exists()

    def test_step_by_step_auto_labels(self, engine, tmp_path):
        """label이 없을 때 자동 생성 확인."""
        steps = [{"title": "A"}, {"title": "B"}]
        out = engine.step_by_step_layout(steps, output_path=tmp_path / "auto.png")
        assert out.exists()

    def test_quote_card(self, engine, tmp_path):
        out = engine.quote_card(
            "상상력은 지식보다 중요하다.",
            author="아인슈타인",
            output_path=tmp_path / "quote.png",
        )
        assert out.exists()
        img = Image.open(out)
        assert img.size[0] == 1080

    def test_quote_card_no_author(self, engine, tmp_path):
        out = engine.quote_card(
            "짧은 인용문", output_path=tmp_path / "quote_no_author.png"
        )
        assert out.exists()

    def test_comparison_table(self, engine, tmp_path):
        headers = ["항목", "A 제품", "B 제품"]
        rows = [
            ["가격", "10만원", "12만원"],
            ["성능", "★★★★", "★★★★★"],
            ["디자인", "★★★", "★★★★"],
        ]
        out = engine.comparison_table(
            headers, rows, output_path=tmp_path / "table.png"
        )
        assert out.exists()

    def test_comparison_table_single_column(self, engine, tmp_path):
        out = engine.comparison_table(
            ["제목"], [["행 1"], ["행 2"]],
            output_path=tmp_path / "single_col.png",
        )
        assert out.exists()


# ── ColorEngine v2 ─────────────────────────────────────────────


class TestColorEngineV2:
    """ColorEngine v2 새 메서드 테스트."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.color_engine import ColorEngine
        return ColorEngine("cinematic")

    def test_apply_lut_identity(self, engine):
        """항등 LUT → 프레임 변환 없음."""

        class FakeClip:
            def transform(self, fn):
                self._fn = fn
                return self

        clip = FakeClip()
        identity = np.arange(256, dtype=np.uint8)
        result = engine.apply_lut(clip, lut_r=identity, lut_g=identity, lut_b=identity)
        assert hasattr(result, "_fn")

        # 프레임 변환 확인
        test_frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        transformed = result._fn(lambda t: test_frame, 0.0)
        np.testing.assert_array_equal(transformed, test_frame)

    def test_apply_lut_inversion(self, engine):
        """반전 LUT → 모든 픽셀이 255-x."""

        class FakeClip:
            def transform(self, fn):
                self._fn = fn
                return self

        clip = FakeClip()
        invert = np.arange(255, -1, -1, dtype=np.uint8)
        result = engine.apply_lut(clip, lut_r=invert, lut_g=invert, lut_b=invert)

        test_frame = np.array([[[100, 150, 200]]], dtype=np.uint8)
        transformed = result._fn(lambda t: test_frame, 0.0)
        expected = np.array([[[155, 105, 55]]], dtype=np.uint8)
        np.testing.assert_array_equal(transformed, expected)

    def test_apply_lut_bad_length(self, engine):
        """길이가 256이 아닌 LUT → 원본 반환."""

        class FakeClip:
            def transform(self, fn):
                self._fn = fn
                return self

        clip = FakeClip()
        bad_lut = np.arange(128, dtype=np.uint8)
        result = engine.apply_lut(clip, lut_r=bad_lut)
        # FakeClip이 반환되어야 함 (transform 호출 안 됨)
        assert result is clip

    def test_apply_role_grading_roles(self, engine):
        """역할별 그레이딩이 다른 결과를 내는지 확인."""

        class FakeClip:
            def transform(self, fn):
                self._fn = fn
                return self

        test_frame = np.full((50, 50, 3), 128, dtype=np.uint8)

        results = {}
        for role in ("hook", "body", "cta"):
            clip = FakeClip()
            graded = engine.apply_role_grading(clip, role=role)
            frame = graded._fn(lambda t: test_frame, 0.0)
            results[role] = float(np.mean(frame))

        # hook과 body는 다른 결과를 내야 함
        assert results["hook"] != results["body"]

    def test_blend_presets_extreme(self):
        """ratio=0.0 → 100% A, ratio=1.0 → 100% B."""
        from ShortsFactory.engines.color_engine import ColorEngine

        engine_a = ColorEngine.blend_presets("cinematic", "warm", ratio=0.0)
        engine_b = ColorEngine.blend_presets("cinematic", "warm", ratio=1.0)

        assert engine_a.preset_name == "cinematic+warm@0.00"
        assert engine_b.preset_name == "cinematic+warm@1.00"

    def test_blend_presets_midpoint(self):
        """ratio=0.5 → 블렌딩."""
        from ShortsFactory.engines.color_engine import ColorEngine

        engine = ColorEngine.blend_presets("cinematic", "warm", ratio=0.5)
        assert "@0.50" in engine.preset_name

    def test_auto_correct(self):
        """자동 보정이 클립을 변환하는지 확인."""
        from ShortsFactory.engines.color_engine import ColorEngine

        # 밝기 편차가 있는 프레임 (평균 ~80, std ~40)
        rng = np.random.RandomState(42)
        dark_frame = np.clip(rng.normal(80, 40, (100, 100, 3)), 0, 255).astype(np.uint8)

        class FakeClip:
            def get_frame(self, t):
                return dark_frame
            def transform(self, fn):
                self._fn = fn
                return self

        clip = FakeClip()
        result = ColorEngine.auto_correct(clip, target_mean=128.0, target_std=50.0)

        corrected = result._fn(lambda t: dark_frame, 0.0)
        mean_after = float(np.mean(corrected))
        mean_before = float(np.mean(dark_frame))
        # 보정 후 목표(128)에 더 가까워야 함
        assert abs(mean_after - 128.0) < abs(mean_before - 128.0)


# ── Orchestrator Phase 3 분기 테스트 ───────────────────────────


class TestOrchestratorShortsFactoryBranch:
    """Orchestrator의 ShortsFactory 렌더링 분기 테스트."""

    def test_try_shorts_factory_render_import_fail(self):
        """ShortsFactory import 실패 시 False 반환."""
        from shorts_maker_v2.pipeline.orchestrator import PipelineOrchestrator

        class MockLogger:
            def __init__(self):
                self.warnings = []
            def warning(self, *args, **kwargs):
                self.warnings.append(args)
            def info(self, *args, **kwargs):
                pass

        mock_logger = MockLogger()

        # 존재하지 않는 채널로 테스트 (RenderAdapter 생성 시 실패 예상)
        result = PipelineOrchestrator._try_shorts_factory_render(
            channel="completely_invalid_channel_xyz",
            scene_plans=[],
            scene_assets=[],
            output_path=Path("/tmp/test_fail.mp4"),
            logger=mock_logger,
        )

        # 실패 시 False 반환
        assert result is False

    def test_use_shorts_factory_flag_default(self):
        """PipelineOrchestrator.__init__이 use_shorts_factory 파라미터를 지원하는지 확인."""
        import inspect
        from shorts_maker_v2.pipeline.orchestrator import PipelineOrchestrator

        sig = inspect.signature(PipelineOrchestrator.__init__)
        params = sig.parameters
        assert "use_shorts_factory" in params
        # 기본값이 False인지 확인
        default = params["use_shorts_factory"].default
        assert default is False
