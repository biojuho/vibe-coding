"""HUD 오버레이 유닛 테스트."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from shorts_maker_v2.render.hud_overlay import render_hud_overlay


def test_hud_overlay_returns_rgba_image() -> None:
    """HUD 오버레이 이미지가 RGBA 모드로 생성되는지 확인."""
    img = render_hud_overlay(target_width=1080, target_height=1920)
    assert img.mode == "RGBA"
    assert img.size == (1080, 1920)


def test_hud_overlay_saves_to_file(tmp_path: Path) -> None:
    """HUD 오버레이 이미지가 파일로 정상 저장되는지 확인."""
    output = tmp_path / "hud.png"
    img = render_hud_overlay(
        target_width=1080,
        target_height=1920,
        output_path=output,
        opacity=100,
    )
    assert output.exists()
    assert output.stat().st_size > 0
    loaded = Image.open(output)
    assert loaded.mode == "RGBA"
    assert loaded.size == (1080, 1920)


def test_hud_overlay_has_transparency() -> None:
    """HUD 오버레이가 완전 불투명이 아님 (반투명 요소 존재 확인)."""
    img = render_hud_overlay(target_width=540, target_height=960, opacity=80)
    # 전체 투명 픽셀이 10% 이상 있어야 함 (대부분 배경이 투명)
    alpha_data = list(img.split()[3].getdata())
    transparent_count = sum(1 for a in alpha_data if a == 0)
    total = len(alpha_data)
    assert transparent_count / total > 0.5, "HUD는 배경 대부분이 투명해야 합니다"


def test_hud_overlay_custom_size() -> None:
    """다양한 해상도에서 정상 작동."""
    for w, h in [(720, 1280), (1080, 1920), (540, 960)]:
        img = render_hud_overlay(target_width=w, target_height=h)
        assert img.size == (w, h)
