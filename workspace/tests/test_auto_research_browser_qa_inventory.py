"""Unit tests for the auto-research browser QA inventory helper."""

from __future__ import annotations

import importlib.util
import json
import os
import struct
import sys
import zlib
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


def _write_rgba_png(path: Path, rows: list[list[tuple[int, int, int, int]]]) -> None:
    height = len(rows)
    width = len(rows[0]) if rows else 0

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + b"\x00\x00\x00\x00"

    raw_rows = []
    for row in rows:
        assert len(row) == width
        raw_rows.append(b"\x00" + b"".join(bytes(pixel) for pixel in row))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"".join(raw_rows)))
        + chunk(b"IEND", b"")
    )


def _write_nonblank_png(path: Path) -> None:
    _write_rgba_png(path, [[(0, 0, 0, 255), (255, 255, 255, 255)]])


def _write_blank_png(path: Path) -> None:
    _write_rgba_png(path, [[(0, 0, 0, 255), (0, 0, 0, 255)]])


def test_browser_app_is_covered_by_current_screenshot(tmp_path: Path) -> None:
    app = tmp_path / "projects" / "knowledge-dashboard"
    _write_package(app, dependencies={"next": "1.0.0", "react": "1.0.0"})
    screenshot_dir = tmp_path / "output" / "playwright"
    screenshot_dir.mkdir(parents=True)
    screenshot = screenshot_dir / "knowledge-t1264-browser-click-qa.png"
    _write_nonblank_png(screenshot)
    modified_at = datetime(2026, 6, 1, tzinfo=UTC).timestamp()
    os.utime(screenshot, (modified_at, modified_at))

    result = browser_qa_inventory.build_inventory(tmp_path, now=datetime(2026, 6, 5, tzinfo=UTC))
    project = result["projects"][0]

    assert result["summary"]["browser_project_count"] == 1
    assert result["summary"]["covered_count"] == 1
    assert result["summary"]["fresh_screenshot_project_count"] == 1
    assert result["summary"]["stale_screenshot_project_count"] == 0
    assert result["summary"]["valid_screenshot_project_count"] == 1
    assert result["summary"]["fresh_valid_screenshot_project_count"] == 1
    assert result["summary"]["usable_screenshot_project_count"] == 1
    assert result["summary"]["fresh_usable_screenshot_project_count"] == 1
    assert result["summary"]["nonblank_screenshot_project_count"] == 1
    assert result["summary"]["fresh_nonblank_screenshot_project_count"] == 1
    assert result["summary"]["freshest_screenshots"] == {
        "projects/knowledge-dashboard": {
            "path": "output/playwright/knowledge-t1264-browser-click-qa.png",
            "modified_at": "2026-06-01T00:00:00+00:00",
            "age_days": 4,
            "fresh": True,
            "image_check": "ok",
            "image_valid": True,
            "nonblank": True,
            "width": 2,
            "height": 1,
        }
    }
    assert project["path"] == "projects/knowledge-dashboard"
    assert project["status"] == "covered"
    assert project["current_screenshot_count"] == 1
    assert project["valid_screenshot_count"] == 1
    assert project["usable_screenshot_count"] == 1
    assert project["nonblank_screenshot_count"] == 1
    assert project["freshest_screenshot_path"] == "output/playwright/knowledge-t1264-browser-click-qa.png"
    assert project["freshest_screenshot_age_days"] == 4
    assert project["freshest_screenshot_fresh"] is True
    assert project["freshest_screenshot_image_check"] == "ok"
    assert project["freshest_screenshot_width"] == 2
    assert project["freshest_screenshot_height"] == 1


def test_stale_browser_screenshot_gets_refresh_recommendation(tmp_path: Path) -> None:
    app = tmp_path / "projects" / "hanwoo-dashboard"
    _write_package(app, dependencies={"next": "1.0.0", "react": "1.0.0"})
    screenshot_dir = tmp_path / "output" / "playwright"
    screenshot_dir.mkdir(parents=True)
    screenshot = screenshot_dir / "hanwoo-t100-browser-click-qa.png"
    _write_nonblank_png(screenshot)
    modified_at = datetime(2026, 5, 1, tzinfo=UTC).timestamp()
    os.utime(screenshot, (modified_at, modified_at))

    result = browser_qa_inventory.build_inventory(tmp_path, now=datetime(2026, 6, 5, tzinfo=UTC))
    project = result["projects"][0]

    assert project["status"] == "covered"
    assert project["freshest_screenshot_age_days"] == 35
    assert project["freshest_screenshot_fresh"] is False
    assert result["summary"]["fresh_screenshot_project_count"] == 0
    assert result["summary"]["stale_screenshot_project_count"] == 1
    assert result["summary"]["valid_screenshot_project_count"] == 1
    assert result["summary"]["fresh_valid_screenshot_project_count"] == 0
    assert result["summary"]["nonblank_screenshot_project_count"] == 1
    assert result["summary"]["fresh_nonblank_screenshot_project_count"] == 0
    assert result["recommendations"] == [
        "Refresh browser QA screenshots older than 14 day(s) for project(s): projects/hanwoo-dashboard"
    ]


def test_invalid_screenshot_does_not_cover_browser_app(tmp_path: Path) -> None:
    app = tmp_path / "projects" / "suika-game-v2"
    _write_package(app, dependencies={"vite": "1.0.0"})
    screenshot_dir = tmp_path / "output" / "playwright"
    screenshot_dir.mkdir(parents=True)
    (screenshot_dir / "suika-t100-browser-click-qa.png").write_bytes(b"png")

    result = browser_qa_inventory.build_inventory(tmp_path, now=datetime(2026, 6, 5, tzinfo=UTC))
    project = result["projects"][0]

    assert project["status"] == "missing"
    assert project["current_screenshot_count"] == 1
    assert project["valid_screenshot_count"] == 0
    assert project["usable_screenshot_count"] == 0
    assert project["evidence"][0]["image_check"] == "invalid"
    assert project["evidence"][0]["image_valid"] is False
    assert result["summary"]["valid_screenshot_project_count"] == 0
    assert result["recommendations"] == [
        "Run direct browser-click QA for project(s): projects/suika-game-v2",
        "Refresh invalid browser QA screenshots for project(s): projects/suika-game-v2",
    ]


def test_blank_screenshot_does_not_cover_browser_app(tmp_path: Path) -> None:
    app = tmp_path / "projects" / "word-chain"
    _write_package(app, dependencies={"vite": "1.0.0"})
    screenshot_dir = tmp_path / "output" / "playwright"
    screenshot_dir.mkdir(parents=True)
    _write_blank_png(screenshot_dir / "word-chain-t100-browser-click-qa.png")

    result = browser_qa_inventory.build_inventory(tmp_path, now=datetime(2026, 6, 5, tzinfo=UTC))
    project = result["projects"][0]

    assert project["status"] == "missing"
    assert project["valid_screenshot_count"] == 1
    assert project["usable_screenshot_count"] == 0
    assert project["nonblank_screenshot_count"] == 0
    assert project["freshest_screenshot_image_check"] == "blank"
    assert result["summary"]["valid_screenshot_project_count"] == 1
    assert result["summary"]["usable_screenshot_project_count"] == 0
    assert result["summary"]["fresh_nonblank_screenshot_project_count"] == 0
    assert result["recommendations"] == [
        "Run direct browser-click QA for project(s): projects/word-chain",
        "Refresh blank browser QA screenshots for project(s): projects/word-chain",
    ]


def test_png_chunk_scan_and_support_helpers_parse_valid_png(tmp_path: Path) -> None:
    screenshot = tmp_path / "valid.png"
    _write_nonblank_png(screenshot)

    scan = browser_qa_inventory._png_chunk_scan(screenshot.read_bytes())

    assert scan.width == 2
    assert scan.height == 1
    assert scan.bit_depth == 8
    assert scan.color_type == 6
    assert scan.compression_method == 0
    assert scan.filter_method == 0
    assert scan.interlace_method == 0
    assert scan.idat
    assert scan.saw_iend is True
    assert scan.issues == []
    assert (
        browser_qa_inventory._png_supported_bytes_per_pixel(
            scan.bit_depth,
            scan.color_type,
            scan.compression_method,
            scan.filter_method,
            scan.interlace_method,
        )
        == 4
    )
    assert browser_qa_inventory._png_supported_bytes_per_pixel(16, 6, 0, 0, 0) is None


def test_png_chunk_scan_reports_truncated_chunks() -> None:
    truncated = browser_qa_inventory.PNG_SIGNATURE + struct.pack(">I", 13) + b"IHDR" + b"\x00\x00\x00"

    scan = browser_qa_inventory._png_chunk_scan(truncated)

    assert scan.width == 0
    assert scan.height == 0
    assert scan.idat == b""
    assert scan.saw_iend is False
    assert scan.issues == ["png chunk IHDR is truncated"]


def test_png_reconstruct_row_applies_sub_filter_and_reports_unsupported_filter() -> None:
    row, offset, issues = browser_qa_inventory._png_reconstruct_row(
        bytes([1, 10, 5, 5]),
        0,
        3,
        bytearray([0, 0, 0]),
        1,
    )

    assert bytes(row) == bytes([10, 15, 20])
    assert offset == 4
    assert issues == []
    assert browser_qa_inventory._png_row_has_pixel_change(row, 1, bytes([10])) is True

    invalid_row, invalid_offset, invalid_issues = browser_qa_inventory._png_reconstruct_row(
        bytes([9, 1, 2, 3]),
        0,
        3,
        bytearray([0, 0, 0]),
        1,
    )

    assert invalid_row == bytearray()
    assert invalid_offset == 4
    assert invalid_issues == ["unsupported png filter type: 9"]


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


def test_browser_inventory_args_from_argv_preserves_cli_contract(tmp_path: Path) -> None:
    output = tmp_path / ".tmp" / "browser-inventory.json"

    args = browser_qa_inventory._browser_inventory_args_from_argv(
        ["--root", str(tmp_path), "--include-non-browser", "--json", "--output", str(output)]
    )

    assert args.root == tmp_path
    assert args.include_non_browser is True
    assert args.json is True
    assert args.output == output


def test_browser_inventory_args_from_argv_uses_existing_defaults() -> None:
    args = browser_qa_inventory._browser_inventory_args_from_argv([])

    assert args.root == Path.cwd()
    assert args.include_non_browser is False
    assert args.json is False
    assert args.output is None


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
