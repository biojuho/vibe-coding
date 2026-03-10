"""채널별 아웃트로 카드 자동 생성.

인트로와 대칭적인 브랜드 아웃트로 이미지를 자동 생성합니다.
채널별 테마 색상 + 채널명 + 소셜 CTA 포함.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 채널별 브랜드 컬러, 아이콘, 표시명 (ending_card.py와 동일)
_CHANNEL_BRAND: dict[str, dict] = {
    "ai_tech":    {"color": "#00D4FF", "icon": "🤖", "display": "퓨처 시냅스"},
    "psychology": {"color": "#FF9EAF", "icon": "🧠", "display": "토닥토닥 심리"},
    "history":    {"color": "#D4A843", "icon": "🏺", "display": "역사팝콘"},
    "space":      {"color": "#A855F7", "icon": "🔭", "display": "도파민 랩"},
    "health":     {"color": "#4CAF50", "icon": "💊", "display": "건강 스포일러"},
}
_DEFAULT_BRAND = {"color": "#FF0000", "icon": "▶", "display": "Subscribe"}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def render_outro_card(
    target_width: int,
    target_height: int,
    output_path: Path,
    channel_key: str = "",
    font_candidates: list[str] | None = None,
) -> Path:
    """
    채널별 아웃트로 카드 PNG 생성.

    - 상단: 채널 아이콘 + 채널명
    - 중앙: "다음 영상에서 만나요!" 메시지
    - 하단: 소셜 버튼 느낌 (좋아요 · 구독)
    - 배경: 채널 테마 색상 기반 그라데이션
    """
    brand = _CHANNEL_BRAND.get(channel_key, _DEFAULT_BRAND)
    accent_rgb = _hex_to_rgb(brand["color"])
    icon = brand["icon"]
    display_name = brand["display"]

    # 배경 — 위에서 아래로 어두운 그라데이션
    img = Image.new("RGBA", (target_width, target_height), (15, 15, 20, 255))
    draw = ImageDraw.Draw(img)
    for y in range(target_height):
        ratio = y / target_height
        # 채널 컬러가 위에서부터 서서히 나타나는 그라데이션
        r = int(15 + accent_rgb[0] * 0.15 * (1 - ratio))
        g = int(15 + accent_rgb[1] * 0.12 * (1 - ratio))
        b = int(20 + accent_rgb[2] * 0.18 * (1 - ratio))
        draw.line([(0, y), (target_width, y)], fill=(r, g, b, 255))

    # 하단 얇은 액센트 라인
    bar_h = max(4, target_width // 120)
    draw.rectangle(
        [(0, target_height - bar_h), (target_width, target_height)],
        fill=(*accent_rgb, 255),
    )

    # 중앙 장식: 큰 원형 글로우 효과
    cx, cy = target_width // 2, target_height // 2
    glow_radius = int(target_width * 0.25)
    for r_offset in range(glow_radius, 0, -2):
        alpha = int(30 * (r_offset / glow_radius))
        draw.ellipse(
            [cx - r_offset, cy - r_offset - 80, cx + r_offset, cy + r_offset - 80],
            fill=(*accent_rgb, alpha),
        )

    # 폰트 로드
    font_large = font_medium = font_small = None
    if font_candidates:
        for fp in font_candidates:
            p = Path(fp)
            if p.exists():
                try:
                    font_large = ImageFont.truetype(str(p), int(target_width * 0.09))
                    font_medium = ImageFont.truetype(str(p), int(target_width * 0.06))
                    font_small = ImageFont.truetype(str(p), int(target_width * 0.045))
                    break
                except Exception:
                    continue
    if not font_large:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 아이콘 + 채널명
    icon_text = f"{icon} {display_name}"
    bb = draw.textbbox((0, 0), icon_text, font=font_large)
    iw = bb[2] - bb[0]
    draw.text(
        (cx - iw // 2 + 3, cy - 160 + 3),
        icon_text, font=font_large,
        fill=(0, 0, 0, 140),
    )
    draw.text(
        (cx - iw // 2, cy - 160),
        icon_text, font=font_large,
        fill=(*accent_rgb, 255),
    )

    # 메인 메시지
    msg = "다음 영상에서 만나요!"
    bb2 = draw.textbbox((0, 0), msg, font=font_medium)
    mw = bb2[2] - bb2[0]
    draw.text(
        (cx - mw // 2 + 2, cy - 40 + 2),
        msg, font=font_medium,
        fill=(0, 0, 0, 120),
    )
    draw.text(
        (cx - mw // 2, cy - 40),
        msg, font=font_medium,
        fill=(240, 240, 240, 255),
    )

    # 소셜 CTA
    cta = "👍 좋아요  •  🔔 구독  •  💬 댓글"
    bb3 = draw.textbbox((0, 0), cta, font=font_small)
    ctw = bb3[2] - bb3[0]
    draw.text(
        (cx - ctw // 2, cy + 60),
        cta, font=font_small,
        fill=(180, 180, 190, 255),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")
    return output_path


def ensure_outro_assets(
    channel_key: str,
    assets_dir: Path,
    target_width: int = 1080,
    target_height: int = 1920,
    font_candidates: list[str] | None = None,
) -> Path | None:
    """아웃트로 에셋이 없으면 자동 생성, 있으면 기존 경로 반환."""
    outro_path = assets_dir / "outro" / f"{channel_key}_outro.png"
    if outro_path.exists():
        return outro_path
    try:
        return render_outro_card(
            target_width=target_width,
            target_height=target_height,
            output_path=outro_path,
            channel_key=channel_key,
            font_candidates=font_candidates,
        )
    except Exception:
        return None
