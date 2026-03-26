from __future__ import annotations

import logging
import os
import random
import urllib.parse
from pathlib import Path

import requests
from moviepy import ImageClip

logger = logging.getLogger(__name__)


def _fetch_pexels_image(query: str, cache_path: Path) -> Path | None:
    """Phase 4-D: Pexels stock photo as B-Roll source (free, high quality)."""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query[:80], "per_page": 5, "size": "small"},
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        photo = random.choice(photos)
        img_url = photo.get("src", {}).get("medium")
        if not img_url:
            return None
        img_resp = requests.get(img_url, timeout=10)
        if img_resp.status_code == 200 and len(img_resp.content) > 1000:
            cache_path.write_bytes(img_resp.content)
            logger.info("[B-Roll] Pexels hit: %s", query[:30])
            return cache_path
    except Exception as exc:
        logger.debug("[B-Roll] Pexels failed: %s", exc)
    return None


def _ensure_broll_image(cache_dir: Path, broll_prompt: str) -> Path | None:
    """B-Roll 이미지 조달: Pexels → Pollinations fallback."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_name = urllib.parse.quote_plus(broll_prompt[:50])
    broll_path = cache_dir / f"broll_{safe_name}.png"

    if broll_path.exists() and broll_path.stat().st_size > 0:
        return broll_path

    # Phase 4-D: Pexels first (stock photo quality)
    result = _fetch_pexels_image(broll_prompt, broll_path)
    if result:
        return result

    # Fallback: Pollinations AI icon
    try:
        p = urllib.parse.quote(f"flat vector icon of {broll_prompt[:100]}, solid color background, minimalist")
        url = f"https://image.pollinations.ai/prompt/{p}?model=flux&width=512&height=512&nologo=true"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 1000:
            broll_path.write_bytes(resp.content)
            return broll_path
    except Exception as e:
        logger.warning("[B-Roll] Pollinations failed: %s", e)

    return None


def create_broll_pip(
    base_clip,
    cache_dir: Path,
    visual_prompt: str,
    target_width: int,
    target_height: int,
    start_time: float = 0.0,
    duration: float | None = None,
):
    """
    B-Roll(보조 이미지/아이콘)을 화면 우상단에 Picture-in-Picture(PIP) 모드로 겹친다.
    """
    broll_path = _ensure_broll_image(cache_dir, visual_prompt)
    if not broll_path:
        return None

    try:
        pip_clip = ImageClip(str(broll_path))
    except Exception as e:
        logger.warning("[B-Roll] Failed to load PIP source %s: %s", broll_path, e)
        return None

    pip_clip = pip_clip.with_duration(duration) if duration is not None else pip_clip.with_duration(base_clip.duration)

    pip_clip = pip_clip.with_start(start_time)

    # 1. 크기 조정 (화면 너비의 30% 정도)
    pip_w = int(target_width * 0.30)

    # 원본 비율 유지하면서 resize
    scale = pip_w / pip_clip.w
    pip_clip = pip_clip.resized(scale)

    # 2. 반투명 및 약간의 테두리 여백
    # opacity 플러그인 등 지원이 완벽하지 않을 수 있으므로 MoviePy의 with_opacity 사용 권장 (기본적으로 with_opacity는 mask alpha 조절)
    try:
        # with_opacity가 있으면 사용.
        if hasattr(pip_clip, "with_opacity"):
            pip_clip = pip_clip.with_opacity(0.85)
        else:
            # MoviePy 1.x/2.x 호환성을 위해 ImageClip 자체에 마스크 부여
            import numpy as np

            mask_arr = np.ones((pip_clip.h, pip_clip.w), dtype=float) * 0.85
            pip_clip = pip_clip.with_mask(ImageClip(mask_arr, is_mask=True))
    except Exception:
        pass

    margin_x = 40
    margin_y = 60

    # 위치: 우상단
    pos_x = target_width - pip_clip.w - margin_x
    pos_y = margin_y

    pip_clip = pip_clip.with_position((pos_x, pos_y))
    return pip_clip
