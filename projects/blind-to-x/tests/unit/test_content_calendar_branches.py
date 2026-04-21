from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.content_calendar import ContentCalendar  # noqa: E402


class FakeDB:
    def __init__(self, rows: list[tuple[str, str, str, str]] | None = None, fail: bool = False):
        self.fail = fail
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            """
            CREATE TABLE draft_analytics (
                topic_cluster TEXT,
                hook_type TEXT,
                emotion_axis TEXT,
                recorded_at TEXT,
                published INTEGER
            )
            """
        )
        for row in rows or []:
            self.conn.execute(
                """
                INSERT INTO draft_analytics (topic_cluster, hook_type, emotion_axis, recorded_at, published)
                VALUES (?, ?, ?, ?, 1)
                """,
                row,
            )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    def __del__(self) -> None:
        self.close()

    @contextmanager
    def _connect(self):
        if self.fail:
            raise sqlite3.OperationalError("db unavailable")
        try:
            yield self.conn
        finally:
            pass


_KST = timezone(timedelta(hours=9))


def _recent_row(topic: str, hook: str, emotion: str) -> tuple[str, str, str, str]:
    return (topic, hook, emotion, datetime.now(_KST).strftime("%Y-%m-%d %H:%M:%S"))


def test_get_recent_posts_reads_from_db() -> None:
    db = FakeDB(
        rows=[
            _recent_row("career", "story", "curious"),
            _recent_row("salary", "question", "anxious"),
        ]
    )
    calendar = ContentCalendar(cost_db=db)

    posts = calendar._get_recent_posts(hours=12, limit=10)

    assert len(posts) == 2
    assert posts[0]["topic_cluster"] in {"career", "salary"}
    assert {post["hook_type"] for post in posts} == {"story", "question"}


def test_get_recent_posts_gracefully_handles_db_errors() -> None:
    calendar = ContentCalendar(cost_db=FakeDB(fail=True))
    assert calendar._get_recent_posts() == []


def test_should_post_topic_blocks_repeated_topic() -> None:
    calendar = ContentCalendar(
        cost_db=FakeDB(rows=[_recent_row("career", "story", "curious"), _recent_row("career", "question", "calm")])
    )

    ok, reason = calendar.should_post_topic("career", "new-hook", "new-emotion")

    assert ok is False
    assert "career" in reason


def test_should_post_topic_blocks_repeated_hook() -> None:
    calendar = ContentCalendar(
        cost_db=FakeDB(rows=[_recent_row("career", "story", "curious"), _recent_row("salary", "story", "calm")])
    )

    ok, reason = calendar.should_post_topic("fresh-topic", "story", "new-emotion")

    assert ok is False
    assert "story" in reason


def test_should_post_topic_blocks_repeated_emotion() -> None:
    calendar = ContentCalendar(
        cost_db=FakeDB(
            rows=[
                _recent_row("career", "story", "anxious"),
                _recent_row("salary", "question", "anxious"),
                _recent_row("culture", "list", "anxious"),
            ]
        )
    )

    ok, reason = calendar.should_post_topic("fresh-topic", "fresh-hook", "anxious")

    assert ok is False
    assert "anxious" in reason


def test_should_post_topic_allows_post_when_under_thresholds() -> None:
    calendar = ContentCalendar(
        cost_db=FakeDB(rows=[_recent_row("career", "story", "curious")]),
        rules={"max_same_topic": 3, "max_same_hook": 3, "max_same_emotion": 4},
    )

    ok, reason = calendar.should_post_topic("salary", "question", "calm")

    assert ok is True
    assert reason == ""
