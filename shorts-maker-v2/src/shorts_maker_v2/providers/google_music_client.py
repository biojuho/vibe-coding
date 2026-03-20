from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
import shutil
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_LYRIA_MODEL = "models/lyria-realtime-exp"
DEFAULT_PCM_SAMPLE_RATE_HZ = 48000
DEFAULT_PCM_CHANNELS = 2
DEFAULT_PCM_SAMPLE_WIDTH_BYTES = 2

_PCM_MIME_RE = re.compile(r"audio/(?:l(?P<bits>\d+)|pcm)(?:;(?P<params>.*))?$", re.IGNORECASE)


def _parse_pcm_mime_type(
    mime_type: str,
    *,
    fallback_sample_rate_hz: int = DEFAULT_PCM_SAMPLE_RATE_HZ,
    fallback_channels: int = DEFAULT_PCM_CHANNELS,
    fallback_sample_width_bytes: int = DEFAULT_PCM_SAMPLE_WIDTH_BYTES,
) -> tuple[int, int, int]:
    """Parse PCM metadata from an audio chunk MIME type."""
    sample_rate_hz = fallback_sample_rate_hz
    channels = fallback_channels
    sample_width_bytes = fallback_sample_width_bytes
    if not mime_type:
        return sample_rate_hz, channels, sample_width_bytes

    match = _PCM_MIME_RE.match(mime_type.strip())
    if not match:
        return sample_rate_hz, channels, sample_width_bytes

    bits = match.group("bits")
    if bits and bits.isdigit():
        sample_width_bytes = max(1, int(bits) // 8)

    params = match.group("params") or ""
    for raw_part in params.split(";"):
        part = raw_part.strip()
        if not part or "=" not in part:
            continue
        key, value = (item.strip().lower() for item in part.split("=", 1))
        if key == "rate" and value.isdigit():
            sample_rate_hz = int(value)
        elif key == "channels" and value.isdigit():
            channels = int(value)
        elif key in {"bits", "bitdepth", "sample_size"} and value.isdigit():
            sample_width_bytes = max(1, int(value) // 8)

    return sample_rate_hz, channels, sample_width_bytes


@dataclass
class PcmAudioAccumulator:
    """Collect raw PCM chunks until enough audio has been received."""

    target_duration_sec: float
    sample_rate_hz: int = DEFAULT_PCM_SAMPLE_RATE_HZ
    channels: int = DEFAULT_PCM_CHANNELS
    sample_width_bytes: int = DEFAULT_PCM_SAMPLE_WIDTH_BYTES
    _chunks: list[bytes] = field(default_factory=list)
    _byte_count: int = 0

    @property
    def byte_count(self) -> int:
        return self._byte_count

    @property
    def duration_sec(self) -> float:
        bytes_per_second = self.sample_rate_hz * self.channels * self.sample_width_bytes
        if bytes_per_second <= 0:
            return 0.0
        return self._byte_count / bytes_per_second

    @property
    def target_byte_count(self) -> int:
        bytes_per_second = self.sample_rate_hz * self.channels * self.sample_width_bytes
        return max(1, int(self.target_duration_sec * bytes_per_second))

    @property
    def is_complete(self) -> bool:
        return self._byte_count >= self.target_byte_count

    def update_format_from_mime_type(self, mime_type: str) -> None:
        rate, channels, sample_width = _parse_pcm_mime_type(
            mime_type,
            fallback_sample_rate_hz=self.sample_rate_hz,
            fallback_channels=self.channels,
            fallback_sample_width_bytes=self.sample_width_bytes,
        )
        self.sample_rate_hz = rate
        self.channels = channels
        self.sample_width_bytes = sample_width

    def add_chunk(self, data: bytes, *, mime_type: str = "") -> None:
        if mime_type:
            self.update_format_from_mime_type(mime_type)
        if not data:
            return
        self._chunks.append(data)
        self._byte_count += len(data)

    def to_bytes(self) -> bytes:
        return b"".join(self._chunks)

    def write_wav(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.sample_width_bytes)
            wav_file.setframerate(self.sample_rate_hz)
            wav_file.writeframes(self.to_bytes())
        return output_path


class GoogleMusicClient:
    """Google Lyria realtime client that saves streamed PCM to audio files."""

    def __init__(
        self,
        api_key: str,
        *,
        request_timeout_sec: int = 180,
        api_version: str = "v1alpha",
    ):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for Google Lyria realtime music generation.")
        self.client = genai.Client(api_key=api_key, http_options={"api_version": api_version})
        self.request_timeout_sec = request_timeout_sec

    @classmethod
    def from_env(
        cls,
        *,
        env_key: str = "GEMINI_API_KEY",
        request_timeout_sec: int = 180,
        api_version: str = "v1alpha",
    ) -> GoogleMusicClient:
        api_key = os.getenv(env_key, "")
        if not api_key:
            raise OSError(f"{env_key} is required. Add it to your .env file first.")
        return cls(api_key=api_key, request_timeout_sec=request_timeout_sec, api_version=api_version)

    async def generate_music_file(
        self,
        *,
        prompt: str,
        output_path: Path,
        duration_sec: float = 30.0,
        bpm: int = 90,
        temperature: float = 1.0,
        model: str = DEFAULT_LYRIA_MODEL,
        weight: float = 1.0,
    ) -> Path:
        """Generate music and save it as ``.wav`` or ``.mp3``."""
        if not prompt.strip():
            raise ValueError("prompt must not be empty.")
        if duration_sec <= 0:
            raise ValueError("duration_sec must be > 0.")
        if bpm <= 0:
            raise ValueError("bpm must be > 0.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path

        target_suffix = output_path.suffix.lower()
        if target_suffix not in {".wav", ".mp3"}:
            raise ValueError("output_path must end with .wav or .mp3")

        accumulator = PcmAudioAccumulator(target_duration_sec=duration_sec)

        async with self.client.aio.live.music.connect(model=model) as session:
            await session.set_weighted_prompts(
                prompts=[types.WeightedPrompt(text=prompt, weight=weight)]
            )
            await session.set_music_generation_config(
                config=types.LiveMusicGenerationConfig(
                    bpm=bpm,
                    temperature=temperature,
                )
            )
            await session.play()
            try:
                await asyncio.wait_for(
                    self._receive_until_complete(session=session, accumulator=accumulator),
                    timeout=self.request_timeout_sec,
                )
            finally:
                with contextlib.suppress(Exception):
                    await session.stop()

        if accumulator.byte_count <= 0:
            raise RuntimeError("Lyria returned no audio chunks.")

        wav_path = output_path if target_suffix == ".wav" else output_path.with_suffix(".wav")
        accumulator.write_wav(wav_path)
        logger.info(
            "[Lyria] Saved %.2fs of music to %s",
            accumulator.duration_sec,
            wav_path.name,
        )

        if target_suffix == ".wav":
            return wav_path

        self._transcode_wav_to_mp3(wav_path=wav_path, mp3_path=output_path)
        with contextlib.suppress(OSError):
            wav_path.unlink()
        return output_path

    async def _receive_until_complete(self, *, session, accumulator: PcmAudioAccumulator) -> None:
        async for message in session.receive():
            server_content = getattr(message, "server_content", None)
            if not server_content:
                continue
            audio_chunks = getattr(server_content, "audio_chunks", None) or []
            for audio_chunk in audio_chunks:
                accumulator.add_chunk(
                    getattr(audio_chunk, "data", b"") or b"",
                    mime_type=getattr(audio_chunk, "mime_type", "") or "",
                )
                if accumulator.is_complete:
                    return

    @staticmethod
    def _transcode_wav_to_mp3(*, wav_path: Path, mp3_path: Path) -> Path:
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            raise RuntimeError("ffmpeg is required to export .mp3 files.")

        mp3_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                ffmpeg_bin,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(mp3_path),
            ],
            check=True,
        )
        if not mp3_path.exists() or mp3_path.stat().st_size <= 0:
            raise RuntimeError("ffmpeg completed but produced no mp3 output.")
        return mp3_path
