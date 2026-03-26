from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import shorts_maker_v2.cli as cli


def _make_config(base_dir: Path) -> SimpleNamespace:
    return SimpleNamespace(
        paths=SimpleNamespace(output_dir="output", logs_dir="logs", runs_dir="runs"),
        rendering=SimpleNamespace(engine="native"),
    )


def _make_manifest(
    *,
    status: str = "success",
    job_id: str = "job-123",
    estimated_cost_usd: float = 1.25,
    total_duration_sec: float = 12.5,
    title: str = "Sample Title",
    output_path: str = "output/sample.mp4",
    thumbnail_path: str = "output/sample.png",
    failed_steps: list[dict[str, str]] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        status=status,
        job_id=job_id,
        estimated_cost_usd=estimated_cost_usd,
        total_duration_sec=total_duration_sec,
        title=title,
        output_path=output_path,
        thumbnail_path=thumbnail_path,
        failed_steps=failed_steps or [],
    )


def test_make_batch_namespace_copies_relevant_fields() -> None:
    base_args = SimpleNamespace(config="config.yaml", renderer="auto")

    result = cli._make_batch_namespace(base_args, "space")

    assert result.config == "config.yaml"
    assert result.channel == "space"
    assert result.renderer == "auto"
    assert result.tts_voice == ""
    assert result.style_preset == ""


def test_pick_from_db_filters_pending_and_respects_limit(monkeypatch) -> None:
    fake_db = SimpleNamespace(
        get_channels=lambda: ["ai_tech"],
        get_all=lambda channel: [
            {"id": 1, "status": "done", "topic": "done"},
            {"id": 2, "status": "pending", "topic": "older"},
            {"id": 3, "status": "pending", "topic": "newer"},
        ],
    )
    monkeypatch.setattr(cli, "_import_content_db", lambda: fake_db)

    result = cli._pick_from_db(channel="", limit=1)

    assert len(result) == 1
    assert result[0]["topic"] == "newer"


def test_doctor_success_creates_directories(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _make_config(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "validate_environment", lambda config: [])
    monkeypatch.setattr(cli, "required_env_keys", lambda config: ["OPENAI_API_KEY"])
    monkeypatch.setattr(cli.shutil, "which", lambda name: "C:/ffmpeg/bin/ffmpeg.exe")

    result = cli._doctor(tmp_path / "config.yaml")

    assert result == 0
    assert (tmp_path / "output").exists()
    assert (tmp_path / "logs").exists()
    assert (tmp_path / "runs").exists()
    stdout = capsys.readouterr().out
    assert "[OK] doctor passed" in stdout


def test_doctor_returns_one_when_env_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _make_config(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "validate_environment", lambda config: ["OPENAI_API_KEY"])
    monkeypatch.setattr(cli, "required_env_keys", lambda config: ["OPENAI_API_KEY"])
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)

    result = cli._doctor(tmp_path / "config.yaml")

    assert result == 1
    assert "Missing environment keys" in capsys.readouterr().out


def test_run_batch_uses_topics_file_and_accepts_topic_unsuitable(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    topics_file = tmp_path / "topics.txt"
    topics_file.write_text("# comment\n첫 번째 주제\n둘째 주제\n", encoding="utf-8")

    config = _make_config(tmp_path)
    manifests = iter(
        [
            _make_manifest(status="success", job_id="job-1"),
            _make_manifest(
                status="topic_unsuitable",
                job_id="job-2",
                failed_steps=[{"message": "Too vague"}],
            ),
        ]
    )
    orchestrator_calls: list[dict[str, object]] = []

    class FakeOrchestrator:
        def __init__(self, **kwargs):
            orchestrator_calls.append({"init": kwargs})

        def run(self, **kwargs):
            orchestrator_calls.append({"run": kwargs})
            return next(manifests)

    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "validate_environment", lambda config: [])
    monkeypatch.setattr(cli, "_apply_channel_overrides", lambda config, ns: config)
    monkeypatch.setattr(cli, "_import_content_db", lambda: None)
    monkeypatch.setattr(cli, "PipelineOrchestrator", FakeOrchestrator)

    args = SimpleNamespace(
        topics_file=str(topics_file),
        from_db=False,
        limit=5,
        channel="ai_tech",
        config="config.yaml",
        renderer="",
        parallel=False,
        no_continue_on_error=False,
    )

    result = cli._run_batch(args, tmp_path / "config.yaml")

    assert result == 0
    stdout = capsys.readouterr().out
    assert "성공 1 / 주제스킵 1 / 실패 0" in stdout
    run_calls = [entry["run"] for entry in orchestrator_calls if "run" in entry]
    assert run_calls[0]["topic"] == "첫 번째 주제"
    assert run_calls[1]["topic"] == "둘째 주제"


def test_run_batch_stops_on_first_error_when_continue_disabled(tmp_path: Path, monkeypatch) -> None:
    config = _make_config(tmp_path)
    db_updates: list[tuple[int, dict[str, object]]] = []
    fake_db = SimpleNamespace(
        get_channels=lambda: ["history"],
        get_all=lambda channel: [
            {"id": 10, "status": "pending", "topic": "첫 번째"},
            {"id": 11, "status": "pending", "topic": "두 번째"},
        ],
        update_job=lambda job_id, **kwargs: db_updates.append((job_id, kwargs)),
    )

    class ExplodingOrchestrator:
        def __init__(self, **kwargs):
            pass

        def run(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "validate_environment", lambda config: [])
    monkeypatch.setattr(cli, "_apply_channel_overrides", lambda config, ns: config)
    monkeypatch.setattr(cli, "_import_content_db", lambda: fake_db)
    monkeypatch.setattr(cli, "PipelineOrchestrator", ExplodingOrchestrator)

    args = SimpleNamespace(
        topics_file=None,
        from_db=True,
        limit=5,
        channel="history",
        config="config.yaml",
        renderer="",
        parallel=False,
        no_continue_on_error=True,
    )

    result = cli._run_batch(args, tmp_path / "config.yaml")

    assert result == 1
    assert len(db_updates) == 2
    assert db_updates[0][0] == 11
    assert db_updates[0][1]["status"] == "running"
    assert db_updates[1][0] == 11
    assert db_updates[1][1]["status"] == "failed"


def test_run_cli_doctor_delegates(tmp_path: Path, monkeypatch) -> None:
    called: dict[str, Path] = {}
    monkeypatch.setattr(cli, "_ensure_utf8_stdio", lambda: None)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "_doctor", lambda path: called.setdefault("path", path) or 0)

    result = cli.run_cli(["doctor", "--config", str(tmp_path / "config.yaml")])

    assert result == called["path"]


def test_run_cli_dashboard_uses_fallback_logs_dir_on_config_error(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    fake_dashboard = ModuleType("shorts_maker_v2.utils.dashboard")
    dashboard_calls: dict[str, Path] = {}

    def generate_dashboard(*, logs_dir, output_file):
        dashboard_calls["logs_dir"] = Path(logs_dir)
        dashboard_calls["output_file"] = Path(output_file)
        return Path(output_file)

    fake_dashboard.generate_dashboard = generate_dashboard
    monkeypatch.setitem(sys.modules, "shorts_maker_v2.utils.dashboard", fake_dashboard)
    monkeypatch.setattr(cli, "_ensure_utf8_stdio", lambda: None)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "load_config", lambda path: (_ for _ in ()).throw(cli.ConfigError("bad config")))

    result = cli.run_cli(["dashboard", "--config", str(tmp_path / "config.yaml"), "--out", "stats.html"])

    assert result == 0
    assert dashboard_calls["logs_dir"] == (tmp_path / "logs")
    assert dashboard_calls["output_file"] == (tmp_path / "stats.html")
    assert "Dashboard generated" in capsys.readouterr().out


def test_run_cli_costs_uses_configured_logs_dir(tmp_path: Path, monkeypatch) -> None:
    config = _make_config(tmp_path)
    tracker_calls: dict[str, Path] = {}

    class FakeTracker:
        def __init__(self, *, logs_dir):
            tracker_calls["logs_dir"] = Path(logs_dir)

        def print_summary(self):
            tracker_calls["printed"] = True

    monkeypatch.setattr(cli, "_ensure_utf8_stdio", lambda: None)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "CostTracker", FakeTracker)

    result = cli.run_cli(["costs", "--config", str(tmp_path / "config.yaml")])

    assert result == 0
    assert tracker_calls["logs_dir"] == (tmp_path / "logs")
    assert tracker_calls["printed"] is True


def test_run_cli_run_requires_topic_or_resume(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_ensure_utf8_stdio", lambda: None)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)

    result = cli.run_cli(["run"])

    assert result == 1
    assert "--topic is required unless --resume is specified" in capsys.readouterr().out


def test_run_cli_run_success(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _make_config(tmp_path)
    manifest = _make_manifest(status="success", output_path="out/video.mp4", estimated_cost_usd=0.42)
    orchestrator_calls: dict[str, object] = {}

    class FakeOrchestrator:
        def __init__(self, **kwargs):
            orchestrator_calls["init"] = kwargs

        def run(self, **kwargs):
            orchestrator_calls["run"] = kwargs
            return manifest

    monkeypatch.setattr(cli, "_ensure_utf8_stdio", lambda: None)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "validate_environment", lambda config: [])
    monkeypatch.setattr(cli, "_apply_channel_overrides", lambda config, args: config)
    monkeypatch.setattr(cli, "PipelineOrchestrator", FakeOrchestrator)

    result = cli.run_cli(
        ["run", "--topic", "AI topic", "--config", str(tmp_path / "config.yaml"), "--out", "video.mp4", "--channel", "ai_tech"]
    )

    assert result == 0
    assert orchestrator_calls["run"]["resume_job_id"] == ""
    assert orchestrator_calls["run"]["output_filename"] == "video.mp4"
    assert "generated video" in capsys.readouterr().out


def test_run_cli_run_failure_prints_failed_steps(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _make_config(tmp_path)
    manifest = _make_manifest(
        status="failed",
        failed_steps=[{"step": "render", "code": "ffmpeg_error", "message": "encode failed"}],
    )

    class FakeOrchestrator:
        def __init__(self, **kwargs):
            pass

        def run(self, **kwargs):
            return manifest

    monkeypatch.setattr(cli, "_ensure_utf8_stdio", lambda: None)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "load_config", lambda path: config)
    monkeypatch.setattr(cli, "validate_environment", lambda config: [])
    monkeypatch.setattr(cli, "_apply_channel_overrides", lambda config, args: config)
    monkeypatch.setattr(cli, "PipelineOrchestrator", FakeOrchestrator)

    result = cli.run_cli(["run", "--topic", "AI topic", "--config", str(tmp_path / "config.yaml")])

    assert result == 1
    stdout = capsys.readouterr().out
    assert "generation failed" in stdout
    assert "render: ffmpeg_error - encode failed" in stdout
