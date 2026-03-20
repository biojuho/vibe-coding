"""품질 게이트 + MinHash LSH 유닛 테스트."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── QualityGate 하드 게이트 테스트 ───────────────────────────────────
class TestQualityGateHard:
    def test_empty_draft_fails(self):
        from pipeline.quality_gate import QualityGate
        gate = QualityGate()
        r = gate.check("", "원문 내용")
        assert not r.passed
        assert "empty_draft" in r.failures[0]

    def test_normal_draft_passes(self):
        from pipeline.quality_gate import QualityGate
        gate = QualityGate()
        draft = "직장인 평균 연봉이 5천만원을 돌파했습니다. 전문가들은 긍정적으로 평가하고 있습니다."
        r = gate.check(draft, "원문 내용", platform="default")
        assert r.passed
        assert r.score > 50

    def test_too_short_twitter(self):
        from pipeline.quality_gate import QualityGate
        gate = QualityGate()
        r = gate.check("짧은 글", "", platform="twitter")
        assert not r.passed
        assert any("too_short" in f for f in r.failures)

    def test_too_long_twitter(self):
        from pipeline.quality_gate import QualityGate
        gate = QualityGate()
        r = gate.check("가" * 300, "", platform="twitter")
        assert not r.passed
        assert any("too_long" in f for f in r.failures)

    def test_pii_detection(self):
        from pipeline.quality_gate import QualityGate
        gate = QualityGate()
        r = gate.check("연락처: 010-1234-5678 으로 연락주세요. 이 정보는 매우 중요합니다.", "")
        assert not r.passed
        assert any("toxic_or_pii" in f for f in r.failures)

    def test_email_detection(self):
        from pipeline.quality_gate import QualityGate
        gate = QualityGate()
        r = gate.check("문의: test@example.com 으로 보내주세요. 감사합니다.", "")
        assert not r.passed

    def test_repetition_detection(self):
        from pipeline.quality_gate import QualityGate
        gate = QualityGate()
        draft = "연봉이 올랐다. 연봉이 올랐다. 연봉이 올랐다. 정말 놀라운 일이다."
        r = gate.check(draft, "")
        assert any("repetition" in f or "minor_repetition" in w
                    for f in r.failures for w in [f]) or \
               any("repetition" in w for w in r.warnings)

    def test_source_fidelity_warning(self):
        from pipeline.quality_gate import QualityGate
        gate = QualityGate()
        source = "평균 연봉 5천만원, 이직률 30%"
        draft = "평균 연봉 8천만원이고 이직률 50%라고 합니다. 정말 놀랍습니다."
        r = gate.check(draft, source)
        # fabricated numbers should trigger warning
        assert r.metrics.get("fact_confidence", 1.0) < 1.0 or len(r.warnings) > 0

    def test_score_calculation(self):
        from pipeline.quality_gate import QualityGate
        gate = QualityGate()
        # Normal text
        r1 = gate.check("정상적인 한국어 문장입니다. 두 번째 문장도 있습니다.", "")
        # Text with issues
        r2 = gate.check("짧", "", platform="twitter")
        assert r1.score > r2.score


# ── MinHash LSH 통합 테스트 ──────────────────────────────────────────
class TestMinHashLSH:
    def test_minhash_build(self):
        from pipeline.dedup import _build_minhash, _HAS_DATASKETCH
        if not _HAS_DATASKETCH:
            pytest.skip("datasketch not installed")
        mh = _build_minhash({"연봉", "이직", "직장인"})
        assert mh is not None

    def test_minhash_empty_returns_none(self):
        from pipeline.dedup import _build_minhash, _HAS_DATASKETCH
        if not _HAS_DATASKETCH:
            pytest.skip("datasketch not installed")
        assert _build_minhash(set()) is None

    def test_similar_titles_detected(self):
        from pipeline.dedup import _build_minhash, _HAS_DATASKETCH, extract_korean_tokens
        if not _HAS_DATASKETCH:
            pytest.skip("datasketch not installed")
        tokens_a = extract_korean_tokens("직장인 연봉 5천만원 돌파 소식")
        tokens_b = extract_korean_tokens("직장인 연봉 5천만원 돌파했다")
        mh_a = _build_minhash(tokens_a)
        mh_b = _build_minhash(tokens_b)
        assert mh_a and mh_b
        sim = mh_a.jaccard(mh_b)
        assert sim > 0.5  # 유사한 제목은 높은 similarity

    def test_different_titles_low_similarity(self):
        from pipeline.dedup import _build_minhash, _HAS_DATASKETCH, extract_korean_tokens
        if not _HAS_DATASKETCH:
            pytest.skip("datasketch not installed")
        tokens_a = extract_korean_tokens("직장인 연봉 5천만원 돌파")
        tokens_b = extract_korean_tokens("부동산 시장 하락 전망")
        mh_a = _build_minhash(tokens_a)
        mh_b = _build_minhash(tokens_b)
        assert mh_a and mh_b
        sim = mh_a.jaccard(mh_b)
        assert sim < 0.3

    def test_cross_source_dedup_with_lsh(self):
        from pipeline.dedup import check_cross_source_duplicates, _HAS_DATASKETCH
        if not _HAS_DATASKETCH:
            pytest.skip("datasketch not installed")
        candidates = [
            {"feed_title": "직장인 연봉 5천만원 돌파", "source": "blind", "feed_engagement": 100},
            {"feed_title": "회사원 월급 현실 폭로", "source": "fmkorea", "feed_engagement": 50},
            {"feed_title": "직장인 연봉 5천만원을 돌파했다", "source": "ppomppu", "feed_engagement": 30},
            {"feed_title": "부동산 시장 전망 분석", "source": "blind", "feed_engagement": 80},
        ]
        result = check_cross_source_duplicates(candidates, threshold=0.5, use_semantic=False)
        # "직장인 연봉 5천만원 돌파"와 유사한 ppomppu 글이 제거되어야 함
        assert len(result) < len(candidates)
        # 부동산 글은 보존
        assert any("부동산" in c.get("feed_title", "") for c in result)

    def test_cross_source_dedup_fallback_no_datasketch(self):
        """datasketch 없이 기존 Jaccard 폴백이 동작하는지 확인."""
        import pipeline.dedup as dedup_mod
        old_flag = dedup_mod._HAS_DATASKETCH
        try:
            dedup_mod._HAS_DATASKETCH = False
            candidates = [
                {"feed_title": "연봉 5천만원 소식입니다", "source": "blind", "feed_engagement": 100},
                {"feed_title": "연봉 5천만원 소식이래요", "source": "fmkorea", "feed_engagement": 50},
            ]
            result = dedup_mod.check_cross_source_duplicates(
                candidates, threshold=0.5, use_semantic=False,
            )
            assert len(result) <= len(candidates)
        finally:
            dedup_mod._HAS_DATASKETCH = old_flag


# ── draft_validator 기본 테스트 ──────────────────────────────────────
class TestDraftValidator:
    @pytest.mark.asyncio
    async def test_validate_passing_drafts(self):
        from pipeline.draft_validator import validate_and_fix_drafts
        drafts = {
            "twitter": "직장인 연봉 5천만원 시대가 도래했습니다. 여러분의 연봉은 어떤가요?",
            "newsletter": "직장인 평균 연봉이 5천만원을 돌파했습니다. " * 5,
            "_hook_score": 8,
        }
        post_data = {"content": "연봉 5천만원 돌파 관련 기사", "title": "연봉 5천만원"}
        result = await validate_and_fix_drafts(drafts, post_data, generator=None)
        # 내부 키 보존
        assert "_hook_score" in result
        # quality_gate 메타 기록
        assert "quality_gate" in post_data

    @pytest.mark.asyncio
    async def test_validate_short_draft_flagged(self):
        from pipeline.draft_validator import validate_and_fix_drafts
        drafts = {"twitter": "짧음"}
        post_data = {"content": "원문", "title": "제목"}
        result = await validate_and_fix_drafts(drafts, post_data, generator=None)
        # generator가 없으므로 재시도 없이 원본 유지
        assert result["twitter"] == "짧음"
        assert not post_data["quality_gate"]["twitter"]["passed"]
