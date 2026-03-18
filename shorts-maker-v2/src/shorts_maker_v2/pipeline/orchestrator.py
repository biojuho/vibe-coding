from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import threading
import uuid
from typing import Any

import yaml

from shorts_maker_v2.config import AppConfig, resolve_runtime_paths
from shorts_maker_v2.models import JobManifest, SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.error_types import (
    PipelineError,
    PipelineErrorType,
    classify_error,
)
from shorts_maker_v2.pipeline.media_step import MediaStep
from shorts_maker_v2.pipeline.render_step import RenderStep
from shorts_maker_v2.pipeline.research_step import ResearchStep
from shorts_maker_v2.pipeline.script_step import ScriptStep, TopicUnsuitableError
from shorts_maker_v2.pipeline.thumbnail_step import ThumbnailStep
from shorts_maker_v2.providers.google_client import GoogleClient
from shorts_maker_v2.providers.llm_router import LLMRouter
from shorts_maker_v2.providers.openai_client import OpenAIClient
from shorts_maker_v2.providers.pexels_client import PexelsClient
from shorts_maker_v2.render.srt_export import export_srt
from shorts_maker_v2.pipeline.series_engine import SeriesEngine
from shorts_maker_v2.utils.cost_guard import CostGuard
from shorts_maker_v2.utils.cost_tracker import CostTracker
from shorts_maker_v2.utils.pipeline_status import (
    PipelineStatusTracker,
    StepStatus,
)

logger = logging.getLogger(__name__)


class JsonlLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _write(self, level: str, event: str, **fields: Any) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            **fields,
        }
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def info(self, event: str, **fields: Any) -> None:
        self._write("INFO", event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._write("WARNING", event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self._write("ERROR", event, **fields)


class PipelineOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        base_dir: Path,
        script_step: ScriptStep | None = None,
        media_step: MediaStep | None = None,
        render_step: RenderStep | None = None,
        *,
        job_index: int = 0,
        renderer_mode: str | None = None,
        use_shorts_factory: bool | None = None,
    ):
        self.config = config
        self._job_index = job_index
        if renderer_mode is None and use_shorts_factory is not None:
            renderer_mode = "auto" if use_shorts_factory else "native"
        self._renderer_mode = renderer_mode or config.rendering.engine
        if self._renderer_mode not in {"native", "auto", "shorts_factory"}:
            raise ValueError(f"Unsupported renderer_mode: {self._renderer_mode}")
        self._use_shorts_factory = self._renderer_mode in {"auto", "shorts_factory"}
        self.paths = resolve_runtime_paths(config, base_dir)
        self.paths.output_dir.mkdir(parents=True, exist_ok=True)
        self.paths.logs_dir.mkdir(parents=True, exist_ok=True)
        self.paths.runs_dir.mkdir(parents=True, exist_ok=True)

        if script_step and media_step and render_step:
            self.script_step = script_step
            self.media_step = media_step
            self.render_step = render_step
            self.thumbnail_step = ThumbnailStep(
                thumbnail_config=config.thumbnail,
                canva_config=config.canva,
            )
            self.research_step: ResearchStep | None = None
            return

        openai_key = os.getenv("OPENAI_API_KEY", "")
        openai_client = OpenAIClient(api_key=openai_key, request_timeout_sec=config.limits.request_timeout_sec)

        gemini_key = os.getenv("GEMINI_API_KEY", "")
        google_client = None
        if gemini_key:
            google_client = GoogleClient(api_key=gemini_key, request_timeout_sec=config.limits.request_timeout_sec)

        pexels_key = os.getenv("PEXELS_API_KEY", "")
        pexels_client = None
        if pexels_key and (config.providers.visual_stock == "pexels" or config.video.stock_mix_ratio > 0):
            pexels_client = PexelsClient(api_key=pexels_key, request_timeout_sec=config.limits.request_timeout_sec)

        # LLM Router (multi-provider fallback)
        llm_providers = (
            list(config.providers.llm_providers)
            if config.providers.llm_providers
            else [config.providers.llm]
        )
        llm_models = dict(config.providers.llm_models) if config.providers.llm_models else {}
        llm_models.setdefault("openai", config.providers.llm_model)
        llm_router = LLMRouter(
            providers=llm_providers,
            models=llm_models,
            max_retries=config.limits.max_retries,
            request_timeout_sec=config.limits.request_timeout_sec,
        )

        # 채널 프로필 로딩
        channel_profile: dict | None = None
        if hasattr(config, '_channel_key') and config._channel_key:
            channel_profile = self._load_channel_profile(config._channel_key, base_dir)

        if channel_profile:
            self.script_step = script_step or ScriptStep.from_channel_profile(
                config, llm_router, channel_profile, openai_client=openai_client,
                channel_key=config._channel_key,
            )
        else:
            self.script_step = script_step or ScriptStep(
                config=config, llm_router=llm_router, openai_client=openai_client,
            )
        self.media_step = media_step or MediaStep(
            config=config, openai_client=openai_client,
            google_client=google_client, pexels_client=pexels_client,
            llm_router=llm_router, job_index=job_index,
        )
        self.render_step = render_step or RenderStep(
            config=config, openai_client=openai_client,
            llm_router=llm_router, job_index=job_index,
            channel_key=getattr(config, "_channel_key", ""),
        )
        self.thumbnail_step = ThumbnailStep(
            thumbnail_config=config.thumbnail,
            canva_config=config.canva,
            openai_client=openai_client,
        )

        # Research Step (config.research.enabled=True 시 활성화)
        if config.research.enabled:
            research_google = google_client if config.research.provider == "gemini" else None
            research_llm = llm_router if config.research.provider == "llm" or not research_google else llm_router
            self.research_step: ResearchStep | None = ResearchStep(
                config=config,
                google_client=research_google,
                llm_router=research_llm,
            )
        else:
            self.research_step = None

    @staticmethod
    def _load_channel_profile(channel_key: str, base_dir: Path) -> dict | None:
        """channel_profiles.yaml에서 채널 프로필을 로드합니다."""
        profiles_path = base_dir / "channel_profiles.yaml"
        if not profiles_path.exists():
            return None
        try:
            data = yaml.safe_load(profiles_path.read_text(encoding="utf-8"))
            channels = data.get("channels", {})
            return channels.get(channel_key)
        except Exception:
            return None

    @staticmethod
    def _new_job_id() -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        suffix = uuid.uuid4().hex[:8]
        return f"{stamp}-{suffix}"

    def _save_manifest(self, manifest: JobManifest, run_dir: Path) -> tuple[Path, Path]:
        run_manifest = run_dir / "manifest.json"
        output_manifest = self.paths.output_dir / f"{manifest.job_id}_manifest.json"
        payload = manifest.to_dict()
        run_manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        output_manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return run_manifest, output_manifest

    @staticmethod
    def _cleanup_run_dir(run_dir: Path, logger: Any) -> None:
        """실패 시 중간 미디어 파일 정리 (manifest/log는 보존)."""
        media_exts = {".mp3", ".wav", ".mp4", ".png", ".jpg", ".jpeg", ".webp", ".json"}
        keep_names = {"manifest.json"}
        cleaned = 0
        try:
            for f in run_dir.rglob("*"):
                if f.is_file() and f.suffix.lower() in media_exts and f.name not in keep_names:
                    f.unlink(missing_ok=True)
                    cleaned += 1
            logger.info("cleanup_done", cleaned_files=cleaned)
        except Exception as exc:
            logger.warning("cleanup_failed", error=str(exc))

    # ── 패턴 #5: 에이전트 루프 스마트 재시도 ────────────────────────────────

    @staticmethod
    def _smart_retry_strategy(
        error: BaseException,
        step_name: str,
        attempt: int,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        """에이전트 루프: 관찰→사고→행동 전략 결정.

        SiteAgent의 에이전트 루프 패턴(관찰→사고→행동→평가)을 적용:
        에러를 관찰(분류)하고, 복구 전략을 사고(결정)합니다.

        Args:
            error: 발생한 예외
            step_name: 실패한 스텝 이름
            attempt: 현재 시도 횟수
            max_attempts: 최대 시도 횟수

        Returns:
            전략 딕셔너리:
            {
                "action": "retry" | "fallback" | "skip" | "abort",
                "error_type": PipelineErrorType,
                "wait_sec": float,
                "detail": str,
            }
        """
        # 1단계: 관찰 (에러 분류)
        error_type = classify_error(error)

        # 2단계: 사고 (전략 결정)
        if not error_type.is_retryable:
            return {
                "action": "abort",
                "error_type": error_type,
                "wait_sec": 0,
                "detail": f"{error_type.icon} [{step_name}] 복구 불가: {error_type.value}",
            }

        if attempt >= max_attempts:
            return {
                "action": "fallback" if step_name in ("research", "thumbnail") else "abort",
                "error_type": error_type,
                "wait_sec": 0,
                "detail": f"{error_type.icon} [{step_name}] 최대 재시도 초과 ({attempt}/{max_attempts})",
            }

        # 타입별 대기 시간
        wait_sec = error_type.suggested_wait_sec
        if error_type == PipelineErrorType.RATE_LIMIT:
            wait_sec = min(wait_sec * attempt, 60)  # progressive backoff

        return {
            "action": "retry",
            "error_type": error_type,
            "wait_sec": wait_sec,
            "detail": f"{error_type.icon} [{step_name}] 재시도 {attempt}/{max_attempts} ({wait_sec:.0f}s 대기)",
        }

    def run(self, topic: str, output_filename: str | None = None, channel: str = "", parallel: bool = False, resume_job_id: str | None = None) -> JobManifest:
        if resume_job_id:
            job_id = resume_job_id
            run_dir = self.paths.runs_dir / job_id
            if not run_dir.exists():
                raise FileNotFoundError(f"Cannot resume: {run_dir} not found.")
        else:
            job_id = self._new_job_id()
            run_dir = self.paths.runs_dir / job_id
            run_dir.mkdir(parents=True, exist_ok=True)
            
        jlog = JsonlLogger(self.paths.logs_dir / f"{job_id}.jsonl")
        cost_guard = CostGuard(max_cost_usd=self.config.limits.max_cost_usd, price_table=self.config.costs)

        # 패턴 #2: 상태 표시 트래커 초기화
        status = PipelineStatusTracker(job_id=job_id)

        manifest = JobManifest(
            job_id=job_id,
            topic=topic,
            status="running",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        failures: list[dict[str, str]] = []
        jlog.info("job_started", job_id=job_id, topic=topic, channel=channel or "")

        try:
            checkpoint_path = run_dir / "checkpoint.json"
            if resume_job_id and checkpoint_path.exists():
                jlog.info("loading_checkpoint", path=str(checkpoint_path))
                cp_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                title = cp_data["title"]
                hook_pattern = cp_data["hook_pattern"]
                scene_plans = [ScenePlan(**sp) for sp in cp_data["scene_plans"]]
                manifest.title = title
                manifest.scene_count = len(scene_plans)
                manifest.hook_pattern = hook_pattern
                manifest.ab_variant = cp_data.get("ab_variant", {})
                jlog.info("checkpoint_loaded", scene_count=manifest.scene_count)
                status.update("checkpoint", StepStatus.COMPLETED, detail=f"{manifest.scene_count} scenes loaded")
            else:
                # ── Research Step (활성화 시) ──
                research_context = None
                if self.research_step:
                    status.start("research", detail="Gathering facts")
                    try:
                        research_context = self.research_step.run(topic)
                        jlog.info(
                            "research_done",
                            facts=len(research_context.facts),
                            data_points=len(research_context.key_data_points),
                            elapsed_sec=research_context.elapsed_sec,
                        )
                        status.complete("research", detail=f"{len(research_context.facts)} facts")
                    except Exception as exc:
                        # 패턴 #5: 스마트 재시도 — research는 실패해도 계속 진행
                        error_type = classify_error(exc)
                        jlog.warning("research_failed", error=str(exc), error_type=error_type.value)
                        status.fail("research", detail=f"{error_type.icon} {error_type.value}")

                status.start("script", detail="Generating script")
                title, scene_plans, hook_pattern = self.script_step.run(topic, research_context=research_context)
                manifest.title = title
                manifest.scene_count = len(scene_plans)
                manifest.hook_pattern = hook_pattern
                # A/B 변수 기록 (성과 분석용)
                manifest.ab_variant = {
                    "hook_pattern": hook_pattern,
                    "tone_preset": str((ScriptStep._tone_counter - 1) % len(ScriptStep.TONE_PRESETS)),
                    "structure_preset": str((ScriptStep._structure_counter - 1) % max(len(self.config.project.structure_presets or {}), 1)),
                    "caption_combo": str(self._job_index % len(RenderStep._CAPTION_COMBOS)),
                }
                cost_guard.add_llm_cost()
                status.complete("script", detail=f"{manifest.scene_count} scenes, {manifest.title[:30]}")
                
                # 체크포인트 저장
                cp_data = {
                    "title": title,
                    "hook_pattern": hook_pattern,
                    "ab_variant": manifest.ab_variant,
                    "scene_plans": [sp.to_dict() for sp in scene_plans]
                }
                checkpoint_path.write_text(json.dumps(cp_data, ensure_ascii=False, indent=2), encoding="utf-8")
                
                jlog.info("script_ready", scene_count=manifest.scene_count, title=title, hook_pattern=hook_pattern)

            status.start("media", detail="Generating media assets")
            media_runner = self.media_step.run_parallel if parallel else self.media_step.run
            scene_assets, media_failures = media_runner(
                scene_plans=scene_plans,
                run_dir=run_dir,
                cost_guard=cost_guard,
                logger=jlog,
            )
            # 패턴 #1: 에러 타입 세분화 — 미디어 실패를 구조화
            for mf in media_failures:
                error_type = classify_error(Exception(mf.get("message", "")))
                mf["error_type"] = error_type.value
            failures.extend(media_failures)
            jlog.info("media_ready", scene_count=len(scene_assets))
            status.complete("media", detail=f"{len(scene_assets)}/{len(scene_plans)} assets")
            
            if len(scene_assets) < len(scene_plans):
                raise RuntimeError(
                    f"Media generation incomplete. Generated {len(scene_assets)} assets out of {len(scene_plans)} scenes. "
                    "Halting pipeline to prevent rendering a broken video. You can resume this job later."
                )

            # ── 영상 길이 강제: 총 오디오가 MAX_SHORTS_SEC 초과 시 body 씬 트림 ──
            MAX_SHORTS_SEC = 43.0  # 45초 상한 - 인트로/전환 여유 2초
            total_audio = sum(a.duration_sec for a in scene_assets)
            if total_audio > MAX_SHORTS_SEC and len(scene_plans) > 2:
                jlog.warning(
                    "duration_over_budget",
                    total_sec=round(total_audio, 1),
                    max_sec=MAX_SHORTS_SEC,
                )
                # hook(첫 씬)과 cta(마지막 씬)는 보존, 뒤쪽 body 씬부터 제거
                while total_audio > MAX_SHORTS_SEC and len(scene_plans) > 2:
                    # 마지막 body 씬 찾기 (cta 직전)
                    trim_idx = len(scene_plans) - 2
                    # hook도 보존
                    if trim_idx <= 0:
                        break
                    removed_plan = scene_plans.pop(trim_idx)
                    removed_asset = scene_assets.pop(trim_idx)
                    total_audio -= removed_asset.duration_sec
                    jlog.info(
                        "scene_trimmed",
                        removed_scene_id=removed_plan.scene_id,
                        removed_duration=round(removed_asset.duration_sec, 1),
                        remaining_total=round(total_audio, 1),
                    )
                logger.info(
                    "[TRIM] 영상 길이 조정: %d씬 → %.1fs",
                    len(scene_plans), total_audio,
                )
                status.update("media", StepStatus.COMPLETED,
                              detail=f"trimmed to {len(scene_plans)} scenes ({total_audio:.1f}s)")

            safe_output_name = Path(output_filename).name if output_filename else f"{job_id}.mp4"

            # ── Phase 3: ShortsFactory 렌더링 분기 ──
            status.start("render", detail="Rendering video")
            sf_rendered = False
            sf_error: str | None = None
            if self._renderer_mode in {"auto", "shorts_factory"} and channel:
                sf_rendered, sf_error = self._try_shorts_factory_render(
                    channel=channel,
                    scene_plans=scene_plans,
                    scene_assets=scene_assets,
                    output_path=self.paths.output_dir / safe_output_name,
                    logger=jlog,
                )
            elif self._renderer_mode == "shorts_factory":
                raise RuntimeError("renderer_mode=shorts_factory requires --channel.")

            if sf_rendered:
                output_path = self.paths.output_dir / safe_output_name
            else:
                if self._renderer_mode == "shorts_factory":
                    raise RuntimeError(sf_error or "ShortsFactory render failed.")
                # 기존 render_step 경로 (폴백 또는 기본)
                output_path = self.render_step.run(
                    scene_plans=scene_plans,
                    scene_assets=scene_assets,
                    output_dir=self.paths.output_dir,
                    output_filename=safe_output_name,
                    run_dir=run_dir,
                    title=title,
                    topic=topic,
                )

            manifest.output_path = output_path.resolve().as_posix()
            manifest.total_duration_sec = round(sum(item.duration_sec for item in scene_assets), 3)
            # YouTube Shorts 상한 (45초) 체크
            if manifest.total_duration_sec > 45:
                jlog.warning(
                    "shorts_overlength",
                    total_sec=manifest.total_duration_sec,
                    limit_sec=45,
                    message=f"⚠️ 영상 {manifest.total_duration_sec:.1f}s > 45s Shorts 상한! 길이 확인 필요.",
                )
            manifest.status = "success"
            manifest.ab_variant["renderer"] = "shorts_factory" if sf_rendered else "native"
            status.complete("render", detail=f"{manifest.total_duration_sec:.1f}s")
            jlog.info(
                "render_done",
                output_path=manifest.output_path,
                total_duration_sec=manifest.total_duration_sec,
                renderer="shorts_factory" if sf_rendered else "native",
            )

            status.start("thumbnail", detail="Generating thumbnail")
            thumb_path = self.thumbnail_step.run(title=title, output_dir=self.paths.output_dir, topic=topic)
            if thumb_path:
                manifest.thumbnail_path = thumb_path
                jlog.info("thumbnail_done", thumbnail_path=thumb_path)
                status.complete("thumbnail")
            else:
                status.update("thumbnail", StepStatus.SKIPPED)

            # SRT 자막 내보내기 (Whisper 타이밍 기반, fallback: narration 텍스트)
            try:
                words_json_paths: list[Path] = []
                scene_offsets: list[float] = []
                narration_texts: list[str] = []
                scene_durations: list[float] = []
                cursor = 0.0
                for plan, asset in zip(scene_plans, scene_assets):
                    wj = Path(asset.audio_path).parent / f"{Path(asset.audio_path).stem}_words.json"
                    words_json_paths.append(wj)
                    scene_offsets.append(cursor)
                    narration_texts.append(plan.narration_ko)
                    scene_durations.append(asset.duration_sec)
                    cursor += asset.duration_sec
                srt_output = self.paths.output_dir / f"{job_id}.srt"
                srt_path = export_srt(
                    words_json_paths=words_json_paths,
                    scene_offsets=scene_offsets,
                    output_path=srt_output,
                    chunk_size=self.config.captions.words_per_chunk,
                    narrations=narration_texts,
                    durations=scene_durations,
                )
                if srt_path.exists() and srt_path.stat().st_size > 0:
                    manifest.srt_path = srt_path.resolve().as_posix()
                    jlog.info("srt_exported", srt_path=manifest.srt_path)
            except Exception as srt_exc:
                jlog.warning("srt_export_failed", error=str(srt_exc))

            # ── 시리즈 후속편 제안 ──
            try:
                series_engine = SeriesEngine(
                    output_dir=self.paths.output_dir,
                    min_performance_score=30.0,
                )
                series_plan = series_engine.suggest_next(topic)
                if series_plan is not None:
                    manifest.series_suggestion = series_plan.to_dict()
                    jlog.info(
                        "series_suggested",
                        series_id=series_plan.series_id,
                        episode=series_plan.episode,
                        title=series_plan.suggested_title,
                    )
            except Exception as series_exc:
                jlog.warning("series_suggestion_failed", error=str(series_exc))

        except TopicUnsuitableError as exc:
            # 주제 부적합 — 자료 부족으로 스킵 (n8n에서 분기 가능)
            failures.append({"step": "script", "code": "TopicUnsuitableError", "message": str(exc), "error_type": "content_filter"})
            manifest.status = "topic_unsuitable"
            jlog.warning("topic_unsuitable", error=str(exc), topic=topic)
            status.fail("script", detail="topic unsuitable")
        except Exception as exc:
            # 패턴 #1+#5: 에러 타입 세분화 + 스마트 전략 로깅
            error_type = classify_error(exc)
            pe = PipelineError.from_exception(exc, step="pipeline")
            failures.append(pe.to_dict())
            manifest.status = "failed"
            jlog.error(
                "job_failed",
                error=str(exc),
                error_type=error_type.value,
                is_retryable=error_type.is_retryable,
            )
            status.fail("pipeline", detail=f"{error_type.icon} {error_type.value}: {str(exc)[:60]}")
            # 체크포인트 재개를 위해 실패 시에도 미디어 파일을 보존합니다.
            # self._cleanup_run_dir(run_dir, jlog)

        manifest.estimated_cost_usd = round(cost_guard.estimated_cost_usd, 6)
        manifest.failed_steps = failures
        run_manifest_path, output_manifest_path = self._save_manifest(manifest, run_dir=run_dir)
        jlog.info(
            "job_finished",
            status=manifest.status,
            estimated_cost_usd=manifest.estimated_cost_usd,
            run_manifest=run_manifest_path.resolve().as_posix(),
            output_manifest=output_manifest_path.resolve().as_posix(),
            status_summary=status.to_log_record(),
        )

        # 비용 추적기에 기록
        try:
            tracker = CostTracker(logs_dir=self.paths.logs_dir)
            tracker.record(
                job_id=job_id,
                cost_usd=manifest.estimated_cost_usd,
                topic=topic,
                channel=channel,
                status=manifest.status,
                duration_sec=manifest.total_duration_sec,
            )
        except Exception:
            pass  # 비용 추적 실패는 무시 (핵심 흐름에 영향 없음)

        return manifest

    # ── Phase 3: ShortsFactory 렌더링 브리지 ────────────────────────────

    @staticmethod
    def _try_shorts_factory_render(
        *,
        channel: str,
        scene_plans: list[ScenePlan],
        scene_assets: list[SceneAsset],
        output_path: Path,
        logger: Any,
    ) -> tuple[bool, str | None]:
        """ShortsFactory RenderAdapter를 통한 렌더링 시도.

        성공 시 (True, None), 실패 시 (False, error)로 반환하여 기존 render_step으로 폴백합니다.

        Args:
            channel: 채널 키 (e.g., "ai_tech")
            scene_plans: 대본 씬 목록
            scene_assets: 미디어 에셋 목록
            output_path: 최종 출력 경로
            logger: 로거

        Returns:
            렌더링 성공 여부와 실패 메시지
        """
        try:
            from ShortsFactory.interfaces import RenderAdapter

            adapter = RenderAdapter()

            # ScenePlan → dict 변환
            scenes_data = [sp.to_dict() for sp in scene_plans]

            # SceneAsset → 에셋 매핑
            assets_map: dict[int, str] = {
                a.scene_id: a.visual_path for a in scene_assets
            }
            audio_map: dict[int, str] = {
                a.scene_id: a.audio_path for a in scene_assets
            }

            result = adapter.render_with_plan(
                channel_id=channel,
                scenes=scenes_data,
                assets=assets_map,
                output_path=output_path,
                audio_paths=audio_map,
            )

            if result.success:
                logger.info(
                    "shorts_factory_render_ok",
                    channel=channel,
                    template=result.template_used,
                    duration_sec=result.duration_sec,
                )
                return True, None
            else:
                logger.warning(
                    "shorts_factory_render_failed",
                    channel=channel,
                    error=result.error,
                    fallback="native_render_step",
                )
                return False, result.error or "ShortsFactory render failed"

        except Exception as exc:
            logger.warning(
                "shorts_factory_import_failed",
                error=str(exc),
                fallback="native_render_step",
            )
            return False, str(exc)
