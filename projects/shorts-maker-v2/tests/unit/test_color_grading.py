"""color_grading.py 유닛 테스트."""

from __future__ import annotations

import numpy as np
import pytest

from shorts_maker_v2.render.color_grading import (
    COLOR_PROFILES,
    ROLE_ADJUSTMENTS,
    _build_vignette_mask,
    _grade_inplace,
    _resolve_profile,
    apply_color_grade,
    apply_vignette,
    color_grade_clip,
)

# ── COLOR_PROFILES / ROLE_ADJUSTMENTS ────────────────────────────────────────


class TestColorProfiles:
    def test_all_channels_defined(self):
        expected = {"ai_tech", "psychology", "history", "medical", "space", "default"}
        assert expected.issubset(COLOR_PROFILES.keys())

    def test_each_profile_has_required_keys(self):
        required = {"brightness", "contrast", "saturation", "tint", "vignette_strength"}
        for name, profile in COLOR_PROFILES.items():
            missing = required - profile.keys()
            assert not missing, f"{name} missing keys: {missing}"

    def test_tint_is_3_tuple(self):
        for name, profile in COLOR_PROFILES.items():
            tint = profile["tint"]
            assert len(tint) == 3, f"{name} tint is not a 3-tuple"

    def test_vignette_strength_in_range(self):
        for name, profile in COLOR_PROFILES.items():
            v = profile["vignette_strength"]
            assert 0.0 <= v <= 1.0, f"{name} vignette_strength {v} out of range"

    def test_role_adjustments_keys(self):
        assert "hook" in ROLE_ADJUSTMENTS
        assert "body" in ROLE_ADJUSTMENTS
        assert "cta" in ROLE_ADJUSTMENTS

    def test_body_role_is_empty(self):
        assert ROLE_ADJUSTMENTS["body"] == {}


# ── apply_color_grade ─────────────────────────────────────────────────────────


class TestApplyColorGrade:
    @pytest.fixture
    def sample_frame(self):
        """128x128 중간 회색 프레임."""
        return np.full((128, 128, 3), 128, dtype=np.uint8)

    def test_returns_uint8(self, sample_frame):
        result = apply_color_grade(sample_frame)
        assert result.dtype == np.uint8

    def test_returns_same_shape(self, sample_frame):
        result = apply_color_grade(sample_frame)
        assert result.shape == sample_frame.shape

    def test_default_channel_applies(self, sample_frame):
        result = apply_color_grade(sample_frame, channel_key="default")
        assert result.shape == sample_frame.shape

    def test_unknown_channel_falls_back_to_default(self, sample_frame):
        result_unknown = apply_color_grade(sample_frame, channel_key="nonexistent")
        result_default = apply_color_grade(sample_frame, channel_key="default")
        np.testing.assert_array_equal(result_unknown, result_default)

    def test_all_channel_keys_work(self, sample_frame):
        for key in COLOR_PROFILES:
            result = apply_color_grade(sample_frame, channel_key=key)
            assert result.dtype == np.uint8

    def test_all_roles_work(self, sample_frame):
        for role in ["hook", "body", "cta", "intro", "outro"]:
            result = apply_color_grade(sample_frame, role=role)
            assert result.shape == sample_frame.shape

    def test_brightness_effect(self):
        """밝기 증가 → 결과값이 더 밝아야 함."""
        frame = np.full((64, 64, 3), 100, dtype=np.uint8)
        bright = apply_color_grade(
            frame, override={"brightness": 1.3, "contrast": 1.0, "saturation": 1.0, "tint": (0, 0, 0)}
        )
        dark = apply_color_grade(
            frame, override={"brightness": 0.7, "contrast": 1.0, "saturation": 1.0, "tint": (0, 0, 0)}
        )
        assert bright.mean() > dark.mean()

    def test_output_clipped_0_255(self, sample_frame):
        """결과값은 항상 0~255 범위."""
        result = apply_color_grade(sample_frame, channel_key="space")
        assert result.min() >= 0
        assert result.max() <= 255

    def test_tint_shifts_channel(self):
        """파란 틴트 → B 채널 증가."""
        frame = np.full((32, 32, 3), 100, dtype=np.uint8)
        result = apply_color_grade(
            frame,
            override={
                "brightness": 1.0,
                "contrast": 1.0,
                "saturation": 1.0,
                "tint": (0, 0, 30),
                "vignette_strength": 0.0,
            },
        )
        # B 채널이 R 채널보다 높아야 함
        assert result[:, :, 2].mean() > result[:, :, 0].mean()

    def test_override_applied(self, sample_frame):
        """override 딕셔너리가 프로파일을 덮어씀."""
        result_default = apply_color_grade(sample_frame, channel_key="ai_tech")
        result_override = apply_color_grade(sample_frame, channel_key="ai_tech", override={"brightness": 2.0})
        # brightness 2.0이 적용되므로 더 밝아야 함
        assert result_override.mean() > result_default.mean()

    def test_hook_role_increases_contrast(self):
        """hook 역할 → 대비 증가."""
        frame = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
        result_body = apply_color_grade(frame, channel_key="default", role="body")
        result_hook = apply_color_grade(frame, channel_key="default", role="hook")
        # hook은 contrast 배율이 높으므로 표준편차가 더 커야 함
        assert result_hook.std() >= result_body.std() - 1  # 허용 오차 1


# ── apply_vignette ────────────────────────────────────────────────────────────


class TestApplyVignette:
    @pytest.fixture
    def white_frame(self):
        return np.full((200, 200, 3), 255, dtype=np.uint8)

    def test_returns_uint8(self, white_frame):
        result = apply_vignette(white_frame, strength=0.5)
        assert result.dtype == np.uint8

    def test_zero_strength_returns_same(self, white_frame):
        result = apply_vignette(white_frame, strength=0.0)
        np.testing.assert_array_equal(result, white_frame)

    def test_edges_darker_than_center(self, white_frame):
        """비네트: 가장자리가 중심보다 어두워야 함."""
        result = apply_vignette(white_frame, strength=0.8)
        h, w = result.shape[:2]
        center_val = result[h // 2, w // 2, :].mean()
        corner_val = result[0, 0, :].mean()
        assert center_val > corner_val

    def test_shape_preserved(self, white_frame):
        result = apply_vignette(white_frame, strength=0.5)
        assert result.shape == white_frame.shape

    def test_output_clipped(self, white_frame):
        result = apply_vignette(white_frame, strength=1.0)
        assert result.min() >= 0
        assert result.max() <= 255

    def test_cache_hit(self):
        """같은 크기+강도 → 같은 마스크 객체 반환."""
        _build_vignette_mask.cache_clear()
        m1 = _build_vignette_mask(100, 200, 0.3)
        m2 = _build_vignette_mask(100, 200, 0.3)
        assert m1 is m2  # lru_cache 히트

    def test_different_sizes_different_masks(self):
        m1 = _build_vignette_mask(100, 200, 0.3)
        m2 = _build_vignette_mask(200, 100, 0.3)
        assert m1 is not m2

    def test_mask_shape(self):
        mask = _build_vignette_mask(80, 60, 0.5)
        # (H, W, 1) 브로드캐스트용
        assert mask.shape == (60, 80, 1)


# ── color_grade_clip ──────────────────────────────────────────────────────────


class TestColorGradeClip:
    def test_returns_transformed_clip(self):
        """color_grade_clip이 clip.transform()을 호출해야 함."""
        from unittest.mock import MagicMock

        mock_clip = MagicMock()
        mock_clip.transform.return_value = mock_clip

        result = color_grade_clip(mock_clip, channel_key="ai_tech", role="hook")

        mock_clip.transform.assert_called_once()
        assert result is mock_clip

    def test_transform_function_processes_frame(self):
        """transform에 전달된 함수가 실제로 프레임을 변환하는지."""
        from unittest.mock import MagicMock

        mock_clip = MagicMock()
        captured_fn = {}

        def capture_transform(fn):
            captured_fn["fn"] = fn
            return mock_clip

        mock_clip.transform.side_effect = capture_transform
        color_grade_clip(mock_clip, channel_key="default", role="body")

        # 캡처된 함수로 실제 프레임 변환 테스트
        frame = np.full((64, 64, 3), 128, dtype=np.uint8)

        def get_frame(t):
            return frame

        result = captured_fn["fn"](get_frame, 0.0)
        assert result.shape == (64, 64, 3)
        assert result.dtype == np.uint8


# ── _grade_inplace fused-pass optimization (T-333) ────────────────────────────


def _reference_grade(result: np.ndarray, profile: dict) -> None:
    """Naive, pre-optimization reference: one array op per step.

    `_grade_inplace` fuses brightness+contrast into a single affine and
    collapses saturation/tint passes for speed (render hot path). This
    reference locks in that the fused result stays mathematically identical.
    """
    brightness = float(profile.get("brightness", 1.0))
    if brightness != 1.0:
        result *= brightness
    contrast = float(profile.get("contrast", 1.0))
    if contrast != 1.0:
        mean = result.mean()
        result[:] = (result - mean) * contrast + mean
    saturation = float(profile.get("saturation", 1.0))
    if saturation != 1.0:
        gray = (result[:, :, 0] * 0.299 + result[:, :, 1] * 0.587 + result[:, :, 2] * 0.114)[:, :, np.newaxis]
        result[:] = gray + (result - gray) * saturation
    tint = profile.get("tint", (0, 0, 0))
    if any(t != 0 for t in tint):
        result[:, :, 0] += tint[0]
        result[:, :, 1] += tint[1]
        result[:, :, 2] += tint[2]


class TestGradeInplaceOptimization:
    def test_matches_naive_reference_all_profiles(self):
        """Fused _grade_inplace must match the naive per-step reference."""
        rng = np.random.default_rng(42)
        for channel_key in COLOR_PROFILES:
            for role in ("hook", "body", "cta"):
                profile = _resolve_profile(channel_key, role, None)
                frame = (rng.random((96, 72, 3)) * 255).astype(np.uint8)

                expected = frame.astype(np.float32)
                _reference_grade(expected, profile)

                actual = frame.astype(np.float32)
                _grade_inplace(actual, profile)

                max_diff = float(np.abs(expected - actual).max())
                assert max_diff < 0.01, (
                    f"{channel_key}/{role}: fused grade diverged from reference by {max_diff}"
                )

    def test_operates_in_place(self):
        """_grade_inplace must mutate the passed array, not return a copy."""
        profile = _resolve_profile("ai_tech", "body", None)
        frame = np.full((32, 32, 3), 100, dtype=np.float32)
        original_id = id(frame)
        _grade_inplace(frame, profile)
        assert id(frame) == original_id
        # ai_tech darkens (brightness 0.95) → mean should drop from 100
        assert frame.mean() != 100.0
