from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageFont


def rgba_array_to_image(array: np.ndarray) -> Image.Image:
    return Image.fromarray(array)


def rgb_array_to_rgba_image(array: np.ndarray) -> Image.Image:
    return Image.fromarray(array).convert("RGBA")


def font_search_dirs() -> tuple[Path, ...]:
    return (Path("C:/Windows/Fonts"), Path(os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts")))


def find_font_path(names: list[str], fallback: str = "malgun.ttf") -> str:
    dirs = font_search_dirs()
    for directory in dirs:
        for name in names:
            if (directory / name).exists():
                return str(directory / name)
    for directory in dirs:
        if (directory / fallback).exists():
            return str(directory / fallback)
    return ""


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.truetype(path, size) if path else ImageFont.load_default(size)
