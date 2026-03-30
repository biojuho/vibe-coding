"""Unit tests for pipeline.regulation_checker (P7)."""

from __future__ import annotations

import unittest


class TestRegulationChecker(unittest.TestCase):
    """RegulationChecker 핵심 기능 테스트."""

    def setUp(self):
        """테스트마다 캐시를 초기화합니다."""
        from pipeline.regulation_checker import reload_regulations

        reload_regulations()  # 캐시 리셋

    def _make_checker(self):
        from pipeline.regulation_checker import RegulationChecker

        return RegulationChecker()

    # ─── 규제 데이터 로드 ───────────────────────────────────────────

    def test_load_regulations_from_yaml(self):
        """classification_rules.yaml에서 규제 데이터를 정상 로드하는지 확인."""
        checker = self._make_checker()
        self.assertIsInstance(checker.regulations, dict)
        # 최소 3개 플랫폼 규제가 로드되어야 함
        self.assertIn("x_twitter", checker.regulations)
        self.assertIn("threads", checker.regulations)
        self.assertIn("naver_blog", checker.regulations)

    def test_get_platform_rules(self):
        """특정 플랫폼 규제 데이터 반환 확인."""
        checker = self._make_checker()
        rules = checker.get_platform_rules("x_twitter")
        self.assertEqual(rules.get("display_name"), "X (Twitter)")
        self.assertEqual(rules.get("max_length"), 280)
        self.assertIn("do_checklist", rules)
        self.assertIn("dont_checklist", rules)

    def test_get_do_dont_checklist(self):
        """Do/Don't 체크리스트 반환 확인."""
        checker = self._make_checker()
        checklist = checker.get_do_dont_checklist("x_twitter")
        self.assertIsInstance(checklist["do"], list)
        self.assertIsInstance(checklist["dont"], list)
        self.assertTrue(len(checklist["do"]) > 0)
        self.assertTrue(len(checklist["dont"]) > 0)

    def test_get_algorithm_tips(self):
        """알고리즘 우대 요소 반환 확인."""
        checker = self._make_checker()
        tips = checker.get_algorithm_tips("threads")
        self.assertIsInstance(tips, list)
        self.assertTrue(len(tips) > 0)

    # ─── 규제 컨텍스트 생성 ────────────────────────────────────────

    def test_build_regulation_context_all(self):
        """전체 플랫폼 규제 컨텍스트 생성 확인."""
        checker = self._make_checker()
        ctx = checker.build_regulation_context()
        self.assertIn("플랫폼 규제 준수 가이드", ctx)
        self.assertIn("X (Twitter)", ctx)
        self.assertIn("Threads", ctx)
        self.assertIn("네이버 블로그", ctx)
        self.assertIn("✅", ctx)
        self.assertIn("❌", ctx)

    def test_build_regulation_context_specific_platforms(self):
        """특정 플랫폼만 컨텍스트 생성 확인."""
        checker = self._make_checker()
        ctx = checker.build_regulation_context(platforms=["x_twitter"])
        self.assertIn("X (Twitter)", ctx)
        # threads와 naver_blog는 포함되지 않아야 함
        self.assertNotIn("Threads", ctx)
        self.assertNotIn("네이버 블로그", ctx)

    def test_build_regulation_context_empty_when_no_data(self):
        """규제 데이터가 없으면 빈 문자열 반환."""
        from pipeline.regulation_checker import RegulationChecker

        checker = RegulationChecker()
        checker.regulations = {}  # 강제 비우기
        ctx = checker.build_regulation_context()
        self.assertEqual(ctx, "")

    # ─── X (Twitter) 검증 ─────────────────────────────────────────

    def test_validate_twitter_pass(self):
        """정상 트윗 검증 통과 확인."""
        checker = self._make_checker()
        content = "블라인드에서 화제인 연봉 이야기. 직장인이면 다들 공감할 듯... 여러분 연봉은 어떠세요? 😂"
        report = checker.validate_twitter(content)
        self.assertTrue(report.passed)
        self.assertEqual(report.score, 100)

    def test_validate_twitter_too_long(self):
        """280자 초과 트윗 검증 실패 확인."""
        checker = self._make_checker()
        content = "A" * 300
        report = checker.validate_twitter(content)
        self.assertFalse(report.passed)
        self.assertLess(report.score, 100)

    def test_validate_twitter_link_only(self):
        """외부 링크 단독 트윗 검증 실패 확인."""
        checker = self._make_checker()
        content = "https://example.com/long-article"
        report = checker.validate_twitter(content)
        self.assertFalse(report.passed)

    def test_validate_twitter_hashtag_limit(self):
        """해시태그 초과 감지 확인."""
        checker = self._make_checker()
        content = "테스트 트윗입니다 #태그1 #태그2 #태그3 #태그4 #태그5"
        report = checker.validate_twitter(content)
        # 3개 초과이므로 점수 차감
        self.assertLess(report.score, 100)

    # ─── Threads 검증 ─────────────────────────────────────────────

    def test_validate_threads_pass(self):
        """정상 Threads 포스트 검증 통과 확인."""
        checker = self._make_checker()
        content = "월요일 아침부터 팀장님이 '우리 팀은 수평적이야'라고 하셨는데\n그 말 끝나기도 전에 '야, 이거 다시 해와' 🙃\n#직장인 #현실 #공감"
        report = checker.validate_threads(content)
        self.assertTrue(report.passed)

    def test_validate_threads_external_link(self):
        """Threads 외부 링크 경고 확인."""
        checker = self._make_checker()
        content = "이 글 꼭 읽어보세요 https://example.com/article\n정말 좋은 내용이에요\n#추천"
        report = checker.validate_threads(content)
        # 외부 링크는 warning이므로 passed는 True일 수 있지만 점수 차감
        self.assertLess(report.score, 100)

    def test_validate_threads_commercial_cta(self):
        """Threads 상업적 CTA 감지 확인."""
        checker = self._make_checker()
        content = "오늘만 할인! 이 쿠폰 사용하면 50% 할인 받으세요. 광고"
        report = checker.validate_threads(content)
        self.assertFalse(report.passed)

    # ─── 네이버 블로그 검증 ───────────────────────────────────────

    def test_validate_naver_blog_pass(self):
        """정상 네이버 블로그 글 검증 통과 확인."""
        checker = self._make_checker()
        # 다양한 고유 문장으로 구성 (중복 문장/키워드 도배 방지)
        paragraphs = [
            "## 2024 직장인 연봉 현실 총정리",
            "블라인드에서 화제된 급여 관련 이야기를 정리했습니다.",
            "직장생활을 하다 보면 자연스럽게 보상에 대한 고민이 생깁니다.",
            "특히 동료와의 비교는 피할 수 없는 현실이죠.",
            "최근 조사에 따르면 대기업과 중소기업의 격차가 더 벌어지고 있습니다.",
            "IT 업계의 경우 스타트업과 대기업 간 차이가 1.5배에 달합니다.",
            "금융권은 여전히 높은 보상 수준을 유지하고 있으며 성과급 비중이 큽니다.",
            "",
            "## 실제 사례로 보는 현실",
            "A씨는 중견기업에서 5년 근무 후 대기업으로 이직했습니다.",
            "이직 후 기본급이 30% 상승했고 복지도 크게 개선되었습니다.",
            "반면 B씨는 스타트업에서 스톡옵션을 받아 장기적 관점에서 투자했죠.",
            "각자의 선택에 따라 결과는 크게 달라질 수 있습니다.",
            "중요한 것은 비교보다 나에게 맞는 전략을 찾는 것이라 봅니다.",
            "커리어 설계는 단기가 아닌 5년, 10년 장기 관점이 필요합니다.",
            "",
            "## 효과적인 협상 전략 가이드",
            "협상 전 시장 데이터를 충분히 조사하는 것이 핵심입니다.",
            "잡플래닛이나 블라인드에서 동종 업계 정보를 미리 파악하세요.",
            "면접 시 현재 수준과 희망 수준의 근거를 구체적으로 제시해야 합니다.",
            "네트워크 활용도 중요한 전략 중 하나입니다.",
            "헤드헌터와의 관계를 꾸준히 유지하면 기회가 더 많아집니다.",
            "자격증이나 포트폴리오 등 객관적 증빙도 준비하면 좋습니다.",
            "",
            "## 마무리하며",
            "여러분은 현재 보상 수준에 만족하시나요?",
            "경험을 바탕으로 한 현실적인 조언이 도움이 되었기를 바랍니다.",
            "댓글로 여러분의 생각을 공유해 주세요.",
            "",
            "#연봉 #직장인 #연봉협상 #성과급 #월급 #인상 #블라인드 #커리어 #이직 #취업 #연봉정보 #평균연봉",
        ]
        content = "\n".join(paragraphs)
        report = checker.validate_naver_blog(content)
        self.assertTrue(report.passed)

    def test_validate_naver_blog_too_short(self):
        """500자 미만 네이버 블로그 글 검증 실패 확인."""
        checker = self._make_checker()
        content = "짧은 블로그 글입니다."
        report = checker.validate_naver_blog(content)
        self.assertFalse(report.passed)

    def test_validate_naver_blog_no_subheadings(self):
        """소제목 없는 네이버 블로그 글 점수 차감 확인."""
        checker = self._make_checker()
        content = "소제목 없이 작성된 긴 글입니다. " * 100
        report = checker.validate_naver_blog(content)
        self.assertLess(report.score, 100)

    # ─── 일괄 검증 ─────────────────────────────────────────────────

    def test_validate_all_drafts(self):
        """모든 플랫폼 드래프트 일괄 검증 확인."""
        checker = self._make_checker()
        drafts = {
            "twitter": "블라인드에서 화제! 직장인이면 공감할 이야기 😂",
            "threads": "월요일 아침에 이런 일이 ㅋㅋ\n#직장 #현실 #공감",
            "naver_blog": "",  # 빈 콘텐츠
        }
        reports = checker.validate_all_drafts(drafts)
        self.assertIn("twitter", reports)
        self.assertIn("threads", reports)
        self.assertIn("naver_blog", reports)
        # naver_blog는 빈 콘텐츠이므로 콘텐츠 존재 검증 실패
        self.assertFalse(reports["naver_blog"].items[0].passed)

    def test_format_validation_summary(self):
        """통합 검증 요약 포맷 확인."""
        checker = self._make_checker()
        drafts = {
            "twitter": "블라인드에서 화제! 직장인이면 공감할 이야기 😂",
            "threads": "월요일 아침에 이런 일이 ㅋㅋ\n#직장 #현실 #공감",
        }
        reports = checker.validate_all_drafts(drafts)
        summary = checker.format_validation_summary(reports)
        self.assertIn("플랫폼 규제 준수 검증 리포트", summary)
        self.assertIn("━", summary)

    # ─── ValidationReport 유틸 ──────────────────────────────────────

    def test_validation_report_to_dict(self):
        """ValidationReport dict 변환 확인."""
        from pipeline.regulation_checker import ValidationReport

        report = ValidationReport(platform="test")
        report.add("테스트 규칙", True, "OK")
        report.add("위반 규칙", False, "위반 감지", severity="error")
        data = report.to_dict()
        self.assertEqual(data["platform"], "test")
        self.assertFalse(data["passed"])
        self.assertEqual(len(data["items"]), 2)

    def test_validation_report_score_clamp(self):
        """점수가 0 이하로 내려가지 않는지 확인."""
        from pipeline.regulation_checker import ValidationReport

        report = ValidationReport(platform="test")
        for i in range(20):
            report.add(f"위반 {i}", False, "문제", severity="error")
        self.assertEqual(report.score, 0)


class TestRegulationCheckerReload(unittest.TestCase):
    """reload_regulations 동작 테스트."""

    def test_reload_clears_cache(self):
        """reload_regulations가 캐시를 초기화하는지 확인."""
        from pipeline.regulation_checker import _load_regulations, reload_regulations

        _load_regulations()  # 1회 로드
        from pipeline import regulation_checker

        self.assertIsNotNone(regulation_checker._regulation_cache)
        reload_regulations()
        self.assertIsNone(regulation_checker._regulation_cache)


if __name__ == "__main__":
    unittest.main()
