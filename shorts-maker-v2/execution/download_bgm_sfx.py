"""BGM / SFX 에셋 다운로드 스크립트.

Pixabay Music API를 사용하여 채널별 BGM과 SFX를 다운로드합니다.
Pixabay API는 무료이며, API 키만 있으면 사용 가능합니다.

Usage:
    # Pixabay API 키 필요 (https://pixabay.com/api/docs/)
    # .env에 PIXABAY_API_KEY=<your-key> 추가 후:
    python execution/download_bgm_sfx.py

    # 또는 직접 지정:
    python execution/download_bgm_sfx.py --api-key YOUR_KEY

참고: Pixabay API 키가 없는 경우, https://pixabay.com/accounts/register/ 에서
무료 계정을 만들면 API 키를 받을 수 있습니다.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ── 프로젝트 루트 탐색 ──
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
BGM_DIR = ASSETS_DIR / "bgm"
SFX_DIR = ASSETS_DIR / "sfx"

# ── Pixabay Music API ──
PIXABAY_API_URL = "https://pixabay.com/api/videos/"  # 음악은 별도 엔드포인트 없음
PIXABAY_AUDIO_URL = "https://pixabay.com/api/"


# ── 채널별 BGM 검색 쿼리 & 파일명 키워드 ──
# 파일명에 mood 키워드를 포함시켜야 render_step._pick_bgm_by_mood()가 매칭
BGM_DOWNLOADS: list[dict] = [
    # ai_tech (energy: high)
    {"query": "electronic upbeat", "filename": "upbeat_electronic_01.mp3", "category": "music"},
    {"query": "synthwave cyberpunk", "filename": "energetic_synthwave_01.mp3", "category": "music"},
    {"query": "technology futuristic", "filename": "upbeat_tech_01.mp3", "category": "music"},
    # psychology (energy: calm)
    {"query": "calm piano ambient", "filename": "calm_piano_01.mp3", "category": "music"},
    {"query": "peaceful meditation", "filename": "calm_ambient_01.mp3", "category": "music"},
    {"query": "soft emotional", "filename": "calm_emotional_01.mp3", "category": "music"},
    # history (energy: medium)
    {"query": "cinematic orchestral", "filename": "cinematic_orchestral_01.mp3", "category": "music"},
    {"query": "documentary background", "filename": "cinematic_documentary_01.mp3", "category": "music"},
    # space (energy: epic)
    {"query": "epic dramatic", "filename": "epic_dramatic_01.mp3", "category": "music"},
    {"query": "epic orchestral space", "filename": "epic_orchestral_01.mp3", "category": "music"},
    {"query": "space ambient cinematic", "filename": "epic_space_01.mp3", "category": "music"},
    # health (energy: medium)
    {"query": "gentle background calm", "filename": "calm_gentle_01.mp3", "category": "music"},
    {"query": "positive uplifting", "filename": "upbeat_positive_01.mp3", "category": "music"},
]

# ── SFX: 파일명에 역할 키워드 포함 ──
# render_step._SFX_ROLE_KEYWORDS 참조:
#   hook: whoosh, impact, hit, boom, hook
#   transition: swish, swoosh, transition, sweep, slide
#   cta: pop, ding, bell, chime, cta, notification
SFX_DOWNLOADS: list[dict] = [
    # Hook SFX
    {"query": "whoosh impact", "filename": "whoosh_impact_01.mp3", "duration_max": 5},
    {"query": "boom cinematic", "filename": "boom_cinematic_01.mp3", "duration_max": 5},
    {"query": "impact hit dramatic", "filename": "hit_dramatic_01.mp3", "duration_max": 5},
    # Transition SFX
    {"query": "swoosh transition", "filename": "swoosh_transition_01.mp3", "duration_max": 3},
    {"query": "sweep smooth", "filename": "sweep_smooth_01.mp3", "duration_max": 3},
    {"query": "slide transition", "filename": "slide_transition_01.mp3", "duration_max": 3},
    # CTA SFX
    {"query": "ding notification", "filename": "ding_notification_01.mp3", "duration_max": 3},
    {"query": "pop bubble", "filename": "pop_bubble_01.mp3", "duration_max": 3},
    {"query": "bell chime", "filename": "bell_chime_01.mp3", "duration_max": 3},
]


def search_pixabay_audio(
    api_key: str,
    query: str,
    *,
    category: str = "music",
    per_page: int = 3,
    min_duration: int = 0,
    max_duration: int = 300,
) -> list[dict]:
    """Pixabay에서 오디오를 검색합니다."""
    # Pixabay는 공식 Music API가 없으므로 일반 API로 이미지 검색 후
    # 별도의 audio 검색이 필요합니다.
    # 대안: Pixabay Music 페이지를 직접 사용하거나 Freesound API를 사용합니다.
    # 여기서는 Freesound API (preview 다운로드)를 fallback으로 사용합니다.
    pass


def search_freesound(
    api_key: str,
    query: str,
    *,
    duration_min: float = 10.0,
    duration_max: float = 180.0,
    per_page: int = 5,
) -> list[dict]:
    """Freesound API v2로 사운드를 검색합니다.

    Note: license 필터를 사용하면 검색 결과가 0건이 되는 API 버그가
    있어 duration 필터만 사용합니다. Freesound의 대부분의 콘텐츠는
    CC0 또는 CC-BY 라이선스입니다.
    """
    resp = requests.get(
        "https://freesound.org/apiv2/search/text/",
        params={
            "token": api_key,
            "query": query,
            "filter": f"duration:[{duration_min} TO {duration_max}]",
            "fields": "id,name,duration,license,previews,download",
            "sort": "score",
            "page_size": per_page,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def download_freesound_preview(
    api_key: str,
    sound: dict,
    output_path: Path,
) -> Path:
    """Freesound의 HQ 미리듣기(MP3)를 다운로드합니다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        logger.info("  ⏭️  이미 존재: %s", output_path.name)
        return output_path

    previews = sound.get("previews", {})
    url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
    if not url:
        raise RuntimeError(f"미리듣기 URL 없음: sound_id={sound.get('id')}")

    resp = requests.get(url, params={"token": api_key}, timeout=60, stream=True)
    resp.raise_for_status()

    with output_path.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info(
        "  ✅ 다운로드 완료: %s (%.1fs, %s)",
        output_path.name,
        sound.get("duration", 0),
        sound.get("license", "unknown"),
    )
    return output_path


def download_bgm(api_key: str) -> int:
    """채널별 BGM 파일들을 다운로드합니다."""
    BGM_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    logger.info("\n🎵 BGM 다운로드 시작 (%d개 트랙)", len(BGM_DOWNLOADS))
    logger.info("   대상 폴더: %s\n", BGM_DIR)

    for item in BGM_DOWNLOADS:
        query = item["query"]
        filename = item["filename"]
        output_path = BGM_DIR / filename

        if output_path.exists():
            logger.info("  ⏭️  이미 존재: %s", filename)
            downloaded += 1
            continue

        logger.info("  🔍 검색: %r → %s", query, filename)
        try:
            results = search_freesound(
                api_key,
                query,
                duration_min=30.0,
                duration_max=120.0,
            )
            if not results:
                logger.warning("  ⚠️  검색 결과 없음: %r", query)
                continue

            download_freesound_preview(api_key, results[0], output_path)
            downloaded += 1
            time.sleep(0.5)  # API 속도 제한 방지

        except Exception as e:
            logger.error("  ❌ 실패: %s — %s", filename, e)

    return downloaded


def download_sfx(api_key: str) -> int:
    """SFX 효과음 파일들을 다운로드합니다."""
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    logger.info("\n🔊 SFX 다운로드 시작 (%d개 효과음)", len(SFX_DOWNLOADS))
    logger.info("   대상 폴더: %s\n", SFX_DIR)

    for item in SFX_DOWNLOADS:
        query = item["query"]
        filename = item["filename"]
        duration_max = item.get("duration_max", 10)
        output_path = SFX_DIR / filename

        if output_path.exists():
            logger.info("  ⏭️  이미 존재: %s", filename)
            downloaded += 1
            continue

        logger.info("  🔍 검색: %r → %s", query, filename)
        try:
            results = search_freesound(
                api_key,
                query,
                duration_min=0.1,
                duration_max=float(duration_max),
            )
            if not results:
                logger.warning("  ⚠️  검색 결과 없음: %r", query)
                continue

            download_freesound_preview(api_key, results[0], output_path)
            downloaded += 1
            time.sleep(0.5)  # API 속도 제한 방지

        except Exception as e:
            logger.error("  ❌ 실패: %s — %s", filename, e)

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="BGM/SFX 에셋 다운로드")
    parser.add_argument(
        "--api-key",
        default=None,
        help="Freesound API 키 (없으면 .env의 FREESOUND_API_KEY 사용)",
    )
    parser.add_argument(
        "--bgm-only",
        action="store_true",
        help="BGM만 다운로드",
    )
    parser.add_argument(
        "--sfx-only",
        action="store_true",
        help="SFX만 다운로드",
    )
    args = parser.parse_args()

    # .env 로드
    for env_path in [PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break

    api_key = args.api_key or os.getenv("FREESOUND_API_KEY", "")
    if not api_key:
        logger.error(
            "❌ FREESOUND_API_KEY가 필요합니다.\n\n"
            "   1. https://freesound.org/apiv2/apply/ 에서 무료 API 키 발급\n"
            "   2. .env 파일에 추가: FREESOUND_API_KEY=your_key_here\n"
            "   3. 또는: python execution/download_bgm_sfx.py --api-key YOUR_KEY\n"
        )
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("🎬 Shorts Maker V2 — BGM/SFX 에셋 다운로드")
    logger.info("=" * 60)

    bgm_count = 0
    sfx_count = 0

    if not args.sfx_only:
        bgm_count = download_bgm(api_key)

    if not args.bgm_only:
        sfx_count = download_sfx(api_key)

    logger.info("\n" + "=" * 60)
    logger.info("📊 결과 요약")
    logger.info("   BGM: %d / %d 다운로드 완료", bgm_count, len(BGM_DOWNLOADS))
    logger.info("   SFX: %d / %d 다운로드 완료", sfx_count, len(SFX_DOWNLOADS))
    logger.info("=" * 60)

    # 파일명 → 매칭 키워드 확인표 출력
    logger.info("\n📋 파일명-키워드 매칭 확인:")
    logger.info("  BGM mood 키워드: calm, upbeat, energetic, epic, cinematic")
    logger.info("  SFX role 키워드:")
    logger.info("    hook:       whoosh, impact, hit, boom")
    logger.info("    transition: swoosh, sweep, slide, transition")
    logger.info("    cta:        ding, pop, bell, chime, notification")


if __name__ == "__main__":
    main()
