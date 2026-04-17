"""MediaVisualMixin — 개별 비주얼 생성기 메서드.

각 프로바이더(DALL-E, Google Veo, Pollinations, Pexels)별 생성 함수와
프롬프트 정화, 색상 팔레트 추출, placeholder 생성을 포함합니다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from shorts_maker_v2.config import AppConfig
    from shorts_maker_v2.providers.google_client import GoogleClient
    from shorts_maker_v2.providers.llm_router import LLMRouter
    from shorts_maker_v2.providers.openai_client import OpenAIClient
    from shorts_maker_v2.providers.pexels_client import PexelsClient

logger = logging.getLogger(__name__)


class MediaVisualMixin:
    """개별 비주얼 생성 메서드를 제공하는 Mixin."""

    config: AppConfig
    openai_client: OpenAIClient
    google_client: GoogleClient | None
    pexels_client: PexelsClient | None
    _llm_router: LLMRouter | None
    _visual_style: str

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
        resp = _req.get(url, params=params, timeout=30)
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
            'composition intact. Output JSON: {"prompt": "..."}'
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
            for _count, idx in counts:
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
