"""Content Calendar — 토픽/훅/감정 반복 방지 가드.

연속으로 비슷한 콘텐츠를 게시하는 것을 방지하여
피드의 다양성을 유지합니다.

사용법:
    calendar = ContentCalendar()
    ok, reason = calendar.should_post_topic("연봉", "논쟁형", "분노")
    if not ok:
        logger.info("Calendar skip: %s", reason)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# KST 타임존
_KST = timezone(timedelta(hours=9))

# 기본 다양성 규칙
_DEFAULT_RULES = {
    "topic_window_hours": 6,      # 같은 토픽 허용 윈도우
    "max_same_topic": 2,          # 윈도우 내 같은 토픽 최대 수
    "hook_lookback": 3,           # 최근 N건 내 같은 hook_type 최대 수
    "max_same_hook": 2,
    "emotion_lookback": 5,        # 최근 N건 내 같은 emotion_axis 최대 수
    "max_same_emotion": 3,
}


class ContentCalendar:
    """콘텐츠 다양성 가드.

    cost_db의 draft_analytics 테이블에서 최근 게시 이력을 조회하여
    토픽/훅/감정의 반복을 방지합니다.
    """

    def __init__(self, cost_db: Any = None, rules: dict | None = None):
        self._db = cost_db
        self._rules = {**_DEFAULT_RULES, **(rules or {})}

    def _get_recent_posts(self, hours: int = 12, limit: int = 20) -> list[dict]:
        """cost_db에서 최근 게시된 포스트 목록을 조회합니다."""
        if self._db is None:
            return []
        try:
            cutoff = (datetime.now(_KST) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            with self._db._connect() as conn:
                rows = conn.execute(
                    """SELECT topic_cluster, hook_type, emotion_axis, recorded_at
                       FROM draft_analytics
                       WHERE recorded_at >= ? AND published = 1
                       ORDER BY recorded_at DESC
                       LIMIT ?""",
                    (cutoff, limit),
                ).fetchall()
            return [
                {
                    "topic_cluster": r[0] or "",
                    "hook_type": r[1] or "",
                    "emotion_axis": r[2] or "",
                    "recorded_at": r[3] or "",
                }
                for r in rows
            ]
        except Exception as exc:
            logger.debug("ContentCalendar DB query failed: %s", exc)
            return []

    def should_post_topic(
        self,
        topic_cluster: str,
        hook_type: str = "",
        emotion_axis: str = "",
    ) -> tuple[bool, str]:
        """토픽/훅/감정 다양성 규칙에 따라 게시 여부를 판단합니다.

        Returns:
            (True, "") if 게시 가능
            (False, "이유 설명") if 스킵 권장
        """
        rules = self._rules
        window_hours = rules["topic_window_hours"]
        recent = self._get_recent_posts(hours=window_hours, limit=20)

        if not recent:
            return True, ""

        # 규칙 1: 같은 토픽이 윈도우 내 최대 수 초과
        if topic_cluster:
            same_topic_count = sum(
                1 for p in recent if p["topic_cluster"] == topic_cluster
            )
            max_topic = rules["max_same_topic"]
            if same_topic_count >= max_topic:
                return (
                    False,
                    f"토픽 '{topic_cluster}' 최근 {window_hours}시간 내 {same_topic_count}건 (최대 {max_topic})",
                )

        # 규칙 2: 최근 N건 중 같은 hook_type 과다
        if hook_type:
            lookback = min(rules["hook_lookback"], len(recent))
            same_hook = sum(
                1 for p in recent[:lookback] if p["hook_type"] == hook_type
            )
            max_hook = rules["max_same_hook"]
            if same_hook >= max_hook:
                return (
                    False,
                    f"훅 '{hook_type}' 최근 {lookback}건 중 {same_hook}건 (최대 {max_hook})",
                )

        # 규칙 3: 최근 N건 중 같은 emotion_axis 과다
        if emotion_axis:
            lookback = min(rules["emotion_lookback"], len(recent))
            same_emotion = sum(
                1 for p in recent[:lookback] if p["emotion_axis"] == emotion_axis
            )
            max_emotion = rules["max_same_emotion"]
            if same_emotion >= max_emotion:
                return (
                    False,
                    f"감정 '{emotion_axis}' 최근 {lookback}건 중 {same_emotion}건 (최대 {max_emotion})",
                )

        return True, ""
