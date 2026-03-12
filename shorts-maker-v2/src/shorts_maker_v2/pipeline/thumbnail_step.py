"""
썸네일 생성 단계.
mode에 따라 Pillow(직접 생성), DALL-E/Gemini(AI 생성), Canva(레거시) 중 선택.
실패 시 None 반환 (파이프라인 계속 진행).

Sprint 4 개선:
- 채널별 AI 썸네일 프롬프트 템플릿 (5채널 × 고유 비주얼 아이덴티티)
- Gemini Imagen 무료 모드 지원
- channel_key 기반 자동 스타일 분기
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from shorts_maker_v2.config import CanvaSettings, ThumbnailSettings

if TYPE_CHECKING:
    from shorts_maker_v2.providers.openai_client import OpenAIClient
    from shorts_maker_v2.providers.google_client import GoogleClient

logger = logging.getLogger(__name__)

POLL_INTERVAL = 2
POLL_TIMEOUT = 120
API_BASE = "https://api.canva.com/rest/v1"
TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"

# ── 채널별 AI 썸네일 프롬프트 템플릿 ─────────────────────────────────────────
# {title}: 영상 제목, {topic}: 주제 키워드로 치환됩니다.
# 모든 프롬프트는 텍스트 없이 비주얼만 생성하도록 "No text" 지시 포함.

_CHANNEL_THUMB_PROMPTS: dict[str, str] = {
    "ai_tech": (
        "YouTube Shorts thumbnail for topic: {topic}. "
        "Neon cyberpunk aesthetic, dark background with glowing blue and purple elements, "
        "holographic HUD overlay, futuristic tech circuits, dramatic rim lighting, "
        "high contrast, cinematic composition. No text, no letters, no words."
    ),
    "psychology": (
        "YouTube Shorts thumbnail for topic: {topic}. "
        "Soft watercolor illustration style, warm pastel colors (amber, beige, soft pink), "
        "gentle bokeh background, emotional human silhouette, cozy atmospheric lighting, "
        "dreamy soft focus, therapeutic calm mood. No text, no letters, no words."
    ),
    "history": (
        "YouTube Shorts thumbnail for topic: {topic}. "
        "Vintage parchment texture, aged sepia tones, dramatic chiaroscuro lighting, "
        "historical painting composition, archaeological discovery atmosphere, "
        "cinematic wide angle, epic documentary feel, film grain. No text, no letters, no words."
    ),
    "space": (
        "YouTube Shorts thumbnail for topic: {topic}. "
        "Ultra-realistic space photography, cosmic nebula with vivid colors, "
        "Hubble telescope style, deep space 8K HDR, dramatic planetary close-up, "
        "volumetric light rays, awe-inspiring scale, epic composition. No text, no letters, no words."
    ),
    "health": (
        "YouTube Shorts thumbnail for topic: {topic}. "
        "Clean modern medical infographic style, professional blue and green tones, "
        "healthy lifestyle photography, bright natural light, simple abstract shapes, "
        "fresh vibrant colors, trustworthy professional atmosphere. No text, no letters, no words. "
        "No medical tools, no blood, no surgery, no anatomy."
    ),
}

_DEFAULT_THUMB_PROMPT = (
    "YouTube Shorts thumbnail, topic: {topic}. "
    "Cinematic dramatic lighting, dark atmospheric background, "
    "high contrast, visually striking, professional. No text, no letters, no words."
)

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


# ── Canva 헬퍼 (레거시) ───────────────────────────────────────────────────────

def _load_token(token_file: Path) -> dict:
    if not token_file.exists():
        raise FileNotFoundError(f"Canva 토큰 없음: {token_file}")
    return json.loads(token_file.read_text(encoding="utf-8"))


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _refresh_access_token(token_file: Path) -> str:
    """refresh_token으로 새 access_token 발급 후 파일 갱신."""
    from dotenv import load_dotenv
    sibling_env = token_file.parent / ".env"
    if sibling_env.exists():
        load_dotenv(sibling_env, override=False)

    client_id = os.getenv("CANVA_CLIENT_ID", "")
    client_secret = os.getenv("CANVA_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError("CANVA_CLIENT_ID / CANVA_CLIENT_SECRET 환경변수가 없어 토큰 갱신 불가")

    token_data = _load_token(token_file)
    refresh_token = token_data.get("refresh_token", "")
    if not refresh_token:
        raise RuntimeError("refresh_token 없음 — canva_auth.py를 다시 실행하세요")

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    new_data = resp.json()
    token_data["access_token"] = new_data["access_token"]
    if "refresh_token" in new_data:
        token_data["refresh_token"] = new_data["refresh_token"]
    token_file.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    print("[Canva] 액세스 토큰 자동 갱신 완료")
    return new_data["access_token"]


def _get_access_token(token_file: Path) -> str:
    token_data = _load_token(token_file)
    return token_data["access_token"]


def _poll(url: str, token: str, timeout: int = POLL_TIMEOUT) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(url, headers=_headers(token), timeout=30)
        resp.raise_for_status()
        job = resp.json().get("job", {})
        status = job.get("status")
        if status == "success":
            return job
        if status == "failed":
            raise RuntimeError(f"Canva 작업 실패: {job}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Canva 작업 타임아웃 ({timeout}s)")


def _export_design(design_id: str, token: str) -> str:
    resp = requests.post(
        f"{API_BASE}/exports",
        headers=_headers(token),
        json={"design_id": design_id, "format": {"type": "png"}},
        timeout=30,
    )
    resp.raise_for_status()
    export_id = resp.json()["job"]["id"]
    job = _poll(f"{API_BASE}/exports/{export_id}", token)
    return job["urls"][0]


def _http_download(url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(requests.get(url, timeout=60).content)
    return output_path


def _sanitize_title(title: str) -> str:
    """cp949 비호환 Unicode 특수문자를 안전한 대체 문자로 치환."""
    return (
        title
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2026", "...")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def _overlay_title(base_png: Path, title: str, output_path: Path) -> Path:
    from PIL import Image, ImageDraw

    img = Image.open(base_png).convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_h = int(h * 0.18)
    draw.rectangle([(0, h - bar_h), (w, h)], fill=(0, 0, 0, 160))

    font_size = max(36, int(h * 0.055))
    font = _load_font_for_thumb(font_size)

    bbox = draw.textbbox((0, 0), title, font=font)
    tx = (w - (bbox[2] - bbox[0])) // 2
    ty = h - bar_h + (bar_h - (bbox[3] - bbox[1])) // 2

    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.text((tx + dx, ty + dy), title, font=font, fill=(0, 0, 0, 255))
    draw.text((tx, ty), title, font=font, fill=(255, 255, 255, 255))

    result = Image.alpha_composite(img, overlay).convert("RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(str(output_path), "PNG")
    return output_path


# ── Pillow 썸네일 생성 ────────────────────────────────────────────────────────

def _load_font_for_thumb(size: int):
    from PIL import ImageFont
    for fp in _FONT_CANDIDATES:
        p = Path(fp)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap_text(text: str, font, draw, max_width: int) -> list[str]:
    """텍스트를 max_width에 맞게 자동 줄바꿈."""
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _generate_pillow_thumbnail(title: str, output_path: Path) -> Path:
    """
    Pillow로 1080×1920 Shorts 썸네일 직접 생성.
    다크 그라데이션 배경 + 굵은 제목 텍스트 + 골드 액센트 라인.
    """
    from PIL import Image, ImageDraw

    W, H = 1080, 1920
    GOLD = (255, 215, 0)
    TOP_COLOR = (13, 13, 30)
    BOT_COLOR = (20, 8, 58)

    # 1. 그라데이션 배경
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(TOP_COLOR[0] * (1 - t) + BOT_COLOR[0] * t)
        g = int(TOP_COLOR[1] * (1 - t) + BOT_COLOR[1] * t)
        b = int(TOP_COLOR[2] * (1 - t) + BOT_COLOR[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 2. 골드 액센트 라인 (상/하)
    draw.rectangle([(0, 0), (W, 8)], fill=GOLD)
    draw.rectangle([(0, H - 8), (W, H)], fill=GOLD)

    # 3. 제목 폰트 (90px)
    font = _load_font_for_thumb(90)
    title_clean = _sanitize_title(title)
    margin = 80
    lines = _wrap_text(title_clean, font, draw, W - margin * 2)

    line_h = 90 + 24  # 폰트 크기 + 줄 간격
    total_text_h = len(lines) * line_h
    y_start = max(margin, (H - total_text_h) // 2 - 80)

    # 4. 텍스트 그림자 + 본문
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) // 2
        y = y_start + i * line_h
        # 검은 그림자
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4), (4, 0)]:
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0))
        # 흰 텍스트
        draw.text((x, y), line, font=font, fill=(255, 255, 255))

    # 5. 텍스트 아래 골드 구분선
    div_y = y_start + total_text_h + 28
    draw.rectangle([(W // 4, div_y), (3 * W // 4, div_y + 4)], fill=GOLD)

    # 6. 하단 반투명 바 (영상 제목 공간)
    bar_h = 140
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, H - bar_h), (W, H)], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    return output_path


# ── ThumbnailStep ─────────────────────────────────────────────────────────────

class ThumbnailStep:
    def __init__(
        self,
        thumbnail_config: ThumbnailSettings,
        canva_config: CanvaSettings,
        openai_client: OpenAIClient | None = None,
        google_client: GoogleClient | None = None,
    ):
        self.thumbnail_config = thumbnail_config
        self.canva_config = canva_config
        self.openai_client = openai_client
        self.google_client = google_client
        self.token_file = Path(canva_config.token_file).resolve() if canva_config.token_file else Path("")

    # ── 공개 인터페이스 ──────────────────────────────────────────────────────

    def run(
        self,
        title: str,
        output_dir: Path,
        topic: str = "",
        channel_key: str = "",
    ) -> str | None:
        """
        썸네일 생성. mode에 따라 pillow / dalle / gemini / canva 분기.
        channel_key가 주어지면 채널별 최적화된 AI 프롬프트를 사용합니다.
        실패 시 None 반환 (파이프라인 중단 없음).
        """
        mode = self.thumbnail_config.mode
        output_path = output_dir / "thumbnail.png"

        try:
            if mode == "none":
                return None
            if mode == "pillow":
                return self._run_pillow(title, output_path)
            if mode == "dalle":
                return self._run_dalle(title, topic, output_path, channel_key)
            if mode == "gemini":
                return self._run_gemini(title, topic, output_path, channel_key)
            if mode == "canva":
                return self._run_canva(title, output_dir, output_path)
            # 알 수 없는 모드 → pillow 폴백
            logger.warning("[Thumbnail] 알 수 없는 mode='%s', Pillow로 폴백", mode)
            return self._run_pillow(title, output_path)
        except Exception as exc:
            logger.error("[Thumbnail] 생성 실패 (건너뜀): %s", exc)
            return None

    # ── 내부 모드 구현 ───────────────────────────────────────────────────────

    def _run_pillow(self, title: str, output_path: Path) -> str | None:
        clean_title = _sanitize_title(title)
        if len(clean_title) > 15:
            print(
                f"[Thumbnail] WARNING: 제목 {len(clean_title)}자 — "
                "15자 이하 권장 (모바일 가독성)"
            )
        result = _generate_pillow_thumbnail(title, output_path)
        print(f"[Thumbnail] Pillow 썸네일 저장: {result}")
        return result.resolve().as_posix()

    @staticmethod
    def _resolve_ai_prompt(topic: str, title: str, channel_key: str, config_template: str) -> str:
        """AI 썸네일 프롬프트를 채널별 템플릿에서 결정.

        우선순위: config.yaml 커스텀 템플릿 > 채널별 내장 템플릿 > 기본 템플릿
        """
        effective_topic = topic or title
        if config_template:
            return config_template.format(title=title, topic=effective_topic)
        if channel_key and channel_key in _CHANNEL_THUMB_PROMPTS:
            prompt = _CHANNEL_THUMB_PROMPTS[channel_key].format(
                title=title, topic=effective_topic,
            )
            logger.info("[Thumbnail] 채널 '%s' 전용 프롬프트 사용", channel_key)
            return prompt
        return _DEFAULT_THUMB_PROMPT.format(title=title, topic=effective_topic)

    def _run_dalle(
        self, title: str, topic: str, output_path: Path, channel_key: str = "",
    ) -> str | None:
        if not self.openai_client:
            logger.warning("[Thumbnail] DALL-E 모드지만 openai_client 없음 → Pillow 폴백")
            return self._run_pillow(title, output_path)

        dalle_prompt = self._resolve_ai_prompt(
            topic, title, channel_key, self.thumbnail_config.dalle_prompt_template,
        )
        logger.info("[Thumbnail] DALL-E prompt (channel=%s): %.80s...", channel_key or "default", dalle_prompt)

        bg_path = output_path.parent / "thumbnail_dalle_bg.png"
        self.openai_client.generate_image(
            model="dall-e-3",
            prompt=dalle_prompt,
            size="1024x1792",
            quality="standard",
            output_path=bg_path,
        )
        _overlay_title(bg_path, _sanitize_title(title), output_path)
        bg_path.unlink(missing_ok=True)
        logger.info("[Thumbnail] DALL-E 썸네일 저장: %s", output_path)
        return output_path.resolve().as_posix()

    def _run_gemini(
        self, title: str, topic: str, output_path: Path, channel_key: str = "",
    ) -> str | None:
        """Gemini Imagen 3 API로 썸네일 생성 (무료 tier)."""
        if not self.google_client:
            logger.warning("[Thumbnail] Gemini 모드지만 google_client 없음 → DALL-E 폴백")
            return self._run_dalle(title, topic, output_path, channel_key)

        gemini_prompt = self._resolve_ai_prompt(
            topic, title, channel_key, self.thumbnail_config.dalle_prompt_template,
        )
        logger.info("[Thumbnail] Gemini prompt (channel=%s): %.80s...", channel_key or "default", gemini_prompt)

        bg_path = output_path.parent / "thumbnail_gemini_bg.png"
        try:
            self.google_client.generate_image(
                prompt=gemini_prompt,
                output_path=bg_path,
                aspect_ratio="9:16",
            )
        except Exception as exc:
            logger.warning("[Thumbnail] Gemini Imagen 실패 → DALL-E 폴백: %s", exc)
            return self._run_dalle(title, topic, output_path, channel_key)

        _overlay_title(bg_path, _sanitize_title(title), output_path)
        bg_path.unlink(missing_ok=True)
        logger.info("[Thumbnail] Gemini 썸네일 저장: %s", output_path)
        return output_path.resolve().as_posix()

    def _run_canva(self, title: str, output_dir: Path, output_path: Path) -> str | None:
        if not self.canva_config.enabled or not self.canva_config.design_id:
            print("[Thumbnail] Canva 모드지만 설정 없음 → Pillow 폴백")
            return self._run_pillow(title, output_path)

        token = _get_access_token(self.token_file)
        tmp_path = output_dir / "thumbnail_base.png"

        try:
            download_url = _export_design(self.canva_config.design_id, token)
        except requests.HTTPError as http_err:
            if http_err.response is not None and http_err.response.status_code == 401:
                print("[Canva] 토큰 만료 — 자동 갱신 시도...")
                token = _refresh_access_token(self.token_file)
                download_url = _export_design(self.canva_config.design_id, token)
            else:
                raise

        _http_download(download_url, tmp_path)
        _overlay_title(tmp_path, _sanitize_title(title), output_path)
        tmp_path.unlink(missing_ok=True)
        print(f"[Canva] 썸네일 저장: {output_path}")
        return output_path.resolve().as_posix()
