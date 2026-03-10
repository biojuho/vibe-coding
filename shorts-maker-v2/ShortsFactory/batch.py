"""
batch.py — CSV 배치 처리 모듈
==============================
CSV 파일에서 여러 영상 데이터를 읽어 순차 렌더링합니다.

CSV 포맷:
    template,channel,hook_text,title,points,keywords
    ai_news,ai_tech,🚨 역대급,GPT-5 출시,성능 3배|멀티모달,3배|멀티모달
"""
from __future__ import annotations

import csv
import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """배치 처리 결과."""
    index: int
    template: str
    channel: str
    status: str  # "success" | "error"
    output_path: str = ""
    error_message: str = ""
    elapsed_sec: float = 0.0


class BatchProcessor:
    """CSV 배치 렌더링 프로세서.

    Args:
        config_dir: config 디렉토리 경로.
    """

    def __init__(self, *, config_dir: Path | str | None = None) -> None:
        self._config_dir = Path(config_dir) if config_dir else None

    def run(
        self,
        csv_path: str,
        output_dir: str,
        *,
        channel: str | None = None,
    ) -> list[BatchResult]:
        """CSV 파일을 파싱하여 순차 렌더링합니다.

        Args:
            csv_path: CSV 파일 경로.
            output_dir: 출력 디렉토리.
            channel: CSV에 channel 컬럼이 없을 때 사용할 기본 채널.

        Returns:
            BatchResult 리스트.
        """
        from ShortsFactory.pipeline import ShortsFactory

        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV 파일 없음: {csv_path}")

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # CSV 파싱
        rows = self._parse_csv(csv_file)
        results: list[BatchResult] = []
        total = len(rows)

        logger.info("[Batch] %d개 항목 처리 시작", total)

        # tqdm 사용 시도
        try:
            from tqdm import tqdm
            iterator = tqdm(enumerate(rows), total=total, desc="배치 렌더링")
        except ImportError:
            iterator = enumerate(rows)

        for i, row in iterator:
            ch = row.get("channel", channel or "")
            tmpl = row.get("template", "")
            start = time.time()

            try:
                data = self._row_to_data(row)
                factory = ShortsFactory(ch, config_dir=self._config_dir)
                factory.create(tmpl, data)

                output_name = f"{i+1:03d}_{ch}_{tmpl}.mp4"
                output_file = out_dir / output_name
                factory.render(output_file)

                results.append(BatchResult(
                    index=i + 1, template=tmpl, channel=ch,
                    status="success", output_path=str(output_file),
                    elapsed_sec=time.time() - start,
                ))
                logger.info("[Batch] %d/%d 성공: %s", i + 1, total, output_name)

            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}"
                results.append(BatchResult(
                    index=i + 1, template=tmpl, channel=ch,
                    status="error", error_message=err_msg,
                    elapsed_sec=time.time() - start,
                ))
                logger.error("[Batch] %d/%d 실패: %s", i + 1, total, err_msg)

        # 에러 로그 저장
        self._save_error_log(results, out_dir)
        self._print_summary(results)

        return results

    # ── 내부 메서드 ─────────────────────────────────────────────────────

    @staticmethod
    def _parse_csv(csv_file: Path) -> list[dict[str, str]]:
        with csv_file.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)

    @staticmethod
    def _row_to_data(row: dict[str, str]) -> dict[str, Any]:
        """CSV 행을 템플릿 데이터 dict로 변환."""
        data: dict[str, Any] = {}
        for key, value in row.items():
            if key in ("template", "channel"):
                continue
            # 파이프(|) 구분은 리스트로 변환
            if "|" in value:
                data[key] = value.split("|")
            elif key == "points":
                # points는 JSON 또는 파이프 구분
                try:
                    data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    data[key] = [{"text": t.strip()} for t in value.split("|")]
            else:
                data[key] = value
        return data

    @staticmethod
    def _save_error_log(results: list[BatchResult], out_dir: Path) -> None:
        errors = [r for r in results if r.status == "error"]
        if not errors:
            return
        log_path = out_dir / "batch_errors.log"
        with log_path.open("w", encoding="utf-8") as f:
            f.write(f"# Batch Error Log — {datetime.now(timezone.utc).isoformat()}\n\n")
            for r in errors:
                f.write(f"[{r.index}] {r.channel}/{r.template}: {r.error_message}\n")
        logger.warning("[Batch] %d개 에러 로그: %s", len(errors), log_path)

    @staticmethod
    def _print_summary(results: list[BatchResult]) -> None:
        success = sum(1 for r in results if r.status == "success")
        errors = sum(1 for r in results if r.status == "error")
        total_time = sum(r.elapsed_sec for r in results)
        print(f"\n{'='*50}")
        print(f"  배치 결과: {success}개 성공 / {errors}개 실패")
        print(f"  총 소요 시간: {total_time:.1f}초")
        print(f"{'='*50}\n")
