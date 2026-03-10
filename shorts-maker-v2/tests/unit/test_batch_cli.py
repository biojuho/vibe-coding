from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from shorts_maker_v2.cli import _print_batch_summary, _run_batch
from shorts_maker_v2.models import BatchResult


def _make_manifest(*, status="success", job_id="j1", cost=0.5, dur=40.0, title="T", path="/out.mp4"):
    m = MagicMock()
    m.status = status
    m.job_id = job_id
    m.estimated_cost_usd = cost
    m.total_duration_sec = dur
    m.title = title
    m.output_path = path
    m.thumbnail_path = ""
    m.failed_steps = [] if status == "success" else [{"step": "test", "code": "E", "message": "err"}]
    return m


def _make_config_file(tmp_path: Path) -> Path:
    import yaml
    payload = {
        "project": {"language": "ko-KR", "default_scene_count": 2},
        "video": {"target_duration_sec": [35, 45], "resolution": [1080, 1920], "fps": 30, "scene_video_duration_sec": 5, "aspect_ratio": "9:16"},
        "providers": {"llm": "openai", "tts": "openai", "visual_primary": "openai-image", "visual_fallback": "openai-image"},
        "limits": {"max_cost_usd": 2.0, "max_retries": 1, "request_timeout_sec": 5},
        "costs": {"llm_per_job": 0.01, "tts_per_second": 0.001, "veo_per_second": 0.03, "image_per_scene": 0.04},
        "paths": {"output_dir": "output", "logs_dir": "logs", "runs_dir": "runs"},
        "captions": {"font_size": 64, "margin_x": 90, "bottom_offset": 240, "text_color": "#FFD700", "stroke_color": "#000000", "stroke_width": 4, "line_spacing": 12, "font_candidates": ["C:/Windows/Fonts/malgun.ttf"]},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def test_batch_from_topics_file(tmp_path, monkeypatch) -> None:
    """토픽 파일에서 읽어 2건 처리, 모두 성공."""
    topics_file = tmp_path / "topics.txt"
    topics_file.write_text("주제 하나\n주제 둘\n# 주석 무시\n", encoding="utf-8")
    config_path = _make_config_file(tmp_path)

    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    manifests = [_make_manifest(job_id="j1"), _make_manifest(job_id="j2")]
    call_idx = {"i": 0}

    def fake_run(self, topic, output_filename=None, channel="", parallel=False):  # noqa: ARG001
        m = manifests[call_idx["i"]]
        call_idx["i"] += 1
        return m

    with patch("shorts_maker_v2.pipeline.orchestrator.PipelineOrchestrator.run", fake_run):
        args = SimpleNamespace(
            topics_file=str(topics_file), from_db=False, limit=5, channel="",
            config=str(config_path), parallel=False, no_continue_on_error=False,
        )
        exit_code = _run_batch(args, config_path)

    assert exit_code == 0
    assert call_idx["i"] == 2


def test_batch_continues_on_error(tmp_path, monkeypatch) -> None:
    """첫 번째 실패해도 두 번째 계속 진행."""
    topics_file = tmp_path / "topics.txt"
    topics_file.write_text("실패 주제\n성공 주제\n", encoding="utf-8")
    config_path = _make_config_file(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    manifests = [_make_manifest(status="failed", job_id="j1"), _make_manifest(job_id="j2")]
    call_idx = {"i": 0}

    def fake_run(self, topic, output_filename=None, channel="", parallel=False):  # noqa: ARG001
        m = manifests[call_idx["i"]]
        call_idx["i"] += 1
        return m

    with patch("shorts_maker_v2.pipeline.orchestrator.PipelineOrchestrator.run", fake_run):
        args = SimpleNamespace(
            topics_file=str(topics_file), from_db=False, limit=5, channel="",
            config=str(config_path), parallel=False, no_continue_on_error=False,
        )
        exit_code = _run_batch(args, config_path)

    assert exit_code == 1  # 실패 포함
    assert call_idx["i"] == 2  # 둘 다 시도됨


def test_batch_stops_on_error_flag(tmp_path, monkeypatch) -> None:
    """--no-continue-on-error 시 첫 실패에서 중단."""
    topics_file = tmp_path / "topics.txt"
    topics_file.write_text("실패 주제\n건너뛸 주제\n", encoding="utf-8")
    config_path = _make_config_file(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    call_count = {"n": 0}

    def fake_run(self, topic, output_filename=None, channel="", parallel=False):  # noqa: ARG001
        call_count["n"] += 1
        raise RuntimeError("forced failure")

    with patch("shorts_maker_v2.pipeline.orchestrator.PipelineOrchestrator.run", fake_run):
        args = SimpleNamespace(
            topics_file=str(topics_file), from_db=False, limit=5, channel="",
            config=str(config_path), parallel=False, no_continue_on_error=True,
        )
        exit_code = _run_batch(args, config_path)

    assert exit_code == 1
    assert call_count["n"] == 1  # 첫 번째만 시도


def test_batch_empty_topics_file(tmp_path, monkeypatch) -> None:
    """빈 파일 → exit 0."""
    topics_file = tmp_path / "topics.txt"
    topics_file.write_text("\n# 주석만\n\n", encoding="utf-8")
    config_path = _make_config_file(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    args = SimpleNamespace(
        topics_file=str(topics_file), from_db=False, limit=5, channel="",
        config=str(config_path), parallel=False, no_continue_on_error=False,
    )
    exit_code = _run_batch(args, config_path)
    assert exit_code == 0


def test_print_batch_summary(capsys) -> None:
    """요약 출력 확인."""
    results = [
        BatchResult(topic="t1", channel="ch", status="success", job_id="j1", cost_usd=0.5, duration_sec=40),
        BatchResult(topic="t2", channel="ch", status="failed", job_id="j2", cost_usd=0, duration_sec=0, error="err"),
    ]
    _print_batch_summary(results)
    out = capsys.readouterr().out
    assert "성공 1" in out
    assert "실패 1" in out
    assert "$0.500" in out
