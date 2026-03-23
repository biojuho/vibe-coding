"""srt_export 단위 테스트."""

from shorts_maker_v2.render.srt_export import _format_timestamp


class TestFormatTimestamp:
    def test_zero(self):
        assert _format_timestamp(0.0) == "00:00:00,000"

    def test_seconds(self):
        assert _format_timestamp(5.5) == "00:00:05,500"

    def test_minutes(self):
        assert _format_timestamp(65.123) == "00:01:05,123"

    def test_hours(self):
        assert _format_timestamp(3661.0) == "01:01:01,000"

    def test_milliseconds_precision(self):
        result = _format_timestamp(1.999)
        assert result == "00:00:01,999"

    def test_large_value(self):
        result = _format_timestamp(7200.0)
        assert result.startswith("02:00:00")
