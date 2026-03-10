from __future__ import annotations

from pathlib import Path
import base64
import time

from google import genai
from google.genai import types
import requests


class GoogleClient:
    def __init__(self, api_key: str, request_timeout_sec: int = 180):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for Google Veo.")
        self.client = genai.Client(api_key=api_key)
        self.request_timeout_sec = request_timeout_sec

    def generate_video(
        self,
        *,
        model: str,
        prompt: str,
        aspect_ratio: str,
        duration_seconds: int,
        output_path: Path,
        poll_interval_sec: int = 10,
        timeout_sec: int = 300,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        operation = self.client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                aspect_ratio=aspect_ratio,
                duration_seconds=duration_seconds,
            ),
        )

        start = time.monotonic()
        while not operation.done:
            if (time.monotonic() - start) > timeout_sec:
                raise TimeoutError("Timed out while waiting for Google video generation.")
            time.sleep(poll_interval_sec)
            operation = self.client.operations.get(operation)

        if not operation.response or not operation.response.generated_videos:
            raise RuntimeError("Google video generation returned no videos.")

        video_obj = operation.response.generated_videos[0].video
        if hasattr(video_obj, "save"):
            video_obj.save(str(output_path))
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path

        if getattr(video_obj, "video_bytes", None):
            raw = video_obj.video_bytes
            if isinstance(raw, str):
                output_path.write_bytes(base64.b64decode(raw))
            else:
                output_path.write_bytes(raw)
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path

        if getattr(video_obj, "uri", None):
            response = requests.get(video_obj.uri, timeout=self.request_timeout_sec)
            response.raise_for_status()
            output_path.write_bytes(response.content)
            if output_path.exists() and output_path.stat().st_size > 0:
                return output_path

        raise RuntimeError("Google video object could not be saved to file.")

    def generate_image(
        self,
        *,
        prompt: str,
        output_path: Path,
    ) -> Path:
        """Gemini 이미지 생성 (무료 tier: 10 RPM, 500 RPD)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        response = self.client.models.generate_content(
            model="gemini-2.0-flash-exp-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                if len(image_data) < 1000:
                    raise RuntimeError(f"Gemini returned too-small image ({len(image_data)} bytes)")
                output_path.write_bytes(image_data)
                return output_path

        raise RuntimeError("Gemini image generation returned no image data.")

    # Imagen 3 모델 fallback 체인 (001은 2026년 초 shutdown됨)
    _IMAGEN3_MODELS = [
        "imagen-3.0-generate-002",   # 최신 (2026-03 기준)
        "imagen-3.0-fast-generate-001",  # 빠른 대안
        "imagen-3.0-generate-001",   # 레거시 (일부 Vertex AI에서 아직 유효)
    ]

    def generate_image_imagen3(
        self,
        *,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "9:16",
        number_of_images: int = 1,
    ) -> Path:
        """Imagen 3 이미지 생성 ($0.02/img, DALL-E 대비 75% 저렴).

        모델 fallback: imagen-3.0-generate-002 → fast-001 → generate-001
        해상도: aspect_ratio 기반 자동 결정 (9:16 → 768×1344 등)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        last_error: Exception | None = None
        for model_name in self._IMAGEN3_MODELS:
            try:
                response = self.client.models.generate_images(
                    model=model_name,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=number_of_images,
                        aspect_ratio=aspect_ratio,
                    ),
                )

                if not response.generated_images:
                    raise RuntimeError(f"{model_name} returned no images.")

                image_obj = response.generated_images[0].image
                image_data = image_obj.image_bytes
                if not image_data or len(image_data) < 1000:
                    raise RuntimeError(
                        f"{model_name} returned too-small image "
                        f"({len(image_data) if image_data else 0} bytes)"
                    )

                output_path.write_bytes(image_data)
                return output_path
            except Exception as exc:
                last_error = exc
                continue  # 다음 모델 시도

        raise RuntimeError(
            f"All Imagen 3 models failed. Last error: {last_error}"
        )

