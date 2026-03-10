from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 채널별 브랜드 컬러, 아이콘, 표시명
_CHANNEL_BRAND: dict[str, dict] = {
    "ai_tech":    {"color": "#00D4FF", "icon": "🤖", "display": "퓨처 시냅스"},
    "psychology": {"color": "#FF9EAF", "icon": "🧠", "display": "토닥토닥 심리"},
    "history":    {"color": "#D4A843", "icon": "🏺", "display": "역사팝콘"},
    "space":      {"color": "#A855F7", "icon": "🔭", "display": "도파민 랩"},
    "health":     {"color": "#4CAF50", "icon": "💊", "display": "건강 스포일러"},
}
_DEFAULT_BRAND = {"color": "#FF0000", "icon": "▶", "display": "Subscribe Now!"}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def render_branded_ending_card(
    target_width: int,
    target_height: int,
    output_path: Path,
    channel_key: str = "",
    font_candidates: list[str] | None = None,
) -> Path:
    """
    채널별 브랜드 컬러가 적용된 엔딩 카드 생성 (2초용).

    Args:
        channel_key: channel_profiles.yaml의 채널 키 (ai_tech, psychology, ...)
    """
    brand = _CHANNEL_BRAND.get(channel_key, _DEFAULT_BRAND)
    accent_rgb = _hex_to_rgb(brand["color"])
    icon = brand["icon"]
    channel_display = brand["display"]

    # 배경 — 채널 컬러 기반 어두운 그라데이션
    img = Image.new("RGBA", (target_width, target_height), (12, 12, 18, 255))
    draw = ImageDraw.Draw(img)
    for y in range(target_height):
        ratio = y / target_height
        r = int(12 + accent_rgb[0] * 0.08 * ratio)
        g = int(12 + accent_rgb[1] * 0.06 * ratio)
        b = int(18 + accent_rgb[2] * 0.12 * ratio)
        draw.line([(0, y), (target_width, y)], fill=(r, g, b, 255))

    # 상단 얇은 액센트 라인
    bar_h = max(4, target_width // 120)
    draw.rectangle([(0, 0), (target_width, bar_h)], fill=(*accent_rgb, 255))

    # 폰트
    font_title = font_sub = None
    if font_candidates:
        for fp in font_candidates:
            p = Path(fp)
            if p.exists():
                try:
                    font_title = ImageFont.truetype(str(p), int(target_width * 0.10))
                    font_sub = ImageFont.truetype(str(p), int(target_width * 0.055))
                    break
                except Exception:
                    continue
    if not font_title:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    cx = target_width // 2
    cy = target_height // 2

    # 아이콘 + 채널명
    icon_text = f"{icon} {channel_display}"
    bb = draw.textbbox((0, 0), icon_text, font=font_title)
    iw = bb[2] - bb[0]
    draw.text((cx - iw // 2 + 3, cy - 140 + 3), icon_text, font=font_title, fill=(0, 0, 0, 150))
    draw.text((cx - iw // 2, cy - 140), icon_text, font=font_title, fill=(*accent_rgb, 255))

    # 구독 권유 텍스트
    sub_text = "좋아요 · 구독 · 알림 🔔"
    bb2 = draw.textbbox((0, 0), sub_text, font=font_sub)
    sw = bb2[2] - bb2[0]
    draw.text((cx - sw // 2 + 2, cy - 20 + 2), sub_text, font=font_sub, fill=(0, 0, 0, 130))
    draw.text((cx - sw // 2, cy - 20), sub_text, font=font_sub, fill=(220, 220, 220, 255))

    # 채널 컬러 구독 버튼
    btn_w = int(target_width * 0.55)
    btn_h = int(target_width * 0.14)
    bx = cx - btn_w // 2
    by = cy + 70
    draw.rounded_rectangle(
        [(bx, by), (bx + btn_w, by + btn_h)],
        radius=btn_h // 2,
        fill=(*accent_rgb, 255),
    )
    btn_text = "SUBSCRIBE"
    bb3 = draw.textbbox((0, 0), btn_text, font=font_sub)
    btw = bb3[2] - bb3[0]
    bth = bb3[3] - bb3[1]
    draw.text(
        (bx + (btn_w - btw) // 2, by + (btn_h - bth) // 2 - 4),
        btn_text,
        font=font_sub,
        fill=(255, 255, 255, 255),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")
    return output_path


def render_ending_card(
    target_width: int,
    target_height: int,
    output_path: Path,
    channel_name: str = "Subscribe Now!",
    font_candidates: list[str] | None = None,
    channel_key: str = "",
) -> Path:
    """하위호환용 래퍼 — render_branded_ending_card()를 사용합니다."""
    return render_branded_ending_card(
        target_width=target_width,
        target_height=target_height,
        output_path=output_path,
        channel_key=channel_key,
        font_candidates=font_candidates,
    )
