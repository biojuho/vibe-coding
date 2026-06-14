#!/usr/bin/env python3
"""Render a deterministic scoped authorization menu from JSON evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_MENU_PATH = Path(".tmp/next-scoped-authorization-menu-current.json")
DEFAULT_COVERAGE_PATH = Path(".tmp/authorization-coverage-current.json")
DEFAULT_HANDOFF_PATH = Path(".tmp/scoped-dirty-worktree-handoff-plan-current.json")
DEFAULT_MARKDOWN_PATH = Path(".tmp/next-scoped-authorization-menu-current.md")
UNCOVERED_PATH_DISPLAY_LIMIT = 5
ZERO_DIRTY_STAGING_CLASSIFICATIONS = {"verified_existing_packet"}
_COVERAGE_GENERATED_RE = re.compile(r"(, generated `)[^`]+(`)")


class _OutputWriteFailure(Exception):
    def __init__(self, path: Path, cause: OSError) -> None:
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.path = path
        self.cause = cause


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        try:
            raw = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            raw = path.read_text(encoding="utf-16")
        parsed = json.loads(raw)
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _read_text(path: Path) -> str | None:
    try:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            return path.read_text(encoding="utf-16")
    except (FileNotFoundError, OSError, UnicodeError):
        return None


def _atomic_temp_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.tmp")


def _prepare_text_no_bom(path: Path, text: str) -> Path:
    tmp = _atomic_temp_path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8", newline="\n")
    except OSError:
        try:
            if tmp.is_file() or tmp.is_symlink():
                tmp.unlink()
        except OSError:
            pass
        raise
    return tmp


def _replace_prepared_text(path: Path, tmp: Path) -> None:
    try:
        tmp.replace(path)
    except OSError:
        try:
            if tmp.is_file() or tmp.is_symlink():
                tmp.unlink()
        except OSError:
            pass
        raise


def _write_text_no_bom(path: Path, text: str) -> None:
    tmp = _prepare_text_no_bom(path, text)
    _replace_prepared_text(path, tmp)


def _write_json_no_bom(path: Path, payload: dict[str, Any]) -> None:
    _write_text_no_bom(path, json.dumps(payload, ensure_ascii=True, indent=2) + "\n")


def _write_menu_outputs(
    output_md: Path, markdown: str, menu_json: Path, menu: dict[str, Any], rewrite_menu: bool
) -> None:
    prepared: list[tuple[Path, Path]] = []
    current_path = output_md
    try:
        current_path = output_md
        prepared.append((output_md, _prepare_text_no_bom(output_md, markdown)))
        if rewrite_menu and menu:
            current_path = menu_json
            prepared.append(
                (menu_json, _prepare_text_no_bom(menu_json, json.dumps(menu, ensure_ascii=True, indent=2) + "\n"))
            )
        for path, tmp in prepared:
            current_path = path
            _replace_prepared_text(path, tmp)
    except OSError as exc:
        for _path, tmp in prepared:
            try:
                if tmp.is_file() or tmp.is_symlink():
                    tmp.unlink()
            except OSError:
                pass
        raise _OutputWriteFailure(current_path, exc) from exc


def _resolve_path(root: Path | None, path: Path) -> Path:
    if root is None or path.is_absolute():
        return path
    return root / path


def _read_pathspec(path: Path) -> list[str]:
    try:
        try:
            raw = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            raw = path.read_text(encoding="utf-16")
    except (FileNotFoundError, OSError, UnicodeError):
        return []

    paths: list[str] = []
    seen: set[str] = set()
    for line in raw.splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        normalized = item.replace("\\", "/")
        if normalized not in seen:
            seen.add(normalized)
            paths.append(normalized)
    return paths


def _sync_recommended_files_from_pathspec(menu: dict[str, Any], root: Path | None) -> int:
    recommended = _as_dict(menu.get("recommended"))
    pathspec_value = _str(recommended.get("pathspec"))
    if not pathspec_value:
        return 0

    pathspec = _resolve_path(root, Path(pathspec_value))
    paths = _read_pathspec(pathspec)
    if not paths:
        return 0

    recommended["files"] = paths
    return len(paths)


def _handoff_group_paths(handoff: dict[str, Any], key: str) -> list[str]:
    for group in _as_list(handoff.get("group_order")):
        if not isinstance(group, dict):
            continue
        if _str(group.get("key")) != key:
            continue
        paths: list[str] = []
        seen: set[str] = set()
        for item in _as_list(group.get("paths")):
            path = _str(item).replace("\\", "/")
            if path and path not in seen:
                seen.add(path)
                paths.append(path)
        return paths
    return []


def _sync_recommended_from_handoff(menu: dict[str, Any], handoff: dict[str, Any]) -> int:
    recommended = _as_dict(menu.get("recommended"))
    token = _str(recommended.get("token"))
    if token != "APPROVE_AI_CONTEXT_RELAY_UPDATE":
        return 0

    paths = _handoff_group_paths(handoff, "ai-context")
    if not paths:
        return 0

    recommended["files"] = paths
    generated_at = _str(handoff.get("generated_at"))
    if generated_at:
        menu["generated_at"] = generated_at
    _sync_ai_context_reason_lines(recommended, handoff, len(paths))
    return len(paths)


def _sync_ai_context_reason_lines(recommended: dict[str, Any], handoff: dict[str, Any], path_count: int) -> None:
    current_reason: list[str] = []
    inserted_scope = False
    inserted_readiness = False
    for item in _as_list(recommended.get("reason")):
        text = _str(item)
        if not text:
            continue
        lowered = text.lower()
        if "least destructive source-control scope" in lowered:
            current_reason.append(
                "Still the least destructive source-control scope: "
                f"{path_count} .ai relay/context/decision/archive dirty paths only."
            )
            inserted_scope = True
            continue
        if lowered.startswith("readiness remains blocked"):
            readiness = _as_dict(_as_dict(handoff.get("inputs")).get("product_readiness"))
            score = _int(readiness.get("score"))
            local = _int(readiness.get("local_blocker_count"))
            publish = _int(readiness.get("publish_blocker_count"))
            external = _int(readiness.get("external_blocker_count"))
            current_reason.append(
                "Readiness remains blocked with "
                f"score {score}, local blockers {local}, publish blockers {publish}, external blockers {external}."
            )
            inserted_readiness = True
            continue
        current_reason.append(text)

    if not inserted_scope:
        current_reason.insert(
            0,
            "Still the least destructive source-control scope: "
            f"{path_count} .ai relay/context/decision/archive dirty paths only.",
        )
    if not inserted_readiness:
        readiness = _as_dict(_as_dict(handoff.get("inputs")).get("product_readiness"))
        if readiness:
            current_reason.append(
                "Readiness remains blocked with "
                f"score {_int(readiness.get('score'))}, "
                f"local blockers {_int(readiness.get('local_blocker_count'))}, "
                f"publish blockers {_int(readiness.get('publish_blocker_count'))}, "
                f"external blockers {_int(readiness.get('external_blocker_count'))}."
            )
    recommended["reason"] = current_reason


def _bullet_path(path: Any) -> str:
    return f"- `{_str(path)}`" if _str(path) else "- `unknown`"


def _packet_lines(recommended: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    packet = _str(recommended.get("packet"))
    pathspec = _str(recommended.get("pathspec"))
    if packet:
        lines.append(f"- `{packet}`")
    if pathspec:
        lines.append(f"- `{pathspec}`")
    return lines or ["- `none`"]


def _coverage_line(coverage: dict[str, Any]) -> str:
    dirty = _int(coverage.get("dirty_count"))
    covered_dirty = _int(coverage.get("covered_dirty_count"))
    uncovered_dirty = _int(coverage.get("uncovered_dirty_count"))
    uncovered_source = _int(coverage.get("uncovered_non_evidence_source_count"))
    pathspec_count = _int(coverage.get("pathspec_count"))
    staged_count = _int(coverage.get("staged_count"))
    generated = _str(coverage.get("generated_at"))
    basis = _str(coverage.get("basis"))
    line = (
        "- Authorization coverage now reports uncovered dirty paths "
        f"`{uncovered_dirty}` and uncovered non-evidence source paths `{uncovered_source}` "
        f"(dirty `{dirty}`, covered `{covered_dirty}`, pathspecs `{pathspec_count}`, staged `{staged_count}`"
    )
    if generated:
        line += f", generated `{generated}`"
    line += ")."
    if basis:
        line += f" Basis: {basis}"
    return line


def _uncovered_source_path_lines(coverage: dict[str, Any]) -> list[str]:
    paths = [_str(path).replace("\\", "/") for path in _as_list(coverage.get("uncovered_non_evidence_source_paths"))]
    paths = [path for path in paths if path]
    if not paths:
        return []
    visible = paths[:UNCOVERED_PATH_DISPLAY_LIMIT]
    joined = ", ".join(f"`{path}`" for path in visible)
    line = f"- Uncovered non-evidence source path(s): {joined}"
    omitted = len(paths) - len(visible)
    if omitted > 0:
        line += f" plus {omitted} more"
    line += "."
    return [line]


def _handoff_dirty_count(handoff: dict[str, Any]) -> int | None:
    signature = _as_dict(handoff.get("dirty_signature"))
    signature_input = _as_dict(signature.get("input"))
    if "dirty_count" in signature_input:
        return _int(signature_input.get("dirty_count"))
    if "dirty_count" in handoff:
        return _int(handoff.get("dirty_count"))
    return None


def _coverage_staleness_reasons(coverage: dict[str, Any], handoff: dict[str, Any]) -> list[str]:
    if not coverage or not handoff:
        return []
    current_dirty = _handoff_dirty_count(handoff)
    if current_dirty is None:
        return []
    if "dirty_count" not in coverage:
        return [f"coverage dirty count is missing while current handoff dirty count is {current_dirty}"]
    coverage_dirty = _int(coverage.get("dirty_count"))
    if coverage_dirty != current_dirty:
        return [f"coverage dirty count {coverage_dirty} does not match current handoff dirty count {current_dirty}"]
    return []


def _stale_coverage_lines(coverage: dict[str, Any], handoff: dict[str, Any]) -> list[str]:
    reasons = _coverage_staleness_reasons(coverage, handoff)
    if not reasons:
        return []
    joined = "; ".join(reasons)
    return [f"- Authorization coverage is stale: {joined}. Regenerate coverage before using this menu."]


def _is_stale_coverage_reason(line: str) -> bool:
    normalized = line.strip().lower()
    return normalized.startswith("pathspec audit now reports") or normalized.startswith(
        "authorization coverage now reports"
    )


def _evidence_lines(menu: dict[str, Any], coverage: dict[str, Any], handoff: dict[str, Any] | None = None) -> list[str]:
    recommended = _as_dict(menu.get("recommended"))
    lines = [
        f"- {text}"
        for item in _as_list(recommended.get("reason"))
        if (text := _str(item)) and not _is_stale_coverage_reason(text)
    ]
    lines.extend(_stale_coverage_lines(coverage, _as_dict(handoff)))
    coverage_line = _coverage_line(coverage)
    if coverage_line not in lines:
        lines.append(coverage_line)
    lines.extend(line for line in _uncovered_source_path_lines(coverage) if line not in lines)
    return lines or [coverage_line]


def _handoff_dirty_paths(handoff: dict[str, Any]) -> set[str] | None:
    signature = _as_dict(handoff.get("dirty_signature"))
    signature_input = _as_dict(signature.get("input"))
    paths = _as_list(signature_input.get("dirty_paths"))
    if not paths:
        return None
    return {_str(path).replace("\\", "/") for path in paths if _str(path)}


def _pathspec_dirty_coverage(item: dict[str, Any], root: Path | None, dirty_paths: set[str] | None) -> int | None:
    if not dirty_paths:
        return None
    pathspec_value = _str(item.get("pathspec"))
    if not pathspec_value:
        return None
    pathspec = _resolve_path(root, Path(pathspec_value))
    paths = set(_read_pathspec(pathspec))
    if not paths:
        return None
    return len(paths & dirty_paths)


def _is_zero_dirty_staging_option(item: dict[str, Any], root: Path | None, dirty_paths: set[str] | None) -> bool:
    classification = _str(item.get("classification"))
    if classification not in ZERO_DIRTY_STAGING_CLASSIFICATIONS:
        return False
    coverage = _pathspec_dirty_coverage(item, root, dirty_paths)
    return coverage == 0


def _available_lines(
    menu: dict[str, Any], handoff: dict[str, Any] | None = None, root: Path | None = None
) -> list[str]:
    rows = []
    omitted_zero_dirty: list[str] = []
    dirty_paths = _handoff_dirty_paths(_as_dict(handoff))
    for item in _as_list(menu.get("also_available")):
        if not isinstance(item, dict):
            continue
        token = _str(item.get("token"))
        reason = _str(item.get("reason"))
        if _is_zero_dirty_staging_option(item, root, dirty_paths):
            if token:
                omitted_zero_dirty.append(token)
            continue
        if token and reason:
            rows.append(f"- `{token}` - {reason}")
        elif token:
            rows.append(f"- `{token}`")
    if rows:
        if omitted_zero_dirty:
            joined = ", ".join(f"`{token}`" for token in omitted_zero_dirty)
            rows.append(f"- Omitted current-zero-dirty staging option(s): {joined}.")
        return rows
    options = [_str(item) for item in _as_list(menu.get("one_line_user_options")) if _str(item)]
    return [f"- `{option}`" for option in options] if options else ["- `none`"]


def _sync_one_line_options(menu: dict[str, Any], handoff: dict[str, Any], root: Path | None) -> int:
    options = [_str(item) for item in _as_list(menu.get("one_line_user_options")) if _str(item)]
    if not options:
        return 0

    dirty_paths = _handoff_dirty_paths(handoff)
    option_items: dict[str, dict[str, Any]] = {}
    recommended = _as_dict(menu.get("recommended"))
    recommended_token = _str(recommended.get("token"))
    if recommended_token:
        option_items[recommended_token] = recommended
    for item in _as_list(menu.get("also_available")):
        if not isinstance(item, dict):
            continue
        token = _str(item.get("token"))
        if token:
            option_items[token] = item

    filtered: list[str] = []
    seen: set[str] = set()
    for option in options:
        if option in seen:
            continue
        item = option_items.get(option)
        if item is not None and _is_zero_dirty_staging_option(item, root, dirty_paths):
            continue
        seen.add(option)
        filtered.append(option)

    if filtered != options:
        menu["one_line_user_options"] = filtered
    return len(options) - len(filtered)


def _normalize_markdown_for_check(text: str | None) -> str:
    if text is None:
        return ""
    normalized_lines: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith("Generated: "):
            normalized_lines.append("Generated: <volatile>")
            continue
        normalized_lines.append(_COVERAGE_GENERATED_RE.sub(r"\1<volatile>\2", line))
    return "\n".join(normalized_lines)


def _markdown_matches_for_check(current: str | None, rendered: str) -> bool:
    return _normalize_markdown_for_check(current) == _normalize_markdown_for_check(rendered)


def render_markdown(
    menu: dict[str, Any],
    coverage: dict[str, Any],
    handoff: dict[str, Any] | None = None,
    root: Path | None = None,
) -> str:
    recommended = _as_dict(menu.get("recommended"))
    token = _str(recommended.get("token")) or "NONE"
    generated = _str(menu.get("generated_at")) or _str(menu.get("generated")) or "unknown"
    files = _as_list(recommended.get("files"))

    lines = [
        "# Next Scoped Authorization Menu",
        "",
        f"Generated: {generated}",
        "",
        "## Recommended",
        "",
        token,
        "",
        "## Scope",
        "",
    ]
    lines.extend(_bullet_path(path) for path in files)
    if not files:
        lines.append("- `none`")
    lines.extend(["", "## Packet", ""])
    lines.extend(_packet_lines(recommended))
    lines.extend(["", "## Evidence", ""])
    lines.extend(_evidence_lines(menu, coverage, handoff))
    lines.extend(["", "## Also Available", ""])
    lines.extend(_available_lines(menu, handoff, root))
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        help="Workspace root for default and relative menu, coverage, and Markdown paths.",
    )
    parser.add_argument("--menu-json", type=Path, default=DEFAULT_MENU_PATH)
    parser.add_argument("--coverage-json", type=Path, default=DEFAULT_COVERAGE_PATH)
    parser.add_argument("--handoff-json", type=Path)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--rewrite-menu-json", action="store_true")
    parser.add_argument("--check", action="store_true", help="Exit nonzero if rendered Markdown is not current.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve() if args.root is not None else None
    menu_json = _resolve_path(root, args.menu_json)
    coverage_json = _resolve_path(root, args.coverage_json)
    default_evidence_paths = args.menu_json == DEFAULT_MENU_PATH and args.coverage_json == DEFAULT_COVERAGE_PATH
    handoff_path = args.handoff_json or (DEFAULT_HANDOFF_PATH if default_evidence_paths else None)
    handoff_json = _resolve_path(root, handoff_path) if handoff_path is not None else None
    output_md = _resolve_path(root, args.output_md)
    menu = _load_json(menu_json)
    coverage = _load_json(coverage_json)
    handoff = _load_json(handoff_json) if handoff_json is not None else {}
    pathspec_synced_file_count = _sync_recommended_files_from_pathspec(menu, root) if menu else 0
    handoff_synced_file_count = _sync_recommended_from_handoff(menu, handoff) if menu and handoff else 0
    one_line_options_removed_count = _sync_one_line_options(menu, handoff, root) if menu else 0
    staleness_reasons = _coverage_staleness_reasons(coverage, handoff)
    markdown = render_markdown(menu, coverage, handoff, root)
    rendered_matches = False
    exact_rendered_matches = False
    write_error = ""
    write_error_path = ""
    if args.check:
        current_markdown = _read_text(output_md)
        exact_rendered_matches = current_markdown == markdown
        rendered_matches = _markdown_matches_for_check(current_markdown, markdown)
    else:
        try:
            _write_menu_outputs(output_md, markdown, menu_json, menu, args.rewrite_menu_json)
        except _OutputWriteFailure as exc:
            write_error = str(exc)
            write_error_path = exc.path.as_posix()

    status = "ok" if menu else "menu_unavailable"
    if write_error:
        status = "write_failed"
    elif staleness_reasons:
        status = "stale_coverage"
    elif args.check and menu and not rendered_matches:
        status = "drift"

    summary = {
        "status": status,
        "root": root.as_posix() if root is not None else "",
        "menu_json": menu_json.as_posix(),
        "coverage_json": coverage_json.as_posix(),
        "handoff_json": handoff_json.as_posix() if handoff_json is not None else "",
        "output_md": output_md.as_posix(),
        "check": bool(args.check),
        "rendered_matches": rendered_matches if args.check else None,
        "exact_rendered_matches": exact_rendered_matches if args.check else None,
        "recommended": _str(_as_dict(menu.get("recommended")).get("token")) if menu else "",
        "pathspec_synced_file_count": pathspec_synced_file_count,
        "handoff_synced_file_count": handoff_synced_file_count,
        "one_line_options_removed_count": one_line_options_removed_count,
        "uncovered_dirty_count": _int(coverage.get("uncovered_dirty_count")),
        "uncovered_non_evidence_source_count": _int(coverage.get("uncovered_non_evidence_source_count")),
        "coverage_stale": bool(staleness_reasons),
        "coverage_staleness_reasons": staleness_reasons,
        "coverage_dirty_count": _int(coverage.get("dirty_count")),
        "current_dirty_count": _handoff_dirty_count(handoff),
        "write_error": write_error,
        "write_error_path": write_error_path,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=True, indent=2))
    if write_error:
        return 4
    if not menu:
        return 1
    if staleness_reasons:
        return 3
    return 2 if args.check and not rendered_matches else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
