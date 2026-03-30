"""render_step 유틸리티/static 메서드 테스트.

MoviePy 클립은 mock으로 대체합니다.
"""

from pathlib import Path
from unittest.mock import MagicMock

from shorts_maker_v2.pipeline.render_step import RenderStep


class TestCollectBgmFiles:
    def test_empty_dir(self, tmp_path: Path):
        files = RenderStep._collect_bgm_files(tmp_path)
        assert files == []

    def test_collects_audio_formats(self, tmp_path: Path):
        (tmp_path / "bgm1.mp3").write_bytes(b"data")
        (tmp_path / "bgm2.wav").write_bytes(b"data")
        (tmp_path / "bgm3.m4a").write_bytes(b"data")
        (tmp_path / "bgm4.aac").write_bytes(b"data")
        (tmp_path / "not_audio.txt").write_bytes(b"data")
        files = RenderStep._collect_bgm_files(tmp_path)
        assert len(files) == 4
        assert all(f.suffix in (".mp3", ".wav", ".m4a", ".aac") for f in files)

    def test_sorted_output(self, tmp_path: Path):
        (tmp_path / "z.mp3").write_bytes(b"data")
        (tmp_path / "a.mp3").write_bytes(b"data")
        files = RenderStep._collect_bgm_files(tmp_path)
        assert files[0].name == "a.mp3"
        assert files[1].name == "z.mp3"


class TestFitVertical:
    def test_landscape_to_vertical(self):
        clip = MagicMock()
        clip.w = 1920
        clip.h = 1080
        resized = MagicMock()
        resized.w = 1920
        resized.h = 1080
        clip.resized.return_value = resized
        cropped = MagicMock()
        resized.cropped.return_value = cropped

        result = RenderStep._fit_vertical(clip, 1080, 1920)
        clip.resized.assert_called_once()
        resized.cropped.assert_called_once()
        assert result is cropped

    def test_square_to_vertical(self):
        clip = MagicMock()
        clip.w = 1000
        clip.h = 1000
        resized = MagicMock()
        resized.w = 1920
        resized.h = 1920
        clip.resized.return_value = resized
        cropped = MagicMock()
        resized.cropped.return_value = cropped

        result = RenderStep._fit_vertical(clip, 1080, 1920)
        assert result is cropped


class TestLoadChannelProfile:
    def test_unknown_channel_returns_dict(self):
        profile = RenderStep._load_channel_profile("nonexistent_xyz")
        assert isinstance(profile, dict)

    def test_known_channel(self):
        profile = RenderStep._load_channel_profile("ai_tech")
        # Should return a dict (may be empty or populated depending on config)
        assert isinstance(profile, dict)


class TestCaptionComboRotation:
    def test_combos_exist(self):
        assert len(RenderStep._CAPTION_COMBOS) >= 3

    def test_each_combo_is_4_tuple(self):
        for combo in RenderStep._CAPTION_COMBOS:
            assert len(combo) == 4
            assert all(isinstance(s, str) for s in combo)


class TestChannelStyleTuning:
    def test_ai_tech_exists(self):
        assert "ai_tech" in RenderStep._CHANNEL_STYLE_TUNING

    def test_has_expected_keys(self):
        for _channel, tuning in RenderStep._CHANNEL_STYLE_TUNING.items():
            assert isinstance(tuning, dict)
            # At least margin_x should exist
            assert "margin_x" in tuning


class TestQualityProfiles:
    def test_draft_profile(self):
        from shorts_maker_v2.pipeline.render_step import _QUALITY_PROFILES

        assert "draft" in _QUALITY_PROFILES
        assert _QUALITY_PROFILES["draft"]["crf"] == 28

    def test_premium_profile(self):
        from shorts_maker_v2.pipeline.render_step import _QUALITY_PROFILES

        assert "premium" in _QUALITY_PROFILES
        assert _QUALITY_PROFILES["premium"]["crf"] < _QUALITY_PROFILES["draft"]["crf"]

    def test_standard_profile(self):
        from shorts_maker_v2.pipeline.render_step import _QUALITY_PROFILES

        assert "standard" in _QUALITY_PROFILES
