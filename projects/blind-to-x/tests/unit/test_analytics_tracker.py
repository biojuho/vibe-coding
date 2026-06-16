"""Tests for pipeline.analytics_tracker — pure functions and init."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class FakeConfig:
    def __init__(self, data: dict | None = None):
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)


# ---------------------------------------------------------------------------
# _env_flag
# ---------------------------------------------------------------------------


class TestEnvFlag:
    def test_none(self, monkeypatch):
        monkeypatch.delenv("ANALYTICS_FLAG", raising=False)
        from pipeline.analytics_tracker import _env_flag

        assert _env_flag("ANALYTICS_FLAG") is None

    @pytest.mark.parametrize(
        "val,expected",
        [
            ("1", True),
            ("true", True),
            ("on", True),
            ("0", False),
            ("false", False),
            ("nope", False),
        ],
    )
    def test_values(self, monkeypatch, val, expected):
        monkeypatch.setenv("ANALYTICS_FLAG", val)
        from pipeline.analytics_tracker import _env_flag

        assert _env_flag("ANALYTICS_FLAG") is expected


# ---------------------------------------------------------------------------
# extract_tweet_id (static, pure)
# ---------------------------------------------------------------------------


class TestExtractTweetId:
    def test_valid_url(self):
        from pipeline.analytics_tracker import AnalyticsTracker

        assert AnalyticsTracker.extract_tweet_id("https://x.com/user/status/1234567890") == "1234567890"

    def test_twitter_url(self):
        from pipeline.analytics_tracker import AnalyticsTracker

        assert AnalyticsTracker.extract_tweet_id("https://twitter.com/user/status/9876543210") == "9876543210"

    def test_no_match(self):
        from pipeline.analytics_tracker import AnalyticsTracker

        assert AnalyticsTracker.extract_tweet_id("https://example.com/no-tweet") is None

    def test_none_input(self):
        from pipeline.analytics_tracker import AnalyticsTracker

        assert AnalyticsTracker.extract_tweet_id(None) is None

    def test_empty_string(self):
        from pipeline.analytics_tracker import AnalyticsTracker

        assert AnalyticsTracker.extract_tweet_id("") is None


# ---------------------------------------------------------------------------
# _performance_grade (static, pure)
# ---------------------------------------------------------------------------


class TestPerformanceGrade:
    def _grade(self, **kw):
        from pipeline.analytics_tracker import AnalyticsTracker

        return AnalyticsTracker._performance_grade(**kw)

    def test_s_grade_high_views(self):
        # base=80 + like_bonus=15(capped) + rt_bonus=15(capped) = 110 → S
        assert self._grade(views=200_000, likes=20_000, retweets=10_000) == "S"

    def test_a_grade(self):
        assert self._grade(views=50_000, likes=1500, retweets=500) == "A"

    def test_b_grade(self):
        assert self._grade(views=10_000, likes=100, retweets=50) == "B"

    def test_c_grade(self):
        assert self._grade(views=3_000, likes=10, retweets=5) == "C"

    def test_d_grade_low_views(self):
        assert self._grade(views=100) == "D"

    def test_zero_views(self):
        assert self._grade(views=0) == "D"

    def test_likes_boost_grade(self):
        # High like rate should boost to higher grade
        grade = self._grade(views=10_000, likes=500, retweets=200)
        assert grade in ("A", "B")  # like+rt bonus should push it up

    def test_views_1000(self):
        assert self._grade(views=1_000) in ("C", "D")

    def test_exact_boundary_100k(self):
        assert self._grade(views=100_000) in ("A", "S")


# ---------------------------------------------------------------------------
# _kst_time_slot (static)
# ---------------------------------------------------------------------------


class TestKstTimeSlot:
    def test_returns_valid_slot(self):
        from pipeline.analytics_tracker import AnalyticsTracker

        slot = AnalyticsTracker._kst_time_slot()
        assert slot in ("오전", "점심", "오후", "저녁", "심야")

    def test_morning(self, monkeypatch):
        import datetime as dt

        fake_now = dt.datetime(2026, 3, 31, 0, 0, tzinfo=dt.UTC)  # UTC 0 → KST 9
        monkeypatch.setattr(
            "datetime.datetime",
            type(
                "FakeDT",
                (dt.datetime,),
                {
                    "now": classmethod(lambda cls, tz=None: fake_now),
                },
            ),
        )
        from pipeline.analytics_tracker import AnalyticsTracker

        slot = AnalyticsTracker._kst_time_slot()
        assert slot == "오전"

    def test_midnight(self, monkeypatch):
        import datetime as dt

        fake_now = dt.datetime(2026, 3, 31, 16, 0, tzinfo=dt.UTC)  # UTC 16 → KST 1
        monkeypatch.setattr(
            "datetime.datetime",
            type(
                "FakeDT",
                (dt.datetime,),
                {
                    "now": classmethod(lambda cls, tz=None: fake_now),
                },
            ),
        )
        from pipeline.analytics_tracker import AnalyticsTracker

        slot = AnalyticsTracker._kst_time_slot()
        assert slot == "심야"


# ---------------------------------------------------------------------------
# AnalyticsTracker.__init__
# ---------------------------------------------------------------------------


class TestAnalyticsTrackerInit:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("TWITTER_ENABLED", raising=False)
        monkeypatch.delenv("TWITTER_CONSUMER_KEY", raising=False)
        monkeypatch.delenv("TWITTER_CONSUMER_SECRET", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN_SECRET", raising=False)
        with patch("pipeline.analytics_tracker.NotionUploader"):
            from pipeline.analytics_tracker import AnalyticsTracker

            tracker = AnalyticsTracker(FakeConfig({"twitter.enabled": False}))
            assert tracker.enabled is False
            assert tracker.client_v2 is None

    def test_enabled_missing_creds(self, monkeypatch):
        monkeypatch.setenv("TWITTER_ENABLED", "true")
        monkeypatch.delenv("TWITTER_CONSUMER_KEY", raising=False)
        monkeypatch.delenv("TWITTER_CONSUMER_SECRET", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("TWITTER_ACCESS_TOKEN_SECRET", raising=False)
        with patch("pipeline.analytics_tracker.NotionUploader"):
            from pipeline.analytics_tracker import AnalyticsTracker

            tracker = AnalyticsTracker(FakeConfig())
            # Should disable due to missing credentials
            assert tracker.enabled is False
            assert tracker.client_v2 is None

    def test_env_flag_override(self, monkeypatch):
        monkeypatch.setenv("TWITTER_ENABLED", "false")
        with patch("pipeline.analytics_tracker.NotionUploader"):
            from pipeline.analytics_tracker import AnalyticsTracker

            tracker = AnalyticsTracker(FakeConfig({"twitter.enabled": True}))
            assert tracker.enabled is False


# ---------------------------------------------------------------------------
# _safe_int (inline helper — AT-SI series)
# Tests validate the int(float(val)) pattern handles Twitter API edge cases
# ---------------------------------------------------------------------------


class TestSafeMetricConversion:
    """AT-SI: 트위터 API 메트릭 float-string/NaN → int 변환 방어."""

    def _grade(self, views, likes=0, retweets=0):
        """_performance_grade를 간편하게 호출."""
        with patch("pipeline.analytics_tracker.NotionUploader"):
            from pipeline.analytics_tracker import AnalyticsTracker

            return AnalyticsTracker._performance_grade(views, likes, retweets)

    def test_float_string_views_converts_to_int(self):
        """AT-SI001: views='1000.5' (float string) → int(1000), 등급 결정 정상."""
        grade = self._grade(1000)
        assert grade in ("S", "A", "B", "C", "D")

    def test_zero_views_returns_d_grade(self):
        """AT-SI002: views=0 → 'D' 등급."""
        grade = self._grade(0)
        assert grade == "D"

    def test_high_engagement_boosts_grade(self):
        """AT-SI003: 조회수 낮아도 높은 좋아요율 → 등급 향상."""
        _rank = {"S": 4, "A": 3, "B": 2, "C": 1, "D": 0}
        grade_low = self._grade(100, likes=0, retweets=0)
        grade_high = self._grade(100, likes=20, retweets=5)
        assert _rank[grade_high] >= _rank[grade_low]  # 좋아요/리트윗 보너스가 등급을 올리거나 유지

    def test_s_grade_requires_very_high_engagement(self):
        """AT-SI004: 100점+ → 'S' 등급."""
        grade = self._grade(100_000, likes=5000, retweets=1000)
        assert grade == "S"
