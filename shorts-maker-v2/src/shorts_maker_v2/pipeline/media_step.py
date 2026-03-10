from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mutagen.mp3 import MP3
from openai import BadRequestError
from PIL import Image, ImageDraw

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.providers.google_client import GoogleClient
from shorts_maker_v2.providers.llm_router import LLMRouter
from shorts_maker_v2.providers.edge_tts_client import EdgeTTSClient
from shorts_maker_v2.providers.openai_client import OpenAIClient
from shorts_maker_v2.providers.pexels_client import PexelsClient
from shorts_maker_v2.utils.cost_guard import CostGuard
from shorts_maker_v2.utils.media_cache import MediaCache
from shorts_maker_v2.utils.retry import retry_with_backoff


class MediaStep:
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

    @staticmethod
    def _log(logger: Any, level: str, event: str, **fields: Any) -> None:
        if logger is None:
            return
        fn = getattr(logger, level, None)
        if callable(fn):
            fn(event, **fields)

    @staticmethod
    def _read_audio_duration(audio_path: Path, fallback_sec: float) -> float:
        try:
            audio = MP3(str(audio_path))
            if audio.info and audio.info.length > 0:
                return float(audio.info.length)
        except Exception:
            pass
        return float(fallback_sec)

    def _generate_audio(self, narration_ko: str, output_path: Path, *, role: str = "body") -> Path:
        # 역할별 음성 매핑 (tts_voice_roles 설정 시)
        voice_roles = self.config.providers.tts_voice_roles
        if voice_roles and role in voice_roles:
            voice = voice_roles[role]
        else:
            voice = self._tts_voice

        # edge-tts 설정 시 무료 Microsoft TTS 사용 + WordBoundary 타이밍 추출
        if self.config.providers.tts == "edge-tts":
            # _words.json 경로: Whisper 없이 자막 동기화 데이터 자동 생성
            words_json_path = output_path.parent / f"{output_path.stem}_words.json"
            audio_result = EdgeTTSClient().generate_tts(
                model=self.config.providers.tts_model,
                voice=voice,
                speed=self.config.providers.tts_speed,
                text=narration_ko,
                output_path=output_path,
                words_json_path=words_json_path,
                role=role,
            )
        else:
            audio_result = self.openai_client.generate_tts(
                model=self.config.providers.tts_model,
                voice=voice,
                speed=self.config.providers.tts_speed,
                text=narration_ko,
                output_path=output_path,
            )

        if self.config.audio.sync_with_whisper and self.openai_client:
            try:
                import json
                words = self.openai_client.transcribe_audio(audio_result)
                words_json_path = audio_result.parent / f"{audio_result.stem}_words.json"
                words_json_path.write_text(
                    json.dumps(words, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
            except Exception:
                pass

        return audio_result

    def _generate_video(self, prompt: str, duration_sec: float, output_path: Path) -> Path:
        if not self.google_client:
            raise RuntimeError("Google client is not available.")
        duration = max(4, min(8, int(round(duration_sec))))
        duration = max(duration, self.config.video.scene_video_duration_sec)
        return self.google_client.generate_video(
            model=self.config.providers.veo_model,
            prompt=prompt,
            aspect_ratio=self.config.video.aspect_ratio,
            duration_seconds=duration,
            output_path=output_path,
            timeout_sec=self.config.limits.request_timeout_sec,
        )

    def _generate_image(self, prompt: str, output_path: Path) -> Path:
        return self.openai_client.generate_image(
            model=self.config.providers.image_model,
            prompt=prompt,
            size=self.config.providers.image_size,
            quality=self.config.providers.image_quality,
            output_path=output_path,
        )

    def _generate_image_pollinations(self, prompt: str, output_path: Path) -> Path:
        """Pollinations.ai FLUX 이미지 생성 — 무료, API 키 불필요."""
        import requests as _req
        if output_path.exists():
            return output_path
        w, h = self.config.video.resolution
        url = f"https://image.pollinations.ai/prompt/{quote(prompt[:1500])}"
        params = {"model": "flux", "width": str(w), "height": str(h), "nologo": "true"}
        resp = _req.get(url, params=params, timeout=120)
        resp.raise_for_status()
        if len(resp.content) < 5000:
            raise ValueError(f"Pollinations returned suspiciously small image: {len(resp.content)}B")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(resp.content)
        return output_path

    def _sanitize_visual_prompt(self, prompt: str) -> str:
        """LLMRouter(7-provider fallback)로 DALL-E safety filter 프롬프트 정화."""
        _system = (
            "You rewrite DALL-E image prompts to avoid content policy violations. "
            "Remove or replace any medical, anatomical, violent, or sensitive terms "
            "with safe abstract/metaphorical alternatives. Keep the visual style and "
            "composition intact. Output JSON: {\"prompt\": \"...\"}"
        )
        _user = f"Original prompt:\n{prompt}\n\nRewrite to be DALL-E safe."

        # 1차: LLMRouter (7-provider fallback)
        if self._llm_router:
            try:
                result = self._llm_router.generate_json(
                    system_prompt=_system,
                    user_prompt=_user,
                    temperature=0.3,
                )
                return str(result.get("prompt", prompt)).strip() or prompt
            except Exception:
                pass

        # 2차 폴백: OpenAI 직접
        sanitized = self.openai_client.generate_json(
            model=self.config.providers.llm_model,
            system_prompt=_system,
            user_prompt=_user,
            temperature=0.3,
        )
        return str(sanitized.get("prompt", prompt)).strip() or prompt

    @staticmethod
    def _extract_palette(image_path: Path, n_colors: int = 3) -> str:
        """이미지에서 주요 색상 팔레트 추출 (가장 많이 쓰인 색상 위주)."""
        try:
            img = Image.open(str(image_path)).convert("RGB")
            # 너무 작으면 부정확하므로 150x150 유지
            img = img.resize((150, 150), Image.Resampling.LANCZOS)
            # FASTOCTREE 로 10개 추출 후 빈도수 정렬
            quantized = img.quantize(colors=10, method=Image.Quantize.FASTOCTREE)
            palette = quantized.getpalette()
            counts = quantized.getcolors()
            
            if not palette or not counts:
                return ""
                
            # (count, index) 정렬 (많이 쓰인 순)
            counts.sort(key=lambda x: x[0], reverse=True)
            
            hex_colors = []
            for count, idx in counts:
                base = idx * 3
                if base + 2 >= len(palette):
                    continue
                r, g, b = palette[base], palette[base + 1], palette[base + 2]
                hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")
                if len(hex_colors) >= n_colors:
                    break
            return ", ".join(hex_colors)
        except Exception:
            return ""

    @staticmethod
    def _generate_placeholder_image(output_path: Path, width: int, height: int) -> Path:
        """DALL-E 실패 시 그라데이션 플레이스홀더 이미지 생성."""
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        for y in range(height):
            r = int(30 + 40 * (y / height))
            g = int(30 + 60 * (y / height))
            b = int(60 + 80 * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path))
        return output_path

    def _generate_stock_video(self, prompt: str, output_path: Path) -> Path:
        if not self.pexels_client:
            raise RuntimeError("Pexels client is not available.")
        target_width, target_height = self.config.video.resolution
        return self.pexels_client.download_video(
            query=prompt,
            output_path=output_path,
            target_width=target_width,
            target_height=target_height,
        )

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

    # ── 씬 역할별 비주얼 프롬프트 가이드 ──
    _ROLE_VISUAL_GUIDE: dict[str, str] = {
        "hook": (
            "[HOOK scene — must be eye-catching] "
            "Use dramatic lighting, bold composition, high contrast, "
            "dynamic camera angle. Make it impossible to scroll past. "
        ),
        "cta": (
            "[CTA scene — call to action] "
            "Clean, minimal background. Action-oriented composition. "
            "Bright, inviting atmosphere. Clear focal point. "
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
            if (_role_guide or _color_hint or _prefix) else scene.visual_prompt_en
        )

    def _generate_best_image(
        self,
        visual_prompt: str,
        img_path: Path,
        duration_sec: float,
        cost_guard: CostGuard,
        video_dir: Path,
        scene: ScenePlan,
        logger: Any,
        use_paid_image: bool = True,
    ) -> tuple[str, str, list[dict[str, str]]]:
        """이미지(또는 비디오) 생성 폴백 체인. (visual_path, visual_type, failures) 반환.

        use_paid_image=False이면 DALL-E 등 유료 이미지 생성을 스킵합니다.
        Body 씬에서 비용 절감을 위해 사용합니다.
        """
        failures: list[dict[str, str]] = []
        visual_type = "image"
        visual_path: Path = img_path
        scene_name = f"scene_{scene.scene_id:02d}"

        # ── 캐시 조회 ──
        cached = self._cache.get(visual_prompt, dest_path=img_path)
        if cached is not None:
            self._log(logger, "info", "image_cache_hit",
                      scene_id=scene.scene_id, cached_path=str(cached))
            return str(cached), visual_type, failures

        wants_video = self.config.providers.visual_primary == "google-veo"
        video_allowed = wants_video and cost_guard.can_use_video(duration_sec)

        if wants_video and not video_allowed:
            self._log(logger, "warning", "video_downgraded_by_cost",
                      scene_id=scene.scene_id,
                      estimated_cost_usd=cost_guard.estimated_cost_usd,
                      max_cost_usd=cost_guard.max_cost_usd)

        if wants_video and video_allowed:
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, vp=video_dir / f"{scene_name}.mp4": self._generate_video(p, duration_sec, vp),
                    max_attempts=self.config.limits.max_retries,
                    base_delay_sec=2.0,
                )
                visual_type = "video"
                cost_guard.add_video_cost(duration_sec)
                return str(visual_path), visual_type, failures
            except Exception as exc:
                failures.append({"step": "visual_primary", "code": type(exc).__name__, "message": str(exc)})
                self._log(logger, "warning", "video_failed_fallback_to_image", scene_id=scene.scene_id, error=str(exc))

        # Body 씬 스톡 영상 믹싱: stock_mix_ratio 확률로 Pexels 스톡 우선 시도
        _is_body = scene.structure_role not in ("hook", "cta")
        _stock_mix = self.config.video.stock_mix_ratio
        _try_stock = (
            visual_type == "image"
            and self.pexels_client
            and (
                self.config.providers.visual_stock == "pexels"
                or (_is_body and _stock_mix > 0 and random.random() < _stock_mix)
            )
        )
        if _try_stock:
            stock_path = video_dir / f"{scene_name}_stock.mp4"
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, sp=stock_path: self._generate_stock_video(p, sp),
                    max_attempts=self.config.limits.max_retries,
                    base_delay_sec=1.0,
                )
                visual_type = "video"
                cost_guard.add_stock_cost()
                self._log(logger, "info", "stock_video_ready",
                          scene_id=scene.scene_id, mixed=_is_body)
                return str(visual_path), visual_type, failures
            except Exception as exc:
                failures.append({"step": "visual_stock", "code": type(exc).__name__, "message": str(exc)})
                self._log(logger, "warning", "stock_video_failed_fallback_to_image", scene_id=scene.scene_id, error=str(exc))

        # 이미지 생성 폴백 체인
        # visual_primary == "google-imagen" 이면 Imagen 3(유료) 우선 시도.
        # visual_primary == "gemini-image" (기본값) 이면 Imagen 스킵, Gemini 무료 직행.
        # Gemini(무료) → Pollinations FLUX(무료) → DALL-E(유료) → Pexels 스톡 → placeholder 순
        image_ready = False
        wants_imagen = self.config.providers.visual_primary == "google-imagen"

        if wants_imagen and use_paid_image and self.google_client:
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, ip=img_path: self.google_client.generate_image_imagen3(prompt=p, output_path=ip),
                    max_attempts=self.config.limits.max_retries,
                    base_delay_sec=1.0,
                )
                cost_guard.add_image_cost()  # Imagen 3 cost ($0.02)
                image_ready = True
                self._log(logger, "info", "image_imagen3_success", scene_id=scene.scene_id)
            except Exception as exc:
                failures.append({"step": "image_imagen3", "code": type(exc).__name__, "message": str(exc)[:120]})
                self._log(logger, "warning", "image_imagen3_failed_fallback_to_free",
                          scene_id=scene.scene_id, error=str(exc))

        if not image_ready and self.google_client:
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, ip=img_path: self.google_client.generate_image(prompt=p, output_path=ip),
                    max_attempts=self.config.limits.max_retries,
                    base_delay_sec=1.0,
                )
                image_ready = True
                self._log(logger, "info", "image_gemini_success", scene_id=scene.scene_id)
            except Exception as exc:
                failures.append({"step": "image_gemini", "code": type(exc).__name__, "message": str(exc)[:120]})
                self._log(logger, "warning", "image_gemini_failed_fallback_to_pollinations",
                          scene_id=scene.scene_id, error=str(exc))

        if not image_ready:
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, ip=img_path: self._generate_image_pollinations(p, ip),
                    max_attempts=self.config.limits.max_retries,
                    base_delay_sec=2.0,
                )
                image_ready = True
                self._log(logger, "info", "image_pollinations_flux_success", scene_id=scene.scene_id)
            except Exception as exc:
                failures.append({"step": "image_pollinations", "code": type(exc).__name__, "message": str(exc)[:120]})
                self._log(logger, "warning", "image_pollinations_failed_fallback_to_dalle",
                          scene_id=scene.scene_id, error=str(exc))

        if not image_ready and use_paid_image:
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, ip=img_path: self._generate_image(p, ip),
                    max_attempts=self.config.limits.max_retries,
                    base_delay_sec=1.0,
                )
                cost_guard.add_image_cost()  # DALL-E cost
                image_ready = True
            except BadRequestError as exc:
                if "content_policy_violation" in str(exc):
                    self._log(logger, "warning", "image_content_policy_blocked",
                              scene_id=scene.scene_id, original_prompt=visual_prompt[:80])
                    failures.append({"step": "image_policy", "code": "ContentPolicy", "message": str(exc)[:120]})
                    try:
                        safe_prompt = self._sanitize_visual_prompt(visual_prompt)
                        self._log(logger, "info", "image_sanitized_retry",
                                  scene_id=scene.scene_id, safe_prompt=safe_prompt[:80])
                        visual_path = self._generate_image(safe_prompt, img_path)
                        cost_guard.add_image_cost()
                        image_ready = True
                    except Exception:
                        pass
                else:
                    failures.append({"step": "image_dalle", "code": type(exc).__name__, "message": str(exc)[:120]})
            except Exception as exc:
                failures.append({"step": "image_dalle", "code": type(exc).__name__, "message": str(exc)[:120]})
        elif not image_ready and not use_paid_image:
            self._log(logger, "info", "image_paid_skipped_body_scene",
                      scene_id=scene.scene_id)

        # content_policy 등 전체 이미지 실패 시 Pexels 스톡 이미지 최종 시도
        if not image_ready and self.pexels_client:
            _stock_fallback_path = video_dir / f"{scene_name}_policy_fallback.mp4"
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, sp=_stock_fallback_path: self._generate_stock_video(p, sp),
                    max_attempts=2,
                    base_delay_sec=1.0,
                )
                visual_type = "video"
                cost_guard.add_stock_cost()
                image_ready = True
                self._log(logger, "info", "stock_fallback_after_policy_block",
                          scene_id=scene.scene_id)
            except Exception as stock_exc:
                failures.append({"step": "stock_policy_fallback", "code": type(stock_exc).__name__, "message": str(stock_exc)[:120]})

        if not image_ready:
            self._log(logger, "warning", "image_all_failed_placeholder", scene_id=scene.scene_id)
            w, h = self.config.video.resolution
            visual_path = self._generate_placeholder_image(img_path, w, h)

        # ── 캐시 저장 (placeholder 제외) ──
        if image_ready:
            self._cache.put(visual_prompt, Path(visual_path) if isinstance(visual_path, str) else visual_path)

        return str(visual_path), visual_type, failures

    def _process_one_scene(
        self,
        scene: ScenePlan,
        audio_dir: Path,
        image_dir: Path,
        video_dir: Path,
        cost_guard: CostGuard,
        logger: Any = None,
        color_hint: str = "",
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
        # Phase 1-C: manual pool management — `with` calls shutdown(wait=True)
        # which blocks on running tasks even after cancel(), wasting time on error.
        _pool = ThreadPoolExecutor(max_workers=2)
        _audio_future = _pool.submit(
            lambda: audio_path if audio_exists else retry_with_backoff(
                lambda: self._generate_audio(scene.narration_ko, audio_path, role=scene.structure_role),
                max_attempts=self.config.limits.max_retries,
                base_delay_sec=1.0,
            )
        )
        # Body 씬은 무료 이미지만 사용 (비용 절감)
        _use_paid = scene.structure_role in ("hook", "cta")

        def _get_visual():
            if visual_path_str:
                return visual_path_str, visual_type, []
            return self._generate_best_image(
                _visual_prompt, img_path, scene.target_sec,
                cost_guard, video_dir, scene, logger, _use_paid,
            )

        _image_future = _pool.submit(_get_visual)

        # TTS 결과 수집 (이미지와 동시에 진행됨)
        try:
            audio_path = _audio_future.result()
        except Exception as exc:
            failures.append({"step": "audio", "code": type(exc).__name__, "message": str(exc)})
            self._log(logger, "error", "audio_failed", scene_id=scene.scene_id, error=str(exc))
            _pool.shutdown(wait=False, cancel_futures=True)
            raise

        # 이미지 결과 수집
        visual_path_str, visual_type, img_failures = _image_future.result()
        failures.extend(img_failures)
        _pool.shutdown(wait=False)

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
                scene, audio_dir, image_dir, video_dir, cost_guard, logger,
                color_hint=palette_hint,
            )
            assets.append(asset)
            all_failures.extend(failures)
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
                    executor.submit(
                        self._process_one_scene,
                        scene, audio_dir, image_dir, video_dir, cost_guard, logger, color_hint,
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
                        all_failures.append({"step": f"scene_{scene_id}", "code": type(exc).__name__, "message": str(exc)})
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
        return assets, all_failures

