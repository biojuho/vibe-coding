"""Notion schema definitions, auto-detection, and validation.

Mixin: NotionSchemaMixin  — NotionUploader의 스키마 관련 책임을 분리.
사용법: NotionUploader(NotionSchemaMixin, ...) 형태로 믹스인.
"""

from __future__ import annotations

import re


class NotionSchemaMixin:
    """Notion DB 스키마 정의·자동감지·검증을 담당하는 Mixin."""

    # ── 검토 중심 기본 속성 시맨틱 키 → 한국어 속성명 ──
    DEFAULT_PROPS = {
        "title": "콘텐츠",
        "memo": "메모",
        "status": "상태",
        "date": "생성일",
        "url": "원본 URL",
        "source": "원본 소스",
        "topic_cluster": "토픽 클러스터",
        "emotion_axis": "감정 축",
        "final_rank_score": "최종 랭크 점수",
        "creator_take": "운영자 해석",
        "review_focus": "검토 포인트",
        "feedback_request": "피드백 요청",
        "risk_flags": "위험 신호",
        "evidence_anchor": "근거 앵커",
        "rejection_reasons": "반려 사유",
        "tweet_body": "트윗 본문",
        "reply_text": "답글 텍스트",
        "threads_body": "Threads 본문",
        "blog_body": "블로그 본문",
        "publish_platforms": "발행 플랫폼",
        "performance_grade": "성과 등급",
    }

    # Deprecated: 이전에 사용하던 속성들. Notion DB에는 남아 있을 수 있으나 코드에서 참조하지 않음.
    DEPRECATED_PROPS = {
        "image_needed": "이미지 필요",
        "tweet_url": "트윗 링크",
        "views": "24h 조회수",
        "likes": "24h 좋아요",
        "retweets": "24h 리트윗",
        "feed_mode": "피드 모드",
        "hook_type": "훅 타입",
        "audience_fit": "대상 독자",
        "scrape_quality_score": "스크랩 품질 점수",
        "publishability_score": "발행 적합도 점수",
        "performance_score": "성과 예측 점수",
        "review_status": "승인 상태",
        "review_note": "검토 메모",
        "chosen_draft_type": "선택 초안 타입",
        "newsletter_body": "뉴스레터 초안",
        "publish_channel": "발행 채널",
        "published_at": "발행 시각",
        "threads_url": "Threads 링크",
        "blog_url": "블로그 링크",
        "publish_scheduled_at": "발행 예정일",
        "regulation_status": "규제 검증",
        "screenshot_url": "스크린샷 URL",
    }

    PROP_ENV_OVERRIDES = {key: f"NOTION_PROP_{key.upper()}" for key in DEFAULT_PROPS}

    EXPECTED_TYPES = {
        "title": {"title"},
        "memo": {"rich_text"},
        "status": {"status", "select"},
        "date": {"date"},
        "url": {"url", "rich_text"},
        "source": {"select", "rich_text"},
        "topic_cluster": {"select", "rich_text"},
        "emotion_axis": {"select", "rich_text"},
        "final_rank_score": {"number"},
        "creator_take": {"rich_text"},
        "review_focus": {"rich_text"},
        "feedback_request": {"rich_text"},
        "risk_flags": {"multi_select", "rich_text"},
        "evidence_anchor": {"rich_text"},
        "rejection_reasons": {"multi_select", "rich_text"},
        "tweet_body": {"rich_text"},
        "reply_text": {"rich_text"},
        "threads_body": {"rich_text"},
        "blog_body": {"rich_text"},
        "publish_platforms": {"multi_select", "rich_text"},
        "performance_grade": {"select", "rich_text"},
    }

    AUTO_DETECT_KEYWORDS = {
        "title": ("title", "제목", "name", "콘텐츠"),
        "memo": ("memo", "메모", "summary", "요약"),
        "status": ("status", "상태", "stage"),
        "date": ("date", "생성", "created"),
        "url": ("url", "원본", "source"),
        "source": ("source", "출처", "원본 소스"),
        "topic_cluster": ("topic", "토픽"),
        "emotion_axis": ("emotion", "감정"),
        "final_rank_score": ("rank", "랭크", "score"),
        "creator_take": ("creator", "운영자 해석", "한줄 해석"),
        "review_focus": ("review focus", "검토 포인트", "판단 포인트"),
        "feedback_request": ("feedback", "피드백 요청", "검토 요청"),
        "risk_flags": ("risk", "위험 신호", "주의 라벨"),
        "evidence_anchor": ("anchor", "근거 앵커", "근거"),
        "rejection_reasons": ("reject", "반려 사유", "반려 이유"),
        "tweet_body": ("tweet", "트윗", "draft", "초안"),
        "reply_text": ("reply", "답글", "답글 텍스트"),
        "threads_body": ("threads", "쓰레드", "Threads 본문"),
        "blog_body": ("blog", "블로그", "블로그 본문"),
        "publish_platforms": ("platforms", "플랫폼", "발행 플랫폼"),
        "performance_grade": ("grade", "성과 등급"),
    }

    TRACKING_QUERY_KEYS = {"fbclid", "gclid", "igshid", "ref", "ref_src", "ref_url", "feature"}
    NOTION_ID_REGEX = re.compile(
        r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[0-9a-fA-F]{32})"
    )

    # ── 메서드 ──

    @classmethod
    def normalize_notion_id(cls, raw_id):
        """Notion ID (32-hex 또는 UUID 형식) → 정규 UUID로 변환."""
        if not raw_id:
            return ""
        value = str(raw_id).strip()
        if not value:
            return ""
        matches = cls.NOTION_ID_REGEX.findall(value)
        if not matches:
            return value
        token = matches[-1].replace("-", "").lower()
        if len(token) != 32:
            return value
        return f"{token[0:8]}-{token[8:12]}-{token[12:16]}-{token[16:20]}-{token[20:32]}"

    @staticmethod
    def _pick_by_keywords(candidates, keywords, used, allow_fallback=True):
        """DB 속성 목록(candidates)에서 키워드 매칭으로 최적 속성 선택."""
        lowered_keywords = [item.lower() for item in keywords]
        for candidate in candidates:
            if candidate in used:
                continue
            lower_name = candidate.lower()
            if any(keyword in lower_name for keyword in lowered_keywords):
                return candidate
        if not allow_fallback:
            return None
        for candidate in candidates:
            if candidate not in used:
                return candidate
        return None

    def _auto_detect_props(self, db_props):
        """DB 속성 목록에서 시맨틱 키와 매칭되는 속성을 자동 감지."""
        by_type: dict[str, list[str]] = {}
        for prop_name, prop_data in db_props.items():
            by_type.setdefault(prop_data.get("type"), []).append(prop_name)

        detected = {}
        used: set[str] = set()
        for semantic_key, expected_types in self.EXPECTED_TYPES.items():
            candidates: list[str] = []
            for prop_type in expected_types:
                candidates.extend(by_type.get(prop_type, []))
            if not candidates:
                continue
            picked = self._pick_by_keywords(
                candidates,
                self.AUTO_DETECT_KEYWORDS.get(semantic_key, (semantic_key,)),
                used,
                allow_fallback=False,
            )
            if picked:
                detected[semantic_key] = picked
                used.add(picked)
        return detected

    def _resolve_props(self, auto_props):
        """환경변수 > config > 자동감지 > 기본값 우선순위로 속성명 확정."""
        resolved = {}
        for key, default_name in self.DEFAULT_PROPS.items():
            env_name = self._env_props.get(key)
            manual_name = self._manual_props.get(key)
            auto_name = auto_props.get(key)
            if env_name:
                resolved[key] = env_name
            elif manual_name and manual_name in self._db_properties:
                resolved[key] = manual_name
            elif auto_name:
                resolved[key] = auto_name
            else:
                resolved[key] = manual_name or default_name
        return resolved

    def _validate_props(self):
        """필수 속성 존재 및 타입 일치 여부 검증."""
        required_keys = {"title", "status", "date", "url", "tweet_body"}
        missing = []
        mismatch = []
        for key, expected_types in self.EXPECTED_TYPES.items():
            prop_name = self.props.get(key)
            if not prop_name:
                if key in required_keys:
                    missing.append(f"{key}(empty)")
                continue

            meta = self._db_properties.get(prop_name)
            if not meta:
                if key in required_keys:
                    missing.append(f"{key}='{prop_name}'")
                continue

            if meta.get("type") not in expected_types:
                mismatch.append(f"{key}='{prop_name}' type={meta.get('type')}, expected={sorted(expected_types)}")

        if missing or mismatch:
            detail = []
            if missing:
                detail.append("missing: " + ", ".join(missing))
            if mismatch:
                detail.append("type_mismatch: " + ", ".join(mismatch))
            return False, "; ".join(detail)
        return True, ""
