"""Shared helpers for test_render_step_*.py split files."""

from __future__ import annotations

from unittest.mock import MagicMock


from shorts_maker_v2.pipeline.render_step import RenderStep


def _make_render_step(
    transition_style: str = "random",
    *,
    channel_key: str = "",
    video_renderer_backend: str | None = None,
) -> RenderStep:
    """RenderStep의 __init__이 사용하는 모든 config 필드를 MagicMock으로 구성."""
    config = MagicMock()

    # video
    config.video.resolution = (1080, 1920)
    config.video.fps = 30
    config.video.transition_style = transition_style
    config.video.encoding_preset = "fast"
    config.video.encoding_crf = 23

    # captions (CaptionStyle 생성에 필요)
    config.captions.mode = "karaoke"
    config.captions.font_size = 72
    config.captions.margin_x = 60
    config.captions.bottom_offset = 280
    config.captions.text_color = "#FFFFFF"
    config.captions.stroke_color = "#000000"
    config.captions.stroke_width = 0
    config.captions.line_spacing = 12
    config.captions.bg_color = "#000000"
    config.captions.bg_opacity = 185
    config.captions.bg_radius = 18
    config.captions.style_preset = "default"
    config.captions.words_per_chunk = 3
    config.captions.font_candidates = ("C:/Windows/Fonts/malgunbd.ttf",)
    config.captions.outline_thickness = "medium"
    config.captions.custom_styles = {}
    config.captions.safe_zone_enabled = True
    config.captions.center_hook = False
    config.captions.line_spacing_factor = 1.0
    config.captions.channel_style_map = {}
    config.captions.highlight_color = "#FFD700"
    config.captions.highlight_mode = "word"
    config.captions.hook_animation = "pop"

    # audio
    config.audio.bgm_dir = "assets/bgm"
    config.audio.bgm_volume = 0.12
    config.audio.fade_duration = 0.5
    config.audio.sfx_enabled = False
    config.audio.sfx_dir = "assets/sfx"
    config.audio.sfx_volume = 0.35
    config.audio.bgm_provider = "local"
    config.audio.ducking_factor = 0.25
    config.audio.lyria_prompt_map = {}

    # intro/outro
    config.intro_outro.intro_path = ""
    config.intro_outro.outro_path = ""
    config.intro_outro.intro_duration = 2.0
    config.intro_outro.outro_duration = 2.0

    # providers
    config.providers.visual_styles = ()
    config.providers.tts_voice = "ko-KR-SunHiNeural"

    openai_client = MagicMock()
    return RenderStep(
        config=config,
        openai_client=openai_client,
        job_index=0,
        channel_key=channel_key,
        video_renderer_backend=video_renderer_backend,
    )


def _make_fake_clip(w: int = 1200, h: int = 2200, duration: float = 3.0):
    """MoviePy clip을 시뮬레이트하는 MagicMock 생성."""
    clip = MagicMock()
    clip.w = w
    clip.h = h
    clip.duration = duration

    def _resized(scale_or_func):
        new_clip = MagicMock()
        s = scale_or_func(0.0) if callable(scale_or_func) else scale_or_func
        new_clip.w = int(w * s)
        new_clip.h = int(h * s)
        new_clip.duration = duration
        new_clip.cropped = MagicMock(return_value=new_clip)
        new_clip.transform = MagicMock(return_value=new_clip)
        new_clip.with_duration = MagicMock(return_value=new_clip)
        return new_clip

    clip.resized = MagicMock(side_effect=_resized)
    clip.cropped = MagicMock(return_value=clip)
    clip.transform = MagicMock(return_value=clip)
    clip.with_duration = MagicMock(return_value=clip)
    return clip


class _DummyClip:
    def __init__(
        self,
        name: str,
        *,
        duration: float = 3.0,
        w: int = 1080,
        h: int = 1920,
        audio=None,
    ) -> None:
        self.name = name
        self.duration = duration
        self.w = w
        self.h = h
        self.audio = audio
        self.closed = False
        self.effects: list = []
        self.start = 0.0
        self.position = None
        self.mask = None

    def with_effects(self, effects):
        self.effects.extend(effects)
        return self

    def with_audio(self, audio):
        self.audio = audio
        return self

    def with_duration(self, duration: float):
        self.duration = duration
        return self

    def with_start(self, start: float):
        self.start = start
        return self

    def with_position(self, position):
        self.position = position
        return self

    def with_mask(self, mask):
        self.mask = mask
        return self

    def subclipped(self, start: float, end: float):
        return _DummyClip(
            f"{self.name}:sub",
            duration=max(0.0, end - start),
            w=self.w,
            h=self.h,
            audio=self.audio,
        )

    def resized(self, scale_or_func):
        scale = scale_or_func(0.0) if callable(scale_or_func) else scale_or_func
        return _DummyClip(
            f"{self.name}:resized",
            duration=self.duration,
            w=max(1, int(self.w * scale)),
            h=max(1, int(self.h * scale)),
            audio=self.audio,
        )

    def cropped(self, *, x1, y1, x2, y2):
        return _DummyClip(
            f"{self.name}:cropped",
            duration=self.duration,
            w=max(1, int(x2 - x1)),
            h=max(1, int(y2 - y1)),
            audio=self.audio,
        )

    def transform(self, _func):
        return self

    def close(self):
        self.closed = True


class _DummyAudioClip(_DummyClip):
    def __init__(self, name: str, *, duration: float = 3.0) -> None:
        super().__init__(name, duration=duration, w=1, h=1, audio=None)


def _configure_render_step_for_run(
    step: RenderStep,
    *,
    captions_mode: str = "karaoke",
    highlight_mode: str = "word",
    bgm_provider: str = "lyria",
    sfx_enabled: bool = False,
) -> None:
    step.config.captions.mode = captions_mode
    step.config.captions.highlight_mode = highlight_mode
    step.config.captions.hook_animation = "pop"
    step.config.providers.tts_voice = "ko-KR-SunHiNeural"
    step.config.audio.bgm_provider = bgm_provider
    step.config.audio.ducking_factor = 0.25
    step.config.audio.lyria_prompt_map = {"default": "calm piano", "ai_tech": "tech pulse"}
    step.config.audio.sfx_enabled = sfx_enabled
    step.config.video.hw_accel = "auto"
    step.config.video.quality_profile = "draft"
    step.config.intro_outro.intro_path = ""
    step.config.intro_outro.outro_path = ""
