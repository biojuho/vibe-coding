from __future__ import annotations

import base64
import logging
import math
import time
from pathlib import Path

import requests
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


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
            model="gemini-2.5-flash-image",
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
        "imagen-3.0-generate-002",  # 최신 (2026-03 기준)
        "imagen-3.0-fast-generate-001",  # 빠른 대안
        "imagen-3.0-generate-001",  # 레거시 (일부 Vertex AI에서 아직 유효)
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
                        f"{model_name} returned too-small image ({len(image_data) if image_data else 0} bytes)"
                    )

                output_path.write_bytes(image_data)
                return output_path
            except Exception as exc:
                last_error = exc
                continue  # 다음 모델 시도

        raise RuntimeError(f"All Imagen 3 models failed. Last error: {last_error}")

    # ── Multimodal Embedding (Gemini Embedding 2 Preview) ───────────────────

    def embed_content(
        self,
        *,
        contents: list[str | tuple[bytes, str]],
        model: str = "gemini-embedding-2-preview",
    ) -> list[list[float]]:
        """텍스트, 이미지, 오디오를 멀티모달 임베딩으로 변환.

        Args:
            contents: 임베딩할 콘텐츠 리스트.
                - str: 텍스트
                - tuple[bytes, str]: (바이트 데이터, MIME 타입)
                  예: (image_bytes, "image/png"), (audio_bytes, "audio/mpeg")
            model: 임베딩 모델 (기본: gemini-embedding-2-preview)

        Returns:
            각 콘텐츠의 임베딩 벡터 리스트.

        Example::
            embeddings = client.embed_content(
                contents=[
                    "인공지능의 미래",
                    (image_bytes, "image/png"),
                    (audio_bytes, "audio/mpeg"),
                ],
            )
        """
        parts: list = []
        for item in contents:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, tuple) and len(item) == 2:
                data, mime_type = item
                parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))
            else:
                raise ValueError(f"Invalid content item: expected str or (bytes, mime_type) tuple, got {type(item)}")

        result = self.client.models.embed_content(
            model=model,
            contents=parts,
        )
        embeddings = [list(e.values) for e in result.embeddings]
        logger.info(
            "[Embedding] %d 항목 임베딩 완료 (model=%s, dim=%d)",
            len(embeddings),
            model,
            len(embeddings[0]) if embeddings else 0,
        )
        return embeddings

    @staticmethod
    def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """두 임베딩 벡터 간의 코사인 유사도 계산 (0~1).

        외부 라이브러리 없이 순수 Python으로 계산.
        """
        if len(vec_a) != len(vec_b):
            raise ValueError(f"Vector dimension mismatch: {len(vec_a)} vs {len(vec_b)}")
        dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
