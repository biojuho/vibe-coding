from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.express_draft import ExpressDraftPipeline


class _MockConfig:
    def get(self, key, default=None):
        return default


@pytest.mark.asyncio
async def test_generate_timeout_includes_enrichment_budget():
    pipeline = ExpressDraftPipeline(config_mgr=_MockConfig(), timeout_seconds=1)
    pipeline._enrichment_engine = MagicMock()

    async def slow_enrichment(*args, **kwargs):
        await asyncio.sleep(10)
        return None

    pipeline._enrichment_engine.process_topic = AsyncMock(side_effect=slow_enrichment)
    pipeline._call_llm = AsyncMock(return_value={"response": '{"x": "ok", "threads": "ok"}'})

    result = await pipeline.generate(
        title="slow enrichment",
        content_preview="timeout budget",
        source="blind",
    )

    assert result.success is False
    assert result.error
    pipeline._call_llm.assert_not_called()
