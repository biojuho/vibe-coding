"""Unit tests for the auto-research browser QA inventory helper."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "browser_qa_inventory.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("browser_qa_inventory", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["browser_qa_inventory"] = module
    spec.loader.exec_module(module)
    return module


browser_qa_inventory = _load_module()


def _write_package(
    path: Path, dependencies: dict[str, str] | None = None, scripts: dict[str, str] | None = None
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    package = {
        "name": path.name,
        "dependencies": dependencies or {},
        "scripts": scripts or {},
    }
    (path / "package.json").write_text(json.dumps(package), encoding="utf-8")


def test_browser_app_is_covered_by_current_screenshot(tmp_path: Path) -> None:
    app = tmp_path / "projects" / "knowledge-dashboard"
    _write_package(app, dependencies={"next": "1.0.0", "react": "1.0.0"})
    screenshot_dir = tmp_path / "output" / "playwright"
    screenshot_dir.mkdir(parents=True)
    screenshot = screenshot_dir / "knowledge-t1264-browser-click-qa.png"
    screenshot.write_bytes(b"png")
    modified_at = datetime(2026, 6, 1, tzinfo=UTC).timestamp()
    os.utime(screenshot, (modified_at, modified_at))

    result = browser_qa_inventory.build_inventory(tmp_path, now=datetime(2026, 6, 5, tzinfo=UTC))
    project = result["projects"][0]

    assert result["summary"]["browser_project_count"] == 1
    assert result["summary"]["covered_count"] == 1
    assert result["summary"]["fresh_screenshot_project_count"] == 1
    assert result["summary"]["stale_screenshot_project_count"] == 0
    assert result["summary"]["freshest_screenshots"] == {
        "projects/knowledge-dashboard": {
            "path": "output/playwright/knowledge-t1264-browser-click-qa.png",
            "modified_at": "2026-06-01T00:00:00+00:00",
            "age_days": 4,
            "fresh": True,
        }
    }
    assert project["path"] == "projects/knowledge-dashboard"
    assert project["status"] == "covered"
    assert project["current_screenshot_count"] == 1
    assert project["freshest_screenshot_path"] == "output/playwright/knowledge-t1264-browser-click-qa.png"
    assert project["freshest_screenshot_age_days"] == 4
    assert project["freshest_screenshot_fresh"] is True


def test_stale_browser_screenshot_gets_refresh_recommendation(tmp_path: Path) -> None:
    app = tmp_path / "projects" / "hanwoo-dashboard"
    _write_package(app, dependencies={"next": "1.0.0", "react": "1.0.0"})
    screenshot_dir = tmp_path / "output" / "playwright"
    screenshot_dir.mkdir(parents=True)
    screenshot = screenshot_dir / "hanwoo-t100-browser-click-qa.png"
    screenshot.write_bytes(b"png")
    modified_at = datetime(2026, 5, 1, tzinfo=UTC).timestamp()
    os.utime(screenshot, (modified_at, modified_at))

    result = browser_qa_inventory.build_inventory(tmp_path, now=datetime(2026, 6, 5, tzinfo=UTC))
    project = result["projects"][0]

    assert project["status"] == "covered"
    assert project["freshest_screenshot_age_days"] == 35
    assert project["freshest_screenshot_fresh"] is False
    assert result["summary"]["fresh_screenshot_project_count"] == 0
    assert result["summary"]["stale_screenshot_project_count"] == 1
    assert result["recommendations"] == [
        "Refresh browser QA screenshots older than 14 day(s) for project(s): projects/hanwoo-dashboard"
    ]


def test_browser_app_is_covered_by_verified_log_line(tmp_path: Path) -> None:
    app = tmp_path / "projects" / "word-chain"
    _write_package(app, dependencies={"vite": "1.0.0"})
    log_dir = tmp_path / ".ai"
    log_dir.mkdir()
    (log_dir / "TASKS.md").write_text(
        "| T-1 | `[word-chain]` Playwright browser QA clicked input and passed with console/network issues 0. |",
        encoding="utf-8",
    )

    result = browser_qa_inventory.build_inventory(tmp_path)
    project = result["projects"][0]

    assert project["status"] == "covered"
    assert project["log_evidence_count"] == 1
    assert project["verified_log_evidence_count"] == 1
    assert result["recommendations"] == [
        "Capture or retain output/playwright screenshots for covered project(s): projects/word-chain"
    ]


def test_missing_browser_app_gets_recommendation(tmp_path: Path) -> None:
    app = tmp_path / "projects" / "suika-game-v2"
    _write_package(app, dependencies={"vite": "1.0.0"})

    result = browser_qa_inventory.build_inventory(tmp_path)

    assert result["summary"]["missing_count"] == 1
    assert result["summary"]["missing_projects"] == ["projects/suika-game-v2"]
    assert result["recommendations"] == ["Run direct browser-click QA for project(s): projects/suika-game-v2"]


def test_non_browser_package_is_hidden_by_default(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "cli-tool", scripts={"test": "pytest"})

    default_result = browser_qa_inventory.build_inventory(tmp_path)
    expanded_result = browser_qa_inventory.build_inventory(tmp_path, include_non_browser=True)

    assert default_result["projects"] == []
    assert expanded_result["projects"][0]["status"] == "not_browser_app"


def test_generic_tokens_do_not_cross_match_dashboards_or_games(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "hanwoo-dashboard", dependencies={"next": "1.0.0"})
    _write_package(tmp_path / "projects" / "knowledge-dashboard", dependencies={"next": "1.0.0"})
    _write_package(tmp_path / "projects" / "suika-game-v2", dependencies={"vite": "1.0.0"})
    _write_package(tmp_path / "projects" / "word-chain", dependencies={"vite": "1.0.0"})
    log_dir = tmp_path / ".ai"
    log_dir.mkdir()
    (log_dir / "TASKS.md").write_text(
        "\n".join(
            [
                "| T-1 | `[knowledge-dashboard]` Playwright browser QA passed with console/network issues 0. |",
                "| T-2 | `[word-chain]` Playwright browser QA clicked game-over state and passed. |",
            ]
        ),
        encoding="utf-8",
    )

    result = browser_qa_inventory.build_inventory(tmp_path)
    by_path = {project["path"]: project for project in result["projects"]}

    assert by_path["projects/knowledge-dashboard"]["status"] == "covered"
    assert by_path["projects/word-chain"]["status"] == "covered"
    assert by_path["projects/hanwoo-dashboard"]["status"] == "missing"
    assert by_path["projects/suika-game-v2"]["status"] == "missing"


def test_bracketed_target_overrides_later_project_mentions(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "hanwoo-dashboard", dependencies={"next": "1.0.0"})
    _write_package(tmp_path / "projects" / "knowledge-dashboard", dependencies={"next": "1.0.0"})
    log_dir = tmp_path / ".ai"
    log_dir.mkdir()
    (log_dir / "TASKS.md").write_text(
        "| T-1 | `[knowledge-dashboard]` Playwright browser-click QA passed; Hanwoo T-251 remains blocked. |",
        encoding="utf-8",
    )

    result = browser_qa_inventory.build_inventory(tmp_path)
    by_path = {project["path"]: project for project in result["projects"]}

    assert by_path["projects/knowledge-dashboard"]["status"] == "covered"
    assert by_path["projects/hanwoo-dashboard"]["status"] == "missing"


def test_handoff_title_target_overrides_later_project_mentions(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "knowledge-dashboard", dependencies={"next": "1.0.0"})
    _write_package(tmp_path / "projects" / "word-chain", dependencies={"vite": "1.0.0"})
    log_dir = tmp_path / ".ai"
    log_dir.mkdir()
    (log_dir / "HANDOFF.md").write_text(
        (
            "| Work | **T-1 knowledge-dashboard React dependency freshness loop**. "
            "Superseded after concurrent T-0 word-chain Vite landed; browser QA passed. |"
        ),
        encoding="utf-8",
    )

    result = browser_qa_inventory.build_inventory(tmp_path)
    by_path = {project["path"]: project for project in result["projects"]}

    assert by_path["projects/knowledge-dashboard"]["status"] == "covered"
    assert by_path["projects/word-chain"]["status"] == "missing"


def test_next_priority_lines_are_not_evidence(tmp_path: Path) -> None:
    _write_package(tmp_path / "projects" / "hanwoo-dashboard", dependencies={"next": "1.0.0"})
    log_dir = tmp_path / ".ai"
    log_dir.mkdir()
    (log_dir / "HANDOFF.md").write_text(
        "| Next Priorities | Run browser-click QA later for hanwoo-dashboard. |",
        encoding="utf-8",
    )

    result = browser_qa_inventory.build_inventory(tmp_path)

    assert result["projects"][0]["status"] == "missing"


def test_cli_output_file_writes_ascii_json_and_preserves_text_stdout(tmp_path: Path, capsys) -> None:
    root = tmp_path / "박주호"
    app = root / "projects" / "knowledge-dashboard"
    _write_package(app, dependencies={"next": "1.0.0", "react": "1.0.0"})
    output = root / ".tmp" / "browser-inventory.json"

    result = browser_qa_inventory.main(["--root", str(root), "--output", str(output)])

    stdout = capsys.readouterr().out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert "browser QA coverage:" in stdout
    assert payload["root"] == str(root.resolve())
    assert output.read_text(encoding="utf-8").isascii()


def test_cli_output_file_can_be_combined_with_json_stdout(tmp_path: Path, capsys) -> None:
    root = tmp_path
    app = root / "projects" / "word-chain"
    _write_package(app, dependencies={"vite": "1.0.0"})
    output = root / ".tmp" / "browser-inventory.json"

    result = browser_qa_inventory.main(["--root", str(root), "--output", str(output), "--json"])

    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert stdout_payload == file_payload
    assert file_payload["summary"]["browser_project_count"] == 1
