from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import requests
from openai import OpenAI

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
        """로컬 WhisperX/faster-whisper로 우선 전사 시도하고, 실패 시 OpenAI whisper-1 API로 fallback."""
        logger.info("[OpenAIClient] 로컬 WhisperX/faster-whisper 전사 우선 시도…")
        try:
            from shorts_maker_v2.providers.whisper_aligner import transcribe_to_word_timings

            # CPU 환경의 밸런스를 고려하여 "medium" 모델로 우선 정밀 분석 시도
            local_words = transcribe_to_word_timings(audio_path, model_size="medium", language="ko")
            if local_words:
                logger.info("[OpenAIClient] 로컬 전사 성공 (단어 수: %d)", len(local_words))
                return local_words

            # "medium"이 실패하거나 빈 결과를 반환한 경우, "base" 모델로 한 번 더 fallback 시도
            logger.info("[OpenAIClient] 로컬 'medium' 전사 결과 없음. 'base' 모델로 재시도…")
            local_words_base = transcribe_to_word_timings(audio_path, model_size="base", language="ko")
            if local_words_base:
                logger.info("[OpenAIClient] 로컬 'base' 전사 성공 (단어 수: %d)", len(local_words_base))
                return local_words_base

        except Exception as local_exc:
            logger.warning("[OpenAIClient] 로컬 전사 시도 중 오류 발생: %s", local_exc)

        # 로컬 분석 실패 시 OpenAI API fallback
        logger.warning("[OpenAIClient] 로컬 전사 실패 -> OpenAI whisper-1 API Fallback 수행")
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
