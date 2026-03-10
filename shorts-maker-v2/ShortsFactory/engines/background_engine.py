"""
background_engine.py — 배경/파티클 엔진
========================================
채널 palette 기반 그라데이션 배경과 파티클 오버레이를 생성합니다.

독립 사용:
    from ShortsFactory.engines.background_engine import BackgroundEngine
    engine = BackgroundEngine(channel_config)
    bg_path = engine.create_gradient(1080, 1920)
"""

from __future__ import annotations

import logging
import math
import random
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class BackgroundEngine:
    """채널 palette 기반 배경/파티클 생성 엔진.

    Args:
        channel_config: channels.yaml에서 읽은 채널 설정 dict.
    """

    def __init__(self, channel_config: dict[str, Any]) -> None:
        self.config = channel_config
        self.palette = channel_config.get("palette", {})

    # ── 공개 메서드 ─────────────────────────────────────────────────────

    def create_gradient(
        self,
        width: int = 1080,
        height: int = 1920,
        *,
        output_path: Path | None = None,
        direction: str = "vertical",
    ) -> Path:
        """palette의 bg → primary 그라데이션 배경 이미지를 생성합니다.

        Args:
            width: 이미지 너비.
            height: 이미지 높이.
            output_path: 출력 경로 (None이면 임시 파일).
            direction: "vertical" 또는 "radial".

        Returns:
            생성된 이미지 경로.
        """
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        bg_color = self._hex_to_rgb(self.palette.get("bg", "#000000"))
        primary = self._hex_to_rgb(self.palette.get("primary", "#FFFFFF"))

        arr = np.zeros((height, width, 3), dtype=np.uint8)

        if direction == "radial":
            cx, cy = width // 2, height // 2
            max_r = math.sqrt(cx ** 2 + cy ** 2)
            y_grid, x_grid = np.mgrid[0:height, 0:width]
            dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2) / max_r
            dist = np.clip(dist, 0, 1)
            for c in range(3):
                arr[:, :, c] = (
                    primary[c] * (1 - dist) + bg_color[c] * dist
                ).astype(np.uint8)
        else:  # vertical
            for c in range(3):
                arr[:, :, c] = np.linspace(
                    bg_color[c], primary[c] * 0.3 + bg_color[c] * 0.7, height
                ).reshape(-1, 1).astype(np.uint8)

        image = Image.fromarray(arr, "RGB")
        image.save(output_path, format="PNG")
        logger.debug("[BackgroundEngine] 그라데이션 생성: %s", output_path.name)
        return output_path

    def create_particle_overlay(
        self,
        width: int = 1080,
        height: int = 1920,
        *,
        num_particles: int = 30,
        output_path: Path | None = None,
    ) -> Path:
        """파티클 오버레이 이미지(PNG, RGBA)를 생성합니다.

        Args:
            width: 이미지 너비.
            height: 이미지 높이.
            num_particles: 파티클 수.
            output_path: 출력 경로.

        Returns:
            생성된 파티클 오버레이 이미지 경로.
        """
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        accent = self._hex_to_rgb(self.palette.get("accent", "#FFFFFF"))
        primary = self._hex_to_rgb(self.palette.get("primary", "#FFFFFF"))

        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        for _ in range(num_particles):
            x = random.randint(0, width)
            y = random.randint(0, height)
            radius = random.randint(2, 8)
            alpha = random.randint(40, 120)
            color = accent if random.random() > 0.5 else primary
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=(*color, alpha),
            )

        image.save(output_path, format="PNG")
        logger.debug("[BackgroundEngine] 파티클 생성: %d개", num_particles)
        return output_path

    def create_grid_overlay(
        self,
        width: int = 1080,
        height: int = 1920,
        *,
        grid_spacing: int = 60,
        line_width: int = 1,
        opacity: float = 0.05,
        line_color: str = "#FFFFFF",
        output_path: Path | None = None,
    ) -> Path:
        """미세한 그리드 패턴 오버레이(RGBA)를 생성합니다.

        사이버펑크/하이테크 느낌의 배경 그리드입니다.

        Args:
            width: 이미지 너비.
            height: 이미지 높이.
            grid_spacing: 그리드 라인 간격 (px).
            line_width: 라인 두께.
            opacity: 라인 불투명도 (0.0~1.0).
            line_color: 라인 색상 (#RRGGBB).
            output_path: 출력 경로 (None이면 임시 파일).

        Returns:
            생성된 그리드 오버레이 이미지 경로.
        """
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rgb = self._hex_to_rgb(line_color)
        alpha = max(0, min(255, int(255 * opacity)))

        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 세로선
        for x in range(0, width, grid_spacing):
            draw.line([(x, 0), (x, height)], fill=(*rgb, alpha), width=line_width)
        # 가로선
        for y in range(0, height, grid_spacing):
            draw.line([(0, y), (width, y)], fill=(*rgb, alpha), width=line_width)

        image.save(output_path, format="PNG")
        logger.debug(
            "[BackgroundEngine] 그리드 오버레이 생성: spacing=%d, opacity=%.0f%%",
            grid_spacing, opacity * 100,
        )
        return output_path

    def create_gradient_shift_frames(
        self,
        width: int = 1080,
        height: int = 1920,
        *,
        color_start: str | None = None,
        color_end: str = "#1a0a2e",
        num_frames: int = 90,
        fps: int = 30,
        output_dir: Path | None = None,
    ) -> list[Path]:
        """그라데이션 쉬프트 프레임 시퀀스를 생성합니다.

        CTA 배경의 bg→color_end 그라데이션 전환 애니메이션용입니다.

        Args:
            width: 이미지 너비.
            height: 이미지 높이.
            color_start: 시작 색상 (None이면 palette bg 사용).
            color_end: 종료 색상.
            num_frames: 프레임 수 (fps × duration).
            fps: 초당 프레임 수.
            output_dir: 프레임 출력 디렉토리.

        Returns:
            프레임 이미지 경로 리스트.
        """
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="gradient_shift_"))
        output_dir.mkdir(parents=True, exist_ok=True)

        start_rgb = self._hex_to_rgb(color_start or self.palette.get("bg", "#0A0E1A"))
        end_rgb = self._hex_to_rgb(color_end)

        paths: list[Path] = []
        for i in range(num_frames):
            t = i / max(num_frames - 1, 1)
            # 부드러운 ease-in-out 보간
            t_smooth = t * t * (3 - 2 * t)

            mid_rgb = tuple(
                int(start_rgb[c] * (1 - t_smooth) + end_rgb[c] * t_smooth)
                for c in range(3)
            )

            arr = np.zeros((height, width, 3), dtype=np.uint8)
            for c in range(3):
                arr[:, :, c] = np.linspace(
                    start_rgb[c] * (1 - t_smooth) + mid_rgb[c] * t_smooth,
                    mid_rgb[c],
                    height,
                ).reshape(-1, 1).astype(np.uint8)

            frame_path = output_dir / f"grad_{i:04d}.png"
            Image.fromarray(arr, "RGB").save(frame_path, format="PNG")
            paths.append(frame_path)

        logger.debug(
            "[BackgroundEngine] 그라데이션 쉬프트 %d프레임 생성", num_frames,
        )
        return paths

    def create_animated_particle_frames(
        self,
        width: int = 1080,
        height: int = 1920,
        *,
        num_particles: int = 25,
        num_frames: int = 30,
        speed: int = 1,
        colors: list[str] | None = None,
        size_range: tuple[int, int] = (2, 8),
        density_multiplier: float = 1.0,
        bg_color: str | None = None,
        output_dir: Path | None = None,
    ) -> list[Path]:
        """느린 상승 파티클 애니메이션 프레임 시퀀스를 생성합니다.

        각 프레임마다 파티클들이 y좌표 -speed px 이동하며,
        화면 밖으로 나가면 하단에서 재생성됩니다.

        Args:
            width: 이미지 너비.
            height: 이미지 높이.
            num_particles: 파티클 수기본값.
            num_frames: 프레임 수 (fps × duration).
            speed: 프레임당 상승 속도 (px).
            colors: 파티클 색상 리스트 (None이면 palette primary/secondary).
            size_range: 파티클 반경 범위 (min, max).
            density_multiplier: 밀도 배율 (1위 효과: 3.0).
            bg_color: 배경색 (None이면 palette bg).
            output_dir: 프레임 출력 디렉토리.

        Returns:
            프레임 이미지 경로 리스트.
        """
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="particles_anim_"))
        output_dir.mkdir(parents=True, exist_ok=True)

        actual_count = int(num_particles * density_multiplier)
        bg_rgb = self._hex_to_rgb(bg_color or self.palette.get("bg", "#0B0D21"))

        if colors is None:
            colors = [
                self.palette.get("primary", "#00D4FF"),
                self.palette.get("secondary", "#7C3AED"),
            ]
        color_rgbs = [self._hex_to_rgb(c) for c in colors]

        # 파티클 초기 상태 생성
        particles = []
        for _ in range(actual_count):
            particles.append({
                "x": random.randint(0, width),
                "y": random.randint(0, height),
                "r": random.randint(size_range[0], size_range[1]),
                "alpha": random.randint(60, 180),
                "color": random.choice(color_rgbs),
                "speed": random.uniform(speed * 0.5, speed * 1.5),
            })

        paths: list[Path] = []
        for frame_idx in range(num_frames):
            image = Image.new("RGBA", (width, height), (*bg_rgb, 255))
            draw = ImageDraw.Draw(image)

            for p in particles:
                # 그리기
                x, y, r = int(p["x"]), int(p["y"]), p["r"]
                draw.ellipse(
                    [x - r, y - r, x + r, y + r],
                    fill=(*p["color"], p["alpha"]),
                )

                # 이동 (상승)
                p["y"] -= p["speed"]

                # 화면 밖으로 나가면 하단에서 재생성
                if p["y"] + p["r"] < 0:
                    p["y"] = height + random.randint(0, 50)
                    p["x"] = random.randint(0, width)
                    p["r"] = random.randint(size_range[0], size_range[1])
                    p["alpha"] = random.randint(60, 180)
                    p["color"] = random.choice(color_rgbs)

            frame_path = output_dir / f"particle_{frame_idx:04d}.png"
            image.save(frame_path, format="PNG")
            paths.append(frame_path)

        logger.debug(
            "[BackgroundEngine] 애니메이션 파티클 %d프레임 (%d개 파티클)",
            num_frames, actual_count,
        )
        return paths

    def create_blurred_bg(
        self,
        image_path: str | Path,
        width: int = 1080,
        height: int = 1920,
        *,
        blur_sigma: int = 25,
        brightness: float = 0.3,
        output_path: Path | None = None,
    ) -> Path:
        """이미지를 블러 + 어둡게 처리하여 배경으로 사용합니다.

        카운트다운 항목의 배경 이미지용입니다.

        Args:
            image_path: 원본 이미지 경로.
            width: 출력 너비.
            height: 출력 높이.
            blur_sigma: 가우시안 블러 시그마.
            brightness: 밝기 배율 (0.0~1.0).
            output_path: 출력 경로.

        Returns:
            생성된 배경 이미지 경로.
        """
        from PIL import ImageFilter as _IF, ImageEnhance

        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            img = Image.open(str(image_path)).convert("RGB")
        except Exception:
            # 이미지 로드 실패 시 단색 배경
            bg_rgb = self._hex_to_rgb(self.palette.get("bg", "#0B0D21"))
            img = Image.new("RGB", (width, height), bg_rgb)

        # 리사이즈 (커버)
        img_ratio = img.width / img.height
        target_ratio = width / height
        if img_ratio > target_ratio:
            new_h = height
            new_w = int(height * img_ratio)
        else:
            new_w = width
            new_h = int(width / img_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        # 중앙 크롭
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        img = img.crop((left, top, left + width, top + height))

        # 블러
        img = img.filter(_IF.GaussianBlur(radius=blur_sigma))

        # 밝기 조절
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)

        img.save(output_path, format="PNG")
        logger.debug("[BackgroundEngine] 블러 배경 생성: sigma=%d, brightness=%.1f", blur_sigma, brightness)
        return output_path

    # ── 내부 메서드 ─────────────────────────────────────────────────────

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return (0, 0, 0)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
