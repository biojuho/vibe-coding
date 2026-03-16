"""Post-LLM 품질 게이트 + 시멘틱 씬 매핑 테스트.

테스트 대상:
  1. DraftQualityGate — 플랫폼별 초안 품질 검증
  2. _SEMANTIC_SCENES — 시멘틱 씬 매핑 통합 프롬프트 생성
"""

import unittest
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 1: DraftQualityGate 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestDraftQualityGate(unittest.TestCase):
    """DraftQualityGate 핵심 기능 테스트."""

    def setUp(self):
        from pipeline.draft_quality_gate import DraftQualityGate
        self.gate = DraftQualityGate()

    # ── Twitter 플랫폼 ──────────────────────────────────────────────

    def test_twitter_good_draft_passes(self):
        """정상적인 트위터 초안은 통과해야 한다."""
        draft = "연봉 인상은 직장인의 가장 큰 관심사죠. 여러분은 올해 얼마나 올랐나요? 회사마다 다르겠지만 공감하시는 분?"
        result = self.gate.validate("twitter", draft)
        self.assertTrue(result.passed)
        self.assertGreaterEqual(result.score, 70)

    def test_twitter_too_long_fails(self):
        """280자 초과 트위터 초안은 실패해야 한다."""
        draft = "가" * 300
        result = self.gate.validate("twitter", draft)
        self.assertFalse(result.passed)
        # 글자 수 초과 → error severity
        errors = [i for i in result.items if not i.passed and i.severity == "error"]
        self.assertTrue(len(errors) > 0)

    def test_twitter_too_short_fails(self):
        """60자 미만 트위터 초안은 실패해야 한다."""
        draft = "짧은 초안"
        result = self.gate.validate("twitter", draft)
        self.assertFalse(result.passed)

    def test_twitter_empty_draft_fails(self):
        """빈 초안은 실패해야 한다."""
        result = self.gate.validate("twitter", "")
        self.assertFalse(result.passed)
        self.assertTrue(result.should_retry)

    def test_twitter_none_draft_fails(self):
        """None 초안은 실패해야 한다."""
        result = self.gate.validate("twitter", None)
        self.assertFalse(result.passed)

    def test_twitter_with_url_warns(self):
        """외부 링크가 포함된 트위터 초안은 금지 패턴 경고가 발생해야 한다."""
        draft = "직장인 필독! 연봉 협상 팁: https://example.com 이 기사 참고해보세요. 여러분은 어떻게 협상하시나요?"
        result = self.gate.validate("twitter", draft)
        forbidden_items = [i for i in result.items if i.rule == "금지 패턴" and not i.passed]
        self.assertTrue(len(forbidden_items) > 0)

    def test_twitter_cta_detected(self):
        """CTA가 있는 트위터 초안에서 CTA 검출이 되어야 한다."""
        draft = "연봉 인상이 안 됐다고? 여러분은 어떻게 생각하나요?" + "가" * 40
        result = self.gate.validate("twitter", draft)
        cta_items = [i for i in result.items if i.rule == "CTA 포함"]
        self.assertTrue(any(i.passed for i in cta_items))

    def test_twitter_no_cta_warns(self):
        """CTA가 없는 트위터 초안에서 CTA 경고가 발생해야 한다."""
        draft = "오늘도 출근했다. 회사에서 점심을 먹었다. 퇴근해서 집에 갔다. 하루가 지나갔네." + "가" * 20
        result = self.gate.validate("twitter", draft)
        cta_items = [i for i in result.items if i.rule == "CTA 포함" and not i.passed]
        self.assertTrue(len(cta_items) > 0)

    # ── Threads 플랫폼 ─────────────────────────────────────────────

    def test_threads_good_draft_passes(self):
        """정상적인 Threads 초안은 통과해야 한다."""
        draft = (
            "요즘 직장인 사이에서 '조용한 퇴사'가 화제입니다. "
            "과도한 업무에 시달리면서도 실제로 퇴사하지 않고, 최소한의 업무만 수행하는 트렌드죠. "
            "여러분은 어떠신가요? #직장인 #조용한퇴사"
        )
        result = self.gate.validate("threads", draft)
        self.assertTrue(result.passed)

    def test_threads_too_long_fails(self):
        """500자 초과 Threads 초안은 실패해야 한다."""
        draft = "직" * 510
        result = self.gate.validate("threads", draft)
        self.assertFalse(result.passed)

    def test_threads_min_hashtag_check(self):
        """Threads 초안은 최소 1개 해시태그가 있어야 한다."""
        draft = "여러분 요즘 회사 어떠세요 공감하시면 댓글 남겨주세요. 진짜 힘든 하루였어요." + "가" * 30
        result = self.gate.validate("threads", draft)
        hashtag_items = [i for i in result.items if i.rule == "해시태그 하한"]
        has_warning = any(not i.passed for i in hashtag_items)
        self.assertTrue(has_warning)

    # ── Naver Blog 플랫폼 ──────────────────────────────────────────

    def test_blog_good_draft_passes(self):
        """정상적인 블로그 초안은 통과해야 한다."""
        heading_section = "## 소제목 하나\n내용입니다.\n## 소제목 둘\n더 많은 내용.\n## 소제목 셋\n추가 내용.\n"
        body = "직장인의 연봉 이야기를 해보겠습니다. " * 50
        cta = "이웃추가 하시면 더 좋은 정보를 드려요! "
        tags = " ".join(f"#태그{i}" for i in range(12))
        draft = heading_section + body + cta + tags
        result = self.gate.validate("naver_blog", draft)
        self.assertTrue(result.passed)

    def test_blog_too_short_fails(self):
        """1000자 미만 블로그 초안은 실패해야 한다."""
        draft = "## 제목\n짧은 블로그 글.\n## 끝\n공감 눌러주세요." + " ".join(f"#태그{i}" for i in range(10))
        result = self.gate.validate("naver_blog", draft)
        min_len_items = [i for i in result.items if "최소 글자 수" in i.rule and not i.passed]
        self.assertTrue(len(min_len_items) > 0)

    def test_blog_requires_headings(self):
        """블로그 초안은 소제목이 최소 2개 있어야 한다."""
        draft = "긴 블로그 글입니다. " * 100 + "이웃추가 해주세요! " + " ".join(f"#태그{i}" for i in range(10))
        result = self.gate.validate("naver_blog", draft)
        heading_items = [i for i in result.items if "소제목" in i.rule and not i.passed]
        self.assertTrue(len(heading_items) > 0)

    # ── 일괄 검증 ──────────────────────────────────────────────────

    def test_validate_all_returns_all_platforms(self):
        """validate_all은 모든 플랫폼 결과를 반환해야 한다."""
        drafts = {
            "twitter": "연봉 인상은 직장인의 관심사. 여러분은 얼마나 올랐어요?" + "가" * 20,
            "threads": "직장인 공감 이야기 #직장인 " + "가" * 60,
            "_provider_used": "gemini",  # 메타 키는 무시되어야 함
        }
        results = self.gate.validate_all(drafts)
        self.assertIn("twitter", results)
        self.assertIn("threads", results)
        self.assertNotIn("_provider_used", results)

    def test_format_summary_contains_score(self):
        """format_summary는 점수 정보를 포함해야 한다."""
        drafts = {"twitter": "직장인 연봉 이야기. 여러분은 어떻게 생각하시나요?" + "가" * 30}
        results = self.gate.validate_all(drafts)
        summary = self.gate.format_summary(results)
        self.assertIn("품질 게이트", summary)
        self.assertIn("/100", summary)

    # ── strict_mode ─────────────────────────────────────────────────

    def test_strict_mode_fails_on_warnings(self):
        """strict_mode에서는 경고도 실패로 처리되어야 한다."""
        from pipeline.draft_quality_gate import DraftQualityGate
        strict_gate = DraftQualityGate(strict_mode=True)
        # CTA 없는 초안 → 경고는 뜨지만 보통은 통과
        draft = "오늘 하루도 무사히 끝났다. 집에 가야지. 또 내일 출근해야 하니까." + "가" * 20
        result = strict_gate.validate("twitter", draft)
        # strict_mode면 경고도 실패 처리
        warnings = [i for i in result.items if not i.passed and i.severity == "warning"]
        if warnings:
            self.assertFalse(result.passed)

    # ── custom_rules ────────────────────────────────────────────────

    def test_custom_rules_override(self):
        """custom_rules로 기본 규칙이 오버라이드 되어야 한다."""
        from pipeline.draft_quality_gate import DraftQualityGate
        custom_gate = DraftQualityGate(custom_rules={"twitter": {"max_len": 140}})
        # 기본 280자 → 140자로 축소
        draft = "가" * 150 + "?"
        result = custom_gate.validate("twitter", draft)
        max_len_fail = [i for i in result.items if "최대 글자 수" in i.rule and not i.passed]
        self.assertTrue(len(max_len_fail) > 0)

    # ── to_dict / summary ──────────────────────────────────────────

    def test_result_to_dict(self):
        """QualityResult.to_dict()는 올바른 구조를 반환해야 한다."""
        draft = "직장인 연봉 이야기. 여러분 생각은 어떠신가요?" + "가" * 30
        result = self.gate.validate("twitter", draft)
        d = result.to_dict()
        self.assertIn("platform", d)
        self.assertIn("score", d)
        self.assertIn("items", d)
        self.assertIsInstance(d["items"], list)

    def test_result_summary(self):
        """QualityResult.summary()는 한 줄 요약을 반환해야 한다."""
        draft = "직장인 연봉 이야기. 여러분은 어떻게 생각하시나요?" + "가" * 30
        result = self.gate.validate("twitter", draft)
        s = result.summary()
        self.assertIn("twitter", s)
        self.assertIn("score=", s)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 2: 시멘틱 씬 매핑 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSemanticSceneMapping(unittest.TestCase):
    """시멘틱 씬 매핑이 이미지 프롬프트에 올바르게 반영되는지 테스트."""

    def _build(self, topic, emotion):
        from pipeline.image_generator import ImageGenerator
        return ImageGenerator.build_image_prompt(
            topic_cluster=topic,
            emotion_axis=emotion,
            title="테스트 제목",
            source="blind",
        )

    def test_semantic_scene_used_when_matched(self):
        """(토픽, 감정) 교차 매핑이 존재하면 시멘틱 씬이 프롬프트에 반영되어야 한다."""
        prompt = self._build("연봉", "분노")
        # 시멘틱 씬 키워드: "tiny paycheck", "coworkers celebrate bonuses"
        self.assertIn("tiny paycheck", prompt)
        self.assertIn("coworkers celebrate bonuses", prompt)

    def test_fallback_to_topic_scene_when_no_match(self):
        """(토픽, 감정) 매핑이 없으면 토픽 기본 장면으로 폴백되어야 한다."""
        # "정치" 토픽에는 시멘틱 씬 매핑이 없음
        prompt = self._build("정치", "분노")
        # 기본 토픽 씬: "reading news on phone"
        self.assertIn("reading news on phone", prompt)

    def test_fallback_to_default_scene(self):
        """토픽도 매핑이 없으면 기본 범용 장면이 사용되어야 한다."""
        prompt = self._build("알수없음", "미지의감정")
        self.assertIn("relatable everyday expression", prompt)

    def test_all_semantic_scenes_produce_valid_prompts(self):
        """모든 시멘틱 씬 매핑 조합이 유효한 프롬프트를 생성해야 한다."""
        from pipeline.image_generator import _SEMANTIC_SCENES
        for (topic, emotion), scene_desc in _SEMANTIC_SCENES.items():
            prompt = self._build(topic, emotion)
            # 기본 구성 요소 확인
            self.assertIn("Pixar", prompt, f"Failed for ({topic}, {emotion})")
            self.assertIn("no text", prompt, f"Failed for ({topic}, {emotion})")
            # 시멘틱 씬의 핵심 단어가 프롬프트에 포함
            first_words = scene_desc.split()[:3]
            for word in first_words:
                self.assertIn(word, prompt, f"Scene word '{word}' missing for ({topic}, {emotion})")

    def test_no_korean_in_prompt(self):
        """프롬프트에 한글이 포함되지 않아야 한다."""
        test_cases = [
            ("연봉", "분노"),
            ("이직", "허탈"),
            ("IT", "웃김"),
            ("자기계발", "현타"),
        ]
        for topic, emotion in test_cases:
            prompt = self._build(topic, emotion)
            korean_chars = [c for c in prompt if '\uac00' <= c <= '\ud7a3']
            self.assertEqual(
                len(korean_chars), 0,
                f"Korean chars found in prompt for ({topic}, {emotion}): {korean_chars}",
            )

    def test_no_text_constraint_always_present(self):
        """모든 프롬프트에 'no text' 제약이 포함되어야 한다."""
        test_cases = [
            ("연봉", "경악"),
            ("상사", "분노"),
            ("복지", "기대감"),
            ("알수없음", ""),
        ]
        for topic, emotion in test_cases:
            prompt = self._build(topic, emotion)
            self.assertIn("no text", prompt, f"'no text' missing for ({topic}, {emotion})")
            self.assertIn("no letters", prompt, f"'no letters' missing for ({topic}, {emotion})")

    def test_emotion_expression_reflected(self):
        """감정 표정이 프롬프트에 반영되어야 한다."""
        prompt = self._build("연봉", "경악")
        self.assertIn("shocked", prompt)
        self.assertIn("jaw dropped", prompt)

    def test_hyunta_emotion_supported(self):
        """새로 추가된 '현타' 감정이 지원되어야 한다."""
        prompt = self._build("자기계발", "현타")
        self.assertIn("exhausted", prompt)

    def test_semantic_scene_count(self):
        """시멘틱 씬 매핑은 최소 60개 이상이어야 한다."""
        from pipeline.image_generator import _SEMANTIC_SCENES
        self.assertGreaterEqual(len(_SEMANTIC_SCENES), 60)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 3: 헬퍼 함수 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestQualityGateHelpers(unittest.TestCase):
    """품질 게이트 헬퍼 함수 테스트."""

    def test_korean_ratio_pure_korean(self):
        from pipeline.draft_quality_gate import _korean_ratio
        ratio = _korean_ratio("안녕하세요")
        self.assertGreater(ratio, 0.9)

    def test_korean_ratio_pure_english(self):
        from pipeline.draft_quality_gate import _korean_ratio
        ratio = _korean_ratio("Hello World")
        self.assertEqual(ratio, 0.0)

    def test_korean_ratio_mixed(self):
        from pipeline.draft_quality_gate import _korean_ratio
        ratio = _korean_ratio("안녕 Hello")
        self.assertGreater(ratio, 0.0)
        self.assertLess(ratio, 1.0)

    def test_korean_ratio_empty(self):
        from pipeline.draft_quality_gate import _korean_ratio
        ratio = _korean_ratio("")
        self.assertEqual(ratio, 0.0)

    def test_count_hashtags(self):
        from pipeline.draft_quality_gate import _count_hashtags
        self.assertEqual(_count_hashtags("#태그1 #태그2 #tag3"), 3)
        self.assertEqual(_count_hashtags("no tags here"), 0)

    def test_count_headings(self):
        from pipeline.draft_quality_gate import _count_headings
        text = "## 첫 번째\n### 두 번째\n#### 세 번째\n일반 텍스트"
        self.assertEqual(_count_headings(text), 2)  # ## 과 ###만 카운트

    def test_has_cta_with_question(self):
        from pipeline.draft_quality_gate import _has_cta
        self.assertTrue(_has_cta("여러분은 어떻게 생각하나요?", [r"[?？]"]))
        self.assertFalse(_has_cta("그냥 그렇다.", [r"[?？]"]))


if __name__ == "__main__":
    unittest.main()
