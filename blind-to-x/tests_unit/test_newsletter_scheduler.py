"""뉴스레터 스케줄러 유닛 테스트.

커버리지:
  - NewsletterScheduler: 설정 로드, 에디션 빌드, 미리보기 생성
  - 최적 발행 시간대 결정
  - 블로그 포맷 변환
  - KST 시간 슬롯 유틸리티
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_BTX_ROOT = Path(__file__).resolve().parent.parent
if str(_BTX_ROOT) not in sys.path:
    sys.path.insert(0, str(_BTX_ROOT))


class _FakeConfig:
    def __init__(self, overrides=None):
        self._data = {
            "newsletter.enabled": True,
            "newsletter.max_items_per_edition": 3,
            "newsletter.min_items_for_publish": 2,
            "newsletter.auto_publish": False,
            "newsletter.output_platforms": ["newsletter", "naver"],
            "analytics.lookback_days": 30,
        }
        if overrides:
            self._data.update(overrides)

    def get(self, key, default=None):
        return self._data.get(key, default)


def _sample_records(n=5):
    """승인 상태의 샘플 레코드 생성."""
    records = []
    topics = ["연봉", "이직", "회사문화", "복지", "직장개그"]
    for i in range(n):
        records.append({
            "title": f"샘플 콘텐츠 {i+1}",
            "content": f"직장인 이야기 {i+1} " * 20,
            "source": "blind",
            "status": "검토완료",
            "newsletter_body": f"뉴스레터 본문 {i+1} — " + "직장 생활의 교훈들. " * 10,
            "topic_cluster": topics[i % len(topics)],
            "emotion_axis": "공감",
            "final_rank_score": 80 - i * 5,
            "views": 100 + i * 50,
            "likes": 20 + i * 3,
            "retweets": 5 + i,
        })
    return records


# ════════════════════════════════════════════════════════════════════════
# NewsletterScheduler 유닛 테스트
# ════════════════════════════════════════════════════════════════════════

class TestNewsletterScheduler:
    def _make_scheduler(self, config_overrides=None, notion=None):
        from pipeline.newsletter_scheduler import NewsletterScheduler
        return NewsletterScheduler(
            config_mgr=_FakeConfig(config_overrides),
            notion_uploader=notion,
        )

    def test_max_items_from_config(self):
        s = self._make_scheduler()
        assert s.max_items == 3

    def test_min_items_from_config(self):
        s = self._make_scheduler()
        assert s.min_items == 2

    def test_auto_publish_default_false(self):
        s = self._make_scheduler()
        assert s.auto_publish is False

    def test_output_platforms(self):
        s = self._make_scheduler()
        assert "newsletter" in s.output_platforms
        assert "naver" in s.output_platforms

    @pytest.mark.asyncio
    async def test_collect_ready_contents_no_notion(self):
        """Notion 없으면 빈 리스트."""
        s = self._make_scheduler(notion=None)
        result = await s.collect_ready_contents()
        assert result == []

    @pytest.mark.asyncio
    async def test_build_edition_with_records(self):
        """레코드 직접 전달 시 에디션 빌드."""
        s = self._make_scheduler()
        records = _sample_records(5)
        edition = await s.build_newsletter_edition(records=records)

        assert edition["item_count"] <= 3  # max_items = 3
        assert edition["can_publish"] is True  # 3 >= min_items(2)
        assert edition["optimal_slot"] != ""
        assert "미리보기" in edition["preview"]
        assert edition["built_at"] != ""

    @pytest.mark.asyncio
    async def test_build_edition_insufficient_items(self):
        """최소 건수 미달 시 can_publish=False."""
        s = self._make_scheduler({"newsletter.min_items_for_publish": 10})
        records = _sample_records(3)
        edition = await s.build_newsletter_edition(records=records)
        assert edition["can_publish"] is False

    @pytest.mark.asyncio
    async def test_build_edition_empty(self):
        """빈 레코드 시 can_publish=False."""
        s = self._make_scheduler()
        edition = await s.build_newsletter_edition(records=[])
        assert edition["item_count"] == 0
        assert edition["can_publish"] is False

    def test_preview_format(self):
        """미리보기 텍스트 포맷 검증."""
        s = self._make_scheduler()
        records = _sample_records(3)
        from pipeline.newsletter_formatter import curate_newsletter_from_records
        curated = curate_newsletter_from_records(records, max_items=3)
        preview = s._build_preview(curated, "점심")
        assert "Blind-to-X" in preview
        assert "점심" in preview
        assert "건" in preview

    def test_get_optimal_slot_fallback(self):
        """PublishOptimizer 실패 시 기본 '점심' 반환."""
        s = self._make_scheduler()
        slot = s._get_optimal_slot([])
        assert slot == "점심"

    def test_format_for_platforms_newsletter(self):
        """에디션을 뉴스레터 포맷으로 변환."""
        s = self._make_scheduler()
        edition = {
            "items": _sample_records(2),
            "platforms": ["newsletter"],
        }
        outputs = s.format_for_platforms(edition)
        assert "newsletter" in outputs
        assert len(outputs["newsletter"]) > 0

    def test_format_for_platforms_naver(self):
        """에디션을 네이버 블로그 포맷으로 변환."""
        s = self._make_scheduler()
        edition = {
            "items": _sample_records(2),
            "platforms": ["newsletter", "naver"],
        }
        outputs = s.format_for_platforms(edition)
        assert "naver" in outputs
        assert "newsletter" in outputs


# ════════════════════════════════════════════════════════════════════════
# KST 유틸리티 테스트
# ════════════════════════════════════════════════════════════════════════

class TestKSTUtilities:
    def test_get_current_kst_slot_returns_valid(self):
        from pipeline.newsletter_scheduler import get_current_kst_slot
        slot = get_current_kst_slot()
        assert slot in {"오전", "점심", "오후", "저녁", "심야"}

    def test_is_publish_window_default(self):
        from pipeline.newsletter_scheduler import is_publish_window
        result = is_publish_window()
        assert isinstance(result, bool)

    def test_is_publish_window_specific_slot(self):
        from pipeline.newsletter_scheduler import is_publish_window, get_current_kst_slot
        current = get_current_kst_slot()
        assert is_publish_window(current) is True
        # 다른 슬롯은 False일 수 있음 (현재 시간에 따라 다름)

    def test_ready_statuses_set(self):
        from pipeline.newsletter_scheduler import NewsletterScheduler
        assert "검토완료" in NewsletterScheduler.READY_STATUSES
        assert "발행승인" in NewsletterScheduler.READY_STATUSES
        assert "승인" in NewsletterScheduler.READY_STATUSES
