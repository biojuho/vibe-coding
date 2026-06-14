#!/usr/bin/env python3
"""Render LLM Wiki release evidence as a GitHub Actions reviewer summary."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PACKET_PATH = Path(".tmp/release-authorization-packet.json")
DEFAULT_OUTPUT_PATH = Path(".tmp/llm-wiki-release-summary.md")
DEFAULT_ARTIFACT_NAME = "llm-wiki-release-evidence"
UPLOAD_ARTIFACT_ACTION = "actions/upload-artifact@v7"


class _WriteFailure(RuntimeError):
    def __init__(self, path: Path, error: BaseException | str) -> None:
        message = f"{type(error).__name__}: {error}" if isinstance(error, BaseException) else error
        super().__init__(message)
        self.path = path
        self.message = message


@dataclass(frozen=True)
class _PreparedCopy:
    source: Path
    target: Path
    temp: Path
    rel_target: str


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _display(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None or value == "":
        return "unknown"
    return str(value).replace("\n", " ").strip()


def _checkbox(passed: bool) -> str:
    return "[x]" if passed else "[ ]"


def _resolve(root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else root / path


def _rel(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _cleanup_temp(path: Path) -> None:
    try:
        if path.is_file() or path.is_symlink():
            path.unlink()
    except OSError:
        pass


def _write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f"{path.name}.refresh-tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8", newline="\n")
        tmp.replace(path)
    except OSError as exc:
        _cleanup_temp(tmp)
        raise _WriteFailure(path, exc) from exc


def _prepare_copy(root: Path, source: Path, target: Path) -> _PreparedCopy:
    tmp = target.with_name(f"{target.name}.refresh-tmp")
    try:
        if tmp.exists() or tmp.is_symlink():
            if tmp.is_dir() and not tmp.is_symlink():
                raise IsADirectoryError(tmp)
            tmp.unlink()
        shutil.copyfile(source, tmp)
    except OSError as exc:
        _cleanup_temp(tmp)
        raise _WriteFailure(target, exc) from exc
    return _PreparedCopy(source=source, target=target, temp=tmp, rel_target=_rel(root, target))


def _commit_prepared_copies(prepared: list[_PreparedCopy]) -> list[str]:
    copied: list[str] = []
    try:
        for item in prepared:
            item.temp.replace(item.target)
            copied.append(item.rel_target)
    except OSError as exc:
        for pending in prepared:
            _cleanup_temp(pending.temp)
        raise _WriteFailure(item.target, exc) from exc
    return copied


def _append_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except OSError as exc:
        raise _WriteFailure(path, exc) from exc


def _hidden_path_risk(path: str) -> bool:
    return any(part.startswith(".") and part not in {".", ".."} for part in Path(path).parts)


def _build_checks(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "label": "strict evidence artifact is available",
            "passed": evidence.get("available") is True,
        },
        {
            "label": "strict release gate status is pass",
            "passed": evidence.get("status") == "pass",
        },
        {
            "label": "evidence HEAD matches the current packet HEAD",
            "passed": evidence.get("head_matches_current") is True,
        },
        {
            "label": "unexpected manifest warning count is zero",
            "passed": _int(evidence.get("unexpected_manifest_warning_count")) == 0,
        },
        {
            "label": "source inventory count is present",
            "passed": _int(evidence.get("source_inventory_count")) > 0,
        },
    ]


def _artifact_paths(
    root: Path,
    *,
    output_path: Path,
    artifact_dir: Path | None,
    evidence_path: str,
) -> dict[str, Any]:
    raw_source = _resolve(root, Path(evidence_path)) if evidence_path else None
    if artifact_dir is None:
        return {
            "prepared": False,
            "directory": None,
            "summary_path": _rel(root, output_path),
            "evidence_path": evidence_path,
            "hidden_path_risk": _hidden_path_risk(evidence_path),
            "copied": [],
        }

    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _WriteFailure(artifact_dir, exc) from exc
    summary_target = artifact_dir / "llm-wiki-release-summary.md"
    evidence_target = artifact_dir / "llm-wiki-strict-audit-current.json"
    prepared: list[_PreparedCopy] = []

    try:
        if output_path.exists() and output_path.resolve() != summary_target.resolve():
            prepared.append(_prepare_copy(root, output_path, summary_target))
        if raw_source and raw_source.exists():
            if raw_source.resolve() != evidence_target.resolve():
                prepared.append(_prepare_copy(root, raw_source, evidence_target))
        copied = _commit_prepared_copies(prepared)
    except _WriteFailure:
        for pending in prepared:
            _cleanup_temp(pending.temp)
        raise
    except OSError as exc:
        for pending in prepared:
            _cleanup_temp(pending.temp)
        raise _WriteFailure(artifact_dir, exc) from exc

    rel_dir = _rel(root, artifact_dir)
    return {
        "prepared": True,
        "directory": rel_dir,
        "summary_path": _rel(root, summary_target),
        "evidence_path": _rel(root, evidence_target),
        "hidden_path_risk": _hidden_path_risk(rel_dir),
        "copied": copied,
    }


def _preflight_artifact_dir(artifact_dir: Path) -> None:
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _WriteFailure(artifact_dir, exc) from exc


def build_summary(
    packet: dict[str, Any],
    *,
    root: Path,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    evidence = _as_dict(packet.get("llm_wiki_strict_evidence"))
    summary = _as_dict(packet.get("summary"))
    blockers = [str(blocker) for blocker in _as_list(packet.get("blockers")) if str(blocker).strip()]
    checks = _build_checks(evidence)
    status = "pass" if all(check["passed"] for check in checks) else "fail"
    evidence_path = str(evidence.get("path") or evidence.get("artifact_path") or "")

    lines = [
        "# LLM Wiki Release Evidence",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Packet status | `{_display(packet.get('status'))}` |",
        f"| Branch | `{_display(summary.get('branch'))}` |",
        f"| HEAD | `{_display(summary.get('head_short') or summary.get('head'))}` |",
        f"| Strict evidence status | `{_display(evidence.get('status'))}` |",
        f"| Evidence HEAD matches current | `{_display(evidence.get('head_matches_current'))}` |",
        f"| Unexpected manifest warnings | `{_display(evidence.get('unexpected_manifest_warning_count'))}` |",
        f"| Accepted known manifest warnings | `{_display(evidence.get('accepted_manifest_warning_count'))}` |",
        f"| Source inventory count | `{_display(evidence.get('source_inventory_count'))}` |",
        f"| Evidence artifact | `{_display(evidence_path)}` |",
        f"| Generated at | `{_display(evidence.get('generated_at'))}` |",
        f"| Reproduce command | `{_display(evidence.get('command'))}` |",
        "",
        "## Reviewer Checklist",
        "",
    ]
    lines.extend(f"- {_checkbox(bool(check['passed']))} {check['label']}" for check in checks)
    lines.extend(
        [
            "",
            "## Release Packet Context",
            "",
            f"- Packet blockers: {_display('; '.join(blockers) if blockers else 'none')}",
            "- This summary validates the LLM Wiki gate only; unrelated dirty worktree, publish, or external blockers",
            "  remain governed by the release authorization packet.",
            "",
            "## Artifact Upload Guidance",
            "",
            "Use a non-hidden artifact directory for GitHub uploads. The raw strict evidence currently lives under",
            "`.tmp/`, and current upload-artifact defaults ignore hidden files and files inside dot-prefixed folders.",
            "",
            "```yaml",
            "- name: Render LLM Wiki release summary",
            "  run: >",
            "    py -3.13 .agents/skills/auto-research/scripts/llm_wiki_release_summary.py",
            "    --root .",
            "    --packet .tmp/release-authorization-packet.json",
            "    --output .tmp/llm-wiki-release-summary.md",
            "    --artifact-dir release-evidence/llm-wiki",
            f"- uses: {UPLOAD_ARTIFACT_ACTION}",
            "  with:",
            f"    name: {DEFAULT_ARTIFACT_NAME}",
            "    path: release-evidence/llm-wiki",
            "    if-no-files-found: error",
            "    retention-days: 30",
            "```",
            "",
        ]
    )
    markdown = "\n".join(lines)

    artifact = _artifact_paths(
        root,
        output_path=output_path,
        artifact_dir=artifact_dir,
        evidence_path=evidence_path,
    )
    artifact["action"] = UPLOAD_ARTIFACT_ACTION
    artifact["name"] = DEFAULT_ARTIFACT_NAME

    return {
        "status": status,
        "packet_status": str(packet.get("status") or "unknown"),
        "checks": checks,
        "artifact_upload": artifact,
        "summary_markdown": markdown,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--github-step-summary", type=Path)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--strict", action="store_true", help="Exit 1 when the LLM Wiki checklist is not passing.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    packet_path = _resolve(root, args.packet)
    output_path = _resolve(root, args.output)
    artifact_dir = _resolve(root, args.artifact_dir)
    step_summary = _resolve(root, args.github_step_summary)
    if step_summary is None and os.environ.get("GITHUB_STEP_SUMMARY"):
        step_summary = Path(os.environ["GITHUB_STEP_SUMMARY"])

    packet = _load_json(packet_path or root / DEFAULT_PACKET_PATH)
    if output_path is None:
        output_path = root / DEFAULT_OUTPUT_PATH

    result = build_summary(packet, root=root, output_path=output_path, artifact_dir=None)
    try:
        if artifact_dir is not None:
            _preflight_artifact_dir(artifact_dir)
        _write_text_atomic(output_path, result["summary_markdown"] + "\n")

        if artifact_dir is not None:
            result = build_summary(packet, root=root, output_path=output_path, artifact_dir=artifact_dir)

        step_summary_result = {"appended": False, "path": _rel(root, step_summary) if step_summary else None}
        if step_summary is not None:
            _append_text(step_summary, result["summary_markdown"] + "\n")
            step_summary_result["appended"] = True
    except _WriteFailure as exc:
        result["status"] = "write_failed"
        result["write_error"] = exc.message
        result["write_error_path"] = _rel(root, exc.path)
        result.pop("summary_markdown", None)
        text = json.dumps(result, ensure_ascii=True, indent=2)
        if args.json:
            print(text)
        else:
            print(f"write_failed: {_rel(root, exc.path)}: {exc.message}")
        return 4
    result["output"] = _rel(root, output_path)
    result["github_step_summary"] = step_summary_result
    result["write_error"] = ""
    result["write_error_path"] = ""
    result.pop("summary_markdown", None)

    text = json.dumps(result, ensure_ascii=True, indent=2)
    if args.json:
        print(text)
    else:
        print((output_path).read_text(encoding="utf-8"))
    return 1 if args.strict and result["status"] != "pass" else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
