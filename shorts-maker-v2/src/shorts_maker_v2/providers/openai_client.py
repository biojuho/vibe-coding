from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from openai import OpenAI
import requests

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self, api_key: str, request_timeout_sec: int = 180):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required.")
        self.client = OpenAI(api_key=api_key, timeout=request_timeout_sec)
        self.request_timeout_sec = request_timeout_sec
        logger.debug("OpenAIClient initialized (timeout=%ds)", request_timeout_sec)

    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> dict:
        logger.info("generate_json: model=%s prompt_len=%d", model, len(user_prompt))
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise ValueError("OpenAI returned empty JSON content.")
        logger.debug("generate_json: response_len=%d", len(content))
        return json.loads(content)

    def generate_tts(
        self,
        *,
        model: str,
        voice: str,
        speed: float,
        text: str,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        logger.info("generate_tts: model=%s voice=%s text_len=%d", model, voice, len(text))
        response = self.client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            speed=speed,
        )
        response.stream_to_file(str(output_path))
        logger.debug("generate_tts: saved %s", output_path)
        return output_path

    def transcribe_audio(self, audio_path: Path) -> list[dict]:
        """Whisper-1로 오디오 전사, 단어 단위 타임스탬프 반환."""
        with audio_path.open("rb") as f:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
        words = getattr(response, "words", None) or []
        return [{"word": w.word, "start": w.start, "end": w.end} for w in words]

    def generate_image(
        self,
        *,
        model: str,
        prompt: str,
        size: str,
        quality: str,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        logger.info("generate_image: model=%s size=%s quality=%s", model, size, quality)
        response = self.client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )

        item = response.data[0]
        if getattr(item, "url", None):
            resp = requests.get(item.url, timeout=self.request_timeout_sec)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
            return output_path

        if getattr(item, "b64_json", None):
            output_path.write_bytes(base64.b64decode(item.b64_json))
            return output_path

        raise ValueError("OpenAI image response did not contain url or b64_json.")

