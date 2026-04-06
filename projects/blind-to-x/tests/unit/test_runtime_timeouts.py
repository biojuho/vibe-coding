import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.process_stages.runtime import AI_IMAGE_DOWNLOAD_TIMEOUT, post_to_twitter


def test_post_to_twitter_ai_image_uses_bounded_session_timeout():
    poster = MagicMock()
    poster.enabled = True
    poster.post_tweet = AsyncMock(return_value={"id": "t789"})

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read = AsyncMock(return_value=b"fake-png-data")

    mock_request_ctx = AsyncMock()
    mock_request_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_request_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_request_ctx)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("pipeline.process_stages.runtime.aiohttp.ClientSession", return_value=mock_session) as mock_client:
        result = asyncio.run(post_to_twitter(poster, "tweet", "https://img.ai/test.png", None))

    assert result == {"id": "t789"}
    mock_client.assert_called_once_with(timeout=AI_IMAGE_DOWNLOAD_TIMEOUT)
