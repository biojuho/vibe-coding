from __future__ import annotations

from pathlib import Path
from typing import Iterable

WORKSPACE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = WORKSPACE_ROOT.parent
PROJECTS_ROOT = REPO_ROOT / "projects"
INFRASTRUCTURE_ROOT = REPO_ROOT / "infrastructure"
TMP_ROOT = REPO_ROOT / ".tmp"

PROJECT_ALIASES = {
    "word-chain-pygame": "word-chain",
}


def workspace_path(*parts: str) -> Path:
    return WORKSPACE_ROOT.joinpath(*parts)


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


def project_name_variants(name: str) -> list[str]:
    alias = PROJECT_ALIASES.get(name, name)
    variants = [alias]
    if name != alias:
        variants.append(name)
    return variants


def project_candidates(name: str) -> list[Path]:
    candidates: list[Path] = []
    for variant in project_name_variants(name):
        candidates.append(PROJECTS_ROOT / variant)
        candidates.append(REPO_ROOT / variant)
        candidates.append(REPO_ROOT / "_archive" / variant)
    return candidates


def resolve_project_dir(name: str, required_paths: Iterable[str] = ()) -> Path:
    required = tuple(required_paths)
    for candidate in project_candidates(name):
        if not candidate.exists():
            continue
        if all((candidate / rel).exists() for rel in required):
            return candidate
    return PROJECTS_ROOT / PROJECT_ALIASES.get(name, name)


def legacy_workspace_candidates() -> list[Path]:
    return [
        WORKSPACE_ROOT,
        REPO_ROOT / "personal-agent",
        REPO_ROOT / "_archive" / "personal-agent",
        PROJECTS_ROOT / "personal-agent",
    ]


def resolve_workspace_legacy_root(required_paths: Iterable[str] = ()) -> Path | None:
    required = tuple(required_paths)
    for candidate in legacy_workspace_candidates():
        if not candidate.exists():
            continue
        if all((candidate / rel).exists() for rel in required):
            return candidate
    return None
