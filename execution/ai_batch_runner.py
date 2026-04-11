"""
AI Batch Runner - 비동기형 AI 배치 실행기

이 도구는 3계층 아키텍처 중 'Execution' 계층에 속하며,
JSON Lines 형식(JSONL)으로 된 다량의 프롬프트를 비동기적으로(concurrently) 실행하여
결과를 저장하는 결정론적 스크립트입니다.

주요 기능:
- `tasks.jsonl` 등의 입력을 받아 `asyncio.Semaphore` 기반의 동시성 제어.
- OpenAI AsyncClient 를 활용한 기본 호출 (필요시 BASE_URL 환경 변수로 프록시 우회 가능).
- 실패 시 재시도(Exponential Backoff).
- 최종 결과를 `output.jsonl`로 저장.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import traceback
from typing import Any

from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def process_item(
    item: dict[str, Any],
    client: AsyncOpenAI,
    model: str,
    sem: asyncio.Semaphore,
    max_retries: int,
) -> dict[str, Any]:
    """단일 아이템을 비동기적으로 처리합니다."""
    prompt = item.get("prompt")
    system_prompt = item.get("system_prompt")
    if not prompt:
        return {**item, "error": "No prompt provided", "status": "failed"}

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    async with sem:
        for attempt in range(max_retries + 1):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=item.get("temperature", 0.7),
                    max_tokens=item.get("max_tokens", 1024),
                )
                output_text = response.choices[0].message.content
                return {**item, "output": output_text, "status": "success"}
            except Exception as e:
                logger.warning("Attempt %d/%d failed for task %s: %s", attempt + 1, max_retries, item.get("id", "unknown"), e)
                if attempt == max_retries:
                    return {
                        **item,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "status": "failed",
                    }
                await asyncio.sleep(2**attempt)
    return {**item, "error": "Unknown error", "status": "failed"}


async def main_async(
    input_file: str, output_file: str, model: str, concurrency: int, max_retries: int
):
    if not os.path.exists(input_file):
        logger.error("Input file not found: %s", input_file)
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY", "dummy-key-if-not-required")
    client = AsyncOpenAI(api_key=api_key)

    # 환경 변수에 BASE_URL이 설정되어 있다면 (예: vLLM, LiteLLM 호환용도)
    if os.environ.get("OPENAI_BASE_URL"):
        client.base_url = os.environ.get("OPENAI_BASE_URL")

    tasks_data = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                tasks_data.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("JSON parsing error on line: %s, error: %s", line, exc)

    logger.info("Loaded %d tasks from %s", len(tasks_data), input_file)

    sem = asyncio.Semaphore(concurrency)

    tasks = [
        asyncio.create_task(process_item(item, client, model, sem, max_retries))
        for item in tasks_data
    ]

    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r.get("status") == "success")
    fail_count = sum(1 for r in results if r.get("status") == "failed")

    logger.info(
        "Completed processing. Success: %d, Failed: %d", success_count, fail_count
    )

    # 상위 디렉터리가 없으면 생성 (output_file 기준)
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    logger.info("Results saved to %s", output_file)


def main():
    parser = argparse.ArgumentParser(description="비동기형 AI 배치 실행기 (JSONL 입력 기반)")
    parser.add_argument("--input", required=True, help="Input JSONL file")
    parser.add_argument("--output", required=True, help="Output JSONL file")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model name to use")
    parser.add_argument(
        "--concurrency", type=int, default=5, help="Maximum concurrent requests"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Max retries per task"
    )

    args = parser.parse_args()

    try:
        asyncio.run(
            main_async(
                args.input, args.output, args.model, args.concurrency, args.max_retries
            )
        )
    except KeyboardInterrupt:
        logger.info("Batch runner interrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
