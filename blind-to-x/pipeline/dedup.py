"""Content deduplication with title similarity and cross-source detection.

Dedup layers (applied in order):
1. URL exact match (O(1), via Notion URL cache)
2. MinHash LSH 근사 중복 탐지 (datasketch, O(n) — fallback: Jaccard bigram O(n²))
3. [Optional] Gemini gemini-embedding-001 semantic similarity (Threshold 0.82)

Semantic dedup catches cases Jaccard misses, e.g.:
  "직장인 월급 현실" vs "회사원 급여 실태" (same meaning, different words)
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

try:
    from datasketch import MinHash, MinHashLSH
    _HAS_DATASKETCH = True
except ImportError:
    _HAS_DATASKETCH = False

logger = logging.getLogger(__name__)

# ── Embedding cache (SQLite, persistent across runs) ────────────────

_EMBED_CACHE_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "embedding_cache.db"


class _EmbeddingCache:
    """Lightweight SQLite cache for Gemini text embeddings."""

    def __init__(self, db_path: Path = _EMBED_CACHE_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _conn(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    text_hash TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> list[float] | None:
        h = self._hash(text)
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT embedding FROM embeddings WHERE text_hash = ?", (h,)
                ).fetchone()
            if row is None:
                return None
            import json
            return json.loads(row[0])
        except Exception:
            return None

    def set(self, text: str, embedding: list[float]) -> None:
        h = self._hash(text)
        try:
            import json
            with self._conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings (text_hash, embedding) VALUES (?, ?)",
                    (h, json.dumps(embedding)),
                )
        except Exception:
            pass


_embed_cache = _EmbeddingCache()


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Cosine similarity between two dense vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def _get_gemini_embedding(text: str) -> list[float] | None:
    """Compute Gemini gemini-embedding-001 for text. Returns None on failure."""
    # Check cache first
    cached = _embed_cache.get(text)
    if cached is not None:
        return cached

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        result = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text,
        )
        embedding = result.embeddings[0].values
        _embed_cache.set(text, embedding)
        return embedding
    except Exception as exc:
        logger.debug("Gemini embedding failed (Jaccard fallback): %s", exc)
        return None

    return None


def semantic_similarity(title_a: str, title_b: str) -> float:
    """Semantic similarity via Gemini embedding (falls back to Jaccard on error)."""
    emb_a = _get_gemini_embedding(normalize_korean_text(title_a))
    emb_b = _get_gemini_embedding(normalize_korean_text(title_b))
    if emb_a is not None and emb_b is not None:
        return _cosine_similarity(emb_a, emb_b)
    # Graceful fallback
    return title_similarity(title_a, title_b)


def normalize_korean_text(text: str) -> str:
    """Normalize Korean text for comparison."""
    text = text.lower().strip()
    text = re.sub(r'[ㅋㅎㅠㅜㄷㅂㅅㅈ]+', '', text)  # emoticons
    text = re.sub(r'[^\w가-힣a-z0-9\s]', '', text)  # punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_korean_tokens(text: str) -> set[str]:
    """Extract character bigram tokens for Jaccard similarity."""
    normalized = normalize_korean_text(text)
    if not normalized:
        return set()
    chars = normalized.replace(' ', '')
    if len(chars) < 2:
        return {chars}
    return {chars[i:i + 2] for i in range(len(chars) - 1)}


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity coefficient between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def title_similarity(title_a: str, title_b: str) -> float:
    """Compute similarity between two titles using character bigram Jaccard."""
    tokens_a = extract_korean_tokens(title_a)
    tokens_b = extract_korean_tokens(title_b)
    return jaccard_similarity(tokens_a, tokens_b)


async def find_similar_in_notion(
    notion_uploader,
    title: str,
    threshold: float = 0.6,
    lookback_days: int = 14,
    limit: int = 50,
    use_semantic: bool = True,
    semantic_threshold: float = 0.82,
) -> list[dict[str, Any]]:
    """Check if a similar title already exists in Notion DB.

    서버사이드 title.contains 필터로 후보를 좁힌 후 Jaccard 비교.
    `use_semantic=True`이고 GOOGLE_API_KEY 있으면 Gemini 임베딩으로 보조 검사.
    서버사이드 필터 실패 시 get_recent_pages 폴백.
    Returns list of matching pages with similarity scores.
    """
    if not notion_uploader or not title or len(title) < 4:
        return []

    # ── 서버사이드 키워드 필터 (Notion API) ─────────────────────────
    # 가장 긴 토큰으로 검색 → 정밀도 최대화
    keywords = [t for t in title.split() if len(t) >= 2]
    recent_pages: list[Any] = []
    if keywords and hasattr(notion_uploader, "search_pages_by_title"):
        best_keyword = max(keywords, key=len)
        server_results = await notion_uploader.search_pages_by_title(best_keyword, limit=limit)
        if server_results:
            recent_pages = server_results
            logger.debug(
                "서버사이드 제목 검색: '%s' → %d건 반환 (전체 조회 대비 절감)",
                best_keyword,
                len(recent_pages),
            )

    # 서버사이드 결과 없으면 최근 페이지 전체 폴백
    if not recent_pages:
        try:
            recent_pages = await notion_uploader.get_recent_pages(days=lookback_days, limit=limit)
        except Exception as exc:
            logger.warning("Failed to fetch recent Notion pages for dedup: %s", exc)
            return []

    matches = []
    query_tokens = extract_korean_tokens(title)
    if not query_tokens:
        return []

    # Gemini 임베딩 (한 번만 계산)
    query_embedding: list[float] | None = None
    if use_semantic:
        query_embedding = _get_gemini_embedding(normalize_korean_text(title))
        if query_embedding:
            logger.debug("Semantic dedup 활성화 (Gemini embedding, threshold=%.2f)", semantic_threshold)

    for page in recent_pages:
        existing_title = notion_uploader.get_page_property_value(page, "title", "")
        if not existing_title:
            continue

        # 1차: Jaccard
        existing_tokens = extract_korean_tokens(existing_title)
        jaccard_sim = jaccard_similarity(query_tokens, existing_tokens)

        # 2차: Gemini 임베딩 (Jaccard가 낮아도 semantic이 높으면 중복 처리)
        final_sim = jaccard_sim
        method = "jaccard"
        if query_embedding is not None and jaccard_sim < threshold:
            emb_existing = _get_gemini_embedding(normalize_korean_text(existing_title))
            if emb_existing is not None:
                sem_sim = _cosine_similarity(query_embedding, emb_existing)
                if sem_sim >= semantic_threshold:
                    final_sim = sem_sim
                    method = "semantic"
                    logger.info(
                        "Semantic DEDUP 감지: '%s' ↔ '%s' (cosine=%.3f)",
                        title[:30], existing_title[:30], sem_sim,
                    )

        if final_sim >= (semantic_threshold if method == "semantic" else threshold):
            matches.append({
                "page_id": page.get("id"),
                "title": existing_title,
                "similarity": round(final_sim, 3),
                "method": method,
                "url": notion_uploader.get_page_property_value(page, "url", ""),
            })

    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches


def _build_minhash(tokens: set[str], num_perm: int = 128) -> "MinHash | None":
    """토큰 집합으로부터 MinHash 객체를 생성. datasketch 미설치 시 None."""
    if not _HAS_DATASKETCH or not tokens:
        return None
    m = MinHash(num_perm=num_perm)
    for token in tokens:
        m.update(token.encode("utf-8"))
    return m


def check_cross_source_duplicates(
    candidates: list[dict[str, Any]],
    threshold: float = 0.6,
    use_semantic: bool = True,
    semantic_threshold: float = 0.82,
) -> list[dict[str, Any]]:
    """Detect duplicate topics across different sources in the current batch.

    datasketch MinHash LSH로 O(n) 후보 필터링 후 정밀 비교.
    datasketch 미설치 시 기존 O(n²) Jaccard로 폴백.

    Returns deduplicated list, preferring higher engagement candidates.
    """
    if len(candidates) <= 1:
        return candidates

    titles = [candidate.get("feed_title") or "" for candidate in candidates]
    token_cache = {i: extract_korean_tokens(t) for i, t in enumerate(titles)}

    # ── MinHash LSH 가속 경로 ─────────────────────────────────────────
    if _HAS_DATASKETCH and len(candidates) >= 4:
        minhash_cache: dict[int, MinHash] = {}
        lsh = MinHashLSH(threshold=threshold, num_perm=128)

        for i, tokens in token_cache.items():
            if not tokens:
                continue
            mh = _build_minhash(tokens)
            if mh:
                minhash_cache[i] = mh
                try:
                    lsh.insert(str(i), mh)
                except ValueError:
                    pass  # 중복 키 무시

        to_remove: set[int] = set()
        for i in range(len(candidates)):
            if i in to_remove or i not in minhash_cache:
                continue
            # LSH로 후보만 빠르게 필터링
            lsh_candidates = lsh.query(minhash_cache[i])
            for j_str in lsh_candidates:
                j = int(j_str)
                if j <= i or j in to_remove:
                    continue
                # 같은 소스는 스킵
                if candidates[i].get("source") == candidates[j].get("source"):
                    continue
                # 정밀 Jaccard 확인
                jaccard_sim = jaccard_similarity(token_cache[i], token_cache.get(j, set()))
                if jaccard_sim >= threshold:
                    eng_i = candidates[i].get("feed_engagement", 0)
                    eng_j = candidates[j].get("feed_engagement", 0)
                    loser = j if eng_i >= eng_j else i
                    to_remove.add(loser)
                    logger.info(
                        "DEDUP [LSH+cross] Removing %s '%s' (sim=%.2f with %s '%s')",
                        candidates[loser].get("source"),
                        (candidates[loser].get("feed_title") or candidates[loser].get("url", ""))[:40],
                        jaccard_sim,
                        candidates[i if loser == j else j].get("source"),
                        (candidates[i if loser == j else j].get("feed_title") or "")[:40],
                    )

        # Semantic 보조 검사: LSH가 놓친 시맨틱 중복 추가 탐지
        if use_semantic:
            embed_cache: dict[int, list[float] | None] = {}
            for i, t in enumerate(titles):
                if i not in to_remove:
                    embed_cache[i] = _get_gemini_embedding(normalize_korean_text(t)) if t else None
            for i in range(len(candidates)):
                if i in to_remove:
                    continue
                for j in range(i + 1, len(candidates)):
                    if j in to_remove:
                        continue
                    if candidates[i].get("source") == candidates[j].get("source"):
                        continue
                    ei, ej = embed_cache.get(i), embed_cache.get(j)
                    if ei is not None and ej is not None:
                        sem_sim = _cosine_similarity(ei, ej)
                        if sem_sim >= semantic_threshold:
                            eng_i = candidates[i].get("feed_engagement", 0)
                            eng_j = candidates[j].get("feed_engagement", 0)
                            loser = j if eng_i >= eng_j else i
                            to_remove.add(loser)
                            logger.info(
                                "DEDUP [semantic+cross] Removing %s '%s' (cosine=%.2f)",
                                candidates[loser].get("source"),
                                (candidates[loser].get("feed_title") or "")[:40],
                                sem_sim,
                            )

        return [c for i, c in enumerate(candidates) if i not in to_remove]

    # ── Fallback: 기존 O(n²) Jaccard (datasketch 미설치 또는 소규모 배치) ──
    embed_cache_fb: dict[int, list[float] | None] = {}
    if use_semantic:
        for i, t in enumerate(titles):
            embed_cache_fb[i] = _get_gemini_embedding(normalize_korean_text(t)) if t else None

    to_remove_fb: set[int] = set()
    for i in range(len(candidates)):
        if i in to_remove_fb:
            continue
        for j in range(i + 1, len(candidates)):
            if j in to_remove_fb:
                continue
            if candidates[i].get("source") == candidates[j].get("source"):
                continue
            if not token_cache[i] or not token_cache[j]:
                continue

            jaccard_sim = jaccard_similarity(token_cache[i], token_cache[j])
            is_dup = jaccard_sim >= threshold
            sim = jaccard_sim

            if not is_dup and use_semantic:
                ei, ej = embed_cache_fb.get(i), embed_cache_fb.get(j)
                if ei is not None and ej is not None:
                    sem_sim = _cosine_similarity(ei, ej)
                    if sem_sim >= semantic_threshold:
                        is_dup = True
                        sim = sem_sim

            if is_dup:
                eng_i = candidates[i].get("feed_engagement", 0)
                eng_j = candidates[j].get("feed_engagement", 0)
                loser = j if eng_i >= eng_j else i
                to_remove_fb.add(loser)
                logger.info(
                    "DEDUP [cross-source] Removing %s '%s' (sim=%.2f with %s '%s')",
                    candidates[loser].get("source"),
                    (candidates[loser].get("feed_title") or candidates[loser].get("url", ""))[:40],
                    sim,
                    candidates[i if loser == j else j].get("source"),
                    (candidates[i if loser == j else j].get("feed_title") or "")[:40],
                )

    return [c for i, c in enumerate(candidates) if i not in to_remove_fb]
