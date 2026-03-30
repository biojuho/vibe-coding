from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_run_scheduled_uses_canonical_workspace_modules():
    module = load_module(
        "test_btx_run_scheduled",
        ROOT / "projects" / "blind-to-x" / "run_scheduled.py",
    )

    assert module.PROJECT_DIR == ROOT / "projects" / "blind-to-x"
    assert module.WORKSPACE_DIR == ROOT / "workspace"
    assert module.WORKSPACE_EXECUTION_DIR == ROOT / "workspace" / "execution"

    follow_ups = module.build_follow_up_tasks("python")
    assert follow_ups[0]["cmd"] == ["python", "-m", "execution.pipeline_watchdog"]
    assert follow_ups[0]["cwd"] == ROOT / "workspace"
    assert follow_ups[1]["cmd"] == ["python", "-m", "execution.backup_to_onedrive"]
    assert follow_ups[1]["cwd"] == ROOT / "workspace"


def test_n8n_bridge_defaults_use_canonical_paths(monkeypatch):
    monkeypatch.setenv("BRIDGE_TOKEN", "test-token")
    monkeypatch.delenv("BTX_DIR", raising=False)
    monkeypatch.delenv("BRIDGE_LOG_DIR", raising=False)

    module = load_module(
        "test_n8n_bridge_server",
        ROOT / "infrastructure" / "n8n" / "bridge_server.py",
    )

    assert module.default_btx_dir() == ROOT / "projects" / "blind-to-x"
    assert module.default_log_dir() == ROOT / "infrastructure" / "n8n" / "logs"

    commands = module.build_allowed_commands(
        repo_root=ROOT,
        btx_dir=ROOT / "projects" / "blind-to-x",
        python_exe="python",
    )
    assert commands["btx_pipeline"]["cwd"] == str(ROOT / "projects" / "blind-to-x")
    assert commands["btx_pipeline"]["cmd"] == [
        "python",
        str(ROOT / "projects" / "blind-to-x" / "main.py"),
        "--parallel",
        "3",
    ]
    assert commands["onedrive_backup"]["cwd"] == str(ROOT / "workspace")
    assert commands["onedrive_backup"]["cmd"] == [
        "python",
        "-m",
        "execution.backup_to_onedrive",
    ]
    assert commands["yt_analytics"]["cmd"] == [
        "python",
        "-m",
        "execution.result_tracker_db",
        "collect",
    ]
    assert commands["notebooklm_pipeline"]["cmd"] == [
        "python",
        "-m",
        "execution.gdrive_pdf_extractor",
        "list-folder",
    ]


def test_n8n_healthcheck_defaults_use_canonical_paths(monkeypatch):
    monkeypatch.delenv("BTX_DIR", raising=False)

    module = load_module(
        "test_n8n_healthcheck",
        ROOT / "infrastructure" / "n8n" / "healthcheck.py",
    )

    assert module.default_btx_dir() == ROOT / "projects" / "blind-to-x"
    assert module.env_candidates() == [
        ROOT / "projects" / "blind-to-x" / ".env",
        ROOT / ".env",
    ]


def test_scheduler_files_do_not_reference_removed_roots():
    files = [
        ROOT / "projects" / "blind-to-x" / "run_scheduled.py",
        ROOT / "projects" / "blind-to-x" / "run_scheduled.bat",
        ROOT / "projects" / "blind-to-x" / "run_pipeline.bat",
        ROOT / "projects" / "blind-to-x" / "register_schedule.ps1",
        ROOT / "projects" / "blind-to-x" / "register_task.ps1",
        ROOT / "projects" / "blind-to-x" / "setup_task_scheduler.ps1",
        ROOT / "projects" / "blind-to-x" / "scheduler_launchers.ps1",
        ROOT / "infrastructure" / "n8n" / "bridge_server.py",
        ROOT / "infrastructure" / "n8n" / "healthcheck.py",
    ]
    legacy_roots = [
        r"Desktop\Vibe coding\blind-to-x",
        r"Desktop\Vibe coding\execution",
    ]

    for path in files:
        content = path.read_text(encoding="utf-8")
        for legacy_root in legacy_roots:
            assert legacy_root not in content, f"{path} still contains {legacy_root}"
