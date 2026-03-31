"""
test_karaoke_sync.py — Phase 2 word-level 자막 싱크 정밀도 테스트

검증 항목:
- sentence_boundary_chunks: 구두점 경계 기반 청크 분割
- apply_ssml_break_correction: SSML break offset 보정
- group_into_chunks: boundary_aware 옵션
- 엣지 케이스: 빈 목록, 단일 단어, 긴 단어 연속
"""

from __future__ import annotations

import pytest

from shorts_maker_v2.render.karaoke import (
    WordSegment,
    apply_ssml_break_correction,
    group_into_chunks,
    sentence_boundary_chunks,
)

# ── 픽스처 ──────────────────────────────────────────────────────────────────


def _w(word: str, start: float, end: float) -> WordSegment:
    return WordSegment(word=word, start=start, end=end)


@pytest.fixture
def simple_words() -> list[WordSegment]:
    """구두점 없는 5개 단어."""
    return [
        _w("안녕하세요", 0.0, 0.5),
        _w("저는", 0.6, 0.8),
        _w("라프입니다", 0.9, 1.4),
        _w("반갑습니다", 1.5, 2.0),
        _w("잘", 2.1, 2.3),
    ]


@pytest.fixture
def boundary_words() -> list[WordSegment]:
    """구두점이 포함된 단어 목록."""
    return [
        _w("안녕하세요,", 0.0, 0.5),
        _w("저는", 0.6, 0.8),
        _w("라프입니다.", 0.9, 1.4),
        _w("오늘은", 1.5, 1.8),
        _w("Phase", 1.9, 2.1),
        _w("2를", 2.2, 2.4),
        _w("구현합니다!", 2.5, 3.0),
    ]


# ── sentence_boundary_chunks 테스트 ──────────────────────────────────────────


class TestSentenceBoundaryChunks:
    def test_empty_returns_empty(self):
        assert sentence_boundary_chunks([]) == []

    def test_single_word(self):
        words = [_w("안녕", 0.0, 0.3)]
        chunks = sentence_boundary_chunks(words)
        assert len(chunks) == 1
        assert chunks[0][2] == "안녕"

    def test_boundary_at_comma(self, boundary_words):
        chunks = sentence_boundary_chunks(boundary_words, max_words=10)
        # 첫 청크는 "안녕하세요," 에서 끊어야 함
        assert chunks[0][2] == "안녕하세요,"

    def test_boundary_at_period(self, boundary_words):
        chunks = sentence_boundary_chunks(boundary_words, max_words=10)
        # 두 번째 청크는 "저는 라프입니다." 에서 끊어야 함
        assert "라프입니다." in chunks[1][2]

    def test_max_words_enforced(self, simple_words):
        chunks = sentence_boundary_chunks(simple_words, max_words=2)
        for _, _, text in chunks:
            assert len(text.split()) <= 2

    def test_timing_start_is_first_word(self, boundary_words):
        chunks = sentence_boundary_chunks(boundary_words)
        assert chunks[0][0] == boundary_words[0].start

    def test_timing_end_is_next_chunk_start(self, boundary_words):
        chunks = sentence_boundary_chunks(boundary_words, max_words=10)
        # 청크가 여러 개일 때 첫 번째 청크("안녕하세요,")의 end는
        # 다음 단어("저는", start=0.6)와 일치해야 함
        if len(chunks) > 1:
            assert chunks[0][1] == pytest.approx(0.6, abs=0.01)

    def test_no_empty_chunks(self, boundary_words):
        chunks = sentence_boundary_chunks(boundary_words)
        for _, _, text in chunks:
            assert text.strip() != ""

    def test_exclamation_boundary(self):
        words = [
            _w("충격적인!", 0.0, 0.5),
            _w("사실이", 0.6, 0.9),
            _w("있습니다", 1.0, 1.5),
        ]
        chunks = sentence_boundary_chunks(words, max_words=10)
        assert chunks[0][2] == "충격적인!"
        assert len(chunks) == 2  # "!!" 이후 두 번째 청크

    def test_korean_fullstop_boundary(self):
        words = [
            _w("네。", 0.0, 0.2),
            _w("알겠습니다", 0.3, 0.7),
        ]
        chunks = sentence_boundary_chunks(words, max_words=10)
        assert chunks[0][2] == "네。"


# ── apply_ssml_break_correction 테스트 ───────────────────────────────────────


class TestApplySsmlBreakCorrection:
    def test_no_break_tag_unchanged(self):
        words = [_w("안녕", 0.0, 0.3), _w("하세요", 0.4, 0.7)]
        corrected = apply_ssml_break_correction(words, "안녕 하세요")
        assert corrected is words  # 동일 객체 반환

    def test_300ms_break_applied(self):
        ssml = '<break time="300ms"/> 안녕하세요'
        words = [_w("안녕하세요", 0.0, 0.5)]  # break 미반영 (start=0)
        corrected = apply_ssml_break_correction(words, ssml)
        assert corrected[0].start == pytest.approx(0.3, abs=0.001)
        assert corrected[0].end == pytest.approx(0.8, abs=0.001)

    def test_already_reflected_unchanged(self):
        """EdgeTTS가 이미 break를 반영한 경우 보정 불필요."""
        ssml = '<break time="300ms"/> 라프입니다'
        # start=0.3 → 300ms의 80% 이상 → 이미 반영된 것으로 판단
        words = [_w("라프입니다", 0.3, 0.8)]
        corrected = apply_ssml_break_correction(words, ssml)
        assert corrected is words  # 보정 없음

    def test_1s_break_applied(self):
        ssml = '<break time="1s"/> 우주입니다'
        words = [_w("우주입니다", 0.0, 0.4)]
        corrected = apply_ssml_break_correction(words, ssml)
        assert corrected[0].start == pytest.approx(1.0, abs=0.001)

    def test_empty_words_unchanged(self):
        ssml = '<break time="300ms"/> 텍스트'
        corrected = apply_ssml_break_correction([], ssml)
        assert corrected == []

    def test_multiple_breaks_accumulated(self):
        """여러 break 태그의 합산이 보정됨."""
        ssml = '<break time="100ms"/><break time="200ms"/> 텍스트'
        words = [_w("텍스트", 0.0, 0.3)]
        corrected = apply_ssml_break_correction(words, ssml)
        # 100ms + 200ms = 0.3s
        assert corrected[0].start == pytest.approx(0.3, abs=0.001)

    def test_new_objects_returned(self):
        """보정 시 새 WordSegment 객체가 생성됨."""
        ssml = '<break time="200ms"/> 새 객체'
        words = [_w("새", 0.0, 0.2), _w("객체", 0.3, 0.5)]
        corrected = apply_ssml_break_correction(words, ssml)
        assert corrected is not words
        assert corrected[0] is not words[0]


# ── group_into_chunks 테스트 ──────────────────────────────────────────────────


class TestGroupIntoChunks:
    def test_boundary_aware_true_uses_boundary(self, boundary_words):
        chunks = group_into_chunks(boundary_words, chunk_size=4, boundary_aware=True)
        # 구두점에서 분리되므로 4개 이하 단어여도 경계에서 끊어짐
        texts = [c[2] for c in chunks]
        assert any("안녕하세요," in t for t in texts)

    def test_boundary_aware_false_uses_fixed(self, simple_words):
        chunks = group_into_chunks(simple_words, chunk_size=2, boundary_aware=False)
        # 정확히 2개씩 묶임
        for _, _, text in chunks[:-1]:
            assert len(text.split()) == 2

    def test_empty_returns_empty(self):
        assert group_into_chunks([], chunk_size=3) == []

    def test_single_word_single_chunk(self):
        words = [_w("단어", 0.0, 0.5)]
        chunks = group_into_chunks(words, chunk_size=3)
        assert len(chunks) == 1
        assert chunks[0][2] == "단어"

    def test_chunk_time_range_valid(self, simple_words):
        chunks = group_into_chunks(simple_words, chunk_size=2)
        for start, end, _ in chunks:
            assert start <= end
