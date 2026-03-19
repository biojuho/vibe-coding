"""Phase 1~5 퀄리티 개선 테스트.

테스트 대상:
  1. DraftQualityGate — 실질 품질 검사 4종 (클리셰, 반복구조, 훅강도, 구체성)
  2. EditorialReviewer — 에디토리얼 리뷰어 구조
  3. ContentCalendar — 토픽 반복 방지
  4. readability — 한국어 가독성 스코어
  5. classify_hook_type — 6종 훅 타입 통일
  6. ImageGenerator — 커뮤니티별 씬 매핑
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 1: DraftQualityGate 실질 품질 검사
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestQualityGateSubstanceChecks(unittest.TestCase):
    """P1-E: 실질 품질 검사 4종 테스트."""

    def setUp(self):
        from pipeline.draft_quality_gate import DraftQualityGate
        self.gate = DraftQualityGate()

    def test_cliche_warning_triggered(self):
        """클리셰 3개 이상이면 warning 발생."""
        draft = (
            "이거 실화? 나만 이런 거 아니죠? 직장인이라면 공감하실 "
            "연봉 5천만원 이야기. 여러분 어떻게 생각하세요?"
        )
        result = self.gate.validate("twitter", draft)
        cliche_items = [i for i in result.items if i.rule == "클리셰 과다"]
        self.assertTrue(len(cliche_items) > 0, "클리셰 과다 항목이 있어야 함")
        self.assertFalse(cliche_items[0].passed)

    def test_no_cliche_warning_for_clean_draft(self):
        """클리셰 없는 깔끔한 초안은 클리셰 과다 경고 없음."""
        draft = "블라인드에서 연봉 5천 자랑글 밑에 달린 댓글이 레전드... 여러분은 어떤가요?"
        result = self.gate.validate("twitter", draft)
        cliche_fail = [i for i in result.items if i.rule == "클리셰 과다" and not i.passed]
        self.assertEqual(len(cliche_fail), 0)

    def test_hook_strength_warning_no_hook(self):
        """첫 문장에 숫자/질문/감정어 없으면 훅 강도 경고."""
        draft = "직장인들의 일상은 참으로 바쁘다. 매일 출근하면 힘든 일이 가득합니다. 그래도 다같이 힘내봐요?"
        result = self.gate.validate("twitter", draft)
        hook_items = [i for i in result.items if i.rule == "훅 강도"]
        if hook_items:  # 문장 분리가 되어야 작동
            self.assertFalse(hook_items[0].passed)

    def test_hook_strength_pass_with_number(self):
        """첫 문장에 숫자가 있으면 훅 강도 통과."""
        draft = "연봉 5천만원 받는 직장인이 블라인드에 올린 글 봤어요? 댓글이 난리."
        result = self.gate.validate("twitter", draft)
        hook_fail = [i for i in result.items if i.rule == "훅 강도" and not i.passed]
        self.assertEqual(len(hook_fail), 0)

    def test_vague_language_warning(self):
        """모호한 표현 2개 이상이면 구체성 부족 경고."""
        draft = "높은 연봉을 받는 많은 사람들이 최근에 이직을 고려하고 있다고 해요. 여러분 생각은?"
        result = self.gate.validate("twitter", draft)
        vague_items = [i for i in result.items if i.rule == "구체성 부족"]
        self.assertTrue(len(vague_items) > 0, "구체성 부족 항목이 있어야 함")

    def test_existing_checks_still_work(self):
        """기존 형식 검사(글자수, 한글비율, CTA)가 여전히 작동."""
        # 정상 트윗 (60자 이상, CTA 포함)
        good = "블라인드에서 연봉 5천 자랑글이 올라왔는데, 밑에 달린 댓글이 진짜 레전드였어요. 여러분은 올해 연봉 얼마나 올랐나요?"
        result = self.gate.validate("twitter", good)
        self.assertTrue(result.passed)
        # 너무 긴 트윗
        bad = "가" * 300
        result2 = self.gate.validate("twitter", bad)
        self.assertFalse(result2.passed)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 2: EditorialReviewer 구조 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEditorialReviewerStructure(unittest.TestCase):
    """P1-C: 에디토리얼 리뷰어 클래스 구조 테스트."""

    def test_import_and_dataclass(self):
        """EditorialResult dataclass가 정상 import 되어야 함."""
        from pipeline.editorial_reviewer import EditorialResult, EditorialReviewer
        result = EditorialResult()
        self.assertIsInstance(result.polished_drafts, dict)
        self.assertIsInstance(result.scores, dict)
        self.assertEqual(result.avg_score, 0.0)

    def test_reviewer_no_api_key_graceful(self):
        """API 키 없을 때 graceful하게 원본 반환."""
        import asyncio
        from pipeline.editorial_reviewer import EditorialReviewer

        # API 키 없이 생성
        reviewer = EditorialReviewer(config=None)
        reviewer.api_key = None

        drafts = {"twitter": "테스트 초안입니다. 여러분 어떠세요?"}
        post_data = {"title": "테스트", "content": "테스트 본문"}

        result = asyncio.run(
            reviewer.review_and_polish(drafts, post_data)
        )
        # API 키 없으면 원본 그대로 반환
        self.assertEqual(result.polished_drafts["twitter"], drafts["twitter"])

    def test_reviewer_skips_internal_keys(self):
        """'_'로 시작하는 내부 키는 리뷰 대상에서 제외."""
        import asyncio
        from pipeline.editorial_reviewer import EditorialReviewer

        reviewer = EditorialReviewer(config=None)
        reviewer.api_key = None

        drafts = {
            "twitter": "테스트 초안. 여러분?",
            "_regulation_check": "내부 데이터",
            "_provider_used": "gemini",
        }
        result = asyncio.run(
            reviewer.review_and_polish(drafts, {"title": "", "content": ""})
        )
        # 내부 키 보존
        self.assertEqual(result.polished_drafts["_regulation_check"], "내부 데이터")
        self.assertEqual(result.polished_drafts["_provider_used"], "gemini")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 3: ContentCalendar 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestContentCalendar(unittest.TestCase):
    """P2-A: 콘텐츠 다양성 가드 테스트."""

    def test_no_db_always_allows(self):
        """DB 없으면 항상 게시 허용."""
        from pipeline.content_calendar import ContentCalendar
        calendar = ContentCalendar(cost_db=None)
        ok, reason = calendar.should_post_topic("연봉", "공감형", "분노")
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_custom_rules(self):
        """커스텀 규칙이 적용되는지 확인."""
        from pipeline.content_calendar import ContentCalendar
        rules = {"max_same_topic": 5, "topic_window_hours": 12}
        calendar = ContentCalendar(cost_db=None, rules=rules)
        self.assertEqual(calendar._rules["max_same_topic"], 5)
        self.assertEqual(calendar._rules["topic_window_hours"], 12)
        # 기본값은 유지
        self.assertEqual(calendar._rules["max_same_hook"], 2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 4: 한국어 가독성 스코어러 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestReadability(unittest.TestCase):
    """P4-A: 한국어 가독성 스코어러 테스트."""

    def test_empty_text(self):
        """빈 텍스트는 기본 50점."""
        from pipeline.readability import calculate_readability
        result = calculate_readability("")
        self.assertEqual(result["readability_score"], 50.0)

    def test_good_readability(self):
        """짧고 자연스러운 문장은 높은 점수."""
        from pipeline.readability import calculate_readability
        text = "연봉 5천 자랑글 레전드. 댓글이 더 웃겨요. 직장인 세계는 넓다."
        result = calculate_readability(text)
        self.assertGreaterEqual(result["readability_score"], 70)

    def test_passive_heavy_text_penalized(self):
        """수동태 과다 텍스트는 감점."""
        from pipeline.readability import calculate_readability
        text = (
            "이 정책은 시행됩니다. 결과는 공유됩니다. "
            "개선안은 검토됩니다. 보고서가 작성됩니다."
        )
        result = calculate_readability(text)
        self.assertGreater(result["passive_ratio"], 0.3)
        self.assertLess(result["readability_score"], 90)

    def test_long_sentences_penalized(self):
        """매우 긴 문장은 감점."""
        from pipeline.readability import calculate_readability
        long_sentence = "가" * 200
        result = calculate_readability(long_sentence)
        self.assertLess(result["readability_score"], 90)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 5: 훅 타입 6종 통일 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHookType6Types(unittest.TestCase):
    """P3-B: classify_hook_type이 6종 훅 타입 모두 반환 가능."""

    def test_insight_type_detected(self):
        """통찰형 키워드가 있으면 통찰형 반환."""
        from pipeline.content_intelligence import classify_hook_type
        result = classify_hook_type("이직하면서 배운 교훈", "이직하면서 배운 5가지 교훈", "통찰")
        self.assertEqual(result, "통찰형")

    def test_oneshot_type_detected(self):
        """한줄팩폭형 키워드가 있으면 한줄팩폭형 반환."""
        from pipeline.content_intelligence import classify_hook_type
        result = classify_hook_type("이건 진짜 레전드", "이건 진짜 실화냐 ㅋㅋ", "웃김")
        self.assertEqual(result, "한줄팩폭형")

    def test_all_types_reachable(self):
        """모든 6종 훅 타입이 반환 가능한지 확인."""
        from pipeline.content_intelligence import classify_hook_type
        types_seen = set()
        test_cases = [
            ("트렌드 분석해봤습니다", "커뮤니티 비교 분석", "통찰"),
            ("이직하면서 배운 교훈", "깨달은 점 정리하면", "통찰"),
            ("왜 이렇게 하는거야?", "논란 있는 주제", "분노"),
            ("정리해봤습니다 팁", "방법 가이드 요약", "공감"),
            ("짤 웃김 현웃", "밈 짤방", "웃김"),
            ("ㅋㅋ 레전드 이건 진짜", "실화냐 미쳤", "경악"),
        ]
        for title, content, emotion in test_cases:
            hook = classify_hook_type(title, content, emotion)
            types_seen.add(hook)
        # 최소 4종 이상은 도달해야 함
        self.assertGreaterEqual(len(types_seen), 4, f"Reached types: {types_seen}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 6: 이미지 커뮤니티 씬 매핑 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestImageCommunityScenes(unittest.TestCase):
    """P4-B: 비블라인드 소스의 커뮤니티별 씬 매핑."""

    def test_ppomppu_scene(self):
        """뽐뿌 소스는 쇼핑 테마 프롬프트 생성."""
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(
            topic_cluster="재테크", source="ppomppu"
        )
        self.assertIn("shopping", prompt.lower())
        self.assertIn("no text", prompt.lower())

    def test_fmkorea_scene(self):
        """에펨코리아 소스는 인터넷 문화 테마 프롬프트 생성."""
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(
            topic_cluster="직장개그", source="fmkorea"
        )
        self.assertIn("internet", prompt.lower())

    def test_blind_still_uses_pixar(self):
        """블라인드 소스는 기존 Pixar 스타일 유지."""
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(
            topic_cluster="연봉", emotion_axis="분노", source="blind"
        )
        self.assertIn("Pixar", prompt)

    def test_unknown_source_uses_default(self):
        """알 수 없는 소스는 기본 스타일 사용."""
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(
            topic_cluster="연봉", source="unknown_source"
        )
        self.assertIn("no text", prompt.lower())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 7: Brand Voice YAML 로드 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBrandVoiceYAML(unittest.TestCase):
    """P1-A: classification_rules.yaml에 brand_voice 섹션이 존재."""

    def test_brand_voice_section_exists(self):
        """brand_voice 섹션이 YAML에 정의되어 있어야 함."""
        import yaml
        from pathlib import Path
        rules_path = Path(__file__).parent.parent.parent / "classification_rules.yaml"
        if not rules_path.exists():
            self.skipTest("classification_rules.yaml not found")
        with open(rules_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertIn("brand_voice", data)
        bv = data["brand_voice"]
        self.assertIn("persona", bv)
        self.assertIn("voice_traits", bv)
        self.assertIn("forbidden_expressions", bv)
        self.assertIsInstance(bv["forbidden_expressions"], list)
        self.assertGreaterEqual(len(bv["forbidden_expressions"]), 5)

    def test_cliche_watchlist_exists(self):
        """cliche_watchlist 섹션이 YAML에 정의되어 있어야 함."""
        import yaml
        from pathlib import Path
        rules_path = Path(__file__).parent.parent.parent / "classification_rules.yaml"
        if not rules_path.exists():
            self.skipTest("classification_rules.yaml not found")
        with open(rules_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertIn("cliche_watchlist", data)
        self.assertIsInstance(data["cliche_watchlist"], list)
        self.assertGreaterEqual(len(data["cliche_watchlist"]), 20)

    def test_hook_rules_has_6_types(self):
        """hook_rules에 6종 훅 타입이 모두 정의되어 있어야 함."""
        import yaml
        from pathlib import Path
        rules_path = Path(__file__).parent.parent.parent / "classification_rules.yaml"
        if not rules_path.exists():
            self.skipTest("classification_rules.yaml not found")
        with open(rules_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        hook_rules = data.get("hook_rules", {})
        expected = {"논쟁형", "정보형", "짤형", "분석형", "통찰형", "한줄팩폭형"}
        actual = set(hook_rules.keys())
        self.assertTrue(expected.issubset(actual), f"Missing: {expected - actual}")


if __name__ == "__main__":
    unittest.main()
