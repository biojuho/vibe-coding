"""error_analyzer 유틸리티 함수 테스트."""

from datetime import datetime

from execution.error_analyzer import _classify_error, _parse_iso


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
