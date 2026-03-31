from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from moviepy.audio.fx import MultiplyVolume

if TYPE_CHECKING:
    from shorts_maker_v2.config import AppConfig
    from shorts_maker_v2.providers.llm_router import LLMRouter
    from shorts_maker_v2.providers.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class RenderAudioMixin:
    """BGM mood classification, Lyria generation, SFX loading, and RMS ducking.

    Mixed into ``RenderStep`` -- all ``self.*`` access refers to RenderStep
    attributes (``config``, ``_llm_router``, ``_openai_client``, etc.).
    """

    # ── BGM 무드 매칭 ─────────────────────────────────────────────────────────

    # 무드별 한국어 키워드 (파일명에도 활용)
    _MOOD_KEYWORDS: dict[str, list[str]] = {
        "dramatic": [
            "블랙홀",
            "우주",
            "죽음",
            "사망",
            "재앙",
            "공포",
            "위험",
            "충격",
            "비밀",
            "경고",
            "무서운",
            "진실",
            "폭발",
            "전쟁",
            "붕괴",
            "최후",
            "멸종",
        ],
        "upbeat": [
            "돈",
            "절약",
            "성공",
            "방법",
            "비결",
            "팁",
            "건강",
            "행복",
            "성장",
            "개선",
            "효과",
            "좋은",
            "최고",
            "쉬운",
            "간단",
            "빠른",
            "부자",
        ],
    }
    # 파일명 기반 무드 감지 키워드
    _BGM_MOOD_NAMES: dict[str, list[str]] = {
        "dramatic": ["dramatic", "cinematic", "epic", "intense", "dark", "suspense"],
        "upbeat": ["upbeat", "happy", "positive", "energetic", "fun", "bright", "pop"],
        "calm": ["calm", "ambient", "chill", "relax", "soft", "peaceful", "gentle"],
    }

    @classmethod
    def _classify_mood_keywords(cls, text: str) -> str:
        """키워드 기반 BGM 무드 분류 (폴백용)."""
        for mood, keywords in cls._MOOD_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return mood
        return "calm"

    def _classify_mood_gpt(self, text: str) -> str | None:
        """LLMRouter(7-provider fallback)로 BGM 무드 분류. 실패 시 None 반환."""
        _system = (
            "You classify YouTube Shorts topics into a BGM mood. "
            'Choose exactly one: "dramatic", "upbeat", or "calm".\n'
            'Output JSON: {"mood": "..."}'
        )
        _user = f"Topic: {text}"

        llm_router: LLMRouter | None = self._llm_router  # type: ignore[attr-defined]
        openai_client: OpenAIClient | None = self._openai_client  # type: ignore[attr-defined]

        # 1차: LLMRouter (7-provider fallback)
        if llm_router:
            try:
                result = llm_router.generate_json(
                    system_prompt=_system,
                    user_prompt=_user,
                    temperature=0.0,
                )
                mood = str(result.get("mood", "")).strip().lower()
                if mood in ("dramatic", "upbeat", "calm"):
                    return mood
            except Exception:
                pass

        # 2차 폴백: OpenAI 직접 (llm_router 없을 때)
        if openai_client:
            try:
                result = openai_client.generate_json(
                    model="gpt-4o-mini",
                    system_prompt=_system,
                    user_prompt=_user,
                    temperature=0.0,
                )
                mood = str(result.get("mood", "")).strip().lower()
                if mood in ("dramatic", "upbeat", "calm"):
                    return mood
            except Exception:
                pass

        return None

    def _classify_mood(self, text: str) -> str:
        """GPT 우선, 실패 시 키워드 폴백."""
        gpt_mood = self._classify_mood_gpt(text)
        if gpt_mood:
            return gpt_mood
        return self._classify_mood_keywords(text)

    # ── BGM file selection / generation ───────────────────────────────────────

    def _pick_bgm_by_mood(self, bgm_files: list[Path], text: str) -> Path:
        """
        텍스트 무드에 맞는 BGM 파일 선택.
        파일명에 무드 키워드가 있으면 우선 선택, 없으면 랜덤 폴백.
        """
        mood = self._classify_mood(text)
        mood_keys = self._BGM_MOOD_NAMES.get(mood, [])
        matched = [f for f in bgm_files if any(k in f.stem.lower() for k in mood_keys)]
        if matched:
            chosen = random.choice(matched)
            logger.info("[BGM] mood=%s -> %s", mood, chosen.name)
            return chosen
        chosen = random.choice(bgm_files)
        logger.info("[BGM] mood=%s (no match, random fallback) -> %s", mood, chosen.name)
        return chosen

    @staticmethod
    def _collect_bgm_files(bgm_dir: Path) -> list[Path]:
        files: list[Path] = []
        for pattern in ("*.mp3", "*.wav", "*.m4a", "*.aac"):
            files.extend(bgm_dir.glob(pattern))
        return sorted(files)

    def _generate_lyria_bgm(
        self,
        *,
        run_dir: Path,
        duration_sec: float,
        channel: str = "",
        topic: str = "",
    ) -> Path | None:
        """Google Lyria로 영상 길이에 맞는 맞춤 BGM을 생성합니다.

        Returns:
            생성된 BGM 파일 경로 또는 None (실패 시)
        """
        import asyncio
        import os

        config: AppConfig = self.config  # type: ignore[attr-defined]

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.info("[BGM/Lyria] GEMINI_API_KEY 없음 -> local fallback")
            return None

        # 채널별 프롬프트 결정
        prompt_map = config.audio.lyria_prompt_map or {}
        prompt = prompt_map.get(channel, prompt_map.get("default", ""))
        if not prompt:
            prompt = "calm lo-fi beats with soft piano, minimal percussion, background music"

        bgm_path = run_dir / "bgm_lyria.mp3"
        if bgm_path.exists() and bgm_path.stat().st_size > 0:
            logger.info("[BGM/Lyria] 캐시 사용: %s", bgm_path.name)
            return bgm_path

        try:
            from shorts_maker_v2.providers.google_music_client import GoogleMusicClient

            client = GoogleMusicClient.from_env()
            # Lyria 생성: 영상 길이 + 2초 여유
            coro = client.generate_music_file(
                prompt=prompt,
                output_path=bgm_path,
                duration_sec=min(duration_sec + 2, 120),
                bpm=90,
                temperature=1.0,
            )
            try:
                asyncio.run(coro)
            except RuntimeError as exc:
                if "event loop" not in str(exc).lower() and "running" not in str(exc).lower():
                    raise
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(asyncio.run, coro)
                    future.result()

            if bgm_path.exists() and bgm_path.stat().st_size > 0:
                logger.info("[BGM/Lyria] 생성 완료: %s (%.1fs)", bgm_path.name, duration_sec)
                return bgm_path
        except Exception as exc:
            logger.warning("[BGM/Lyria] 생성 실패: %s -> local fallback", exc)

        return None

    # ── RMS ducking ───────────────────────────────────────────────────────────

    @staticmethod
    def _apply_rms_ducking(
        narration_audio: Any,
        bgm_clip: Any,
        *,
        base_vol: float = 0.12,
        duck_factor: float = 0.25,
        window_sec: float = 0.5,
    ) -> Any:
        """RMS 기반 Audio Ducking: 나레이션이 있는 구간에서 BGM 볼륨을 자동 감소.

        나레이션 RMS가 높은 구간 -> BGM 볼륨을 duck_factor로 감소
        나레이션이 없는 구간 -> BGM 볼륨을 base_vol 그대로 유지
        """
        try:
            nar_dur = narration_audio.duration
            if not nar_dur or nar_dur <= 0:
                return bgm_clip.with_effects([MultiplyVolume(base_vol)])

            # 나레이션 RMS 에너지를 window_sec 간격으로 샘플링
            fps = 44100
            nar_array = narration_audio.to_soundarray(fps=fps)
            if nar_array.ndim > 1:
                nar_array = nar_array.mean(axis=1)

            window_samples = int(window_sec * fps)
            n_windows = max(1, len(nar_array) // window_samples)

            rms_values = []
            for i in range(n_windows):
                chunk = nar_array[i * window_samples : (i + 1) * window_samples]
                rms = float(np.sqrt(float(np.mean(chunk**2))))
                rms_values.append(rms)

            # RMS 임계값: 평균의 30%를 기준으로 음성 구간 판별
            if not rms_values:
                return bgm_clip.with_effects([MultiplyVolume(base_vol)])

            rms_threshold = float(np.mean(rms_values)) * 0.3
            speech_count = sum(1 for r in rms_values if r > rms_threshold)

            # 음성 구간 비율로 전체 BGM 볼륨 결정 (chunk 분할 대신 간단한 접근)
            # 음성 비율이 높으면 전체적으로 낮은 볼륨, 낮으면 약간 높은 볼륨
            speech_ratio = speech_count / max(len(rms_values), 1)
            effective_vol = base_vol * (duck_factor + (1 - duck_factor) * (1 - speech_ratio))

            ducked = bgm_clip.with_effects([MultiplyVolume(effective_vol)])
            logger.info(
                "[BGM/Ducking] RMS ducking 적용: speech=%d/%d (%.0f%%), vol=%.2f",
                speech_count,
                len(rms_values),
                speech_ratio * 100,
                effective_vol,
            )
            return ducked
        except Exception as exc:
            logger.warning("[BGM/Ducking] RMS ducking 실패, 고정 볼륨 사용: %s", exc)
            return bgm_clip.with_effects([MultiplyVolume(base_vol)])

    # ── SFX 효과음 ──────────────────────────────────────────────────────────────

    # SFX 파일명 기반 역할 매칭 (파일명에 키워드 포함)
    _SFX_ROLE_KEYWORDS: dict[str, list[str]] = {
        "hook": ["whoosh", "impact", "hit", "boom", "hook"],
        "transition": ["swish", "swoosh", "transition", "sweep", "slide"],
        "cta": ["pop", "ding", "bell", "chime", "cta", "notification"],
    }

    def _load_sfx_files(self, run_dir: Path) -> dict[str, list[Path]]:
        """SFX 디렉토리에서 역할별 효과음 파일 로드."""
        config: AppConfig = self.config  # type: ignore[attr-defined]
        sfx_dir = (run_dir.parent.parent / config.audio.sfx_dir).resolve()
        if not sfx_dir.exists():
            return {}
        all_files = list(sfx_dir.glob("*.mp3")) + list(sfx_dir.glob("*.wav"))
        if not all_files:
            return {}
        categorized: dict[str, list[Path]] = {"hook": [], "transition": [], "cta": []}
        for f in all_files:
            stem = f.stem.lower()
            matched = False
            for role, keywords in self._SFX_ROLE_KEYWORDS.items():
                if any(kw in stem for kw in keywords):
                    categorized[role].append(f)
                    matched = True
                    break
            if not matched:
                categorized["transition"].append(f)
        return categorized

    def _build_sfx_clips(
        self,
        scene_roles: list[str],
        scene_durations: list[float],
        sfx_files: dict[str, list[Path]],
    ) -> list[Any]:
        """씬 역할/전환 시점에 SFX 오디오 클립 배치."""
        config: AppConfig = self.config  # type: ignore[attr-defined]
        sfx_clips: list[Any] = []
        volume = config.audio.sfx_volume
        cursor = 0.0
        for i, (role, dur) in enumerate(zip(scene_roles, scene_durations, strict=False)):
            # Hook 씬 시작에 임팩트 SFX
            if role == "hook" and sfx_files.get("hook"):
                sfx_path = random.choice(sfx_files["hook"])
                clip = self._load_audio_clip(sfx_path)  # type: ignore[attr-defined]
                clip = clip.with_effects([MultiplyVolume(volume)])
                sfx_clips.append(clip.with_start(cursor))
            # CTA 씬 시작에 팝 SFX
            elif role == "cta" and sfx_files.get("cta"):
                sfx_path = random.choice(sfx_files["cta"])
                clip = self._load_audio_clip(sfx_path)  # type: ignore[attr-defined]
                clip = clip.with_effects([MultiplyVolume(volume)])
                sfx_clips.append(clip.with_start(cursor))
            # Closing 씬: SFX 없음 (조용한 여운)
            # 씬 전환 시점에 스위시 SFX (마지막 씬 제외)
            if i < len(scene_roles) - 1 and sfx_files.get("transition"):
                sfx_path = random.choice(sfx_files["transition"])
                clip = self._load_audio_clip(sfx_path)  # type: ignore[attr-defined]
                clip = clip.with_effects([MultiplyVolume(volume)])
                transition_t = max(0, cursor + dur - 0.15)
                sfx_clips.append(clip.with_start(transition_t))
            cursor += dur
        return sfx_clips
