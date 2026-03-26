"""Notion DB 뷰 설정에 필요한 속성 존재 여부 검증 스크립트.

Usage:
    cd blind-to-x
    python scripts/check_notion_views.py
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")

import httpx  # noqa: E402

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# 뷰별 필수 속성 정의
VIEW_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "📋 발행 워크플로우 (Board)": {
        "required": ["승인 상태", "콘텐츠", "토픽 클러스터", "감정 축", "최종 랭크 점수", "원본 소스", "상태"],
        "description": "Board view grouped by '승인 상태'",
    },
    "🎴 X 트윗 큐 (Gallery)": {
        "required": ["트윗 본문", "콘텐츠", "토픽 클러스터", "Source URL", "승인 상태", "발행 플랫폼", "최종 랭크 점수", "트윗 링크"],
        "description": "Gallery view for copying tweets",
    },
    "🧵 Threads 큐 (Gallery)": {
        "required": ["Threads 본문", "콘텐츠", "감정 축", "Source URL", "승인 상태", "발행 플랫폼", "최종 랭크 점수", "Threads 링크"],
        "description": "Gallery view for copying Threads posts",
    },
    "🗓️ 콘텐츠 캘린더 (Calendar)": {
        "required": ["발행 예정일", "콘텐츠", "승인 상태", "발행 플랫폼", "토픽 클러스터"],
        "description": "Calendar view by '발행 예정일'",
    },
}


def fetch_db_properties() -> dict[str, str]:
    """Notion DB에서 현재 속성 목록을 가져옵니다."""
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("❌ NOTION_API_KEY 또는 NOTION_DATABASE_ID가 .env에 설정되지 않았습니다.")
        sys.exit(1)

    # databases 엔드포인트 시도, 실패 시 data_sources 엔드포인트
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    clean_id = NOTION_DATABASE_ID.replace("-", "")

    for endpoint in [f"databases/{clean_id}", f"data_sources/{clean_id}"]:
        url = f"https://api.notion.com/v1/{endpoint}"
        try:
            resp = httpx.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                props = data.get("properties", {})
                return {name: info.get("type", "unknown") for name, info in props.items()}
        except Exception as e:
            print(f"  ⚠️ {endpoint} 실패: {e}")

    print("❌ Notion DB 조회 실패. DB ID와 API 키를 확인하세요.")
    sys.exit(1)


def check_views(properties: dict[str, str]) -> bool:
    """뷰별 필수 속성 존재 여부를 검증합니다."""
    all_ok = True

    print(f"\n📊 현재 DB 속성: {len(properties)}개\n")

    for view_name, req in VIEW_REQUIREMENTS.items():
        print(f"{'='*60}")
        print(f"🔍 {view_name}")
        print(f"   {req['description']}")
        print(f"{'='*60}")

        missing = []
        for prop_name in req["required"]:
            if prop_name in properties:
                print(f"  ✅ {prop_name} ({properties[prop_name]})")
            else:
                print(f"  ❌ {prop_name} — 누락!")
                missing.append(prop_name)
                all_ok = False

        if missing:
            print(f"\n  ⚠️ 누락 속성 {len(missing)}개: {', '.join(missing)}")
            print("  → Notion DB에서 해당 속성을 수동으로 추가하세요.")
        else:
            print("\n  ✅ 모든 필수 속성 존재 — 뷰 생성 가능!")
        print()

    return all_ok


def main() -> None:
    """메인 실행."""
    print("🔄 Notion DB 속성 확인 중...")
    properties = fetch_db_properties()
    ok = check_views(properties)

    print("=" * 60)
    if ok:
        print("✅ 모든 뷰에 필요한 속성이 존재합니다!")
        print("   → docs/notion_view_setup_guide.md를 참조하여 뷰를 생성하세요.")
    else:
        print("⚠️ 일부 속성이 누락되었습니다. 위의 안내를 따라 추가하세요.")
    print("=" * 60)


if __name__ == "__main__":
    main()
