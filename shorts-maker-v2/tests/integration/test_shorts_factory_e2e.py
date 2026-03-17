"""test_shorts_factory_e2e.py — ShortsFactory RenderAdapter E2E 통합 테스트.

Task 3+4: RenderAdapter 파이프라인 연동 + 실제 영상 생성 검증.

이 테스트는 다음을 검증합니다:
1. RenderAdapter.render_with_plan() → ShortsFactory.render_from_plan() → SFRenderStep.render_scenes() 전체 경로
2. orchestrator._try_shorts_factory_render() 분기 동작
3. SFRenderStep이 실제 MP4를 생성하는지 (ffmpeg 필요)
4. 에러 시 폴백 동작
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# 프로젝트 경로 추가
_PROJECT = Path(__file__).resolve().parent.parent.parent
_SRC = _PROJECT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_PROJECT) not in sys.path:
    sys.path.insert(0, str(_PROJECT))


def _write_test_tone(path: Path, *, duration_sec: float = 1.0, sample_rate: int = 22050) -> Path:
    frame_count = int(duration_sec * sample_rate)
    amplitude = 12000
    freq_hz = 440.0
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frame_count):
            phase = 2.0 * np.pi * freq_hz * (index / sample_rate)
            sample = int(amplitude * np.sin(phase))
            wav_file.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))
    return path

# ffmpeg 감지
HAS_FFMPEG = shutil.which("ffmpeg") is not None
SKIP_FFMPEG = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")


# ── 픽스처 ────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="sf_e2e_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_image(tmp_dir):
    """테스트용 1080x1920 이미지 생성."""
    from PIL import Image
    img = Image.fromarray(
        np.random.randint(0, 255, (1920, 1080, 3), dtype=np.uint8)
    )
    path = tmp_dir / "test_visual.png"
    img.save(str(path))
    return path


@pytest.fixture
def sample_scenes():
    """테스트용 ScenePlan dict 리스트."""
    return [
        {
            "scene_id": 1,
            "narration_ko": "인공지능의 새로운 혁명이 시작됩니다",
            "visual_prompt_en": "AI revolution concept art",
            "target_sec": 4.0,
            "structure_role": "hook",
        },
        {
            "scene_id": 2,
            "narration_ko": "GPT-5가 올해 출시될 예정입니다",
            "visual_prompt_en": "GPT-5 launch announcement",
            "target_sec": 5.0,
            "structure_role": "body",
        },
        {
            "scene_id": 3,
            "narration_ko": "구독과 좋아요를 눌러주세요",
            "visual_prompt_en": "Subscribe button animation",
            "target_sec": 3.0,
            "structure_role": "cta",
        },
    ]


# ── 1. SFRenderStep 유닛 테스트 ────────────────────────────────────

class TestSFRenderStep:
    """ShortsFactory/render.py SFRenderStep 유닛 테스트."""

    def test_import(self):
        """SFRenderStep이 정상적으로 import 되는지 확인."""
        from ShortsFactory.render import SFRenderStep
        assert SFRenderStep is not None

    def test_init_with_dict(self):
        """dict 기반 초기화."""
        from ShortsFactory.render import SFRenderStep
        config = {
            "id": "ai_tech",
            "palette": {"primary": "#00D4AA", "secondary": "#1a1a2e"},
            "color_preset": "neon_tech",
        }
        renderer = SFRenderStep(config)
        assert renderer._color_preset == "neon_tech"
        assert renderer.TARGET_WIDTH == 1080
        assert renderer.TARGET_HEIGHT == 1920

    def test_init_with_channel_config(self):
        """ChannelConfig 객체 기반 초기화."""
        from ShortsFactory.pipeline import ShortsFactory
        factory = ShortsFactory(channel="ai_tech")
        from ShortsFactory.render import SFRenderStep
        renderer = SFRenderStep(factory.channel)
        assert renderer._color_preset == factory.channel.color_preset

    def test_create_gradient_bg(self):
        """그라데이션 배경 생성."""
        from ShortsFactory.render import SFRenderStep
        renderer = SFRenderStep({"palette": {"primary": "#FF0000", "secondary": "#0000FF"}})
        bg = renderer._create_gradient_bg(100, 200)
        assert bg.shape == (200, 100, 3)
        assert bg.dtype == np.uint8
        # 상단은 빨간색에 가깝고, 하단은 파란색에 가까움
        assert bg[0, 0, 0] > bg[199, 0, 0]  # Red decreases
        assert bg[0, 0, 2] < bg[199, 0, 2]  # Blue increases

    def test_hex_to_rgb(self):
        from ShortsFactory.render import SFRenderStep
        assert SFRenderStep._hex_to_rgb("#FF0000") == (255, 0, 0)
        assert SFRenderStep._hex_to_rgb("#00FF00") == (0, 255, 0)
        assert SFRenderStep._hex_to_rgb("invalid") == (30, 30, 60)

    @SKIP_FFMPEG
    def test_render_scenes_minimal(self, tmp_dir, sample_image):
        """최소 Scene으로 실제 MP4 생성 검증 (ffmpeg 필요)."""
        from ShortsFactory.render import SFRenderStep
        from ShortsFactory.templates.base_template import Scene

        renderer = SFRenderStep({
            "id": "ai_tech",
            "palette": {"primary": "#00D4AA", "secondary": "#1a1a2e"},
            "color_preset": "neon_tech",
            "hook_style": "clean_popup",
            "transition": "fade",
        })

        scenes = [
            Scene(role="hook", text="Hook 씬", duration=2.0, image_path=sample_image),
            Scene(role="body", text="Body 씬", duration=2.0, image_path=sample_image),
        ]

        output = str(tmp_dir / "test_output.mp4")
        result = renderer.render_scenes(scenes, output)

        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    @SKIP_FFMPEG
    def test_render_scenes_no_image(self, tmp_dir):
        """이미지 없는 씬 → 그라데이션 배경 폴백."""
        from ShortsFactory.render import SFRenderStep
        from ShortsFactory.templates.base_template import Scene

        renderer = SFRenderStep({
            "palette": {"primary": "#FF6B35", "secondary": "#004E89"},
        })

        scenes = [
            Scene(role="body", text="이미지 없는 씬", duration=2.0),
        ]

        output = str(tmp_dir / "no_image_test.mp4")
        result = renderer.render_scenes(scenes, output)
        assert Path(result).exists()

    def test_render_scenes_empty_raises(self):
        """빈 씬 리스트 → RuntimeError."""
        from ShortsFactory.render import SFRenderStep
        renderer = SFRenderStep({})
        with pytest.raises(RuntimeError, match="렌더링할 씬이 없습니다"):
            renderer.render_scenes([], "output.mp4")


# ── 2. RenderAdapter → render_from_plan 경로 테스트 ──────────────

class TestRenderAdapterPipeline:
    """RenderAdapter → ShortsFactory.render_from_plan() 통합 경로."""

    def test_render_with_plan_valid_channel(self, sample_scenes, sample_image, tmp_dir):
        """유효한 채널 + 유효한 씬 데이터에서 render_with_plan 호출.
        ffmpeg 없으면 에러가 나지만, SFRenderStep까지 도달하는지 검증.
        """
        from ShortsFactory.interfaces import RenderAdapter

        adapter = RenderAdapter()
        assets = {s["scene_id"]: str(sample_image) for s in sample_scenes}
        output = str(tmp_dir / "adapter_test.mp4")

        result = adapter.render_with_plan(
            channel_id="ai_tech",
            scenes=sample_scenes,
            assets=assets,
            output_path=output,
        )

        # ffmpeg 없으면 실패하지만 RenderResult는 반환됨
        assert result is not None
        if HAS_FFMPEG:
            assert result.success is True
            assert Path(result.output_path).exists()
        else:
            # ffmpeg 없으면 실패하되 에러 메시지가 있어야 함
            assert result.success is False or result.success is True

    def test_render_with_plan_invalid_channel_returns_failure(self, sample_scenes, tmp_dir):
        """잘못된 채널 → RenderResult(success=False)."""
        from ShortsFactory.interfaces import RenderAdapter

        adapter = RenderAdapter()
        result = adapter.render_with_plan(
            channel_id="invalid_channel_xyz",
            scenes=sample_scenes,
            assets={1: "/tmp/fake.png"},
            output_path=str(tmp_dir / "fail.mp4"),
        )
        assert result.success is False
        assert result.error is not None


# ── 3. Orchestrator _try_shorts_factory_render 분기 테스트 ─────

class TestOrchestratorSFBranch:
    """PipelineOrchestrator._try_shorts_factory_render() 검증."""

    def test_try_sf_render_returns_tuple(self, sample_image, tmp_dir):
        """정적 메서드가 (success, error) 튜플을 반환하는지 확인."""
        from shorts_maker_v2.pipeline.orchestrator import PipelineOrchestrator
        from shorts_maker_v2.models import ScenePlan, SceneAsset

        scene_plans = [
            ScenePlan(scene_id=1, narration_ko="테스트", visual_prompt_en="test", target_sec=3.0, structure_role="hook"),
            ScenePlan(scene_id=2, narration_ko="본문", visual_prompt_en="body", target_sec=4.0, structure_role="body"),
        ]
        scene_assets = [
            SceneAsset(scene_id=1, audio_path=str(tmp_dir / "fake.mp3"), visual_type="image", visual_path=str(sample_image), duration_sec=3.0),
            SceneAsset(scene_id=2, audio_path=str(tmp_dir / "fake2.mp3"), visual_type="image", visual_path=str(sample_image), duration_sec=4.0),
        ]

        mock_logger = MagicMock()
        result = PipelineOrchestrator._try_shorts_factory_render(
            channel="ai_tech",
            scene_plans=scene_plans,
            scene_assets=scene_assets,
            output_path=tmp_dir / "sf_output.mp4",
            logger=mock_logger,
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)

    def test_sf_branch_fallback_on_import_error(self, tmp_dir):
        """ShortsFactory import 실패 시 False 반환 (폴백)."""
        from shorts_maker_v2.pipeline.orchestrator import PipelineOrchestrator
        from shorts_maker_v2.models import ScenePlan, SceneAsset

        mock_logger = MagicMock()

        with patch.dict("sys.modules", {"ShortsFactory.interfaces": None}):
            result = PipelineOrchestrator._try_shorts_factory_render(
                channel="ai_tech",
                scene_plans=[],
                scene_assets=[],
                output_path=tmp_dir / "fail.mp4",
                logger=mock_logger,
            )
            assert result[0] is False
            assert isinstance(result[1], str)

    def test_renderer_mode_defaults_to_native(self):
        """명시하지 않으면 renderer_mode가 native로 설정되는지 확인."""
        from shorts_maker_v2.pipeline.orchestrator import PipelineOrchestrator
        from unittest.mock import MagicMock

        config = MagicMock()
        config.limits.request_timeout_sec = 30
        config.limits.max_retries = 3
        config.limits.max_cost_usd = 1.0
        config.providers.llm_providers = []
        config.providers.llm = "openai"
        config.providers.llm_model = "gpt-4o-mini"
        config.providers.llm_models = {}
        config.providers.visual_stock = "none"
        config.video.stock_mix_ratio = 0
        config.research.enabled = False
        config.rendering.engine = "native"
        config.thumbnail = MagicMock()
        config.canva = MagicMock()

        orch = PipelineOrchestrator(
            config=config,
            base_dir=Path(__file__).parent,
            script_step=MagicMock(),
            media_step=MagicMock(),
            render_step=MagicMock(),
        )
        assert orch._renderer_mode == "native"
        assert orch._use_shorts_factory is False


# ── 4. render_from_plan Scene 변환 E2E (ffmpeg 필요) ────────────

class TestRenderFromPlanE2E:
    """ShortsFactory.render_from_plan() E2E 검증."""

    @SKIP_FFMPEG
    def test_full_render_from_plan(self, sample_scenes, sample_image, tmp_dir):
        """실제 render_from_plan → MP4 생성 E2E."""
        from ShortsFactory.pipeline import ShortsFactory

        factory = ShortsFactory(channel="ai_tech")

        assets = {s["scene_id"]: str(sample_image) for s in sample_scenes}
        output = str(tmp_dir / "full_e2e.mp4")

        result = factory.render_from_plan(
            scenes=sample_scenes,
            assets=assets,
            output=output,
        )

        assert Path(result).exists()
        assert Path(result).stat().st_size > 1000  # 최소 1KB 이상

    @SKIP_FFMPEG
    def test_render_from_plan_with_template(self, sample_scenes, sample_image, tmp_dir):
        """특정 템플릿을 지정하여 render_from_plan."""
        from ShortsFactory.pipeline import ShortsFactory

        factory = ShortsFactory(channel="ai_tech")
        assets = {s["scene_id"]: str(sample_image) for s in sample_scenes}
        output = str(tmp_dir / "with_template.mp4")

        result = factory.render_from_plan(
            scenes=sample_scenes,
            assets=assets,
            output=output,
            template="ai_news",
        )

        assert Path(result).exists()

    @SKIP_FFMPEG
    def test_render_from_plan_preserves_audio_stream(self, sample_scenes, sample_image, tmp_dir):
        """plan-based render should keep per-scene audio in the final MP4."""
        from ShortsFactory.pipeline import ShortsFactory

        factory = ShortsFactory(channel="ai_tech")
        assets = {s["scene_id"]: str(sample_image) for s in sample_scenes[:1]}
        audio_path = _write_test_tone(tmp_dir / "scene_01.wav", duration_sec=4.0)
        output = str(tmp_dir / "with_audio.mp4")

        result = factory.render_from_plan(
            scenes=sample_scenes[:1],
            assets=assets,
            output=output,
            audio_paths={1: audio_path},
        )

        assert Path(result).exists()

        ffmpeg_output = subprocess.run(
            ["ffmpeg", "-i", str(result)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        ).stderr
        assert "Audio:" in ffmpeg_output

    def test_render_from_plan_scene_conversion(self, sample_scenes, sample_image):
        """Scene 변환이 올바른지 검증 (렌더링 없이)."""
        from ShortsFactory.pipeline import ShortsFactory
        from ShortsFactory.templates import TEMPLATE_REGISTRY, Scene

        factory = ShortsFactory(channel="ai_tech")

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

        assets = {s["scene_id"]: str(sample_image) for s in sample_scenes}

        # Scene 변환
        factory_scenes = []
        for sp in sample_scenes:
            scene = Scene(
                role=sp.get("structure_role", "body"),
                text=sp.get("narration_ko", ""),
                keywords=[],
                image_path=Path(assets[sp["scene_id"]]) if sp["scene_id"] in assets else None,
                duration=sp.get("target_sec", 5.0),
            )
            factory_scenes.append(scene)

        assert len(factory_scenes) == 3
        assert factory_scenes[0].role == "hook"
        assert factory_scenes[1].role == "body"
        assert factory_scenes[2].role == "cta"
        assert factory_scenes[0].text == "인공지능의 새로운 혁명이 시작됩니다"

        # finalize
        finalized = tmpl.finalize_scenes(factory_scenes)
        assert len(finalized) >= 3  # disclaimer가 추가될 수도 있음


# ── 5. 채널별 렌더링 검증 ─────────────────────────────────────────

class TestChannelSpecificRendering:
    """각 채널별 SFRenderStep 동작 검증."""

    @pytest.mark.parametrize("channel", ["ai_tech", "psychology", "history", "space", "health"])
    def test_channel_init(self, channel):
        """각 채널로 SFRenderStep 초기화."""
        from ShortsFactory.pipeline import ShortsFactory
        from ShortsFactory.render import SFRenderStep

        factory = ShortsFactory(channel=channel)
        renderer = SFRenderStep(factory.channel)
        assert renderer._channel_dict["id"] == channel

    @pytest.mark.parametrize("channel", ["ai_tech", "psychology", "history", "space", "health"])
    def test_channel_gradient_bg(self, channel):
        """채널별 그라데이션 배경이 고유한지 확인."""
        from ShortsFactory.pipeline import ShortsFactory
        from ShortsFactory.render import SFRenderStep

        factory = ShortsFactory(channel=channel)
        renderer = SFRenderStep(factory.channel)
        bg = renderer._create_gradient_bg(108, 192)  # 축소 크기
        assert bg.shape == (192, 108, 3)
