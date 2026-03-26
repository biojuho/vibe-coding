#!/usr/bin/env python
"""트렌드 스카우트 — 채널별 바이럴 주제 자동 발굴 스탠드얼론 스크립트.

Usage:
    python execution/trend_scout.py --channel ai_tech --n 10
    python execution/trend_scout.py --channel psychology --n 5 --json

Output (기본):
    채널: 퓨처 시냅스 (ai_tech)
    ──────────────────────────────────────────
     순위  점수  후킹패턴              제목 후보
     1     9.2  cognitive_dissonance  바이브코딩 격차가 벌어지는 이유
     2     8.7  myth_busting          클로드가 승인창 없앤 진짜 이유
    ...
    ✅ .tmp/trend_candidates_20260326.json 저장 완료

Output (--json):
    .tmp/trend_candidates_20260326.json 경로만 출력
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# --- 프로젝트 루트를 sys.path에 추가 ---
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from shorts_maker_v2.config import AppConfig, load_config
from shorts_maker_v2.pipeline.topic_angle_generator import ScoredAngle, TopicAngleGenerator
from shorts_maker_v2.pipeline.trend_discovery_step import TrendCandidate, TrendDiscoveryStep
from shorts_maker_v2.providers.llm_router import LLMRouter

logging.basicConfig(
    level=logging.WARNING,  # 스탠드얼론에서는 WARNING 이상만 표시
    format="%(levelname)s  %(message)s",
)


CHANNEL_DISPLAY = {
    "ai_tech": "퓨처 시냅스",
    "psychology": "토닥토닥 심리",
    "history": "역사팝콘",
    "space": "도파민 랩",
    "health": "건강 스포일러",
}

HOOK_EMOJI = {
    "cognitive_dissonance": "🔄",
    "shocking_stat": "📊",
    "myth_busting": "💥",
    "counterintuitive_question": "❓",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="채널별 트렌드 주제 자동 발굴",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--channel",
        required=True,
        choices=["ai_tech", "psychology", "history", "space", "health"],
        help="대상 채널",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=5,
        help="반환할 후보 수 (기본: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON 파일 경로만 출력",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help=".tmp/ 저장 비활성화",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )
    return parser.parse_args()


def print_results(angles: list[ScoredAngle], channel_key: str) -> None:
    """표 형식으로 결과 출력."""
    display_name = CHANNEL_DISPLAY.get(channel_key, channel_key)
    print(f"\n📡 채널: {display_name} ({channel_key})")
    print("─" * 70)
    print(f"{'순위':>4}  {'점수':>5}  {'패턴':<12}  제목 후보")
    print("─" * 70)
    for i, angle in enumerate(angles, 1):
        hook_icon = HOOK_EMOJI.get(angle.hook_pattern, "▶")
        score_bar = "█" * int(angle.viral_score) + "░" * (10 - int(angle.viral_score))
        print(f"  {i:>2}.  {angle.viral_score:>4.1f}  {hook_icon} {angle.hook_pattern:<20}  {angle.title}")
        if angle.title_variants and len(angle.title_variants) > 1:
            for v in angle.title_variants:
                if v != angle.title:
                    print(f"        {'':>5}   {'':>20}  └ {v}")
    print("─" * 70)
    print(f"💡 각도 설명: {angles[0].angle if angles else 'N/A'}")
    print()


def save_results(
    candidates: list[TrendCandidate],
    angles: list[ScoredAngle],
    channel_key: str,
) -> Path:
    """결과를 .tmp/ 디렉터리에 JSON으로 저장."""
    tmp_dir = _PROJECT_ROOT / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    out_path = tmp_dir / f"trend_candidates_{channel_key}_{today}.json"

    data = {
        "generated_at": datetime.now().isoformat(),
        "channel": channel_key,
        "trend_candidates": [
            {
                "keyword": c.keyword,
                "source": c.source,
                "score": c.score,
                "raw_title": c.raw_title,
            }
            for c in candidates
        ],
        "scored_angles": [
            {
                "topic": a.topic,
                "title": a.title,
                "title_variants": a.title_variants,
                "angle": a.angle,
                "hook_pattern": a.hook_pattern,
                "viral_score": a.viral_score,
                "source_keyword": a.source_keyword,
            }
            for a in angles
        ],
    }
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 설정 로드
    config_path = _PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        print(f"❌ config.yaml not found: {config_path}", file=sys.stderr)
        return 1

    try:
        config = load_config(config_path)
    except Exception as exc:
        print(f"❌ Config load failed: {exc}", file=sys.stderr)
        return 1

    # LLM Router 초기화
    try:
        llm_router = LLMRouter(config)
    except Exception as exc:
        print(f"⚠️  LLM Router 초기화 실패 (LLM fallback 비활성화): {exc}", file=sys.stderr)
        llm_router = None

    # Step 1: 트렌드 수집
    print(f"🔍 트렌드 수집 중... (채널: {args.channel}, 최대 {args.n}개)")
    discovery = TrendDiscoveryStep(config, llm_router=llm_router)
    candidates = discovery.run(channel_key=args.channel, n=args.n * 2)  # 여유롭게 수집

    if not candidates:
        print("⚠️  트렌드 후보를 찾지 못했습니다. --verbose로 상세 오류 확인.", file=sys.stderr)
        return 1

    # Step 2: 각도 + 제목 생성
    print(f"🧠 인지 부조화 훅 생성 중... ({len(candidates)}개 후보 분석)")
    if llm_router is None:
        print("⚠️  LLM Router 없음 — fallback 각도 사용", file=sys.stderr)

    generator = TopicAngleGenerator(config, llm_router=llm_router)  # type: ignore[arg-type]
    angles = generator.run(candidates, channel_key=args.channel, n=args.n)

    if not angles:
        print("❌ 각도 생성 실패", file=sys.stderr)
        return 1

    # 출력
    if not args.json:
        print_results(angles, args.channel)

    # 저장
    if not args.no_save:
        out_path = save_results(candidates, angles, args.channel)
        if args.json:
            print(str(out_path))
        else:
            print(f"✅ 저장 완료: {out_path}")
            print("\n▶ 다음 단계 — 파이프라인에 바로 투입:")
            if angles:
                print(f'   python -m shorts_maker_v2 --channel {args.channel} "{angles[0].topic}"')

    return 0


if __name__ == "__main__":
    sys.exit(main())
