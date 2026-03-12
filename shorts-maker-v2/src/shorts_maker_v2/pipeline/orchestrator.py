from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import uuid
from typing import Any

import yaml

from shorts_maker_v2.config import AppConfig, resolve_runtime_paths
from shorts_maker_v2.models import JobManifest, ScenePlan
from shorts_maker_v2.pipeline.media_step import MediaStep
from shorts_maker_v2.pipeline.render_step import RenderStep
from shorts_maker_v2.pipeline.script_step import ScriptStep, TopicUnsuitableError
from shorts_maker_v2.pipeline.thumbnail_step import ThumbnailStep
from shorts_maker_v2.providers.google_client import GoogleClient
from shorts_maker_v2.providers.llm_router import LLMRouter
from shorts_maker_v2.providers.openai_client import OpenAIClient
from shorts_maker_v2.providers.pexels_client import PexelsClient
from shorts_maker_v2.render.srt_export import export_srt
from shorts_maker_v2.utils.cost_guard import CostGuard
from shorts_maker_v2.utils.cost_tracker import CostTracker


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
    ):
        self.config = config
        self._job_index = job_index
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
        )
        self.thumbnail_step = ThumbnailStep(
            thumbnail_config=config.thumbnail,
            canva_config=config.canva,
            openai_client=openai_client,
        )

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
            
        logger = JsonlLogger(self.paths.logs_dir / f"{job_id}.jsonl")
        cost_guard = CostGuard(max_cost_usd=self.config.limits.max_cost_usd, price_table=self.config.costs)

        manifest = JobManifest(
            job_id=job_id,
            topic=topic,
            status="running",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        failures: list[dict[str, str]] = []
        logger.info("job_started", job_id=job_id, topic=topic, channel=channel or "")

        try:
            checkpoint_path = run_dir / "checkpoint.json"
            if resume_job_id and checkpoint_path.exists():
                logger.info("loading_checkpoint", path=str(checkpoint_path))
                cp_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                title = cp_data["title"]
                hook_pattern = cp_data["hook_pattern"]
                scene_plans = [ScenePlan(**sp) for sp in cp_data["scene_plans"]]
                manifest.title = title
                manifest.scene_count = len(scene_plans)
                manifest.hook_pattern = hook_pattern
                manifest.ab_variant = cp_data.get("ab_variant", {})
                logger.info("checkpoint_loaded", scene_count=manifest.scene_count)
            else:
                title, scene_plans, hook_pattern = self.script_step.run(topic)
                manifest.title = title
                manifest.scene_count = len(scene_plans)
                manifest.hook_pattern = hook_pattern
                # A/B 변수 기록 (성과 분석용)
                manifest.ab_variant = {
                    "hook_pattern": hook_pattern,
                    "tone_preset": str(ScriptStep._tone_counter - 1),
                    "structure_preset": str(ScriptStep._structure_counter - 1),
                    "caption_combo": str(self._job_index % len(RenderStep._CAPTION_COMBOS)),
                }
                cost_guard.add_llm_cost()
                
                # 체크포인트 저장
                cp_data = {
                    "title": title,
                    "hook_pattern": hook_pattern,
                    "ab_variant": manifest.ab_variant,
                    "scene_plans": [sp.to_dict() for sp in scene_plans]
                }
                checkpoint_path.write_text(json.dumps(cp_data, ensure_ascii=False, indent=2), encoding="utf-8")
                
                logger.info("script_ready", scene_count=manifest.scene_count, title=title, hook_pattern=hook_pattern)

            media_runner = self.media_step.run_parallel if parallel else self.media_step.run
            scene_assets, media_failures = media_runner(
                scene_plans=scene_plans,
                run_dir=run_dir,
                cost_guard=cost_guard,
                logger=logger,
            )
            failures.extend(media_failures)
            logger.info("media_ready", scene_count=len(scene_assets))
            
            if len(scene_assets) < len(scene_plans):
                raise RuntimeError(
                    f"Media generation incomplete. Generated {len(scene_assets)} assets out of {len(scene_plans)} scenes. "
                    "Halting pipeline to prevent rendering a broken video. You can resume this job later."
                )

            safe_output_name = Path(output_filename).name if output_filename else f"{job_id}.mp4"
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
            manifest.status = "success"
            logger.info(
                "render_done",
                output_path=manifest.output_path,
                total_duration_sec=manifest.total_duration_sec,
            )

            thumb_path = self.thumbnail_step.run(title=title, output_dir=self.paths.output_dir, topic=topic)
            if thumb_path:
                manifest.thumbnail_path = thumb_path
                logger.info("thumbnail_done", thumbnail_path=thumb_path)

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
                    logger.info("srt_exported", srt_path=manifest.srt_path)
            except Exception as srt_exc:
                logger.warning("srt_export_failed", error=str(srt_exc))
        except TopicUnsuitableError as exc:
            # 주제 부적합 — 자료 부족으로 스킵 (n8n에서 분기 가능)
            failures.append({"step": "script", "code": "TopicUnsuitableError", "message": str(exc)})
            manifest.status = "topic_unsuitable"
            logger.warning("topic_unsuitable", error=str(exc), topic=topic)
        except Exception as exc:
            failures.append({"step": "pipeline", "code": type(exc).__name__, "message": str(exc)})
            manifest.status = "failed"
            logger.error("job_failed", error=str(exc), error_type=type(exc).__name__)
            # 체크포인트 재개를 위해 실패 시에도 미디어 파일을 보존합니다.
            # self._cleanup_run_dir(run_dir, logger)

        manifest.estimated_cost_usd = round(cost_guard.estimated_cost_usd, 6)
        manifest.failed_steps = failures
        run_manifest_path, output_manifest_path = self._save_manifest(manifest, run_dir=run_dir)
        logger.info(
            "job_finished",
            status=manifest.status,
            estimated_cost_usd=manifest.estimated_cost_usd,
            run_manifest=run_manifest_path.resolve().as_posix(),
            output_manifest=output_manifest_path.resolve().as_posix(),
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
