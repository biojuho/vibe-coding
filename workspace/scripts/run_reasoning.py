"""
귀납적 추론 엔진 CLI Runner.

Usage:
    # 텍스트 직접 입력
    python workspace/scripts/run_reasoning.py --category "AI_테크" --content "뉴스 텍스트..."

    # 파일에서 읽기
    python workspace/scripts/run_reasoning.py --category "트렌드" --content-file .tmp/report.txt

    # 패턴 DB 통계
    python workspace/scripts/run_reasoning.py --stats
    python workspace/scripts/run_reasoning.py --stats --category "AI_테크"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="귀납적 추론 엔진 — Popper 반증주의 기반 3단계 추론",
    )
    parser.add_argument("--category", type=str, help="분석 카테고리 (예: AI_테크, 트렌드)")
    parser.add_argument("--content", type=str, help="분석할 텍스트 (직접 입력)")
    parser.add_argument("--content-file", type=str, help="분석할 텍스트 파일 경로")
    parser.add_argument("--source-title", type=str, default="", help="원본 소스 제목")
    parser.add_argument("--report-id", type=str, default="", help="리포트 ID (미지정 시 자동 생성)")
    parser.add_argument("--stats", action="store_true", help="패턴 DB 통계 출력")
    parser.add_argument("--providers", type=str, nargs="*", help="LLM 프로바이더 지정 (예: google deepseek)")

    args = parser.parse_args()

    from execution.reasoning_engine import ReasoningAdapter

    adapter = ReasoningAdapter(
        providers=args.providers if args.providers else None,
    )

    # 통계 모드
    if args.stats:
        stats = adapter.get_pattern_stats(category=args.category)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return

    # 추론 모드 — 필수 인자 체크
    if not args.category:
        parser.error("--category 필수 (예: --category AI_테크)")

    content_text = ""
    if args.content:
        content_text = args.content
    elif args.content_file:
        p = Path(args.content_file)
        if not p.exists():
            print(f"ERROR: 파일을 찾을 수 없습니다: {p}", file=sys.stderr)
            sys.exit(1)
        content_text = p.read_text(encoding="utf-8")
    else:
        parser.error("--content 또는 --content-file 중 하나를 지정하세요")

    if not adapter.is_available():
        print("ERROR: 사용 가능한 LLM 프로바이더가 없습니다.", file=sys.stderr)
        sys.exit(1)

    report_id = args.report_id or f"cli-{args.category}"

    result = adapter.run_full_reasoning(
        report_id=report_id,
        category=args.category,
        content_text=content_text,
        source_title=args.source_title,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
