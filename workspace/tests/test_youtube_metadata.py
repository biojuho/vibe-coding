from __future__ import annotations

from execution.youtube_metadata import MAX_DESCRIPTION_BYTES, MAX_TAG_CHARS, build_shorts_upload_metadata


def _youtube_tag_char_count(tags: list[str]) -> int:
    total = 0
    for index, tag in enumerate(tags):
        total += len(tag)
        if " " in tag:
            total += 2
        if index:
            total += 1
    return total


def test_build_shorts_upload_metadata_uses_context_and_safe_limits() -> None:
    description, tags = build_shorts_upload_metadata(
        {
            "topic": "<Black Hole> explained in one minute",
            "title": "Why Black Holes Bend Light",
            "channel": "space science",
            "hook_pattern": "question hook",
            "duration_sec": 42.2,
        }
    )

    assert description.startswith("Why Black Holes Bend Light")
    assert "핵심 요약: Black Hole explained in one minute" in description
    assert "question hook 훅" in description
    assert "42초 분량" in description
    assert "#Shorts" in description
    assert "#spacescience" in description
    assert "<" not in description
    assert ">" not in description
    assert len(description.encode("utf-8")) <= MAX_DESCRIPTION_BYTES
    assert tags[:4] == [
        "space science",
        "Black Hole explained in one minute",
        "Why Black Holes Bend Light",
        "question hook",
    ]
    assert _youtube_tag_char_count(tags) <= MAX_TAG_CHARS


def test_build_shorts_upload_metadata_truncates_description_by_utf8_bytes() -> None:
    description, _tags = build_shorts_upload_metadata(
        {
            "topic": "한글" * 3000,
            "title": "제목",
            "channel": "AI/Tech",
        }
    )

    assert len(description.encode("utf-8")) <= MAX_DESCRIPTION_BYTES
    assert description.encode("utf-8").decode("utf-8") == description


def test_build_shorts_upload_metadata_counts_spaced_tags_like_youtube_api() -> None:
    long_spaced_topic = " ".join([f"tag{i:02d}" for i in range(80)])

    _description, tags = build_shorts_upload_metadata(
        {
            "topic": long_spaced_topic,
            "title": long_spaced_topic,
            "channel": "space science",
            "hook_pattern": "curiosity gap",
        }
    )

    assert "space science" in tags
    assert _youtube_tag_char_count(tags) <= MAX_TAG_CHARS
