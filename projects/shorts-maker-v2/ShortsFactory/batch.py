#!/usr/bin/env python3
"""ShortsFactory — CSV 배치 렌더링.

CSV 파일에서 여러 영상 데이터를 읽어 한 번에 렌더링합니다.

CSV 형식:
    channel,template,output_name,data_json
    ai_tech,ai_news_breaking,gpt5_news,"{""news_title"":""GPT-5 출시"",...}"

사용법:
    python -m ShortsFactory.batch --csv ai_contents.csv --outdir ./output/
"""

from __future__ import annotations

import csv
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("ShortsFactory.batch")


def batch_render(
    csv_path: str | Path,
    output_dir: str | Path = "output",
    config_path: str | Path | None = None,
    on_progress: Any = None,
) -> list[dict]:
    """CSV에서 배치 렌더링을 실행합니다.

    Args:
        csv_path: CSV 파일 경로
        output_dir: 출력 디렉토리
        config_path: channels.yaml 경로 (None이면 기본 경로)
        on_progress: 진행률 콜백 fn(current, total, result_dict)

    Returns:
        각 작업의 결과 리스트
    """
    from .pipeline import ShortsFactory

    csv_path = Path(csv_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")

    # CSV 파싱
    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        logger.warning("CSV에 데이터가 없습니다.")
        return []

    total = len(rows)
    results = []
    errors = []
    t0 = time.time()

    # tqdm 시도
    try:
        from tqdm import tqdm

        iterator = tqdm(enumerate(rows), total=total, desc="🎬 배치 렌더링")
    except ImportError:
        iterator = enumerate(rows)

    for i, row in iterator:
        channel = row.get("channel", "").strip()
        template = row.get("template", "").strip()
        output_name = row.get("output_name", f"batch_{i:04d}").strip()
        data_json = row.get("data_json", "{}").strip()

        if not channel or not template:
            result = {"index": i, "status": "skipped", "error": "channel 또는 template 누락"}
            results.append(result)
            continue

        try:
            data = json.loads(data_json) if data_json else {}
        except json.JSONDecodeError as e:
            result = {"index": i, "status": "error", "error": f"JSON 파싱 실패: {e}"}
            results.append(result)
            errors.append(result)
            continue

        # 출력 경로
        safe_name = output_name.replace("/", "_").replace("\\", "_")
        out_path = str(out_dir / f"{safe_name}.mp4")

        try:
            factory = ShortsFactory(channel=channel, config_path=config_path)
            factory.create(template, data)
            path = factory.render(out_path)
            result = {
                "index": i,
                "channel": channel,
                "template": template,
                "output": path,
                "status": "done",
            }
        except Exception as e:
            result = {
                "index": i,
                "channel": channel,
                "template": template,
                "status": "error",
                "error": str(e),
            }
            errors.append(result)
            logger.error(f"  [{i + 1}/{total}] ❌ {channel}/{template}: {e}")

        results.append(result)
        if on_progress:
            on_progress(i + 1, total, result)

    elapsed = time.time() - t0
    done = sum(1 for r in results if r.get("status") == "done")
    fail = len(errors)

    logger.info(f"\n{'=' * 50}")
    logger.info(f"배치 완료: {done}/{total} 성공, {fail} 실패 ({elapsed:.1f}초)")
    logger.info(f"{'=' * 50}")

    # 에러 로그
    if errors:
        err_path = out_dir / "batch_errors.json"
        with open(err_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        logger.info(f"에러 로그: {err_path}")

    # 결과 요약
    summary_path = out_dir / "batch_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total": total,
                "done": done,
                "errors": fail,
                "elapsed_sec": round(elapsed, 1),
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return results
