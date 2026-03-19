"""Tests for pipeline.cross_source_insight — cross-source trend detection & insight generation."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.cross_source_insight import (  # noqa: E402
    detect_cross_source_trends,
    generate_insight_draft,
    process_cross_source_insights,
)


# ── Test data ─────────────────────────────────────────────────────────


def _make_result(source: str, topic: str, title: str = "", score: float = 70.0):
    """Helper to create a processed post result."""
    return {
        "success": True,
        "url": f"https://{source}.com/{title.replace(' ', '-')}",
        "title": title or f"{topic} 관련 게시글",
        "source": source,
        "content": f"{topic}에 대한 내용입니다.",
        "content_profile": {
            "topic_cluster": topic,
            "hook_type": "공감형",
            "emotion_axis": "공감",
            "audience_fit": "전직장인",
            "recommended_draft_type": "공감형",
            "final_rank_score": score,
            "source": source,
        },
    }


# ── detect_cross_source_trends tests ──────────────────────────────────


def test_detect_no_trends_insufficient_posts():
    """게시글 수가 min_posts 미만이면 트렌드 없음."""
    results = [
        _make_result("blind", "연봉", "연봉 이야기 1"),
        _make_result("ppomppu", "연봉", "연봉 이야기 2"),
    ]
    trends = detect_cross_source_trends(results, min_posts=3, min_sources=2)
    assert trends == []


def test_detect_no_trends_single_source():
    """소스가 1개뿐이면 트렌드 없음."""
    results = [
        _make_result("blind", "연봉", "연봉 이야기 1"),
        _make_result("blind", "연봉", "연봉 이야기 2"),
        _make_result("blind", "연봉", "연봉 이야기 3"),
    ]
    trends = detect_cross_source_trends(results, min_posts=3, min_sources=2)
    assert trends == []


def test_detect_trend_found():
    """3건 이상, 2소스 이상이면 트렌드 감지."""
    results = [
        _make_result("blind", "연봉", "블라인드 연봉", 80.0),
        _make_result("ppomppu", "연봉", "뽐뿌 연봉", 70.0),
        _make_result("jobplanet", "연봉", "잡플 연봉", 75.0),
    ]
    trends = detect_cross_source_trends(results, min_posts=3, min_sources=2)
    assert len(trends) == 1
    assert trends[0]["topic_cluster"] == "연봉"
    assert trends[0]["post_count"] == 3
    assert trends[0]["source_count"] == 3
    assert trends[0]["avg_rank_score"] == 75.0


def test_detect_multiple_trends():
    """여러 토픽이 동시에 트렌드."""
    results = [
        _make_result("blind", "연봉", "연봉1", 80.0),
        _make_result("ppomppu", "연봉", "연봉2", 70.0),
        _make_result("jobplanet", "연봉", "연봉3", 75.0),
        _make_result("blind", "이직", "이직1", 85.0),
        _make_result("fmkorea", "이직", "이직2", 65.0),
        _make_result("ppomppu", "이직", "이직3", 70.0),
    ]
    trends = detect_cross_source_trends(results, min_posts=3, min_sources=2)
    assert len(trends) == 2
    topics = {t["topic_cluster"] for t in trends}
    assert "연봉" in topics
    assert "이직" in topics


def test_detect_skips_failed_results():
    """success=False인 결과는 무시."""
    results = [
        _make_result("blind", "연봉", "연봉1"),
        _make_result("ppomppu", "연봉", "연봉2"),
        {"success": False, "url": "https://example.com", "source": "jobplanet"},
    ]
    trends = detect_cross_source_trends(results, min_posts=3, min_sources=2)
    assert trends == []


def test_detect_skips_기타_topic():
    """토픽이 '기타'인 게시글은 무시."""
    results = [
        _make_result("blind", "기타", "기타1"),
        _make_result("ppomppu", "기타", "기타2"),
        _make_result("jobplanet", "기타", "기타3"),
    ]
    trends = detect_cross_source_trends(results, min_posts=3, min_sources=2)
    assert trends == []


def test_detect_sorted_by_score():
    """avg_rank_score 내림차순 정렬."""
    results = [
        _make_result("blind", "연봉", "연봉1", 60.0),
        _make_result("ppomppu", "연봉", "연봉2", 60.0),
        _make_result("jobplanet", "연봉", "연봉3", 60.0),
        _make_result("blind", "이직", "이직1", 90.0),
        _make_result("fmkorea", "이직", "이직2", 90.0),
        _make_result("ppomppu", "이직", "이직3", 90.0),
    ]
    trends = detect_cross_source_trends(results, min_posts=3, min_sources=2)
    assert len(trends) == 2
    assert trends[0]["topic_cluster"] == "이직"  # 90.0 > 60.0
    assert trends[1]["topic_cluster"] == "연봉"


def test_detect_custom_thresholds():
    """커스텀 min_posts/min_sources 적용."""
    results = [
        _make_result("blind", "연봉", "연봉1"),
        _make_result("ppomppu", "연봉", "연봉2"),
    ]
    # min_posts=2, min_sources=2 → 감지됨
    trends = detect_cross_source_trends(results, min_posts=2, min_sources=2)
    assert len(trends) == 1


# ── generate_insight_draft tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_insight_draft_success():
    """LLM 인사이트 초안 생성 성공."""
    trend_group = {
        "topic_cluster": "연봉",
        "posts": [
            {"url": "u1", "title": "연봉1", "source": "blind", "content_snippet": "내용1", "final_rank_score": 80, "hook_type": "공감형", "emotion_axis": "공감", "audience_fit": "전직장인"},
            {"url": "u2", "title": "연봉2", "source": "ppomppu", "content_snippet": "내용2", "final_rank_score": 70, "hook_type": "논쟁형", "emotion_axis": "분노", "audience_fit": "전직장인"},
            {"url": "u3", "title": "연봉3", "source": "jobplanet", "content_snippet": "내용3", "final_rank_score": 75, "hook_type": "정보형", "emotion_axis": "통찰", "audience_fit": "이직준비층"},
        ],
        "sources": {"blind", "ppomppu", "jobplanet"},
        "source_count": 3,
        "post_count": 3,
        "avg_rank_score": 75.0,
    }

    mock_generator = MagicMock()
    mock_generator._enabled_providers.return_value = ["gemini"]
    mock_generator.max_retries_per_provider = 1
    mock_generator._generate_once = AsyncMock(
        return_value=("<twitter>트렌드 분석 트윗</twitter><image_prompt>office scene</image_prompt>", 100, 200)
    )
    mock_generator._parse_response.return_value = (
        {"twitter": "트렌드 분석 트윗", "_provider_used": "gemini"},
        "office scene",
    )
    mock_generator.cost_tracker = None

    drafts, image_prompt = await generate_insight_draft(
        trend_group, mock_generator, ["twitter"]
    )
    assert "twitter" in drafts
    assert drafts["_insight_type"] == "cross_source"
    assert drafts["_topic_cluster"] == "연봉"
    assert image_prompt == "office scene"


@pytest.mark.asyncio
async def test_generate_insight_draft_all_providers_fail():
    """모든 프로바이더 실패 시 에러 메시지 반환."""
    trend_group = {
        "topic_cluster": "이직",
        "posts": [],
        "sources": {"blind", "ppomppu"},
        "source_count": 2,
        "post_count": 3,
        "avg_rank_score": 70.0,
    }

    mock_generator = MagicMock()
    mock_generator._enabled_providers.return_value = ["gemini"]
    mock_generator.max_retries_per_provider = 1
    mock_generator._generate_once = AsyncMock(side_effect=RuntimeError("API error"))
    mock_generator.cost_tracker = None

    drafts, image_prompt = await generate_insight_draft(
        trend_group, mock_generator, ["twitter"]
    )
    assert "failed" in drafts["twitter"].lower() or "이직" in drafts["twitter"]


# ── process_cross_source_insights tests ───────────────────────────────


@pytest.mark.asyncio
async def test_process_no_trends():
    """트렌드 없으면 빈 리스트 반환."""
    results = [_make_result("blind", "연봉", "연봉1")]
    mock_generator = MagicMock()

    insights = await process_cross_source_insights(
        results=results,
        draft_generator=mock_generator,
        config=MagicMock(get=lambda k, d=None: d),
    )
    assert insights == []


@pytest.mark.asyncio
async def test_process_with_trends():
    """트렌드 감지 시 인사이트 생성."""
    results = [
        _make_result("blind", "연봉", "연봉1", 80.0),
        _make_result("ppomppu", "연봉", "연봉2", 70.0),
        _make_result("jobplanet", "연봉", "연봉3", 75.0),
    ]

    mock_generator = MagicMock()
    mock_generator._enabled_providers.return_value = ["gemini"]
    mock_generator.max_retries_per_provider = 1
    mock_generator._generate_once = AsyncMock(
        return_value=("<twitter>인사이트</twitter>", 100, 200)
    )
    mock_generator._parse_response.return_value = (
        {"twitter": "인사이트", "_provider_used": "gemini"},
        None,
    )
    mock_generator.cost_tracker = None

    config = MagicMock()
    config.get = lambda k, d=None: {
        "cross_source_insight.min_posts": 3,
        "cross_source_insight.min_sources": 2,
        "dry_run": False,
    }.get(k, d)

    with patch("pipeline.cost_db.get_cost_db") as mock_db:
        mock_db.return_value = MagicMock()
        insights = await process_cross_source_insights(
            results=results,
            draft_generator=mock_generator,
            config=config,
        )

    assert len(insights) == 1
    assert insights[0]["source"] == "cross_source_insight"
    assert insights[0]["content_profile"]["topic_cluster"] == "연봉"
    assert insights[0]["content_profile"]["hook_type"] == "분석형"


@pytest.mark.asyncio
async def test_process_notion_upload_error_handled():
    """Notion 업로드 실패해도 결과는 반환."""
    results = [
        _make_result("blind", "연봉", "연봉1"),
        _make_result("ppomppu", "연봉", "연봉2"),
        _make_result("jobplanet", "연봉", "연봉3"),
    ]

    mock_generator = MagicMock()
    mock_generator._enabled_providers.return_value = ["gemini"]
    mock_generator.max_retries_per_provider = 1
    mock_generator._generate_once = AsyncMock(return_value=("<twitter>t</twitter>", 10, 20))
    mock_generator._parse_response.return_value = ({"twitter": "t", "_provider_used": "g"}, None)
    mock_generator.cost_tracker = None

    mock_notion = MagicMock()
    mock_notion.upload_post = AsyncMock(side_effect=RuntimeError("Notion 503"))

    config = MagicMock()
    config.get = lambda k, d=None: {
        "cross_source_insight.min_posts": 3,
        "cross_source_insight.min_sources": 2,
    }.get(k, d)

    with patch("pipeline.cost_db.get_cost_db") as mock_db:
        mock_db.return_value = MagicMock()
        insights = await process_cross_source_insights(
            results=results,
            draft_generator=mock_generator,
            notion_uploader=mock_notion,
            config=config,
        )

    assert len(insights) == 1
    assert "notion_error" in insights[0]
