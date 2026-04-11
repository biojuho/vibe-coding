import asyncio

import pytest

from pipeline.enrichment_engine import ContextEnrichmentEngine, EnrichedContext


@pytest.mark.asyncio
async def test_batch_process_respects_max_concurrency():
    engine = ContextEnrichmentEngine(exa_api_key=None, perplexity_api_key=None, max_concurrency=2)
    active = 0
    max_seen = 0

    async def slow_process(topic, _client=None):
        nonlocal active, max_seen
        active += 1
        max_seen = max(max_seen, active)
        await asyncio.sleep(0.05)
        active -= 1
        return EnrichedContext(
            original_topic=topic,
            deep_insights="insight",
            global_references=[],
            sentiment_angle="neutral",
        )

    engine.process_topic = slow_process
    topics = [f"topic-{index}" for index in range(5)]

    results = await engine.batch_process(topics)

    assert set(results.keys()) == set(topics)
    assert max_seen <= 2
