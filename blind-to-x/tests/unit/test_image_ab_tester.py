"""이미지 A/B 테스터 유닛 테스트.

커버리지:
  - ImageABTester: 변형 생성, 성과 비교, 위너 결정, 리포트 생성
  - ImageVariant / ABTestResult 데이터 클래스
  - build_image_prompt variant 파라미터 호환성
"""
from __future__ import annotations

import sys
from pathlib import Path


_BTX_ROOT = Path(__file__).resolve().parent.parent
if str(_BTX_ROOT) not in sys.path:
    sys.path.insert(0, str(_BTX_ROOT))


from pipeline.image_ab_tester import ImageABTester, ImageVariant, ABTestResult  # noqa: E402


class TestVariantGeneration:
    def _tester(self):
        return ImageABTester()

    def test_generates_default_and_alt(self):
        t = self._tester()
        variants = t.generate_variants("연봉", "분노", "연봉 협상 실패")
        assert len(variants) >= 2
        assert variants[0].variant_id == "A"
        assert variants[0].variant_type == "default"
        assert variants[1].variant_id == "B"
        assert variants[1].variant_type == "alt_style"

    def test_generates_three_variants(self):
        t = self._tester()
        variants = t.generate_variants("이직", "공감", "이직 후기", max_variants=3)
        assert len(variants) == 3
        types = {v.variant_type for v in variants}
        assert "default" in types
        assert "alt_style" in types
        assert "alt_mood" in types

    def test_limits_to_two_variants(self):
        t = self._tester()
        variants = t.generate_variants("직장개그", "웃김", "", max_variants=2)
        assert len(variants) == 2

    def test_variant_has_prompt(self):
        t = self._tester()
        variants = t.generate_variants("연봉", "분노")
        for v in variants:
            assert v.prompt != ""
            assert "workplace" in v.prompt.lower() or "office" in v.prompt.lower()

    def test_variant_to_dict(self):
        v = ImageVariant(
            variant_id="A",
            variant_type="default",
            prompt="test prompt",
            style="infographic",
            mood="clean",
            colors="blue, white",
        )
        d = v.to_dict()
        assert d["variant_id"] == "A"
        assert d["prompt"] == "test prompt"

    def test_unknown_topic_uses_default(self):
        t = self._tester()
        variants = t.generate_variants("존재안하는토픽", "공감")
        assert len(variants) >= 2
        # 기본 스타일 사용됨
        assert variants[0].style != ""


class TestCompareResults:
    def _tester(self):
        return ImageABTester()

    def test_clear_winner(self):
        t = self._tester()
        result = t.compare_results({
            "A": {"views": 1000, "likes": 50, "retweets": 10},
            "B": {"views": 1000, "likes": 100, "retweets": 30},
        })
        assert result.winner == "B"
        assert "참여율" in result.winner_reason

    def test_no_significant_difference(self):
        t = self._tester()
        result = t.compare_results({
            "A": {"views": 1000, "likes": 50, "retweets": 10},
            "B": {"views": 1000, "likes": 51, "retweets": 10},
        })
        # 차이가 5% 미만이면 유의하지 않음
        assert result.winner is None
        assert "미미" in result.winner_reason or "추가" in result.winner_reason

    def test_empty_metrics(self):
        t = self._tester()
        result = t.compare_results({})
        assert result.winner is None
        assert "데이터 없음" in result.winner_reason

    def test_zero_views(self):
        t = self._tester()
        result = t.compare_results({
            "A": {"views": 0, "likes": 0, "retweets": 0},
            "B": {"views": 0, "likes": 0, "retweets": 0},
        })
        assert result.winner is None

    def test_result_to_dict(self):
        r = ABTestResult(
            test_id="test_1",
            topic_cluster="연봉",
            emotion_axis="분노",
            variants=[],
            winner="B",
            winner_reason="test",
            metrics={"A": {"views": 100}, "B": {"views": 200}},
            created_at="2026-03-08",
        )
        d = r.to_dict()
        assert d["test_id"] == "test_1"
        assert d["winner"] == "B"


class TestStyleReport:
    def _tester(self):
        return ImageABTester()

    def test_report_with_decisive_results(self):
        t = self._tester()
        results = [
            ABTestResult(
                test_id=f"t_{i}",
                topic_cluster="연봉",
                emotion_axis="분노",
                variants=[
                    ImageVariant("A", "default", "", "modern infographic", "", ""),
                    ImageVariant("B", "alt_style", "", "flat design", "", ""),
                ],
                winner="B" if i % 2 == 0 else "A",
            )
            for i in range(6)
        ]
        report = t.generate_style_report(results)
        assert report["total_tests"] == 6
        assert report["decisive_tests"] == 6
        assert len(report["style_wins"]) > 0

    def test_report_empty(self):
        t = self._tester()
        report = t.generate_style_report([])
        assert report["total_tests"] == 0
        assert report["decisive_tests"] == 0

    def test_report_no_decisive(self):
        t = self._tester()
        results = [
            ABTestResult(
                test_id="t_1",
                topic_cluster="연봉",
                emotion_axis="분노",
                variants=[],
                winner=None,
            )
        ]
        report = t.generate_style_report(results)
        assert report["decisive_tests"] == 0


class TestBuildImagePromptVariant:
    def test_default_variant_unchanged(self):
        from pipeline.image_generator import ImageGenerator
        prompt = ImageGenerator.build_image_prompt(
            topic_cluster="연봉",
            emotion_axis="공감",
            variant="default",
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 10

    def test_variant_param_accepted(self):
        """variant 파라미터가 에러 없이 받아들여지는지 확인."""
        from pipeline.image_generator import ImageGenerator
        # 모든 variant 값이 에러 없이 실행되어야 함
        for v in ("default", "alt_style", "alt_mood"):
            prompt = ImageGenerator.build_image_prompt(
                topic_cluster="이직",
                emotion_axis="분노",
                variant=v,
            )
            assert isinstance(prompt, str)
