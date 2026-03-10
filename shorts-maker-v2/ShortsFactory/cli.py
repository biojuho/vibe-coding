"""
cli.py — ShortsFactory CLI 인터페이스
=====================================
사용법:
    python -m ShortsFactory --channel ai_tech --template ai_news --data '{...}'
    python -m ShortsFactory --batch contents.csv --output-dir ./output/
    python -m ShortsFactory --list-channels
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from ShortsFactory.pipeline import ShortsFactory


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ShortsFactory",
        description="5채널 통합 숏츠 제작 파이프라인",
    )
    p.add_argument("--channel", "-c", help="채널 키 (ai_tech, psychology, history, space, health)")
    p.add_argument("--template", "-t", help="템플릿 이름 (ai_news, psych_experiment 등)")
    p.add_argument("--data", "-d", help="콘텐츠 데이터 JSON 문자열")
    p.add_argument("--data-file", help="콘텐츠 데이터 JSON 파일 경로")
    p.add_argument("--output", "-o", default="output.mp4", help="출력 파일 경로")
    p.add_argument("--batch", "-b", help="배치 CSV 파일 경로")
    p.add_argument("--output-dir", default="./output", help="배치 출력 디렉토리")
    p.add_argument("--list-channels", action="store_true", help="사용 가능한 채널 목록")
    p.add_argument("--list-templates", action="store_true", help="사용 가능한 템플릿 목록")
    p.add_argument("--verbose", "-v", action="store_true", help="디버그 로깅")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # 로깅
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # 채널 목록
    if args.list_channels:
        channels = ShortsFactory.list_channels()
        print("\n📺 사용 가능한 채널:")
        for ch in channels:
            print(f"  {ch['key']:15s} — {ch['name']} (hook: {ch['hook_style']})")
        return 0

    # 템플릿 목록
    if args.list_templates:
        from ShortsFactory.templates import TEMPLATE_REGISTRY
        print("\n📋 사용 가능한 템플릿:")
        for name, cls in TEMPLATE_REGISTRY.items():
            print(f"  {name:20s} — {cls.__doc__ or cls.template_name}")
        return 0

    # 배치 모드
    if args.batch:
        if not args.channel:
            print("❌ --batch 모드에서는 --channel이 필요합니다.")
            return 1
        factory = ShortsFactory(args.channel)
        results = factory.batch_render(args.batch, args.output_dir)
        errors = sum(1 for r in results if r.status == "error")
        return 1 if errors > 0 else 0

    # 단일 모드
    if not args.channel or not args.template:
        parser.print_help()
        return 1

    # 데이터 로드
    data = {}
    if args.data:
        data = json.loads(args.data)
    elif args.data_file:
        with open(args.data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

    factory = ShortsFactory(args.channel)
    factory.create(args.template, data)
    result = factory.render(args.output)
    print(f"\n✅ 완료: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
