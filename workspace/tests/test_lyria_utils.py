"""lyria_bgm_generator 유틸리티 함수 테스트."""

from pathlib import Path

from execution.lyria_bgm_generator import _build_output_path, _slugify


class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World") == "hello-world"

    def test_korean(self):
        result = _slugify("따뜻한 피아노")
        assert "따뜻한" in result

    def test_special_chars_removed(self):
        result = _slugify("ambient!@#$%techno")
        assert "!" not in result
        assert "techno" in result

    def test_long_string_truncated(self):
        result = _slugify("a" * 100)
        assert len(result) <= 48

    def test_empty_uses_fallback(self):
        assert _slugify("!!!") == "lyria-bgm"

    def test_custom_fallback(self):
        assert _slugify("!!!", fallback="custom") == "custom"

    def test_whitespace_collapsed(self):
        result = _slugify("  hello   world  ")
        assert result == "hello-world"


class TestBuildOutputPath:
    def test_wav_format(self, tmp_path: Path):
        path = _build_output_path("warm piano", tmp_path, "wav")
        assert path.suffix == ".wav"
        assert path.parent == tmp_path
        assert "warm-piano" in path.stem

    def test_mp3_format(self, tmp_path: Path):
        path = _build_output_path("techno beat", tmp_path, "mp3")
        assert path.suffix == ".mp3"
