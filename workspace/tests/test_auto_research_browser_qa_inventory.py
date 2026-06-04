"""Unit tests for the auto-research browser QA inventory helper."""

from __future__ import annotations

import importlib.util
import json
import sys
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
    (screenshot_dir / "knowledge-t1264-browser-click-qa.png").write_bytes(b"png")

    result = browser_qa_inventory.build_inventory(tmp_path)
    project = result["projects"][0]

    assert result["summary"]["browser_project_count"] == 1
    assert result["summary"]["covered_count"] == 1
    assert project["path"] == "projects/knowledge-dashboard"
    assert project["status"] == "covered"
    assert project["current_screenshot_count"] == 1


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
