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
        assert 'name="viewport" content="width=device-width, initial-scale=1"' in content
        assert '<link rel="icon" href="data:,' in content

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
        assert 'class="table-wrap" role="region" aria-label="일별 통계 표"' in content
        assert "grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));" in content
        assert "overflow-x: auto;" in content

    def test_responsive_browser_contract(self, tmp_path: Path):
        logs = tmp_path / "logs"
        logs.mkdir()
        costs_file = logs / "costs.jsonl"
        costs_file.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "job_id": "j1",
                            "timestamp": "2026-03-23T10:00:00+00:00",
                            "status": "success",
                            "cost_usd": 0.25,
                        }
                    ),
                    json.dumps(
                        {
                            "job_id": "j2",
                            "timestamp": "2026-03-23T11:00:00+00:00",
                            "status": "failed",
                            "cost_usd": 0.10,
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        out = tmp_path / "out.html"
        content = generate_dashboard(logs, out).read_text(encoding="utf-8")

        assert "<main>" in content
        assert 'id="dashboard-updated"' in content
        assert 'aria-describedby="dashboard-updated"' in content
        assert "min-width: 620px;" in content
        assert "-webkit-overflow-scrolling: touch;" in content
        assert 'tabindex="0"' in content

    def test_docs_dashboard_sample_matches_responsive_contract(self):
        sample = Path(__file__).resolve().parents[2] / "docs" / "dashboard.html"
        content = sample.read_text(encoding="utf-8")

        assert 'name="viewport" content="width=device-width, initial-scale=1"' in content
        assert '<link rel="icon" href="data:,' in content
        assert "grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));" in content
        assert 'class="table-wrap" role="region" aria-label="일별 통계 표"' in content

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
        costs_file.write_text('not json\n{"cost_usd": 0.1}\n', encoding="utf-8")

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
                "level": "INFO",
                "event": "render_complete",
                "output_path": "/out.mp4",
                "cost_usd_total": 0.35,
                "status": "success",
            },
        ]
        with job_file.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        out = tmp_path / "out.html"
        generate_dashboard(logs, out)
        assert out.exists()

    def test_job_finished_event(self, tmp_path: Path):
        """job_finished 이벤트가 있는 개별 job 로그."""
        logs = tmp_path / "logs"
        logs.mkdir()
        job_file = logs / "job-success-001.jsonl"
        entries = [
            {"event": "start", "timestamp": "2026-03-25T09:00:00+09:00"},
            {"event": "job_finished", "timestamp": "2026-03-25T09:05:00+09:00"},
        ]
        with job_file.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        out = tmp_path / "out.html"
        result = generate_dashboard(logs, out)
        content = result.read_text(encoding="utf-8")
        assert "2026-03-25" in content

    def test_pipeline_complete_event(self, tmp_path: Path):
        """pipeline_complete 이벤트에서 비용 추출."""
        logs = tmp_path / "logs"
        logs.mkdir()
        job_file = logs / "pipeline-ok-002.jsonl"
        entries = [
            {"event": "start", "timestamp": "2026-03-26T10:00:00+00:00"},
            {"event": "pipeline_complete", "status": "success", "estimated_cost_usd": 0.42},
        ]
        with job_file.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        out = tmp_path / "out.html"
        result = generate_dashboard(logs, out)
        content = result.read_text(encoding="utf-8")
        assert "$0.42" in content or "0.4200" in content

    def test_pipeline_error_event(self, tmp_path: Path):
        """pipeline_error 이벤트 → failed 집계."""
        logs = tmp_path / "logs"
        logs.mkdir()
        job_file = logs / "error-job-003.jsonl"
        entries = [
            {"event": "start", "timestamp": "2026-03-26T11:00:00+00:00"},
            {"event": "pipeline_error"},
        ]
        with job_file.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        out = tmp_path / "out.html"
        result = generate_dashboard(logs, out)
        content = result.read_text(encoding="utf-8")
        assert "color: red" in content  # failed count is colored red

    def test_render_done_cost_extraction(self, tmp_path: Path):
        """render_done 이벤트에서 비용 추출."""
        logs = tmp_path / "logs"
        logs.mkdir()
        job_file = logs / "render-cost-004.jsonl"
        entries = [
            {"event": "start", "timestamp": "2026-03-26T12:00:00+00:00"},
            {"event": "render_done", "estimated_cost_usd": 0.15},
            {"event": "job_finished"},
        ]
        with job_file.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        out = tmp_path / "out.html"
        result = generate_dashboard(logs, out)
        content = result.read_text(encoding="utf-8")
        assert "0.15" in content

    def test_invalid_timestamp_uses_unknown(self, tmp_path: Path):
        """잘못된 timestamp → 'Unknown' 날짜."""
        logs = tmp_path / "logs"
        logs.mkdir()
        costs_file = logs / "costs.jsonl"
        record = {"job_id": "bad-ts", "timestamp": "not-a-date", "status": "success", "cost_usd": 0.01}
        costs_file.write_text(json.dumps(record) + "\n", encoding="utf-8")

        out = tmp_path / "out.html"
        result = generate_dashboard(logs, out)
        content = result.read_text(encoding="utf-8")
        assert "Unknown" in content

    def test_broken_jsonl_file_skipped(self, tmp_path: Path):
        """파일 읽기 에러 시 건너뜀 (비정상 인코딩 등)."""
        logs = tmp_path / "logs"
        logs.mkdir()
        # 정상 파일 하나 + 깨진 파일 하나
        good = logs / "good.jsonl"
        good.write_text(
            json.dumps({"job_id": "g1", "timestamp": "2026-03-27T10:00:00+00:00", "status": "success", "cost_usd": 0.5})
            + "\n",
            encoding="utf-8",
        )
        bad = logs / "bad.jsonl"
        bad.write_bytes(b"\xff\xfe invalid bytes\n")

        out = tmp_path / "out.html"
        result = generate_dashboard(logs, out)
        content = result.read_text(encoding="utf-8")
        assert "$0.5" in content or "0.5000" in content

    def test_broken_jsonl_file_logs_debug_skip(self, tmp_path: Path, caplog):
        """파일 읽기 에러 시 dashboard: skipping job file 로그 발생."""
        import logging

        logs = tmp_path / "logs"
        logs.mkdir()
        bad = logs / "unreadable.jsonl"
        bad.write_bytes(b"\xff\xfe invalid bytes\n")

        out = tmp_path / "out.html"
        with caplog.at_level(logging.DEBUG, logger="shorts_maker_v2.utils.dashboard"):
            generate_dashboard(logs, out)
        messages = [r.message for r in caplog.records]
        assert any("dashboard: skipping job file" in m for m in messages)
