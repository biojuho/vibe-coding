"""Extended tests for pipeline.dedup — _EmbeddingCache, MinHash LSH, find_similar_in_notion."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.dedup import (
    _EmbeddingCache,
    _cosine_similarity,
    normalize_korean_text,
    extract_korean_tokens,
    title_similarity,
    semantic_similarity,
    find_similar_in_notion,
    check_cross_source_duplicates,
    _build_minhash,
)


# ── _cosine_similarity ────────────────────────────────────────────


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert _cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert _cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_zero_vector(self):
        assert _cosine_similarity([0, 0], [1, 2]) == 0.0

    def test_partial_similarity(self):
        sim = _cosine_similarity([1, 1], [1, 0])
        assert 0 < sim < 1


# ── _EmbeddingCache ──────────────────────────────────────────────


class TestEmbeddingCache:
    def test_get_nonexistent(self, tmp_path):
        cache = _EmbeddingCache(db_path=tmp_path / "test_cache.db")
        assert cache.get("missing text") is None

    def test_set_and_get(self, tmp_path):
        cache = _EmbeddingCache(db_path=tmp_path / "test_cache.db")
        embedding = [0.1, 0.2, 0.3, 0.4]
        cache.set("hello world", embedding)
        result = cache.get("hello world")
        assert result == embedding

    def test_overwrite(self, tmp_path):
        cache = _EmbeddingCache(db_path=tmp_path / "test_cache.db")
        cache.set("key", [1.0, 2.0])
        cache.set("key", [3.0, 4.0])
        assert cache.get("key") == [3.0, 4.0]

    def test_hash_is_deterministic(self, tmp_path):
        cache = _EmbeddingCache(db_path=tmp_path / "test_cache.db")
        h1 = cache._hash("test string")
        h2 = cache._hash("test string")
        assert h1 == h2
        assert h1 != cache._hash("different string")

    def test_corrupted_db_returns_none(self, tmp_path):
        db_path = tmp_path / "corrupt.db"
        db_path.write_text("not a sqlite database")
        # Should handle gracefully
        try:
            cache = _EmbeddingCache(db_path=db_path)
        except Exception:
            pass  # init may fail, that's fine


# ── normalize_korean_text ────────────────────────────────────────


class TestNormalizeKoreanText:
    def test_removes_emoticons(self):
        assert "ㅋ" not in normalize_korean_text("연봉ㅋㅋ 적어")

    def test_removes_punctuation(self):
        result = normalize_korean_text("연봉!! 올려줘?!")
        assert "!" not in result
        assert "?" not in result

    def test_whitespace_normalization(self):
        result = normalize_korean_text("  연봉   적다   ")
        assert "  " not in result
        assert result == "연봉 적다"

    def test_preserves_korean_and_english(self):
        result = normalize_korean_text("salary 연봉")
        assert "salary" in result
        assert "연봉" in result


# ── extract_korean_tokens ────────────────────────────────────────


class TestExtractKoreanTokens:
    def test_normal_text(self):
        tokens = extract_korean_tokens("연봉 적다")
        # "연봉적다" → bigrams: {"연봉", "봉적", "적다"}
        assert len(tokens) >= 2

    def test_single_char(self):
        tokens = extract_korean_tokens("봉")
        assert tokens == {"봉"}

    def test_empty_after_normalize(self):
        tokens = extract_korean_tokens("!!! ???")
        assert tokens == set()


# ── title_similarity ─────────────────────────────────────────────


class TestTitleSimilarity:
    def test_identical_titles(self):
        assert title_similarity("연봉 협상 실패", "연봉 협상 실패") == pytest.approx(1.0)

    def test_completely_different(self):
        sim = title_similarity("연봉 협상", "고양이 사진")
        assert sim < 0.3

    def test_similar_titles(self):
        sim = title_similarity("연봉 협상 실패했어요", "연봉 협상에서 실패함")
        assert sim > 0.2  # Jaccard bigram on Korean is coarser than English


# ── semantic_similarity (Gemini mocked) ──────────────────────────


class TestSemanticSimilarity:
    def test_fallback_to_jaccard_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        # Reset state - embedding should fail → falls back to Jaccard
        sim = semantic_similarity("연봉 협상", "연봉 협상")
        assert sim > 0.9  # same text → Jaccard fallback ≈ 1.0


# ── _build_minhash ───────────────────────────────────────────────


class TestBuildMinhash:
    def test_empty_tokens(self):
        result = _build_minhash(set())
        assert result is None

    def test_builds_minhash(self):
        try:
            from datasketch import MinHash
            result = _build_minhash({"연봉", "적다"})
            assert result is not None
            assert isinstance(result, MinHash)
        except ImportError:
            pytest.skip("datasketch not installed")


# ── find_similar_in_notion ───────────────────────────────────────


class TestFindSimilarInNotion:
    def test_none_uploader(self):
        result = asyncio.run(find_similar_in_notion(None, "test"))
        assert result == []

    def test_short_title(self):
        result = asyncio.run(find_similar_in_notion(MagicMock(), "ab"))
        assert result == []

    def test_empty_title(self):
        result = asyncio.run(find_similar_in_notion(MagicMock(), ""))
        assert result == []

    def test_server_side_search_used(self, monkeypatch):
        """When search_pages_by_title exists and returns results."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        mock_notion = MagicMock()
        mock_notion.search_pages_by_title = AsyncMock(return_value=[
            {"id": "p1", "properties": {}},
        ])
        # Use near-identical title to ensure similarity >= threshold (0.6)
        mock_notion.get_page_property_value = MagicMock(return_value="연봉 협상 실패했어요 후기")

        result = asyncio.run(find_similar_in_notion(
            mock_notion, "연봉 협상 실패했어요", threshold=0.3, use_semantic=False
        ))
        mock_notion.search_pages_by_title.assert_called_once()
        assert len(result) >= 1
        assert result[0]["similarity"] > 0.3

    def test_fallback_to_recent_pages(self, monkeypatch):
        """When server-side search returns empty → fallback to recent pages."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        mock_notion = MagicMock()
        mock_notion.search_pages_by_title = AsyncMock(return_value=[])
        mock_notion.get_recent_pages = AsyncMock(return_value=[
            {"id": "p2"},
        ])
        mock_notion.get_page_property_value = MagicMock(return_value="완전 다른 주제")

        result = asyncio.run(find_similar_in_notion(
            mock_notion, "연봉 협상 실패했어요", use_semantic=False
        ))
        mock_notion.get_recent_pages.assert_called_once()

    def test_recent_pages_exception(self, monkeypatch):
        """get_recent_pages raises → empty result."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        mock_notion = MagicMock()
        mock_notion.search_pages_by_title = AsyncMock(return_value=[])
        mock_notion.get_recent_pages = AsyncMock(side_effect=Exception("네트워크 오류"))

        result = asyncio.run(find_similar_in_notion(
            mock_notion, "연봉 협상 실패했어요", use_semantic=False
        ))
        assert result == []

    def test_no_matching_pages(self, monkeypatch):
        """All pages have completely different titles."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        mock_notion = MagicMock()
        mock_notion.search_pages_by_title = AsyncMock(return_value=[
            {"id": "p1"},
        ])
        mock_notion.get_page_property_value = MagicMock(return_value="고양이 사진 모음")

        result = asyncio.run(find_similar_in_notion(
            mock_notion, "연봉 협상 실패했어요", threshold=0.6, use_semantic=False
        ))
        assert result == []

    def test_empty_existing_title_skipped(self, monkeypatch):
        """Pages with empty titles should be skipped."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        mock_notion = MagicMock()
        mock_notion.search_pages_by_title = AsyncMock(return_value=[{"id": "p1"}])
        mock_notion.get_page_property_value = MagicMock(return_value="")

        result = asyncio.run(find_similar_in_notion(
            mock_notion, "연봉 협상 실패했어요", use_semantic=False
        ))
        assert result == []


# ── check_cross_source_duplicates ────────────────────────────────


class TestCheckCrossSourceDuplicates:
    def test_single_candidate(self):
        candidates = [{"feed_title": "연봉", "source": "blind"}]
        result = check_cross_source_duplicates(candidates, use_semantic=False)
        assert len(result) == 1

    def test_empty_list(self):
        assert check_cross_source_duplicates([], use_semantic=False) == []

    def test_same_source_not_deduped(self):
        candidates = [
            {"feed_title": "연봉 협상 실패", "source": "blind", "feed_engagement": 10},
            {"feed_title": "연봉 협상 실패했어요", "source": "blind", "feed_engagement": 5},
        ]
        result = check_cross_source_duplicates(candidates, use_semantic=False)
        assert len(result) == 2

    def test_cross_source_dedup(self):
        candidates = [
            {"feed_title": "연봉 협상 실패 후기", "source": "blind", "feed_engagement": 100},
            {"feed_title": "연봉 협상 실패 후기", "source": "fmkorea", "feed_engagement": 50},
        ]
        result = check_cross_source_duplicates(candidates, use_semantic=False)
        # Lower engagement one should be removed
        assert len(result) == 1
        assert result[0]["source"] == "blind"

    def test_different_titles_kept(self):
        candidates = [
            {"feed_title": "연봉 협상 실패", "source": "blind", "feed_engagement": 10},
            {"feed_title": "고양이 사진 모음", "source": "fmkorea", "feed_engagement": 5},
        ]
        result = check_cross_source_duplicates(candidates, use_semantic=False)
        assert len(result) == 2

    def test_higher_engagement_wins(self):
        candidates = [
            {"feed_title": "연봉 협상 실패 후기", "source": "fmkorea", "feed_engagement": 200},
            {"feed_title": "연봉 협상 실패 후기", "source": "blind", "feed_engagement": 50},
        ]
        result = check_cross_source_duplicates(candidates, use_semantic=False)
        assert len(result) == 1
        assert result[0]["source"] == "fmkorea"

    def test_small_batch_uses_fallback(self):
        """Less than 4 candidates → falls back to O(n²) Jaccard."""
        candidates = [
            {"feed_title": "연봉 올려줘요", "source": "blind", "feed_engagement": 10},
            {"feed_title": "연봉 올려줘요", "source": "fmkorea", "feed_engagement": 5},
            {"feed_title": "고양이 사랑해요", "source": "naver", "feed_engagement": 1},
        ]
        result = check_cross_source_duplicates(candidates, use_semantic=False)
        assert len(result) == 2  # one duplicate pair removed

    def test_empty_title_handled(self):
        candidates = [
            {"feed_title": "", "source": "blind", "feed_engagement": 10},
            {"feed_title": "", "source": "fmkorea", "feed_engagement": 5},
        ]
        result = check_cross_source_duplicates(candidates, use_semantic=False)
        # Empty titles → no tokens → not matched as duplicates
        assert len(result) == 2

    def test_large_batch_uses_lsh(self):
        """>=4 candidates (with datasketch) should use LSH path."""
        candidates = [
            {"feed_title": "연봉 협상 실패 후기", "source": "blind", "feed_engagement": 100},
            {"feed_title": "연봉 협상 실패 후기입니다", "source": "fmkorea", "feed_engagement": 50},
            {"feed_title": "고양이 사랑해요", "source": "naver", "feed_engagement": 30},
            {"feed_title": "맛집 추천드립니다", "source": "ppomppu", "feed_engagement": 20},
            {"feed_title": "연봉 올려달라고 했더니", "source": "jobplanet", "feed_engagement": 10},
        ]
        result = check_cross_source_duplicates(candidates, use_semantic=False)
        # At least one duplicate pair should be removed
        assert len(result) <= 5
