"""Selective repository context builder for the coding graph."""

from __future__ import annotations

from dataclasses import dataclass, field

from execution.repo_map import RepoMapBuilder


@dataclass(slots=True)
class SelectedContext:
    text: str
    files: list[str] = field(default_factory=list)
    truncated: bool = False
    changed_files: list[str] = field(default_factory=list)


class ContextSelector:
    """Build a compact, ranked repository context string within a budget."""

    def __init__(
        self,
        repo_map: RepoMapBuilder | None = None,
        *,
        budget_chars: int = 2800,
        max_files: int = 6,
    ) -> None:
        self.repo_map = repo_map or RepoMapBuilder()
        self.budget_chars = budget_chars
        self.max_files = max_files

    def select(
        self,
        query: str,
        *,
        existing_context: str = "",
        budget_chars: int | None = None,
        max_files: int | None = None,
        include_roots: tuple[str, ...] | None = None,
    ) -> SelectedContext:
        budget = budget_chars or self.budget_chars
        limit = max_files or self.max_files
        roots = include_roots or self._infer_roots(query, existing_context)
        changed_files = sorted(self.repo_map.collect_changed_files())
        candidates = self.repo_map.build(
            query,
            changed_files=changed_files,
            include_roots=roots,
            max_files=max(limit * 3, limit),
        )

        blocks = ["Repository map relevant to the current task:"]
        selected_files: list[str] = []
        truncated = False
        relevant_changes: list[str] = []

        for entry in candidates:
            if len(selected_files) >= limit:
                truncated = True
                break
            block = entry.to_context_block()
            candidate_text = "\n\n".join([*blocks, block])
            if len(candidate_text) > budget and selected_files:
                truncated = True
                break
            blocks.append(block)
            selected_files.append(entry.relative_path)
            if entry.relative_path in changed_files:
                relevant_changes.append(entry.relative_path)

        if not selected_files:
            return SelectedContext(text="", files=[], truncated=False, changed_files=[])

        if relevant_changes:
            blocks.append("Relevant working tree changes: " + ", ".join(relevant_changes[:4]))

        return SelectedContext(
            text="\n\n".join(blocks),
            files=selected_files,
            truncated=truncated,
            changed_files=relevant_changes,
        )

    def _infer_roots(self, query: str, existing_context: str) -> tuple[str, ...]:
        haystack = f"{query}\n{existing_context}".lower()
        roots: list[str] = []

        if any(token in haystack for token in ("workspace/", "graph_engine", "workers.py", "directive", "execution/")):
            roots.append("workspace")
        if "infrastructure/" in haystack or "mcp" in haystack:
            roots.append("infrastructure")
        if "projects/" in haystack:
            roots.append("projects")

        projects_root = self.repo_map.repo_root / "projects"
        if projects_root.exists():
            for project_dir in projects_root.iterdir():
                if project_dir.is_dir() and project_dir.name.lower() in haystack:
                    roots.append("projects")
                    break

        if not roots:
            roots.append("workspace")

        return tuple(dict.fromkeys(roots))
