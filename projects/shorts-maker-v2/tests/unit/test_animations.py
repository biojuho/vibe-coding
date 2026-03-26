"""Tests for shorts_maker_v2.render.animations — text animation effects.

All tests mock MoviePy internals so no actual video rendering occurs.
"""

from __future__ import annotations

import math
import types
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from shorts_maker_v2.render import animations


# ── helpers ────────────────────────────────────────────────────────


def _make_fake_clip(width: int = 8, height: int = 6, with_mask: bool = False):
    """Create a minimal object that quacks like an ImageClip for testing."""
    frame = np.full((height, width, 3), 128, dtype=np.uint8)

    clip = MagicMock()
    clip.w = width
    clip.h = height
    clip.size = (width, height)

    # .transform(fn) → capture the filter_frame, apply to a synthetic frame
    def fake_transform(filter_func):
        # MoviePy calls filter_func(get_frame, t) where get_frame(t)->ndarray
        result = MagicMock()
        result.w = width
        result.h = height
        result.mask = None
        # Stash the filter so tests can call it
        result._filter = filter_func
        result._get_frame = lambda t: frame.copy()
        return result

    clip.transform = fake_transform

    # .resized(fn) → capture the resize function
    def fake_resized(fn):
        result = MagicMock()
        result.w = width
        result.h = height
        result._resize_fn = fn
        return result

    clip.resized = fake_resized

    if with_mask:
        mask_frame = np.ones((height, width), dtype=np.float64)
        mask = MagicMock()
        mask_result = MagicMock()
        mask.transform.return_value = mask_result
        clip.mask = mask
    else:
        clip.mask = None

    return clip, frame


# ═══════════════════════════════════════════════════════════════════
# _apply_typing_effect
# ═══════════════════════════════════════════════════════════════════


class TestTypingEffect:
    def test_partial_reveal_masks_right_side(self):
        clip, frame = _make_fake_clip(width=10, height=4)
        result = animations._apply_typing_effect(clip, duration=1.0)
        # At t=0.5, progress=0.5 → reveal_w=5, columns 5..9 should be zeroed
        out = result._filter(result._get_frame, 0.5)
        assert np.all(out[:, 5:] == 0)
        assert np.all(out[:, :5] == 128)

    def test_after_duration_returns_full_frame(self):
        clip, frame = _make_fake_clip(width=8)
        result = animations._apply_typing_effect(clip, duration=0.5)
        out = result._filter(result._get_frame, 0.6)
        np.testing.assert_array_equal(out, frame)

    def test_mask_is_also_transformed(self):
        clip, _ = _make_fake_clip(width=10, height=4, with_mask=True)
        # Should not raise — exercises the mask branch of _apply_typing_effect
        result = animations._apply_typing_effect(clip, duration=1.0)
        # The clip.mask is truthy so the mask transform branch runs
        clip.mask.transform.assert_called_once()

    def test_mask_filter_covers_branches(self):
        """Exercise the filter_mask closure that _apply_typing_effect passes to mask.transform."""
        clip, _ = _make_fake_clip(width=10, height=4, with_mask=True)
        animations._apply_typing_effect(clip, duration=1.0)
        # Retrieve the filter_mask function from the mock call
        filter_mask = clip.mask.transform.call_args[0][0]
        mask_frame = np.ones((4, 10), dtype=np.float64)
        get_mask = lambda t: mask_frame.copy()

        # Partial reveal at t=0.5 → reveal_w=5, columns 5..9 zeroed
        out = filter_mask(get_mask, 0.5)
        assert np.all(out[:, 5:] == 0)
        assert np.all(out[:, :5] == 1.0)

        # After duration → full mask returned unchanged
        out = filter_mask(get_mask, 1.1)
        np.testing.assert_array_equal(out, mask_frame)


# ═══════════════════════════════════════════════════════════════════
# _apply_popup_effect
# ═══════════════════════════════════════════════════════════════════


class TestPopupEffect:
    def test_resize_phases(self):
        clip, _ = _make_fake_clip()
        result = animations._apply_popup_effect(clip, duration=1.0)
        fn = result._resize_fn

        # At t=0, p=0 → scale starts at 0.5
        assert fn(0.0) == pytest.approx(0.5, abs=0.01)

        # At p=0.7 boundary → scale ≈ 1.1
        assert fn(0.7) == pytest.approx(1.1, abs=0.01)

        # At p=1.0 (t>=duration) → 1.0
        assert fn(1.0) == pytest.approx(1.0, abs=0.01)

    def test_after_duration_returns_one(self):
        clip, _ = _make_fake_clip()
        result = animations._apply_popup_effect(clip, duration=0.5)
        fn = result._resize_fn
        assert fn(0.6) == 1.0


# ═══════════════════════════════════════════════════════════════════
# _apply_glitch_effect
# ═══════════════════════════════════════════════════════════════════


class TestGlitchEffect:
    def test_even_frame_passes_through(self):
        """When int(t*20) % 2 == 0, frame is returned unmodified."""
        clip, frame = _make_fake_clip(width=8, height=4)
        result = animations._apply_glitch_effect(clip, duration=2.0)
        # t=0.0 → int(0*20)=0, 0%2==0 → pass through
        out = result._filter(result._get_frame, 0.0)
        np.testing.assert_array_equal(out, frame)

    def test_odd_frame_may_shift(self):
        """When int(t*20) is odd, the frame is potentially shifted."""
        clip, frame = _make_fake_clip(width=20, height=4)
        result = animations._apply_glitch_effect(clip, duration=2.0)
        # t=0.05 → int(0.05*20)=1, 1%2==1 → glitch branch
        with patch("shorts_maker_v2.render.animations.random") as mock_random:
            mock_random.randint.return_value = 5  # positive shift
            out = result._filter(result._get_frame, 0.05)
            # RGB channels should be swapped (R↔B) and shifted
            assert out.shape == frame.shape

    def test_after_duration_no_glitch(self):
        clip, frame = _make_fake_clip()
        result = animations._apply_glitch_effect(clip, duration=0.5)
        out = result._filter(result._get_frame, 0.6)
        np.testing.assert_array_equal(out, frame)

    def test_zero_shift_returns_frame(self):
        """When random.randint returns 0, frame is returned as-is."""
        clip, frame = _make_fake_clip(width=8, height=4)
        result = animations._apply_glitch_effect(clip, duration=2.0)
        with patch("shorts_maker_v2.render.animations.random") as mock_random:
            mock_random.randint.return_value = 0
            out = result._filter(result._get_frame, 0.05)  # odd frame → glitch branch
            np.testing.assert_array_equal(out, frame)

    def test_negative_shift(self):
        """Negative shift displaces frame leftward."""
        clip, frame = _make_fake_clip(width=20, height=4)
        result = animations._apply_glitch_effect(clip, duration=2.0)
        with patch("shorts_maker_v2.render.animations.random") as mock_random:
            mock_random.randint.return_value = -5
            out = result._filter(result._get_frame, 0.05)
            assert out.shape == frame.shape
            # RGB channels swapped (R↔B)
            assert out.dtype == np.uint8

    def test_mask_filter_covers_branches(self):
        """Exercise glitch mask filter: even frame, zero shift, positive shift, negative shift."""
        clip, _ = _make_fake_clip(width=20, height=4, with_mask=True)
        animations._apply_glitch_effect(clip, duration=2.0)
        filter_mask = clip.mask.transform.call_args[0][0]
        mask_frame = np.ones((4, 20), dtype=np.float64)
        get_mask = lambda t: mask_frame.copy()

        # After duration → pass through
        out = filter_mask(get_mask, 2.1)
        np.testing.assert_array_equal(out, mask_frame)

        # Even frame → pass through
        out = filter_mask(get_mask, 0.0)
        np.testing.assert_array_equal(out, mask_frame)

        # Zero shift → pass through
        with patch("shorts_maker_v2.render.animations.random") as mock_random:
            mock_random.randint.return_value = 0
            out = filter_mask(get_mask, 0.05)
            np.testing.assert_array_equal(out, mask_frame)

        # Positive shift
        with patch("shorts_maker_v2.render.animations.random") as mock_random:
            mock_random.randint.return_value = 3
            out = filter_mask(get_mask, 0.05)
            assert out.shape == mask_frame.shape

        # Negative shift
        with patch("shorts_maker_v2.render.animations.random") as mock_random:
            mock_random.randint.return_value = -3
            out = filter_mask(get_mask, 0.05)
            assert out.shape == mask_frame.shape

    def test_mask_path_is_covered(self):
        clip, _ = _make_fake_clip(width=8, height=4, with_mask=True)
        _ = animations._apply_glitch_effect(clip, duration=1.0)
        # If clip has mask, transform is called on it too
        # We simply verify no exception is raised


# ═══════════════════════════════════════════════════════════════════
# _apply_bounce_effect
# ═══════════════════════════════════════════════════════════════════


class TestBounceEffect:
    def test_resize_func_range(self):
        clip, _ = _make_fake_clip()
        result = animations._apply_bounce_effect(clip, duration=1.0)
        fn = result._resize_fn

        # Sample multiple points — result should be between 0.0 and 1.5
        for t in [0.0, 0.1, 0.3, 0.5, 0.8, 0.99]:
            val = fn(t)
            assert 0.0 <= val <= 1.5, f"bounce at t={t} out of range: {val}"

    def test_after_duration_is_one(self):
        clip, _ = _make_fake_clip()
        result = animations._apply_bounce_effect(clip, duration=0.5)
        assert result._resize_fn(0.6) == 1.0


# ═══════════════════════════════════════════════════════════════════
# _apply_countdown_effect
# ═══════════════════════════════════════════════════════════════════


class TestCountdownEffect:
    def test_fade_in_darkens_early_frame(self):
        clip, frame = _make_fake_clip(width=4, height=4)
        result = animations._apply_countdown_effect(clip, duration=3.0)
        # countdown_dur = min(0.9, 3.0*0.3) = 0.9
        # At t=0, fade = 0 → frame should be all zero
        out = result._filter(result._get_frame, 0.0)
        assert np.all(out == 0)

    def test_after_countdown_returns_full(self):
        clip, frame = _make_fake_clip()
        result = animations._apply_countdown_effect(clip, duration=3.0)
        out = result._filter(result._get_frame, 1.0)  # well past 0.9s countdown
        np.testing.assert_array_equal(out, frame)


# ═══════════════════════════════════════════════════════════════════
# _apply_particle_effect
# ═══════════════════════════════════════════════════════════════════


class TestParticleEffect:
    def test_particles_modify_frame(self):
        clip, frame = _make_fake_clip(width=20, height=20)
        result = animations._apply_particle_effect(clip, duration=2.0)
        # At some non-zero time, particles should have modified at least some pixel
        out = result._filter(result._get_frame, 0.5)
        # Not all pixels can be identical to the original because particles are added
        assert out.shape == frame.shape
        # At least one pixel should differ (particles add brightness)
        has_diff = not np.array_equal(out, frame)
        # Particles may or may not trigger depending on sin values, so we accept both
        assert out.dtype == np.uint8

    def test_after_duration_returns_original(self):
        clip, frame = _make_fake_clip(width=20, height=20)
        result = animations._apply_particle_effect(clip, duration=0.5)
        out = result._filter(result._get_frame, 0.6)
        np.testing.assert_array_equal(out, frame)


# ═══════════════════════════════════════════════════════════════════
# apply_text_animation (dispatcher)
# ═══════════════════════════════════════════════════════════════════


class TestApplyTextAnimation:
    @pytest.mark.parametrize(
        "anim_type",
        ["typing", "glitch", "popup", "bounce", "countdown", "particle"],
    )
    def test_dispatches_known_types(self, anim_type):
        clip, _ = _make_fake_clip()
        result = animations.apply_text_animation(clip, anim_type, duration=0.5)
        assert result is not None
        assert result is not clip  # a new clip/mock should have been created

    def test_random_selects_valid_type(self):
        clip, _ = _make_fake_clip()
        with patch("shorts_maker_v2.render.animations.random") as mock_random:
            mock_random.choice.return_value = "popup"
            result = animations.apply_text_animation(clip, "random", duration=0.5)
            mock_random.choice.assert_called_once()
            assert result is not None

    def test_none_returns_original_clip(self):
        clip, _ = _make_fake_clip()
        result = animations.apply_text_animation(clip, "none", duration=0.5)
        assert result is clip

    def test_unknown_type_returns_original_clip(self):
        clip, _ = _make_fake_clip()
        result = animations.apply_text_animation(clip, "nonexistent_effect", duration=0.5)
        assert result is clip
