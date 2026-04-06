"""Helpers for selecting performance examples and building reports."""

from __future__ import annotations

import logging
import math
from collections import Counter
from typing import Any

from pipeline.rules_loader import get_rule_section

logger = logging.getLogger(__name__)


class FeedbackLoop:
    def __init__(self, notion_uploader, config):
        self.notion_uploader = notion_uploader
        self.config = config

    @staticmethod
    def _load_yaml_golden_examples(limit: int) -> list[dict[str, Any]]:
        try:
            golden = get_rule_section("golden_examples", {}) or {}
            flattened: list[dict[str, Any]] = []
            for topic_cluster, examples in golden.items():
                for example in examples or []:
                    flattened.append(
                        {
                            "views": 0,
                            "text": example.get("text", ""),
                            "topic_cluster": topic_cluster,
                            "hook_type": example.get("hook_type", "공감형"),
                            "emotion_axis": example.get("emotion_axis", "공감"),
                            "draft_style": example.get("hook_type", "공감형"),
                            "example_source": "yaml_golden",
                        }
                    )
            return flattened[:limit]
        except Exception as exc:
            logger.warning("Failed to load YAML golden examples: %s", exc)
            return []

    @staticmethod
    def _pearson_corr(xs: list[float], ys: list[float]) -> float:
        """두 리스트의 Pearson 상관계수. 계산 불가 시 0.0 반환."""
        n = len(xs)
        if n < 3:
            return 0.0
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
        den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
        if den_x < 1e-9 or den_y < 1e-9:
            return 0.0
        return num / (den_x * den_y)

    async def compute_adaptive_weights(self) -> dict[str, float]:
        """실제 트위터 성과(조회수) 기반으로 랭킹 가중치를 자동 산출.

        - 각 점수 타입(품질/발행적합도/성과예측)과 실제 조회수의 상관계수 계산
        - 상관계수를 정규화하여 가중치로 변환 (10%~60% 범위 클리핑)
        - 데이터 부족(< 5건) 시 빈 dict 반환 → 기본 가중치 유지
        """
        records = await self.notion_uploader.get_top_performing_posts(
            limit=50,
            lookback_days=int(self.config.get("analytics.lookback_days", 30)),
            minimum_posts=0,
            allow_fallback_examples=False,
        )
        # 실제 성과 데이터가 있는 레코드만 사용
        valid = [
            r
            for r in records
            if r.get("views")
            and float(r.get("views") or 0) > 0
            and r.get("scrape_quality_score")
            and r.get("publishability_score")
            and r.get("performance_score")
        ]
        if len(valid) < 5:
            logger.info("적응형 가중치 산출 불가: 유효 데이터 %d건 (최소 5건 필요)", len(valid))
            return {}

        actual = [float(r.get("views") or 0) for r in valid]
        quality = [float(r.get("scrape_quality_score") or 50) for r in valid]
        pub = [float(r.get("publishability_score") or 50) for r in valid]
        perf = [float(r.get("performance_score") or 50) for r in valid]

        corr_q = self._pearson_corr(quality, actual)
        corr_p = self._pearson_corr(pub, actual)
        corr_e = self._pearson_corr(perf, actual)

        logger.info(
            "성과 상관계수 — scrape_quality: %.3f, publishability: %.3f, performance: %.3f",
            corr_q,
            corr_p,
            corr_e,
        )

        # 음수 상관은 0으로 처리 후 정규화
        raw = [max(0.0, corr_q), max(0.0, corr_p), max(0.0, corr_e)]
        total = sum(raw)
        if total < 0.01:
            logger.info("모든 상관계수 ≤ 0. 기본 가중치 유지.")
            return {}

        # 10%~60% 범위로 클리핑 후 재정규화
        clipped = [max(0.10, min(0.60, _v / total)) for _v in raw]
        total_clipped = sum(clipped)
        weights = {
            "scrape_quality": round(clipped[0] / total_clipped, 3),
            "publishability": round(clipped[1] / total_clipped, 3),
            "performance": round(clipped[2] / total_clipped, 3),
        }
        logger.info("적응형 가중치 산출 완료 (%d건 기반): %s", len(valid), weights)
        return weights

    async def get_few_shot_examples(self, limit: int | None = None) -> list[dict[str, Any]]:
        lookback_days = int(self.config.get("analytics.lookback_days", 30))
        top_limit = limit or int(self.config.get("analytics.top_examples_limit", 5))
        minimum_posts = int(self.config.get("analytics.minimum_posts_for_feedback", 20))
        performance_examples = await self.notion_uploader.get_top_performing_posts(
            limit=top_limit,
            lookback_days=lookback_days,
            minimum_posts=minimum_posts,
            allow_fallback_examples=False,
        )
        if performance_examples:
            return performance_examples

        approved_examples = await self.notion_uploader.get_recent_approved_posts(
            limit=top_limit,
            lookback_days=lookback_days,
        )
        if approved_examples:
            logger.info("Few-shot fallback: using %d approved examples", len(approved_examples))
            return approved_examples

        yaml_examples = self._load_yaml_golden_examples(top_limit)
        if yaml_examples:
            logger.info("Few-shot fallback: using %d YAML golden examples", len(yaml_examples))
        return yaml_examples

    # ── P1-B2: 성공/실패 패턴 분석 ────────────────────────────────────

    @staticmethod
    def analyze_success_patterns(
        records: list[dict[str, Any]],
        grade_filter: set[str] | None = None,
    ) -> dict[str, Any]:
        """S/A등급 트윗의 공통 패턴 추출 (P1-B2).

        Returns:
            {
                "count": int,
                "top_topics": [(topic, count), ...],
                "top_hooks": [(hook, count), ...],
                "top_emotions": [(emotion, count), ...],
                "top_styles": [(style, count), ...],
                "avg_rank_score": float,
                "insights": [str, ...],
            }
        """
        if grade_filter is None:
            grade_filter = {"S", "A"}

        winners = [r for r in records if r.get("performance_grade", "D") in grade_filter]
        if not winners:
            return {"count": 0, "insights": ["S/A등급 데이터 없음. 더 많은 발행이 필요합니다."]}

        topic_c = Counter(r.get("topic_cluster", "기타") for r in winners)
        hook_c = Counter(r.get("hook_type", "공감형") for r in winners)
        emotion_c = Counter(r.get("emotion_axis", "공감") for r in winners)
        style_c = Counter(r.get("chosen_draft_type") or r.get("recommended_draft_type") or "공감형" for r in winners)

        scores = [float(r.get("final_rank_score", 0) or 0) for r in winners]
        avg_score = sum(scores) / len(scores) if scores else 0

        # 인사이트 자동 생성
        insights = []
        if topic_c.most_common(1):
            top_t, top_cnt = topic_c.most_common(1)[0]
            ratio = top_cnt / len(winners) * 100
            insights.append(f"S/A 트윗의 {ratio:.0f}%가 '{top_t}' 토픽 (우세)")
        if hook_c.most_common(1):
            top_h, _ = hook_c.most_common(1)[0]
            insights.append(f"최다 성공 훅 타입: {top_h}")
        if avg_score > 0:
            insights.append(f"평균 발행 전 랭크 점수: {avg_score:.1f}")

        return {
            "count": len(winners),
            "top_topics": topic_c.most_common(5),
            "top_hooks": hook_c.most_common(5),
            "top_emotions": emotion_c.most_common(5),
            "top_styles": style_c.most_common(5),
            "avg_rank_score": round(avg_score, 2),
            "insights": insights,
        }

    @staticmethod
    def get_failure_patterns(
        records: list[dict[str, Any]],
        min_occurrences: int = 3,
    ) -> dict[str, Any]:
        """D등급 반복 실패 패턴 식별 및 필터 규칙 생성 (P1-B2).

        Returns:
            {
                "count": int,
                "risky_combos": [(combo_key, count), ...],
                "auto_filters": [{"type": ..., "value": ..., "reason": ...}, ...],
            }
        """
        losers = [r for r in records if r.get("performance_grade") == "D"]
        if not losers:
            return {"count": 0, "risky_combos": [], "auto_filters": []}

        # 토픽+훅 조합별 실패 빈도
        combo_c: Counter = Counter()
        topic_c: Counter = Counter()
        for r in losers:
            topic = r.get("topic_cluster", "기타")
            hook = r.get("hook_type", "공감형")
            combo_c[f"{topic}+{hook}"] += 1
            topic_c[topic] += 1

        risky = [(k, _v) for k, _v in combo_c.most_common(10) if _v >= min_occurrences]

        # 자동 필터 규칙 생성
        auto_filters = []
        for combo, cnt in risky:
            auto_filters.append(
                {
                    "type": "topic_hook_combo",
                    "value": combo,
                    "count": cnt,
                    "reason": f"{combo} 조합이 {cnt}회 D등급 — 발행 전 추가 검토 권장",
                }
            )

        # 지나치게 실패하는 토픽 단독 필터
        for topic, cnt in topic_c.most_common(5):
            total_with_topic = sum(1 for r in records if r.get("topic_cluster") == topic)
            if total_with_topic > 0 and cnt / total_with_topic >= 0.7 and cnt >= min_occurrences:
                auto_filters.append(
                    {
                        "type": "topic_risk",
                        "value": topic,
                        "fail_rate": round(cnt / total_with_topic * 100, 1),
                        "reason": f"'{topic}' 토픽 D등급 비율 {cnt}/{total_with_topic} ({cnt / total_with_topic * 100:.0f}%)",
                    }
                )

        return {
            "count": len(losers),
            "risky_combos": risky,
            "auto_filters": auto_filters,
        }

    async def build_weekly_report_payload(self, days: int = 7) -> dict[str, Any]:
        pages = await self.notion_uploader.get_recent_pages(days=days, limit=100)
        records = [self.notion_uploader.extract_page_record(page) for page in pages]

        totals = Counter()
        topic_counter = Counter()
        hook_counter = Counter()
        emotion_counter = Counter()
        draft_counter = Counter()
        grade_counter = Counter()  # P1-B2: 등급 분포
        winners: list[dict[str, Any]] = []
        losers: list[dict[str, Any]] = []

        for record in records:
            totals["total"] += 1
            if record.get("status") == "검토필요":
                totals["review_queue"] += 1
            if record.get("status") == "승인됨":
                totals["approved"] += 1
            if record.get("tweet_url"):
                totals["published"] += 1

            metric_score = (
                float(record.get("views", 0) or 0)
                + float(record.get("likes", 0) or 0) * 2.0
                + float(record.get("retweets", 0) or 0) * 3.0
            )

            topic_counter.update([record.get("topic_cluster", "기타")])
            hook_counter.update([record.get("hook_type", "공감형")])
            emotion_counter.update([record.get("emotion_axis", "공감")])
            draft_counter.update([record.get("chosen_draft_type") or record.get("recommended_draft_type") or "공감형"])
            grade_counter.update([record.get("performance_grade", "-")])

            row = {
                "title": record.get("title", ""),
                "views": record.get("views", 0),
                "likes": record.get("likes", 0),
                "retweets": record.get("retweets", 0),
                "topic_cluster": record.get("topic_cluster", "기타"),
                "hook_type": record.get("hook_type", "공감형"),
                "emotion_axis": record.get("emotion_axis", "공감"),
                "final_rank_score": record.get("final_rank_score", 0),
                "performance_grade": record.get("performance_grade", "-"),
                "score": metric_score,
            }
            if metric_score > 0:
                winners.append(row)
            else:
                losers.append(row)

        winners.sort(key=lambda item: item["score"], reverse=True)
        losers.sort(key=lambda item: item["final_rank_score"] if "final_rank_score" in item else 0)

        # P1-B2: 패턴 분석 통합
        success_patterns = self.analyze_success_patterns(records)
        failure_patterns = self.get_failure_patterns(records)

        return {
            "totals": dict(totals),
            "grade_distribution": dict(grade_counter),
            "top_topics": topic_counter.most_common(5),
            "top_hooks": hook_counter.most_common(5),
            "top_emotions": emotion_counter.most_common(5),
            "top_draft_styles": draft_counter.most_common(5),
            "top_performers": winners[:5],
            "needs_attention": losers[:5],
            "success_patterns": success_patterns,
            "failure_patterns": failure_patterns,
            "records": records,
        }
