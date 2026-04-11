from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.express_draft import ExpressDraftPipeline


class _MockConfig:
    def get(self, key, default=None):
        return default


@pytest.mark.asyncio
async def test_generate_timeout_includes_enrichment_budget():
    pipeline = ExpressDraftPipeline(config_mgr=_MockConfig(), timeout_seconds=1)
    pipeline._enrichment_engine = MagicMock()

    pipeline._enrichment_engine.process_topic = AsyncMock(return_value=None)
    pipeline._call_llm = AsyncMock(return_value={"response": '{"x": "ok", "threads": "ok"}'})

    # _fast_sleeps 픽스처가 asyncio.sleep을 즉시 반환하므로
    # asyncio.wait_for를 직접 모킹하여 TimeoutError를 발생시킴
    _original_wait_for = asyncio.wait_for

    async def _patched_wait_for(coro, *, timeout=None):
        """타임아웃 1초 이하 설정에만 TimeoutError 발생"""
        try:
            if timeout is not None and timeout <= 1:
                coro.close()
                raise asyncio.TimeoutError()
            return await _original_wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise

    with patch("pipeline.express_draft.asyncio.wait_for", side_effect=_patched_wait_for):
        result = await pipeline.generate(
            title="slow enrichment",
            content_preview="timeout budget",
            source="blind",
        )

    assert result.success is False
    assert result.error
    pipeline._call_llm.assert_not_called()
