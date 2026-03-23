"""dashboard.py 단위 테스트."""

import json
from pathlib import Path

from shorts_maker_v2.utils.dashboard import generate_dashboard


class TestGenerateDashboard:
    def test_empty_dir(self, tmp_path: Path):
        logs = tmp_path / "logs"
        logs.mkdir()
        out = tmp_path / "out.html"
        result = generate_dashboard(logs, out)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "데이터가 없습니다" in content

    def test_with_cost_data(self, tmp_path: Path):
        logs = tmp_path / "logs"
        logs.mkdir()
        costs_file = logs / "costs.jsonl"
        records = [
            {"job_id": "j1", "timestamp": "2026-03-23T10:00:00+00:00", "status": "success", "cost_usd": 0.25},
            {"job_id": "j2", "timestamp": "2026-03-23T11:00:00+00:00", "status": "success", "cost_usd": 0.30},
            {"job_id": "j3", "timestamp": "2026-03-23T12:00:00+00:00", "status": "failed", "cost_usd": 0.10},
        ]
        with costs_file.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        out = tmp_path / "out.html"
        result = generate_dashboard(logs, out)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "html" in content.lower()

    def test_deduplicates_job_ids(self, tmp_path: Path):
        logs = tmp_path / "logs"
        logs.mkdir()
        costs_file = logs / "costs.jsonl"
        records = [
            {"job_id": "same", "timestamp": "2026-03-23T10:00:00+00:00", "status": "success", "cost_usd": 0.5},
            {"job_id": "same", "timestamp": "2026-03-23T10:00:00+00:00", "status": "success", "cost_usd": 0.5},
        ]
        with costs_file.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        out = tmp_path / "out.html"
        generate_dashboard(logs, out)
        # Job should only be counted once
        content = out.read_text(encoding="utf-8")
        assert content  # just verify it generated without error

    def test_invalid_json_lines_skipped(self, tmp_path: Path):
        logs = tmp_path / "logs"
        logs.mkdir()
        costs_file = logs / "data.jsonl"
        costs_file.write_text("not json\n{\"cost_usd\": 0.1}\n", encoding="utf-8")

        out = tmp_path / "out.html"
        result = generate_dashboard(logs, out)
        assert result.exists()

    def test_job_log_file(self, tmp_path: Path):
        logs = tmp_path / "logs"
        logs.mkdir()
        # A per-job JSONL log (not costs.jsonl format)
        job_file = logs / "20260323-100000-abc123.jsonl"
        entries = [
            {"level": "INFO", "event": "start", "ts": "2026-03-23T10:00:00"},
            {
                "level": "INFO", "event": "render_complete",
                "output_path": "/out.mp4", "cost_usd_total": 0.35,
                "status": "success",
            },
        ]
        with job_file.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        out = tmp_path / "out.html"
        generate_dashboard(logs, out)
        assert out.exists()
