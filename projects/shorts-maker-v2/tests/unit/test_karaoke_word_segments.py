from __future__ import annotations

import pytest

from shorts_maker_v2.render.karaoke import (
    WordSegment,
    apply_ssml_break_correction,
    group_word_segments,
)


def _w(word: str, start: float, end: float) -> WordSegment:
    return WordSegment(word=word, start=start, end=end)


def test_group_word_segments_preserves_irregular_timing() -> None:
    words = [
        _w("GPT", 0.00, 0.18),
        _w("API", 0.22, 0.51),
        _w("출시", 0.95, 1.42),
        _w("임박", 1.46, 1.82),
    ]

    chunks = group_word_segments(words, chunk_size=2, boundary_aware=False)

    assert len(chunks) == 2
    first_chunk_words = chunks[0][3]
    second_chunk_words = chunks[1][3]
    assert [(w.word, w.start, w.end) for w in first_chunk_words] == [
        ("GPT", 0.00, 0.18),
        ("API", 0.22, 0.51),
    ]
    assert [(w.word, w.start, w.end) for w in second_chunk_words] == [
        ("출시", 0.95, 1.42),
        ("임박", 1.46, 1.82),
    ]
    assert chunks[0][0] == pytest.approx(0.00, abs=0.001)
    assert chunks[0][1] == pytest.approx(0.95, abs=0.001)
    assert chunks[0][2] == "GPT API"
    assert chunks[1][0] == pytest.approx(0.95, abs=0.001)
    assert chunks[1][1] == pytest.approx(1.82, abs=0.001)
    assert chunks[1][2] == "출시 임박"


def test_group_word_segments_keeps_boundary_aware_end_at_next_chunk_start() -> None:
    words = [
        _w("심리학,", 0.00, 0.30),
        _w("테스트", 0.31, 0.72),
        _w("시작", 0.90, 1.30),
    ]

    chunks = group_word_segments(words, chunk_size=3, boundary_aware=True)

    assert len(chunks) == 2
    assert chunks[0][0] == pytest.approx(0.00, abs=0.001)
    assert chunks[0][1] == pytest.approx(0.31, abs=0.001)
    assert chunks[0][2] == "심리학,"
    assert [w.word for w in chunks[0][3]] == ["심리학,"]


def test_ssml_break_correction_flows_into_group_word_segments() -> None:
    raw_words = [
        _w("GPT", 0.00, 0.20),
        _w("벤치마크", 0.24, 0.70),
    ]
    corrected = apply_ssml_break_correction(raw_words, '<break time="400ms"/> GPT 벤치마크')
    chunks = group_word_segments(corrected, chunk_size=2, boundary_aware=False)

    assert corrected[0].start == pytest.approx(0.40, abs=0.001)
    assert corrected[1].start == pytest.approx(0.64, abs=0.001)
    assert chunks[0][0] == pytest.approx(0.40, abs=0.001)
    assert chunks[0][1] == pytest.approx(0.70 + 0.40, abs=0.001)
