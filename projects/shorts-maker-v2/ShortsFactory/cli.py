#!/usr/bin/env python3
"""ShortsFactory — CLI 인터페이스.

사용법:
    # 단일 영상 렌더
    python -m ShortsFactory.cli render --channel ai_tech --template ai_news_breaking --data '{"news_title":"GPT-5"}' --out output.mp4

    # 배치 렌더
    python -m ShortsFactory.cli batch --csv contents.csv --outdir ./output/

    # 채널 목록
    python -m ShortsFactory.cli channels

    # 템플릿 목록
    python -m ShortsFactory.cli templates

    # 채널 정보
    python -m ShortsFactory.cli info --channel ai_tech
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)


def cmd_channels(args):
    from .pipeline import ShortsFactory

    channels = ShortsFactory.list_channels()
    print(f"\n{'=' * 60}")
    print(f"🎬 ShortsFactory — {len(channels)}개 채널")
    print(f"{'=' * 60}")
    for ch in channels:
        tmpl = ", ".join(ch["templates"])
        print(f"  {ch['id']:15s} | {ch['display_name']:12s} | 프리셋: {ch['color_preset']}")
        print(f"{'':17s} └ 템플릿: {tmpl}")
    print()


def cmd_templates(args):
    from .pipeline import ShortsFactory

    tmpls = ShortsFactory.list_templates()
    print(f"\n📋 등록된 템플릿 ({len(tmpls)}종):")
    for t in tmpls:
        print(f"  • {t}")
    print()


def cmd_info(args):
    from .pipeline import ShortsFactory

    factory = ShortsFactory(channel=args.channel)
    info = factory.info()
    print(f"\n{'=' * 50}")
    print(f"📊 채널 정보: {info['display_name']} ({info['channel']})")
    print(f"{'=' * 50}")
    print(f"  팔레트:   {info['palette']}")
    print(f"  프리셋:   {info['color_preset']}")
    print(f"  캡션콤보: {info['caption_combo']}")
    print(f"  훅 스타일: {info['hook_style']}")
    print(f"  전환:     {info['transition']}")
    print(f"  키워드:   {info['keywords']}개")
    print(f"  면책조항: {'✅' if info['disclaimer'] else '❌'}")
    print(f"  템플릿:   {', '.join(info['templates'])}")
    print()


def cmd_render(args):
    from .pipeline import ShortsFactory

    data = {}
    if args.data:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 실패: {e}")
            sys.exit(1)

    factory = ShortsFactory(channel=args.channel)
    factory.create(args.template, data)
    result = factory.render(args.out)
    print(f"\n✅ 렌더 완료: {result}")


def cmd_batch(args):
    from .batch import batch_render

    results = batch_render(args.csv, args.outdir)
    done = sum(1 for r in results if r.get("status") == "done")
    fail = sum(1 for r in results if r.get("status") == "error")
    print(f"\n📊 배치 결과: {done} 성공, {fail} 실패 / {len(results)} 전체")


def main():
    parser = argparse.ArgumentParser(prog="ShortsFactory", description="5채널 통합 쇼츠 생성 파이프라인")
    sub = parser.add_subparsers(dest="command", help="명령어")

    # channels
    sub.add_parser("channels", help="채널 목록 보기")

    # templates
    sub.add_parser("templates", help="템플릿 목록 보기")

    # info
    p_info = sub.add_parser("info", help="채널 상세 정보")
    p_info.add_argument("--channel", required=True)

    # render
    p_render = sub.add_parser("render", help="단일 영상 렌더")
    p_render.add_argument("--channel", required=True)
    p_render.add_argument("--template", required=True)
    p_render.add_argument("--data", default="{}", help="JSON 데이터")
    p_render.add_argument("--out", default="output.mp4")

    # batch
    p_batch = sub.add_parser("batch", help="CSV 배치 렌더")
    p_batch.add_argument("--csv", required=True)
    p_batch.add_argument("--outdir", default="output")

    args = parser.parse_args()

    cmds = {
        "channels": cmd_channels,
        "templates": cmd_templates,
        "info": cmd_info,
        "render": cmd_render,
        "batch": cmd_batch,
    }

    if args.command in cmds:
        cmds[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
