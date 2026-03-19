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
    "constraints": "absolutely no text, no letters, no numbers, no words, no captions, no watermark, no speech bubbles, no signs with writing, clean image only, 16:9 aspect ratio",
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

# ── 시멘틱 씬 매핑: 토픽×감정 교차 조합별 구체적 장면 사전 ─────────────
# 형식: _SEMANTIC_SCENES[(topic, emotion)] → 영문 장면 설명
# 호출순서:
#   1. (topic, emotion) 정확 매칭 → 최적 장면
#   2. fallback: 토픽 기본 장면 (_TOPIC_SCENES)
_SEMANTIC_SCENES: dict[tuple[str, str], str] = {
    # ── 연봉 ────────────────────────────────────────────────────────
    ("연봉", "분노"): "office worker angrily staring at a tiny paycheck stub while coworkers celebrate bonuses in the background",
    ("연봉", "허탈"): "office worker staring blankly at empty wallet at a dimly lit desk with scattered bills",
    ("연봉", "경악"): "office worker jaw dropped reading a shockingly low salary offer letter on screen",
    ("연봉", "웃김"): "office worker laughing nervously comparing tiny paycheck to enormous coffee shop receipt",
    ("연봉", "공감"): "two office workers sharing sympathetic looks over lunch comparing their pay stubs",
    ("연봉", "자부심"): "confident office worker proudly holding a glowing paycheck with coins floating around",
    ("연봉", "현타"): "exhausted office worker calculating monthly expenses at desk late at night",
    # ── 이직 ────────────────────────────────────────────────────────
    ("이직", "분노"): "frustrated worker slamming resignation letter on boss's desk in a heated office",
    ("이직", "허탈"): "worker standing alone in empty office corridor holding a cardboard box of belongings",
    ("이직", "경악"): "shocked worker receiving unexpected job offer call while at current boring desk",
    ("이직", "웃김"): "worker doing a secret happy dance in bathroom stall after getting a new job offer",
    ("이직", "공감"): "two workers whispering about quitting over coffee in break room",
    ("이직", "기대감"): "worker confidently walking toward a bright glowing door leaving dark cubicle behind",
    ("이직", "불안"): "nervous worker standing at crossroads between two office buildings in foggy weather",
    # ── 회사문화 ──────────────────────────────────────────────────────
    ("회사문화", "분노"): "angry workers in overcrowded open office with noise and chaos everywhere",
    ("회사문화", "허탈"): "lone worker sitting in massive empty meeting room after pointless two-hour meeting",
    ("회사문화", "경악"): "worker staring at absurd company memo posted on bulletin board in disbelief",
    ("회사문화", "웃김"): "workers secretly playing games on phones during mandatory team-building exercise",
    ("회사문화", "공감"): "tired workers nodding knowingly at each other during boring company announcement",
    # ── 상사 ────────────────────────────────────────────────────────
    ("상사", "분노"): "worker clenching fists under desk while stern boss lectures in meeting room",
    ("상사", "허탈"): "deflated worker leaving boss's office after unfair performance review",
    ("상사", "경악"): "worker shocked seeing boss take credit for their work on presentation screen",
    ("상사", "웃김"): "boss accidentally sending embarrassing message to entire company chat",
    ("상사", "공감"): "group of workers sharing eye rolls behind demanding boss during meeting",
    # ── 복지 ────────────────────────────────────────────────────────
    ("복지", "분노"): "worker reading email about benefit cuts while standing by vending machine",
    ("복지", "웃김"): "overjoyed worker discovering unexpected company snack bar stocked with premium treats",
    ("복지", "공감"): "workers happily enjoying cozy bean bags and coffee in modern break room",
    ("복지", "자부심"): "worker touring friends through amazing company facilities with proud smile",
    ("복지", "기대감"): "excited worker reading about new remote work policy announcement on laptop",
    # ── 연애 ────────────────────────────────────────────────────────
    ("연애", "공감"): "young professional daydreaming at desk with romantic sunset through office window",
    ("연애", "웃김"): "awkward blind date scene at trendy cafe with both people nervously checking phones",
    ("연애", "허탈"): "lonely worker eating convenience store dinner alone looking at couples outside",
    ("연애", "기대감"): "worker excitedly getting ready for date checking outfit in office bathroom mirror",
    # ── 결혼 ────────────────────────────────────────────────────────
    ("결혼", "분노"): "couple arguing over wedding budget spreadsheet at kitchen table with calculator",
    ("결혼", "허탈"): "exhausted newlywed looking at empty bank account after wedding expenses",
    ("결혼", "공감"): "young couple juggling wedding planning folder and work laptop with tired smiles",
    ("결혼", "기대감"): "happy couple looking at wedding venue brochure with sparkling eyes",
    # ── 가족 ────────────────────────────────────────────────────────
    ("가족", "공감"): "tired parent working laptop at kitchen table with sleeping child on shoulder",
    ("가족", "허탈"): "parent looking at family photo on desk while working late in empty office",
    ("가족", "웃김"): "parent receiving chaotic video call from kids while in important virtual meeting",
    ("가족", "자부심"): "proud parent hanging child's drawing on office cubicle wall with warm smile",
    # ── 재테크 ──────────────────────────────────────────────────────
    ("재테크", "분노"): "frustrated investor seeing red stock chart plummeting on multiple screens",
    ("재테크", "경악"): "shocked worker staring at crypto chart that crashed overnight on phone",
    ("재테크", "웃김"): "worker secretly checking stock app under desk during meeting and doing victory gesture",
    ("재테크", "공감"): "workers huddled at lunch discussing investment tips over kimbap",
    ("재테크", "불안"): "nervous investor refreshing portfolio app at 3am in dark room",
    # ── 직장개그 ──────────────────────────────────────────────────────
    ("직장개그", "웃김"): "exaggerated funny office scene with worker's chair rolling away during presentation",
    ("직장개그", "공감"): "worker nodding off in meeting and suddenly jerking awake in front of everyone",
    ("직장개그", "경악"): "worker accidentally sending personal message to company-wide group chat",
    # ── 부동산 ──────────────────────────────────────────────────────
    ("부동산", "분노"): "frustrated young worker looking at impossibly high apartment price tags in window",
    ("부동산", "허탈"): "couple staring hopelessly at apartment price comparison on giant screen",
    ("부동산", "경악"): "shocked worker reading rent increase notice letter with jaw dropped",
    ("부동산", "기대감"): "excited couple touring dream apartment with sunlight streaming through windows",
    # ── IT ──────────────────────────────────────────────────────────
    ("IT", "분노"): "developer angrily staring at error-filled code on multiple monitors at 2am",
    ("IT", "웃김"): "developer celebrating a single line of code working after hours of debugging",
    ("IT", "허탈"): "developer realizing Friday deploy broke everything with loading spinner of doom",
    ("IT", "공감"): "developers sharing knowing look during impossible deadline meeting",
    # ── 건강 ────────────────────────────────────────────────────────
    ("건강", "공감"): "office workers stretching together at desks during break time",
    ("건강", "현타"): "exhausted worker rubbing neck pain while staring at computer screen",
    ("건강", "기대감"): "energetic worker going for morning jog before heading to office",
    # ── 자기계발 ──────────────────────────────────────────────────────
    ("자기계발", "공감"): "worker studying online course on laptop at cafe after work hours",
    ("자기계발", "자부심"): "worker proudly displaying certificate on desk with determination in eyes",
    ("자기계발", "기대감"): "worker starting fresh morning routine with books and coffee at sunrise",
    ("자기계발", "현타"): "worker exhausted falling asleep on study materials late at night",
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

        # ── 커뮤니티별 시맨틱 씬 (비블라인드 소스) ────────────────────
        _COMMUNITY_SCENES: dict[str, dict[str, str]] = {
            "ppomppu": {
                "base": "playful shopping illustration",
                "scene": "animated character excitedly discovering an amazing deal on a phone screen with sale tags floating around",
                "mood": "energetic, bargain-hunting",
            },
            "뽐뿌": {
                "base": "playful shopping illustration",
                "scene": "animated character excitedly discovering an amazing deal on a phone screen with sale tags floating around",
                "mood": "energetic, bargain-hunting",
            },
            "fmkorea": {
                "base": "internet culture cartoon",
                "scene": "animated character scrolling through a chaotic online forum with memes and reactions floating around",
                "mood": "humorous, internet-savvy, meme-like",
            },
            "에펨코리아": {
                "base": "internet culture cartoon",
                "scene": "animated character scrolling through a chaotic online forum with memes and reactions floating around",
                "mood": "humorous, internet-savvy, meme-like",
            },
            "jobplanet": {
                "base": "corporate review infographic illustration",
                "scene": "animated character analyzing a company review dashboard with star ratings and charts",
                "mood": "analytical, data-driven",
            },
            "잡플래닛": {
                "base": "corporate review infographic illustration",
                "scene": "animated character analyzing a company review dashboard with star ratings and charts",
                "mood": "analytical, data-driven",
            },
        }
        _NO_TEXT = "absolutely no text, no letters, no numbers, no words, no captions, no writing of any kind, no watermark, clean image only"

        if _source in _COMMUNITY_SCENES:
            comm = _COMMUNITY_SCENES[_source]
            emotion_mood = _EMOTION_MOOD_OVERRIDE.get(emotion_axis, comm["mood"])
            return f"{comm['base']}, {comm['scene']}, {emotion_mood} mood, {_NO_TEXT}, high quality, 16:9 aspect ratio"

        # ── 기존 로직: 소스 미지정 or 기타 ──────────────────────────────
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

        # 프롬프트 조합 — 한글 제목/초안 텍스트는 프롬프트에 포함하지 않음
        # (한글 텍스트가 이미지에 오타로 렌더링되는 문제 방지)
        _NO_TEXT = "absolutely no text, no letters, no numbers, no words, no captions, no writing of any kind, no watermark, clean image only"
        return f"A {style} about Korean office workers with {mood} mood using {colors} color palette, {_NO_TEXT}, high quality, 16:9 aspect ratio"

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

        시멘틱 씬 매핑 적용:
          1순위: _SEMANTIC_SCENES[(topic, emotion)] — 토픽×감정 교차 매핑
          2순위: _TOPIC_SCENES[topic] — 토픽 기본 장면
          3순위: default_scene — 범용 직장 장면
        """
        base = _BLIND_ANIME_STYLE["base"]
        character = _BLIND_ANIME_STYLE["character"]
        quality = _BLIND_ANIME_STYLE["quality"]
        constraints = _BLIND_ANIME_STYLE["constraints"]

        # 토픽별 기본 장면 설정 (시멘틱 씬 매핑의 fallback)
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

        # 시멘틱 씬 매핑: (토픽, 감정) 교차 조합 우선 → 토픽 기본 → 범용
        semantic_key = (topic_cluster, emotion_axis)
        if semantic_key in _SEMANTIC_SCENES:
            scene = _SEMANTIC_SCENES[semantic_key]
            logger.debug("Semantic scene matched: %s → %s", semantic_key, scene[:60])
        else:
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
            "현타": "exhausted empty eyes staring into space",
        }
        expression = _EMOTION_EXPRESSIONS.get(emotion_axis, "expressive and relatable")

        # 한글 제목/초안 텍스트는 프롬프트에 포함하지 않음
        # (한글 텍스트가 이미지에 오타로 렌더링되는 문제 방지)
        # 시멘틱 씬 매핑 + 감정 표정으로 장면을 직관적으로 구성

        return (
            f"{base} of a {character}, {scene}, "
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

        # ── PIL 기반 이미지 품질 검증 ──────────────────────────────────
        if result and os.path.exists(result):
            valid, reason = self._validate_image(result)
            if not valid:
                logger.warning("Image quality check failed (%s): %s", reason, result)
                # 1회 재시도: 프롬프트 보강
                retry_result = None
                retry_prompt = prompt + ", highly detailed, photorealistic quality, vivid colors"
                if provider_used == "gemini":
                    retry_result = await self._generate_gemini(retry_prompt)
                elif provider_used == "pollinations":
                    retry_result = await self._generate_pollinations(retry_prompt)
                if retry_result and os.path.exists(retry_result):
                    valid2, _ = self._validate_image(retry_result)
                    if valid2:
                        result = retry_result
                        logger.info("Image retry succeeded after quality check failure")

        # ── ImageCache 저장 ───────────────────────────────────────────
        if result and _cache and topic_cluster:
            try:
                _cache.set(topic_cluster, emotion_axis, result, provider=provider_used)
            except Exception:
                pass

        return result

    @staticmethod
    def _validate_image(path: str) -> tuple[bool, str]:
        """PIL로 이미지 품질을 검증합니다.

        Returns:
            (True, "") if 통과
            (False, "이유") if 실패
        """
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            return True, ""  # PIL 없으면 무조건 통과

        try:
            with Image.open(path) as img:
                width, height = img.size
                if width < 256 or height < 256:
                    return False, f"too_small ({width}x{height})"

                # RGB 변환 후 분산 체크 (거의 단색인지)
                rgb = img.convert("RGB")
                arr = np.array(rgb)
                variance = float(arr.var())
                if variance < 100.0:
                    return False, f"too_uniform (variance={variance:.0f})"

            return True, ""
        except Exception as exc:
            return False, f"open_failed ({exc})"

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
