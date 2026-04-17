import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import escalation_runner


@pytest.fixture
def mock_config():
    config = MagicMock()
    return config


@pytest.mark.asyncio
@patch("pipeline.spike_detector.SpikeDetector")
@patch("pipeline.escalation_queue.EscalationQueue")
@patch("pipeline.express_draft.ExpressDraftPipeline")
@patch("pipeline.draft_generator.TweetDraftGenerator")
async def test_run_cycle_no_spikes(mock_draft_gen, mock_pipeline, mock_queue, mock_detector, mock_config):
    detector_inst = mock_detector.return_value
    detector_inst.scan = AsyncMock(return_value=[])

    processed = await escalation_runner._run_cycle(mock_config, dry_run=True)
    assert processed == 0
    mock_queue.return_value.enqueue.assert_not_called()


@pytest.mark.asyncio
@patch("pipeline.spike_detector.SpikeDetector")
@patch("pipeline.escalation_queue.EscalationQueue")
@patch("pipeline.express_draft.ExpressDraftPipeline")
@patch("pipeline.draft_generator.TweetDraftGenerator")
async def test_run_cycle_with_spikes(mock_draft_gen, mock_pipeline, mock_queue, mock_detector, mock_config):
    spike_mock = MagicMock()

    detector_inst = mock_detector.return_value
    detector_inst.scan = AsyncMock(return_value=[spike_mock])

    event_mock = MagicMock()
    event_mock.id = 1
    event_mock.source = "test_source"
    event_mock.title = "Test title"
    event_mock.velocity_score = 10.0

    queue_inst = mock_queue.return_value
    queue_inst.enqueue.return_value = 1
    queue_inst.dequeue_pending.return_value = [event_mock]

    pipeline_inst = mock_pipeline.return_value
    draft_result = MagicMock()
    draft_result.success = True
    draft_result.draft_x = "My draft"
    draft_result.draft_threads = []

    pipeline_inst.generate = AsyncMock(return_value=draft_result)

    processed = await escalation_runner._run_cycle(mock_config, dry_run=True)

    assert processed == 1
    queue_inst.enqueue.assert_called_once_with(spike_mock)
    pipeline_inst.generate.assert_called_once()
    queue_inst.update_status.assert_called_with(
        1, escalation_runner.EventStatus.AWAITING_APPROVAL, draft_x="My draft", draft_threads=[]
    )


@pytest.mark.asyncio
@patch("execution.telegram_notifier.answer_callback_query")
@patch("execution.telegram_notifier.edit_message_reply_markup")
async def test_process_callback(mock_edit, mock_answer):
    queue_mock = MagicMock()
    event_mock = MagicMock()
    event_mock.id = 123
    queue_mock.get_event.return_value = event_mock

    query = {"id": "cb1", "data": "approve_123", "message": {"chat": {"id": 999}, "message_id": 888}}

    await escalation_runner._process_callback(query, queue_mock)

    queue_mock.update_status.assert_called_with(123, escalation_runner.EventStatus.APPROVED)
    mock_answer.assert_called_with("cb1", text="✅ 발행이 승인되었습니다!")
    mock_edit.assert_called_with(999, 888, None)
