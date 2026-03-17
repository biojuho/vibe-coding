from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any

import yaml


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectSettings:
    language: str
    default_scene_count: int
    script_review_enabled: bool = False  # True 시 GPT 품질 채점 후 기준 미달 재생성
    script_review_min_score: int = 6     # 10점 만점 최소 기준 (hook/flow/cta 각각)
    structure_presets: dict[str, list[str]] | None = None  # YPP: 콘텐츠 구조 프리셋


@dataclass(frozen=True)
class VideoSettings:
    target_duration_sec: tuple[int, int]
    resolution: tuple[int, int]
    fps: int
    scene_video_duration_sec: int
    aspect_ratio: str
    transition_style: str = "crossfade"  # "crossfade" | "flash" | "cut" | "random"
    encoding_preset: str = "fast"        # ffmpeg preset: ultrafast/fast/medium/slow
    encoding_crf: int = 23               # 품질 기반 인코딩 (0=무손실, 23=기본, 51=최저)
    hw_accel: str = "auto"               # "auto" | "nvenc" | "qsv" | "amf" | "none"
    stock_mix_ratio: float = 0.0         # Body 씬 중 Pexels 스톡 영상 비율 (0.0 ~ 1.0)


@dataclass(frozen=True)
class ProviderSettings:
    llm: str
    tts: str
    visual_primary: str
    visual_fallback: str
    llm_model: str
    tts_model: str
    tts_voice: str
    tts_speed: float
    image_model: str
    image_size: str
    image_quality: str
    veo_model: str
    visual_stock: str = ""  # "pexels" | "" (비활성)
    image_style_prefix: str = ""  # 채널별 이미지 스타일 접두어
    llm_providers: tuple[str, ...] = ()  # fallback 순서 (비어있으면 llm 단일 사용)
    llm_models: dict[str, str] | None = None  # provider별 모델 매핑
    tts_voice_pool: tuple[str, ...] = ()  # YPP: 음성 풀 (비어있으면 tts_voice 단일)
    tts_voice_strategy: str = "fixed"  # fixed | rotate | random
    tts_voice_roles: dict[str, str] | None = None  # YPP: 역할별 음성 매핑 (hook/body/cta)
    visual_styles: tuple[str, ...] = ()  # YPP: 영상별 아트 스타일 풀
    # Gemini 3.1 Thinking Mode (minimal/low/medium/high)
    thinking_level: str = "low"  # 대본 생성용 기본값 (빠른 속도)
    thinking_level_review: str = "high"  # 대본 리뷰용 (심층 추론)
    # Multimodal Embedding (콘텐츠 중복 검사)
    embedding_model: str = "gemini-embedding-2-preview"


@dataclass(frozen=True)
class LimitSettings:
    max_cost_usd: float
    max_retries: int
    request_timeout_sec: int


@dataclass(frozen=True)
class CostTable:
    llm_per_job: float
    tts_per_second: float
    veo_per_second: float
    image_per_scene: float
    stock_per_scene: float = 0.0  # Pexels = 무료


@dataclass(frozen=True)
class PathSettings:
    output_dir: str
    logs_dir: str
    runs_dir: str


@dataclass(frozen=True)
class CaptionSettings:
    font_size: int
    margin_x: int
    bottom_offset: int
    text_color: str
    stroke_color: str
    stroke_width: int
    line_spacing: int
    font_candidates: tuple[str, ...]
    mode: str = "karaoke"       # "static" | "karaoke"
    words_per_chunk: int = 3
    bg_color: str = "#000000"
    bg_opacity: int = 185
    bg_radius: int = 18
    style_preset: str = "default"  # "default" | "neon" | "subtitle" | "bold"
    hook_animation: str = "random" # "random" | "typing" | "glitch" | "popup" | "none"
    highlight_color: str = "#FFD700"  # 카라오케 word-level highlight 색상 (금색)
    highlight_mode: str = "word"      # "word" (단어별 하이라이트) | "chunk" (기존 청크 모드)


@dataclass(frozen=True)
class AudioSettings:
    bgm_dir: str = "assets/bgm"
    bgm_volume: float = 0.12
    fade_duration: float = 0.5
    sfx_enabled: bool = True
    sfx_dir: str = "assets/sfx"
    sfx_volume: float = 0.35
    sync_with_whisper: bool = False


@dataclass(frozen=True)
class IntroOutroSettings:
    intro_path: str = ""
    outro_path: str = ""
    intro_duration: float = 1.5
    outro_duration: float = 1.5


@dataclass(frozen=True)
class CanvaSettings:
    enabled: bool
    design_id: str
    token_file: str


@dataclass(frozen=True)
class ThumbnailSettings:
    mode: str = "pillow"              # "pillow" | "dalle" | "canva" | "none"
    dalle_prompt_template: str = ""   # {title}/{topic} 치환 지원


@dataclass(frozen=True)
class ResearchSettings:
    enabled: bool = False          # True 시 대본 생성 전 웹 리서치 수행
    provider: str = "gemini"       # "gemini" (Google Search Grounding) | "llm" (LLM 지식만)


@dataclass(frozen=True)
class RenderSettings:
    engine: str = "native"  # "native" | "auto" | "shorts_factory"


@dataclass(frozen=True)
class CacheSettings:
    enabled: bool = True
    dir: str = ".cache"
    max_size_mb: int = 500
    ttl_days: int = 30


@dataclass(frozen=True)
class AppConfig:
    project: ProjectSettings
    video: VideoSettings
    providers: ProviderSettings
    limits: LimitSettings
    costs: CostTable
    paths: PathSettings
    captions: CaptionSettings
    audio: AudioSettings
    canva: CanvaSettings
    intro_outro: IntroOutroSettings = IntroOutroSettings()
    thumbnail: ThumbnailSettings = ThumbnailSettings()
    cache: CacheSettings = CacheSettings()
    research: ResearchSettings = ResearchSettings()
    rendering: RenderSettings = RenderSettings()


@dataclass(frozen=True)
class RuntimePaths:
    base_dir: Path
    output_dir: Path
    logs_dir: Path
    runs_dir: Path


def _section(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"Section '{key}' must be an object.")
    return value


def _tuple2_int(value: Any, key: str) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ConfigError(f"'{key}' must be a list of two integers.")
    try:
        return int(value[0]), int(value[1])
    except Exception as exc:
        raise ConfigError(f"'{key}' must be integers.") from exc


def _tuple_str(values: Any, key: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ConfigError(f"'{key}' must be a non-empty list.")
    casted: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"'{key}' values must be non-empty strings.")
        casted.append(value)
    return tuple(casted)


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path).resolve()
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ConfigError("Config root must be an object.")

    project_raw = _section(raw, "project")
    project = ProjectSettings(
        language=str(project_raw.get("language", "ko-KR")),
        default_scene_count=int(project_raw.get("default_scene_count", 7)),
        script_review_enabled=bool(project_raw.get("script_review_enabled", False)),
        script_review_min_score=int(project_raw.get("script_review_min_score", 6)),
        structure_presets={
            str(k): [str(r) for r in v.get("flow", [])]
            for k, v in project_raw.get("structure_presets", {}).items()
            if isinstance(v, dict)
        } or None,
    )
    if project.default_scene_count <= 0:
        raise ConfigError("project.default_scene_count must be > 0.")

    video_raw = _section(raw, "video")
    target_duration_sec = _tuple2_int(video_raw.get("target_duration_sec", [35, 45]), "video.target_duration_sec")
    if target_duration_sec[0] <= 0 or target_duration_sec[1] <= 0 or target_duration_sec[0] > target_duration_sec[1]:
        raise ConfigError("video.target_duration_sec must be positive and ordered [min, max].")
    resolution = _tuple2_int(video_raw.get("resolution", [1080, 1920]), "video.resolution")
    if resolution[0] <= 0 or resolution[1] <= 0:
        raise ConfigError("video.resolution values must be > 0.")

    video = VideoSettings(
        target_duration_sec=target_duration_sec,
        resolution=resolution,
        fps=int(video_raw.get("fps", 30)),
        scene_video_duration_sec=int(video_raw.get("scene_video_duration_sec", 5)),
        aspect_ratio=str(video_raw.get("aspect_ratio", "9:16")),
        transition_style=str(video_raw.get("transition_style", "crossfade")),
        encoding_preset=str(video_raw.get("encoding_preset", "fast")),
        encoding_crf=int(video_raw.get("encoding_crf", 23)),
        hw_accel=str(video_raw.get("hw_accel", "auto")),
        stock_mix_ratio=float(video_raw.get("stock_mix_ratio", 0.0)),
    )
    if video.fps <= 0:
        raise ConfigError("video.fps must be > 0.")
    if video.scene_video_duration_sec <= 0:
        raise ConfigError("video.scene_video_duration_sec must be > 0.")

    providers_raw = _section(raw, "providers")
    llm_providers_raw = providers_raw.get("llm_providers", [])
    llm_providers = tuple(str(p) for p in llm_providers_raw) if isinstance(llm_providers_raw, list) else ()
    llm_models_raw = providers_raw.get("llm_models", None)
    llm_models = dict(llm_models_raw) if isinstance(llm_models_raw, dict) else None

    providers = ProviderSettings(
        llm=str(providers_raw.get("llm", "openai")),
        tts=str(providers_raw.get("tts", "openai")),
        visual_primary=str(providers_raw.get("visual_primary", "google-veo")),
        visual_fallback=str(providers_raw.get("visual_fallback", "openai-image")),
        llm_model=str(providers_raw.get("llm_model", "gpt-4o-mini")),
        tts_model=str(providers_raw.get("tts_model", "tts-1")),
        tts_voice=str(providers_raw.get("tts_voice", "alloy")),
        tts_speed=float(providers_raw.get("tts_speed", 1.05)),
        image_model=str(providers_raw.get("image_model", "dall-e-3")),
        image_size=str(providers_raw.get("image_size", "1024x1792")),
        image_quality=str(providers_raw.get("image_quality", "standard")),
        veo_model=str(providers_raw.get("veo_model", "veo-2.0-generate-001")),
        visual_stock=str(providers_raw.get("visual_stock", "")),
        image_style_prefix=str(providers_raw.get("image_style_prefix", "")),
        llm_providers=llm_providers,
        llm_models=llm_models,
        tts_voice_pool=tuple(
            str(v) for v in providers_raw.get("tts_voice_pool", [])
        ) if isinstance(providers_raw.get("tts_voice_pool"), list) else (),
        tts_voice_strategy=str(providers_raw.get("tts_voice_strategy", "fixed")),
        tts_voice_roles={
            str(k): str(v)
            for k, v in providers_raw.get("tts_voice_roles", {}).items()
        } if isinstance(providers_raw.get("tts_voice_roles"), dict) else None,
        visual_styles=tuple(
            str(s) for s in providers_raw.get("visual_styles", [])
        ) if isinstance(providers_raw.get("visual_styles"), list) else (),
        thinking_level=str(providers_raw.get("thinking_level", "low")),
        thinking_level_review=str(providers_raw.get("thinking_level_review", "high")),
        embedding_model=str(providers_raw.get("embedding_model", "gemini-embedding-2-preview")),
    )

    limits_raw = _section(raw, "limits")
    limits = LimitSettings(
        max_cost_usd=float(limits_raw.get("max_cost_usd", 2.0)),
        max_retries=int(limits_raw.get("max_retries", 3)),
        request_timeout_sec=int(limits_raw.get("request_timeout_sec", 180)),
    )
    if limits.max_cost_usd <= 0:
        raise ConfigError("limits.max_cost_usd must be > 0.")
    if limits.max_retries <= 0:
        raise ConfigError("limits.max_retries must be > 0.")

    costs_raw = _section(raw, "costs")
    costs = CostTable(
        llm_per_job=float(costs_raw.get("llm_per_job", 0.25)),
        tts_per_second=float(costs_raw.get("tts_per_second", 0.0008)),
        veo_per_second=float(costs_raw.get("veo_per_second", 0.03)),
        image_per_scene=float(costs_raw.get("image_per_scene", 0.04)),
        stock_per_scene=float(costs_raw.get("stock_per_scene", 0.0)),
    )

    paths_raw = _section(raw, "paths")
    paths = PathSettings(
        output_dir=str(paths_raw.get("output_dir", "output")),
        logs_dir=str(paths_raw.get("logs_dir", "logs")),
        runs_dir=str(paths_raw.get("runs_dir", "runs")),
    )

    captions_raw = _section(raw, "captions")
    captions = CaptionSettings(
        font_size=int(captions_raw.get("font_size", 64)),
        margin_x=int(captions_raw.get("margin_x", 90)),
        bottom_offset=int(captions_raw.get("bottom_offset", 240)),
        text_color=str(captions_raw.get("text_color", "#FFD700")),
        stroke_color=str(captions_raw.get("stroke_color", "#000000")),
        stroke_width=int(captions_raw.get("stroke_width", 4)),
        line_spacing=int(captions_raw.get("line_spacing", 12)),
        font_candidates=_tuple_str(
            captions_raw.get(
                "font_candidates",
                ["C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/arialbd.ttf"],
            ),
            "captions.font_candidates",
        ),
        mode=str(captions_raw.get("mode", "karaoke")),
        words_per_chunk=int(captions_raw.get("words_per_chunk", 3)),
        bg_color=str(captions_raw.get("bg_color", "#000000")),
        bg_opacity=int(captions_raw.get("bg_opacity", 185)),
        bg_radius=int(captions_raw.get("bg_radius", 18)),
        style_preset=str(captions_raw.get("style_preset", "default")),
        hook_animation=str(captions_raw.get("hook_animation", "random")),
        highlight_color=str(captions_raw.get("highlight_color", "#FFD700")),
        highlight_mode=str(captions_raw.get("highlight_mode", "word")),
    )
    if captions.font_size <= 0:
        raise ConfigError("captions.font_size must be > 0.")
    if captions.margin_x < 0 or captions.bottom_offset < 0:
        raise ConfigError("captions.margin_x and captions.bottom_offset must be >= 0.")
    if captions.stroke_width < 0:
        raise ConfigError("captions.stroke_width must be >= 0.")
    if not (0 <= captions.bg_opacity <= 255):
        raise ConfigError("captions.bg_opacity must be 0–255.")

    # Phase 2-B: range validations
    if not (0 <= video.encoding_crf <= 51):
        raise ConfigError("video.encoding_crf must be 0–51.")
    if not (0.0 <= video.stock_mix_ratio <= 1.0):
        raise ConfigError("video.stock_mix_ratio must be 0.0–1.0.")
    if providers.tts_speed <= 0:
        raise ConfigError("providers.tts_speed must be > 0.")

    audio_raw = _section(raw, "audio")
    audio = AudioSettings(
        bgm_dir=str(audio_raw.get("bgm_dir", "assets/bgm")),
        bgm_volume=float(audio_raw.get("bgm_volume", 0.12)),
        fade_duration=float(audio_raw.get("fade_duration", 0.5)),
        sfx_enabled=bool(audio_raw.get("sfx_enabled", True)),
        sfx_dir=str(audio_raw.get("sfx_dir", "assets/sfx")),
        sfx_volume=float(audio_raw.get("sfx_volume", 0.35)),
    )

    canva_raw = _section(raw, "canva")
    canva = CanvaSettings(
        enabled=bool(canva_raw.get("enabled", False)),
        design_id=str(canva_raw.get("design_id", "")),
        token_file=str(canva_raw.get("token_file", "")),
    )

    io_raw = _section(raw, "intro_outro")
    intro_outro = IntroOutroSettings(
        intro_path=str(io_raw.get("intro_path", "")),
        outro_path=str(io_raw.get("outro_path", "")),
        intro_duration=float(io_raw.get("intro_duration", 1.5)),
        outro_duration=float(io_raw.get("outro_duration", 1.5)),
    )

    thumbnail_raw = _section(raw, "thumbnail")
    thumbnail = ThumbnailSettings(
        mode=str(thumbnail_raw.get("mode", "pillow")),
        dalle_prompt_template=str(thumbnail_raw.get("dalle_prompt_template", "")),
    )

    cache_raw = _section(raw, "cache") if "cache" in raw else {}
    cache = CacheSettings(
        enabled=bool(cache_raw.get("enabled", True)),
        dir=str(cache_raw.get("dir", ".cache")),
        max_size_mb=int(cache_raw.get("max_size_mb", 500)),
        ttl_days=int(cache_raw.get("ttl_days", 30)),
    )

    research_raw = _section(raw, "research") if "research" in raw else {}
    research = ResearchSettings(
        enabled=bool(research_raw.get("enabled", False)),
        provider=str(research_raw.get("provider", "gemini")),
    )

    rendering_raw = _section(raw, "rendering") if "rendering" in raw else {}
    rendering = RenderSettings(
        engine=str(rendering_raw.get("engine", "native")),
    )
    if rendering.engine not in {"native", "auto", "shorts_factory"}:
        raise ConfigError("rendering.engine must be one of: native, auto, shorts_factory.")

    return AppConfig(
        project=project,
        video=video,
        providers=providers,
        limits=limits,
        costs=costs,
        paths=paths,
        captions=captions,
        audio=audio,
        canva=canva,
        intro_outro=intro_outro,
        thumbnail=thumbnail,
        cache=cache,
        research=research,
        rendering=rendering,
    )


def required_env_keys(config: AppConfig) -> tuple[str, ...]:
    keys = {"OPENAI_API_KEY"}
    if config.providers.visual_primary in ("google-veo", "google-imagen"):
        keys.add("GEMINI_API_KEY")
    if config.providers.visual_stock == "pexels":
        keys.add("PEXELS_API_KEY")
    # Multi-provider LLM: at least one of the providers should have a key
    # (actual availability is checked at runtime by LLMRouter)
    provider_key_map = {
        "google": "GEMINI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "xai": "XAI_API_KEY",
    }
    for provider in config.providers.llm_providers:
        env_key = provider_key_map.get(provider)
        if env_key:
            keys.add(env_key)
    return tuple(sorted(keys))


def resolve_runtime_paths(config: AppConfig, base_dir: Path) -> RuntimePaths:
    root = base_dir.resolve()
    return RuntimePaths(
        base_dir=root,
        output_dir=(root / config.paths.output_dir).resolve(),
        logs_dir=(root / config.paths.logs_dir).resolve(),
        runs_dir=(root / config.paths.runs_dir).resolve(),
    )


def validate_environment(config: AppConfig) -> list[str]:
    missing: list[str] = []
    for key in required_env_keys(config):
        if not os.getenv(key):
            missing.append(key)
    return missing
