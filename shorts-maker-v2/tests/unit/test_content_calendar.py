"""content_calendar 헬퍼 함수 테스트."""

from shorts_maker_v2.utils.content_calendar import (
    _extract_date,
    _extract_select,
    _extract_title,
    _jaccard_similarity,
    _tokenize,
)


class TestExtractTitle:
    def test_normal(self):
        prop = {"title": [{"text": {"content": "Hello World"}}]}
        assert _extract_title(prop) == "Hello World"

    def test_empty_list(self):
        assert _extract_title({"title": []}) == ""

    def test_not_dict(self):
        assert _extract_title("not a dict") == ""

    def test_none_title(self):
        assert _extract_title({}) == ""

    def test_missing_text_key(self):
        prop = {"title": [{"no_text": True}]}
        assert _extract_title(prop) == ""


class TestExtractSelect:
    def test_normal(self):
        prop = {"select": {"name": "pending"}}
        assert _extract_select(prop) == "pending"

    def test_none_select(self):
        assert _extract_select({"select": None}) == ""

    def test_missing_key(self):
        assert _extract_select({}) == ""

    def test_select_no_name(self):
        assert _extract_select({"select": {"id": "x"}}) == ""


class TestExtractDate:
    def test_normal(self):
        prop = {"date": {"start": "2026-03-23"}}
        assert _extract_date(prop) == "2026-03-23"

    def test_none_date(self):
        assert _extract_date({"date": None}) == ""

    def test_missing_start(self):
        assert _extract_date({"date": {"end": "2026-04-01"}}) == ""

    def test_missing_key(self):
        assert _extract_date({}) == ""


class TestTokenize:
    def test_english(self):
        tokens = _tokenize("Hello World")
        assert "hello" in tokens
        assert "world" in tokens

    def test_korean(self):
        tokens = _tokenize("인공지능 기술")
        assert "인공지능" in tokens
        assert "기술" in tokens

    def test_mixed(self):
        tokens = _tokenize("AI 기술 revolution!")
        assert "ai" in tokens
        assert "기술" in tokens
        assert "revolution" in tokens

    def test_empty(self):
        assert _tokenize("") == set()

    def test_punctuation_stripped(self):
        tokens = _tokenize("hello! world?")
        assert "hello" in tokens
        assert "!" not in tokens


class TestJaccardSimilarity:
    def test_identical(self):
        assert _jaccard_similarity("hello world", "hello world") == 1.0

    def test_no_overlap(self):
        assert _jaccard_similarity("hello", "world") == 0.0

    def test_partial_overlap(self):
        sim = _jaccard_similarity("AI 기술 혁명", "AI 데이터 기술")
        assert 0.0 < sim < 1.0

    def test_empty_string(self):
        assert _jaccard_similarity("", "hello") == 0.0
        assert _jaccard_similarity("hello", "") == 0.0

    def test_both_empty(self):
        assert _jaccard_similarity("", "") == 0.0
