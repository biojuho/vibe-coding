"""뉴스레터 자동 발행 스케줄러 (P4-M3).

Notion DB에서 발행 대기 콘텐츠를 수집하고, 큐레이션·포맷팅·최적 시간대
기반으로 뉴스레터 에디션을 빌드합니다.

사용법:
    scheduler = NewsletterScheduler(config_mgr, notion_uploader)
    edition = await scheduler.build_newsletter_edition()
    print(edition["preview"])
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# KST 오프셋
_KST = timezone(timedelta(hours=9))


class NewsletterScheduler:
    """뉴스레터 자동 발행 스케줄러.

    1. Notion DB에서 '검토완료'/'발행승인' 상태 콘텐츠 수집
    2. curate_newsletter_from_records()로 상위 N건 큐레이팅
    3. PublishOptimizer로 최적 발행 시간대 결정
    4. newsletter_formatter로 포맷팅
    5. 에디션 리포트 반환 (발행은 사용자 승인 후)
    """

    # 수집 대상 Notion 상태값
    READY_STATUSES = {"검토완료", "발행승인", "승인"}

    def __init__(self, config_mgr=None, notion_uploader=None):
        self.config = config_mgr
        self.notion = notion_uploader

    # ── 설정 헬퍼 ─────────────────────────────────────────────────────
    def _cfg(self, key: str, default=None):
        if self.config is None:
            return default
        return self.config.get(key, default)

    @property
    def max_items(self) -> int:
        return int(self._cfg("newsletter.max_items_per_edition", 5))

    @property
    def min_items(self) -> int:
        return int(self._cfg("newsletter.min_items_for_publish", 2))

    @property
    def auto_publish(self) -> bool:
        return bool(self._cfg("newsletter.auto_publish", False))

    @property
    def output_platforms(self) -> list[str]:
        return self._cfg("newsletter.output_platforms", ["newsletter"])

    # ── 콘텐츠 수집 ──────────────────────────────────────────────────
    async def collect_ready_contents(self) -> list[dict[str, Any]]:
        """Notion DB에서 발행 대기 상태인 콘텐츠를 수집합니다.

        Returns:
            승인된 콘텐츠 레코드 리스트 (최종 랭크 점수 내림차순).
        """
        if self.notion is None:
            logger.warning("Notion uploader 미설정. 빈 리스트 반환.")
            return []

        try:
            # NotionUploader.fetch_recent_records() 사용
            records = await self.notion.fetch_recent_records(
                lookback_days=int(self._cfg("analytics.lookback_days", 30)),
            )
        except Exception as exc:
            logger.error("Notion 레코드 수집 실패: %s", exc)
            return []

        # 발행 대기 상태 필터링
        ready = [
            r for r in records
            if str(r.get("status", "")).strip() in self.READY_STATUSES
            and r.get("newsletter_body")  # 뉴스레터 초안 있는 것만
        ]

        def _safe_float(val: Any) -> float:
            try:
                return float(val or 0)
            except (ValueError, TypeError):
                return 0.0

        # final_rank_score 내림차순 정렬
        ready.sort(
            key=lambda r: _safe_float(r.get("final_rank_score")),
            reverse=True,
        )

        logger.info(
            "뉴스레터 발행 대기 콘텐츠: %d건 (전체 %d건 중 승인 상태)",
            len(ready), len(records),
        )
        return ready

    # ── 에디션 빌드 ──────────────────────────────────────────────────
    async def build_newsletter_edition(
        self,
        records: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """뉴스레터 에디션을 구성합니다.

        Args:
            records: 직접 전달 시 사용. None이면 Notion에서 수집.

        Returns:
            {
                "items": [큐레이팅된 레코드들],
                "item_count": int,
                "preview": str (포맷팅 미리보기),
                "optimal_slot": str,
                "can_publish": bool,
                "platforms": ["newsletter", ...],
                "built_at": ISO timestamp,
            }
        """
        if records is None:
            records = await self.collect_ready_contents()

        # 큐레이션
        from pipeline.newsletter_formatter import curate_newsletter_from_records
        curated = curate_newsletter_from_records(records, max_items=self.max_items)

        # 최적 발행 시간대 결정
        optimal_slot = self._get_optimal_slot(records)

        # 에디션 미리보기 생성
        preview = self._build_preview(curated, optimal_slot)

        can_publish = len(curated) >= self.min_items

        edition = {
            "items": curated,
            "item_count": len(curated),
            "preview": preview,
            "optimal_slot": optimal_slot,
            "can_publish": can_publish,
            "platforms": self.output_platforms,
            "built_at": datetime.now(_KST).isoformat(),
        }

        if not can_publish:
            logger.info(
                "뉴스레터 발행 불가: %d건 < 최소 %d건",
                len(curated), self.min_items,
            )
        else:
            logger.info(
                "뉴스레터 에디션 빌드 완료: %d건, 최적 시간대=%s",
                len(curated), optimal_slot,
            )

        return edition

    # ── 블로그 포맷 변환 ──────────────────────────────────────────────
    def format_for_platforms(
        self,
        edition: dict[str, Any],
    ) -> dict[str, str]:
        """에디션의 콘텐츠를 각 플랫폼 포맷으로 변환합니다.

        Returns:
            {"newsletter": "...", "naver": "...", "brunch": "..."}
        """
        from pipeline.newsletter_formatter import (
            NewsletterResult,
            format_for_blog,
        )

        outputs: dict[str, str] = {}
        items = edition.get("items", [])

        # 뉴스레터 합본 텍스트
        newsletter_parts = []
        for i, item in enumerate(items, 1):
            body = item.get("newsletter_body") or ""
            title = item.get("title") or f"콘텐츠 {i}"
            newsletter_parts.append(f"## {i}. {title}\n\n{body}")

        newsletter_text = "\n\n---\n\n".join(newsletter_parts)
        outputs["newsletter"] = newsletter_text

        # 블로그 포맷
        for platform in edition.get("platforms", []):
            if platform in ("naver", "brunch"):
                try:
                    # 첫 번째 아이템으로 블로그 생성
                    if items:
                        first = items[0]
                        first_body = first.get("newsletter_body") or ""
                        first_title = first.get("title") or ""
                        nr = NewsletterResult(
                            hook=first_title,
                            story=first_body,
                            insight="직장인 커뮤니티에서 화제가 된 이야기를 큐레이션했습니다.",
                            cta="댓글로 여러분의 경험을 공유해주세요.",
                            full_text=first_body,
                            word_count=len(first_body.split()),
                            char_count=len(first_body),
                            topic_cluster=first.get("topic_cluster", "기타"),
                            emotion_axis=first.get("emotion_axis", "공감"),
                        )
                        outputs[platform] = format_for_blog(nr, platform=platform)
                except Exception as exc:
                    logger.warning("블로그 포맷 변환 실패 (%s): %s", platform, exc)

        return outputs

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────
    def _get_optimal_slot(self, records: list[dict[str, Any]]) -> str:
        """PublishOptimizer를 사용하여 최적 발행 시간대를 결정합니다."""
        try:
            from pipeline.publish_optimizer import PublishOptimizer
            optimizer = PublishOptimizer()
            recommendations = optimizer.get_optimal_publish_time(records)
            if recommendations:
                return recommendations[0]["slot"]
        except Exception as exc:
            logger.debug("발행 시간 최적화 실패, 기본 사용: %s", exc)
        return "점심"  # 기본 추천

    def _build_preview(
        self,
        curated: list[dict[str, Any]],
        optimal_slot: str,
    ) -> str:
        """에디션 미리보기 텍스트를 생성합니다."""
        now_kst = datetime.now(_KST)
        lines = [
            f"📰 Blind-to-X 뉴스레터 에디션 미리보기",
            f"   빌드 시각: {now_kst.strftime('%Y-%m-%d %H:%M KST')}",
            f"   추천 발행 시간대: {optimal_slot}",
            f"   선별 콘텐츠: {len(curated)}건",
            "",
        ]

        for i, item in enumerate(curated, 1):
            title = item.get("title", "(제목 없음)")
            source = item.get("source", "?")
            topic = item.get("topic_cluster", "기타")
            score = item.get("final_rank_score", 0)
            lines.append(f"   {i}. [{source}] {title}")
            lines.append(f"      토픽={topic}, 점수={score}")

        return "\n".join(lines)


def get_current_kst_slot() -> str:
    """현재 KST 시간대 슬롯 반환."""
    try:
        kst_hour = datetime.now(_KST).hour
    except Exception:
        import time
        kst_hour = (time.gmtime().tm_hour + 9) % 24

    if 6 <= kst_hour < 12:
        return "오전"
    elif 12 <= kst_hour < 14:
        return "점심"
    elif 14 <= kst_hour < 18:
        return "오후"
    elif 18 <= kst_hour < 22:
        return "저녁"
    return "심야"


def is_publish_window(target_slot: str | None = None) -> bool:
    """현재 시각이 발행 타겟 시간대인지 확인."""
    current = get_current_kst_slot()
    if target_slot is None:
        # 기본 발행 시간: 오전, 점심, 저녁
        return current in {"오전", "점심", "저녁"}
    return current == target_slot
