from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import blind_scraper as bs  # noqa: E402


class FakeConfig:
    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


def _build_config(tmp_path, quality=None):
    return FakeConfig(
        {
            "screenshot_dir": str(tmp_path / "shots"),
            "request": {"timeout_seconds": 20, "retries": 1, "backoff_seconds": 0.1},
            "scrape_quality": quality or {},
        }
    )


def test_assess_quality_high_score_for_normal_korean_text(tmp_path):
    scraper = bs.BlindScraper(_build_config(tmp_path))
    quality = scraper.assess_quality(
        {
            "title": "직장인 공감 글",
            "content": "오늘 팀 미팅에서 나온 이슈를 정리했고, 해결 방안을 함께 논의했습니다.",
        }
    )
    assert quality["score"] >= bs.QUALITY_SCORE_THRESHOLD
    assert "low_korean_ratio" not in quality["reasons"]


def test_assess_quality_low_korean_ratio_detected(tmp_path):
    scraper = bs.BlindScraper(_build_config(tmp_path))
    quality = scraper.assess_quality(
        {
            "title": "all english title",
            "content": "this post is mostly english with symbols !!! $$$ and numbers 123456",
        }
    )
    assert quality["score"] < bs.QUALITY_SCORE_THRESHOLD
    assert "low_korean_ratio" in quality["reasons"]


def test_scrape_quality_defaults_are_applied(tmp_path):
    scraper = bs.BlindScraper(_build_config(tmp_path, quality={}))
    assert scraper.min_content_length == 20
    assert abs(scraper.min_korean_ratio - 0.15) < 1e-9
    assert scraper.require_title is True
    assert abs(scraper.max_empty_field_ratio - 0.4) < 1e-9
    assert scraper.selector_timeout_ms == 5000
    assert scraper.direct_fallback_timeout_ms == 8000


def test_calculate_run_metrics_quality_and_stage_counts():
    results = [
        {"success": True, "error_code": None, "notion_url": "https://notion.so/page-a", "quality_score": 80},
        {
            "success": True,
            "error_code": bs.ERROR_FILTERED_LOW_QUALITY,
            "notion_url": "(skipped-filtered)",
            "quality_score": 40,
        },
        {"success": False, "error_code": bs.ERROR_SCRAPE_PARSE_FAILED, "quality_score": None},
        {"success": False, "error_code": bs.ERROR_SCRAPE_FEED_FAILED, "quality_score": None},
    ]
    metrics = bs.calculate_run_metrics(results, dry_run=False)

    assert len(metrics["filtered_low_quality"]) == 1
    assert len(metrics["parse_failures"]) == 1
    assert len(metrics["feed_fetch_failures"]) == 1
    assert abs(metrics["avg_quality_score"] - 60.0) < 1e-9
    assert metrics["live_upload_attempts"] == 3
    assert len(metrics["live_upload_success"]) == 1
