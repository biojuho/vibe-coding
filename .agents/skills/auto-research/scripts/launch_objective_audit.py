#!/usr/bin/env python3
"""Build a launch-objective completion audit manifest from current evidence."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_OBJECTIVE = (
    "Product launch evidence covers direct target product readiness, auto-research self-improvement loop, "
    "GitHub project inventory, browser-click QA, A/B adoption, current-code triage, current-head release "
    "authorization, and launch readiness gates."
)
SKILL_ARTIFACTS = (
    ".agents/skills/auto-research/SKILL.md",
    ".agents/skills/auto-research/scripts/ab_decision.py",
    ".agents/skills/auto-research/scripts/browser_qa_inventory.py",
    ".agents/skills/auto-research/scripts/completion_audit.py",
    ".agents/skills/auto-research/scripts/dependency_freshness_inventory.py",
    ".agents/skills/auto-research/scripts/github_project_inventory.py",
    ".agents/skills/auto-research/scripts/launch_objective_audit.py",
    ".agents/skills/auto-research/scripts/next_experiment_selector.py",
    ".agents/skills/auto-research/scripts/release_authorization_packet.py",
)
AI_RELAY_ARTIFACTS = (
    ".ai/HANDOFF.md",
    ".ai/TASKS.md",
    ".ai/SESSION_LOG.md",
    ".ai/CONTEXT.md",
    ".ai/GOAL.md",
)
QUALITY_OBJECTIVE_ARTIFACTS = (
    ".ai/PROJECTS.md",
    ".ai/HANDOFF.md",
    ".ai/TASKS.md",
    ".ai/CONTEXT.md",
    "projects/blind-to-x/docs/output_quality_selection_gate_2026-06-07.md",
)
QUALITY_TARGET_PROJECTS = (
    "blind-to-x",
    "shorts-maker-v2",
    "hanwoo-dashboard",
    "knowledge-dashboard",
)
QUALITY_EXTERNAL_BENCHMARK_TERMS = (
    "external output bar",
    "buffer",
    "typefully",
    "hypefury",
    "w3c",
    "streamlit",
    "youtube",
    "x official",
)
QUALITY_ITERATION_TERMS = (
    "a/b",
    "adopt_candidate",
    "baseline",
    "candidate",
    "browser qa",
)
AB_MANIFEST_GLOB = "ab-manifest-*.json"
TASK_ID_RE = re.compile(r"\b[Tt][-_]?(\d{3,6})\b")
GOAL_STATUS_RE = re.compile(r"^-\s*Status:\s*(.*?)\s*$", re.IGNORECASE | re.MULTILINE)
MARKDOWN_CHECKBOX_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s+(.*)$")
GRAPH_RELEVANT_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".svelte",
    ".vue",
    ".sh",
    ".bash",
    ".ps1",
    ".bat",
    ".cmd",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
}
GRAPH_RELEVANT_FILENAMES = {"Dockerfile", "Makefile", "commit-msg", "pre-commit"}
GOAL_ACTIVE_STATUSES = {"active", "enabled", "in_progress", "in-progress", "blocked", "waiting"}
DEFAULT_INVENTORY_CACHE_MAX_AGE_SECONDS = 6 * 60 * 60
RECENT_INVENTORY_FALLBACKS = {
    "browser_inventory": ".tmp/browser-qa-inventory.json",
}
GOAL_OBJECTIVE_TERMS = (
    "auto-research",
    "product launch",
    "launch-ready",
    "제품출시",
    "제품 출시",
    "오토리서치",
)


def _exists(root: Path, rel_path: str) -> bool:
    return (root / rel_path).exists()


def _read_text(root: Path, rel_path: str) -> str:
    try:
        return (root / rel_path).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _recent_json_result(
    root: Path,
    *,
    label: str,
    rel_path: str,
    failed_result: dict[str, Any],
    max_age_seconds: int = DEFAULT_INVENTORY_CACHE_MAX_AGE_SECONDS,
) -> dict[str, Any] | None:
    path = root / rel_path
    try:
        age_seconds = time.time() - path.stat().st_mtime
    except (FileNotFoundError, OSError):
        return None
    if age_seconds < 0:
        age_seconds = 0
    if age_seconds > max_age_seconds:
        return None
    data = _load_json_object(path)
    if data is None:
        return None
    stderr = str(failed_result.get("stderr") or "").strip()
    detail = f"used recent {rel_path} after live {label} helper was unavailable"
    if stderr:
        detail = f"{detail}: {stderr}"
    return {
        "available": True,
        "returncode": 0,
        "stdout": json.dumps(data, ensure_ascii=True),
        "stderr": detail,
        "data": data,
        "fallback_path": rel_path,
        "fallback_age_seconds": int(age_seconds),
    }


def _with_recent_inventory_fallback(root: Path, label: str, result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if result.get("available") is True and data:
        return result
    rel_path = RECENT_INVENTORY_FALLBACKS.get(label)
    if not rel_path:
        return result
    fallback = _recent_json_result(root, label=label, rel_path=rel_path, failed_result=result)
    return fallback or result


def _ab_manifest_sort_key(path: Path) -> tuple[int, str] | None:
    try:
        return path.stat().st_mtime_ns, path.name
    except OSError:
        return None


def _ab_manifest_task_id(path: Path, manifest: dict[str, Any]) -> int | None:
    texts = [path.name, path.stem]
    for key in ("experiment", "task_id", "id"):
        value = manifest.get(key)
        if value is not None:
            texts.append(str(value))

    for text in texts:
        match = TASK_ID_RE.search(text)
        if match:
            return int(match.group(1))
    return None


def _run_json(root: Path, args: list[str], timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(root),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "data": {},
        }
    stdout = completed.stdout.strip()
    data: dict[str, Any] = {}
    available = completed.returncode == 0
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            available = False
            data = {"parse_error": str(exc)}
        else:
            if isinstance(parsed, dict):
                data = parsed
            else:
                available = False
                data = {"parse_error": "JSON root was not an object"}
    return {
        "available": available,
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": completed.stderr.strip(),
        "data": data,
    }


def _run_text(root: Path, args: list[str], timeout: int = 15) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(root),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False, ""
    if completed.returncode != 0:
        return False, completed.stderr.strip()
    return True, completed.stdout.strip()


def _is_graph_relevant_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip()
    path_obj = Path(normalized)
    return path_obj.name in GRAPH_RELEVANT_FILENAMES or path_obj.suffix.lower() in GRAPH_RELEVANT_SUFFIXES


def _graph_relevant_files_between(root: Path, base_sha: str, head_sha: str) -> list[str] | None:
    if not base_sha or not head_sha or base_sha == head_sha:
        return []
    ok, output = _run_text(root, ["git", "diff", "--name-only", f"{base_sha}..{head_sha}"])
    if not ok:
        return None
    return [path for path in output.splitlines() if path.strip() and _is_graph_relevant_path(path)]


def _select_next_experiment_from_inputs(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    selector_path = Path(__file__).with_name("next_experiment_selector.py")
    spec = importlib.util.spec_from_file_location("auto_research_next_experiment_selector", selector_path)
    if spec is None or spec.loader is None:
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"Could not load next_experiment_selector.py from {selector_path}",
            "data": {},
        }

    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        selection = module.select_next_experiment(
            readiness=inputs["readiness"]["data"],
            github_inventory=inputs["github_inventory"]["data"],
            browser_inventory=inputs["browser_inventory"]["data"],
            dependency_inventory=inputs["dependency_inventory"]["data"],
        )
    except Exception as exc:  # pragma: no cover - defensive CLI error path
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "data": {},
        }

    return {
        "available": True,
        "returncode": 0,
        "stdout": json.dumps(selection, ensure_ascii=True),
        "stderr": "",
        "data": selection,
    }


def _release_authorization_packet_from_inputs(root: Path, readiness: dict[str, Any]) -> dict[str, Any]:
    packet_path = Path(__file__).with_name("release_authorization_packet.py")
    spec = importlib.util.spec_from_file_location("auto_research_release_authorization_packet", packet_path)
    if spec is None or spec.loader is None:
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"Could not load release_authorization_packet.py from {packet_path}",
            "data": {},
        }

    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        packet = module.build_packet(root, readiness=readiness)
    except Exception as exc:  # pragma: no cover - defensive CLI error path
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "data": {},
        }

    return {
        "available": True,
        "returncode": 0,
        "stdout": json.dumps(packet, ensure_ascii=True),
        "stderr": "",
        "data": packet,
    }


def _code_review_gate_from_inputs(root: Path, timeout: int) -> dict[str, Any]:
    commands = [[sys.executable, "execution/code_review_gate.py", "--base", "HEAD~1", "--json"]]
    if sys.platform == "win32":
        commands.append(["py", "-3.13", "execution/code_review_gate.py", "--base", "HEAD~1", "--json"])

    last_result: dict[str, Any] | None = None
    for command in commands:
        result = _run_json(root, command, timeout)
        last_result = result
        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        error = str(data.get("error") or result.get("stderr") or "")
        if data.get("status") == "error" and "not importable" in error:
            continue
        return result

    return last_result or {
        "available": False,
        "returncode": None,
        "stdout": "",
        "stderr": "code_review_gate.py could not run",
        "data": {},
    }


def _item(
    requirement: str,
    artifacts: list[str],
    evidence: list[str],
    *,
    complete: bool,
    blockers: list[str] | None = None,
    verified: bool = True,
    coverage: str | None = None,
) -> dict[str, Any]:
    return {
        "requirement": requirement,
        "artifacts": artifacts,
        "evidence": evidence,
        "verified": verified,
        "coverage": coverage if coverage is not None else ("complete" if complete else "partial"),
        "blockers": blockers or [],
    }


def _evidence_sentence(label: str, value: Any) -> str:
    text = str(value or "unknown").strip() or "unknown"
    suffix = "" if text.endswith((".", "!", "?")) else "."
    return f"{label}: {text}{suffix}"


def _sentence_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    sentences: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        suffix = "" if text.endswith((".", "!", "?")) else "."
        sentences.append(f"{text}{suffix}")
    return sentences


def _found_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    text_lower = text.lower()
    return [term for term in terms if term.lower() in text_lower]


def _quality_objective_item(root: Path) -> dict[str, Any]:
    project_dashboard = _read_text(root, ".ai/PROJECTS.md")
    combined_text = "\n".join(_read_text(root, rel_path) for rel_path in QUALITY_OBJECTIVE_ARTIFACTS)
    missing_artifacts = [path for path in QUALITY_OBJECTIVE_ARTIFACTS if not _exists(root, path)]
    missing_project_criteria = [
        project for project in QUALITY_TARGET_PROJECTS if project.lower() not in project_dashboard.lower()
    ]
    quality_marker_count = project_dashboard.count("좋은 output 기준")
    external_terms = _found_terms(combined_text, QUALITY_EXTERNAL_BENCHMARK_TERMS)
    iteration_terms = _found_terms(combined_text, QUALITY_ITERATION_TERMS)
    has_good_bad_output = "good vs bad output" in combined_text.lower() or (
        "good output" in combined_text.lower() and "bad output" in combined_text.lower()
    )

    blockers: list[str] = []
    if missing_artifacts:
        blockers.append("Missing output-quality objective artifact(s): " + ", ".join(missing_artifacts))
    if missing_project_criteria:
        blockers.append("Missing project output-quality criteria for: " + ", ".join(missing_project_criteria))
    if quality_marker_count < len(QUALITY_TARGET_PROJECTS):
        blockers.append(
            "PROJECTS.md has insufficient '좋은 output 기준' sections: "
            f"{quality_marker_count}/{len(QUALITY_TARGET_PROJECTS)}."
        )
    if len(external_terms) < 2:
        blockers.append("External benchmark evidence is too thin for the output-quality objective.")
    if not has_good_bad_output:
        blockers.append("No Good vs Bad output distinction found in objective evidence.")
    if len(iteration_terms) < 3:
        blockers.append("Iterative baseline/candidate/A-B evidence is too thin for the output-quality objective.")

    complete = not blockers
    return _item(
        "Enforce explicit output-quality criteria, external benchmarks, and iterative improvement evidence.",
        list(QUALITY_OBJECTIVE_ARTIFACTS),
        [
            "Project output criteria coverage "
            f"{len(QUALITY_TARGET_PROJECTS) - len(missing_project_criteria)}/{len(QUALITY_TARGET_PROJECTS)}: "
            f"{', '.join(QUALITY_TARGET_PROJECTS)}.",
            f"PROJECTS.md '좋은 output 기준' sections={quality_marker_count}.",
            "External benchmark signals: " + (", ".join(external_terms) if external_terms else "none") + ".",
            f"Good-vs-bad output distinction present={has_good_bad_output}.",
            "Iterative improvement signals: " + (", ".join(iteration_terms) if iteration_terms else "none") + ".",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(project_dashboard or combined_text),
    )


def _markdown_checkbox_summary(root: Path, rel_path: str) -> dict[str, Any]:
    total = 0
    completed = 0
    open_items: list[str] = []
    for line in _read_text(root, rel_path).splitlines():
        match = MARKDOWN_CHECKBOX_RE.match(line)
        if not match:
            continue
        total += 1
        marker = match.group(1).lower()
        text = match.group(2).strip()
        if marker == "x":
            completed += 1
        else:
            open_items.append(text)
    return {
        "total": total,
        "completed": completed,
        "open": total - completed,
        "open_items": open_items,
    }


def _skill_item(root: Path) -> dict[str, Any]:
    missing = [path for path in SKILL_ARTIFACTS if not _exists(root, path)]
    skill_text = _read_text(root, ".agents/skills/auto-research/SKILL.md").lower()
    required_terms = (
        "ab_decision.py",
        "browser_qa_inventory.py",
        "completion_audit.py",
        "dependency_freshness_inventory.py",
        "github_project_inventory.py",
        "launch_objective_audit.py",
        "next_experiment_selector.py",
        "release_authorization_packet.py",
    )
    missing_terms = [term for term in required_terms if term not in skill_text]
    complete = not missing and not missing_terms
    evidence = [
        f"{len(SKILL_ARTIFACTS) - len(missing)}/{len(SKILL_ARTIFACTS)} required auto-research artifacts exist.",
        "SKILL.md documents A/B, completion audit, next experiment selector, launch objective audit, "
        "GitHub inventory, browser QA inventory, dependency freshness, and release authorization packet commands."
        if not missing_terms
        else "SKILL.md is missing documented command reference(s): " + ", ".join(missing_terms),
    ]
    blockers = []
    if missing:
        blockers.append("Missing auto-research artifact(s): " + ", ".join(missing))
    if missing_terms:
        blockers.append("Missing SKILL.md command reference(s): " + ", ".join(missing_terms))
    return _item(
        "Create and document the Karpathy-style auto-research self-improvement skill.",
        list(SKILL_ARTIFACTS),
        evidence,
        complete=complete,
        blockers=blockers,
    )


def _github_item(github_inventory: dict[str, Any]) -> dict[str, Any]:
    git = github_inventory.get("git") if isinstance(github_inventory.get("git"), dict) else {}
    open_prs = github_inventory.get("open_prs") if isinstance(github_inventory.get("open_prs"), dict) else {}
    projects = github_inventory.get("projects") if isinstance(github_inventory.get("projects"), list) else []
    workflows = github_inventory.get("workflows") if isinstance(github_inventory.get("workflows"), list) else []
    recommendations = github_inventory.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []
    open_pr_count = open_prs.get("count")
    open_pr_available = open_prs.get("available") is True
    dirty_count = git.get("dirty_count")
    complete = bool(projects) and open_pr_available and open_pr_count == 0 and dirty_count == 0 and not recommendations
    blockers: list[str] = []
    if not projects:
        blockers.append("No GitHub/local projects were discovered.")
    if not open_pr_available:
        blockers.append("Open PR inventory is unavailable.")
    elif open_pr_count:
        blockers.append(f"{open_pr_count} open PR(s) remain.")
    if dirty_count:
        blockers.append(f"Git inventory reports dirty_count={dirty_count}.")
    blockers.extend(str(item) for item in recommendations)
    return _item(
        "Find GitHub-related projects and PR/workflow surfaces before choosing improvements.",
        [".github/workflows", ".github/dependabot.yml", "projects"],
        [
            f"github_project_inventory discovered {len(projects)} project(s) and {len(workflows)} workflow file(s).",
            f"open_prs.available={open_pr_available}, open_prs.count={open_pr_count}.",
            f"git.dirty_count={dirty_count}.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(github_inventory),
    )


def _target_blind_to_x_item(readiness: dict[str, Any]) -> dict[str, Any]:
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    target: dict[str, Any] | None = None
    for project in projects:
        if not isinstance(project, dict):
            continue
        if (
            project.get("name") == "blind-to-x"
            or str(project.get("path") or "").replace("\\", "/") == "projects/blind-to-x"
        ):
            target = project
            break

    artifacts = [
        "projects/blind-to-x",
        "projects/blind-to-x/README.md",
        "projects/blind-to-x/config.example.yaml",
        "projects/blind-to-x/docs/ops-runbook.md",
        "execution/product_readiness_score.py",
        ".tmp/project_qc_runner_latest.json",
    ]
    if target is None:
        return _item(
            "Prove blind-to-x target product launch readiness with direct project evidence.",
            artifacts,
            ["product_readiness_score did not include a blind-to-x project entry."],
            complete=False,
            blockers=["blind-to-x readiness evidence is missing from product_readiness_score output."],
            verified=bool(readiness),
        )

    qc = target.get("qc") if isinstance(target.get("qc"), dict) else {}
    docs = target.get("docs") if isinstance(target.get("docs"), list) else []
    env = target.get("env") if isinstance(target.get("env"), dict) else {}
    env_checks = env.get("checks") if isinstance(env.get("checks"), list) else []
    tasks = target.get("tasks") if isinstance(target.get("tasks"), list) else []
    dirty_paths = target.get("dirty_paths") if isinstance(target.get("dirty_paths"), list) else []

    score = int(target.get("score") or 0)
    state = str(target.get("state") or "unknown")
    qc_status = str(qc.get("status") or "unknown")
    qc_failed = int(qc.get("failed") or 0)
    qc_stale = qc.get("stale") is True
    present_docs = [str(doc.get("path") or "unknown") for doc in docs if isinstance(doc, dict) and doc.get("present")]
    missing_docs = [
        str(doc.get("path") or "unknown") for doc in docs if isinstance(doc, dict) and not doc.get("present")
    ]
    env_ok_count = sum(1 for check in env_checks if isinstance(check, dict) and check.get("ok") is True)
    env_check_count = len([check for check in env_checks if isinstance(check, dict)])
    env_names = [
        str(check.get("name") or "unknown")
        for check in env_checks
        if isinstance(check, dict) and check.get("ok") is True
    ]

    complete = (
        score >= 100
        and state == "ready"
        and qc_status == "PASS"
        and qc_failed == 0
        and not qc_stale
        and not missing_docs
        and bool(present_docs)
        and env_check_count > 0
        and env_ok_count == env_check_count
        and not tasks
        and not dirty_paths
    )
    blockers: list[str] = []
    if score < 100 or state != "ready":
        blockers.append(f"blind-to-x readiness is score={score}, state={state}; expected score>=100 and ready.")
    if qc_status != "PASS" or qc_failed or qc_stale:
        blockers.append(f"blind-to-x QC is status={qc_status}, failed={qc_failed}, stale={qc_stale}.")
    if missing_docs:
        blockers.append("Missing blind-to-x launch doc artifact(s): " + ", ".join(missing_docs))
    if not present_docs:
        blockers.append("No blind-to-x launch doc artifacts were reported present.")
    if env_check_count == 0 or env_ok_count != env_check_count:
        blockers.append(f"blind-to-x env checks ok {env_ok_count}/{env_check_count}.")
    if tasks:
        blockers.append(f"blind-to-x has {len(tasks)} unresolved readiness task(s).")
    if dirty_paths:
        blockers.append(f"blind-to-x has {len(dirty_paths)} dirty path(s).")

    return _item(
        "Prove blind-to-x target product launch readiness with direct project evidence.",
        artifacts,
        [
            f"blind-to-x readiness score={score}, state={state}.",
            f"blind-to-x QC status={qc_status}, passed={qc.get('passed')}, failed={qc_failed}, "
            f"skipped={qc.get('skipped')}, stale={qc_stale}.",
            f"blind-to-x docs present {len(present_docs)}/{len(docs)}: {', '.join(present_docs) or 'none'}.",
            f"blind-to-x env checks ok {env_ok_count}/{env_check_count}: {', '.join(env_names) or 'none'}.",
            f"blind-to-x tasks={len(tasks)}, dirty_paths={len(dirty_paths)}.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(readiness),
    )


def _target_shorts_maker_v2_item(root: Path, readiness: dict[str, Any]) -> dict[str, Any]:
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    target: dict[str, Any] | None = None
    for project in projects:
        if not isinstance(project, dict):
            continue
        if (
            project.get("name") == "shorts-maker-v2"
            or str(project.get("path") or "").replace("\\", "/") == "projects/shorts-maker-v2"
        ):
            target = project
            break

    artifacts = [
        "projects/shorts-maker-v2",
        "projects/shorts-maker-v2/README.md",
        "projects/shorts-maker-v2/ARCHITECTURE.md",
        "projects/shorts-maker-v2/CLAUDE.md",
        "projects/shorts-maker-v2/FEATURE.md",
        "projects/shorts-maker-v2/pyproject.toml",
        "execution/product_readiness_score.py",
        ".tmp/project_qc_runner_latest.json",
    ]
    if target is None:
        return _item(
            "Prove shorts-maker-v2 target product launch readiness with direct project evidence.",
            artifacts,
            ["product_readiness_score did not include a shorts-maker-v2 project entry."],
            complete=False,
            blockers=["shorts-maker-v2 readiness evidence is missing from product_readiness_score output."],
            verified=bool(readiness),
        )

    qc = target.get("qc") if isinstance(target.get("qc"), dict) else {}
    docs = target.get("docs") if isinstance(target.get("docs"), list) else []
    env = target.get("env") if isinstance(target.get("env"), dict) else {}
    env_checks = env.get("checks") if isinstance(env.get("checks"), list) else []
    tasks = target.get("tasks") if isinstance(target.get("tasks"), list) else []
    dirty_paths = target.get("dirty_paths") if isinstance(target.get("dirty_paths"), list) else []

    score = int(target.get("score") or 0)
    state = str(target.get("state") or "unknown")
    qc_status = str(qc.get("status") or "unknown")
    qc_failed = int(qc.get("failed") or 0)
    qc_stale = qc.get("stale") is True
    present_docs = [str(doc.get("path") or "unknown") for doc in docs if isinstance(doc, dict) and doc.get("present")]
    missing_docs = [
        str(doc.get("path") or "unknown") for doc in docs if isinstance(doc, dict) and not doc.get("present")
    ]
    env_ok_count = sum(1 for check in env_checks if isinstance(check, dict) and check.get("ok") is True)
    env_check_count = len([check for check in env_checks if isinstance(check, dict)])
    env_names = [
        str(check.get("name") or "unknown")
        for check in env_checks
        if isinstance(check, dict) and check.get("ok") is True
    ]
    feature_checklist = _markdown_checkbox_summary(root, "projects/shorts-maker-v2/FEATURE.md")
    feature_total = int(feature_checklist["total"])
    feature_completed = int(feature_checklist["completed"])
    feature_open = int(feature_checklist["open"])
    feature_open_items = [str(item) for item in feature_checklist["open_items"]]

    complete = (
        score >= 100
        and state == "ready"
        and qc_status == "PASS"
        and qc_failed == 0
        and not qc_stale
        and not missing_docs
        and bool(present_docs)
        and env_check_count > 0
        and env_ok_count == env_check_count
        and not tasks
        and not dirty_paths
        and feature_total > 0
        and feature_open == 0
    )
    blockers: list[str] = []
    if score < 100 or state != "ready":
        blockers.append(f"shorts-maker-v2 readiness is score={score}, state={state}; expected score>=100 and ready.")
    if qc_status != "PASS" or qc_failed or qc_stale:
        blockers.append(f"shorts-maker-v2 QC is status={qc_status}, failed={qc_failed}, stale={qc_stale}.")
    if missing_docs:
        blockers.append("Missing shorts-maker-v2 launch doc artifact(s): " + ", ".join(missing_docs))
    if not present_docs:
        blockers.append("No shorts-maker-v2 launch doc artifacts were reported present.")
    if env_check_count == 0 or env_ok_count != env_check_count:
        blockers.append(f"shorts-maker-v2 env checks ok {env_ok_count}/{env_check_count}.")
    if tasks:
        blockers.append(f"shorts-maker-v2 has {len(tasks)} unresolved readiness task(s).")
    if dirty_paths:
        blockers.append(f"shorts-maker-v2 has {len(dirty_paths)} dirty path(s).")
    if feature_total == 0:
        blockers.append("shorts-maker-v2 FEATURE.md has no acceptance checklist evidence.")
    elif feature_open:
        sample = "; ".join(feature_open_items[:3])
        suffix = f": {sample}" if sample else "."
        blockers.append(f"shorts-maker-v2 FEATURE.md has {feature_open} open acceptance checklist item(s){suffix}")

    return _item(
        "Prove shorts-maker-v2 target product launch readiness with direct project evidence.",
        artifacts,
        [
            f"shorts-maker-v2 readiness score={score}, state={state}.",
            f"shorts-maker-v2 QC status={qc_status}, passed={qc.get('passed')}, failed={qc_failed}, "
            f"skipped={qc.get('skipped')}, stale={qc_stale}.",
            f"shorts-maker-v2 docs present {len(present_docs)}/{len(docs)}: {', '.join(present_docs) or 'none'}.",
            f"shorts-maker-v2 env checks ok {env_ok_count}/{env_check_count}: {', '.join(env_names) or 'none'}.",
            f"shorts-maker-v2 tasks={len(tasks)}, dirty_paths={len(dirty_paths)}.",
            f"shorts-maker-v2 FEATURE checklist complete {feature_completed}/{feature_total}, open={feature_open}.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(readiness),
    )


def _target_hanwoo_dashboard_item(readiness: dict[str, Any]) -> dict[str, Any]:
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    target: dict[str, Any] | None = None
    for project in projects:
        if not isinstance(project, dict):
            continue
        if (
            project.get("name") == "hanwoo-dashboard"
            or str(project.get("path") or "").replace("\\", "/") == "projects/hanwoo-dashboard"
        ):
            target = project
            break

    artifacts = [
        "projects/hanwoo-dashboard",
        "projects/hanwoo-dashboard/README.md",
        "projects/hanwoo-dashboard/API_SPEC.md",
        "projects/hanwoo-dashboard/package.json",
        "projects/hanwoo-dashboard/.env.example",
        "execution/product_readiness_score.py",
        ".tmp/project_qc_runner_latest.json",
    ]
    if target is None:
        return _item(
            "Prove hanwoo-dashboard target product launch readiness with direct project evidence.",
            artifacts,
            ["product_readiness_score did not include a hanwoo-dashboard project entry."],
            complete=False,
            blockers=["hanwoo-dashboard readiness evidence is missing from product_readiness_score output."],
            verified=bool(readiness),
        )

    qc = target.get("qc") if isinstance(target.get("qc"), dict) else {}
    docs = target.get("docs") if isinstance(target.get("docs"), list) else []
    env = target.get("env") if isinstance(target.get("env"), dict) else {}
    env_checks = env.get("checks") if isinstance(env.get("checks"), list) else []
    tasks = target.get("tasks") if isinstance(target.get("tasks"), list) else []
    dirty_paths = target.get("dirty_paths") if isinstance(target.get("dirty_paths"), list) else []

    score = int(target.get("score") or 0)
    state = str(target.get("state") or "unknown")
    qc_status = str(qc.get("status") or "unknown")
    qc_failed = int(qc.get("failed") or 0)
    qc_stale = qc.get("stale") is True
    present_docs = [str(doc.get("path") or "unknown") for doc in docs if isinstance(doc, dict) and doc.get("present")]
    missing_docs = [
        str(doc.get("path") or "unknown") for doc in docs if isinstance(doc, dict) and not doc.get("present")
    ]
    env_ok_count = sum(1 for check in env_checks if isinstance(check, dict) and check.get("ok") is True)
    env_check_count = len([check for check in env_checks if isinstance(check, dict)])
    env_names = [
        str(check.get("name") or "unknown")
        for check in env_checks
        if isinstance(check, dict) and check.get("ok") is True
    ]
    task_ids = [str(task.get("id") or "unknown") for task in tasks if isinstance(task, dict)]

    complete = (
        score >= 100
        and state == "ready"
        and qc_status == "PASS"
        and qc_failed == 0
        and not qc_stale
        and not missing_docs
        and bool(present_docs)
        and env_check_count > 0
        and env_ok_count == env_check_count
        and not tasks
        and not dirty_paths
    )
    blockers: list[str] = []
    if score < 100 or state != "ready":
        blockers.append(f"hanwoo-dashboard readiness is score={score}, state={state}; expected score>=100 and ready.")
    if qc_status != "PASS" or qc_failed or qc_stale:
        blockers.append(f"hanwoo-dashboard QC is status={qc_status}, failed={qc_failed}, stale={qc_stale}.")
    if missing_docs:
        blockers.append("Missing hanwoo-dashboard launch doc artifact(s): " + ", ".join(missing_docs))
    if not present_docs:
        blockers.append("No hanwoo-dashboard launch doc artifacts were reported present.")
    if env_check_count == 0 or env_ok_count != env_check_count:
        blockers.append(f"hanwoo-dashboard env checks ok {env_ok_count}/{env_check_count}.")
    if tasks:
        blockers.append(
            f"hanwoo-dashboard has {len(tasks)} unresolved readiness task(s): {', '.join(task_ids) or 'unknown'}."
        )
    if dirty_paths:
        blockers.append(f"hanwoo-dashboard has {len(dirty_paths)} dirty path(s).")

    task_ids_are_known = not tasks or all(task_id != "unknown" for task_id in task_ids)
    coverage_complete = (
        bool(readiness) and bool(present_docs) and not missing_docs and env_check_count > 0 and task_ids_are_known
    )

    return _item(
        "Prove hanwoo-dashboard target product launch readiness with direct project evidence.",
        artifacts,
        [
            f"hanwoo-dashboard readiness score={score}, state={state}.",
            f"hanwoo-dashboard QC status={qc_status}, passed={qc.get('passed')}, failed={qc_failed}, "
            f"skipped={qc.get('skipped')}, stale={qc_stale}.",
            f"hanwoo-dashboard docs present {len(present_docs)}/{len(docs)}: {', '.join(present_docs) or 'none'}.",
            f"hanwoo-dashboard env checks ok {env_ok_count}/{env_check_count}: {', '.join(env_names) or 'none'}.",
            f"hanwoo-dashboard tasks={len(tasks)} ({', '.join(task_ids) or 'none'}), dirty_paths={len(dirty_paths)}.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(readiness),
        coverage="complete" if coverage_complete else "partial",
    )


def _target_knowledge_dashboard_item(readiness: dict[str, Any]) -> dict[str, Any]:
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    target: dict[str, Any] | None = None
    for project in projects:
        if not isinstance(project, dict):
            continue
        if (
            project.get("name") == "knowledge-dashboard"
            or str(project.get("path") or "").replace("\\", "/") == "projects/knowledge-dashboard"
        ):
            target = project
            break

    artifacts = [
        "projects/knowledge-dashboard",
        "projects/knowledge-dashboard/README.md",
        "projects/knowledge-dashboard/package.json",
        "projects/knowledge-dashboard/src/app/page.tsx",
        "execution/product_readiness_score.py",
        ".tmp/project_qc_runner_latest.json",
    ]
    if target is None:
        return _item(
            "Prove knowledge-dashboard target product launch readiness with direct project evidence.",
            artifacts,
            ["product_readiness_score did not include a knowledge-dashboard project entry."],
            complete=False,
            blockers=["knowledge-dashboard readiness evidence is missing from product_readiness_score output."],
            verified=bool(readiness),
        )

    qc = target.get("qc") if isinstance(target.get("qc"), dict) else {}
    docs = target.get("docs") if isinstance(target.get("docs"), list) else []
    env = target.get("env") if isinstance(target.get("env"), dict) else {}
    env_checks = env.get("checks") if isinstance(env.get("checks"), list) else []
    tasks = target.get("tasks") if isinstance(target.get("tasks"), list) else []
    dirty_paths = target.get("dirty_paths") if isinstance(target.get("dirty_paths"), list) else []

    score = int(target.get("score") or 0)
    state = str(target.get("state") or "unknown")
    qc_status = str(qc.get("status") or "unknown")
    qc_failed = int(qc.get("failed") or 0)
    qc_stale = qc.get("stale") is True
    present_docs = [str(doc.get("path") or "unknown") for doc in docs if isinstance(doc, dict) and doc.get("present")]
    missing_docs = [
        str(doc.get("path") or "unknown") for doc in docs if isinstance(doc, dict) and not doc.get("present")
    ]
    env_ok_count = sum(1 for check in env_checks if isinstance(check, dict) and check.get("ok") is True)
    env_check_count = len([check for check in env_checks if isinstance(check, dict)])
    env_names = [
        str(check.get("name") or "unknown")
        for check in env_checks
        if isinstance(check, dict) and check.get("ok") is True
    ]

    complete = (
        score >= 100
        and state == "ready"
        and qc_status == "PASS"
        and qc_failed == 0
        and not qc_stale
        and not missing_docs
        and bool(present_docs)
        and env_check_count > 0
        and env_ok_count == env_check_count
        and not tasks
        and not dirty_paths
    )
    blockers: list[str] = []
    if score < 100 or state != "ready":
        blockers.append(
            f"knowledge-dashboard readiness is score={score}, state={state}; expected score>=100 and ready."
        )
    if qc_status != "PASS" or qc_failed or qc_stale:
        blockers.append(f"knowledge-dashboard QC is status={qc_status}, failed={qc_failed}, stale={qc_stale}.")
    if missing_docs:
        blockers.append("Missing knowledge-dashboard launch doc artifact(s): " + ", ".join(missing_docs))
    if not present_docs:
        blockers.append("No knowledge-dashboard launch doc artifacts were reported present.")
    if env_check_count == 0 or env_ok_count != env_check_count:
        blockers.append(f"knowledge-dashboard env checks ok {env_ok_count}/{env_check_count}.")
    if tasks:
        blockers.append(f"knowledge-dashboard has {len(tasks)} unresolved readiness task(s).")
    if dirty_paths:
        blockers.append(f"knowledge-dashboard has {len(dirty_paths)} dirty path(s).")

    return _item(
        "Prove knowledge-dashboard target product launch readiness with direct project evidence.",
        artifacts,
        [
            f"knowledge-dashboard readiness score={score}, state={state}.",
            f"knowledge-dashboard QC status={qc_status}, passed={qc.get('passed')}, failed={qc_failed}, "
            f"skipped={qc.get('skipped')}, stale={qc_stale}.",
            f"knowledge-dashboard docs present {len(present_docs)}/{len(docs)}: {', '.join(present_docs) or 'none'}.",
            f"knowledge-dashboard env checks ok {env_ok_count}/{env_check_count}: {', '.join(env_names) or 'none'}.",
            f"knowledge-dashboard tasks={len(tasks)}, dirty_paths={len(dirty_paths)}.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(readiness),
    )


def _browser_item(browser_inventory: dict[str, Any]) -> dict[str, Any]:
    summary = browser_inventory.get("summary") if isinstance(browser_inventory.get("summary"), dict) else {}
    recommendations = browser_inventory.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []
    browser_count = int(summary.get("browser_project_count") or 0)
    covered_count = int(summary.get("covered_count") or 0)
    missing_count = int(summary.get("missing_count") or 0)
    screenshot_count = int(summary.get("current_screenshot_project_count") or 0)
    fresh_screenshot_count = int(summary.get("fresh_screenshot_project_count", screenshot_count) or 0)
    stale_screenshot_count = int(summary.get("stale_screenshot_project_count") or 0)
    fresh_usable_screenshot_count = int(
        summary.get("fresh_usable_screenshot_project_count", fresh_screenshot_count) or 0
    )
    fresh_nonblank_screenshot_count = int(
        summary.get("fresh_nonblank_screenshot_project_count", fresh_usable_screenshot_count) or 0
    )
    complete = (
        browser_count > 0
        and missing_count == 0
        and covered_count == browser_count
        and screenshot_count == browser_count
        and fresh_screenshot_count == browser_count
        and fresh_usable_screenshot_count == browser_count
        and fresh_nonblank_screenshot_count == browser_count
    )
    blockers = [str(item) for item in recommendations]
    if missing_count:
        blockers.append("Browser QA missing project(s): " + ", ".join(summary.get("missing_projects") or []))
    if browser_count and screenshot_count < browser_count:
        blockers.append(f"Only {screenshot_count}/{browser_count} browser project(s) have retained screenshots.")
    if browser_count and fresh_screenshot_count < browser_count:
        blockers.append(
            f"Only {fresh_screenshot_count}/{browser_count} browser project(s) have fresh retained screenshots."
        )
    if browser_count and fresh_usable_screenshot_count < browser_count:
        blockers.append(
            f"Only {fresh_usable_screenshot_count}/{browser_count} browser project(s) have fresh usable screenshots."
        )
    if browser_count and fresh_nonblank_screenshot_count < browser_count:
        blockers.append(
            f"Only {fresh_nonblank_screenshot_count}/{browser_count} browser project(s) have fresh nonblank screenshots."
        )
    browser_evidence = [
        f"browser_qa_inventory coverage {covered_count}/{browser_count}, missing_count={missing_count}.",
        f"current screenshot coverage {screenshot_count}/{browser_count}.",
        f"fresh screenshot coverage {fresh_screenshot_count}/{browser_count}; stale={stale_screenshot_count}.",
    ]
    if "fresh_usable_screenshot_project_count" in summary or "fresh_nonblank_screenshot_project_count" in summary:
        browser_evidence.append(
            f"fresh usable screenshot coverage {fresh_usable_screenshot_count}/{browser_count}; "
            f"fresh nonblank={fresh_nonblank_screenshot_count}/{browser_count}."
        )
    return _item(
        "Use Codex/browser automation to click through every browser app and retain evidence.",
        ["output/playwright", ".ai/TASKS.md", ".ai/HANDOFF.md", ".ai/SESSION_LOG.md"],
        browser_evidence,
        complete=complete,
        blockers=blockers,
        verified=bool(browser_inventory),
    )


def _dependency_peer_blocker_evidence(dependency_inventory: dict[str, Any]) -> str:
    projects = dependency_inventory.get("projects") if isinstance(dependency_inventory.get("projects"), list) else []
    labels: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        project_path = str(project.get("path") or "unknown")
        dependencies = project.get("dependencies") if isinstance(project.get("dependencies"), list) else []
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            if not dependency.get("deferred") or dependency.get("peer_blocker_check") != "blocked":
                continue
            latest_suffix = ""
            if dependency.get("peer_blocker_latest_check"):
                latest_suffix = (
                    f", latest_supported={int(dependency.get('peer_blocker_latest_supported_count') or 0)}"
                    f", latest_blocked={int(dependency.get('peer_blocker_latest_blocked_count') or 0)}"
                    f", latest_unavailable={int(dependency.get('peer_blocker_latest_unavailable_count') or 0)}"
                )
            labels.append(
                f"{project_path}/{dependency.get('name') or 'unknown'} "
                f"peer_blocker_count={int(dependency.get('peer_blocker_count') or 0)}{latest_suffix}"
            )

    if labels:
        return "Peer-blocked deferred majors: " + "; ".join(labels) + "."
    return "Peer-blocked deferred majors: none."


def _dependency_prerelease_channel_evidence(dependency_inventory: dict[str, Any]) -> str:
    projects = dependency_inventory.get("projects") if isinstance(dependency_inventory.get("projects"), list) else []
    labels: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        project_path = str(project.get("path") or "unknown")
        dependencies = project.get("dependencies") if isinstance(project.get("dependencies"), list) else []
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            if dependency.get("classification") != "current_prerelease_channel":
                continue
            labels.append(
                f"{project_path}/{dependency.get('name') or 'unknown'} "
                f"{dependency.get('dist_tag_channel') or 'channel'}={dependency.get('dist_tag_version') or 'unknown'} "
                f"current={dependency.get('current') or 'unknown'} stable_latest={dependency.get('latest') or 'unknown'}"
            )

    if labels:
        return "Current prerelease-channel packages: " + "; ".join(labels) + "."
    return "Current prerelease-channel packages: none."


def _dependency_item(
    dependency_inventory: dict[str, Any],
    *,
    root: Path | None = None,
    session_orientation: dict[str, Any] | None = None,
    code_review_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = dependency_inventory.get("summary") if isinstance(dependency_inventory.get("summary"), dict) else {}
    recommendations = dependency_inventory.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []
    candidate_count = int(summary.get("candidate_dependency_count") or 0)
    deferred_count = int(summary.get("deferred_dependency_count") or 0)
    outdated_count = int(summary.get("outdated_dependency_count") or 0)
    unavailable_count = int(summary.get("unavailable_project_count") or 0)
    complete = candidate_count == 0 and unavailable_count == 0
    blockers = []
    if candidate_count:
        blockers.append(f"{candidate_count} direct patch/minor dependency candidate(s) remain.")
    if unavailable_count:
        blockers.append(f"{unavailable_count} package project(s) had unavailable npm freshness inventory.")
    extra_artifacts: list[str] = []
    extra_evidence: list[str] = []

    if session_orientation is not None:
        extra_artifacts.append("execution/session_orient.py")
        graph = session_orientation.get("graph") if isinstance(session_orientation.get("graph"), dict) else {}
        freshness = graph.get("freshness") or "unavailable"
        built_at_commit = graph.get("built_at_commit") or "unknown"
        current_head = graph.get("current_head") or "unknown"
        extra_evidence.append(
            f"code_review_graph freshness={freshness}, built_at_commit={built_at_commit}, current_head={current_head}."
        )
        if freshness != "current":
            relevant_files = (
                _graph_relevant_files_between(root, str(built_at_commit), str(current_head))
                if root is not None
                else None
            )
            if relevant_files is None:
                complete = False
                blockers.append(
                    f"code_review_graph freshness is {freshness}; changed files since graph build are unavailable."
                )
            elif relevant_files:
                complete = False
                blockers.append(
                    f"code_review_graph freshness is {freshness}; graph-relevant changes remain: "
                    f"{', '.join(relevant_files[:5])}."
                )
            else:
                extra_evidence.append("code_review_graph stale range has no graph-relevant file changes.")

    if code_review_gate is not None:
        extra_artifacts.append("execution/code_review_gate.py")
        status = code_review_gate.get("status") or "unavailable"
        risk_score = code_review_gate.get("risk_score")
        changed_files = (
            code_review_gate.get("changed_files") if isinstance(code_review_gate.get("changed_files"), list) else []
        )
        test_gaps = code_review_gate.get("test_gaps") if isinstance(code_review_gate.get("test_gaps"), list) else []
        extra_evidence.append(
            "code_review_gate "
            f"status={status}, risk_score={risk_score}, changed_files={len(changed_files)}, test_gaps={len(test_gaps)}."
        )
        if status not in {"pass", "warn"}:
            complete = False
            blockers.append(f"code_review_gate status={status}; expected pass or warn.")

    return _item(
        "Research current dependency/code freshness and adopt only safe, evidence-backed improvements.",
        [
            ".agents/skills/auto-research/scripts/dependency_freshness_inventory.py",
            *extra_artifacts,
            "package.json",
            "pnpm-lock.yaml",
            "projects",
        ],
        [
            f"dependency_freshness_inventory candidate_dependency_count={candidate_count}.",
            f"outdated_dependency_count={outdated_count}.",
            f"deferred_dependency_count={deferred_count}; deferred major/channel items require separate explicit experiments.",
            f"unavailable_project_count={unavailable_count}.",
            _dependency_peer_blocker_evidence(dependency_inventory),
            _dependency_prerelease_channel_evidence(dependency_inventory),
            "Recommendations: " + "; ".join(str(item) for item in recommendations)
            if recommendations
            else "Recommendations: none.",
            *extra_evidence,
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(dependency_inventory),
    )


def _readiness_item(readiness: dict[str, Any]) -> dict[str, Any]:
    overall = readiness.get("overall") if isinstance(readiness.get("overall"), dict) else {}
    gates = readiness.get("workspace_gates") if isinstance(readiness.get("workspace_gates"), dict) else {}
    github_gate = gates.get("github_release") if isinstance(gates.get("github_release"), dict) else {}
    workflows = github_gate.get("required_workflows") if isinstance(github_gate.get("required_workflows"), list) else []
    local_blockers = int(overall.get("local_blocker_count") or 0)
    workspace_blockers = int(overall.get("workspace_blocker_count") or 0)
    publish_blockers = int(overall.get("publish_blocker_count") or 0)
    agent_tasks = int(overall.get("agent_task_count") or 0)
    publish_boundary_blocked = (
        workspace_blockers > 0 and publish_blockers >= workspace_blockers and local_blockers == 0 and agent_tasks == 0
    )
    non_publish_workspace_blockers = 0 if publish_boundary_blocked else workspace_blockers
    complete = local_blockers == 0 and non_publish_workspace_blockers == 0 and agent_tasks == 0
    blockers = []
    if local_blockers:
        blockers.append(f"local_blocker_count={local_blockers}")
    if non_publish_workspace_blockers:
        blockers.append(f"workspace_blocker_count={workspace_blockers}")
    if agent_tasks:
        blockers.append(f"agent_task_count={agent_tasks}")
    evidence = [
        f"product_readiness_score overall score={overall.get('score')}, state={overall.get('state')}.",
        "readiness blocker counts: "
        f"workspace={workspace_blockers}, local={local_blockers}, publish={publish_blockers}, "
        f"agent_tasks={agent_tasks}.",
        "Required workflows: "
        + ", ".join(
            f"{workflow.get('name')}={workflow.get('conclusion') or workflow.get('status')}" for workflow in workflows
        ),
    ]
    if publish_boundary_blocked:
        evidence.append(
            "Local readiness gates are green; the publish/current-head Actions boundary is tracked "
            "separately by the release authorization and selector audit items."
        )
    return _item(
        "Verify local product-readiness gates before claiming launch readiness.",
        ["execution/product_readiness_score.py", ".tmp/project_qc_runner_latest.json", ".github/workflows"],
        evidence,
        complete=complete,
        blockers=blockers,
        verified=bool(readiness),
        coverage="complete" if publish_boundary_blocked else None,
    )


def _release_authorization_packet_item(packet: dict[str, Any]) -> dict[str, Any]:
    status = str(packet.get("status") or "unknown")
    git = packet.get("git") if isinstance(packet.get("git"), dict) else {}
    authorization = packet.get("authorization") if isinstance(packet.get("authorization"), dict) else {}
    workflows = packet.get("required_workflows") if isinstance(packet.get("required_workflows"), list) else []
    packet_blockers = [str(blocker) for blocker in packet.get("blockers") or [] if str(blocker).strip()]
    unproven = [str(workflow) for workflow in packet.get("unproven_workflows") or [] if str(workflow).strip()]
    post_push_gates = [str(gate) for gate in authorization.get("post_push_gates") or [] if str(gate).strip()]
    guardrails = _sentence_list(authorization.get("guardrails"))
    dirty_count = int(git.get("dirty_count") or 0)
    ahead_count = int(git.get("ahead_count") or 0)
    head_sha = str(git.get("head_sha") or "unknown")
    head_label = head_sha[:8] if head_sha != "unknown" else head_sha
    allowed_without_authorization = authorization.get("allowed_without_explicit_user_authorization")

    blockers: list[str] = []
    if status == "ready_for_authorization":
        blockers.append(
            "release authorization packet is ready, but explicit push authorization and current-head Actions are still required."
        )
    elif status == "blocked_dirty_worktree":
        blockers.append(f"release authorization packet blocked by dirty worktree paths: {dirty_count}.")
    elif status == "git_unavailable":
        blockers.append("release authorization packet could not inspect git state.")
    elif status not in {"not_required", "already_verified"}:
        blockers.append(f"release authorization packet returned unexpected status={status}.")
    if allowed_without_authorization is not False:
        blockers.append("release authorization packet did not enforce explicit user authorization.")
    if status == "ready_for_authorization" and ahead_count > 0 and not authorization.get("suggested_command"):
        blockers.append("release authorization packet omitted the suggested push command for a clean ahead head.")

    workflow_evidence = ", ".join(
        f"{workflow.get('name')}={workflow.get('status') or workflow.get('conclusion')}"
        for workflow in workflows
        if isinstance(workflow, dict)
    )
    evidence = [
        f"release_authorization_packet status={status}, branch={git.get('branch')}, head={head_label}.",
        f"release_authorization_packet ahead_count={ahead_count}, dirty_count={dirty_count}.",
        "Required workflows: " + (workflow_evidence if workflow_evidence else "none."),
        "Unproven workflows: " + (", ".join(unproven) if unproven else "none."),
        "Post-push gates: " + (", ".join(post_push_gates) if post_push_gates else "none."),
        "Suggested push command present="
        f"{bool(authorization.get('suggested_command'))}; "
        f"allowed_without_explicit_user_authorization={allowed_without_authorization}.",
    ]
    if guardrails:
        evidence.append(f"Release authorization guardrails: {' '.join(guardrails)}")
    if packet_blockers:
        evidence.append(f"Packet blockers: {'; '.join(packet_blockers)}.")

    return _item(
        "Generate a no-push release authorization packet before any clean-ahead publish.",
        [".agents/skills/auto-research/scripts/release_authorization_packet.py"],
        evidence,
        complete=not blockers,
        blockers=blockers,
        verified=bool(packet),
        coverage="complete" if packet else "partial",
    )


def _selector_item(selection: dict[str, Any]) -> dict[str, Any]:
    status = str(selection.get("status") or "unknown")
    selected = selection.get("selected") if isinstance(selection.get("selected"), dict) else {}
    summary = selection.get("summary") if isinstance(selection.get("summary"), dict) else {}
    selected_kind = str(selected.get("kind") or summary.get("selected_kind") or "unknown")
    selected_project = str(selected.get("project") or "unknown")
    action = str(selected.get("action") or "unknown")
    guardrails = _sentence_list(selected.get("guardrails"))
    required_gates = _sentence_list(selected.get("required_gates"))
    blocked = selected.get("blocked") is True
    complete = status in {"blocked_external_only", "ready_for_completion_audit"}
    publish_boundary_selected = selected_kind == "current_head_release_checks_unproven"
    blockers: list[str] = []
    if publish_boundary_selected:
        blockers.append(
            "next_experiment_selector selected unresolved publish boundary: "
            f"status={status}, kind={selected_kind}, project={selected_project}"
        )
    elif not complete:
        blockers.append(
            "next_experiment_selector selected unresolved local work: "
            f"status={status}, kind={selected_kind}, project={selected_project}"
        )
    elif status == "ready_for_completion_audit" and blocked:
        blockers.append("next_experiment_selector reported ready status with a blocked selected candidate.")

    if status == "blocked_external_only":
        selector_evidence = "Selector confirms only external/user-owned work remains."
    elif status == "ready_for_completion_audit":
        selector_evidence = "Selector reports no remaining local experiment candidate."
    elif publish_boundary_selected:
        selector_evidence = "Selector reports a publish-boundary check before launch completion can be claimed."
    else:
        selector_evidence = "Selector reports local follow-up work before launch completion can be claimed."

    evidence = [
        f"next_experiment_selector status={status}, selected_kind={selected_kind}, project={selected_project}.",
        _evidence_sentence("Selected action", action),
        selector_evidence,
    ]
    if guardrails:
        evidence.append(f"Selector guardrails: {' '.join(guardrails)}")
    if required_gates:
        evidence.append(f"Selector required gates: {' '.join(required_gates)}")

    return _item(
        "Run the deterministic next-experiment selector and confirm no local auto-research candidate remains.",
        [".agents/skills/auto-research/scripts/next_experiment_selector.py"],
        evidence,
        complete=complete and not blockers,
        blockers=blockers,
        coverage="complete" if publish_boundary_selected else None,
    )


def _external_blocker_item(readiness: dict[str, Any]) -> dict[str, Any]:
    overall = readiness.get("overall") if isinstance(readiness.get("overall"), dict) else {}
    external_blockers = int(overall.get("external_blocker_count") or 0)
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    task_ids: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        for task in project.get("tasks") or []:
            owner = str(task.get("owner") or "").strip().lower() if isinstance(task, dict) else ""
            if isinstance(task, dict) and owner == "user" and task.get("id"):
                task_ids.append(str(task["id"]))
    complete = external_blockers == 0
    external_blockers_have_task_ids = external_blockers == 0 or len(task_ids) >= external_blockers
    blockers = []
    if external_blockers:
        blockers.append(
            f"{external_blockers} external/user-owned blocker(s) remain: {', '.join(task_ids) or 'unknown'}"
        )
    return _item(
        "Separate externally blocked live checks from local product-polish completion.",
        [".ai/TASKS.md", "projects/hanwoo-dashboard", "execution/product_readiness_score.py"],
        [
            f"product_readiness_score external_blocker_count={external_blockers}.",
            f"user-owned task ids: {', '.join(task_ids) if task_ids else 'none'}.",
        ],
        complete=complete,
        blockers=blockers,
        verified=bool(readiness),
        coverage="complete" if external_blockers_have_task_ids else "partial",
    )


def _latest_ab_manifest(
    root: Path,
    *,
    ab_manifest_path: Path | None = None,
) -> tuple[str | None, dict[str, Any] | None, list[str]]:
    tmp_dir = root / ".tmp"
    errors: list[str] = []

    if ab_manifest_path is not None:
        requested_path = ab_manifest_path if ab_manifest_path.is_absolute() else root / ab_manifest_path
        if _ab_manifest_sort_key(requested_path) is None:
            errors.append(f"Requested A/B manifest artifact is unreadable: {_rel(root, requested_path)}")
            return None, None, errors
        data = _load_json_object(requested_path)
        if data is None:
            errors.append(f"Requested A/B manifest artifact is invalid: {_rel(root, requested_path)}")
            return None, None, errors
        return _rel(root, requested_path), data, errors

    if not tmp_dir.exists():
        return None, None, errors

    scored_candidates: list[tuple[tuple[int, int, int, str], Path, dict[str, Any]]] = []
    for path in tmp_dir.glob(AB_MANIFEST_GLOB):
        sort_key = _ab_manifest_sort_key(path)
        if sort_key is None:
            errors.append(f"Ignored unreadable A/B manifest artifact: {_rel(root, path)}")
            continue
        data = _load_json_object(path)
        if data is None:
            errors.append(f"Ignored invalid A/B manifest artifact: {_rel(root, path)}")
            continue
        task_id = _ab_manifest_task_id(path, data)
        candidate_key = (
            1 if task_id is not None else 0,
            task_id if task_id is not None else -1,
            sort_key[0],
            sort_key[1],
        )
        scored_candidates.append((candidate_key, path, data))

    if scored_candidates:
        _, path, data = max(scored_candidates, key=lambda item: item[0])
        return _rel(root, path), data, errors
    return None, None, errors


def _ab_manifest_evidence(
    root: Path, *, ab_manifest_path: Path | None = None
) -> tuple[list[str], list[str], list[str]]:
    manifest_path, manifest, errors = _latest_ab_manifest(root, ab_manifest_path=ab_manifest_path)
    evidence = list(errors)
    blockers: list[str] = []
    artifacts: list[str] = []
    if manifest_path is None or manifest is None:
        evidence.append("No local A/B manifest artifact found; relying on .ai relay evidence.")
        return artifacts, evidence, blockers

    artifacts.append(manifest_path)
    experiment = str(manifest.get("experiment") or manifest_path)
    task_id = _ab_manifest_task_id(root / manifest_path, manifest)
    candidate = manifest.get("candidate") if isinstance(manifest.get("candidate"), dict) else {}
    metrics = candidate.get("metrics") if isinstance(candidate.get("metrics"), dict) else {}
    gates = candidate.get("gates") if isinstance(candidate.get("gates"), dict) else None
    if gates is None:
        all_gates = manifest.get("gates") if isinstance(manifest.get("gates"), dict) else {}
        gates = all_gates.get("candidate") if isinstance(all_gates.get("candidate"), dict) else {}
    required_gates = manifest.get("required_gates") if isinstance(manifest.get("required_gates"), list) else []
    failed_gates = [str(gate) for gate in required_gates if not gates.get(str(gate), False)]
    passed_gate_count = len(required_gates) - len(failed_gates)

    evidence.append(f"Latest A/B manifest artifact: {manifest_path} ({experiment}).")
    if task_id is not None:
        evidence.append(f"Latest A/B manifest selection used task id T-{task_id}.")
    evidence.append(
        f"Latest A/B candidate metrics={len(metrics)}, required gates passed {passed_gate_count}/{len(required_gates)}."
    )
    if not metrics:
        blockers.append(f"Latest A/B manifest has no candidate metrics: {manifest_path}")
    if failed_gates:
        blockers.append(f"Latest A/B manifest failed required gate(s): {', '.join(failed_gates)}")
    return artifacts, evidence, blockers


def _ab_loop_item(root: Path, *, ab_manifest_path: Path | None = None) -> dict[str, Any]:
    tasks_text = _read_text(root, ".ai/TASKS.md").lower()
    handoff_text = _read_text(root, ".ai/HANDOFF.md").lower()
    has_ab_script = _exists(root, ".agents/skills/auto-research/scripts/ab_decision.py")
    has_completion_script = _exists(root, ".agents/skills/auto-research/scripts/completion_audit.py")
    has_recent_ab_evidence = "a/b `adopt_candidate`" in tasks_text or "a/b `adopt_candidate`" in handoff_text
    ab_artifacts, ab_evidence, ab_blockers = _ab_manifest_evidence(root, ab_manifest_path=ab_manifest_path)
    complete = has_ab_script and has_completion_script and has_recent_ab_evidence and not ab_blockers
    blockers = []
    if not has_ab_script:
        blockers.append("Missing ab_decision.py.")
    if not has_completion_script:
        blockers.append("Missing completion_audit.py.")
    if not has_recent_ab_evidence:
        blockers.append("No recent A/B adoption evidence found in .ai relay files.")
    blockers.extend(ab_blockers)
    return _item(
        "Run bounded A/B experiments and adopt only candidates that improve verified metrics.",
        [
            ".agents/skills/auto-research/scripts/ab_decision.py",
            ".ai/TASKS.md",
            ".ai/HANDOFF.md",
            *ab_artifacts,
        ],
        [
            "A/B decision helper exists." if has_ab_script else "A/B decision helper is missing.",
            *ab_evidence,
            "Recent .ai relay includes adopt_candidate evidence."
            if has_recent_ab_evidence
            else "No recent relay A/B evidence found.",
        ],
        complete=complete,
        blockers=blockers,
    )


def _relay_item(root: Path) -> dict[str, Any]:
    missing = [path for path in AI_RELAY_ARTIFACTS if not _exists(root, path)]
    goal_text = _read_text(root, ".ai/GOAL.md")
    goal_status_match = GOAL_STATUS_RE.search(goal_text)
    goal_status = goal_status_match.group(1).strip() if goal_status_match else "unknown"
    goal_status_norm = goal_status.lower().replace(" ", "_")
    goal_mentions_current_objective = any(term in goal_text.lower() for term in GOAL_OBJECTIVE_TERMS)
    goal_is_current = (
        ".ai/GOAL.md" not in missing and goal_status_norm in GOAL_ACTIVE_STATUSES and goal_mentions_current_objective
    )
    complete = not missing and goal_is_current
    blockers = ["Missing .ai relay artifact(s): " + ", ".join(missing)] if missing else []
    if ".ai/GOAL.md" not in missing:
        if goal_status_norm not in GOAL_ACTIVE_STATUSES:
            blockers.append(f"GOAL.md status is {goal_status}; expected an active launch-loop status.")
        if not goal_mentions_current_objective:
            blockers.append("GOAL.md does not describe the current product launch/auto-research objective.")
    return _item(
        "Keep the self-improvement loop resumable across tools and sessions.",
        list(AI_RELAY_ARTIFACTS),
        [
            f"{len(AI_RELAY_ARTIFACTS) - len(missing)}/{len(AI_RELAY_ARTIFACTS)} relay files exist.",
            "HANDOFF/TASKS/SESSION_LOG/CONTEXT/GOAL provide the next-session continuation surface.",
            f"GOAL.md status={goal_status}; current launch objective mapped={goal_mentions_current_objective}.",
        ],
        complete=complete,
        blockers=blockers,
    )


def build_manifest(
    root: Path,
    *,
    objective: str = DEFAULT_OBJECTIVE,
    ab_manifest_path: Path | None = None,
    readiness: dict[str, Any] | None = None,
    github_inventory: dict[str, Any] | None = None,
    browser_inventory: dict[str, Any] | None = None,
    dependency_inventory: dict[str, Any] | None = None,
    next_experiment_selection: dict[str, Any] | None = None,
    release_authorization_packet: dict[str, Any] | None = None,
    session_orientation: dict[str, Any] | None = None,
    code_review_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    items = [
        _skill_item(root),
        _github_item(github_inventory or {}),
        _browser_item(browser_inventory or {}),
        _dependency_item(
            dependency_inventory or {},
            root=root,
            session_orientation=session_orientation,
            code_review_gate=code_review_gate,
        ),
        _readiness_item(readiness or {}),
    ]
    if release_authorization_packet is not None:
        items.append(_release_authorization_packet_item(release_authorization_packet))
    if next_experiment_selection is not None:
        items.append(_selector_item(next_experiment_selection))
    items.extend(
        [
            _external_blocker_item(readiness or {}),
            _quality_objective_item(root),
            _ab_loop_item(root, ab_manifest_path=ab_manifest_path),
            _relay_item(root),
            _target_hanwoo_dashboard_item(readiness or {}),
            _target_blind_to_x_item(readiness or {}),
            _target_shorts_maker_v2_item(root, readiness or {}),
            _target_knowledge_dashboard_item(readiness or {}),
        ]
    )
    return {
        "objective": objective,
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(root),
        "success_criteria": [
            "Every explicit launch objective requirement is mapped to concrete artifacts and current evidence.",
            "Local launch gates are green before claiming product readiness.",
            "Externally blocked live checks remain explicit blockers instead of being hidden by proxy signals.",
        ],
        "items": items,
    }


def collect_current_inputs(root: Path, timeout: int) -> dict[str, dict[str, Any]]:
    python = sys.executable
    commands = {
        "session_orientation": [python, "execution/session_orient.py", "--json"],
        "readiness": [python, "execution/product_readiness_score.py", "--json"],
        "github_inventory": [
            python,
            ".agents/skills/auto-research/scripts/github_project_inventory.py",
            "--root",
            ".",
            "--include-prs",
            "--json",
        ],
        "browser_inventory": [
            python,
            ".agents/skills/auto-research/scripts/browser_qa_inventory.py",
            "--root",
            ".",
            "--json",
        ],
        "dependency_inventory": [
            python,
            ".agents/skills/auto-research/scripts/dependency_freshness_inventory.py",
            "--root",
            ".",
            "--json",
        ],
    }
    collected = {
        name: _with_recent_inventory_fallback(root, name, _run_json(root, command, timeout))
        for name, command in commands.items()
    }
    collected["code_review_gate"] = _code_review_gate_from_inputs(root, timeout)
    readiness_data = collected.get("readiness", {}).get("data")
    collected["release_authorization_packet"] = _release_authorization_packet_from_inputs(
        root,
        readiness_data if isinstance(readiness_data, dict) else {},
    )
    collected["next_experiment_selection"] = _select_next_experiment_from_inputs(collected)
    return collected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Workspace root")
    parser.add_argument("--objective", default=DEFAULT_OBJECTIVE, help="Objective text for the manifest")
    parser.add_argument("--ab-manifest", type=Path, help="Use a specific local A/B manifest artifact")
    parser.add_argument("--output", type=Path, help="Write manifest JSON to this path")
    parser.add_argument("--timeout-seconds", type=int, default=120, help="Timeout per evidence command")
    parser.add_argument("--json", action="store_true", help="Print JSON manifest to stdout")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    collected = collect_current_inputs(root, args.timeout_seconds)
    selector_result = collected.get("next_experiment_selection") or {}
    release_packet_result = collected.get("release_authorization_packet") or {}
    manifest = build_manifest(
        root,
        objective=args.objective,
        ab_manifest_path=args.ab_manifest,
        readiness=collected["readiness"]["data"],
        github_inventory=collected["github_inventory"]["data"],
        browser_inventory=collected["browser_inventory"]["data"],
        dependency_inventory=collected["dependency_inventory"]["data"],
        next_experiment_selection=selector_result.get("data") if selector_result else None,
        release_authorization_packet=release_packet_result.get("data") if release_packet_result else None,
        session_orientation=(collected.get("session_orientation") or {}).get("data"),
        code_review_gate=(collected.get("code_review_gate") or {}).get("data"),
    )
    manifest["evidence_commands"] = {
        name: {
            "available": result["available"],
            "returncode": result["returncode"],
            "stderr": result["stderr"],
        }
        for name, result in collected.items()
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    if args.json or not args.output:
        json.dump(manifest, sys.stdout, ensure_ascii=True, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
