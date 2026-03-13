"""Generate thumbnail image using Gemini (free), Pollinations.ai (free), or OpenAI DALL-E 3."""

import asyncio
import logging
import os
import tempfile
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)

# Gemini image generation models (priority order: primary → fallback)
# gemini-2.5-flash-image (Nano Banana): speed/efficiency optimized, 1024px, free tier
# gemini-3.1-flash-image-preview (Nano Banana 2): best all-around, preview
_GEMINI_IMAGE_MODELS = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image-preview",
]

# ── P2-A3: 토픽별 이미지 스타일 매핑 ────────────────────────────────
_TOPIC_IMAGE_STYLES: dict[str, dict[str, str]] = {
    "연봉": {"style": "modern infographic", "mood": "professional, clean", "colors": "blue and gold"},
    "이직": {"style": "dramatic illustration", "mood": "decisive, hopeful", "colors": "teal and orange"},
    "회사문화": {"style": "corporate cartoon", "mood": "satirical, relatable", "colors": "gray and yellow"},
    "상사": {"style": "editorial illustration", "mood": "tense, dramatic", "colors": "red and dark gray"},
    "복지": {"style": "warm illustration", "mood": "cozy, positive", "colors": "green and warm white"},
    "연애": {"style": "soft watercolor", "mood": "romantic, warm", "colors": "pink and soft purple"},
    "결혼": {"style": "elegant illustration", "mood": "ceremonial, emotional", "colors": "gold and ivory"},
    "가족": {"style": "warm sketch", "mood": "nostalgic, tender", "colors": "warm brown and soft orange"},
    "재테크": {"style": "data visualization art", "mood": "sharp, analytical", "colors": "green and dark blue"},
    "직장개그": {"style": "meme-style cartoon", "mood": "funny, exaggerated", "colors": "bright yellow and comic blue"},
    "부동산": {"style": "architectural illustration", "mood": "urban, realistic", "colors": "concrete gray and sky blue"},
    "IT": {"style": "tech-futuristic", "mood": "innovative, sleek", "colors": "neon blue and dark background"},
    "건강": {"style": "fitness illustration", "mood": "energetic, fresh", "colors": "green and white"},
    "정치": {"style": "newspaper editorial", "mood": "serious, neutral", "colors": "black, white, and red accent"},
    "자기계발": {"style": "motivational poster", "mood": "inspiring, ambitious", "colors": "sunrise orange and navy"},
}
_DEFAULT_IMAGE_STYLE = {"style": "modern illustration", "mood": "professional, relatable", "colors": "neutral tones"}

# ── 블라인드 전용: 애니/삽화/Pixar 3D 캐릭터 스타일 ──────────────────
_BLIND_ANIME_STYLE = {
    "base": "Pixar-style 3D animated illustration",
    "character": "cute expressive Korean office worker character with big eyes",
    "quality": "cinematic lighting, warm color grading, soft shadows, bokeh background",
    "constraints": "no text overlay, no watermark, no speech bubbles, 16:9 aspect ratio",
}

# 감정별 분위기 오버라이드
_EMOTION_MOOD_OVERRIDE: dict[str, str] = {
    "분노": "intense, frustrated",
    "허탈": "empty, melancholic",
    "경악": "shocking, dramatic",
    "웃김": "humorous, lighthearted",
    "자부심": "proud, triumphant",
    "불안": "anxious, uncertain",
    "기대감": "excited, hopeful",
}


def _env_flag(name: str):
    raw = os.environ.get(name)
    if raw is None:
        return None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class ImageGenerator:
    """Multi-provider image generator with free-first fallback."""

    def __init__(self, config, cost_tracker=None):
        self.config = config
        self.cost_tracker = cost_tracker

        # Provider priority: "gemini" (free) > "pollinations" (free) > "dalle" ($0.04/image)
        self.provider = config.get("image.provider", "gemini")
        self.enabled = True
        self.client = None
        self._gemini_client = None

        # Gemini setup (free, uses existing GOOGLE_API_KEY)
        if self.provider == "gemini":
            google_key = os.environ.get("GOOGLE_API_KEY") or config.get("gemini.api_key")
            if google_key:
                try:
                    from google import genai
                    self._gemini_client = genai.Client(api_key=google_key)
                    logger.info("Image provider: gemini (free)")
                except ImportError:
                    logger.warning("google-genai not installed. Falling back to pollinations.")
                    self.provider = "pollinations"
            else:
                logger.info("GOOGLE_API_KEY missing. Falling back to pollinations.")
                self.provider = "pollinations"

        # Pollinations setup (free, no API key needed)
        if self.provider == "pollinations":
            logger.info("Image provider: pollinations (free)")

        # DALL-E setup (paid)
        if self.provider == "dalle":
            api_key = config.get("openai.api_key")
            env_api_key = os.environ.get("OPENAI_API_KEY")
            self.api_key = env_api_key or api_key
            self.model = config.get("openai.image_model", "dall-e-3")

            env_enabled = _env_flag("OPENAI_IMAGE_ENABLED")
            openai_enabled = env_enabled if env_enabled is not None else config.get("openai.enabled", False)

            if openai_enabled and self.api_key:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
                logger.info("Image provider: dalle (paid)")
            else:
                logger.info("DALL-E unavailable. Falling back to pollinations (free).")
                self.provider = "pollinations"

    # ── P2-A3: 토픽 기반 이미지 프롬프트 자동 빌드 ────────────────────
    @staticmethod
    def build_image_prompt(
        topic_cluster: str = "",
        emotion_axis: str = "",
        title: str = "",
        draft_text: str = "",
        variant: str = "default",
        source: str = "",
    ) -> str:
        """토픽/감정/제목 기반으로 이미지 생성 프롬프트 자동 구성 (P2-A3).

        Args:
            topic_cluster: 콘텐츠 토픽 클러스터.
            emotion_axis: 감정 축.
            title: 원본 게시글 제목.
            draft_text: 트윗 초안 텍스트.
            variant: "default" | "alt_style" | "alt_mood" (A/B 테스트용).
            source: 콘텐츠 출처 ("blind", "ppomppu", "fmkorea" 등).

        Returns:
            영문 이미지 생성 프롬프트.
        """
        # [QA 수정 #5] source가 None으로 들어올 경우 방어
        # [QA 수정 #6] 기존 호출처(source 미전달)는 기본값 ""으로 기존 로직 실행
        _source = (source or "").lower().strip()

        # ── 블라인드 전용: 애니/삽화/Pixar 3D 스타일 ────────────────────
        if _source in {"blind", "블라인드"}:
            return ImageGenerator._build_blind_anime_prompt(
                topic_cluster, emotion_axis, title, draft_text
            )

        # ── 기존 로직: 뽐뿌/에펨 등 (실제로는 호출되지 않아야 함) ──────
        style_info = _TOPIC_IMAGE_STYLES.get(topic_cluster, _DEFAULT_IMAGE_STYLE)
        style = style_info["style"]
        mood = style_info["mood"]
        colors = style_info["colors"]

        # 감정별 분위기 오버라이드
        if emotion_axis and emotion_axis in _EMOTION_MOOD_OVERRIDE:
            mood = _EMOTION_MOOD_OVERRIDE[emotion_axis]

        # A/B 테스트 우수 가중치 최우선 반영
        try:
            from pipeline.ab_feedback_loop import ABFeedbackLoop
            tuned = ABFeedbackLoop.load_tuned_styles()
            if topic_cluster in tuned:
                if "mood" in tuned[topic_cluster]:
                    mood = tuned[topic_cluster]["mood"]
                if "style" in tuned[topic_cluster]:
                    style = tuned[topic_cluster]["style"]
        except Exception:
            pass

        # 콘텐츠 요약 (제목 우선, 없으면 초안에서 추출)
        subject_hint = ""
        if title:
            subject_hint = title[:30].strip()
        elif draft_text:
            subject_hint = draft_text[:50].strip()

        # 프롬프트 조합 (March 1st preferred style)
        if subject_hint:
            return f"A {style} about Korean office workers related to '{subject_hint}' with {mood} mood using {colors} color palette, no text overlay, no watermark, high quality, 16:9 aspect ratio"
        else:
            return f"A {style} about Korean office workers with {mood} mood using {colors} color palette, no text overlay, no watermark, high quality, 16:9 aspect ratio"

    @staticmethod
    def _build_blind_anime_prompt(
        topic_cluster: str = "",
        emotion_axis: str = "",
        title: str = "",
        draft_text: str = "",
    ) -> str:
        """블라인드 전용: Pixar/애니메이션 삽화 스타일 프롬프트 생성.

        공감 유도를 위해 귀엽고 표정이 풍부한 3D 캐릭터가
        직장 상황을 연출하는 일러스트를 생성합니다.
        """
        base = _BLIND_ANIME_STYLE["base"]
        character = _BLIND_ANIME_STYLE["character"]
        quality = _BLIND_ANIME_STYLE["quality"]
        constraints = _BLIND_ANIME_STYLE["constraints"]

        # 토픽별 장면 설정
        _TOPIC_SCENES: dict[str, str] = {
            "연봉": "looking at paycheck with coins and bills floating around in a modern office",
            "이직": "standing at a crossroads between two office buildings, holding a resignation letter",
            "회사문화": "sitting at desk surrounded by coworkers in a hectic open office",
            "상사": "nervously facing a stern boss figure in a meeting room",
            "복지": "happily enjoying company perks like coffee and snacks in a bright break room",
            "연애": "daydreaming at desk with heart-shaped thought bubbles",
            "결혼": "juggling wedding ring and work laptop with a conflicted expression",
            "가족": "looking at a family photo on desk with a warm but tired smile",
            "재테크": "surrounded by stock charts and piggy banks with an analytical expression",
            "직장개그": "making a funny face while coworkers laugh in background",
            "부동산": "staring wide-eyed at a tiny apartment model next to towering price tags",
            "IT": "coding at a futuristic workstation with multiple holographic screens",
            "건강": "stretching at desk with a water bottle, looking refreshed",
            "정치": "reading news on phone with a surprised expression in office cafeteria",
            "자기계발": "studying late at night at desk with determination in eyes",
        }
        default_scene = "sitting at an office desk with a relatable everyday expression"
        scene = _TOPIC_SCENES.get(topic_cluster, default_scene)

        # 감정별 표정 설정
        _EMOTION_EXPRESSIONS: dict[str, str] = {
            "분노": "frustrated and angry expression with clenched fists",
            "허탈": "empty hollow stare with drooping shoulders",
            "경악": "shocked wide-eyed expression with jaw dropped",
            "웃김": "laughing out loud with tears of joy",
            "자부심": "proud confident smile with chest puffed out",
            "불안": "nervous fidgeting with worried eyes",
            "기대감": "excited sparkling eyes with hopeful smile",
            "공감": "empathetic nodding with understanding eyes",
        }
        expression = _EMOTION_EXPRESSIONS.get(emotion_axis, "expressive and relatable")

        # 제목에서 키워드 힌트
        subject_hint = ""
        if title:
            subject_hint = f" related to '{title[:30].strip()}'"
        elif draft_text:
            subject_hint = f" related to '{draft_text[:40].strip()}'"

        return (
            f"{base} of a {character}, {scene}{subject_hint}, "
            f"showing {expression}, "
            f"{quality}, {constraints}"
        )

    async def generate_image(self, prompt: str, topic_cluster: str = "", emotion_axis: str = "") -> str | None:
        """Generate an image from a prompt. Returns a temp file path or URL.

        Uses ImageCache to avoid duplicate generation for the same topic+emotion pair.
        """
        if not prompt:
            logger.warning("Empty prompt provided for image generation.")
            return None

        # 프롬프트 품질 검증: 5단어 미만이면 저품질 이미지 → 스킵
        if len(prompt.strip().split()) < 5:
            logger.warning("Image prompt too short (%d words), skipping.", len(prompt.strip().split()))
            return None

        # ── ImageCache 조회 ───────────────────────────────────────────
        _cache = None
        if topic_cluster:
            try:
                from pipeline.image_cache import ImageCache
                _cache = ImageCache()
                cached = _cache.get(topic_cluster, emotion_axis)
                if cached:
                    return cached
            except Exception as exc:
                logger.debug("ImageCache lookup failed (ignored): %s", exc)

        result = None
        provider_used = self.provider
        if self.provider == "gemini":
            result = await self._generate_gemini(prompt)
            if result is None:
                logger.info("Gemini image failed, falling back to Pollinations...")
                result = await self._generate_pollinations(prompt)
                provider_used = "pollinations"
        elif self.provider == "pollinations":
            result = await self._generate_pollinations(prompt)
        else:
            result = await self._generate_dalle(prompt)
            provider_used = "dalle"

        # ── ImageCache 저장 ───────────────────────────────────────────
        if result and _cache and topic_cluster:
            try:
                _cache.set(topic_cluster, emotion_axis, result, provider=provider_used)
            except Exception:
                pass

        return result

    async def _generate_gemini(self, prompt: str) -> str | None:
        """Generate image via Gemini (free, uses GOOGLE_API_KEY).

        Tries each model in _GEMINI_IMAGE_MODELS in order.
        Falls through to Pollinations if all models fail.
        """
        if not self._gemini_client:
            return None

        from google.genai import types

        for model_name in _GEMINI_IMAGE_MODELS:
            logger.info("Generating image via Gemini [%s]... Prompt: %s...", model_name, prompt[:50])
            try:
                response = await asyncio.to_thread(
                    self._gemini_client.models.generate_content,
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                )

                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_data = part.inline_data.data
                        if len(image_data) < 1000:
                            logger.error("Gemini [%s] returned too-small image (%d bytes)", model_name, len(image_data))
                            break  # try next model

                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                            f.write(image_data)
                            temp_path = f.name

                        logger.info("Successfully generated image via Gemini [%s] (%d bytes)", model_name, len(image_data))
                        return temp_path

                logger.warning("Gemini [%s] response contained no image data.", model_name)
            except Exception as e:
                logger.warning("Gemini [%s] failed: %s. Trying next model...", model_name, e)

        logger.error("All Gemini models failed for image generation.")
        return None

    async def _generate_pollinations(self, prompt: str) -> str | None:
        """Generate image via Pollinations.ai (free, no API key needed)."""
        encoded = quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}"
        params = {"model": "flux", "width": "1024", "height": "1024", "nologo": "true"}

        logger.info("Generating image via Pollinations (free)... Prompt: %s...", prompt[:50])

        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        logger.error("Pollinations API error: HTTP %d", resp.status)
                        return None
                    image_data = await resp.read()
                    if len(image_data) < 1000:
                        logger.error("Pollinations returned too-small image (%d bytes)", len(image_data))
                        return None

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                        f.write(image_data)
                        temp_path = f.name

                    logger.info("Successfully generated image via Pollinations (%d bytes)", len(image_data))
                    return temp_path
        except Exception as e:
            logger.exception("Pollinations image generation failed: %s", e)
            return None

    async def _generate_dalle(self, prompt: str) -> str | None:
        """Generate image via OpenAI DALL-E 3."""
        if not self.client:
            logger.error("OpenAI API key is missing. Image generation skipped.")
            return None

        logger.info("Generating image with DALL-E 3... Prompt: %s...", prompt[:50])

        last_err = None
        for attempt in range(1, 4):
            try:
                response = await self.client.images.generate(
                    model=self.model,
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                image_url = response.data[0].url
                logger.info("Successfully generated thumbnail image")
                if self.cost_tracker:
                    self.cost_tracker.add_dalle_cost()
                return image_url
            except Exception as e:
                last_err = e
                is_rate_limit = "rate" in str(e).lower() or "429" in str(e)
                wait = min(2**attempt, 60) if is_rate_limit else 2
                if attempt < 3:
                    logger.warning("Image generation attempt %d/3 failed: %s. Retrying in %ds...", attempt, e, wait)
                    await asyncio.sleep(wait)

        logger.error("Failed to generate image after 3 attempts: %s", last_err, exc_info=last_err)
        return None
