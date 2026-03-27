"""
test_visual_regression.py — 비주얼 리그레션 테스트 프레임워크
===========================================================
엔진별 렌더링 결과를 베이스라인과 비교하여
시각적 변경 사항(리그레션)을 자동 감지합니다.

작동 방식:
1. 최초 실행 시 골든 이미지(baseline)를 생성하여 .tmp/baselines/ 에 저장
2. 이후 실행 시 새 렌더링 vs 베이스라인의 SSIM/PSNR을 비교
3. 임계값 이하면 테스트 실패 (regression detected)

사용법:
    pytest tests/unit/test_visual_regression.py -v
    pytest tests/unit/test_visual_regression.py --update-baselines  # 베이스라인 갱신
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── 설정 ──────────────────────────────────────────────────────────────

_BASELINE_DIR = Path(__file__).resolve().parents[2] / ".tmp" / "visual_baselines"
_CHANNEL_CONFIG = {
    "palette": {
        "bg": "#0A0E1A",
        "primary": "#00D4FF",
        "accent": "#00FF88",
        "secondary": "#7C3AED",
    },
    "font_title": "Pretendard-ExtraBold",
    "font_body": "Pretendard-Regular",
    "hook_style": "popup",
    "keyword_highlights": {"numbers": "#FFD700"},
}

# SSIM 유사도 임계값 (0.0~1.0, 1.0 = 완전 동일)
_SSIM_THRESHOLD = 0.85


# ── SSIM 계산 (scikit-image 없이) ─────────────────────────────────────


def compute_ssim(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """두 이미지 간 Structural Similarity Index (SSIM) 계산.

    간소화된 구현: 전체 이미지에 대한 단일 SSIM 값.
    실제 SSIM과 근사하지만 window 기반이 아닌 글로벌 계산.

    Args:
        img_a: 첫 번째 이미지 (numpy array, uint8).
        img_b: 두 번째 이미지 (numpy array, uint8).

    Returns:
        SSIM 값 (0.0~1.0).
    """
    if img_a.shape != img_b.shape:
        # 크기 다르면 리사이즈
        from PIL import Image as _Img

        b = _Img.fromarray(img_b).resize((img_a.shape[1], img_a.shape[0]), _Img.LANCZOS)
        img_b = np.array(b)

    a = img_a.astype(np.float64)
    b = img_b.astype(np.float64)

    # 상수 (8비트 기준)
    L = 255.0
    k1, k2 = 0.01, 0.03
    c1 = (k1 * L) ** 2
    c2 = (k2 * L) ** 2

    mu_a = np.mean(a)
    mu_b = np.mean(b)
    sigma_a_sq = np.var(a)
    sigma_b_sq = np.var(b)
    sigma_ab = np.mean((a - mu_a) * (b - mu_b))

    numerator = (2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)
    denominator = (mu_a**2 + mu_b**2 + c1) * (sigma_a_sq + sigma_b_sq + c2)

    return float(numerator / denominator)


def compute_psnr(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """Peak Signal-to-Noise Ratio (PSNR) 계산.

    Args:
        img_a: 첫 번째 이미지.
        img_b: 두 번째 이미지.

    Returns:
        PSNR (dB). 무한대면 동일 이미지.
    """
    if img_a.shape != img_b.shape:
        from PIL import Image as _Img

        b = _Img.fromarray(img_b).resize((img_a.shape[1], img_a.shape[0]), _Img.LANCZOS)
        img_b = np.array(b)

    mse = np.mean((img_a.astype(np.float64) - img_b.astype(np.float64)) ** 2)
    if mse == 0:
        return float("inf")
    return float(10.0 * np.log10(255.0**2 / mse))


# ── 베이스라인 관리 ──────────────────────────────────────────────────


def _get_baseline_path(test_name: str) -> Path:
    """테스트 이름으로 베이스라인 경로 생성."""
    return _BASELINE_DIR / f"{test_name}.png"


def _get_metadata_path() -> Path:
    """베이스라인 메타데이터 파일 경로."""
    return _BASELINE_DIR / "metadata.json"


def _load_metadata() -> dict:
    """베이스라인 메타데이터 로드."""
    path = _get_metadata_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_metadata(metadata: dict) -> None:
    """베이스라인 메타데이터 저장."""
    path = _get_metadata_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def _save_baseline(test_name: str, image: Image.Image) -> None:
    """베이스라인 이미지 저장."""
    path = _get_baseline_path(test_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")

    # 메타데이터 업데이트
    metadata = _load_metadata()
    arr = np.array(image)
    metadata[test_name] = {
        "size": list(image.size),
        "mode": image.mode,
        "checksum": hashlib.md5(arr.tobytes()).hexdigest(),
    }
    _save_metadata(metadata)


def _compare_with_baseline(
    test_name: str,
    current: Image.Image,
    threshold: float = _SSIM_THRESHOLD,
) -> tuple[bool, float, float]:
    """현재 이미지를 베이스라인과 비교.

    Returns:
        (passed, ssim_value, psnr_value)
    """
    baseline_path = _get_baseline_path(test_name)

    if not baseline_path.exists():
        # 베이스라인 없으면 새로 생성
        _save_baseline(test_name, current)
        return True, 1.0, float("inf")

    baseline = Image.open(baseline_path)
    arr_current = np.array(current.convert("RGB"))
    arr_baseline = np.array(baseline.convert("RGB"))

    ssim = compute_ssim(arr_current, arr_baseline)
    psnr = compute_psnr(arr_current, arr_baseline)

    return ssim >= threshold, ssim, psnr


# ── 테스트 클래스 ─────────────────────────────────────────────────────


class TestVisualRegressionTextEngine:
    """TextEngine 비주얼 리그레션 테스트."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.text_engine import TextEngine

        return TextEngine(_CHANNEL_CONFIG)

    def test_subtitle_body_regression(self, engine, tmp_path):
        """body 자막 렌더링 리그레션 체크."""
        output = tmp_path / "body_subtitle.png"
        engine.render_subtitle("테스트 자막입니다", role="body", output_path=output)
        img = Image.open(output)
        passed, ssim, psnr = _compare_with_baseline("text_body_subtitle", img)
        assert passed, f"Visual regression! SSIM={ssim:.4f} (threshold={_SSIM_THRESHOLD})"

    def test_subtitle_hook_regression(self, engine, tmp_path):
        """hook 자막 렌더링 리그레션 체크."""
        output = tmp_path / "hook_subtitle.png"
        engine.render_subtitle("주목!", role="hook", output_path=output)
        img = Image.open(output)
        passed, ssim, psnr = _compare_with_baseline("text_hook_subtitle", img)
        assert passed, f"Visual regression! SSIM={ssim:.4f}"

    def test_badge_regression(self, engine, tmp_path):
        """배지 렌더링 리그레션 체크."""
        output = tmp_path / "badge.png"
        engine.render_badge(5, output_path=output)
        img = Image.open(output)
        passed, ssim, psnr = _compare_with_baseline("text_badge_5", img)
        assert passed, f"Visual regression! SSIM={ssim:.4f}"

    def test_glow_regression(self, engine, tmp_path):
        """글로우 자막 리그레션 체크."""
        output = tmp_path / "glow.png"
        engine.render_subtitle_with_glow("네온 효과", output_path=output)
        img = Image.open(output)
        passed, ssim, psnr = _compare_with_baseline("text_glow", img)
        assert passed, f"Visual regression! SSIM={ssim:.4f}"


class TestVisualRegressionBackgroundEngine:
    """BackgroundEngine 비주얼 리그레션 테스트."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.background_engine import BackgroundEngine

        return BackgroundEngine(_CHANNEL_CONFIG)

    def test_gradient_vertical_regression(self, engine, tmp_path):
        """세로 그라데이션 리그레션 체크."""
        output = tmp_path / "grad_v.png"
        engine.create_gradient(200, 300, direction="vertical", output_path=output)
        img = Image.open(output)
        passed, ssim, psnr = _compare_with_baseline("bg_gradient_vertical", img)
        assert passed, f"Visual regression! SSIM={ssim:.4f}"

    def test_gradient_radial_regression(self, engine, tmp_path):
        """방사형 그라데이션 리그레션 체크."""
        output = tmp_path / "grad_r.png"
        engine.create_gradient(200, 300, direction="radial", output_path=output)
        img = Image.open(output)
        passed, ssim, psnr = _compare_with_baseline("bg_gradient_radial", img)
        assert passed, f"Visual regression! SSIM={ssim:.4f}"

    def test_grid_overlay_regression(self, engine, tmp_path):
        """그리드 오버레이 리그레션 체크."""
        output = tmp_path / "grid.png"
        engine.create_grid_overlay(200, 200, output_path=output)
        img = Image.open(output)
        passed, ssim, psnr = _compare_with_baseline("bg_grid_overlay", img)
        assert passed, f"Visual regression! SSIM={ssim:.4f}"


class TestVisualRegressionLayoutEngine:
    """LayoutEngine 비주얼 리그레션 테스트."""

    @pytest.fixture
    def engine(self):
        from ShortsFactory.engines.layout_engine import LayoutEngine

        return LayoutEngine(_CHANNEL_CONFIG)

    def test_split_screen_regression(self, engine, tmp_path):
        """분할 화면 리그레션 체크."""
        output = tmp_path / "split.png"
        engine.split_screen("좋은 것", "나쁜 것", output_path=output)
        img = Image.open(output)
        passed, ssim, psnr = _compare_with_baseline("layout_split_screen", img)
        assert passed, f"Visual regression! SSIM={ssim:.4f}"

    def test_card_layout_regression(self, engine, tmp_path):
        """카드 레이아웃 리그레션 체크."""
        output = tmp_path / "cards.png"
        items = [
            {"title": "항목 1", "body": "설명 텍스트 1"},
            {"title": "항목 2", "body": "설명 텍스트 2"},
        ]
        engine.card_layout(items, output_path=output)
        img = Image.open(output)
        passed, ssim, psnr = _compare_with_baseline("layout_cards", img)
        assert passed, f"Visual regression! SSIM={ssim:.4f}"
