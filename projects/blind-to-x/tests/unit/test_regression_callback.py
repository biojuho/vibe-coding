import pytest
from unittest.mock import MagicMock, patch

from escalation_runner import _process_callback


@pytest.mark.asyncio
async def test_regression_callback_data_value_error():
    """
    회귀 테스트: telegram callback_data 파싱 시 ValueError 대응 (ID가 숫자가 아닌 경우).
    버그 재현: 이전에 event_id를 URL로 넘겨서 int(event_id)가 ValueError를 발생시켜 알림 처리가 중단되는 문제가 있었음.
    """
    queue_mock = MagicMock()
    # int() 변환 불가한 문자열이 들어왔을 때 ValueError가 발생하지만
    # _process_callback이 정상적으로 예외 처리하고 실행 완료되어야 함

    query = {"id": "cb_123", "data": "approve_not-an-integer", "message": {"message_id": 42, "chat": {"id": 999}}}
    with patch("execution.telegram_notifier.answer_callback_query") as m_answer:
        with patch("execution.telegram_notifier.edit_message_reply_markup") as m_edit:
            await _process_callback(query, queue_mock)

            # ValueError가 잡혀서 event_obj = None으로 처리되어야 함.
            queue_mock.get_event.assert_not_called()
            queue_mock.update_status.assert_not_called()

            # "이벤트를 찾을 수 없습니다" 메시지로 answer_callback_query가 호출되어야 함
            m_answer.assert_called_once_with("cb_123", text="⚠️ 이벤트를 찾을 수 없습니다.")
            m_edit.assert_called_once_with(999, 42, None)
