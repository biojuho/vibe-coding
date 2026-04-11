from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from escalation_runner import _run_cycle


@pytest.mark.asyncio
async def test_run_cycle_builds_express_pipeline_with_draft_generator() -> None:
    config = MagicMock()
    detector = MagicMock()
    detector.scan = AsyncMock(
        return_value=[
            {
                "title": "급상승 토픽",
                "source": "blind",
                "velocity_score": 12.0,
            }
        ]
    )
    queue = MagicMock()
    queue.enqueue.return_value = 1
    queue.dequeue_pending.return_value = [
        SimpleNamespace(id=1, source="blind", title="급상승 토픽", velocity_score=12.0)
    ]
    queue.get_stats.return_value = {"pending": 0}
    pipeline = MagicMock()
    pipeline.generate = AsyncMock(
        return_value=SimpleNamespace(
            success=False,
            error="provider unavailable",
            draft_x="",
            draft_threads="",
        )
    )
    draft_generator = MagicMock()

    with (
        patch("pipeline.spike_detector.SpikeDetector", return_value=detector),
        patch("pipeline.escalation_queue.EscalationQueue", return_value=queue),
        patch("pipeline.express_draft.ExpressDraftPipeline", return_value=pipeline) as pipeline_cls,
        patch("pipeline.draft_generator.TweetDraftGenerator", return_value=draft_generator) as draft_cls,
    ):
        processed = await _run_cycle(config, dry_run=True)

    assert processed == 0
    draft_cls.assert_called_once_with(config)
    pipeline_cls.assert_called_once_with(config, draft_generator=draft_generator)
