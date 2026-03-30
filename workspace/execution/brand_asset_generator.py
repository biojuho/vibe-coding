"""
채널 브랜드 에셋 생성기.
채널명으로 심플 인트로/아웃트로 PNG 이미지를 Pillow로 자동 생성.

Usage:
    python workspace/execution/brand_asset_generator.py --channel "우주/천문학"
    python workspace/execution/brand_asset_generator.py --channel "요리" --bg-color "#1a0a2e"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import resolve_project_dir

_SHORTS_DIR = resolve_project_dir("shorts-maker-v2", required_paths=("config.yaml",))
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for fp in _FONT_CANDIDATES:
        p = Path(fp)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                continue
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def generate_intro_image(
    channel: str,
    output_path: Path,
    width: int = 1080,
    height: int = 400,
    bg_color: str = "#0d0d1a",
    accent_color: str = "#FFD700",
) -> Path:
    """채널명을 표시하는 인트로 이미지 생성 (1080×400 RGBA PNG)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (width, height), _hex_to_rgb(bg_color) + (255,))
    draw = ImageDraw.Draw(img)

    # 상단 액센트 라인
    accent_rgb = _hex_to_rgb(accent_color)
    draw.rectangle([(0, 0), (width, 6)], fill=accent_rgb + (255,))
    # 하단 액센트 라인
    draw.rectangle([(0, height - 6), (width, height)], fill=accent_rgb + (255,))

    # 채널명 (큰 폰트)
    font_ch = _load_font(64)
    bbox = draw.textbbox((0, 0), channel, font=font_ch)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) / 2 - bbox[0]
    y = (height - text_h) / 2 - bbox[1] - 20
    draw.text((x, y), channel, font=font_ch, fill="#FFFFFF")

    # 부제 텍스트
    sub_text = "구독 · 좋아요 · 알림 설정"
    font_sub = _load_font(28)
    bbox_sub = draw.textbbox((0, 0), sub_text, font=font_sub)
    sub_w = bbox_sub[2] - bbox_sub[0]
    x_sub = (width - sub_w) / 2 - bbox_sub[0]
    y_sub = y + text_h + 24
    draw.text((x_sub, y_sub), sub_text, font=font_sub, fill=accent_color)

    img.save(str(output_path), format="PNG")
    return output_path


def generate_outro_image(
    channel: str,
    output_path: Path,
    width: int = 1080,
    height: int = 300,
    bg_color: str = "#0d0d1a",
    accent_color: str = "#FFD700",
) -> Path:
    """아웃트로 이미지 생성 (1080×300 RGBA PNG)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (width, height), _hex_to_rgb(bg_color) + (255,))
    draw = ImageDraw.Draw(img)

    # 상단 액센트 라인
    accent_rgb = _hex_to_rgb(accent_color)
    draw.rectangle([(0, 0), (width, 6)], fill=accent_rgb + (255,))

    # 아웃트로 텍스트
    main_text = "시청해 주셔서 감사합니다!"
    font_main = _load_font(52)
    bbox = draw.textbbox((0, 0), main_text, font=font_main)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) / 2 - bbox[0]
    y = (height - text_h) / 2 - bbox[1] - 18
    draw.text((x, y), main_text, font=font_main, fill="#FFFFFF")

    # 채널명
    font_ch = _load_font(30)
    bbox_ch = draw.textbbox((0, 0), channel, font=font_ch)
    ch_w = bbox_ch[2] - bbox_ch[0]
    x_ch = (width - ch_w) / 2 - bbox_ch[0]
    y_ch = y + text_h + 16
    draw.text((x_ch, y_ch), channel, font=font_ch, fill=accent_color)

    img.save(str(output_path), format="PNG")
    return output_path


def generate_channel_brand(
    channel: str,
    output_dir: Path | None = None,
    bg_color: str = "#0d0d1a",
    accent_color: str = "#FFD700",
) -> tuple[Path, Path]:
    """인트로 + 아웃트로 PNG 한 번에 생성. (intro.png, outro.png) 경로 반환."""
    if output_dir is None:
        output_dir = _SHORTS_DIR / "assets" / "channels" / channel
    output_dir = Path(output_dir)

    intro_path = output_dir / "intro.png"
    outro_path = output_dir / "outro.png"

    generate_intro_image(channel, intro_path, bg_color=bg_color, accent_color=accent_color)
    generate_outro_image(channel, outro_path, bg_color=bg_color, accent_color=accent_color)

    return intro_path, outro_path


def _cli() -> int:
    parser = argparse.ArgumentParser(description="채널 브랜드 에셋 생성")
    parser.add_argument("--channel", required=True, help="채널명")
    parser.add_argument("--bg-color", default="#0d0d1a", help="배경 색상 (hex, 기본: #0d0d1a)")
    parser.add_argument("--accent-color", default="#FFD700", help="액센트 색상 (hex, 기본: #FFD700)")
    parser.add_argument(
        "--output-dir", default="", help="저장 경로 (기본: projects/shorts-maker-v2/assets/channels/<channel>)"
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else None
    intro_p, outro_p = generate_channel_brand(
        args.channel,
        output_dir=out_dir,
        bg_color=args.bg_color,
        accent_color=args.accent_color,
    )
    print(f"[OK] 인트로: {intro_p}")
    print(f"[OK] 아웃트로: {outro_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
