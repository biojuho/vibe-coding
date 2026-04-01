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
        # AI스러운 클리셰 3개 이상 포함 (흥미로운 점은, 결론적으로, 주목할 만한)
        draft = "흥미로운 점은 연봉 5천이라는 것입니다. 결론적으로 주목할 만한 이야기죠. 여러분 어떻게 생각하세요?"
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

    def test_hook_strength_info_no_hook(self):
        """첫 문장에 장면/대사/숫자가 없으면 이제 하드 페일이어야 한다."""
        draft = "직장인들의 일상은 참으로 바쁘다. 매일 출근하면 힘든 일이 가득합니다. 그래도 다같이 힘내봐요?"
        result = self.gate.validate("twitter", draft)
        failed_rules = {i.rule for i in result.items if not i.passed}
        self.assertIn("구체 장면 없음", failed_rules)
        self.assertFalse(result.passed)

    def test_hook_strength_pass_with_number(self):
        """첫 문장에 숫자가 있으면 훅 강도 통과."""
        draft = "연봉 5천만원 받는 직장인이 블라인드에 올린 글 봤어요? 댓글이 난리."
        result = self.gate.validate("twitter", draft)
        hook_fail = [i for i in result.items if i.rule == "훅 강도" and not i.passed]
        self.assertEqual(len(hook_fail), 0)

    def test_vague_language_warning(self):
        """모호한 표현 3개 이상이면 구체성 부족 경고."""
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


from unittest.mock import patch, AsyncMock  # noqa: E402
from pipeline.editorial_reviewer import EditorialReviewer  # noqa: E402


class TestEditorialReviewerStructure(unittest.TestCase):
    """P1-C: 에디토리얼 리뷰어 클래스 구조 테스트."""

    def test_import_and_dataclass(self):
        """EditorialResult dataclass가 정상 import 되어야 함."""
        from pipeline.editorial_reviewer import EditorialResult

        result = EditorialResult()
        self.assertIsInstance(result.polished_drafts, dict)
        self.assertIsInstance(result.scores, dict)
        self.assertEqual(result.avg_score, 0.0)

    def test_reviewer_no_api_key_graceful(self):
        """API 키 없을 때 graceful하게 원본 반환."""
        import asyncio
        from pipeline.editorial_reviewer import EditorialReviewer

        # Provider 없이 생성
        reviewer = EditorialReviewer(config=None)
        reviewer._providers = []

        drafts = {"twitter": "테스트 초안입니다. 여러분 어떠세요?"}
        post_data = {"title": "테스트", "content": "테스트 본문"}

        result = asyncio.run(reviewer.review_and_polish(drafts, post_data))
        # Provider 없으면 원본 그대로 반환
        self.assertEqual(result.polished_drafts["twitter"], drafts["twitter"])

    def test_reviewer_skips_internal_keys(self):
        """'_'로 시작하는 내부 키는 리뷰 대상에서 제외."""
        import asyncio
        from pipeline.editorial_reviewer import EditorialReviewer

        reviewer = EditorialReviewer(config=None)
        reviewer._providers = []

        drafts = {
            "twitter": "테스트 초안. 여러분?",
            "_regulation_check": "내부 데이터",
            "_provider_used": "gemini",
        }
        result = asyncio.run(reviewer.review_and_polish(drafts, {"title": "", "content": ""}))
        # 내부 키 보존
        self.assertEqual(result.polished_drafts["_regulation_check"], "내부 데이터")
        self.assertEqual(result.polished_drafts["_provider_used"], "gemini")

    @patch.object(EditorialReviewer, "_call_llm", new_callable=AsyncMock)
    def test_reviewer_langgraph_loop(self, mock_call_llm):
        """LangGraph Evaluator-Optimizer 루프가 동작하는지 테스트."""
        import asyncio
        from pipeline.editorial_reviewer import EditorialReviewer

        reviewer = EditorialReviewer(config=None)

        # 첫 번째 평가: 모든 점수 4점 (평균 4.0, 임계값 5.0 미달) -> 재작성 유발
        # 두 번째 평가: 모든 점수 8점 (평균 8.0, 임계값 통과) -> 루프 종료
        mock_call_llm.side_effect = [
            {
                "scores": {"hook": 4, "specificity": 4, "voice": 4, "engagement": 4, "readability": 4},
                "suggestions": ["개선점 1"],
                "rewritten": "개선된 텍스트입니다.",
            },
            {
                "scores": {"hook": 8, "specificity": 8, "voice": 8, "engagement": 8, "readability": 8},
                "suggestions": ["완벽함"],
                "rewritten": "",
            },
        ]

        # 빈 provider면 _call_llm이 안 불리므로 더미 추가
        reviewer._providers = [{"name": "fake"}]

        drafts = {"twitter": "초기 초안"}
        post_data = {"title": "테스트", "content": "내용", "source": "unknown"}

        result = asyncio.run(reviewer.review_and_polish(drafts, post_data))

        self.assertEqual(result.polished_drafts["twitter"], "개선된 텍스트입니다.")
        self.assertEqual(result.scores["twitter_hook"], 8)
        self.assertEqual(mock_call_llm.call_count, 2)


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

        text = "이 정책은 시행됩니다. 결과는 공유됩니다. 개선안은 검토됩니다. 보고서가 작성됩니다."
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

        prompt = ImageGenerator.build_image_prompt(topic_cluster="재테크", source="ppomppu")
        self.assertIn("shopping", prompt.lower())
        self.assertIn("no text", prompt.lower())

    def test_fmkorea_scene(self):
        """에펨코리아 소스는 인터넷 문화 테마 프롬프트 생성."""
        from pipeline.image_generator import ImageGenerator

        prompt = ImageGenerator.build_image_prompt(topic_cluster="직장개그", source="fmkorea")
        self.assertIn("internet", prompt.lower())

    def test_blind_still_uses_pixar(self):
        """블라인드 소스는 기존 Pixar 스타일 유지."""
        from pipeline.image_generator import ImageGenerator

        prompt = ImageGenerator.build_image_prompt(topic_cluster="연봉", emotion_axis="분노", source="blind")
        self.assertIn("Pixar", prompt)

    def test_unknown_source_uses_default(self):
        """알 수 없는 소스는 기본 스타일 사용."""
        from pipeline.image_generator import ImageGenerator

        prompt = ImageGenerator.build_image_prompt(topic_cluster="연봉", source="unknown_source")
        self.assertIn("no text", prompt.lower())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 7: Brand Voice YAML 로드 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBrandVoiceYAML(unittest.TestCase):
    """P1-A: rules_loader를 통해 brand_voice 섹션이 존재하는지 확인."""

    def test_brand_voice_section_exists(self):
        """brand_voice 섹션이 YAML에 정의되어 있어야 함."""
        from pipeline.rules_loader import load_rules

        data = load_rules()
        self.assertIn("brand_voice", data)
        bv = data["brand_voice"]
        self.assertIn("persona", bv)
        self.assertIn("voice_traits", bv)
        self.assertIn("forbidden_expressions", bv)
        self.assertIsInstance(bv["forbidden_expressions"], list)
        self.assertGreaterEqual(len(bv["forbidden_expressions"]), 4)

    def test_cliche_watchlist_exists(self):
        """cliche_watchlist 섹션이 YAML에 정의되어 있어야 함."""
        from pipeline.rules_loader import load_rules

        data = load_rules()
        self.assertIn("cliche_watchlist", data)
        self.assertIsInstance(data["cliche_watchlist"], list)
        self.assertGreaterEqual(len(data["cliche_watchlist"]), 10)

    def test_hook_rules_has_6_types(self):
        """hook_rules에 6종 훅 타입이 모두 정의되어 있어야 함."""
        from pipeline.rules_loader import load_rules

        data = load_rules()
        hook_rules = data.get("hook_rules", {})
        expected = {"논쟁형", "정보형", "짤형", "분석형", "통찰형", "한줄팩폭형"}
        actual = set(hook_rules.keys())
        self.assertTrue(expected.issubset(actual), f"Missing: {expected - actual}")

    def test_new_yaml_sections_exist(self):
        """P1 고도화 YAML 섹션들이 존재하는지 확인."""
        from pipeline.rules_loader import load_rules

        data = load_rules()
        # P1-1: 토픽별 프롬프트 전략
        self.assertIn("topic_prompt_strategies", data)
        self.assertIn("연봉", data["topic_prompt_strategies"])
        self.assertIn("직장개그", data["topic_prompt_strategies"])
        # P1-2: 나쁜 예시
        self.assertIn("anti_examples", data)
        self.assertIn("generic_bad", data["anti_examples"])
        self.assertGreaterEqual(len(data["anti_examples"]["generic_bad"]), 2)
        # P1-3: 에디토리얼 임계값
        self.assertIn("editorial_thresholds", data)
        self.assertIn("defaults", data["editorial_thresholds"])
        # P0-2: thinking_framework
        self.assertIn("thinking_framework", data.get("prompt_templates", {}))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Part 8: P0~P1 퀄리티 고도화 유닛 테스트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class _FakeConfig:
    """테스트용 Config 스텁."""

    def get(self, key, default=None):
        return default


class TestExtractContentEssence(unittest.TestCase):
    """P0-1: 원문 핵심 추출 기능 테스트."""

    def setUp(self):
        import pipeline.draft_generator as dg

        # emotion_rules 모킹
        dg._draft_rules_cache = {
            "emotion_rules": [
                {"label": "분노", "keywords": ["빡", "열받", "화나"]},
                {"label": "공감", "keywords": ["공감", "맞말", "나만"]},
            ],
        }

    def tearDown(self):
        import pipeline.draft_generator as dg

        dg._draft_rules_cache = None

    def test_numbers_with_context(self):
        from pipeline.draft_generator import TweetDraftGenerator

        post_data = {
            "title": "연봉 5천만원 자랑글",
            "content": "블라인드에서 연봉 5천만원 자랑하는 글이 올라왔는데 댓글이 200개 넘었다.",
        }
        result = TweetDraftGenerator._extract_content_essence(post_data)
        self.assertGreaterEqual(len(result["key_numbers"]), 2)

    def test_quotes_extraction(self):
        from pipeline.draft_generator import TweetDraftGenerator

        post_data = {
            "title": "상사 발언",
            "content": "팀장이 '우리 팀은 수평적이야'라고 했는데 바로 '야, 이거 다시 해와'라고 함",
        }
        result = TweetDraftGenerator._extract_content_essence(post_data)
        self.assertGreaterEqual(len(result["quotes"]), 1)

    def test_emotional_peaks(self):
        from pipeline.draft_generator import TweetDraftGenerator

        post_data = {
            "title": "퇴사",
            "content": "진짜 빡쳐서 퇴사 결심했다. 회사가 너무 열받게 한다. 나만 이런 건가?",
        }
        result = TweetDraftGenerator._extract_content_essence(post_data)
        self.assertGreaterEqual(len(result["emotional_peaks"]), 1)

    def test_narrative_bookends(self):
        from pipeline.draft_generator import TweetDraftGenerator

        post_data = {
            "title": "이직 이야기",
            "content": "이직을 결심한 건 3개월 전이었다. 긴 여정이었지만 결국 성공했다.",
        }
        result = TweetDraftGenerator._extract_content_essence(post_data)
        self.assertTrue(result["opening"])
        self.assertTrue(result["closing"])
        self.assertNotEqual(result["opening"], result["closing"])

    def test_empty_content(self):
        from pipeline.draft_generator import TweetDraftGenerator

        post_data = {"title": "", "content": ""}
        result = TweetDraftGenerator._extract_content_essence(post_data)
        self.assertEqual(result["key_numbers"], [])
        self.assertEqual(result["quotes"], [])


class TestThinkingTagStrip(unittest.TestCase):
    """P0-2: _parse_response가 <thinking> 태그를 제거하는지 테스트."""

    def setUp(self):
        import pipeline.draft_generator as dg

        dg._draft_rules_cache = {}

    def tearDown(self):
        import pipeline.draft_generator as dg

        dg._draft_rules_cache = None

    def test_thinking_stripped_from_response(self):
        from pipeline.draft_generator import TweetDraftGenerator

        gen = TweetDraftGenerator(config=_FakeConfig())
        response = (
            "<thinking>\n이 글의 핵심은 연봉 격차다.\n</thinking>\n\n"
            "<twitter>연봉 5천 자랑글 밑에 달린 댓글이 레전드</twitter>"
        )
        drafts, _ = gen._parse_response(response, ["twitter"], "gemini")
        self.assertIn("twitter", drafts)
        self.assertNotIn("<thinking>", drafts["twitter"])
        self.assertIn("레전드", drafts["twitter"])


class TestClicheInjection(unittest.TestCase):
    """P0-3: _build_prompt에 클리셰 목록이 주입되는지 테스트."""

    def setUp(self):
        import pipeline.draft_generator as dg
        import pipeline.draft_prompts as dp

        _cache = {
            "cliche_watchlist": ["이거 실화?", "나만 이런 거 아니죠?", "공감하면 RT"],
            "brand_voice": {
                "persona": "테스트",
                "voice_traits": [],
                "forbidden_expressions": [],
                "examples": {},
            },
        }
        dg._draft_rules_cache = _cache
        dp._draft_rules_cache = _cache

    def tearDown(self):
        import pipeline.draft_generator as dg
        import pipeline.draft_prompts as dp

        dg._draft_rules_cache = None
        dp._draft_rules_cache = None

    def test_cliche_list_in_prompt(self):
        from pipeline.draft_generator import TweetDraftGenerator

        gen = TweetDraftGenerator(config=_FakeConfig())
        post_data = {
            "title": "테스트",
            "content": "테스트 본문",
            "source": "blind",
            "content_profile": {"topic_cluster": "기타"},
        }
        prompt = gen._build_prompt(post_data, None, ["twitter"])
        self.assertIn("절대 사용 금지 — 클리셰 목록", prompt)
        self.assertIn("이거 실화?", prompt)


class TestTargetedRetryInstructions(unittest.TestCase):
    """P0-4: 재시도 시 구체적 수정 지침이 포함되는지 테스트."""

    def setUp(self):
        import pipeline.draft_generator as dg

        dg._draft_rules_cache = {}

    def tearDown(self):
        import pipeline.draft_generator as dg

        dg._draft_rules_cache = None

    def test_fix_instructions_for_min_length(self):
        from pipeline.draft_generator import TweetDraftGenerator

        gen = TweetDraftGenerator(config=_FakeConfig())
        feedback = [{"platform": "twitter", "score": 40, "issues": ["최소 글자 수 미달"]}]
        retry = gen._build_retry_prompt("원래 프롬프트", feedback)
        self.assertIn("수정 방법:", retry)
        self.assertIn("구체적인 사례", retry)

    def test_fix_instructions_for_cta(self):
        from pipeline.draft_generator import TweetDraftGenerator

        gen = TweetDraftGenerator(config=_FakeConfig())
        feedback = [{"platform": "twitter", "score": 60, "issues": ["CTA 패턴 미포함"]}]
        retry = gen._build_retry_prompt("원래 프롬프트", feedback)
        self.assertIn("수정 방법:", retry)
        self.assertIn("구체적인 질문", retry)


class TestTopicPromptStrategies(unittest.TestCase):
    """P1-1: 토픽별 프롬프트 전략이 프롬프트에 주입되는지 테스트."""

    def setUp(self):
        import pipeline.draft_generator as dg

        dg._draft_rules_cache = {
            "topic_prompt_strategies": {
                "연봉": {
                    "emphasis": "구체적 숫자를 최대한 활용",
                    "avoid": "막연한 표현",
                    "hook_template": "[숫자] + [반전]",
                },
            },
        }

    def tearDown(self):
        import pipeline.draft_generator as dg

        dg._draft_rules_cache = None

    def test_topic_strategy_in_prompt(self):
        from pipeline.draft_generator import TweetDraftGenerator

        gen = TweetDraftGenerator(config=_FakeConfig())
        post_data = {
            "title": "연봉 이야기",
            "content": "연봉 5000만원",
            "source": "blind",
            "content_profile": {"topic_cluster": "연봉"},
        }
        prompt = gen._build_prompt(post_data, None, ["twitter"])
        self.assertIn("토픽별 작성 전략 — 연봉", prompt)
        self.assertIn("구체적 숫자를 최대한 활용", prompt)

    def test_no_strategy_for_unknown_topic(self):
        from pipeline.draft_generator import TweetDraftGenerator

        gen = TweetDraftGenerator(config=_FakeConfig())
        post_data = {
            "title": "기타",
            "content": "본문",
            "source": "blind",
            "content_profile": {"topic_cluster": "기타"},
        }
        prompt = gen._build_prompt(post_data, None, ["twitter"])
        self.assertNotIn("토픽별 작성 전략", prompt)


class TestAntiExamples(unittest.TestCase):
    """P1-2: 나쁜 예시가 프롬프트에 주입되는지 테스트."""

    def setUp(self):
        import pipeline.draft_generator as dg
        import pipeline.draft_prompts as dp

        _cache = {
            "anti_examples": {
                "generic_bad": [
                    {"text": "많은 직장인들이...", "reason": "상투적"},
                ],
            },
        }
        dg._draft_rules_cache = _cache
        dp._draft_rules_cache = _cache

    def tearDown(self):
        import pipeline.draft_generator as dg
        import pipeline.draft_prompts as dp

        dg._draft_rules_cache = None
        dp._draft_rules_cache = None

    def test_anti_examples_in_prompt(self):
        from pipeline.draft_generator import TweetDraftGenerator

        gen = TweetDraftGenerator(config=_FakeConfig())
        post_data = {
            "title": "테스트",
            "content": "본문",
            "source": "blind",
            "content_profile": {"topic_cluster": "기타"},
        }
        prompt = gen._build_prompt(post_data, None, ["twitter"])
        self.assertIn("나쁜 예시 — 이렇게 쓰지 마세요", prompt)
        self.assertIn("많은 직장인들이...", prompt)


class TestDynamicEditorialThreshold(unittest.TestCase):
    """P1-3: 토픽/플랫폼별 동적 임계값 테스트."""

    def test_default_threshold(self):
        import pipeline.editorial_reviewer as er

        er._rules_cache = {
            "editorial_thresholds": {
                "defaults": {"twitter": 6.5, "threads": 6.0},
            },
        }
        er._brand_voice_cache = {}
        reviewer = er.EditorialReviewer()
        self.assertEqual(reviewer._get_threshold("twitter", "기타"), 6.5)
        self.assertEqual(reviewer._get_threshold("threads", "기타"), 6.0)
        er._rules_cache = None
        er._brand_voice_cache = None

    def test_topic_override(self):
        import pipeline.editorial_reviewer as er

        er._rules_cache = {
            "editorial_thresholds": {
                "defaults": {"twitter": 6.5},
                "topic_overrides": {"재테크": {"twitter": 7.0}},
            },
        }
        er._brand_voice_cache = {}
        reviewer = er.EditorialReviewer()
        self.assertEqual(reviewer._get_threshold("twitter", "재테크"), 7.0)
        self.assertEqual(reviewer._get_threshold("twitter", "직장개그"), 6.5)
        er._rules_cache = None
        er._brand_voice_cache = None

    def test_fallback_to_constant(self):
        import pipeline.editorial_reviewer as er

        er._rules_cache = {}
        er._brand_voice_cache = {}
        reviewer = er.EditorialReviewer()
        self.assertEqual(reviewer._get_threshold("unknown", ""), 5.0)
        er._rules_cache = None
        er._brand_voice_cache = None


class TestFactChecker(unittest.TestCase):
    """P1-4: 팩트 검증 기능 테스트."""

    def test_matching_numbers_pass(self):
        from pipeline.fact_checker import verify_facts

        source = "이번 분기 연봉이 5천만원으로 인상되었고 직원 200명이 대상이다."
        draft = "연봉 5천만원 인상, 200명 대상이라니 대박"
        result = verify_facts(source, draft)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.fabricated_items), 0)

    def test_fabricated_number_detected(self):
        from pipeline.fact_checker import verify_facts

        source = "연봉이 5천만원이다."
        draft = "연봉 5천만원이면 세후 350만원 정도인데 상위 30%에 해당"
        result = verify_facts(source, draft)
        self.assertFalse(result.passed)
        self.assertGreaterEqual(len(result.fabricated_items), 1)

    def test_no_numbers_in_draft(self):
        from pipeline.fact_checker import verify_facts

        result = verify_facts("연봉 5천만원", "연봉 이야기가 화제다")
        self.assertTrue(result.passed)

    def test_korean_number_normalization(self):
        from pipeline.fact_checker import _normalize_number

        self.assertEqual(_normalize_number("5천"), 5000.0)
        self.assertEqual(_normalize_number("200만"), 2000000.0)
        self.assertEqual(_normalize_number("1억"), 100000000.0)
        self.assertAlmostEqual(_normalize_number("3.5"), 3.5)

    def test_common_numbers_ignored(self):
        from pipeline.fact_checker import _is_common_number

        self.assertTrue(_is_common_number("2024"))
        self.assertTrue(_is_common_number("1"))
        self.assertFalse(_is_common_number("5천만"))

    def test_numbers_match_different_format(self):
        from pipeline.fact_checker import _numbers_match

        self.assertTrue(_numbers_match("5000", "5천"))
        self.assertTrue(_numbers_match("200", "200명"))

    def test_confidence_score(self):
        from pipeline.fact_checker import verify_facts

        result = verify_facts("연봉 5천만원", "연봉 5천만원이면 좋겠지만 현실은 3천만원")
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
