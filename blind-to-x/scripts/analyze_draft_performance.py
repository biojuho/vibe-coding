"""드래프트 A/B 성과 분석 + 자동 스타일 선택 스크립트 (Phase 4-2 / Phase 5B).

draft_analytics 테이블의 누적 데이터를 분석해 어느 draft_style이
가장 높은 발행률(published rate)과 랭크 점수를 보이는지 확인하고,
config.yaml의 `content_strategy.preferred_draft_style`을 자동 업데이트합니다.

Phase 5B: 토픽x스타일x감정 크로스 분석 + classification_rules.yaml weight 업데이트.

사용법:
    python scripts/analyze_draft_performance.py [--dry-run] [--min-samples N] [--top-k N]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_BTX_ROOT = Path(__file__).resolve().parent.parent


def _load_analytics(min_samples: int = 10) -> list[dict]:
    """draft_analytics 테이블에서 데이터 로드."""
    try:
        sys.path.insert(0, str(_BTX_ROOT))
        from pipeline.cost_db import CostDatabase
        db = CostDatabase()
        with db._conn() as conn:
            rows = conn.execute(
                """SELECT draft_style, topic_cluster, hook_type, emotion_axis,
                          provider_used, final_rank_score, published, date
                   FROM draft_analytics
                   WHERE draft_style != ''
                   ORDER BY recorded_at DESC"""
            ).fetchall()
        data = [dict(r) for r in rows]
        logger.info("draft_analytics 로드: %d건", len(data))
        return data
    except Exception as exc:
        logger.error("데이터 로드 실패: %s", exc)
        return []


def _compute_style_stats(data: list[dict], min_samples: int = 5) -> list[dict]:
    """스타일별 통계 계산."""
    from collections import defaultdict

    stats: dict[str, dict] = defaultdict(lambda: {
        "style": "",
        "count": 0,
        "published": 0,
        "rank_sum": 0.0,
        "topics": defaultdict(int),
        "emotions": defaultdict(int),
    })

    for row in data:
        style = row.get("draft_style") or "unknown"
        s = stats[style]
        s["style"] = style
        s["count"] += 1
        s["published"] += int(row.get("published") or 0)
        s["rank_sum"] += float(row.get("final_rank_score") or 0)
        topic = row.get("topic_cluster") or "기타"
        emotion = row.get("emotion_axis") or "공감"
        s["topics"][topic] += 1
        s["emotions"][emotion] += 1

    results = []
    for style, s in stats.items():
        if s["count"] < min_samples:
            logger.info("스타일 '%s': 샘플 부족 (%d < %d), 제외", style, s["count"], min_samples)
            continue
        publish_rate = s["published"] / s["count"]
        avg_rank = s["rank_sum"] / s["count"]
        # 복합 점수: 60% 발행률 + 40% 평균 랭크(0~100 스케일)
        composite = publish_rate * 60 + (avg_rank / 100) * 40

        top_topic = max(s["topics"], key=s["topics"].__getitem__) if s["topics"] else "?"
        top_emotion = max(s["emotions"], key=s["emotions"].__getitem__) if s["emotions"] else "?"

        results.append({
            "style": style,
            "count": s["count"],
            "published": s["published"],
            "publish_rate": round(publish_rate, 4),
            "avg_rank": round(avg_rank, 2),
            "composite_score": round(composite, 2),
            "top_topic": top_topic,
            "top_emotion": top_emotion,
        })

    results.sort(key=lambda x: x["composite_score"], reverse=True)
    return results


def _print_report(stats: list[dict]) -> None:
    """통계 리포트 출력."""
    if not stats:
        logger.info("분석할 데이터가 없습니다.")
        return

    header = f"{'Style':<18} {'Count':>6} {'Published':>10} {'Pub.Rate':>9} {'AvgRank':>8} {'Composite':>10} {'TopTopic':<12} {'TopEmotion'}"
    print("\n" + "=" * len(header))
    print("드래프트 스타일 A/B 성과 분석")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for s in stats:
        print(
            f"{s['style']:<18} "
            f"{s['count']:>6} "
            f"{s['published']:>10} "
            f"{s['publish_rate']:>8.1%} "
            f"{s['avg_rank']:>8.1f} "
            f"{s['composite_score']:>10.2f} "
            f"{s['top_topic']:<12} "
            f"{s['top_emotion']}"
        )

    print("=" * len(header))
    winner = stats[0]
    print(f"\n✅ 최적 스타일: '{winner['style']}' "
          f"(복합점수 {winner['composite_score']}, 발행률 {winner['publish_rate']:.1%}, "
          f"평균랭크 {winner['avg_rank']})")


def _update_config(best_style: str, config_path: Path) -> bool:
    """config.yaml의 content_strategy.preferred_draft_style 업데이트."""
    if not config_path.exists():
        logger.warning("config.yaml 없음: %s", config_path)
        return False

    try:
        import yaml
        with config_path.open(encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        current = (config.get("content_strategy") or {}).get("preferred_draft_style", "")
        if current == best_style:
            logger.info("preferred_draft_style 이미 '%s'로 설정됨. 변경 불필요.", best_style)
            return False

        config.setdefault("content_strategy", {})["preferred_draft_style"] = best_style

        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        logger.info(
            "config.yaml 업데이트: preferred_draft_style '%s' → '%s'",
            current or "(없음)", best_style,
        )
        return True
    except Exception as exc:
        logger.error("config.yaml 업데이트 실패: %s", exc)
        return False


def _compute_topic_cross_stats(data: list[dict], min_samples: int = 3) -> list[dict]:
    """토픽x스타일 크로스 분석: 토픽별 최고 성과 스타일 반환."""
    from collections import defaultdict

    cross: dict[tuple, dict] = defaultdict(lambda: {"count": 0, "rank_sum": 0.0, "published": 0})
    for row in data:
        topic = row.get("topic_cluster") or "기타"
        style = row.get("draft_style") or "unknown"
        key = (topic, style)
        cross[key]["count"] += 1
        cross[key]["rank_sum"] += float(row.get("final_rank_score") or 0)
        cross[key]["published"] += int(row.get("published") or 0)

    # 토픽별로 최고 성과 스타일 선택
    topic_best: dict[str, dict] = {}
    for (topic, style), stats in cross.items():
        if stats["count"] < min_samples:
            continue
        avg_rank = stats["rank_sum"] / stats["count"]
        pub_rate = stats["published"] / stats["count"]
        composite = pub_rate * 60 + (avg_rank / 100) * 40
        if topic not in topic_best or composite > topic_best[topic]["composite"]:
            topic_best[topic] = {
                "topic": topic,
                "best_style": style,
                "composite": round(composite, 2),
                "avg_rank": round(avg_rank, 2),
                "pub_rate": round(pub_rate, 4),
                "count": stats["count"],
            }

    return sorted(topic_best.values(), key=lambda x: x["composite"], reverse=True)


def _print_cross_report(cross_stats: list[dict]) -> None:
    """토픽x스타일 크로스 분석 출력."""
    if not cross_stats:
        return
    print("\n[토픽별 최고 성과 스타일]")
    header = f"{'Topic':<14} {'BestStyle':<18} {'Count':>6} {'PubRate':>8} {'AvgRank':>8} {'Score':>8}"
    print(header)
    print("-" * len(header))
    for s in cross_stats:
        print(
            f"{s['topic']:<14} {s['best_style']:<18} "
            f"{s['count']:>6} {s['pub_rate']:>7.1%} "
            f"{s['avg_rank']:>8.1f} {s['composite']:>8.2f}"
        )


def _update_classification_weights(
    cross_stats: list[dict],
    rules_path: Path,
) -> bool:
    """topic_rules에 performance_weight 필드 업데이트.

    성과 점수(composite)를 0.5~1.5 범위로 정규화해 weight로 기록.
    content_intelligence.py에서 이 weight를 활용해 토픽 분류 우선순위를 조정할 수 있습니다.
    """
    if not cross_stats or not rules_path.exists():
        return False
    try:
        import yaml

        with rules_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        topic_rules = data.get("topic_rules", [])
        if not topic_rules:
            return False

        # composite score → weight (0.5 ~ 1.5 범위 정규화)
        scores = [s["composite"] for s in cross_stats]
        if not scores:
            return False
        score_min, score_max = min(scores), max(scores)
        score_range = score_max - score_min or 1.0
        topic_weight_map = {
            s["topic"]: round(0.5 + (s["composite"] - score_min) / score_range, 3)
            for s in cross_stats
        }

        changed = False
        for rule in topic_rules:
            label = rule.get("label", "")
            if label in topic_weight_map:
                new_weight = topic_weight_map[label]
                if rule.get("performance_weight") != new_weight:
                    rule["performance_weight"] = new_weight
                    changed = True

        if not changed:
            logger.info("classification_rules.yaml weight 변경 없음.")
            return False

        # 헤더 주석 보존
        original_lines = rules_path.read_text(encoding="utf-8").splitlines(keepends=True)
        header_lines = [line for line in original_lines if line.startswith("#")]
        body = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
        rules_path.write_text("".join(header_lines) + body, encoding="utf-8")
        logger.info("classification_rules.yaml performance_weight 업데이트 완료 (%d 토픽)", len(topic_weight_map))
        return True
    except Exception as exc:
        logger.error("classification_rules.yaml 업데이트 실패: %s", exc)
        return False


def _record_ml_retrain() -> None:
    """데이터 변화 시 ML 모델 재훈련 트리거."""
    try:
        sys.path.insert(0, str(_BTX_ROOT))
        from pipeline.ml_scorer import get_ml_scorer
        scorer = get_ml_scorer()
        retrained = scorer.retrain_if_needed()
        if retrained:
            logger.info("ML 모델 재훈련 완료.")
        else:
            logger.info("ML 모델 재훈련 불필요 (충분한 새 데이터 미확보).")
    except Exception as exc:
        logger.debug("ML 재훈련 트리거 실패 (무시): %s", exc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="드래프트 A/B 성과 분석")
    parser.add_argument("--dry-run", action="store_true", help="config 미수정, 분석만 출력")
    parser.add_argument("--min-samples", type=int, default=5, help="최소 샘플 수 (기본 5)")
    parser.add_argument("--top-k", type=int, default=3, help="상위 K 스타일 출력 (기본 3)")
    parser.add_argument("--config", default=str(_BTX_ROOT / "config.yaml"), help="config.yaml 경로")
    args = parser.parse_args(argv)

    data = _load_analytics()
    if not data:
        logger.warning("데이터 없음. draft_analytics 테이블을 먼저 채우세요.")
        return 0

    stats = _compute_style_stats(data, min_samples=args.min_samples)
    if not stats:
        logger.warning("최소 샘플(%d)을 만족하는 스타일이 없습니다.", args.min_samples)
        return 0

    _print_report(stats[:args.top_k])

    # Phase 5B: 토픽x스타일 크로스 분석
    cross_stats = _compute_topic_cross_stats(data, min_samples=max(2, args.min_samples // 2))
    _print_cross_report(cross_stats)

    if args.dry_run:
        logger.info("[dry-run] config.yaml / classification_rules.yaml 미수정.")
        return 0

    # 최적 스타일로 config 업데이트
    best = stats[0]["style"]
    _update_config(best, Path(args.config))

    # Phase 5B: classification_rules.yaml performance_weight 업데이트
    rules_path = Path(args.config).parent / "classification_rules.yaml"
    _update_classification_weights(cross_stats, rules_path)

    # ML 모델 재훈련 시도
    _record_ml_retrain()

    return 0


if __name__ == "__main__":
    sys.exit(main())
