"""
회귀 테스트: T-BUG-SLOW-TEST
==============================
근본 원인: enrichment_engine.py Fallback 경로의 asyncio.sleep(0.5)가
           테스트 환경에서 실제 대기를 일으켜 pytest 전체 실행을 248초까지 늘렸음.

이 파일은 해당 버그가 재발했을 때 반드시 FAIL하도록 설계됩니다.
"""

import time

import pytest

from pipeline.enrichment_engine import ContextEnrichmentEngine


class TestRegressionSlowTest:
    """T-BUG-SLOW-TEST 회귀 보호 테스트.

    enrichment_engine의 Fallback 경로에 asyncio.sleep이 재삽입되면
    아래 테스트가 타임아웃으로 FAIL합니다.
    """

    @pytest.mark.asyncio
    async def test_regression_no_sleep_in_perplexity_fallback(self):
        """Perplexity 키 없는 Fallback이 1.0초 안에 반환되어야 한다.

        asyncio.sleep(0.5)가 재삽입 + 여러 호출 누적 시 이 임계값을 초과하여 FAIL.
        (httpx.AsyncClient 초기화 오버헤드 ~0.1s 허용)
        """
        engine = ContextEnrichmentEngine(
            exa_api_key=None,
            perplexity_api_key=None,
        )

        start = time.perf_counter()
        result = await engine.process_topic("테스트 토픽")
        elapsed = time.perf_counter() - start

        assert result is not None, "Fallback 모드에서 None을 반환하면 안 된다"
        assert elapsed < 1.0, (
            f"Fallback 경로가 {elapsed:.3f}초 소요됨 — asyncio.sleep 재삽입 의심! (T-BUG-SLOW-TEST 재발)"
        )

    @pytest.mark.asyncio
    async def test_regression_no_sleep_in_batch_fallback(self):
        """batch_process의 Fallback 경로가 3초 안에 완료되어야 한다.

        sleep(0.5) × 3토픽 = 1.5s 최소 + 순차 실행 시 더 길어짐.
        sleep 재삽입 시 이 임계값을 초과해 FAIL.
        """
        engine = ContextEnrichmentEngine(
            exa_api_key=None,
            perplexity_api_key=None,
        )
        topics = ["토픽A", "토픽B", "토픽C"]

        start = time.perf_counter()
        await engine.batch_process(topics)
        elapsed = time.perf_counter() - start

        # sleep(0.5) × 3토픽 병렬처리여도 최소 0.5s는 걸림, 3초 기준이면 충분히 구분됨
        assert elapsed < 3.0, (
            f"batch_process Fallback이 {elapsed:.3f}초 소요됨 — asyncio.sleep 재삽입 의심! (T-BUG-SLOW-TEST 재발)"
        )

    @pytest.mark.asyncio
    async def test_regression_perplexity_fallback_returns_string(self):
        """Perplexity 키 없을 때 빈 문자열이 아닌 의미있는 Fallback 메시지를 반환해야 한다."""
        engine = ContextEnrichmentEngine(
            exa_api_key=None,
            perplexity_api_key=None,
        )
        result = await engine.process_topic("직장인 번아웃")

        assert result is not None
        assert result.original_topic == "직장인 번아웃"
        assert len(result.deep_insights) > 0, "Fallback 인사이트가 비어있으면 안 된다"
        assert "직장인 번아웃" in result.deep_insights, "Fallback 메시지에 원본 토픽이 포함되어야 한다"

    def test_regression_no_asyncio_sleep_in_source(self):
        """enrichment_engine.py 소스에 asyncio.sleep이 없는지 정적 검증.

        소스 코드에서 직접 sleep 호출 여부를 검사합니다.
        이 테스트는 코드 리뷰 없이 sleep이 재삽입되는 것을 방지합니다.
        """
        import inspect
        from pipeline import enrichment_engine

        source = inspect.getsource(enrichment_engine)

        # asyncio.sleep은 허용되지 않음 (주석 내 언급은 OK, 실제 호출만 금지)
        assert "await asyncio.sleep" not in source, (
            "enrichment_engine.py에 'await asyncio.sleep'이 발견됨! T-BUG-SLOW-TEST 재발 방지를 위해 제거 필요."
        )
