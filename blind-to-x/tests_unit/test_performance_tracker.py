"""P6: performance_tracker + classification_rules 플랫폼 확장 테스트."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

# ── 테스트 대상 ────────────────────────────────────────────────────
from pipeline.performance_tracker import (
    PerformanceRecord,
    PerformanceTracker,
    PLATFORM_METRICS,
    ENGAGEMENT_WEIGHTS,
)

RULES_FILE = Path(__file__).parent.parent / "classification_rules.yaml"


# ═══════════════════════════════════════════════════════════════════
# 1. PerformanceRecord 단위 테스트
# ═══════════════════════════════════════════════════════════════════
class TestPerformanceRecord(unittest.TestCase):
    def test_twitter_engagement(self):
        rec = PerformanceRecord("page1", "twitter", {"likes": 100, "retweets": 20, "replies": 10})
        # 100*1 + 20*3 + 10*5 = 100 + 60 + 50 = 210
        self.assertEqual(rec.engagement_score, 210.0)
        self.assertEqual(rec.grade, "S")

    def test_threads_engagement(self):
        rec = PerformanceRecord("page2", "threads", {"likes": 30, "comments": 5, "saves": 10})
        # 30*1 + 5*5 + 10*3 = 30 + 25 + 30 = 85
        self.assertEqual(rec.engagement_score, 85.0)
        self.assertEqual(rec.grade, "S")

    def test_naver_blog_engagement(self):
        rec = PerformanceRecord("page3", "naver_blog", {"views": 200, "comments": 3})
        # 200*0.1 + 3*5 = 20 + 15 = 35
        self.assertEqual(rec.engagement_score, 35.0)
        self.assertEqual(rec.grade, "B")

    def test_low_engagement_grade_c(self):
        rec = PerformanceRecord("page4", "threads", {"likes": 2})
        # 2*1 = 2
        self.assertEqual(rec.grade, "C")

    def test_to_dict(self):
        rec = PerformanceRecord("page5", "twitter", {"likes": 10}, topic_cluster="연봉")
        d = rec.to_dict()
        self.assertEqual(d["platform"], "twitter")
        self.assertEqual(d["topic_cluster"], "연봉")
        self.assertIn("recorded_at", d)


# ═══════════════════════════════════════════════════════════════════
# 2. PerformanceTracker 통합 테스트
# ═══════════════════════════════════════════════════════════════════
class TestPerformanceTracker(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tracker = PerformanceTracker(data_dir=self.tmpdir)

    def test_record_and_retrieve(self):
        self.tracker.record_performance("p1", "threads", {"likes": 50, "comments": 10}, "연봉")
        self.tracker.record_performance("p2", "naver_blog", {"views": 300, "comments": 5}, "이직")
        records = self.tracker.get_records()
        self.assertEqual(len(records), 2)

    def test_filter_by_platform(self):
        self.tracker.record_performance("p1", "threads", {"likes": 50}, "연봉")
        self.tracker.record_performance("p2", "naver_blog", {"views": 300}, "이직")
        threads_only = self.tracker.get_records(platform="threads")
        self.assertEqual(len(threads_only), 1)
        self.assertEqual(threads_only[0].platform, "threads")

    def test_filter_by_topic(self):
        self.tracker.record_performance("p1", "threads", {"likes": 50}, "연봉")
        self.tracker.record_performance("p2", "threads", {"likes": 30}, "이직")
        salary_only = self.tracker.get_records(topic="연봉")
        self.assertEqual(len(salary_only), 1)

    def test_generate_report_empty(self):
        report = self.tracker.generate_report(days=7)
        self.assertEqual(report["total_posts"], 0)

    def test_generate_report_with_data(self):
        self.tracker.record_performance("p1", "threads", {"likes": 50, "comments": 10}, "연봉")
        self.tracker.record_performance("p2", "threads", {"likes": 80, "comments": 20}, "이직")
        self.tracker.record_performance("p3", "naver_blog", {"views": 500, "comments": 8}, "연봉")
        report = self.tracker.generate_report(days=7)
        self.assertEqual(report["total_posts"], 3)
        self.assertIn("threads", report["platform_stats"])
        self.assertIn("naver_blog", report["platform_stats"])
        self.assertGreater(len(report["best_performing"]), 0)

    def test_topic_recommendations(self):
        self.tracker.record_performance("p1", "threads", {"likes": 100, "comments": 20}, "연봉")
        self.tracker.record_performance("p2", "threads", {"likes": 5}, "직장개그")
        recs = self.tracker.get_topic_recommendations("threads", days=30)
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["topic"], "연봉")  # 높은 점수가 먼저

    def test_jsonl_persistence(self):
        self.tracker.record_performance("p1", "threads", {"likes": 50}, "연봉")
        # 새 tracker 인스턴스로 로드
        tracker2 = PerformanceTracker(data_dir=self.tmpdir)
        records = tracker2.get_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].notion_page_id, "p1")


# ═══════════════════════════════════════════════════════════════════
# 3. classification_rules.yaml 플랫폼 확장 검증
# ═══════════════════════════════════════════════════════════════════
class TestClassificationRulesPlatformExtension(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if RULES_FILE.exists():
            with open(RULES_FILE, encoding="utf-8") as f:
                cls.rules = yaml.safe_load(f) or {}
        else:
            cls.rules = {}

    def test_tone_mapping_threads_exists(self):
        """tone_mapping_threads 섹션이 존재해야 합니다."""
        self.assertIn("tone_mapping_threads", self.rules)

    def test_tone_mapping_naver_blog_exists(self):
        """tone_mapping_naver_blog 섹션이 존재해야 합니다."""
        self.assertIn("tone_mapping_naver_blog", self.rules)

    def test_threads_tone_covers_all_topics(self):
        """Threads 톤 매핑이 기본 tone_mapping의 모든 토픽을 커버해야 합니다."""
        base_topics = set(self.rules.get("tone_mapping", {}).keys())
        threads_topics = set(self.rules.get("tone_mapping_threads", {}).keys())
        missing = base_topics - threads_topics
        self.assertFalse(missing, f"Threads 톤에 누락된 토픽: {missing}")

    def test_blog_tone_covers_all_topics(self):
        """블로그 톤 매핑이 기본 tone_mapping의 모든 토픽을 커버해야 합니다."""
        base_topics = set(self.rules.get("tone_mapping", {}).keys())
        blog_topics = set(self.rules.get("tone_mapping_naver_blog", {}).keys())
        missing = base_topics - blog_topics
        self.assertFalse(missing, f"블로그 톤에 누락된 토픽: {missing}")

    def test_golden_examples_threads_exists(self):
        """Threads 전용 골든 예시가 존재해야 합니다."""
        self.assertIn("golden_examples_threads", self.rules)

    def test_golden_examples_naver_blog_exists(self):
        """네이버 블로그 전용 골든 예시가 존재해야 합니다."""
        self.assertIn("golden_examples_naver_blog", self.rules)

    def test_threads_cta_mapping_exists(self):
        """Threads CTA 매핑이 존재해야 합니다."""
        self.assertIn("threads_cta_mapping", self.rules)
        cta = self.rules["threads_cta_mapping"]
        # 기본 감정 축 10개 중 최소 5개 커버
        self.assertGreaterEqual(len(cta), 5)

    def test_naver_blog_seo_tags_exists(self):
        """네이버 블로그 SEO 태그가 존재해야 합니다."""
        self.assertIn("naver_blog_seo_tags", self.rules)
        tags = self.rules["naver_blog_seo_tags"]
        for topic, tag_list in tags.items():
            self.assertIsInstance(tag_list, list, f"{topic}의 SEO 태그가 리스트가 아닙니다")
            self.assertGreaterEqual(len(tag_list), 10, f"{topic}의 SEO 태그가 10개 미만입니다")

    def test_prompt_templates_threads_exists(self):
        """프롬프트 템플릿에 threads가 있어야 합니다."""
        templates = self.rules.get("prompt_templates", {})
        self.assertIn("threads", templates)

    def test_prompt_templates_naver_blog_exists(self):
        """프롬프트 템플릿에 naver_blog가 있어야 합니다."""
        templates = self.rules.get("prompt_templates", {})
        self.assertIn("naver_blog", templates)

    def test_threads_template_has_tone_placeholder(self):
        """Threads 프롬프트 템플릿에 {threads_tone} 변수가 포함되어야 합니다."""
        tmpl = self.rules.get("prompt_templates", {}).get("threads", "")
        self.assertIn("{threads_tone}", tmpl)

    def test_blog_template_has_tone_placeholder(self):
        """블로그 프롬프트 템플릿에 {naver_blog_tone} 변수가 포함되어야 합니다."""
        tmpl = self.rules.get("prompt_templates", {}).get("naver_blog", "")
        self.assertIn("{naver_blog_tone}", tmpl)


# ═══════════════════════════════════════════════════════════════════
# 4. 플랫폼 메트릭 정의 테스트
# ═══════════════════════════════════════════════════════════════════
class TestPlatformMetrics(unittest.TestCase):
    def test_all_platforms_have_metrics(self):
        for platform in ["twitter", "threads", "naver_blog", "newsletter"]:
            self.assertIn(platform, PLATFORM_METRICS)

    def test_all_platforms_have_weights(self):
        for platform in ["twitter", "threads", "naver_blog", "newsletter"]:
            self.assertIn(platform, ENGAGEMENT_WEIGHTS)

    def test_threads_metrics_count(self):
        self.assertGreaterEqual(len(PLATFORM_METRICS["threads"]), 4)

    def test_naver_blog_metrics_count(self):
        self.assertGreaterEqual(len(PLATFORM_METRICS["naver_blog"]), 4)


if __name__ == "__main__":
    unittest.main()
