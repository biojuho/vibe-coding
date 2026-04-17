"""MediaFallbackMixin — 비주얼 폴백 체인 오케스트레이션.

google-veo → Pexels stock → imagen3 → gemini → pollinations → DALL-E → placeholder
순서의 다단계 폴백 구조를 관리합니다.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

from openai import BadRequestError

from shorts_maker_v2.utils.retry import retry_with_backoff

if TYPE_CHECKING:
    from shorts_maker_v2.models import ScenePlan
    from shorts_maker_v2.utils.cost_guard import CostGuard

logger = logging.getLogger(__name__)


class MediaFallbackMixin:
    """비주얼 생성 폴백 체인을 제공하는 Mixin.

    MediaVisualMixin의 개별 생성 메서드를 호출하며,
    비용 가드, 캐시, 로깅과 연동합니다.
    """

    def _try_video_primary(
        self,
        visual_prompt: str,
        duration_sec: float,
        video_dir: Path,
        scene_name: str,
        cost_guard: CostGuard,
        logger: Any,
        scene_id: int,
        provider_retry_attempts: int | None = None,
    ) -> tuple[str, str] | None:
        """google-veo 비디오 생성 시도.

        Returns:
            (path, "video") 성공 시
            None            provider 불일치·비용 다운그레이드·실제 실패 모두 None 반환.
            실제 예외로 실패한 경우 self._last_video_primary_failed = True 플래그 설정.
        """
        self._last_video_primary_failed = False

        if self.config.providers.visual_primary != "google-veo":
            return None

        if not cost_guard.can_use_video(duration_sec):
            self._log(
                logger,
                "warning",
                "video_downgraded_by_cost",
                scene_id=scene_id,
                estimated_cost_usd=cost_guard.estimated_cost_usd,
                max_cost_usd=cost_guard.max_cost_usd,
            )
            return None

        try:
            path = retry_with_backoff(
                lambda p=visual_prompt, vp=video_dir / f"{scene_name}.mp4": self._generate_video(p, duration_sec, vp),
                max_attempts=self._resolve_retry_attempts(provider_retry_attempts),
                base_delay_sec=2.0,
            )
            cost_guard.add_video_cost(duration_sec)
            return str(path), "video"
        except Exception as exc:
            self._log(logger, "warning", "video_failed_fallback_to_image", scene_id=scene_id, error=str(exc))
            self._last_video_primary_failed = True
            return None

    def _try_stock_video(
        self,
        visual_prompt: str,
        video_dir: Path,
        scene_name: str,
        cost_guard: CostGuard,
        logger: Any,
        scene_id: int,
        *,
        suffix: str = "_stock",
        max_attempts: int = 2,
        provider_retry_attempts: int | None = None,
    ) -> tuple[str, str] | None:
        """Pexels 스톡 비디오 시도. 성공 시 (path, "video"), 실패/불가 시 None."""
        if not self.pexels_client:
            return None
        try:
            stock_path = video_dir / f"{scene_name}{suffix}.mp4"
            path = retry_with_backoff(
                lambda p=visual_prompt, sp=stock_path: self._generate_stock_video(p, sp),
                max_attempts=min(max_attempts, self._resolve_retry_attempts(provider_retry_attempts)),
                base_delay_sec=1.0,
            )
            cost_guard.add_stock_cost()
            return str(path), "video"
        except Exception as exc:
            self._log(logger, "warning", "stock_video_failed_fallback_to_image", scene_id=scene_id, error=str(exc))
            return None

    def _try_image_chain(
        self,
        visual_prompt: str,
        img_path: Path,
        scene: ScenePlan,
        cost_guard: CostGuard,
        logger: Any,
        use_paid_image: bool,
        provider_retry_attempts: int | None = None,
    ) -> tuple[Path, bool, list[dict[str, str]]]:
        """이미지 생성 폴백 체인: imagen3 → gemini → pollinations → dalle → placeholder.

        Returns: (visual_path, image_ready, failures)
        """
        failures: list[dict[str, str]] = []
        visual_path: Path = img_path
        image_ready = False
        scene_id = scene.scene_id
        wants_imagen = self.config.providers.visual_primary == "google-imagen"
        retry_attempts = self._resolve_retry_attempts(provider_retry_attempts)

        # 1. Imagen 3 (유료, visual_primary=="google-imagen" 시만)
        if not image_ready and wants_imagen and use_paid_image and self.google_client:
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, ip=img_path: self.google_client.generate_image_imagen3(
                        prompt=p, output_path=ip
                    ),
                    max_attempts=retry_attempts,
                    base_delay_sec=1.0,
                )
                cost_guard.add_image_cost()
                image_ready = True
                self._log(logger, "info", "image_imagen3_success", scene_id=scene_id)
            except Exception as exc:
                failures.append({"step": "image_imagen3", "code": type(exc).__name__, "message": str(exc)[:120]})
                self._log(logger, "warning", "image_imagen3_failed_fallback_to_free", scene_id=scene_id, error=str(exc))

        # 2. Gemini 무료
        if not image_ready and self.google_client:
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, ip=img_path: self.google_client.generate_image(prompt=p, output_path=ip),
                    max_attempts=retry_attempts,
                    base_delay_sec=1.0,
                )
                image_ready = True
                self._log(logger, "info", "image_gemini_success", scene_id=scene_id)
            except Exception as exc:
                failures.append({"step": "image_gemini", "code": type(exc).__name__, "message": str(exc)[:120]})
                self._log(
                    logger, "warning", "image_gemini_failed_fallback_to_pollinations", scene_id=scene_id, error=str(exc)
                )

        # 3. Pollinations FLUX 무료
        if not image_ready:
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, ip=img_path: self._generate_image_pollinations(p, ip),
                    max_attempts=min(2, retry_attempts),
                    base_delay_sec=1.0,
                )
                image_ready = True
                self._log(logger, "info", "image_pollinations_flux_success", scene_id=scene_id)
            except Exception as exc:
                failures.append({"step": "image_pollinations", "code": type(exc).__name__, "message": str(exc)[:120]})
                self._log(
                    logger, "warning", "image_pollinations_failed_fallback_to_dalle", scene_id=scene_id, error=str(exc)
                )

        # 4. DALL-E 유료
        if not image_ready and use_paid_image:
            try:
                visual_path = retry_with_backoff(
                    lambda p=visual_prompt, ip=img_path: self._generate_image(p, ip),
                    max_attempts=retry_attempts,
                    base_delay_sec=1.0,
                )
                cost_guard.add_image_cost()
                image_ready = True
            except BadRequestError as exc:
                if "content_policy_violation" in str(exc):
                    self._log(
                        logger,
                        "warning",
                        "image_content_policy_blocked",
                        scene_id=scene_id,
                        original_prompt=visual_prompt[:80],
                    )
                    failures.append({"step": "image_policy", "code": "ContentPolicy", "message": str(exc)[:120]})
                    try:
                        safe_prompt = self._sanitize_visual_prompt(visual_prompt)
                        self._log(
                            logger, "info", "image_sanitized_retry", scene_id=scene_id, safe_prompt=safe_prompt[:80]
                        )
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
            self._log(logger, "info", "image_paid_skipped_body_scene", scene_id=scene_id)

        return visual_path, image_ready, failures

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
        provider_retry_attempts: int | None = None,
    ) -> tuple[str, str, list[dict[str, str]]]:
        """이미지(또는 비디오) 생성 폴백 체인. (visual_path, visual_type, failures) 반환.

        use_paid_image=False이면 DALL-E 등 유료 이미지 생성을 스킵합니다.
        Body 씬에서 비용 절감을 위해 사용합니다.
        """
        failures: list[dict[str, str]] = []
        scene_name = f"scene_{scene.scene_id:02d}"

        # ── 캐시 조회 ──
        cached = self._cache.get(visual_prompt, dest_path=img_path)
        if cached is not None:
            self._log(logger, "info", "image_cache_hit", scene_id=scene.scene_id, cached_path=str(cached))
            return str(cached), "image", failures

        # ── 1. google-veo 비디오 ──
        result = self._try_video_primary(
            visual_prompt,
            duration_sec,
            video_dir,
            scene_name,
            cost_guard,
            logger,
            scene.scene_id,
            provider_retry_attempts,
        )
        if result:
            return result[0], result[1], failures
        if self._last_video_primary_failed:
            failures.append(
                {"step": "visual_primary", "code": "VideoFailed", "message": "google-veo unavailable or failed"}
            )

        # ── 2. Pexels 스톡 영상 믹싱 (stock_mix_ratio 확률) ──
        _stock_mix = self.config.video.stock_mix_ratio
        if self.pexels_client and _stock_mix > 0 and random.random() < _stock_mix:
            result = self._try_stock_video(
                visual_prompt,
                video_dir,
                scene_name,
                cost_guard,
                logger,
                scene.scene_id,
                provider_retry_attempts=provider_retry_attempts,
            )
            if result:
                self._log(logger, "info", "stock_video_ready", scene_id=scene.scene_id, mixed=True)
                return result[0], result[1], failures
            failures.append({"step": "visual_stock", "code": "StockFailed", "message": "stock video failed"})

        # ── 3. 이미지 체인: imagen3 → gemini → pollinations → dalle ──
        visual_path, image_ready, img_failures = self._try_image_chain(
            visual_prompt,
            img_path,
            scene,
            cost_guard,
            logger,
            use_paid_image,
            provider_retry_attempts,
        )
        failures.extend(img_failures)

        # ── 4. 전체 이미지 실패 시 Pexels 스톡 최종 폴백 ──
        if not image_ready and self.pexels_client:
            result = self._try_stock_video(
                visual_prompt,
                video_dir,
                scene_name,
                cost_guard,
                logger,
                scene.scene_id,
                suffix="_policy_fallback",
                max_attempts=2,
                provider_retry_attempts=provider_retry_attempts,
            )
            if result:
                self._log(logger, "info", "stock_fallback_after_policy_block", scene_id=scene.scene_id)
                self._cache.put(visual_prompt, Path(result[0]))
                return result[0], result[1], failures
            failures.append(
                {"step": "stock_policy_fallback", "code": "StockFailed", "message": "stock fallback failed"}
            )

        # ── 5. placeholder ──
        if not image_ready:
            self._log(logger, "warning", "image_all_failed_placeholder", scene_id=scene.scene_id)
            w, h = self.config.video.resolution
            visual_path = self._generate_placeholder_image(img_path, w, h)

        # ── 캐시 저장 (placeholder 제외) ──
        if image_ready:
            self._cache.put(visual_prompt, Path(visual_path) if isinstance(visual_path, str) else visual_path)

        return str(visual_path), "image", failures
