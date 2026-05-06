import os
import shutil
from pathlib import Path

from PIL import Image

from shorts_maker_v2.render.caption_pillow import CaptionStyle, render_caption_image


def test_hook_caption_snapshot(tmp_path: Path) -> None:
    """
    Hook 자막(center_hook=False)의 시각적 스냅샷 테스트.
    안전 영역(Safe-zone) 하단 1/3 지점에 배치되는 방식을 검증하기 위해 실제 이미지 산출물을 생성.
    """
    # Arrange
    text = "실제 이미지 기반의 훅(Hook) 자막 테스트"
    output_path = tmp_path / "hook_snapshot.png"

    style = CaptionStyle(
        font_size=80,
        margin_x=50,
        bottom_offset=100,
        text_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=5,
        line_spacing=4,
        font_candidates=("arial.ttf",),
        min_lines=1,
        mode="karaoke",
        words_per_chunk=3,
        bg_color="#000000",
        bg_opacity=128,
        bg_radius=10,
        safe_zone_enabled=True,
        center_hook=False,
    )

    # Act
    res_path = render_caption_image(text=text, canvas_width=1080, style=style, output_path=output_path)

    # Assert
    assert res_path.exists()
    img = Image.open(res_path)
    assert img.size[0] > 0
    assert img.size[1] > 0

    # Save a copy to artifacts for visual QA
    os.makedirs(".tmp/snapshots", exist_ok=True)
    shutil.copy(res_path, ".tmp/snapshots/hook_snapshot.png")
