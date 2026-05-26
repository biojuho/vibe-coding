"""Output Quality Uplift (2026-05-26) 회귀 테스트.

이 파일은 ``docs/output_quality_uplift_2026-05-26.md`` 의 Phase 1 결정론적
하드닝 5개 검사에 대한 회귀 가드입니다.

검사 대상:
  - P1-A 인플루언서 어휘 zero-tolerance
  - P1-B 마무리 여운 (마지막 문장 ? / CTA 금지)
  - P1-C 이모지 카운트 제한
  - P1-D 출처 도입 강박 ('~에서 봤는데')
  - P1-E 원문 N-gram 베끼기 (quality_gate)
"""

from __future__ import annotations

import pytest

from pipeline.draft_quality_gate import (
    DraftQualityGate,
    _count_emojis,
    _ends_with_cta_or_question,
    _find_influencer_vocab,
    _has_lead_dependency,
)
from pipeline.quality_gate import QualityGate


# ── 공통 헬퍼 ─────────────────────────────────────────────────────────


def _pad(text: str, target: int = 80) -> str:
    """min_len 통과용 한글 패딩 (문장 반복 없음)."""
    if len(text) >= target:
        return text
    return (
        text
        + " 오늘 회사 회의실에서 있었던 황당하고 신기한 이야기 하나 들려드릴게요. 생각보다 무척 재미있고 흥미로울 것 같습니다."
    )


def _failed_rule_names(result) -> set[str]:
    return {item.rule for item in result.items if not item.passed}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# P1-A: 인플루언서 어휘 zero-tolerance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestInfluencerVocab:
    @pytest.mark.parametrize(
        "word",
        ["끝판왕", "민낯", "쓴맛", "기절할 뻔", "어처구니없", "팩폭", "레전드"],
    )
    def test_single_word_triggers(self, word):
        """1회 등장만으로도 검출되어야 한다."""
        hits = _find_influencer_vocab(f"오늘 본 글이 {word} 그 자체였다")
        assert any(word in h or h in word for h in hits)

    def test_normal_text_no_hits(self):
        assert _find_influencer_vocab("회의실에 들어서니 다들 조용히 화면만 보고 있었다") == []

    def test_signal_in_normal_context_is_safe(self):
        """'시그널' 이 일반 어휘로 쓰이는 경우 (매수 시그널 등) 는 안전."""
        # "매수 시그널이" 는 명사화 패턴 매칭에 걸리지만 그래야 함 — 인플루언서 톤
        # "시그널" 단독 등장은 패턴 매칭 (은/는/이/가 + 시그널) 에 안 걸려야 함
        text = "이번 분기 실적이 시그널 역할을 한다는 분석이 있었다"
        # "역할을" 앞에 "시그널 "이 있고, "(은|는|이|가) 시그널" 또는 "시그널(이|가|는|는?다)" 매칭 → "시그널 역할" 은 안 걸림
        hits = _find_influencer_vocab(text)
        # 안전: "시그널"이 명사화 패턴에 안 들어감
        assert hits == []

    def test_dup_words_dedup(self):
        hits = _find_influencer_vocab("끝판왕 끝판왕 끝판왕")
        assert hits == ["끝판왕"]

    def test_validate_marks_error(self):
        """validate() 통해 error severity 로 잡혀야 한다."""
        gate = DraftQualityGate()
        draft = _pad("회의에서 들은 한 마디가 그날의 끝판왕이었다. 다들 말이 없어졌다.")
        result = gate.validate("twitter", draft)
        rules = {i.rule for i in result.items if not i.passed and i.severity == "error"}
        assert "인플루언서 어휘" in rules
        assert result.passed is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# P1-B: 마무리 여운
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestClosingResonance:
    def test_question_ending_flagged(self):
        assert _ends_with_cta_or_question("조용히 한 줄을 남겼다. 그 말이 오래 남았어요?") is not None

    def test_cta_ending_flagged(self):
        assert _ends_with_cta_or_question("회의는 그렇게 끝났다. 댓글로 의견 알려주세요.") is not None

    def test_statement_ending_passes(self):
        assert _ends_with_cta_or_question("회의실은 그렇게 조용해졌다. 한참 뒤에야 누군가 자리에서 일어났다.") is None

    def test_middle_question_safe(self):
        """질문이 본문 중간에 있고 마무리는 평서문이면 통과."""
        text = "왜 이런 일이 생겼을까? 결국 누군가는 먼저 자리에서 일어났다."
        assert _ends_with_cta_or_question(text) is None

    def test_validate_marks_error_twitter(self):
        gate = DraftQualityGate()
        # 질문이 마지막에 오도록 충분한 본문 + 마지막은 질문.
        draft = (
            "회의실이 조용해졌다. 다들 말이 없었다. "
            "그 짧은 침묵이 한참을 가는 날이 있다. "
            "그날 분위기에서 다들 한숨만 한 번씩 쉬었다. "
            "여러분도 그런 적 있나요?"
        )
        result = gate.validate("twitter", draft)
        rules = _failed_rule_names(result)
        assert "마무리 여운" in rules

    def test_validate_blog_not_checked(self):
        """블로그 플랫폼은 마무리 여운 검사 대상이 아님."""
        gate = DraftQualityGate()
        draft = (
            "## 제목\n"
            + "회의실 이야기. " * 200
            + "## 마무리\n공감 눌러주세요?\n"
            + " ".join(f"#태그{i}" for i in range(10))
        )
        result = gate.validate("naver_blog", draft)
        rules = _failed_rule_names(result)
        assert "마무리 여운" not in rules


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# P1-C: 이모지 카운트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEmojiCount:
    def test_zero_emojis(self):
        assert _count_emojis("회의실은 조용했다") == 0

    def test_one_emoji_ok(self):
        assert _count_emojis("회의실은 조용했다 🥲") == 1

    def test_three_emojis(self):
        assert _count_emojis("회의 🥲 점심 😭 퇴근 🔥") == 3

    def test_validate_two_emojis_warning(self):
        gate = DraftQualityGate()
        draft = _pad("회의실은 조용했다 🥲 점심도 그랬다 😭")
        result = gate.validate("twitter", draft)
        warnings = [i for i in result.items if not i.passed and i.severity == "warning"]
        assert any(w.rule == "이모지 절제" for w in warnings)

    def test_validate_four_emojis_error(self):
        gate = DraftQualityGate()
        draft = _pad("회의 🥲 점심 😭 퇴근 🔥 야근 😤")
        result = gate.validate("twitter", draft)
        errors = [i for i in result.items if not i.passed and i.severity == "error"]
        assert any(e.rule == "이모지 과다" for e in errors)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# P1-D: 출처 도입 강박
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLeadDependency:
    @pytest.mark.parametrize(
        "first",
        [
            "블라인드에서 봤는데 연봉 8천이라는 분이 있더라.",
            "뽐뿌에서 본 글인데 사연이 짠하더라.",
            "잡플래닛에 올라온 글인데 회사가 이렇게 한다고.",
            "fmkorea에서 본 얘기인데 다들 비슷한 처지라고.",
        ],
    )
    def test_dependency_detected(self, first):
        assert _has_lead_dependency(first) is True

    def test_natural_opening_passes(self):
        """자연스러운 도입은 안 걸려야 한다."""
        assert _has_lead_dependency("회의실에 들어서니 다들 화면만 보고 있었다.") is False

    def test_source_mention_in_middle_ok(self):
        """본문 중간에 출처 언급은 허용 (첫 문장만 검사)."""
        text = "회의실은 조용했다. 블라인드에서 본 글처럼 다들 비슷한 표정이었다."
        assert _has_lead_dependency(text) is False

    def test_validate_marks_warning(self):
        gate = DraftQualityGate()
        draft = _pad("블라인드에서 본 글인데 연봉이 8천이라더라. 다들 비슷한 표정이었다.")
        result = gate.validate("twitter", draft)
        warnings = [i for i in result.items if not i.passed and i.severity == "warning"]
        assert any(w.rule == "도입 강박" for w in warnings)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# P1-E: 원문 N-gram 베끼기 (quality_gate.QualityGate)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOriginality:
    def setup_method(self):
        self.gate = QualityGate()

    def test_distinct_paraphrase_clean(self):
        source = "오늘 회사에서 정말 황당한 일이 있었습니다. 부장님이 점심시간에 회의를 잡았어요."
        draft = "점심을 양보해야 했던 그날의 회의 한 장면이 다들 머리에 남았다더라."
        result = self.gate.check(draft, source_content=source)
        # copy_overlap 가 metrics 에 없거나 0 이어야 함
        assert result.metrics.get("copy_chunks", 0) == 0

    def test_short_overlap_safe(self):
        """짧은 일치(12자 미만) 는 무시."""
        source = "회의실은 조용했다. 다들 자리에 앉아 있었다."
        draft = "회의실은 조용했다. 분위기가 무거웠다. 누구도 입을 열지 않았다."
        result = self.gate.check(draft, source_content=source)
        # "회의실은 조용했다" (8자 + 공백 무시 = 8자) < 12 → 무시
        assert result.metrics.get("copy_chunks", 0) == 0

    def test_partial_copy_warns(self):
        """12자 이상 연속 일치 2개 → warning."""
        # 한국어 12자 이상 연속 일치 2곳 만들기
        source = "이번 분기 실적 발표 후 회의실 분위기가 가라앉았다. 팀장은 무거운 얼굴로 한참 자료를 넘겨봤다."
        # draft 가 source 의 두 긴 chunk 를 그대로 가져다 씀
        draft = (
            "이번 분기 실적 발표 후 회의실 분위기가 가라앉았다. "
            "그날의 짧은 침묵이 오래 기억에 남았다. "
            "팀장은 무거운 얼굴로 한참 자료를 넘겨봤다."
        )
        result = self.gate.check(draft, source_content=source)
        assert result.metrics.get("copy_chunks", 0) >= 2
        assert any("copy_overlap_partial" in w for w in result.warnings) or any(
            "copy_overlap" in f for f in result.failures
        )

    def test_heavy_copy_fails(self):
        """4 chunk 이상 연속 일치 → failure.

        chunk 가 한 덩어리로 병합되지 않도록 사이에 novel(원문에 없는) 문구를 끼움.
        """
        source = (
            "이번 분기 실적 발표 후 회의실 분위기가 무거웠다는 후일담이 있었습니다. "
            "팀장은 자료를 넘기며 한숨을 한 번 쉬었다는 얘기도 있었지요. "
            "막내 사원이 조심스레 의견을 꺼냈다는 점이 그날 가장 인상적이었다네. "
            "결국 점심도 거른 채로 자리에 앉아 있었다는 후기로 마무리되었습니다."
        )
        draft = (
            "이번 분기 실적 발표 후 회의실 분위기가 무거웠다는 후일담이 있었습니다. "
            "그날의 짧은 침묵이 아직 기억에 또렷이 남아 있다고 한다. "  # novel
            "팀장은 자료를 넘기며 한숨을 한 번 쉬었다는 얘기도 있었지요. "
            "표정에서 모두가 한 박자 느려졌다는 인상을 받았다고 들었다. "  # novel
            "막내 사원이 조심스레 의견을 꺼냈다는 점이 그날 가장 인상적이었다네. "
            "회의실의 공기가 한순간 멈춰버린 듯한 감각이 있었다고 한다. "  # novel
            "결국 점심도 거른 채로 자리에 앉아 있었다는 후기로 마무리되었습니다."
        )
        result = self.gate.check(draft, source_content=source)
        assert result.metrics.get("copy_chunks", 0) >= 4
        assert result.passed is False
        assert any("copy_overlap" in f for f in result.failures)

    def test_quoted_passage_excluded(self):
        """인용부("...") 안의 원문 그대로 인용은 제외."""
        source = "팀장은 '이번 분기는 동결입니다 잘부탁드립니다' 라고 잘라 말했다 다들."
        draft = '팀장이 "이번 분기는 동결입니다 잘부탁드립니다" 라고 말한 순간 회의실 공기가 멈췄다.'
        result = self.gate.check(draft, source_content=source)
        # 인용은 제외 → copy_overlap 안 잡혀야 함
        assert result.metrics.get("copy_chunks", 0) == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 2: Bland Creator Take & Semantic Similarity (2026-05-26+)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBlandCreatorTake:
    def setup_method(self):
        self.gate = QualityGate()

    def test_bland_creator_take_triggers_failure(self):
        """숫자가 전혀 없고 뻔한 상투적 소셜 표현이 2개 이상이면 실패해야 함."""
        # bland_buzzwords: "정말 중요", "꼭 기억" 포함, 아라비아 숫자 없음
        text = _pad("이번 이터레이션에서 가장 정말 중요 생각하는 부분은 다들 꼭 기억하셨으면 좋겠습니다.")
        result = self.gate.check(text)
        assert result.passed is False
        assert any("bland_creator_take:" in f for f in result.failures)
        assert result.metrics.get("has_digits") == 0.0
        assert result.metrics.get("bland_buzzword_count") >= 2.0

    def test_bland_with_digits_passes(self):
        """뻔한 어구가 있더라도 구체적 수치(숫자)가 포함되어 있으면 실패가 아니어야 함."""
        # "정말 중요", "꼭 기억" 2개 포함되나, "3가지" 라는 구체적 수치(숫자) 제공
        text = _pad("이번에 다루는 3가지 팩트 중 정말 중요 핵심은 꼭 기억하셔야 합니다.")
        result = self.gate.check(text)
        assert result.passed is True
        assert not any("bland_creator_take:" in f for f in result.failures)
        assert result.metrics.get("has_digits") == 1.0

    def test_buzzword_overuse_warns(self):
        """숫자가 포함되어 있어도 뻔한 어구가 3개 이상이면 warning 발생해야 함."""
        text = _pad(
            "12일 발표된 자료를 생각해보면, 다들 어떻게 생각하시나요? 저는 정말 중요 생각하는 부분이 있습니다. 꼭 기억합시다."
        )
        result = self.gate.check(text)
        assert result.passed is True  # Warning이므로 passed는 True
        assert any("bland_creator_take_warning" in w for w in result.warnings)
        assert result.metrics.get("bland_buzzword_count") >= 3.0

    def test_normal_social_take_passes_completely(self):
        """일반적이고 구체적인 본문은 완전히 통과."""
        text = _pad("작년 대비 영업 이익이 무려 45% 성장했습니다. 특히 해외 시장에서의 반응이 뜨거웠던 덕분입니다.")
        result = self.gate.check(text)
        assert result.passed is True
        assert not any("bland_creator" in f for f in result.failures)
        assert not any("bland_creator" in w for w in result.warnings)


class TestSemanticSimilarity:
    def setup_method(self):
        self.gate = QualityGate()
        from pipeline.draft_cache import DraftCache

        self.cache = DraftCache()
        self.cache.clear()  # 깨끗한 테스트 상태 시작

    def teardown_method(self):
        self.cache.clear()

    def test_high_similarity_triggers_failure(self):
        """최근 저장된 초안과 유사도가 0.85 이상이면 실패해야 함."""
        # 1. 최근 캐시 데이터 인서트
        past_draft = {
            "twitter": "오늘 점심은 오랜만에 부장님이 다 같이 피자를 먹자고 하셔서 기분 좋게 식사했네요.",
            "threads": "피자 파티 맛있었다",
        }
        self.cache.set("test_key_1", past_draft, "img_prompt")

        # 2. 아주 비슷한 초안 (공백 1개 차이 -> 90% 이상 유사)
        current_draft = "오늘 점심은 오랜만에 부장님이 다 같이 피자를 먹자고 하셔서 기분좋게 식사했네요."
        result = self.gate.check(current_draft, platform="twitter")

        assert result.passed is False
        assert any("semantic_similarity_limit" in f for f in result.failures)
        assert result.metrics.get("max_semantic_similarity", 0) >= 0.85

    def test_partial_similarity_triggers_warning(self):
        """최근 초안과 유사도가 0.70 이상 0.85 미만인 경우 warning 발생해야 함."""
        past_draft = {
            "twitter": "오늘 점심은 오랜만에 부장님이 다 같이 피자를 먹자고 하셔서 기분 좋게 식사했네요.",
            "threads": "피자 파티 맛있었다",
        }
        self.cache.set("test_key_2", past_draft, "img_prompt")

        # 뻔한 단어가 살짝 추가됨 (0.838 수준의 3-gram Jaccard 유사도 발생)
        current_draft = "오늘 점심은 오랜만에 부장님이 다 같이 피자를 먹자고 하셔서 정말 기분 좋게 식사했네요."
        result = self.gate.check(current_draft, platform="twitter")

        assert result.passed is True  # Warning이므로 passed
        assert any("semantic_similarity_warning" in w for w in result.warnings)
        assert 0.70 <= result.metrics.get("max_semantic_similarity", 0) < 0.85

    def test_distinct_draft_passes_completely(self):
        """완전히 다른 초안은 유사도 체크를 완벽히 통과."""
        past_draft = {
            "twitter": "오늘 아침 지하철 2호선 연착 때문에 지각할 뻔해서 아침부터 심장이 쫄깃했네요.",
            "threads": "지하철 연착 지옥",
        }
        self.cache.set("test_key_3", past_draft, "img_prompt")

        current_draft = "업계 전반적으로 AI 도입 속도가 가속화되면서 개발 환경도 매일 변화하고 있습니다."
        result = self.gate.check(current_draft, platform="twitter")

        assert result.passed is True
        assert not any("semantic_similarity" in f for f in result.failures)
        assert not any("semantic_similarity" in w for w in result.warnings)
        assert result.metrics.get("max_semantic_similarity", 0) < 0.70
