"""Build a completion-audit manifest for the LLM Wiki autonomous loop objective.

The structural wiki audit answers "is the wiki internally trustworthy?".
This script answers a different question: "does the current repo evidence map
back to the user's explicit autonomous-loop prompt?"  Its output is intentionally
compatible with `.agents/skills/auto-research/scripts/completion_audit.py`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
OUTPUT_DEFAULT = Path(".tmp/llm-wiki-objective-audit-current.json")
WIKI_DIR = Path("docs/wiki/llm")
SOURCE_INVENTORY = WIKI_DIR / "source-inventory.json"
CODE_FACTS = WIKI_DIR / "code-facts.json"
CONFIG_FACTS = WIKI_DIR / "config-facts.json"
NEXT_EXPERIMENT = Path(".tmp/next-experiment.json")


def _repo_path(repo_root: Path, rel_path: str | Path) -> Path:
    path = Path(rel_path)
    return path if path.is_absolute() else repo_root / path


def _repo_output_path(repo_root: Path, rel_path: str | Path) -> Path:
    path = Path(rel_path)
    return path if path.is_absolute() else repo_root / path


def _read_text(repo_root: Path, rel_path: str | Path) -> str:
    path = _repo_path(repo_root, rel_path)
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_json(repo_root: Path, rel_path: str | Path) -> dict[str, Any]:
    text = _read_text(repo_root, rel_path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _exists(repo_root: Path, rel_path: str | Path) -> bool:
    return _repo_path(repo_root, rel_path).exists()


def _summary_int(summary: dict[str, Any], key: str) -> int:
    try:
        return int(summary.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _load_llm_wiki_audit_module():
    script_path = Path(__file__).with_name("llm_wiki_audit.py")
    spec = importlib.util.spec_from_file_location("_llm_wiki_audit_for_objective", script_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _llm_wiki_report(repo_root: Path, *, today: date) -> dict[str, Any]:
    audit = _load_llm_wiki_audit_module()
    return audit.build_report(repo_root, today=today)


def _contains_all(text: str, markers: tuple[str, ...]) -> bool:
    return all(marker in text for marker in markers)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _wiki_markdown_texts(repo_root: Path) -> dict[str, str]:
    wiki_dir = _repo_path(repo_root, WIKI_DIR)
    if not wiki_dir.exists():
        return {}
    return {path.name: path.read_text(encoding="utf-8", errors="replace") for path in sorted(wiki_dir.glob("*.md"))}


def _ab_page_count(repo_root: Path) -> int:
    return sum(1 for text in _wiki_markdown_texts(repo_root).values() if "A/B" in text)


def _selector_kind(repo_root: Path) -> str:
    data = _read_json(repo_root, NEXT_EXPERIMENT)
    summary = data.get("summary", {})
    if isinstance(summary, dict) and isinstance(summary.get("selected_kind"), str):
        return summary["selected_kind"]
    selected = data.get("selected", {})
    if isinstance(selected, dict) and isinstance(selected.get("kind"), str):
        return selected["kind"]
    return ""


def _item(
    requirement: str,
    *,
    artifacts: list[str],
    evidence: list[str],
    complete: bool,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    blockers = [blocker for blocker in blockers or [] if blocker]
    return {
        "requirement": requirement,
        "artifacts": artifacts,
        "evidence": evidence,
        "verified": bool(complete and evidence and artifacts),
        "coverage": "complete" if complete else "missing",
        "blockers": blockers,
    }


def _missing_blockers(required: dict[str, bool]) -> list[str]:
    return [f"Missing or stale evidence: {name}" for name, present in required.items() if not present]


def build_manifest(repo_root: Path, *, today: date | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    today = today or date.today()
    report = _llm_wiki_report(repo_root, today=today)
    summary = report.get("summary", {})
    summary = summary if isinstance(summary, dict) else {}

    readme = _read_text(repo_root, WIKI_DIR / "README.md")
    handoff = _read_text(repo_root, ".ai/HANDOFF.md")
    tasks = _read_text(repo_root, ".ai/TASKS.md")
    session_log = _read_text(repo_root, ".ai/SESSION_LOG.md")
    ai_text = "\n".join([handoff, tasks, session_log])
    ab_count = _ab_page_count(repo_root)
    selector_kind = _selector_kind(repo_root)

    audit_status = str(summary.get("status", "unknown"))
    source_inventory_count = _summary_int(summary, "source_inventory_count")
    source_page_count = _summary_int(summary, "source_page_count")
    code_fact_count = _summary_int(summary, "code_fact_count")
    config_fact_count = _summary_int(summary, "config_fact_count")
    unexpected_warning_count = _summary_int(summary, "manifest_check_unexpected_warning_count")
    accepted_warning_count = _summary_int(summary, "manifest_check_accepted_warning_count")
    release_summary_status = str(summary.get("release_summary_contract_status", "unknown"))

    items: list[dict[str, Any]] = []

    zero_step = {
        "README index has core LLM Wiki pages": _contains_all(
            readme,
            ("01-architecture.md", "14-maintenance-verification.md", "15-source-inventory.md"),
        ),
        "initial LLM Wiki build was logged": "T-1573" in session_log,
        "autonomous reinforcement cycles are logged": _contains_any(session_log, ("T-1577", "T-1578", "T-1579")),
    }
    zero_step_complete = all(zero_step.values())
    items.append(
        _item(
            "0단계: LLM Wiki 목적, 현재 구조, 기존 gap 목록을 먼저 확인한다.",
            artifacts=[
                "docs/wiki/llm/README.md",
                "docs/wiki/llm/14-maintenance-verification.md",
                ".ai/SESSION_LOG.md",
            ],
            evidence=[
                "README indexes the initial architecture and maintenance pages.",
                "SESSION_LOG records T-1573 initial LLM Wiki build and later reinforcement cycles.",
            ],
            complete=zero_step_complete,
            blockers=_missing_blockers(zero_step),
        )
    )

    gap_selection = {
        "source inventory page exists": _exists(repo_root, WIKI_DIR / "15-source-inventory.md"),
        "runtime gap page exists": _exists(repo_root, WIKI_DIR / "18-runtime-wiring-checks.md"),
        "LLM Wiki follow-up tasks are logged": _contains_any(
            ai_text, ("Next LLM Wiki candidate", "LLM Wiki candidate")
        ),
    }
    gap_selection_complete = all(gap_selection.values())
    items.append(
        _item(
            "Gap 선정: 다음 보강 주제는 handoff/task evidence에서 선택하고 gap list에 남긴다.",
            artifacts=[".ai/HANDOFF.md", ".ai/TASKS.md", "docs/wiki/llm/15-source-inventory.md"],
            evidence=[
                "Handoff/task notes include LLM Wiki follow-up candidates.",
                "15-source-inventory.md and 18-runtime-wiring-checks.md keep source and runtime gap lists visible.",
            ],
            complete=gap_selection_complete,
            blockers=_missing_blockers(gap_selection),
        )
    )

    external_research = {
        "wiki audit passes": audit_status == "pass",
        "source inventory manifest exists": _exists(repo_root, SOURCE_INVENTORY),
        "external source inventory is non-empty": source_inventory_count > 0,
        "at least one source-backed page exists": source_page_count > 0,
        "source policy is documented": "source-inventory.json" in readme,
    }
    external_research_complete = all(external_research.values())
    items.append(
        _item(
            "외부 조사: 공식 문서/표준 중심의 1차 출처를 확인하고 source inventory에 기록한다.",
            artifacts=["docs/wiki/llm/source-inventory.json", "docs/wiki/llm/15-source-inventory.md"],
            evidence=[
                f"llm_wiki_audit status={audit_status}",
                f"source_inventory_count={source_inventory_count}",
                f"source_page_count={source_page_count}",
            ],
            complete=external_research_complete,
            blockers=_missing_blockers(external_research),
        )
    )

    ab_decisions = {
        "multiple pages contain A/B decisions": ab_count >= 3,
        "maintenance A/B page exists": _exists(repo_root, WIKI_DIR / "14-maintenance-verification.md"),
        "runtime wiring A/B page exists": _exists(repo_root, WIKI_DIR / "18-runtime-wiring-checks.md"),
    }
    ab_decisions_complete = all(ab_decisions.values())
    items.append(
        _item(
            "A/B 비교: 둘 이상의 구현/운영안이 있을 때 비교표와 채택 결정을 문서화한다.",
            artifacts=["docs/wiki/llm/14-maintenance-verification.md", "docs/wiki/llm/18-runtime-wiring-checks.md"],
            evidence=[f"A/B decision page count={ab_count}", "A/B pages compare manual prose vs deterministic gates."],
            complete=ab_decisions_complete,
            blockers=_missing_blockers(ab_decisions),
        )
    )

    latest_reflection = {
        "code facts manifest exists": _exists(repo_root, CODE_FACTS),
        "config facts manifest exists": _exists(repo_root, CONFIG_FACTS),
        "code facts are populated": code_fact_count > 0,
        "config facts are populated": config_fact_count > 0,
        "unexpected manifest warnings are zero": unexpected_warning_count == 0,
    }
    latest_reflection_complete = all(latest_reflection.values())
    items.append(
        _item(
            "최신 반영: 코드/config/wiki 사실을 manifest로 재생성하고 unexpected drift를 0으로 유지한다.",
            artifacts=[
                "docs/wiki/llm/code-facts.json",
                "docs/wiki/llm/config-facts.json",
                "execution/llm_wiki_audit.py",
            ],
            evidence=[
                f"code_fact_count={code_fact_count}",
                f"config_fact_count={config_fact_count}",
                f"accepted_manifest_warning_count={accepted_warning_count}",
                f"unexpected_manifest_warning_count={unexpected_warning_count}",
            ],
            complete=latest_reflection_complete,
            blockers=_missing_blockers(latest_reflection),
        )
    )

    self_verify = {
        "audit script exists": _exists(repo_root, "execution/llm_wiki_audit.py"),
        "audit tests exist": _exists(repo_root, "workspace/tests/test_llm_wiki_audit.py"),
        "release summary helper exists": _exists(
            repo_root,
            ".agents/skills/auto-research/scripts/llm_wiki_release_summary.py",
        ),
        "release summary contract passes": release_summary_status == "pass",
    }
    self_verify_complete = all(self_verify.values())
    items.append(
        _item(
            "적용 및 검증: wiki 예시와 release evidence surface를 deterministic gate로 검증한다.",
            artifacts=[
                "execution/llm_wiki_audit.py",
                "workspace/tests/test_llm_wiki_audit.py",
                ".agents/skills/auto-research/scripts/llm_wiki_release_summary.py",
            ],
            evidence=[
                f"release_summary_contract_status={release_summary_status}",
                "strict release evidence and reviewer-summary helpers are referenced by the wiki audit contract.",
            ],
            complete=self_verify_complete,
            blockers=_missing_blockers(self_verify),
        )
    )

    cycle_reporting = {
        "handoff exists": bool(handoff),
        "tasks exist": bool(tasks),
        "session log exists": bool(session_log),
        "recent LLM Wiki or dirty-handoff cycle is recorded": _contains_any(ai_text, ("T-1606", "T-1607", "T-1608")),
    }
    cycle_reporting_complete = all(cycle_reporting.values())
    items.append(
        _item(
            "사이클 보고: 보강 후 HANDOFF/TASKS/SESSION_LOG에 결과, 검증, 다음 경계를 남긴다.",
            artifacts=[".ai/HANDOFF.md", ".ai/TASKS.md", ".ai/SESSION_LOG.md"],
            evidence=[
                "Current relay records T-1606 LLM Wiki pre-stage gates and later dirty-handoff gates.",
                f"selector_kind={selector_kind or 'unavailable'}",
            ],
            complete=cycle_reporting_complete,
            blockers=_missing_blockers(cycle_reporting),
        )
    )

    duplicate_drift = {
        "wiki audit passes": audit_status == "pass",
        "source/code/config manifests exist": all(
            _exists(repo_root, path) for path in (SOURCE_INVENTORY, CODE_FACTS, CONFIG_FACTS)
        ),
        "unexpected manifest warnings are zero": unexpected_warning_count == 0,
        "release summary contract passes": release_summary_status == "pass",
    }
    duplicate_drift_complete = all(duplicate_drift.values())
    items.append(
        _item(
            "중복/드리프트 방지: 출처, 코드 사실, config 사실, release-summary contract를 감사한다.",
            artifacts=[
                "execution/llm_wiki_audit.py",
                "docs/wiki/llm/source-inventory.json",
                "docs/wiki/llm/code-facts.json",
                "docs/wiki/llm/config-facts.json",
            ],
            evidence=[
                f"llm_wiki_audit status={audit_status}",
                f"unexpected_manifest_warning_count={unexpected_warning_count}",
                f"release_summary_contract_status={release_summary_status}",
            ],
            complete=duplicate_drift_complete,
            blockers=_missing_blockers(duplicate_drift),
        )
    )

    active_loop_blockers = ["Objective is an active autonomous loop until the user explicitly says stop."]
    if selector_kind:
        active_loop_blockers.append(f"Current selector boundary remains {selector_kind}.")
    if "T-251" in ai_text:
        active_loop_blockers.append("Workspace launch boundary still includes user-owned Hanwoo T-251.")
    items.append(
        _item(
            "종료 조건: 사용자가 중단을 말하기 전까지 루프는 complete로 주장하지 않는다.",
            artifacts=[".tmp/next-experiment.json", ".ai/HANDOFF.md", ".ai/GOAL.md"],
            evidence=[
                f"selector_kind={selector_kind or 'unavailable'}",
                "HANDOFF keeps the no-stage/no-commit/no-push/no-T-251-retry boundary visible.",
            ],
            complete=True,
            blockers=active_loop_blockers,
        )
    )

    complete_items = sum(1 for item in items if item["coverage"] == "complete" and not item["blockers"])
    blocked_items = sum(1 for item in items if item["blockers"])
    return {
        "schema_version": 1,
        "objective": (
            "LLM Wiki 자율 보강 루프: 0단계 현황 파악, gap 선정, 외부 조사, A/B 비교, 최신 반영, "
            "검증, 사이클 보고, 중복/드리프트 방지, 사용자가 멈추라고 할 때까지 반복"
        ),
        "generated_at": today.isoformat(),
        "audit_source": "execution/llm_wiki_objective_audit.py",
        "success_criteria": [
            "Every explicit loop requirement is mapped to concrete repo artifacts.",
            "The structural LLM Wiki audit remains green.",
            "The manifest remains incomplete while the autonomous loop or external/user-owned blockers remain active.",
        ],
        "summary": {
            "status": "blocked" if blocked_items else "complete",
            "item_count": len(items),
            "complete_item_count": complete_items,
            "blocked_item_count": blocked_items,
            "llm_wiki_audit_status": audit_status,
            "source_inventory_count": source_inventory_count,
            "ab_page_count": ab_count,
            "selector_kind": selector_kind,
        },
        "items": items,
    }


def _parse_today(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _print_text(manifest: dict[str, Any], output_path: Path) -> None:
    summary = manifest["summary"]
    print(f"status: {summary['status']}")
    print(f"objective: {manifest['objective']}")
    print(f"output: {output_path}")
    print(
        "summary: "
        f"{summary['complete_item_count']}/{summary['item_count']} complete, "
        f"{summary['blocked_item_count']} blocked, "
        f"llm_wiki_audit={summary['llm_wiki_audit_status']}, "
        f"selector={summary['selector_kind'] or 'unavailable'}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--today", type=str, default=None, help="Override today's date (YYYY-MM-DD).")
    parser.add_argument("--json", action="store_true", help="Emit the manifest JSON to stdout.")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    manifest = build_manifest(repo_root, today=_parse_today(args.today))
    output_path = _repo_output_path(repo_root, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        json.dump(manifest, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        _print_text(manifest, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
