"""Lint workspace Agent Skill metadata and local references."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


REFERENCE_PATTERN = re.compile(r"`([^`\n]+\.(?:md|py|yaml|yml|json|toml|txt|ps1|bat|mjs|ts|tsx|js))`")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MIN_DESCRIPTION_LENGTH = 40


@dataclass(frozen=True)
class SkillFile:
    name: str
    relative_path: str
    absolute_path: Path
    frontmatter: dict[str, str]
    body: str
    read_error: str | None = None


def _round_score(value: float) -> int:
    return int(round(max(0, min(100, value))))


def _read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace"), "invalid UTF-8 bytes replaced"
    except OSError as exc:
        return "", str(exc)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    end_index = text.find("\n---", 4)
    if end_index == -1:
        return {}, text

    raw = text[4:end_index].strip("\n")
    body = text[end_index + 4 :].lstrip("\n")
    values: dict[str, str] = {}
    current_key: str | None = None
    multiline: list[str] = []

    def flush_multiline() -> None:
        nonlocal current_key, multiline
        if current_key is not None:
            values[current_key] = " ".join(line.strip() for line in multiline).strip()
        current_key = None
        multiline = []

    for line in raw.splitlines():
        if current_key is not None and (line.startswith(" ") or line.startswith("  ")):
            multiline.append(line)
            continue

        flush_multiline()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value in {">", ">-", "|", "|-"}:
            current_key = key
            multiline = []
        else:
            values[key] = value

    flush_multiline()
    return values, body


def discover_skill_files(
    repo_root: Path,
    skills_root: Path | None = None,
    *,
    include_archived: bool = False,
) -> list[SkillFile]:
    skills_root = skills_root or repo_root / ".agents" / "skills"
    if not skills_root.exists():
        return []

    result: list[SkillFile] = []
    for path in sorted(skills_root.rglob("SKILL.md")):
        if not include_archived and "_archive" in path.relative_to(skills_root).parts:
            continue
        text, error = _read_text(path)
        frontmatter, body = _parse_frontmatter(text)
        result.append(
            SkillFile(
                name=frontmatter.get("name", "") or path.parent.name,
                relative_path=path.relative_to(repo_root).as_posix(),
                absolute_path=path,
                frontmatter=frontmatter,
                body=body,
                read_error=error,
            )
        )
    return result


def _issue(skill: SkillFile, severity: str, code: str, message: str) -> dict[str, str]:
    return {
        "skill": skill.name,
        "path": skill.relative_path,
        "severity": severity,
        "code": code,
        "message": message,
    }


def _candidate_refs(text: str) -> set[str]:
    refs = set(REFERENCE_PATTERN.findall(text))
    for link in MARKDOWN_LINK_PATTERN.findall(text):
        if "://" in link or link.startswith("#"):
            continue
        clean = link.split("#", 1)[0].strip()
        if clean:
            refs.add(clean)
    return refs


def _reference_exists(repo_root: Path, skill_path: Path, reference: str) -> bool:
    clean = reference.strip().strip('"').strip("'").replace("\\", "/")
    if not clean or clean.startswith("$") or clean.startswith("<"):
        return True
    if " " in clean or clean.startswith("~") or re.search(r"\bYYYY\b", clean):
        return True
    if clean.startswith(("http://", "https://", "app://", "plugin://")):
        return True
    if re.match(r"^[A-Za-z]:/", clean):
        return True
    if clean.startswith("/"):
        candidate = repo_root / clean.lstrip("/")
        return candidate.exists()

    return (skill_path.parent / clean).exists() or (repo_root / clean).exists()


def lint_skills(repo_root: Path, skills: list[SkillFile]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    name_counts = Counter(skill.name.lower() for skill in skills)

    for skill in skills:
        if skill.read_error:
            issues.append(_issue(skill, "warning", "read_error", skill.read_error))

        if not skill.frontmatter:
            issues.append(_issue(skill, "error", "missing_frontmatter", "SKILL.md must start with YAML frontmatter."))

        name = skill.frontmatter.get("name", "").strip()
        description = skill.frontmatter.get("description", "").strip()
        if not name:
            issues.append(_issue(skill, "error", "missing_name", "Frontmatter is missing `name`."))
        if not description:
            issues.append(_issue(skill, "error", "missing_description", "Frontmatter is missing `description`."))
        elif len(description) < MIN_DESCRIPTION_LENGTH:
            issues.append(
                _issue(
                    skill,
                    "warning",
                    "short_description",
                    f"Description is under {MIN_DESCRIPTION_LENGTH} characters.",
                )
            )

        if name and name_counts[name.lower()] > 1:
            issues.append(_issue(skill, "warning", "duplicate_name", f"`{name}` is used by multiple skills."))

        trigger_text = f"{description}\n{skill.body}".lower()
        if "trigger" not in trigger_text and "use when" not in trigger_text and "사용" not in trigger_text:
            issues.append(
                _issue(
                    skill,
                    "warning",
                    "missing_trigger_guidance",
                    "Skill should state when an agent should use it.",
                )
            )

        for reference in sorted(_candidate_refs(skill.body)):
            if not _reference_exists(repo_root, skill.absolute_path, reference):
                issues.append(_issue(skill, "warning", "broken_reference", f"Referenced path not found: {reference}"))

    return issues


def build_report(
    repo_root: Path,
    *,
    skills_root: Path | None = None,
    include_archived: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    skills = discover_skill_files(repo_root, skills_root, include_archived=include_archived)
    issues = lint_skills(repo_root, skills)
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
    affected = {issue["path"] for issue in issues}
    healthy_count = max(0, len(skills) - len(affected))
    score = _round_score(100 - error_count * 15 - warning_count)
    if error_count:
        status = "fail"
    elif warning_count:
        status = "warn"
    else:
        status = "pass"

    by_code = Counter(issue["code"] for issue in issues)
    top_issues = [
        {"code": code, "count": count}
        for code, count in sorted(by_code.items(), key=lambda item: (-item[1], item[0]))[:8]
    ]

    return {
        "generated_at": (now or datetime.now(timezone.utc)).astimezone().isoformat(),
        "summary": {
            "status": status,
            "score": score,
            "skill_count": len(skills),
            "include_archived": include_archived,
            "healthy_count": healthy_count,
            "warning_count": warning_count,
            "error_count": error_count,
            "issue_count": len(issues),
        },
        "top_issues": top_issues,
        "issues": issues[:80],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skills-root", type=Path, default=None)
    parser.add_argument("--include-archived", action="store_true", help="Also lint skills under _archive folders.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "projects" / "knowledge-dashboard" / "data" / "skill_lint.json",
    )
    parser.add_argument("--json", action="store_true", help="Print the report JSON to stdout.")
    args = parser.parse_args()

    report = build_report(args.repo_root, skills_root=args.skills_root, include_archived=args.include_archived)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"Skill lint written to {args.output} ({report['summary']['status']}, score={report['summary']['score']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
