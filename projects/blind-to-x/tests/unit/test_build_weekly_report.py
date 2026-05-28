"""build_weekly_report.py 단위 테스트.

`_render_report` 의 markdown 직렬화 + T-1197 tuner 섹션 임베드 + fail-open 동작을 검증.
주 진입점 `run()` 은 Notion/feedback_loop 의존이 커서 여기서는 다루지 않는다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_BTX_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BTX_ROOT))

from scripts.build_weekly_report import _render_best_of_n_section, _render_report  # noqa: E402


def _basic_payload():
    return {
        "totals": {
            "total": 12,
            "review_queue": 3,
            "approved": 7,
            "published": 5,
        },
        "top_topics": [("career", 6), ("money", 4)],
        "top_hooks": [("question", 5), ("statistic", 3)],
        "top_emotions": [("empathy", 6), ("anger", 2)],
        "top_performers": [
            {
                "title": "Title A",
                "views": 1000,
                "likes": 50,
                "retweets": 10,
                "topic_cluster": "career",
                "hook_type": "question",
                "emotion_axis": "empathy",
            }
        ],
    }


def test_render_report_includes_all_required_summary_sections():
    """기본 markdown 구조가 깨지지 않아야: 헤더 + 요약 + Topics/Hooks/Emotions/Performers."""
    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(_basic_payload())
    assert text.startswith("# Blind-to-X Weekly Report")
    assert "## Summary" in text
    assert "Total records: 12" in text
    assert "Review queue: 3" in text
    assert "## Top Topics" in text
    assert "- career: 6" in text
    assert "## Top Hooks" in text
    assert "## Top Emotions" in text
    assert "## Top Performers" in text
    assert "Title A | views=1000 likes=50 retweets=10" in text


def test_render_report_embeds_tuner_section_when_available():
    """T-1197: tuner 결과가 정상이면 markdown 코드 블록으로 임베드되어야."""
    fake_section = (
        "\n## Best-of-N Comment-Weight Tuning (dry-run)\n\n```\n"
        "=== Best-of-N comment-weight tuning (dry-run) ===\n"
        "기간: 최근 30일 / published 샘플: 12건\n"
        "권장: 0.5\n```\n"
    )
    with patch(
        "scripts.build_weekly_report._render_best_of_n_section",
        return_value=fake_section,
    ):
        text = _render_report(_basic_payload(), best_of_n_days=30)
    assert "## Best-of-N Comment-Weight Tuning (dry-run)" in text
    assert "기간: 최근 30일 / published 샘플: 12건" in text
    assert "권장: 0.5" in text
    # 기존 본문이 잘려나가지 않아야.
    assert "## Top Performers" in text


def test_render_report_omits_tuner_section_on_empty_return():
    """tuner 가 빈 문자열 반환(예: 예외 swallow) 시 본문은 그대로, 섹션은 없어야."""
    with patch("scripts.build_weekly_report._render_best_of_n_section", return_value=""):
        text = _render_report(_basic_payload())
    assert "## Best-of-N Comment-Weight Tuning" not in text
    assert "## Top Performers" in text  # 기존 본문 유지


def test_render_best_of_n_section_swallows_tuner_exceptions():
    """T-1197 fail-open: tuner import/실행 예외는 weekly report 본문을 깨면 안 된다."""
    # build_report 가 raise 하도록 패치
    with patch(
        "scripts.tune_best_of_n_weight.build_report",
        side_effect=RuntimeError("tuner exploded"),
    ):
        text = _render_best_of_n_section(days=30)
    assert text == ""


def test_render_best_of_n_section_swallows_db_load_failure():
    """load_recent_rows 가 raise 해도 마찬가지로 빈 문자열."""
    with patch(
        "scripts.tune_best_of_n_weight.load_recent_rows",
        side_effect=OSError("no db"),
    ):
        text = _render_best_of_n_section(days=30)
    assert text == ""


@pytest.mark.parametrize("days", [7, 14, 30, 90])
def test_render_best_of_n_section_passes_days_window_to_loader(days):
    """sweep 윈도우가 호출자 파라미터로 전달되는지 확인."""
    captured = {}

    def fake_loader(*, days):
        captured["days"] = days
        return []

    with (
        patch("scripts.tune_best_of_n_weight.load_recent_rows", side_effect=fake_loader),
        patch(
            "scripts.tune_best_of_n_weight.build_report",
            return_value=("ok-report", {"sample_count": 0, "recommendation": None}),
        ),
    ):
        text = _render_best_of_n_section(days=days)
    assert captured["days"] == days
    assert "ok-report" in text


def test_render_best_of_n_section_wraps_text_in_code_fence():
    """직렬화된 출력이 markdown ``` 코드 블록 안에 들어가야 (Korean formatting 보존)."""
    with (
        patch("scripts.tune_best_of_n_weight.load_recent_rows", return_value=[]),
        patch(
            "scripts.tune_best_of_n_weight.build_report",
            return_value=(
                "line1\nline2\n  - indented",
                {"sample_count": 0, "recommendation": None},
            ),
        ),
    ):
        text = _render_best_of_n_section(days=30)
    assert text.count("```") == 2
    assert "line1\nline2\n  - indented" in text
    assert "## Best-of-N Comment-Weight Tuning (dry-run)" in text
