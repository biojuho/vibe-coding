"""
벤치마크: 로컬 Ollama 추론 vs 기준 성능 측정.

Ollama가 실행 중일 때 실제 모델 응답 시간, 정확도, 토큰 처리량을 측정합니다.
모든 결과는 `workspace/.tmp/benchmark_results.json`에 저장됩니다.

Usage:
    python workspace/execution/benchmark_local.py
    python workspace/execution/benchmark_local.py --model gemma3:4b
    python workspace/execution/benchmark_local.py --compare google
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution._logging import logger
from execution.local_inference import OllamaClient
from execution.smart_router import SmartRouter


# ── 벤치마크 프롬프트 ─────────────────────────────────────────

BENCHMARK_PROMPTS = [
    # SIMPLE (단순 코드)
    {
        "id": "S1",
        "complexity": "SIMPLE",
        "system": "You are a Python expert.",
        "prompt": "Write a Python function that calculates the factorial of a number.",
        "expected_keywords": ["def", "factorial", "return"],
    },
    {
        "id": "S2",
        "complexity": "SIMPLE",
        "system": "You are a Python expert.",
        "prompt": "Write a list comprehension that filters even numbers from a list.",
        "expected_keywords": ["[", "for", "if", "%"],
    },
    # MODERATE (클래스/패턴)
    {
        "id": "M1",
        "complexity": "MODERATE",
        "system": "You are a senior Python developer.",
        "prompt": (
            "Implement a Python class for a thread-safe singleton pattern "
            "with lazy initialization. Include type hints and docstrings."
        ),
        "expected_keywords": ["class", "def", "__init__", "instance"],
    },
    {
        "id": "M2",
        "complexity": "MODERATE",
        "system": "You are a Python expert.",
        "prompt": (
            "Write an async Python function that fetches data from multiple URLs "
            "concurrently using aiohttp, with proper error handling and timeout."
        ),
        "expected_keywords": ["async", "await", "aiohttp", "timeout"],
    },
    # COMPLEX (아키텍처/분석)
    {
        "id": "C1",
        "complexity": "COMPLEX",
        "system": "You are a software architect.",
        "prompt": (
            "Design a rate limiter for a REST API that supports:\n"
            "1. Token bucket algorithm\n"
            "2. Per-user and global limits\n"
            "3. Redis-backed distributed state\n"
            "Provide the Python implementation with full type hints."
        ),
        "expected_keywords": ["class", "def", "redis", "token", "limit"],
    },
    {
        "id": "C2",
        "complexity": "COMPLEX",
        "system": "You are a database architect.",
        "prompt": (
            "Analyze the trade-offs between event sourcing and CQRS patterns "
            "for an e-commerce order management system. Cover:\n"
            "- Data consistency guarantees\n"
            "- Read/write performance characteristics\n"
            "- Operational complexity\n"
            "Provide concrete examples and recommendations."
        ),
        "expected_keywords": ["event", "command", "query", "consistency"],
    },
]


# ── 벤치마크 실행기 ──────────────────────────────────────────


def _match_expected_keywords(content: str, expected_keywords: list[str]) -> tuple[list[str], float]:
    """Return matched expected keywords and normalized accuracy."""
    if not expected_keywords:
        return [], 0.0

    content_lower = content.lower()
    matched = [kw for kw in expected_keywords if kw.lower() in content_lower]
    return matched, len(matched) / len(expected_keywords)


def run_single_benchmark(
    client: OllamaClient,
    prompt_data: dict[str, Any],
    model: str | None = None,
) -> dict[str, Any]:
    """단일 프롬프트 벤치마크 실행."""
    start = time.perf_counter()
    result: dict[str, Any] = {
        "id": prompt_data["id"],
        "complexity": prompt_data["complexity"],
        "model": model or client.default_model,
        "status": "failed",
    }

    try:
        content, in_tok, out_tok = client.generate(
            system_prompt=prompt_data["system"],
            user_prompt=prompt_data["prompt"],
            model=model,
            temperature=0.3,
        )
        elapsed = time.perf_counter() - start

        # 키워드 매칭 정확도
        matched, accuracy = _match_expected_keywords(content, prompt_data["expected_keywords"])

        result.update(
            {
                "status": "success",
                "elapsed_sec": round(elapsed, 2),
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "tokens_per_sec": round(out_tok / elapsed, 1) if elapsed > 0 else 0,
                "keyword_accuracy": round(accuracy, 2),
                "matched_keywords": matched,
                "response_length": len(content),
                "response_preview": content[:200],
            }
        )

        logger.info(
            "[%s] %s | %.1fs | %d tok/s | accuracy=%.0f%%",
            prompt_data["id"],
            "✅" if accuracy >= 0.5 else "⚠️",
            elapsed,
            result["tokens_per_sec"],
            accuracy * 100,
        )

    except Exception as e:
        elapsed = time.perf_counter() - start
        result.update(
            {
                "status": "error",
                "error": str(e),
                "elapsed_sec": round(elapsed, 2),
            }
        )
        logger.warning("[%s] ❌ 실패: %s (%.1fs)", prompt_data["id"], e, elapsed)

    return result


def _collect_router_results(
    router: SmartRouter,
    prompts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classify benchmark prompts with SmartRouter."""
    results = []
    for prompt_data in prompts:
        classified = router.classify(prompt_data["prompt"])
        results.append(
            {
                "id": prompt_data["id"],
                "expected": prompt_data["complexity"],
                "classified": classified.complexity.value,
                "match": prompt_data["complexity"].lower() == classified.complexity.value.lower(),
                "score": round(classified.score, 3),
            }
        )
    return results


def _run_ollama_benchmarks(
    client: OllamaClient,
    prompts: list[dict[str, Any]],
    target_model: str,
) -> list[dict[str, Any]]:
    """Run every benchmark prompt against the target Ollama model."""
    return [run_single_benchmark(client, prompt_data, model=target_model) for prompt_data in prompts]


def _average_metric(results: list[dict[str, Any]], metric: str, ndigits: int) -> float:
    return round(sum(result[metric] for result in results) / len(results), ndigits)


def _estimate_cloud_cost(total_tokens: int) -> dict[str, float]:
    return {
        "openai_gpt4o_mini": round(total_tokens * 0.00015 / 1000, 4),  # $0.15/1M
        "anthropic_claude_sonnet": round(total_tokens * 0.003 / 1000, 4),  # $3/1M
        "google_gemini_flash": round(total_tokens * 0.000075 / 1000, 4),  # $0.075/1M
        "ollama_local": 0.0,
    }


def _summarize_ollama_results(
    ollama_results: list[dict[str, Any]],
    *,
    total_prompts: int,
) -> dict[str, Any]:
    """Build aggregate statistics for benchmark output."""
    successful = [result for result in ollama_results if result["status"] == "success"]
    stats: dict[str, Any] = {
        "total_prompts": total_prompts,
        "successful": len(successful),
        "failed": len(ollama_results) - len(successful),
    }

    if successful:
        stats["avg_elapsed_sec"] = _average_metric(successful, "elapsed_sec", 2)
        stats["avg_tokens_per_sec"] = _average_metric(successful, "tokens_per_sec", 1)
        stats["avg_keyword_accuracy"] = _average_metric(successful, "keyword_accuracy", 2)

        # 복잡도별 통계
        for level in ("SIMPLE", "MODERATE", "COMPLEX"):
            level_results = [result for result in successful if result["complexity"] == level]
            if level_results:
                stats[f"avg_elapsed_{level.lower()}"] = _average_metric(level_results, "elapsed_sec", 2)
                stats[f"avg_accuracy_{level.lower()}"] = _average_metric(level_results, "keyword_accuracy", 2)

    total_tokens = sum(result.get("input_tokens", 0) + result.get("output_tokens", 0) for result in successful)
    stats["estimated_cloud_cost"] = _estimate_cloud_cost(total_tokens)
    return stats


def _build_benchmark_output(
    *,
    target_model: str,
    available_models: list[str],
    stats: dict[str, Any],
    router_results: list[dict[str, Any]],
    ollama_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "ollama_version": "0.18.2",
        "model": target_model,
        "available_models": available_models,
        "stats": stats,
        "router_accuracy": router_results,
        "ollama_results": ollama_results,
    }


def _write_benchmark_output(output: dict[str, Any]) -> Path:
    output_dir = WORKSPACE_ROOT / ".tmp"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "benchmark_results.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def run_benchmark(
    model: str | None = None,
    compare_provider: str | None = None,
) -> dict[str, Any]:
    """전체 벤치마크 실행."""
    client = OllamaClient()

    try:
        # 서버 확인
        if not client.is_available():
            logger.error("Ollama 서버 연결 실패. 'ollama serve'를 실행하세요.")
            return {"error": "Ollama server not available"}

        # 모델 확인
        available_models = client.list_models()
        target_model = model or client.default_model
        logger.info("=== 벤치마크 시작 ===")
        logger.info("모델: %s", target_model)
        logger.info("프롬프트: %d개", len(BENCHMARK_PROMPTS))
        logger.info("사용 가능한 모델: %s", available_models)

        router_results = _collect_router_results(SmartRouter(), BENCHMARK_PROMPTS)
        ollama_results = _run_ollama_benchmarks(client, BENCHMARK_PROMPTS, target_model)
        stats = _summarize_ollama_results(ollama_results, total_prompts=len(BENCHMARK_PROMPTS))
        output = _build_benchmark_output(
            target_model=target_model,
            available_models=available_models,
            stats=stats,
            router_results=router_results,
            ollama_results=ollama_results,
        )

        output_path = _write_benchmark_output(output)
        logger.info("결과 저장: %s", output_path)

        # 요약 출력
        _print_summary(stats, router_results, target_model)
        return output
    finally:
        client.close()


def _print_summary(
    stats: dict[str, Any],
    router_results: list[dict[str, Any]],
    model: str,
) -> None:
    """벤치마크 요약 출력."""
    print("\n" + "=" * 60)
    print(f"  📊 벤치마크 결과 — {model}")
    print("=" * 60)

    print(f"\n  성공: {stats['successful']}/{stats['total_prompts']}")
    if stats.get("avg_elapsed_sec"):
        print(f"  평균 응답 시간: {stats['avg_elapsed_sec']}s")
        print(f"  평균 토큰/초: {stats['avg_tokens_per_sec']}")
        print(f"  평균 키워드 정확도: {stats['avg_keyword_accuracy'] * 100:.0f}%")

    print("\n  복잡도별 응답 시간:")
    for level in ("simple", "moderate", "complex"):
        key = f"avg_elapsed_{level}"
        if key in stats:
            acc_key = f"avg_accuracy_{level}"
            print(f"    {level.upper():>10}: {stats[key]:.1f}s (정확도 {stats.get(acc_key, 0) * 100:.0f}%)")

    # 라우터 정확도
    router_correct = sum(1 for r in router_results if r["match"])
    print(f"\n  SmartRouter 분류 정확도: {router_correct}/{len(router_results)}")
    for r in router_results:
        emoji = "✅" if r["match"] else "❌"
        print(f"    {emoji} [{r['id']}] 예상={r['expected']} → 결과={r['classified']}")

    # 비용 비교
    if stats.get("estimated_cloud_cost"):
        costs = stats["estimated_cloud_cost"]
        print("\n  💰 추정 클라우드 비용 (동일 워크로드):")
        for provider, cost in costs.items():
            print(f"    {provider:>30}: ${cost:.4f}")

    print("\n" + "=" * 60)


# ── CLI ─────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="로컬 추론 벤치마크")
    parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="테스트할 Ollama 모델 (기본: 환경변수 OLLAMA_DEFAULT_MODEL)",
    )
    parser.add_argument(
        "--compare",
        "-c",
        default=None,
        help="비교할 클라우드 프로바이더 (예: google, openai)",
    )
    args = parser.parse_args()

    run_benchmark(model=args.model, compare_provider=args.compare)


if __name__ == "__main__":
    main()
