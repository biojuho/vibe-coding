"""Tests for metrics_report — 메트릭 리포트 생성 모듈."""

from __future__ import annotations

import json

# 스크립트 모듈 직접 import 대신 함수 단위 테스트
import sys
from pathlib import Path

# scripts 디렉토리를 path에 추가
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from metrics_report import _load_records, format_text_report, generate_report


class TestGenerateReport:
    """generate_report 함수 테스트."""

    def test_empty_records(self):
        report = generate_report([])
        assert report["total_calls"] == 0
        assert report["total_cost_usd"] == 0.0
        assert report["avg_latency_ms"] == 0.0

    def test_single_record(self):
        records = [
            {
                "model": "gemini-2.5-flash",
                "provider": "google",
                "cost_usd": 0.001,
                "input_tokens": 100,
                "output_tokens": 50,
                "latency_ms": 200.0,
            }
        ]
        report = generate_report(records)
        assert report["total_calls"] == 1
        assert report["total_cost_usd"] == 0.001
        assert report["total_input_tokens"] == 100
        assert report["total_output_tokens"] == 50
        assert report["avg_latency_ms"] == 200.0

    def test_multiple_models(self):
        records = [
            {
                "model": "gemini-2.5-flash",
                "provider": "google",
                "cost_usd": 0.001,
                "input_tokens": 100,
                "output_tokens": 50,
                "latency_ms": 200.0,
            },
            {
                "model": "gpt-4o-mini",
                "provider": "openai",
                "cost_usd": 0.005,
                "input_tokens": 200,
                "output_tokens": 100,
                "latency_ms": 500.0,
            },
        ]
        report = generate_report(records)
        assert report["total_calls"] == 2
        assert report["total_cost_usd"] == 0.006
        assert len(report["by_model"]) == 2
        assert len(report["by_provider"]) == 2

    def test_missing_fields(self):
        """필드 누락 시 기본값 사용."""
        records = [{"model": "test"}]
        report = generate_report(records)
        assert report["total_calls"] == 1
        assert report["total_cost_usd"] == 0.0

    def test_p95_latency(self):
        records = [{"latency_ms": i * 10.0, "model": "m"} for i in range(1, 101)]
        report = generate_report(records)
        # int(100 * 0.95) = 95 → sorted[95] = 960.0
        assert report["p95_latency_ms"] == 960.0


class TestFormatTextReport:
    """format_text_report 함수 테스트."""

    def test_basic_format(self):
        report = generate_report(
            [
                {
                    "model": "gemini-2.5-flash",
                    "provider": "google",
                    "cost_usd": 0.01,
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "latency_ms": 300.0,
                }
            ]
        )
        text = format_text_report(report)
        assert "Pipeline LLM Metrics Report" in text
        assert "Total API Calls" in text
        assert "gemini-2.5-flash" in text
        assert "google" in text

    def test_empty_report(self):
        report = generate_report([])
        text = format_text_report(report)
        assert "0" in text


class TestLoadRecords:
    """_load_records 함수 테스트."""

    def test_load_from_directory(self, tmp_path):
        """JSONL 파일에서 레코드 로드."""
        jsonl_file = tmp_path / "llm_2026-05-08.jsonl"
        records = [
            {"model": "test1", "cost_usd": 0.001},
            {"model": "test2", "cost_usd": 0.002},
        ]
        jsonl_file.write_text(
            "\n".join(json.dumps(r) for r in records),
            encoding="utf-8",
        )
        loaded = _load_records(tmp_path, days=365)
        assert len(loaded) == 2

    def test_skip_invalid_json(self, tmp_path):
        """잘못된 JSON 행은 건너뜀."""
        jsonl_file = tmp_path / "llm_2026-05-08.jsonl"
        jsonl_file.write_text(
            '{"model": "ok"}\nINVALID JSON\n{"model": "ok2"}\n',
            encoding="utf-8",
        )
        loaded = _load_records(tmp_path, days=365)
        assert len(loaded) == 2

    def test_skip_old_files(self, tmp_path):
        """오래된 날짜의 파일은 건너뜀."""
        old_file = tmp_path / "llm_2020-01-01.jsonl"
        old_file.write_text('{"model": "old"}\n', encoding="utf-8")
        loaded = _load_records(tmp_path, days=1)
        assert len(loaded) == 0
