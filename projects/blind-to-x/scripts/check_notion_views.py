"""Review-first Notion property checker for blind-to-x.

Usage:
    cd blind-to-x
    python scripts/check_notion_views.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").replace("-", "")

VIEW_REQUIREMENTS: dict[str, dict[str, list[str] | str]] = {
    "검토 워크플로우 (Board)": {
        "required": ["콘텐츠", "상태", "토픽 클러스터", "최종 랭크 점수", "위험 신호", "반려 사유"],
        "description": "상태 기준 보드. 검토량과 반려 패턴을 빠르게 보는 뷰.",
    },
    "검토 큐 (Table)": {
        "required": [
            "콘텐츠",
            "원본 소스",
            "운영자 해석",
            "근거 앵커",
            "검토 포인트",
            "피드백 요청",
            "위험 신호",
            "반려 사유",
        ],
        "description": "운영자가 실제 판단과 피드백을 남기는 메인 뷰.",
    },
    "반려 회고 (Table)": {
        "required": ["콘텐츠", "상태", "위험 신호", "반려 사유", "토픽 클러스터", "생성일"],
        "description": "어떤 유형이 반복적으로 잘리는지 회고하는 뷰.",
    },
    "발행 후보 (Optional)": {
        "required": ["콘텐츠", "상태", "발행 플랫폼", "트윗 본문", "Threads 본문", "블로그 본문"],
        "description": "승인된 초안을 채널별로 복사할 때 쓰는 선택 뷰.",
    },
}


def fetch_db_properties() -> dict[str, str]:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("NOTION_API_KEY 또는 NOTION_DATABASE_ID가 .env에 설정되어 있지 않습니다.")
        raise SystemExit(1)

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    for endpoint in (f"databases/{NOTION_DATABASE_ID}", f"data_sources/{NOTION_DATABASE_ID}"):
        url = f"https://api.notion.com/v1/{endpoint}"
        try:
            response = httpx.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                properties = response.json().get("properties", {})
                return {name: info.get("type", "unknown") for name, info in properties.items()}
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"  warning: {endpoint} 조회 실패: {exc}")

    print("Notion DB 조회에 실패했습니다. DB ID와 공유 권한을 다시 확인해주세요.")
    raise SystemExit(1)


def check_views(properties: dict[str, str]) -> bool:
    all_ok = True
    print(f"\n현재 DB 속성 수: {len(properties)}\n")

    for view_name, requirement in VIEW_REQUIREMENTS.items():
        print("=" * 60)
        print(view_name)
        print(requirement["description"])
        print("=" * 60)

        missing: list[str] = []
        for prop_name in requirement["required"]:
            if prop_name in properties:
                print(f"  OK  {prop_name} ({properties[prop_name]})")
            else:
                print(f"  MISS {prop_name}")
                missing.append(prop_name)
                all_ok = False

        if missing:
            print(f"\n  누락 속성: {', '.join(missing)}")
            print("  먼저 review schema sync를 실행하세요.")
        else:
            print("\n  필요한 속성이 모두 있습니다.")
        print()

    return all_ok


def main() -> None:
    print("Notion 리뷰 뷰 기준 속성 점검 중...")
    properties = fetch_db_properties()
    all_ok = check_views(properties)

    print("=" * 60)
    if all_ok:
        print("모든 리뷰 뷰에 필요한 속성이 준비되어 있습니다.")
    else:
        print("리뷰용 속성이 일부 비어 있습니다.")
        print("권장 명령:")
        print("  py -3 scripts/sync_notion_review_schema.py --config config.yaml --apply")
        print("  py -3 scripts/backfill_notion_review_columns.py --config config.yaml --apply")
    print("=" * 60)


if __name__ == "__main__":
    main()
