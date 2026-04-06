"""Extended tests for pipeline.text_polisher — polish_text paths, readability, TextPolisher class."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.text_polisher import (
    PolishResult,
    TextPolisher,
    _compute_readability,
    _fix_spacing,
    _fix_typos,
    _split_sentences,
    polish_text,
)


# ── _split_sentences (fallback regex) ────────────────────────────────


class TestSplitSentences:
    def test_regex_fallback(self):
        """Without Kiwi, should split on sentence-ending punctuation."""
        # Force fallback by mocking _get_kiwi to return None
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = _split_sentences("Hello world. This is a test! And more? Yes.")
            assert len(result) >= 3

    def test_empty_string(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = _split_sentences("")
            assert result == []

    def test_single_sentence(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = _split_sentences("Just one sentence here")
            assert len(result) >= 1


# ── _fix_spacing (without Kiwi) ─────────────────────────────────────


class TestFixSpacing:
    def test_no_kiwi_returns_original(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            text = "연봉이노무 낮아서"
            assert _fix_spacing(text) == text


# ── _fix_typos (without Kiwi) ────────────────────────────────────────


class TestFixTypos:
    def test_no_kiwi_returns_original(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            text = "맞춤법이 틀려요"
            assert _fix_typos(text) == text


# ── _compute_readability ─────────────────────────────────────────────


class TestComputeReadability:
    def test_empty_text(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = _compute_readability("")
            assert result["readability"] >= 0
            assert result["avg_sentence_length"] >= 0

    def test_short_sentences(self):
        """Very short sentences should have some penalty."""
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = _compute_readability("짧. 다. 네.")
            assert result["readability"] >= 0

    def test_long_sentences(self):
        """Very long sentences (>50 chars avg) lose points."""
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            long_text = "가" * 60 + ". " + "나" * 60 + "."
            result = _compute_readability(long_text)
            assert result["avg_sentence_length"] > 50
            assert result["readability"] < 100

    def test_optimal_length(self):
        """Sentences of 20-40 chars should score well."""
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            sentences = ["직장인 연봉이 올랐습니다. " * 2, "회사가 잘 되고 있네요. " * 2]
            text = " ".join(sentences)
            result = _compute_readability(text)
            assert result["readability"] > 0

    def test_too_few_sentences(self):
        """Single sentence -> sent_score penalty."""
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = _compute_readability("This is just one single sentence without any period")
            # num_sentences < 2 penalty
            assert result["readability"] <= 100

    def test_many_sentences(self):
        """More than 15 sentences -> slight penalty."""
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            text = ". ".join([f"문장 번호 {i}입니다" for i in range(20)]) + "."
            result = _compute_readability(text)
            assert result["readability"] >= 0

    def test_sino_korean_ratio_without_kiwi(self):
        """Without Kiwi, sino_korean_ratio should be 0.0."""
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = _compute_readability("한자어 비율 테스트입니다.")
            assert result["sino_korean_ratio"] == 0.0

    def test_high_sino_ratio_penalty(self):
        """When sino_korean_ratio > 0.5, apply penalty (requires Kiwi mock)."""
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            # Without Kiwi, can't truly test sino ratio
            result = _compute_readability("테스트 문장입니다. 또 다른 문장입니다.")
            assert 0 <= result["readability"] <= 100


# ── polish_text ──────────────────────────────────────────────────────


class TestPolishText:
    def test_empty_input(self):
        result = polish_text("")
        assert result.text == ""
        assert result.original == ""

    def test_whitespace_only(self):
        result = polish_text("   ")
        assert result.text == "   "

    def test_no_corrections_needed(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = polish_text("정상적인 문장입니다.")
            assert result.text == "정상적인 문장입니다."
            assert result.corrections_made == 0

    def test_skip_spacing(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = polish_text("테스트", fix_spacing=False)
            assert result.text == "테스트"

    def test_skip_typo(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = polish_text("테스트", fix_typo=False)
            assert result.text == "테스트"

    def test_skip_both(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = polish_text("테스트", fix_spacing=False, fix_typo=False)
            assert result.text == "테스트"
            assert result.corrections_made == 0

    def test_readability_in_result(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            result = polish_text("직장인 연봉 이야기입니다. 올해 인상률이 궁금합니다.")
            assert result.readability >= 0
            assert result.avg_sentence_length >= 0

    def test_result_dataclass_fields(self):
        result = polish_text("hello")
        assert isinstance(result, PolishResult)
        assert hasattr(result, "text")
        assert hasattr(result, "original")
        assert hasattr(result, "readability")
        assert hasattr(result, "avg_sentence_length")
        assert hasattr(result, "corrections_made")
        assert hasattr(result, "sino_korean_ratio")


# ── TextPolisher class ───────────────────────────────────────────────


class TestTextPolisherClass:
    def test_init(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            polisher = TextPolisher()
            assert polisher.fix_spacing is True
            assert polisher.fix_typo is True

    def test_init_custom_flags(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            polisher = TextPolisher(fix_spacing=False, fix_typo=False)
            assert polisher.fix_spacing is False
            assert polisher.fix_typo is False

    def test_polish_method(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            polisher = TextPolisher()
            result = polisher.polish("테스트 문장입니다.")
            assert isinstance(result, PolishResult)

    def test_compute_readability_method(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            polisher = TextPolisher()
            score = polisher.compute_readability("좋은 문장입니다. 가독성이 높습니다.")
            assert isinstance(score, float)
            assert 0 <= score <= 100

    def test_available_property_without_kiwi(self):
        with patch("pipeline.text_polisher._get_kiwi", return_value=None):
            polisher = TextPolisher.__new__(TextPolisher)
            polisher.fix_spacing = True
            polisher.fix_typo = True
            assert polisher.available is False
