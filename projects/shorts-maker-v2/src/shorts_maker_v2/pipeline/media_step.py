from __future__ import annotations

import logging
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.media.audio_mixin import MediaAudioMixin
from shorts_maker_v2.pipeline.media.fallback_mixin import MediaFallbackMixin
from shorts_maker_v2.pipeline.media.visual_mixin import MediaVisualMixin
from shorts_maker_v2.utils.cost_guard import CostGuard
from shorts_maker_v2.utils.media_cache import MediaCache
from shorts_maker_v2.utils.retry import retry_with_backoff, submit_retry_with_backoff

try:
    from mutagen.mp3 import MP3
except ImportError:  # pragma: no cover - mutagen is a declared runtime dependency.
    MP3 = None

if TYPE_CHECKING:
    from shorts_maker_v2.providers.google_client import GoogleClient
    from shorts_maker_v2.providers.llm_router import LLMRouter
    from shorts_maker_v2.providers.openai_client import OpenAIClient
    from shorts_maker_v2.providers.pexels_client import PexelsClient

logger = logging.getLogger(__name__)


class MediaStep(MediaAudioMixin, MediaVisualMixin, MediaFallbackMixin):
    def __init__(
        self,
        config: AppConfig,
        openai_client: OpenAIClient,
        google_client: GoogleClient | None = None,
        pexels_client: PexelsClient | None = None,
        *,
        llm_router: LLMRouter | None = None,
        job_index: int = 0,
    ):
        self.config = config
        self.openai_client = openai_client
        self.google_client = google_client
        self.pexels_client = pexels_client
        self._llm_router = llm_router
        self._job_index = job_index
        raw_channel_key = getattr(config, "_channel_key", "")
        self._channel_key = raw_channel_key if isinstance(raw_channel_key, str) else ""

        # YPP: TTS voice selection (rotate/random/fixed)
        pool = config.providers.tts_voice_pool
        strategy = config.providers.tts_voice_strategy
        if pool and strategy == "rotate":
            self._tts_voice = pool[job_index % len(pool)]
        elif pool and strategy == "random":
            self._tts_voice = random.choice(pool)
        else:
            self._tts_voice = config.providers.tts_voice

        # YPP: Visual style selection (rotate per job)
        styles = config.providers.visual_styles
        if styles:
            self._visual_style = styles[job_index % len(styles)]
        else:
            self._visual_style = config.providers.image_style_prefix

        # Media cache initialization
        self._cache = MediaCache(
            cache_dir=config.cache.dir,
            enabled=config.cache.enabled,
            max_size_mb=config.cache.max_size_mb,
        )

        # Silent-fail propagation 버퍼.
        # _generate_audio 의 Whisper word-sync 실패 같이 "audio 자체는 성공했지만
        # 단어 타이밍이 비어서 카라오케 자막이 깨질 위험" 같은 경고를 모은다.
        # run/run_parallel 종료 시 all_failures 에 합쳐서 orchestrator
        # degraded_steps 에 노출시킨다(2026-05-19 검증: 이전엔 logger.warning
        # 만 찍히고 manifest.degraded_steps 가 빈 채로 ship 되어 사용자 가시성 0).
        self._pending_audio_warnings: list[dict[str, str]] = []

    @staticmethod
    def _log(logger: Any, level: str, event: str, **fields: Any) -> None:
        if logger is None:
            return
        fn = getattr(logger, level, None)
        if callable(fn):
            fn(event, **fields)

    @staticmethod
    def _scene_id_from_path(path: Path) -> int | None:
        """`scene_05.mp3` 형태의 경로 stem 에서 scene_id 정수를 추출. 실패 시 None.

        Whisper word-sync 등 씬 인자를 직접 받지 않는 단계에서 실패 레코드에
        scene_id 를 각인하기 위한 보조 함수다.
        """
        match = re.search(r"scene_(\d+)", path.stem)
        return int(match.group(1)) if match else None

    @staticmethod
    def _read_audio_duration(audio_path: Path, fallback_sec: float) -> float:
        try:
            if MP3 is None:
                return float(fallback_sec)
            audio = MP3(str(audio_path))
            if audio.info and audio.info.length > 0:
                return float(audio.info.length)
        except Exception as exc:
            logger.debug("[MediaStep] MP3 duration 파싱 실패 (fallback 사용): %s", exc)
        return float(fallback_sec)

    @staticmethod
    def _prepare_dirs(run_dir: Path) -> tuple[Path, Path, Path]:
        media_dir = run_dir / "media"
        audio_dir = media_dir / "audio"
        image_dir = media_dir / "images"
        video_dir = media_dir / "videos"
        audio_dir.mkdir(parents=True, exist_ok=True)
        image_dir.mkdir(parents=True, exist_ok=True)
        video_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir, image_dir, video_dir

    def _resolve_retry_attempts(self, override: int | None = None) -> int:
        if override is None:
            return self.config.limits.max_retries
        return max(1, int(override))

    # ── 씬 역할별 비주얼 프롬프트 가이드 (5-ACT 아트 디렉션) ──
    _ROLE_VISUAL_GUIDE: dict[str, str] = {
        "hook": (
            "[HOOK scene — must be eye-catching] "
            "Use dramatic lighting, bold composition, high contrast, "
            "dynamic camera angle, neon glow. Make it impossible to scroll past. "
        ),
        "problem": (
            "[PROBLEM scene — convey tension and empathy] "
            "Dark moody atmosphere, dim lighting, desaturated colors. "
            "Show struggle or frustration through visual metaphor. "
        ),
        "insight": (
            "[INSIGHT scene — reveal and illuminate] "
            "Bright revealing light breaking through darkness, "
            "split screen or data overlay, vibrant accent colors. "
        ),
        "solution": (
            "[SOLUTION scene — clear and actionable] "
            "Clean modern aesthetic, whiteboard or infographic style, "
            "bright accents on white/light background. Step-by-step feel. "
        ),
        "cta": (
            "[CTA scene — call to action] "
            "Clean, minimal background. Action-oriented composition. "
            "Bright, inviting atmosphere. Clear focal point. "
        ),
        "closing": (
            "[CLOSING scene — contemplative] "
            "Soft ambient lighting, wide establishing shot, peaceful atmosphere, "
            "gentle fade, cinematic stillness. "
        ),
    }

    def _build_visual_prompt(self, scene: ScenePlan, color_hint: str) -> str:
        """씬 역할별 비주얼 프롬프트 조합."""
        _prefix = self._visual_style
        _role_guide = self._ROLE_VISUAL_GUIDE.get(scene.structure_role, "")
        _color_hint = ""
        if color_hint and scene.structure_role != "hook":
            _color_hint = f"[Color palette consistency: use tones of {color_hint}] "
        return (
            f"{_role_guide}{_color_hint}{_prefix} {scene.visual_prompt_en}".strip()
            if (_role_guide or _color_hint or _prefix)
            else scene.visual_prompt_en
        )

    def _process_one_scene(
        self,
        scene: ScenePlan,
        audio_dir: Path,
        image_dir: Path,
        video_dir: Path,
        cost_guard: CostGuard,
        logger: Any = None,
        color_hint: str = "",
        parallelize_provider_io: bool = True,
        provider_retry_attempts: int | None = None,
    ) -> tuple[SceneAsset, list[dict[str, str]]]:
        """단일 씬의 TTS + 비주얼 생성. 스레드 안전.

        TTS와 이미지 생성을 ThreadPoolExecutor로 병렬 실행해 대기 시간 최소화.
        (TTS 3~5s + 이미지 5~10s → 순차 8~15s → 병렬 max(3,5)~10s)
        """
        failures: list[dict[str, str]] = []
        scene_name = f"scene_{scene.scene_id:02d}"
        audio_path = audio_dir / f"{scene_name}.mp3"
        img_path = image_dir / f"{scene_name}.png"
        video_path = video_dir / f"{scene_name}.mp4"
        stock_path = video_dir / f"{scene_name}_stock.mp4"
        _visual_prompt = self._build_visual_prompt(scene, color_hint)

        # ── 이미 생성된 에셋 재사용 (체크포인트 재개용) ──
        audio_exists = audio_path.exists() and audio_path.stat().st_size > 0
        visual_path_str = ""
        visual_type = ""

        if video_path.exists() and video_path.stat().st_size > 0:
            visual_path_str = str(video_path)
            visual_type = "video"
        elif stock_path.exists() and stock_path.stat().st_size > 0:
            visual_path_str = str(stock_path)
            visual_type = "video"
        elif img_path.exists() and img_path.stat().st_size > 0:
            visual_path_str = str(img_path)
            visual_type = "image"

        if audio_exists and visual_path_str:
            duration_sec = self._read_audio_duration(audio_path, fallback_sec=scene.target_sec)
            self._log(logger, "info", "asset_recovered_from_checkpoint", scene_id=scene.scene_id)
            return SceneAsset(
                scene_id=scene.scene_id,
                audio_path=str(audio_path),
                visual_type=visual_type,
                visual_path=visual_path_str,
                duration_sec=duration_sec,
            ), failures

        # ── TTS + 이미지 생성 병렬 실행 ──
        # Body 씬은 무료 이미지만 사용 (비용 절감)
        _use_paid = scene.structure_role in ("hook", "cta", "closing")
        retry_attempts = self._resolve_retry_attempts(provider_retry_attempts)

        def _get_audio() -> Path:
            if audio_exists:
                return audio_path
            return retry_with_backoff(
                lambda: self._generate_audio(scene.narration_ko, audio_path, role=scene.structure_role),
                max_attempts=retry_attempts,
                base_delay_sec=1.0,
            )

        def _get_visual() -> tuple[str, str, list]:
            if visual_path_str:
                return visual_path_str, visual_type, []
            return self._generate_best_image(
                _visual_prompt,
                img_path,
                scene.target_sec,
                cost_guard,
                video_dir,
                scene,
                logger,
                _use_paid,
                retry_attempts,
            )

        should_parallelize_provider_io = parallelize_provider_io and not _use_paid

        if should_parallelize_provider_io:
            with ThreadPoolExecutor(max_workers=2) as pool:
                _audio_future = pool.submit(_get_audio)
                _image_future = pool.submit(_get_visual)

                try:
                    audio_path = _audio_future.result()
                except Exception as exc:
                    failures.append({"step": "audio", "code": type(exc).__name__, "message": str(exc)})
                    self._log(logger, "error", "audio_failed", scene_id=scene.scene_id, error=str(exc))
                    raise

            # 이미지 결과 수집
            visual_path_str, visual_type, img_failures = _image_future.result()
        else:
            try:
                audio_path = _get_audio()
            except Exception as exc:
                failures.append({"step": "audio", "code": type(exc).__name__, "message": str(exc)})
                self._log(logger, "error", "audio_failed", scene_id=scene.scene_id, error=str(exc))
                raise

            visual_path_str, visual_type, img_failures = _get_visual()

        failures.extend(img_failures)

        duration_sec = self._read_audio_duration(audio_path, fallback_sec=scene.target_sec)
        cost_guard.add_tts_cost(duration_sec)
        self._log(logger, "info", "audio_ready", scene_id=scene.scene_id, duration_sec=round(duration_sec, 3))

        asset = SceneAsset(
            scene_id=scene.scene_id,
            audio_path=str(audio_path),
            visual_type=visual_type,
            visual_path=visual_path_str,
            duration_sec=duration_sec,
        )
        self._log(logger, "info", "scene_asset_ready", scene_id=scene.scene_id, visual_type=visual_type)
        # 모든 실패 레코드에 scene_id 를 각인 — manifest.failed_steps 에서 어느
        # 씬의 폴백/실패인지 추적 가능하게 한다. setdefault 라 기존 키는 보존.
        for _failure in failures:
            _failure.setdefault("scene_id", scene.scene_id)
        return asset, failures

    def run(
        self,
        scene_plans: list[ScenePlan],
        run_dir: Path,
        cost_guard: CostGuard,
        logger: Any = None,
    ) -> tuple[list[SceneAsset], list[dict[str, str]]]:
        audio_dir, image_dir, video_dir = self._prepare_dirs(run_dir)
        all_failures: list[dict[str, str]] = []
        assets: list[SceneAsset] = []
        palette_hint = ""  # Hook 씬에서 추출한 색상 팔레트

        for scene in scene_plans:
            asset, failures = self._process_one_scene(
                scene,
                audio_dir,
                image_dir,
                video_dir,
                cost_guard,
                logger,
                color_hint=palette_hint,
            )
            assets.append(asset)
            all_failures.extend(failures)
            # silent-fail 버퍼(Whisper word-sync 등) 도 같이 흘려보낸다.
            if self._pending_audio_warnings:
                all_failures.extend(self._pending_audio_warnings)
                self._pending_audio_warnings = []
            # Hook 씬 처리 후 색상 팔레트 추출 → 이후 씬에 주입
            if scene.structure_role == "hook" and not palette_hint and asset.visual_type == "image":
                palette_hint = self._extract_palette(Path(asset.visual_path))
                if palette_hint:
                    self._log(logger, "info", "palette_extracted", palette=palette_hint)
        return assets, all_failures

    def run_parallel(
        self,
        scene_plans: list[ScenePlan],
        run_dir: Path,
        cost_guard: CostGuard,
        logger: Any = None,
        max_workers: int = 3,
    ) -> tuple[list[SceneAsset], list[dict[str, str]]]:
        """씬별 TTS+비주얼을 ThreadPoolExecutor로 병렬 처리.

        Hook 씬을 먼저 처리하여 색상 팔레트를 추출하고,
        이후 씬에 일관된 비주얼 스타일을 적용합니다.
        """
        audio_dir, image_dir, video_dir = self._prepare_dirs(run_dir)
        all_failures: list[dict[str, str]] = []
        results: dict[int, SceneAsset] = {}
        palette_hint = ""

        def _run_batch(scenes: list[ScenePlan], color_hint: str) -> None:
            if not scenes:
                return
            with ThreadPoolExecutor(max_workers=min(len(scenes), max_workers)) as executor:
                futures = {
                    submit_retry_with_backoff(
                        executor,
                        lambda scene=scene: self._process_one_scene(
                            scene,
                            audio_dir,
                            image_dir,
                            video_dir,
                            cost_guard,
                            logger,
                            color_hint,
                            False,
                            1,
                        ),
                        max_attempts=self.config.limits.max_retries,
                        base_delay_sec=1.0,
                        on_retry=lambda attempt, sleep_sec, exc, scene_id=scene.scene_id: self._log(
                            logger,
                            "warning",
                            "parallel_scene_retry_scheduled",
                            scene_id=scene_id,
                            next_attempt=attempt + 1,
                            delay_sec=round(sleep_sec, 3),
                            error=str(exc),
                        ),
                    ): scene.scene_id
                    for scene in scenes
                }
                for future in as_completed(futures):
                    scene_id = futures[future]
                    try:
                        asset, failures = future.result()
                        results[scene_id] = asset
                        all_failures.extend(failures)
                    except Exception as exc:
                        all_failures.append(
                            {
                                "step": f"scene_{scene_id}",
                                "scene_id": scene_id,
                                "code": type(exc).__name__,
                                "message": str(exc),
                            }
                        )
                        self._log(logger, "error", "parallel_scene_failed", scene_id=scene_id, error=str(exc))

        # Hook 씬 먼저 처리 (팔레트 추출을 위해)
        hook_scenes = [s for s in scene_plans if s.structure_role == "hook"]
        other_scenes = [s for s in scene_plans if s.structure_role != "hook"]

        _run_batch(hook_scenes, "")

        # Hook 씬 팔레트 추출
        for scene in hook_scenes:
            asset = results.get(scene.scene_id)
            if asset and asset.visual_type == "image" and not palette_hint:
                palette_hint = self._extract_palette(Path(asset.visual_path))
                if palette_hint:
                    self._log(logger, "info", "palette_extracted", palette=palette_hint)
                break

        # 나머지 씬 병렬 처리 (palette_hint 적용)
        _run_batch(other_scenes, palette_hint)

        # scene_id 순으로 정렬하여 반환
        assets = [results[s.scene_id] for s in scene_plans if s.scene_id in results]
        # Whisper word-sync 등 silent-fail 누적 경고 drain.
        if self._pending_audio_warnings:
            all_failures.extend(self._pending_audio_warnings)
            self._pending_audio_warnings = []
        return assets, all_failures

    def regenerate_scene(
        self,
        scene: ScenePlan,
        run_dir: Path,
        cost_guard: CostGuard,
        logger: Any = None,
        color_hint: str = "",
        component: str = "both",
    ) -> tuple[SceneAsset, list[dict[str, str]]]:
        """실패 씬의 미디어를 재생성.

        기존 파일을 삭제 후 _process_one_scene을 호출한다.

        Args:
            scene: 재생성할 씬 플랜
            run_dir: 작업 디렉토리
            cost_guard: 비용 가드
            logger: JSONL 로거
            color_hint: 색상 팔레트 힌트
            component: "audio" | "visual" | "both"

        Returns:
            (SceneAsset, failures)
        """
        audio_dir, image_dir, video_dir = self._prepare_dirs(run_dir)
        scene_name = f"scene_{scene.scene_id:02d}"

        # 지정된 컴포넌트의 기존 파일 삭제
        if component in ("audio", "both"):
            audio_path = audio_dir / f"{scene_name}.mp3"
            if audio_path.exists():
                audio_path.unlink(missing_ok=True)

        if component in ("visual", "both"):
            for ext_dir, exts in [
                (image_dir, [".png", ".jpg", ".jpeg", ".webp"]),
                (video_dir, [".mp4"]),
            ]:
                for ext in exts:
                    p = ext_dir / f"{scene_name}{ext}"
                    if p.exists():
                        p.unlink(missing_ok=True)
                    # stock variant
                    p_stock = ext_dir / f"{scene_name}_stock{ext}"
                    if p_stock.exists():
                        p_stock.unlink(missing_ok=True)

        self._log(
            logger,
            "info",
            "scene_regenerate",
            scene_id=scene.scene_id,
            component=component,
        )

        return self._process_one_scene(
            scene,
            audio_dir,
            image_dir,
            video_dir,
            cost_guard,
            logger,
            color_hint=color_hint,
        )
