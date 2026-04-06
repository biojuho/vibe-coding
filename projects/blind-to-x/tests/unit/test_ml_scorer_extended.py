"""Extended tests for pipeline.ml_scorer — _build_feature_matrix, _ModelBundle, MLScorer."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.ml_scorer import (
    MLScorer,
    _ModelBundle,
    _build_feature_matrix,
    _load_training_data,
)


# ── _build_feature_matrix ────────────────────────────────────────────


class TestBuildFeatureMatrix:
    def _sample_rows(self, n=5, published=1, yt_views=0):
        return [
            {
                "topic_cluster": "경제" if i % 2 == 0 else "IT",
                "hook_type": "공감형",
                "emotion_axis": "분노" if i % 3 == 0 else "공감",
                "draft_style": "공감형",
                "final_rank_score": 50 + i * 10,
                "published": published,
                "yt_views": yt_views + i * 100,
                "engagement_rate": 2.5,
            }
            for i in range(n)
        ]

    def test_basic_matrix(self):
        rows = self._sample_rows(3)
        X, y, feature_names, cat_sorted = _build_feature_matrix(rows)
        assert len(X) == 3
        assert len(y) == 3
        assert "final_rank_score" in feature_names
        assert len(X[0]) == len(feature_names)

    def test_binary_target(self):
        rows = self._sample_rows(3, published=1)
        _, y, _, _ = _build_feature_matrix(rows, use_views=False)
        assert all(v in (0, 1) for v in y)

    def test_continuous_target(self):
        rows = self._sample_rows(3, yt_views=100)
        _, y, _, _ = _build_feature_matrix(rows, use_views=True)
        assert all(v >= 0 for v in y)  # log(views+1) >= 0

    def test_missing_values_handled(self):
        rows = [
            {
                "topic_cluster": "",
                "hook_type": None,
                "emotion_axis": "공감",
                "draft_style": "공감형",
                "final_rank_score": "N/A",
                "published": None,
                "yt_views": None,
            }
        ]
        X, y, feature_names, cat_sorted = _build_feature_matrix(rows)
        assert len(X) == 1
        assert X[0][-1] == 0.0  # "N/A" -> 0.0
        assert y[0] == 0  # None -> 0

    def test_one_hot_encoding(self):
        rows = [
            {
                "topic_cluster": "경제",
                "hook_type": "공감형",
                "emotion_axis": "분노",
                "draft_style": "공감형",
                "final_rank_score": 80,
                "published": 1,
            },
            {
                "topic_cluster": "IT",
                "hook_type": "논쟁형",
                "emotion_axis": "공감",
                "draft_style": "정보전달형",
                "final_rank_score": 60,
                "published": 0,
            },
        ]
        X, y, feature_names, cat_sorted = _build_feature_matrix(rows)
        # Each categorical should have its unique values as one-hot features
        assert "topic_cluster=경제" in feature_names
        assert "topic_cluster=IT" in feature_names
        assert len(X[0]) == len(feature_names)


# ── _ModelBundle ─────────────────────────────────────────────────────


class TestModelBundle:
    def _make_bundle(self):
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.3, 0.7]]
        mock_model.predict.return_value = [5.0]

        return _ModelBundle(
            model=mock_model,
            cat_sorted={
                "topic_cluster": ["IT", "경제"],
                "hook_type": ["공감형"],
                "emotion_axis": ["공감"],
                "draft_style": ["공감형"],
            },
            feature_names=[
                "topic_cluster=IT",
                "topic_cluster=경제",
                "hook_type=공감형",
                "emotion_axis=공감",
                "draft_style=공감형",
                "final_rank_score",
            ],
            training_rows=50,
            target_type="binary",
        )

    def test_build_vec(self):
        bundle = self._make_bundle()
        vec = bundle._build_vec("경제", "공감형", "공감", "공감형", 85.0)
        assert len(vec) == 6  # 2 + 1 + 1 + 1 + final_rank_score
        assert vec[-1] == 85.0

    def test_build_vec_unknown_category(self):
        bundle = self._make_bundle()
        vec = bundle._build_vec("새토픽", "공감형", "공감", "공감형", 50.0)
        # "새토픽" not in cat_sorted -> all topic_cluster features are 0
        assert vec[0] == 0
        assert vec[1] == 0

    def test_predict_raw_binary(self):
        bundle = self._make_bundle()
        score = bundle.predict_raw("경제", "공감형", "공감", "공감형", 80.0)
        assert score == pytest.approx(0.7)  # second class probability

    def test_predict_raw_continuous(self):
        bundle = self._make_bundle()
        bundle.target_type = "continuous"
        score = bundle.predict_raw("경제", "공감형", "공감", "공감형", 80.0)
        assert score == pytest.approx(5.0)

    def test_predict_proba_alias(self):
        bundle = self._make_bundle()
        score = bundle.predict_proba("경제", "공감형", "공감", "공감형", 80.0)
        assert score == bundle.predict_raw("경제", "공감형", "공감", "공감형", 80.0)


# ── MLScorer ─────────────────────────────────────────────────────────


class TestMLScorer:
    def test_predict_score_no_model(self):
        """Without trained model, returns heuristic fallback."""
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 5

        score, meta = scorer.predict_score("경제", "공감형", "분노", "공감형")
        assert score == 0.0
        assert meta["method"] == "heuristic"
        assert "insufficient_data" in meta["reason"]

    def test_predict_score_with_model(self):
        """With a model, returns ML prediction."""
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._heuristic_row_count = 100

        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.2, 0.8]]

        scorer._bundle = _ModelBundle(
            model=mock_model,
            cat_sorted={
                "topic_cluster": ["경제"],
                "hook_type": ["공감형"],
                "emotion_axis": ["분노"],
                "draft_style": ["공감형"],
            },
            feature_names=[
                "topic_cluster=경제",
                "hook_type=공감형",
                "emotion_axis=분노",
                "draft_style=공감형",
                "final_rank_score",
            ],
            training_rows=100,
            target_type="binary",
            model_tier="gradient",
        )
        scorer._last_row_count = 100

        score, meta = scorer.predict_score("경제", "공감형", "분노", "공감형", 85.0)
        assert score == pytest.approx(80.0, abs=0.5)
        assert meta["method"] == "ml"
        assert meta["model_tier"] == "gradient"

    def test_predict_score_continuous(self):
        """Continuous target returns scaled score."""
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._heuristic_row_count = 100

        mock_model = MagicMock()
        mock_model.predict.return_value = [5.0]  # log-views

        scorer._bundle = _ModelBundle(
            model=mock_model,
            cat_sorted={
                "topic_cluster": ["경제"],
                "hook_type": ["공감형"],
                "emotion_axis": ["분노"],
                "draft_style": ["공감형"],
            },
            feature_names=[
                "topic_cluster=경제",
                "hook_type=공감형",
                "emotion_axis=분노",
                "draft_style=공감형",
                "final_rank_score",
            ],
            training_rows=100,
            target_type="continuous",
            model_tier="gradient",
        )
        scorer._last_row_count = 100

        score, meta = scorer.predict_score("경제", "공감형", "분노", "공감형", 85.0)
        assert 0 <= score <= 100
        assert meta["target_type"] == "continuous"

    def test_predict_score_exception(self):
        """Model prediction exception -> heuristic fallback."""
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._heuristic_row_count = 100

        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = RuntimeError("prediction crash")

        scorer._bundle = _ModelBundle(
            model=mock_model,
            cat_sorted={
                "topic_cluster": ["경제"],
                "hook_type": ["공감형"],
                "emotion_axis": ["분노"],
                "draft_style": ["공감형"],
            },
            feature_names=[
                "topic_cluster=경제",
                "hook_type=공감형",
                "emotion_axis=분노",
                "draft_style=공감형",
                "final_rank_score",
            ],
            training_rows=100,
        )
        scorer._last_row_count = 100

        score, meta = scorer.predict_score("경제", "공감형", "분노", "공감형")
        assert score == 0.0
        assert meta["method"] == "heuristic"
        assert "prediction_error" in meta["reason"]

    def test_is_active(self):
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        assert scorer.is_active() is False

        scorer._bundle = MagicMock()
        assert scorer.is_active() is True

    def test_retrain_if_needed_no_new_data(self):
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 100
        scorer._heuristic_row_count = 100

        with patch("pipeline.ml_scorer._load_training_data", return_value=([], 100)):
            result = scorer.retrain_if_needed()
            assert result is False

    def test_retrain_if_needed_enough_new_data(self):
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 80
        scorer._heuristic_row_count = 80

        with patch("pipeline.ml_scorer._load_training_data", return_value=([], 105)):
            with patch.object(scorer, "_train"):
                result = scorer.retrain_if_needed()
                assert result is True


# ── _load_training_data ──────────────────────────────────────────────


class TestLoadTrainingData:
    def test_db_exception(self):
        """DB failure returns empty."""
        with patch("pipeline.cost_db.CostDatabase", side_effect=Exception("no DB")):
            rows, count = _load_training_data()
            assert rows == []
            assert count == 0


# ── MLScorer._train ──────────────────────────────────────────────────


_has_sklearn = False
try:
    import sklearn  # noqa: F401

    _has_sklearn = True
except ImportError:
    pass

_skip_no_sklearn = pytest.mark.skipif(not _has_sklearn, reason="scikit-learn not installed")


class TestMLScorerTrain:
    def _sample_rows(self, n=25, with_views=False):
        return [
            {
                "topic_cluster": "경제" if i % 2 == 0 else "IT",
                "hook_type": "공감형" if i % 3 == 0 else "논쟁형",
                "emotion_axis": "분노" if i % 2 == 0 else "공감",
                "draft_style": "공감형",
                "provider_used": "gemini",
                "final_rank_score": 50 + i * 2,
                "published": 1 if i % 2 == 0 else 0,
                "yt_views": (i * 500 if with_views else 0),
                "engagement_rate": 2.5,
            }
            for i in range(n)
        ]

    def test_train_insufficient_data(self):
        """Less than MIN_LOGISTIC_ROWS -> heuristic fallback."""
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 0

        with patch("pipeline.ml_scorer._load_training_data", return_value=([], 5)):
            scorer._train()
            assert scorer._bundle is None
            assert scorer._heuristic_row_count == 5

    @_skip_no_sklearn
    def test_train_logistic_tier(self):
        """20-99 rows -> LogisticRegression tier."""
        rows = self._sample_rows(30)
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 0

        with (
            patch("pipeline.ml_scorer._load_training_data", return_value=(rows, 30)),
            patch("pipeline.ml_scorer._MODEL_PATH") as mock_path,
            patch("pipeline.ml_scorer._HAS_JOBLIB", False),
        ):
            mock_path.exists.return_value = False
            scorer._train()
            assert scorer._bundle is not None
            assert scorer._bundle.model_tier == "logistic"
            assert scorer._bundle.training_rows == 30

    @_skip_no_sklearn
    def test_train_gradient_tier(self):
        """100+ rows -> GradientBoosting tier."""
        rows = self._sample_rows(110)
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 0

        with (
            patch("pipeline.ml_scorer._load_training_data", return_value=(rows, 110)),
            patch("pipeline.ml_scorer._MODEL_PATH") as mock_path,
            patch("pipeline.ml_scorer._HAS_JOBLIB", False),
        ):
            mock_path.exists.return_value = False
            scorer._train()
            assert scorer._bundle is not None
            assert scorer._bundle.model_tier == "gradient"
            assert scorer._bundle.training_rows == 110

    @_skip_no_sklearn
    def test_train_gradient_with_views(self):
        """Gradient tier with enough yt_views -> continuous target."""
        rows = self._sample_rows(110, with_views=True)
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 0

        with (
            patch("pipeline.ml_scorer._load_training_data", return_value=(rows, 110)),
            patch("pipeline.ml_scorer._MODEL_PATH") as mock_path,
            patch("pipeline.ml_scorer._HAS_JOBLIB", False),
        ):
            mock_path.exists.return_value = False
            scorer._train()
            assert scorer._bundle is not None
            assert scorer._bundle.target_type == "continuous"

    def test_train_sklearn_not_installed(self):
        """sklearn ImportError -> heuristic fallback."""
        rows = self._sample_rows(30)
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 0

        with (
            patch("pipeline.ml_scorer._load_training_data", return_value=(rows, 30)),
            patch.dict("sys.modules", {"sklearn": None, "sklearn.linear_model": None}),
        ):
            scorer._train()
            assert scorer._bundle is None

    @_skip_no_sklearn
    def test_train_with_joblib_save(self):
        """Model saved via joblib when available."""
        rows = self._sample_rows(30)
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 0

        with (
            patch("pipeline.ml_scorer._load_training_data", return_value=(rows, 30)),
            patch("pipeline.ml_scorer._HAS_JOBLIB", True),
            patch("pipeline.ml_scorer._joblib") as mock_joblib,
            patch("pipeline.ml_scorer._MODEL_PATH") as mock_path,
        ):
            mock_path.exists.return_value = False
            scorer._train()
            assert scorer._bundle is not None
            mock_joblib.dump.assert_called_once()


# ── MLScorer._load_or_train ──────────────────────────────────────────


class TestMLScorerLoadOrTrain:
    def test_load_or_train_no_saved_model(self):
        """No saved model -> trains fresh."""
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 0

        with (
            patch("pipeline.ml_scorer._MODEL_PATH") as mock_path,
            patch("pipeline.ml_scorer._LEGACY_PKL_PATH") as mock_legacy,
            patch("pipeline.ml_scorer._load_training_data", return_value=([], 0)),
        ):
            mock_path.exists.return_value = False
            mock_legacy.exists.return_value = False
            scorer._load_or_train()
            assert scorer._bundle is None  # insufficient data

    def test_load_or_train_legacy_pkl_deleted(self):
        """Legacy pickle file is deleted when found."""
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 0

        with (
            patch("pipeline.ml_scorer._MODEL_PATH") as mock_path,
            patch("pipeline.ml_scorer._LEGACY_PKL_PATH") as mock_legacy,
            patch("pipeline.ml_scorer._load_training_data", return_value=([], 0)),
        ):
            mock_path.exists.return_value = False
            mock_legacy.exists.return_value = True
            scorer._load_or_train()
            mock_legacy.unlink.assert_called_once()

    def test_load_or_train_schema_mismatch_retrains(self):
        """Schema version mismatch in saved model -> retrain."""
        scorer = MLScorer.__new__(MLScorer)
        scorer._lock = __import__("threading").Lock()
        scorer._bundle = None
        scorer._last_row_count = 0
        scorer._heuristic_row_count = 0

        old_bundle = MagicMock()
        old_bundle.schema_version = 0  # old version
        old_bundle.training_rows = 50

        with (
            patch("pipeline.ml_scorer._MODEL_PATH") as mock_path,
            patch("pipeline.ml_scorer._LEGACY_PKL_PATH") as mock_legacy,
            patch("pipeline.ml_scorer._HAS_JOBLIB", True),
            patch("pipeline.ml_scorer._joblib") as mock_joblib,
            patch("pipeline.ml_scorer._load_training_data", return_value=([], 0)),
        ):
            mock_path.exists.return_value = True
            mock_legacy.exists.return_value = False
            mock_joblib.load.return_value = old_bundle
            scorer._load_or_train()
            # Should have called _train after schema mismatch
            assert scorer._bundle is None  # retrained with 0 data -> heuristic
