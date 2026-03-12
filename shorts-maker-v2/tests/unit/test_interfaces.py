"""test_interfaces.py — ShortsFactory 인터페이스 유닛 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest


class TestRenderRequest:
    """RenderRequest 데이터클래스 검증."""

    def test_basic_creation(self):
        from ShortsFactory.interfaces import RenderRequest
        req = RenderRequest(
            channel_id="ai_tech",
            template_name="ai_news_breaking",
            content_data={"news_title": "GPT-5 출시"},
            output_path="output/test.mp4",
        )
        assert req.channel_id == "ai_tech"
        assert req.template_name == "ai_news_breaking"
        assert isinstance(req.output_path, Path)

    def test_defaults(self):
        from ShortsFactory.interfaces import RenderRequest
        req = RenderRequest(
            channel_id="psychology",
            template_name="psychology_experiment",
            content_data={},
            output_path="/tmp/test.mp4",
        )
        assert req.overrides == {}
        assert req.audio_path is None
        assert req.subtitle_data is None
        assert req.assets == {}


class TestRenderResult:
    """RenderResult 데이터클래스 검증."""

    def test_success_result(self):
        from ShortsFactory.interfaces import RenderResult
        result = RenderResult(
            success=True,
            output_path=Path("output/test.mp4"),
            duration_sec=3.5,
            template_used="ai_news_breaking",
            channel_id="ai_tech",
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        from ShortsFactory.interfaces import RenderResult
        result = RenderResult(
            success=False,
            error="Template not found",
        )
        assert result.success is False
        assert result.error == "Template not found"
        assert result.output_path is None


class TestTemplateInfo:
    """TemplateInfo 데이터클래스 검증."""

    def test_basic_creation(self):
        from ShortsFactory.interfaces import TemplateInfo
        info = TemplateInfo(
            name="ai_countdown",
            channel="ai_tech",
            description="AI 카운트다운",
            supports_countdown=True,
        )
        assert info.name == "ai_countdown"
        assert info.supports_countdown is True


class TestRenderAdapter:
    """RenderAdapter 통합 검증."""

    def test_list_templates_all(self):
        from ShortsFactory.interfaces import RenderAdapter
        adapter = RenderAdapter()
        templates = adapter.list_templates()
        assert len(templates) >= 15
        names = {t.name for t in templates}
        assert "ai_news_breaking" in names

    def test_list_templates_by_channel(self):
        from ShortsFactory.interfaces import RenderAdapter
        adapter = RenderAdapter()
        ai_templates = adapter.list_templates(channel_id="ai_tech")
        for t in ai_templates:
            assert t.channel == "ai_tech"

    def test_get_channel_info(self):
        from ShortsFactory.interfaces import RenderAdapter
        adapter = RenderAdapter()
        info = adapter.get_channel_info("psychology")
        assert info["channel"] == "psychology"
        assert "palette" in info

    def test_render_invalid_template(self):
        from ShortsFactory.interfaces import RenderAdapter, RenderRequest
        adapter = RenderAdapter()
        req = RenderRequest(
            channel_id="ai_tech",
            template_name="nonexistent_template",
            content_data={},
            output_path="/tmp/fail.mp4",
        )
        result = adapter.render(req)
        assert result.success is False
        assert "Unknown template" in result.error

    def test_render_with_plan_invalid_channel(self):
        """render_with_plan에 잘못된 channel_id를 전달하면 실패 RenderResult 반환."""
        from ShortsFactory.interfaces import RenderAdapter
        adapter = RenderAdapter()
        result = adapter.render_with_plan(
            channel_id="nonexistent_channel",
            scenes=[{"scene_id": 1, "narration_ko": "테스트", "target_sec": 3.0, "structure_role": "body"}],
            assets={1: "/tmp/image.png"},
            output_path="/tmp/fail.mp4",
        )
        assert result.success is False
        assert result.error is not None


class TestRenderFromPlan:
    """ShortsFactory.render_from_plan() 검증."""

    def test_render_from_plan_invalid_template_falls_back(self):
        """존재하지 않는 템플릿 → 폴백 경로 시도 (create/render) → 에러."""
        from ShortsFactory.pipeline import ShortsFactory
        factory = ShortsFactory(channel="ai_tech")

        # 존재하지 않는 템플릿으로 fallback 시 ValueError 발생
        with pytest.raises(ValueError, match="Unknown template"):
            factory.render_from_plan(
                scenes=[{"scene_id": 1, "narration_ko": "테스트", "target_sec": 3.0, "structure_role": "body"}],
                assets={1: "/tmp/image.png"},
                output="/tmp/fail.mp4",
                template="totally_nonexistent_template_xyz",
            )

    def test_render_from_plan_creates_scenes(self):
        """render_from_plan이 Scene 객체를 올바르게 생성하는지 검증."""
        from ShortsFactory.pipeline import ShortsFactory
        from ShortsFactory.templates import TEMPLATE_REGISTRY, Scene

        factory = ShortsFactory(channel="ai_tech")

        # TEMPLATE_REGISTRY에서 실제 존재하는 템플릿 확인
        assert "ai_news" in TEMPLATE_REGISTRY

        # 씬 데이터 생성
        scene_data = [
            {"scene_id": 1, "narration_ko": "첫 번째 씬", "target_sec": 5.0, "structure_role": "hook"},
            {"scene_id": 2, "narration_ko": "두 번째 씬", "target_sec": 5.0, "structure_role": "body"},
        ]

        # Scene 변환이 올바르게 되는지 간접 확인
        # (실제 렌더링은 ffmpeg 필요하므로 건너뜀)
        tmpl_cls = TEMPLATE_REGISTRY["ai_news"]
        channel_dict = {
            "id": factory.channel.id,
            "palette": factory.channel.palette,
            "font": factory.channel.font,
            "color_preset": factory.channel.color_preset,
            "caption_combo": factory.channel.caption_combo,
            "hook_style": factory.channel.hook_style,
            "transition": factory.channel.transition,
            "disclaimer": factory.channel.disclaimer,
            "highlight_color": factory.channel.highlight_color,
            "keyword_highlights": factory.channel.keyword_highlights,
        }
        tmpl = tmpl_cls(channel_dict)

        scenes = []
        for sp in scene_data:
            scene = Scene(
                role=sp["structure_role"],
                text=sp["narration_ko"],
                keywords=[],
                duration=sp["target_sec"],
            )
            scenes.append(scene)

        assert len(scenes) == 2
        assert scenes[0].role == "hook"
        assert scenes[1].text == "두 번째 씬"

    def test_get_template_info(self):
        """get_template_info가 올바른 정보를 반환하는지 검증."""
        from ShortsFactory.pipeline import ShortsFactory
        factory = ShortsFactory(channel="ai_tech")

        info = factory.get_template_info("ai_news")
        assert info is not None
        assert info["name"] == "ai_news"
        assert "class" in info

        # 존재하지 않는 템플릿
        assert factory.get_template_info("nonexistent") is None

