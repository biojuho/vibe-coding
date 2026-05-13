from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from shorts_maker_v2.config import AppConfig, resolve_runtime_paths
from shorts_maker_v2.models import GateVerdict, JobManifest, SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.error_types import (
    PipelineError,
    PipelineErrorType,
    classify_error,
)
from shorts_maker_v2.pipeline.media_step import MediaStep
from shorts_maker_v2.pipeline.planning_step import PlanningStep
from shorts_maker_v2.pipeline.qc_step import QCStep, SemanticQCStep
from shorts_maker_v2.pipeline.render_step import RenderStep
from shorts_maker_v2.pipeline.research_step import ResearchStep
from shorts_maker_v2.pipeline.script_step import ScriptStep, TopicUnsuitableError
from shorts_maker_v2.pipeline.series_engine import SeriesEngine
from shorts_maker_v2.pipeline.structure_step import StructureStep
from shorts_maker_v2.pipeline.thumbnail_step import ThumbnailStep
from shorts_maker_v2.providers.google_client import GoogleClient
from shorts_maker_v2.providers.llm_router import LLMRouter
from shorts_maker_v2.providers.openai_client import OpenAIClient
from shorts_maker_v2.providers.pexels_client import PexelsClient
from shorts_maker_v2.render.srt_export import export_srt
from shorts_maker_v2.utils.cost_guard import CostGuard
from shorts_maker_v2.utils.cost_tracker import CostTracker
from shorts_maker_v2.utils.pipeline_status import (
    PipelineStatusTracker,
    StepStatus,
)
from shorts_maker_v2.utils.retention_hints import (
    RetentionReport,
    SceneInfo,
    analyze_retention,
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
        with self._lock, self.log_path.open("a", encoding="utf-8") as handle:
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
            list(config.providers.llm_providers) if config.providers.llm_providers else [config.providers.llm]
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
        if hasattr(config, "_channel_key") and config._channel_key:
            channel_profile = self._load_channel_profile(config._channel_key, base_dir)

        if channel_profile:
            self.script_step = script_step or ScriptStep.from_channel_profile(
                config,
                llm_router,
                channel_profile,
                openai_client=openai_client,
                channel_key=config._channel_key,
            )
        else:
            self.script_step = script_step or ScriptStep(
                config=config,
                llm_router=llm_router,
                openai_client=openai_client,
            )
        self.media_step = media_step or MediaStep(
            config=config,
            openai_client=openai_client,
            google_client=google_client,
            pexels_client=pexels_client,
            llm_router=llm_router,
            job_index=job_index,
        )
        self.render_step = render_step or RenderStep(
            config=config,
            openai_client=openai_client,
            llm_router=llm_router,
            job_index=job_index,
            channel_key=getattr(config, "_channel_key", ""),
        )
        self.thumbnail_step = ThumbnailStep(
            thumbnail_config=config.thumbnail,
            canva_config=config.canva,
            openai_client=openai_client,
            google_client=google_client,
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

    def run(
        self,
        topic: str,
        output_filename: str | None = None,
        channel: str = "",
        parallel: bool = False,
        resume_job_id: str | None = None,
    ) -> JobManifest:
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
        degraded_steps: list[dict[str, Any]] = []
        step_timings: dict[str, float] = {}
        pipeline_start = time.perf_counter()
        jlog.info("job_started", job_id=job_id, topic=topic, channel=channel or "")

        def record_degraded_step(step_name: str, exc: BaseException, *, blocking: bool = False) -> None:
            error_type = classify_error(exc)
            degraded_steps.append(
                {
                    "step": step_name,
                    "message": str(exc),
                    "error_type": error_type.value,
                    "is_retryable": error_type.is_retryable,
                    "blocking": blocking,
                }
            )
            jlog.warning(
                f"{step_name}_failed",
                error=str(exc),
                error_type=error_type.value,
                blocking=blocking,
            )
            status.fail(step_name, detail=f"{error_type.icon} {error_type.value}")
            if blocking:
                raise PipelineError(
                    message=str(exc),
                    error_type=error_type,
                    step=step_name,
                    cause=exc,
                    context={"blocking": True},
                )

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
                # ── Gate 1: PlanningStep (기획 자동화) ──
                status.start("planning", detail="Generating production plan")
                _t0 = time.perf_counter()
                try:
                    planning_step = PlanningStep(
                        config=self.config,
                        llm_router=LLMRouter(
                            providers=(
                                list(self.config.providers.llm_providers)
                                if self.config.providers.llm_providers
                                else [self.config.providers.llm]
                            ),
                            models=dict(self.config.providers.llm_models) if self.config.providers.llm_models else {},
                            max_retries=self.config.limits.max_retries,
                            request_timeout_sec=self.config.limits.request_timeout_sec,
                        ),
                    )
                    planning_result = planning_step.run(topic=topic, channel_key=channel)
                    if isinstance(planning_result, tuple):
                        production_plan, planning_verdict = planning_result
                    else:
                        production_plan = planning_result
                        planning_verdict = GateVerdict.PASS
                    manifest.production_plan = production_plan.to_dict()
                    step_timings["planning"] = round(time.perf_counter() - _t0, 2)
                    jlog.info(
                        "planning_done",
                        concept=production_plan.concept[:60],
                        persona=production_plan.target_persona[:40],
                        verdict=planning_verdict.value,
                        perf_sec=step_timings["planning"],
                    )
                    status.complete("planning", detail=production_plan.concept[:40])
                except Exception as exc:
                    # Planning은 실패해도 계속 진행 (optional enhancement)
                    step_timings["planning"] = round(time.perf_counter() - _t0, 2)
                    record_degraded_step("planning", exc, blocking=True)
                    production_plan = None

                # ── Research Step (활성화 시) ──
                research_context = None
                if self.research_step:
                    status.start("research", detail="Gathering facts")
                    _t0 = time.perf_counter()
                    try:
                        research_context = self.research_step.run(topic)
                        step_timings["research"] = round(time.perf_counter() - _t0, 2)
                        jlog.info(
                            "research_done",
                            facts=len(research_context.facts),
                            data_points=len(research_context.key_data_points),
                            elapsed_sec=research_context.elapsed_sec,
                            perf_sec=step_timings["research"],
                        )
                        status.complete("research", detail=f"{len(research_context.facts)} facts")
                    except Exception as exc:
                        # 패턴 #5: 스마트 재시도 — research는 실패해도 계속 진행
                        step_timings["research"] = round(time.perf_counter() - _t0, 2)
                        record_degraded_step("research", exc)

                # ── NEW: StructureStep (Gate 2 — 구성안 설계) ──
                structure_outline = None
                if self.config.project.structure_validation != "off":
                    status.start("structure", detail="Designing scene outline")
                    _t0 = time.perf_counter()
                    try:
                        _llm_router_for_structure = LLMRouter(
                            providers=(
                                list(self.config.providers.llm_providers)
                                if self.config.providers.llm_providers
                                else [self.config.providers.llm]
                            ),
                            models=dict(self.config.providers.llm_models) if self.config.providers.llm_models else {},
                            max_retries=self.config.limits.max_retries,
                            request_timeout_sec=self.config.limits.request_timeout_sec,
                        )
                        structure_step = StructureStep(
                            config=self.config,
                            llm_router=_llm_router_for_structure,
                            channel_key=channel,
                        )
                        structure_outline = structure_step.run(
                            topic=topic,
                            production_plan=production_plan,
                            research_context=research_context,
                        )
                        manifest.structure_outline = structure_outline.to_dict()
                        step_timings["structure"] = round(time.perf_counter() - _t0, 2)
                        # LLM 재시도가 모두 실패해 결정론 폴백으로 떨어졌다면
                        # silently ship 되지 않도록 degraded_steps 로 표면화.
                        # Gate 4 가 PASS 여도 manifest.status 가 "degraded" 로 강등된다.
                        if getattr(structure_outline, "is_fallback", False):
                            degraded_steps.append(
                                {
                                    "step": "structure",
                                    "message": (
                                        "Structure outline fell back to deterministic template "
                                        "after LLM retries — scene intents/visuals may be reduced."
                                    ),
                                    "error_type": "outline_fallback",
                                    "is_retryable": False,
                                    "blocking": False,
                                }
                            )
                            jlog.warning(
                                "structure_fallback_used",
                                scene_count=len(structure_outline.scenes),
                                narrative_arc=structure_outline.narrative_arc,
                            )
                        jlog.info(
                            "structure_done",
                            scene_count=len(structure_outline.scenes),
                            narrative_arc=structure_outline.narrative_arc,
                            is_fallback=getattr(structure_outline, "is_fallback", False),
                            perf_sec=step_timings["structure"],
                        )
                        status.complete("structure", detail=f"{len(structure_outline.scenes)} scenes")
                    except Exception as exc:
                        step_timings["structure"] = round(time.perf_counter() - _t0, 2)
                        record_degraded_step(
                            "structure",
                            exc,
                            blocking=self.config.project.structure_validation == "strict",
                        )
                        structure_outline = None

                status.start("script", detail="Generating script")
                _t0 = time.perf_counter()
                title, scene_plans, hook_pattern = self.script_step.run(
                    topic,
                    research_context=research_context,
                    structure_outline=structure_outline,
                )
                step_timings["script"] = round(time.perf_counter() - _t0, 2)
                manifest.title = title
                manifest.scene_count = len(scene_plans)
                manifest.hook_pattern = hook_pattern
                # A/B 변수 기록 (성과 분석용)
                manifest.ab_variant = {
                    "hook_pattern": hook_pattern,
                    "tone_preset": str((ScriptStep._tone_counter - 1) % len(ScriptStep.TONE_PRESETS)),
                    "structure_preset": str(
                        (ScriptStep._structure_counter - 1) % max(len(self.config.project.structure_presets or {}), 1)
                    ),
                    "caption_combo": str(self._job_index % len(RenderStep._CAPTION_COMBOS)),
                }
                cost_guard.add_llm_cost()
                status.complete("script", detail=f"{manifest.scene_count} scenes, {manifest.title[:30]}")

                # ── Hook Strength Scoring (optional, non-blocking) ──
                try:
                    from shorts_maker_v2.pipeline.hook_scorer import score_hook

                    hook_scenes = [sp for sp in scene_plans if sp.structure_role == "hook"]
                    if hook_scenes:
                        hook_score = score_hook(hook_scenes[0].narration_ko)
                        manifest.hook_score = hook_score.to_dict()
                        jlog.info(
                            "hook_score_done",
                            hook_strength=hook_score.hook_strength,
                            passed=hook_score.passed,
                        )
                        if not hook_score.passed:
                            jlog.warning(
                                "hook_score_weak",
                                strength=hook_score.hook_strength,
                                feedback=hook_score.feedback,
                            )
                except Exception as exc:
                    jlog.warning("hook_score_error", error=str(exc)[:100])
                    logger.debug("Hook scoring failed: %s", exc)

                # 체크포인트 저장
                cp_data = {
                    "title": title,
                    "hook_pattern": hook_pattern,
                    "ab_variant": manifest.ab_variant,
                    "scene_plans": [sp.to_dict() for sp in scene_plans],
                    "structure_outline": structure_outline.to_dict() if structure_outline else None,
                }
                checkpoint_path.write_text(json.dumps(cp_data, ensure_ascii=False, indent=2), encoding="utf-8")

                jlog.info(
                    "script_ready",
                    scene_count=manifest.scene_count,
                    title=title,
                    hook_pattern=hook_pattern,
                    perf_sec=step_timings["script"],
                )

            # ── Content Intelligence: 감성 분석 (optional, non-blocking) ──
            try:
                from shorts_maker_v2.utils.content_intelligence import (
                    analyze_sentiment,
                )

                narrations = [sp.narration_ko for sp in scene_plans]
                sentiment_result = analyze_sentiment(narrations)
                manifest.sentiment = sentiment_result.to_dict()
                jlog.info(
                    "sentiment_analysis_done",
                    primary_emotion=sentiment_result.primary_emotion,
                    intensity=sentiment_result.intensity,
                    tag_count=len(sentiment_result.tags),
                )
            except Exception as exc:
                jlog.warning("sentiment_analysis_error", error=str(exc)[:100])
                logger.debug("Sentiment analysis failed: %s", exc)

            status.start("media", detail="Generating media assets")
            _t0 = time.perf_counter()
            media_runner = self.media_step.run_parallel if parallel else self.media_step.run
            scene_assets, media_failures = media_runner(
                scene_plans=scene_plans,
                run_dir=run_dir,
                cost_guard=cost_guard,
                logger=jlog,
            )
            step_timings["media"] = round(time.perf_counter() - _t0, 2)
            # 패턴 #1: 에러 타입 세분화 — 미디어 실패를 구조화
            for mf in media_failures:
                error_type = classify_error(Exception(mf.get("message", "")))
                mf["error_type"] = error_type.value
            failures.extend(media_failures)
            jlog.info("media_ready", scene_count=len(scene_assets), perf_sec=step_timings["media"])
            status.complete("media", detail=f"{len(scene_assets)}/{len(scene_plans)} assets")

            if len(scene_assets) < len(scene_plans):
                raise RuntimeError(
                    f"Media generation incomplete. Generated {len(scene_assets)} "
                    f"assets out of {len(scene_plans)} scenes. "
                    "Halting pipeline to prevent rendering a broken video. You can resume this job later."
                )

            # ── 씬별 QC + 재시도 (scene_qc_enabled=True일 때) ──
            # qc_strictness="off"이면 enabled여도 블록 자체를 스킵해 비용을 들이지 않는다.
            scene_qc_strictness = self.config.project.qc_strictness
            if self.config.project.scene_qc_enabled and scene_qc_strictness != "off":
                status.start("scene_qc", detail="Per-scene quality check")
                _t0 = time.perf_counter()
                max_scene_retries = self.config.project.scene_qc_max_retries
                all_scene_qc_results = []
                for idx, (plan, asset) in enumerate(zip(scene_plans, scene_assets, strict=False)):
                    prev_plan = scene_plans[idx - 1] if idx > 0 else None
                    next_plan = scene_plans[idx + 1] if idx < len(scene_plans) - 1 else None
                    # 시각 연속성 체크용 prev_asset. scene_assets[idx-1] 는 이전 iteration 에서
                    # 이미 (필요시) regen 된 최신 자산이므로 그대로 사용.
                    prev_asset = scene_assets[idx - 1] if idx > 0 else None
                    qc_result = QCStep.gate_scene_qc(
                        plan,
                        asset,
                        prev_plan,
                        next_plan,
                        strictness=scene_qc_strictness,
                        prev_asset=prev_asset,
                    )
                    retry = 0
                    for retry in range(max_scene_retries):
                        if qc_result.verdict == "pass":
                            break
                        # 실패한 컴포넌트 판별
                        component = "visual" if qc_result.checks.get("audio_ok", True) else "both"
                        jlog.info(
                            "scene_qc_retry",
                            scene_id=plan.scene_id,
                            retry=retry + 1,
                            component=component,
                            issues=qc_result.issues,
                        )
                        new_asset, regen_failures = self.media_step.regenerate_scene(
                            plan,
                            run_dir,
                            cost_guard,
                            jlog,
                            component=component,
                        )
                        scene_assets[idx] = new_asset
                        failures.extend(regen_failures)
                        qc_result = QCStep.gate_scene_qc(
                            plan,
                            new_asset,
                            prev_plan,
                            next_plan,
                            strictness=scene_qc_strictness,
                            prev_asset=prev_asset,
                        )
                    qc_result.retry_count = retry + 1 if qc_result.verdict != "pass" else 0
                    all_scene_qc_results.append(qc_result.to_dict())
                manifest.scene_qc_results = all_scene_qc_results
                step_timings["scene_qc"] = round(time.perf_counter() - _t0, 2)
                summary = PipelineOrchestrator._aggregate_scene_qc_summary(all_scene_qc_results)
                manifest.scene_qc_summary = summary
                if summary["unresolved"]:
                    jlog.warning(
                        "scene_qc_unresolved",
                        unresolved_count=len(summary["unresolved"]),
                        scene_ids=[u["scene_id"] for u in summary["unresolved"]],
                    )
                    degraded_steps.append(
                        {
                            "step": "scene_qc",
                            "message": f"{len(summary['unresolved'])} scene(s) still failing after retries",
                            "scene_ids": [u["scene_id"] for u in summary["unresolved"]],
                            "error_type": "qc_unresolved",
                            "is_retryable": False,
                            "blocking": False,
                        }
                    )
                jlog.info("scene_qc_done", passed=summary["passed"], total=summary["total"])
                status.complete("scene_qc", detail=f"{summary['passed']}/{summary['total']} passed")

            # ── SemanticQC: LLM 기반 씬-씬 의미 QC (opt-in, T-288 non-goal #3) ──
            # script_review 의 글로벌 점수 외에, 최종 narration 상태(scene_qc retry 후)
            # 에서 어느 씬 전환이 약한지를 LLM judge 가 specific 하게 잡는다.
            # 단일 LLM 호출. regen 트리거하지 않고 manifest 와 degraded_steps 로만
            # 표면화 — 씬 narration 재생성은 script 단계 책임.
            if self.config.project.semantic_qc_enabled:
                status.start("semantic_qc", detail="LLM scene-flow + tone judge")
                _t0 = time.perf_counter()
                try:
                    _llm_router_for_semantic = LLMRouter(
                        providers=(
                            list(self.config.providers.llm_providers)
                            if self.config.providers.llm_providers
                            else [self.config.providers.llm]
                        ),
                        models=dict(self.config.providers.llm_models) if self.config.providers.llm_models else {},
                        max_retries=self.config.limits.max_retries,
                        request_timeout_sec=self.config.limits.request_timeout_sec,
                    )
                    semantic_step = SemanticQCStep(
                        llm_router=_llm_router_for_semantic,
                        min_score=self.config.project.semantic_qc_min_score,
                    )
                    structure_outline_for_semantic = locals().get("structure_outline")
                    semantic_result = semantic_step.run(
                        scene_plans=scene_plans,
                        structure_outline=structure_outline_for_semantic,
                    )
                    manifest.semantic_qc = semantic_result.to_dict()
                    step_timings["semantic_qc"] = round(time.perf_counter() - _t0, 2)
                    if semantic_result.verdict == "degraded":
                        degraded_steps.append(
                            {
                                "step": "semantic_qc",
                                "message": (
                                    f"Scene flow / tone consistency below threshold "
                                    f"(flow={semantic_result.scene_flow_score}, "
                                    f"tone={semantic_result.tone_consistency_score}, "
                                    f"min={self.config.project.semantic_qc_min_score}): "
                                    f"{semantic_result.feedback}"
                                ),
                                "error_type": "semantic_below_threshold",
                                "is_retryable": False,
                                "blocking": False,
                                "weak_transitions": semantic_result.weak_transitions,
                            }
                        )
                        jlog.warning(
                            "semantic_qc_degraded",
                            scene_flow=semantic_result.scene_flow_score,
                            tone_consistency=semantic_result.tone_consistency_score,
                            weak_count=len(semantic_result.weak_transitions),
                        )
                        status.fail(
                            "semantic_qc",
                            detail=f"flow={semantic_result.scene_flow_score} tone={semantic_result.tone_consistency_score}",
                        )
                    elif semantic_result.verdict == "error":
                        jlog.warning("semantic_qc_error", feedback=semantic_result.feedback)
                        status.update("semantic_qc", StepStatus.SKIPPED, detail="LLM error")
                    else:
                        jlog.info(
                            "semantic_qc_pass",
                            scene_flow=semantic_result.scene_flow_score,
                            tone_consistency=semantic_result.tone_consistency_score,
                        )
                        status.complete(
                            "semantic_qc",
                            detail=f"flow={semantic_result.scene_flow_score} tone={semantic_result.tone_consistency_score}",
                        )
                except Exception as exc:
                    # 의미 QC 자체 실패는 영상 ship 을 막지 않는다. opt-in 기능.
                    step_timings["semantic_qc"] = round(time.perf_counter() - _t0, 2)
                    jlog.warning("semantic_qc_skipped", error=str(exc)[:200])
                    status.update("semantic_qc", StepStatus.SKIPPED, detail=str(exc)[:60])

            # ── Gate 3: 미디어 QC ──
            status.start("gate3_media_qc", detail="Validating media assets")
            target_dur = tuple(self.config.video.target_duration_sec)
            gate3_report = QCStep.gate3_media(
                scene_plans=scene_plans,
                scene_assets=scene_assets,
                target_duration=target_dur,
            )
            if gate3_report.verdict == GateVerdict.PASS.value:
                jlog.info("gate3_pass", checks=gate3_report.checks)
                status.complete("gate3_media_qc")
            else:
                jlog.warning(
                    "gate3_fail",
                    verdict=gate3_report.verdict,
                    issues=gate3_report.issues,
                )
                status.fail("gate3_media_qc", detail="; ".join(gate3_report.issues[:2]))

            # ── Retention Hints (optional, non-blocking) ──
            try:
                scene_infos = [
                    SceneInfo(
                        scene_id=sp.scene_id,
                        duration_sec=sa.duration_sec,
                        structure_role=sp.structure_role,
                        narration_length=len(sp.narration_ko),
                    )
                    for sp, sa in zip(scene_plans, scene_assets, strict=False)
                ]
                retention_report: RetentionReport = analyze_retention(scene_infos)
                manifest.retention_hints = retention_report.to_dict()
                jlog.info(
                    "retention_hints_done",
                    retention_score=retention_report.estimated_retention_score,
                    loop_potential=retention_report.loop_potential,
                    hint_count=len(retention_report.hints),
                )
            except Exception as exc:
                jlog.warning("retention_hints_error", error=str(exc)[:100])
                logger.debug("Retention hints failed: %s", exc)

            # ── Safe Zone QC (optional, non-blocking) ──
            try:
                sz_report = QCStep.gate_safe_zone(
                    scene_plans=scene_plans,
                    scene_assets=scene_assets,
                )
                if sz_report.verdict == GateVerdict.PASS.value:
                    jlog.info("safe_zone_pass", checks=sz_report.checks)
                else:
                    jlog.warning(
                        "safe_zone_issues",
                        verdict=sz_report.verdict,
                        issues=sz_report.issues,
                    )
            except Exception as exc:
                jlog.warning("safe_zone_error", error=str(exc)[:100])
                logger.debug("Safe zone QC failed: %s", exc)

            # ── 영상 길이 점검: 총 오디오가 MAX_SHORTS_SEC 초과 시 경고만 출력 ──
            # (씬 삭제 대신 경고 로그만 남겨 영상이 완전한 형태로 렌더링되도록 함)
            MAX_SHORTS_SEC = 43.0  # 45초 상한 - 인트로/전환 여유 2초
            total_audio = sum(a.duration_sec for a in scene_assets)
            if total_audio > MAX_SHORTS_SEC:
                jlog.warning(
                    "duration_over_budget",
                    total_sec=round(total_audio, 1),
                    max_sec=MAX_SHORTS_SEC,
                    message=(
                        f"⚠️ 총 오디오 {total_audio:.1f}s > {MAX_SHORTS_SEC}s 예산 초과. "
                        "씬을 삭제하지 않고 그대로 렌더링합니다."
                    ),
                )
                logger.warning(
                    "[TRIM SKIPPED] 총 오디오 %.1fs > %.1fs — 씬 삭제 없이 렌더링",
                    total_audio,
                    MAX_SHORTS_SEC,
                )

            safe_output_name = Path(output_filename).name if output_filename else f"{job_id}.mp4"

            # ── Phase 3: ShortsFactory 렌더링 분기 ──
            status.start("render", detail="Rendering video")
            _t0 = time.perf_counter()
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
            step_timings["render"] = round(time.perf_counter() - _t0, 2)

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
            manifest.ab_variant["renderer"] = "shorts_factory" if sf_rendered else "native"
            status.complete("render", detail=f"{manifest.total_duration_sec:.1f}s")
            jlog.info(
                "render_done",
                output_path=manifest.output_path,
                total_duration_sec=manifest.total_duration_sec,
                renderer="shorts_factory" if sf_rendered else "native",
                perf_sec=step_timings["render"],
            )

            # ── Gate 4: 최종 QC ──
            status.start("gate4_final_qc", detail="Final quality check")
            _is_stub = not isinstance(self.render_step, RenderStep)
            gate4_report = QCStep.gate4_final(
                manifest=manifest,
                output_path=str(output_path),
                target_duration=target_dur if "target_dur" in dir() else (40, 50),
                stub_mode=_is_stub,
            )
            manifest.qc_result = {
                "checks": gate4_report.checks,
                "verdict": gate4_report.verdict,
                "issues": gate4_report.issues,
            }
            if gate4_report.verdict == GateVerdict.PASS.value:
                jlog.info("gate4_pass", checks=gate4_report.checks)
                if degraded_steps:
                    manifest.status = "degraded"
                    jlog.warning("job_degraded", degraded_steps=degraded_steps)
                    status.fail("gate4_final_qc", detail=f"{len(degraded_steps)} degraded prerequisite(s)")
                else:
                    manifest.status = "success"
                    status.complete("gate4_final_qc")
                # ── 업로드 폴더로 복사 ──
                upload_dir = self.config.project.upload_ready_dir
                if upload_dir and manifest.status == "success":
                    try:
                        upload_path = Path(upload_dir)
                        upload_path.mkdir(parents=True, exist_ok=True)
                        for src in [output_path]:
                            if src and Path(str(src)).exists():
                                shutil.copy2(str(src), upload_path / Path(str(src)).name)
                        jlog.info("upload_ready", dir=str(upload_path))
                    except Exception as upload_exc:
                        jlog.warning("upload_copy_failed", error=str(upload_exc))
            else:
                manifest.status = "hold"  # HOLD: 수동 검토 필요
                jlog.warning(
                    "gate4_hold",
                    verdict=gate4_report.verdict,
                    issues=gate4_report.issues,
                )
                status.fail("gate4_final_qc", detail="; ".join(gate4_report.issues[:2]))

            status.start("thumbnail", detail="Generating thumbnail")
            _t0 = time.perf_counter()
            thumb_path = self.thumbnail_step.run(
                title=title,
                output_dir=self.paths.output_dir,
                topic=topic,
                channel_key=getattr(self.config, "_channel_key", ""),
                scene_assets=scene_assets,
                job_id=job_id,
            )
            step_timings["thumbnail"] = round(time.perf_counter() - _t0, 2)
            if thumb_path:
                manifest.thumbnail_path = thumb_path
                jlog.info("thumbnail_done", thumbnail_path=thumb_path, perf_sec=step_timings["thumbnail"])
                status.complete("thumbnail")
            else:
                status.update("thumbnail", StepStatus.SKIPPED)

            # SRT 자막 내보내기 (Whisper 타이밍 기반, fallback: narration 텍스트)
            _t0 = time.perf_counter()
            try:
                words_json_paths: list[Path] = []
                scene_offsets: list[float] = []
                narration_texts: list[str] = []
                scene_durations: list[float] = []
                cursor = 0.0
                for plan, asset in zip(scene_plans, scene_assets, strict=False):
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
                    step_timings["srt"] = round(time.perf_counter() - _t0, 2)
                    jlog.info("srt_exported", srt_path=manifest.srt_path, perf_sec=step_timings["srt"])
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
            failures.append(
                {"step": "script", "code": "TopicUnsuitableError", "message": str(exc), "error_type": "content_filter"}
            )
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
        manifest.degraded_steps = degraded_steps

        # ── 파이프라인 전체 소요 시간 ──
        step_timings["total"] = round(time.perf_counter() - pipeline_start, 2)
        manifest.step_timings = step_timings

        # [PERF] 스텝별 타이밍 요약 로그
        perf_parts = [f"{k}={v:.1f}s" for k, v in step_timings.items()]
        logger.info("[PERF] %s", " | ".join(perf_parts))
        print(f"\n[PERF] {' | '.join(perf_parts)}\n")

        run_manifest_path, output_manifest_path = self._save_manifest(manifest, run_dir=run_dir)
        jlog.info(
            "job_finished",
            status=manifest.status,
            estimated_cost_usd=manifest.estimated_cost_usd,
            run_manifest=run_manifest_path.resolve().as_posix(),
            output_manifest=output_manifest_path.resolve().as_posix(),
            status_summary=status.to_log_record(),
            step_timings=step_timings,
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
        except Exception as exc:
            logger.warning("비용 추적 실패: %s", exc)

        return manifest

    # ── Scene QC 집계 ───────────────────────────────────────────────────

    @staticmethod
    def _aggregate_scene_qc_summary(scene_qc_results: list[dict[str, Any]]) -> dict[str, Any]:
        """씬별 QC 결과 리스트를 manifest용 요약 dict로 집계.

        재시도 후에도 fail로 남은 씬은 ``unresolved``에 모아 manifest로 표면화하고
        오케스트레이터가 degraded_steps에 등록할 수 있도록 한다.
        """
        passed = sum(1 for r in scene_qc_results if r.get("verdict") == "pass")
        unresolved = [
            {
                "scene_id": r.get("scene_id"),
                "retry_count": r.get("retry_count", 0),
                "issues": r.get("issues", []),
            }
            for r in scene_qc_results
            if r.get("verdict") != "pass"
        ]
        return {
            "passed": passed,
            "total": len(scene_qc_results),
            "unresolved": unresolved,
            "verdict": "pass" if not unresolved else "degraded",
        }

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
        return RenderStep.try_render_with_adapter(
            channel=channel,
            scene_plans=scene_plans,
            scene_assets=scene_assets,
            output_path=output_path,
            logger=logger,
        )
