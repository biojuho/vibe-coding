"""Tests for pipeline.text_polisher."""

import pytest
from unittest.mock import MagicMock, patch

from pipeline.text_polisher import (
    TextPolisher,
    polish_text,
    _compute_readability,
    _fix_spacing,
    _fix_typos,
    _split_sentences,
)
import pipeline.text_polisher as tp

@pytest.fixture(autouse=True)
def reset_kiwi_state():
    """Reset global kiwi state before each test."""
    tp._kiwi_instance = None
    tp._kiwi_load_attempted = False
    yield
    tp._kiwi_instance = None
    tp._kiwi_load_attempted = False

def test_get_kiwi_fallback():
    with patch("pipeline.text_polisher.kiwipiepy", None, create=True):
        # Even if kiwipiepy isn't there, it shouldn't crash
        # Actually importing kiwipiepy will raise ImportError
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "kiwipiepy":
                raise ImportError("mocked no kiwi")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            kiwi = tp._get_kiwi()
            assert kiwi is None
            assert tp._kiwi_load_attempted is True

def test_split_sentences_fallback():
    with patch("pipeline.text_polisher._get_kiwi", return_value=None):
        sents = _split_sentences("안녕하세요. 반갑습니다! 내일 봐요.")
        assert len(sents) == 3
        assert sents[0] == "안녕하세요."
        assert sents[1] == "반갑습니다!"
        assert sents[2] == "내일 봐요."

def test_fix_spacing_fallback():
    with patch("pipeline.text_polisher._get_kiwi", return_value=None):
        res = _fix_spacing("안녕 하세요")
        assert res == "안녕 하세요"  # No change without kiwi

def test_fix_typos_fallback():
    with patch("pipeline.text_polisher._get_kiwi", return_value=None):
        res = _fix_typos("오랫만이야")
        assert res == "오랫만이야"  # No change

def test_compute_readability_fallback():
    with patch("pipeline.text_polisher._get_kiwi", return_value=None):
        res = _compute_readability("안녕하세요. 좋은 아침입니다.")
        assert "readability" in res
        assert "avg_sentence_length" in res
        assert res["avg_sentence_length"] > 0
        assert res["sino_korean_ratio"] == 0.0

def test_polish_text_empty():
    res = polish_text("   ")
    assert res.text == "   "
    assert res.original == "   "

def test_text_polisher_class():
    with patch("pipeline.text_polisher._get_kiwi", return_value=None):
        polisher = TextPolisher()
        assert not polisher.available
        res = polisher.polish("테스트입니다.")
        assert res.original == "테스트입니다."
        assert polisher.compute_readability("안녕") > 0

@patch("pipeline.text_polisher._get_kiwi")
def test_kiwi_available_path(mock_get_kiwi):
    mock_kiwi = MagicMock()
    mock_get_kiwi.return_value = mock_kiwi

    # Mock split_into_sents
    mock_sent1, mock_sent2 = MagicMock(), MagicMock()
    mock_sent1.text = "안녕."
    mock_sent2.text = "잘가."
    mock_kiwi.split_into_sents.return_value = [mock_sent1, mock_sent2]

    # Mock space
    mock_kiwi.space.return_value = "안녕. 잘 가."

    # Mock tokenize for typo and readability
    mock_token1 = MagicMock()
    mock_token1.form = "안녕"
    mock_token1.tag = "NNG"
    mock_token2 = MagicMock()
    mock_token2.form = "."
    mock_token2.tag = "SF"
    mock_kiwi.tokenize.return_value = [mock_token1, mock_token2]

    # Mock join
    mock_kiwi.join.return_value = "안녕. 잘가."

    polisher = TextPolisher()
    assert polisher.available is True

    result = polisher.polish("안녕.잘가.")
    assert result.corrections_made > 0
    assert result.sino_korean_ratio == 1.0  # 1 out of 1 NNGs is >= 2 chars
