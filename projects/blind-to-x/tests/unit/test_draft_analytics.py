"""Tests for pipeline.draft_analytics — record_draft_event, refresh_ml_scorer_if_needed."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestRecordDraftEvent:
    def test_successful_record(self):
        from pipeline.draft_analytics import record_draft_event

        mock_db = MagicMock()
        with patch("pipeline.cost_db.CostDatabase", return_value=mock_db):
            record_draft_event(
                source="blind",
                topic_cluster="연봉",
                hook_type="question",
                emotion_axis="분노",
                draft_style="viral",
                provider_used="gemini",
                final_rank_score=85.0,
                published=True,
                content_url="https://example.com/1",
                notion_page_id="page-123",
            )
            mock_db.record_draft.assert_called_once()

    def test_with_scores(self):
        from pipeline.draft_analytics import record_draft_event

        mock_db = MagicMock()
        with patch("pipeline.cost_db.CostDatabase", return_value=mock_db):
            record_draft_event(
                content_url="https://example.com/2",
                notion_page_id="page-456",
                hook_score=8.5,
                virality_score=7.0,
                fit_score=9.0,
            )
            mock_db.record_draft.assert_called_once()
            mock_db.update_draft_scores.assert_called_once_with(
                content_url="https://example.com/2",
                notion_page_id="page-456",
                hook_score=8.5,
                virality_score=7.0,
                fit_score=9.0,
            )

    def test_no_scores_skips_update(self):
        from pipeline.draft_analytics import record_draft_event

        mock_db = MagicMock()
        with patch("pipeline.cost_db.CostDatabase", return_value=mock_db):
            record_draft_event(source="test")
            mock_db.record_draft.assert_called_once()
            mock_db.update_draft_scores.assert_not_called()

    def test_exception_suppressed(self):
        from pipeline.draft_analytics import record_draft_event

        with patch("pipeline.cost_db.CostDatabase", side_effect=RuntimeError("db broken")):
            # Should not raise
            record_draft_event(source="test")

    def test_defaults(self):
        from pipeline.draft_analytics import record_draft_event

        mock_db = MagicMock()
        with patch("pipeline.cost_db.CostDatabase", return_value=mock_db):
            record_draft_event()
            call_kwargs = mock_db.record_draft.call_args[1]
            assert call_kwargs["source"] == ""
            assert call_kwargs["published"] is False
            assert call_kwargs["final_rank_score"] == 0.0


class TestRefreshMlScorer:
    def test_successful_refresh(self):
        from pipeline.draft_analytics import refresh_ml_scorer_if_needed

        mock_scorer = MagicMock()
        with patch("pipeline.ml_scorer.get_ml_scorer", return_value=mock_scorer):
            refresh_ml_scorer_if_needed()
            mock_scorer.retrain_if_needed.assert_called_once()

    def test_exception_suppressed(self):
        from pipeline.draft_analytics import refresh_ml_scorer_if_needed

        with patch("pipeline.ml_scorer.get_ml_scorer", side_effect=ImportError("no sklearn")):
            # Should not raise
            refresh_ml_scorer_if_needed()
