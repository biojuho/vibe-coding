import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

# execution/ 경로 구조 대응을 위해 절대 경로 임포트 추가 방지 목적으로
# pytest 실행 시 execution/ 이 PYTHONPATH에 있다고 가정합니다.
from ai_batch_runner import process_item


@pytest.mark.asyncio
async def test_regression_ai_batch_runner_empty_choices():
    """
    [QA 수정] 방어 로직 회귀 테스트:
    response.choices가 비어있을 엣지 케이스에 대해 IndexError가 나지 않고,
    ValueError로 잘 잡히며 "failed"를 반환하는지 확인합니다.
    """
    item = {"id": 1, "prompt": "Hello"}

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = []  # 비어있는 응답 시뮬레이션

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    sem = asyncio.Semaphore(1)

    result = await process_item(item, mock_client, "gpt-4o-mini", sem, max_retries=0)

    assert result.get("status") == "failed"
    assert "empty choices list" in result.get("error", "")


@pytest.mark.asyncio
async def test_regression_ai_batch_runner_null_content():
    """
    [QA 수정] 방어 로직 회귀 테스트:
    response.choices[0].message.content가 None일 때의 예외 캐치 여부 확인.
    """
    item = {"id": 2, "prompt": "World"}

    mock_client = MagicMock()
    mock_response = MagicMock()

    class FakeMessage:
        content = None

    class FakeChoice:
        message = FakeMessage()

    mock_response.choices = [FakeChoice()]

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    sem = asyncio.Semaphore(1)

    result = await process_item(item, mock_client, "gpt-4o-mini", sem, max_retries=0)

    assert result.get("status") == "failed"
    assert "null content" in result.get("error", "")
