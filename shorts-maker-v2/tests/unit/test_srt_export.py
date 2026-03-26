"""srt_export 단위 테스트."""

from __future__ import annotations

from pathlib import Path

from shorts_maker_v2.render.karaoke import WordSegment
from shorts_maker_v2.render.srt_export import (
    _format_timestamp,
    _generate_srt_from_narrations,
    export_srt,
    generate_srt_from_words,
)


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


def test_generate_srt_from_words_merges_short_chunk(monkeypatch) -> None:
    monkeypatch.setattr(
        "shorts_maker_v2.render.srt_export.group_into_chunks",
        lambda words, chunk_size: [
            (0.0, 0.2, "짧은 자막"),
            (0.2, 1.0, "이어지는 자막"),
        ],
    )

    result = generate_srt_from_words([WordSegment("a", 0.0, 0.1)], chunk_size=1, min_duration_sec=0.5)

    assert "00:00:00,000 --> 00:00:01,000" in result
    assert "짧은 자막 이어지는 자막" in result
    assert result.splitlines()[0] == "1"


def test_generate_srt_from_words_flushes_last_pending_chunk(monkeypatch) -> None:
    monkeypatch.setattr(
        "shorts_maker_v2.render.srt_export.group_into_chunks",
        lambda words, chunk_size: [
            (1.0, 1.2, "마지막 자막"),
        ],
    )

    result = generate_srt_from_words([WordSegment("a", 1.0, 1.2)], chunk_size=1, min_duration_sec=0.5)

    assert "00:00:01,000 --> 00:00:01,500" in result
    assert "마지막 자막" in result


def test_export_srt_writes_shifted_words_json(tmp_path: Path, monkeypatch) -> None:
    json_path = tmp_path / "scene_words.json"
    json_path.write_text("[]", encoding="utf-8")
    output_path = tmp_path / "captions" / "result.srt"

    monkeypatch.setattr(
        "shorts_maker_v2.render.srt_export.load_words_json",
        lambda path: [WordSegment("hello", 0.0, 0.6), WordSegment("world", 0.6, 1.2)],
    )

    result = export_srt([json_path], [2.5], output_path, chunk_size=2)

    assert result == output_path
    text = output_path.read_text(encoding="utf-8")
    assert "00:00:02,500 --> 00:00:03,700" in text
    assert "hello world" in text


def test_export_srt_falls_back_to_narrations(tmp_path: Path) -> None:
    output_path = tmp_path / "fallback.srt"

    result = export_srt(
        words_json_paths=[tmp_path / "missing_words.json"],
        scene_offsets=[0.0, 3.0],
        output_path=output_path,
        narrations=["첫 문장. 둘째 문장!", "   "],
        durations=[2.0, 1.0],
    )

    assert result == output_path
    text = output_path.read_text(encoding="utf-8")
    assert "첫 문장." in text
    assert "둘째 문장!" in text
    assert "00:00:00,000 --> 00:00:01,000" in text
    assert "00:00:01,000 --> 00:00:02,000" in text


def test_export_srt_returns_output_path_without_writing_when_no_inputs(tmp_path: Path) -> None:
    output_path = tmp_path / "empty.srt"

    result = export_srt(
        words_json_paths=[tmp_path / "missing_words.json"],
        scene_offsets=[0.0],
        output_path=output_path,
    )

    assert result == output_path
    assert not output_path.exists()


def test_generate_srt_from_narrations_preserves_decimal_numbers() -> None:
    result = _generate_srt_from_narrations(
        narrations=["성장률은 3.5%였다. 다음 문장도 있다!"],
        durations=[4.0],
        offsets=[1.0],
    )

    assert "성장률은 3.5%였다." in result
    assert "다음 문장도 있다!" in result
    assert "00:00:01,000 --> 00:00:03,000" in result
    assert "00:00:03,000 --> 00:00:05,000" in result
