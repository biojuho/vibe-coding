"""error_analyzer 유틸리티 함수 테스트."""

from datetime import datetime

import execution.error_analyzer as error_analyzer
from execution.error_analyzer import (
    _category_lines,
    _classify_error,
    _collect_pattern_records,
    _group_pattern_records,
    _parse_iso,
    _pattern_lines,
    _recurring_patterns,
    _top_module_lines,
    _trend_label,
    generate_weekly_report,
)


class TestClassifyError:
    def test_timeout(self):
        assert _classify_error("Request timed out after 30s") == "api_timeout"

    def test_timeout_error_class(self):
        assert _classify_error("asyncio.TimeoutError") == "api_timeout"

    def test_selector_failure(self):
        assert _classify_error("Selector .post-title not found") == "selector_failure"

    def test_cost_exceeded(self):
        assert _classify_error("CostExceeded: daily budget hit") == "cost_exceeded"

    def test_rate_limit_429(self):
        assert _classify_error("HTTP 429 rate limit") == "cost_exceeded"

    def test_auth_expired(self):
        assert _classify_error("401 Unauthorized token expired") == "auth_expired"

    def test_network_error(self):
        assert _classify_error("ConnectionError: DNS resolution failed") == "network"

    def test_unknown_returns_other(self):
        assert _classify_error("Something completely random happened") == "other"

    def test_case_insensitive(self):
        assert _classify_error("TIMEOUT occurred") == "api_timeout"


class TestParseIso:
    def test_valid_iso(self):
        result = _parse_iso("2026-03-22T12:00:00")
        assert isinstance(result, datetime)
        assert result.year == 2026

    def test_valid_iso_with_tz(self):
        result = _parse_iso("2026-03-22T12:00:00+09:00")
        assert isinstance(result, datetime)
        assert result.tzinfo is None  # converted to naive

    def test_invalid_returns_none(self):
        assert _parse_iso("not-a-date") is None

    def test_none_returns_none(self):
        assert _parse_iso(None) is None

    def test_empty_returns_none(self):
        assert _parse_iso("") is None


class TestPatternHelpers:
    def test_collect_pattern_records_merges_available_sources(self, monkeypatch):
        now = datetime.now().isoformat()
        monkeypatch.setattr(
            error_analyzer,
            "list_entries",
            lambda limit=500: [{"created_at": now, "symptom": "timeout", "module": "runner"}],
        )
        monkeypatch.setattr(
            error_analyzer,
            "_load_failure_snapshots",
            lambda days: [{"timestamp": now, "error": "401 expired", "module": "auth"}],
        )
        monkeypatch.setattr(
            error_analyzer,
            "_load_watchdog_errors",
            lambda days: [{"time": now, "message": "DNS failed", "task": "watchdog"}],
        )

        assert _collect_pattern_records(days=7) == [
            ("api_timeout", "runner", now),
            ("auth_expired", "auth", now),
            ("network", "watchdog", now),
        ]

    def test_recurring_patterns_groups_modules_and_sorts_by_count(self):
        grouped = _group_pattern_records(
            [
                ("api_timeout", "runner", "2026-06-01T00:00:00"),
                ("api_timeout", "worker", "2026-06-02T00:00:00"),
                ("network", "watchdog", "2026-06-03T00:00:00"),
                ("api_timeout", "runner", "2026-06-04T00:00:00"),
            ]
        )

        assert _recurring_patterns(grouped, min_occurrences=2) == [
            {
                "error_type": "api_timeout",
                "count": 3,
                "last_seen": "2026-06-04T00:00:00",
                "affected_modules": ["runner", "worker"],
            }
        ]


class TestWeeklyReportHelpers:
    def test_trend_label_compares_current_to_previous_week_only(self):
        assert _trend_label(10, 15) == "UP +100% (5 -> 10)"
        assert _trend_label(3, 10) == "DOWN -57% (7 -> 3)"
        assert _trend_label(5, 10) == "FLAT (5)"
        assert _trend_label(5, 5) == "NEW (no prior data)"

    def test_markdown_section_helpers_render_empty_and_populated_values(self):
        assert _category_lines({}) == "  (none)"
        assert _top_module_lines([]) == "  (none)"
        assert _pattern_lines([]) == "(no recurring patterns detected)"

        assert _category_lines({"network": 1, "api_timeout": 3}).splitlines()[0] == "  - api_timeout: 3"
        assert _top_module_lines([{"module": "runner", "count": 2}]) == "  - runner: 2"
        assert "| api_timeout | 3 | 2026-06-04T00:00 | runner |" in _pattern_lines(
            [
                {
                    "error_type": "api_timeout",
                    "count": 3,
                    "last_seen": "2026-06-04T00:00:00",
                    "affected_modules": ["runner"],
                }
            ]
        )

    def test_generate_weekly_report_uses_analyzer_sections(self, monkeypatch):
        monkeypatch.setattr(
            error_analyzer,
            "analyze_recent_errors",
            lambda days: {
                "total": 4 if days == 7 else 6,
                "by_category": {"api_timeout": 3, "network": 1},
                "top_modules": [{"module": "runner", "count": 2}],
                "period_days": days,
            },
        )
        monkeypatch.setattr(
            error_analyzer,
            "detect_recurring_patterns",
            lambda min_occurrences=3: [
                {
                    "error_type": "api_timeout",
                    "count": 3,
                    "last_seen": "2026-06-04T00:00:00",
                    "affected_modules": ["runner"],
                }
            ],
        )
        monkeypatch.setattr(error_analyzer, "get_stats", lambda: {"by_severity": {"high": 2}})

        report = generate_weekly_report()

        assert "- **Trend vs previous week**: UP +100% (2 -> 4)" in report
        assert "  - high: 2" in report
        assert "  - api_timeout: 3" in report
        assert "  - runner: 2" in report
        assert "| api_timeout | 3 | 2026-06-04T00:00 | runner |" in report
