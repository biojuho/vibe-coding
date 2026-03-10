"""ML-based viral score predictor for blind-to-x content (Phase 4-1).

Replaces/augments the heuristic `calculate_performance_score()` once enough
labeled training data accumulates in the CostDatabase draft_analytics table.

Activation:
  - MIN_TRAINING_ROWS (default 100) labelled records required in draft_analytics
  - Falls back to heuristic scoring when data is insufficient

Model:
  - Gradient Boosted Trees (sklearn GradientBoostingClassifier)
  - Target: `published` (binary, 0/1)
  - Features: topic_cluster, hook_type, emotion_axis, draft_style (one-hot) +
              final_rank_score as numeric feature
  - Output: predicted publish probability → scaled to 0–100

Persistence:
  - Model is saved to `.tmp/ml_scorer.pkl` after training
  - Re-trained when new data has grown by ≥ RETRAIN_THRESHOLD rows
  - Thread-safe via file-lock pattern

Usage:
    scorer = MLScorer()
    score, meta = scorer.predict_score(topic_cluster, hook_type, emotion_axis, draft_style)
    # Returns (float 0-100, {"method": "ml"|"heuristic", ...})
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

try:
    import joblib as _joblib
    _HAS_JOBLIB = True
except ImportError:
    import pickle as _pickle  # type: ignore[no-redef]
    _HAS_JOBLIB = False

logger = logging.getLogger(__name__)

_BTX_ROOT = Path(__file__).resolve().parent.parent
_MODEL_PATH = _BTX_ROOT / ".tmp" / "ml_scorer.joblib"
_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

# 하위 호환: 구 pickle 경로 (마이그레이션용)
_LEGACY_PKL_PATH = _BTX_ROOT / ".tmp" / "ml_scorer.pkl"

# 스키마 버전 — feature_names 구조가 변경될 때 증가
_SCHEMA_VERSION = 2

MIN_TRAINING_ROWS = int(os.environ.get("BTX_ML_MIN_ROWS", "100"))
RETRAIN_THRESHOLD = int(os.environ.get("BTX_ML_RETRAIN_ROWS", "20"))


def _load_training_data() -> tuple[list[dict], int]:
    """Load draft_analytics rows from CostDatabase. Returns (rows, total_count)."""
    try:
        from pipeline.cost_db import CostDatabase
        db = CostDatabase()
        with db._conn() as conn:
            rows = conn.execute(
                """SELECT topic_cluster, hook_type, emotion_axis, draft_style,
                          provider_used, final_rank_score, published,
                          yt_views, engagement_rate
                   FROM draft_analytics
                   WHERE topic_cluster != ''
                   ORDER BY recorded_at DESC"""
            ).fetchall()
        data = [dict(r) for r in rows]
        return data, len(data)
    except Exception as exc:
        logger.warning("MLScorer: failed to load training data: %s", exc)
        return [], 0


def _build_feature_matrix(rows: list[dict], use_views: bool = False):
    """Convert rows to (X, y) for sklearn. Returns (X_list, y_list, feature_names, cat_sorted).

    Args:
        use_views: If True, use log(yt_views + 1) as continuous target instead of binary `published`.
    """
    import math

    # Categorical columns to one-hot encode
    cat_cols = ["topic_cluster", "hook_type", "emotion_axis", "draft_style"]

    # Collect unique values per category
    cat_values: dict[str, set] = {c: set() for c in cat_cols}
    for row in rows:
        for col in cat_cols:
            val = row.get(col) or "unknown"
            cat_values[col].add(val)

    # Sort for determinism
    cat_sorted: dict[str, list] = {c: sorted(v) for c, v in cat_values.items()}

    X, y = [], []
    feature_names: list[str] = []
    # Build feature_names once
    for col in cat_cols:
        for val in cat_sorted[col]:
            feature_names.append(f"{col}={val}")
    feature_names.append("final_rank_score")

    for row in rows:
        vec = []
        for col in cat_cols:
            val = row.get(col) or "unknown"
            for v in cat_sorted[col]:
                vec.append(1 if val == v else 0)
        vec.append(float(row.get("final_rank_score") or 0.0))
        X.append(vec)
        if use_views:
            y.append(math.log1p(float(row.get("yt_views") or 0.0)))
        else:
            y.append(int(row.get("published") or 0))

    return X, y, feature_names, cat_sorted


class _ModelBundle:
    """Holds a trained sklearn model + encoding metadata + schema version."""

    def __init__(
        self,
        model,
        cat_sorted: dict,
        feature_names: list,
        training_rows: int,
        target_type: str = "binary",
        schema_version: int = _SCHEMA_VERSION,
    ):
        self.model = model
        self.cat_sorted = cat_sorted
        self.feature_names = feature_names
        self.training_rows = training_rows
        self.target_type = target_type  # "binary" or "continuous"
        self.schema_version = schema_version  # 구조 변경 감지용

    def _build_vec(
        self,
        topic_cluster: str,
        hook_type: str,
        emotion_axis: str,
        draft_style: str,
        final_rank_score: float = 0.0,
    ) -> list:
        cat_cols = ["topic_cluster", "hook_type", "emotion_axis", "draft_style"]
        inputs = {
            "topic_cluster": topic_cluster or "unknown",
            "hook_type": hook_type or "unknown",
            "emotion_axis": emotion_axis or "unknown",
            "draft_style": draft_style or "unknown",
        }
        vec = []
        for col in cat_cols:
            val = inputs[col]
            for v in self.cat_sorted.get(col, []):
                vec.append(1 if val == v else 0)
        vec.append(float(final_rank_score))
        return vec

    def predict_raw(
        self,
        topic_cluster: str,
        hook_type: str,
        emotion_axis: str,
        draft_style: str,
        final_rank_score: float = 0.0,
    ) -> float:
        """Return raw model output: publish proba (binary) or log-views (continuous)."""
        vec = self._build_vec(topic_cluster, hook_type, emotion_axis, draft_style, final_rank_score)
        target_type = getattr(self, "target_type", "binary")
        if target_type == "continuous":
            return float(self.model.predict([vec])[0])
        proba = self.model.predict_proba([vec])[0]
        return float(proba[1]) if len(proba) > 1 else float(proba[0])

    # Backward-compatibility alias
    def predict_proba(
        self,
        topic_cluster: str,
        hook_type: str,
        emotion_axis: str,
        draft_style: str,
        final_rank_score: float = 0.0,
    ) -> float:
        return self.predict_raw(topic_cluster, hook_type, emotion_axis, draft_style, final_rank_score)


class MLScorer:
    """Thread-safe ML-based content publish-probability scorer.

    Falls back to returning None when insufficient data or sklearn unavailable.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._bundle: _ModelBundle | None = None
        self._last_row_count: int = 0
        self._load_or_train()

    def _load_or_train(self) -> None:
        """Load persisted model or train fresh if enough data.

        Phase 3-B: joblib 우선 사용. 구 pickle 파일은 무시하고 재학습.
        schema_version 불일치 시 재학습 트리거.
        """
        with self._lock:
            # 구 pickle 파일 존재 시 삭제 (보안 위험 제거)
            if _LEGACY_PKL_PATH.exists():
                try:
                    _LEGACY_PKL_PATH.unlink()
                    logger.info("MLScorer: 구 pickle 모델 삭제 (보안, joblib로 재학습)")
                except Exception:
                    pass

            if _MODEL_PATH.exists():
                try:
                    bundle = _joblib.load(_MODEL_PATH) if _HAS_JOBLIB else None
                    if bundle is None:
                        raise RuntimeError("joblib 미설치, 재학습")
                    # schema_version 검증
                    if getattr(bundle, "schema_version", 0) != _SCHEMA_VERSION:
                        raise ValueError(
                            f"Schema version mismatch: "
                            f"saved={getattr(bundle, 'schema_version', 0)}, "
                            f"expected={_SCHEMA_VERSION}"
                        )
                    self._bundle = bundle
                    self._last_row_count = bundle.training_rows
                    logger.info(
                        "MLScorer: loaded model (trained on %d rows, schema_v%d)",
                        bundle.training_rows, bundle.schema_version,
                    )
                    _, current_count = _load_training_data()
                    if current_count - self._last_row_count >= RETRAIN_THRESHOLD:
                        logger.info("MLScorer: new data available → retraining")
                        self._train()
                    return
                except Exception as exc:
                    logger.warning("MLScorer: failed to load saved model, retraining: %s", exc)

            self._train()

    def _train(self) -> None:
        """Train model from draft_analytics. Must be called inside _lock."""
        rows, count = _load_training_data()
        if count < MIN_TRAINING_ROWS:
            logger.info(
                "MLScorer: not enough data (%d/%d rows). Using heuristic fallback.",
                count, MIN_TRAINING_ROWS,
            )
            self._bundle = None
            return

        try:
            from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
        except ImportError:
            logger.warning("MLScorer: scikit-learn not installed. Heuristic fallback active.")
            self._bundle = None
            return

        try:
            # Phase 5: continuous target when ≥15% of rows have YouTube view data
            views_count = sum(1 for r in rows if float(r.get("yt_views") or 0) > 0)
            use_views = views_count >= max(10, int(count * 0.15))
            target_type = "continuous" if use_views else "binary"
            logger.info(
                "MLScorer: target=%s (yt_views rows: %d/%d)",
                target_type, views_count, count,
            )

            X, y, feature_names, cat_sorted = _build_feature_matrix(rows, use_views=use_views)

            if target_type == "continuous":
                model = GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.1,
                    random_state=42,
                )
            else:
                model = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.1,
                    random_state=42,
                )
            model.fit(X, y)

            bundle = _ModelBundle(
                model, cat_sorted, feature_names,
                training_rows=count, target_type=target_type,
                schema_version=_SCHEMA_VERSION,
            )
            self._bundle = bundle
            self._last_row_count = count

            # Phase 3-B: joblib로 안전 저장 (pickle 대체)
            try:
                if _HAS_JOBLIB:
                    _joblib.dump(bundle, _MODEL_PATH)
                    logger.info(
                        "MLScorer: model saved via joblib (%d rows, %d features, target=%s, schema_v%d)",
                        count, len(feature_names), target_type, _SCHEMA_VERSION,
                    )
                else:
                    logger.warning("MLScorer: joblib 미설치, 모델 저장 건너뜀 (pip install joblib)")
            except Exception as exc:
                logger.warning("MLScorer: failed to save model: %s", exc)

        except Exception as exc:
            logger.error("MLScorer: training failed: %s", exc)
            self._bundle = None

    def predict_score(
        self,
        topic_cluster: str,
        hook_type: str,
        emotion_axis: str,
        draft_style: str,
        final_rank_score: float = 0.0,
    ) -> tuple[float, dict[str, Any]]:
        """Return (score 0–100, metadata dict).

        Returns (None, {"method": "heuristic"}) when ML model not available.
        Caller should fall back to calculate_performance_score() in that case.
        """
        if self._bundle is None:
            _, current_count = _load_training_data()
            return 0.0, {
                "method": "heuristic",
                "reason": f"insufficient_data ({current_count}/{MIN_TRAINING_ROWS})",
            }

        try:
            raw = self._bundle.predict_raw(
                topic_cluster=topic_cluster,
                hook_type=hook_type,
                emotion_axis=emotion_axis,
                draft_style=draft_style,
                final_rank_score=final_rank_score,
            )
            target_type = getattr(self._bundle, "target_type", "binary")
            if target_type == "continuous":
                # Scale log-views to 0-100: log(50000) ≈ 10.82 as practical ceiling
                _LOG_VIEWS_MAX = 10.82
                score = round(min(100.0, max(0.0, raw / _LOG_VIEWS_MAX * 100)), 1)
            else:
                score = round(raw * 100, 1)
            return score, {
                "method": "ml",
                "target_type": target_type,
                "trained_on": self._bundle.training_rows,
                "raw_prediction": round(raw, 4),
            }
        except Exception as exc:
            logger.warning("MLScorer.predict_score() failed: %s", exc)
            return 0.0, {"method": "heuristic", "reason": f"prediction_error: {exc}"}

    def is_active(self) -> bool:
        """Returns True if ML model is loaded and ready."""
        return self._bundle is not None

    def retrain_if_needed(self) -> bool:
        """Trigger retrain if enough new rows since last training. Returns True if retrained."""
        _, current_count = _load_training_data()
        if current_count - self._last_row_count >= RETRAIN_THRESHOLD:
            with self._lock:
                self._train()
            return True
        return False


# Module-level singleton (lazy-initialized per process)
_scorer: MLScorer | None = None
_scorer_lock = threading.Lock()


def get_ml_scorer() -> MLScorer:
    """Return the module-level MLScorer singleton (thread-safe lazy init)."""
    global _scorer
    if _scorer is None:
        with _scorer_lock:
            if _scorer is None:
                _scorer = MLScorer()
    return _scorer
