"""Unit tests for scoped authorization menu rendering."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "scoped_authorization_menu.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("scoped_authorization_menu", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["scoped_authorization_menu"] = module
    spec.loader.exec_module(module)
    return module


scoped_authorization_menu = _load_module()


def _menu() -> dict[str, object]:
    return {
        "generated_at": "2026-06-11T06:10:00+09:00",
        "root": "C:/Users/\ubc15\uc8fc\ud638/Desktop/Vibe coding",
        "recommended": {
            "token": "APPROVE_EXAMPLE",
            "packet": ".tmp/example-current.md",
            "pathspec": ".tmp/approve-example.pathspec",
            "files": ["workspace/tests/example.py"],
            "reason": ["Focused packet is verified."],
        },
        "also_available": [
            {"token": "APPROVE_OTHER", "reason": "Another verified packet."},
        ],
    }


def test_render_markdown_uses_numeric_coverage_counts() -> None:
    markdown = scoped_authorization_menu.render_markdown(
        _menu(),
        {
            "dirty_count": 12,
            "covered_dirty_count": 8,
            "uncovered_dirty_count": 4,
            "uncovered_non_evidence_source_count": 0,
            "pathspec_count": 3,
            "staged_count": 0,
        },
    )

    assert "APPROVE_EXAMPLE" in markdown
    assert "- `workspace/tests/example.py`" in markdown
    assert "uncovered dirty paths `4` and uncovered non-evidence source paths `0`" in markdown
    assert "dirty `12`, covered `8`, pathspecs `3`, staged `0`" in markdown
    assert "System.Collections" not in markdown
    assert "$(" not in markdown


def test_render_markdown_lists_uncovered_non_evidence_source_paths() -> None:
    markdown = scoped_authorization_menu.render_markdown(
        _menu(),
        {
            "dirty_count": 12,
            "covered_dirty_count": 8,
            "uncovered_dirty_count": 4,
            "uncovered_non_evidence_source_count": 6,
            "uncovered_non_evidence_source_paths": [
                "execution/session_log_rotator.py",
                "workspace\\tests\\test_session_log_rotator.py",
                "workspace/tests/test_extra_one.py",
                "workspace/tests/test_extra_two.py",
                "workspace/tests/test_extra_three.py",
                "workspace/tests/test_extra_four.py",
            ],
            "pathspec_count": 3,
            "staged_count": 0,
        },
    )

    assert "Uncovered non-evidence source path(s):" in markdown
    assert "`execution/session_log_rotator.py`" in markdown
    assert "`workspace/tests/test_session_log_rotator.py`" in markdown
    assert "`workspace/tests/test_extra_three.py`" in markdown
    assert "plus 1 more" in markdown
    assert "test_extra_four.py" not in markdown


def test_render_markdown_drops_stale_coverage_reason() -> None:
    menu = _menu()
    menu["recommended"]["reason"].append("Pathspec audit now reports dirty 139, covered 130, uncovered 9.")

    markdown = scoped_authorization_menu.render_markdown(
        menu,
        {
            "dirty_count": 148,
            "covered_dirty_count": 148,
            "uncovered_dirty_count": 0,
            "uncovered_non_evidence_source_count": 0,
            "pathspec_count": 78,
            "staged_count": 0,
            "generated_at": "2026-06-11T11:00:05Z",
            "basis": "current coverage",
        },
    )

    assert "Pathspec audit now reports dirty 139" not in markdown
    assert "uncovered dirty paths `0` and uncovered non-evidence source paths `0`" in markdown
    assert "dirty `148`, covered `148`, pathspecs `78`, staged `0`" in markdown
    assert "Basis: current coverage" in markdown


def test_render_markdown_omits_zero_dirty_staging_options(tmp_path: Path) -> None:
    positive = tmp_path / "approve-positive.pathspec"
    zero = tmp_path / "approve-zero.pathspec"
    cleanup = tmp_path / "cleanup-zero.pathspec"
    positive.write_text("workspace/tests/current.py\n", encoding="utf-8")
    zero.write_text(".npmrc\n", encoding="utf-8")
    cleanup.write_text(".tmp/stale.lock\n", encoding="utf-8")
    menu = _menu()
    menu["also_available"] = [
        {
            "token": "APPROVE_POSITIVE_SCOPE",
            "pathspec": str(positive),
            "classification": "verified_existing_packet",
            "reason": "Current dirty staging packet.",
        },
        {
            "token": "APPROVE_ZERO_SCOPE",
            "pathspec": str(zero),
            "classification": "verified_existing_packet",
            "reason": "Stale staging packet.",
        },
        {
            "token": "APPROVE_TMP_CLEANUP",
            "pathspec": str(cleanup),
            "classification": "cleanup_packet_blocked_until_safe_not_staging",
            "reason": "Cleanup packet remains visible.",
        },
    ]
    handoff = {
        "dirty_signature": {
            "input": {
                "dirty_paths": [
                    "workspace/tests/current.py",
                    ".tmp/stale.lock",
                ],
            },
        },
    }

    markdown = scoped_authorization_menu.render_markdown(menu, {}, handoff, tmp_path)

    assert "`APPROVE_POSITIVE_SCOPE`" in markdown
    assert "`APPROVE_TMP_CLEANUP`" in markdown
    assert "- `APPROVE_ZERO_SCOPE` - Stale staging packet." not in markdown
    assert "Omitted current-zero-dirty staging option(s): `APPROVE_ZERO_SCOPE`." in markdown


def test_write_json_no_bom_ascii_escapes_non_ascii(tmp_path: Path) -> None:
    target = tmp_path / "menu.json"
    scoped_authorization_menu._write_json_no_bom(target, _menu())

    raw = target.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\\ubc15\\uc8fc\\ud638" in raw
    parsed = json.loads(raw.decode("utf-8"))
    assert parsed["recommended"]["token"] == "APPROVE_EXAMPLE"


def test_main_renders_markdown_and_rewrites_menu_json(tmp_path: Path) -> None:
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    output_md = tmp_path / "menu.md"
    menu_json.write_text(json.dumps(_menu(), ensure_ascii=False), encoding="utf-8")
    coverage_json.write_text(
        json.dumps(
            {
                "uncovered_dirty_count": 7,
                "uncovered_non_evidence_source_count": 1,
            }
        ),
        encoding="utf-8",
    )

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--output-md",
            str(output_md),
            "--rewrite-menu-json",
        ]
    )

    assert code == 0
    assert "uncovered dirty paths `7` and uncovered non-evidence source paths `1`" in output_md.read_text(
        encoding="utf-8"
    )
    rewritten = menu_json.read_bytes()
    assert not rewritten.startswith(b"\xef\xbb\xbf")
    assert b"\\ubc15\\uc8fc\\ud638" in rewritten


def test_main_rewrites_one_line_options_without_zero_dirty_staging_tokens(tmp_path: Path, capsys) -> None:
    positive = tmp_path / "approve-positive.pathspec"
    zero = tmp_path / "approve-zero.pathspec"
    cleanup = tmp_path / "cleanup-zero.pathspec"
    positive.write_text("workspace/tests/current.py\n", encoding="utf-8")
    zero.write_text(".npmrc\n", encoding="utf-8")
    cleanup.write_text(".tmp/stale.lock\n", encoding="utf-8")
    menu = _menu()
    menu["one_line_user_options"] = [
        "APPROVE_POSITIVE_SCOPE",
        "APPROVE_ZERO_SCOPE",
        "APPROVE_TMP_CLEANUP",
        "STOP",
    ]
    menu["also_available"] = [
        {
            "token": "APPROVE_POSITIVE_SCOPE",
            "pathspec": str(positive),
            "classification": "verified_existing_packet",
            "reason": "Current dirty staging packet.",
        },
        {
            "token": "APPROVE_ZERO_SCOPE",
            "pathspec": str(zero),
            "classification": "verified_existing_packet",
            "reason": "Stale staging packet.",
        },
        {
            "token": "APPROVE_TMP_CLEANUP",
            "pathspec": str(cleanup),
            "classification": "cleanup_packet_blocked_until_safe_not_staging",
            "reason": "Cleanup packet remains visible.",
        },
    ]
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    handoff_json = tmp_path / "handoff.json"
    output_md = tmp_path / "menu.md"
    menu_json.write_text(json.dumps(menu), encoding="utf-8")
    coverage_json.write_text(json.dumps({}), encoding="utf-8")
    handoff_json.write_text(
        json.dumps(
            {
                "dirty_signature": {
                    "input": {
                        "dirty_paths": [
                            "workspace/tests/current.py",
                            ".tmp/stale.lock",
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--handoff-json",
            str(handoff_json),
            "--output-md",
            str(output_md),
            "--rewrite-menu-json",
            "--json",
        ]
    )

    assert code == 0
    rewritten = json.loads(menu_json.read_text(encoding="utf-8"))
    assert rewritten["one_line_user_options"] == [
        "APPROVE_POSITIVE_SCOPE",
        "APPROVE_TMP_CLEANUP",
        "STOP",
    ]
    markdown = output_md.read_text(encoding="utf-8")
    assert "Omitted current-zero-dirty staging option(s): `APPROVE_ZERO_SCOPE`." in markdown
    summary = json.loads(capsys.readouterr().out)
    assert summary["one_line_options_removed_count"] == 1


def test_main_reports_markdown_atomic_write_failure_without_overwriting(tmp_path: Path, capsys) -> None:
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    output_md = tmp_path / "menu.md"
    output_md.write_text("existing menu\n", encoding="utf-8")
    scoped_authorization_menu._atomic_temp_path(output_md).mkdir()
    menu_json.write_text(json.dumps(_menu()), encoding="utf-8")
    coverage_json.write_text(
        json.dumps(
            {
                "uncovered_dirty_count": 7,
                "uncovered_non_evidence_source_count": 1,
            }
        ),
        encoding="utf-8",
    )

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--output-md",
            str(output_md),
            "--json",
        ]
    )

    assert code == 4
    assert output_md.read_text(encoding="utf-8") == "existing menu\n"
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "write_failed"
    assert summary["write_error_path"] == output_md.as_posix()
    assert summary["write_error"]


def test_main_reports_markdown_parent_write_failure_without_traceback(tmp_path: Path, capsys) -> None:
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    blocked_parent = tmp_path / "blocked-parent"
    output_md = blocked_parent / "menu.md"
    blocked_parent.write_text("blocking file\n", encoding="utf-8")
    menu_json.write_text(json.dumps(_menu()), encoding="utf-8")
    coverage_json.write_text(
        json.dumps(
            {
                "uncovered_dirty_count": 7,
                "uncovered_non_evidence_source_count": 1,
            }
        ),
        encoding="utf-8",
    )

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--output-md",
            str(output_md),
            "--json",
        ]
    )

    assert code == 4
    assert blocked_parent.read_text(encoding="utf-8") == "blocking file\n"
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "write_failed"
    assert summary["write_error_path"] == output_md.as_posix()
    assert "FileExistsError" in summary["write_error"]


def test_main_reports_menu_json_atomic_write_failure_without_overwriting(tmp_path: Path, capsys) -> None:
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    output_md = tmp_path / "menu.md"
    original_menu = json.dumps(_menu(), ensure_ascii=False)
    menu_json.write_text(original_menu, encoding="utf-8")
    output_md.write_text("existing menu\n", encoding="utf-8")
    scoped_authorization_menu._atomic_temp_path(menu_json).mkdir()
    coverage_json.write_text(
        json.dumps(
            {
                "uncovered_dirty_count": 7,
                "uncovered_non_evidence_source_count": 1,
            }
        ),
        encoding="utf-8",
    )

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--output-md",
            str(output_md),
            "--rewrite-menu-json",
            "--json",
        ]
    )

    assert code == 4
    assert menu_json.read_text(encoding="utf-8") == original_menu
    assert output_md.read_text(encoding="utf-8") == "existing menu\n"
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "write_failed"
    assert summary["write_error_path"] == menu_json.as_posix()
    assert summary["write_error"]


def test_main_syncs_recommended_files_from_pathspec(tmp_path: Path, capsys) -> None:
    menu = _menu()
    menu["recommended"]["files"] = ["stale.py"]
    pathspec = tmp_path / "approve-example.pathspec"
    menu["recommended"]["pathspec"] = str(pathspec)
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    output_md = tmp_path / "menu.md"
    pathspec.write_text("fresh.py\nnested\\fresh_test.py\nfresh.py\n", encoding="utf-8")
    menu_json.write_text(json.dumps(menu), encoding="utf-8")
    coverage_json.write_text(
        json.dumps(
            {
                "uncovered_dirty_count": 0,
                "uncovered_non_evidence_source_count": 0,
            }
        ),
        encoding="utf-8",
    )

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--output-md",
            str(output_md),
            "--json",
        ]
    )

    assert code == 0
    markdown = output_md.read_text(encoding="utf-8")
    assert "- `fresh.py`" in markdown
    assert "- `nested/fresh_test.py`" in markdown
    assert "stale.py" not in markdown
    summary = json.loads(capsys.readouterr().out)
    assert summary["pathspec_synced_file_count"] == 2


def test_main_prefers_current_ai_context_handoff_group_over_stale_pathspec(tmp_path: Path, capsys) -> None:
    menu = _menu()
    menu["generated_at"] = "2026-06-11T00:00:00Z"
    menu["recommended"]["token"] = "APPROVE_AI_CONTEXT_RELAY_UPDATE"
    menu["recommended"]["files"] = ["stale-context.md"]
    pathspec = tmp_path / "approve-ai-context.pathspec"
    menu["recommended"]["pathspec"] = str(pathspec)
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    handoff_json = tmp_path / "handoff.json"
    output_md = tmp_path / "menu.md"
    pathspec.write_text(".ai/HANDOFF.md\n.ai/archive/HANDOFF_archive_2026-06-12.md\n", encoding="utf-8")
    menu_json.write_text(json.dumps(menu), encoding="utf-8")
    coverage_json.write_text(
        json.dumps(
            {
                "dirty_count": 452,
                "uncovered_dirty_count": 0,
                "uncovered_non_evidence_source_count": 0,
            }
        ),
        encoding="utf-8",
    )
    handoff_json.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-13T10:35:40Z",
                "inputs": {
                    "product_readiness": {
                        "score": 90,
                        "local_blocker_count": 1,
                        "publish_blocker_count": 1,
                        "external_blocker_count": 1,
                    }
                },
                "dirty_signature": {"input": {"dirty_count": 452}},
                "group_order": [
                    {
                        "key": "ai-context",
                        "paths": [
                            ".ai/HANDOFF.md",
                            ".ai/archive/HANDOFF_archive_2026-06-13.md",
                            ".ai/archive/SESSION_LOG_before_2026-06-05.md",
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--handoff-json",
            str(handoff_json),
            "--output-md",
            str(output_md),
            "--rewrite-menu-json",
            "--json",
        ]
    )

    assert code == 0
    markdown = output_md.read_text(encoding="utf-8")
    assert "Generated: 2026-06-13T10:35:40Z" in markdown
    assert ".ai/archive/HANDOFF_archive_2026-06-13.md" in markdown
    assert ".ai/archive/HANDOFF_archive_2026-06-12.md" not in markdown
    assert "3 .ai relay/context/decision/archive dirty paths only" in markdown
    assert "score 90, local blockers 1, publish blockers 1, external blockers 1" in markdown
    assert "score 92" not in markdown
    rewritten = json.loads(menu_json.read_text(encoding="utf-8"))
    assert rewritten["generated_at"] == "2026-06-13T10:35:40Z"
    assert ".ai/archive/HANDOFF_archive_2026-06-13.md" in rewritten["recommended"]["files"]
    assert rewritten["recommended"]["reason"][0].startswith("Still the least destructive")
    summary = json.loads(capsys.readouterr().out)
    assert summary["pathspec_synced_file_count"] == 2
    assert summary["handoff_synced_file_count"] == 3


def test_check_mode_passes_when_markdown_is_current(tmp_path: Path) -> None:
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    output_md = tmp_path / "menu.md"
    coverage = {
        "uncovered_dirty_count": 2,
        "uncovered_non_evidence_source_count": 0,
    }
    menu_json.write_text(json.dumps(_menu()), encoding="utf-8")
    coverage_json.write_text(json.dumps(coverage), encoding="utf-8")
    output_md.write_text(scoped_authorization_menu.render_markdown(_menu(), coverage), encoding="utf-8")

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--output-md",
            str(output_md),
            "--check",
        ]
    )

    assert code == 0


def test_check_mode_ignores_volatile_generated_timestamp_drift(tmp_path: Path, capsys) -> None:
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    output_md = tmp_path / "menu.md"
    old_menu = _menu()
    old_menu["generated_at"] = "2026-06-11T00:00:00Z"
    new_menu = _menu()
    new_menu["generated_at"] = "2026-06-11T00:01:00Z"
    old_coverage = {
        "dirty_count": 12,
        "covered_dirty_count": 10,
        "uncovered_dirty_count": 2,
        "uncovered_non_evidence_source_count": 0,
        "pathspec_count": 3,
        "staged_count": 0,
        "generated_at": "2026-06-11T00:00:10Z",
    }
    new_coverage = dict(old_coverage)
    new_coverage["generated_at"] = "2026-06-11T00:01:10Z"
    menu_json.write_text(json.dumps(new_menu), encoding="utf-8")
    coverage_json.write_text(json.dumps(new_coverage), encoding="utf-8")
    output_md.write_text(scoped_authorization_menu.render_markdown(old_menu, old_coverage), encoding="utf-8")

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--output-md",
            str(output_md),
            "--check",
            "--json",
        ]
    )

    assert code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "ok"
    assert summary["rendered_matches"] is True
    assert summary["exact_rendered_matches"] is False


def test_check_mode_rejects_stale_coverage_even_when_markdown_matches(tmp_path: Path, capsys) -> None:
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    handoff_json = tmp_path / "handoff.json"
    output_md = tmp_path / "menu.md"
    coverage = {
        "dirty_count": 168,
        "covered_dirty_count": 168,
        "uncovered_dirty_count": 0,
        "uncovered_non_evidence_source_count": 0,
    }
    handoff = {
        "dirty_signature": {
            "input": {
                "dirty_count": 177,
            }
        }
    }
    menu_json.write_text(json.dumps(_menu()), encoding="utf-8")
    coverage_json.write_text(json.dumps(coverage), encoding="utf-8")
    handoff_json.write_text(json.dumps(handoff), encoding="utf-8")
    output_md.write_text(scoped_authorization_menu.render_markdown(_menu(), coverage, handoff), encoding="utf-8")

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--handoff-json",
            str(handoff_json),
            "--output-md",
            str(output_md),
            "--check",
            "--json",
        ]
    )

    assert code == 3
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "stale_coverage"
    assert summary["rendered_matches"] is True
    assert summary["coverage_stale"] is True
    assert summary["coverage_dirty_count"] == 168
    assert summary["current_dirty_count"] == 177
    assert "does not match current handoff dirty count 177" in summary["coverage_staleness_reasons"][0]


def test_root_option_resolves_default_paths_from_workspace_root(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "workspace"
    cwd = tmp_path / "elsewhere"
    evidence_dir = root / ".tmp"
    evidence_dir.mkdir(parents=True)
    cwd.mkdir()
    coverage = {
        "uncovered_dirty_count": 0,
        "uncovered_non_evidence_source_count": 0,
    }
    menu_json = evidence_dir / "next-scoped-authorization-menu-current.json"
    coverage_json = evidence_dir / "authorization-coverage-current.json"
    output_md = evidence_dir / "next-scoped-authorization-menu-current.md"
    menu_json.write_text(json.dumps(_menu()), encoding="utf-8")
    coverage_json.write_text(json.dumps(coverage), encoding="utf-8")
    output_md.write_text(scoped_authorization_menu.render_markdown(_menu(), coverage), encoding="utf-8")

    monkeypatch.chdir(cwd)
    code = scoped_authorization_menu.main(["--root", str(root), "--check", "--json"])

    assert code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["root"] == root.resolve().as_posix()
    assert summary["menu_json"] == menu_json.as_posix()
    assert summary["coverage_json"] == coverage_json.as_posix()
    assert summary["output_md"] == output_md.as_posix()
    assert summary["rendered_matches"] is True


def test_check_mode_reports_drift_without_overwriting(tmp_path: Path, capsys) -> None:
    menu_json = tmp_path / "menu.json"
    coverage_json = tmp_path / "coverage.json"
    output_md = tmp_path / "menu.md"
    menu_json.write_text(json.dumps(_menu()), encoding="utf-8")
    coverage_json.write_text(
        json.dumps(
            {
                "uncovered_dirty_count": 9,
                "uncovered_non_evidence_source_count": 3,
            }
        ),
        encoding="utf-8",
    )
    output_md.write_text("stale menu\n", encoding="utf-8")

    code = scoped_authorization_menu.main(
        [
            "--menu-json",
            str(menu_json),
            "--coverage-json",
            str(coverage_json),
            "--output-md",
            str(output_md),
            "--check",
            "--json",
        ]
    )

    assert code == 2
    assert output_md.read_text(encoding="utf-8") == "stale menu\n"
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "drift"
    assert summary["check"] is True
    assert summary["rendered_matches"] is False
