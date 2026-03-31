"""Deterministic repository map builder for agentic coding workflows.

The map is intentionally compact: file path, language, summary, top-level
symbols, imports, and a simple relevance score. This lets the orchestration
layer choose related files without sending full source files to the LLM.
"""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from path_contract import REPO_ROOT
from execution._logging import logger

_ALLOWED_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".txt",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
}

_EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".turbo",
    ".tmp",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    "coverage",
}

_SYMBOL_LINE_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
_IMPORT_LINE_RE = re.compile(
    r"""^\s*(?:from\s+([A-Za-z0-9_./-]+)\s+import|import\s+([A-Za-z0-9_.,\s]+)|(?:import|export)\s+.*?from\s+["']([^"']+)["'])""",
    re.MULTILINE,
)
_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+")


@dataclass(slots=True)
class RepoMapEntry:
    relative_path: str
    absolute_path: Path
    language: str
    line_count: int
    module_summary: str
    symbols: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def to_context_block(self) -> str:
        lines = [f"File: {self.relative_path}"]
        lines.append(f"Language: {self.language}, lines: {self.line_count}, score: {self.score:.1f}")
        if self.module_summary:
            lines.append(f"Summary: {self.module_summary}")
        if self.symbols:
            lines.append("Symbols: " + ", ".join(self.symbols[:6]))
        if self.imports:
            lines.append("Imports: " + ", ".join(self.imports[:6]))
        if self.reasons:
            lines.append("Matched by: " + ", ".join(self.reasons[:5]))
        return "\n".join(lines)


class RepoMapBuilder:
    """Build a lightweight repository map for selective context loading."""

    def __init__(
        self,
        repo_root: Path | None = None,
        *,
        include_roots: Iterable[str] = ("workspace", "projects"),
        max_file_bytes: int = 200_000,
    ) -> None:
        self.repo_root = Path(repo_root or REPO_ROOT).resolve()
        self.include_roots = tuple(dict.fromkeys(str(root).strip("/\\") for root in include_roots if str(root).strip()))
        self.max_file_bytes = max_file_bytes
        self._cache: dict[Path, tuple[int, int, RepoMapEntry]] = {}

    def collect_changed_files(self) -> set[str]:
        """Return git working-tree paths relative to the repo root."""
        try:
            proc = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=normal"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except Exception as exc:
            logger.debug("[RepoMap] git status unavailable: %s", exc)
            return set()

        if proc.returncode != 0:
            return set()

        changed: set[str] = set()
        for raw_line in proc.stdout.splitlines():
            if len(raw_line) < 4:
                continue
            path_text = raw_line[3:].strip()
            if " -> " in path_text:
                path_text = path_text.split(" -> ", 1)[1]
            normalized = path_text.replace("\\", "/").strip()
            if normalized:
                changed.add(normalized)
        return changed

    def build(
        self,
        query: str,
        *,
        changed_files: Iterable[str] | None = None,
        include_roots: Iterable[str] | None = None,
        max_files: int = 12,
    ) -> list[RepoMapEntry]:
        query_tokens = self._query_tokens(query)
        changed = {self._normalize_relative(path) for path in (changed_files or [])}
        roots = tuple(
            dict.fromkeys(str(root).strip("/\\") for root in (include_roots or self.include_roots) if str(root).strip())
        )

        entries: list[RepoMapEntry] = []
        for path in self._iter_source_files(roots):
            entry = self._analyze_file(path)
            if entry is None:
                continue
            entry.score, entry.reasons = self._score_entry(entry, query_tokens, changed)
            if entry.score > 0:
                entries.append(entry)

        if not entries and changed:
            for rel_path in sorted(changed):
                candidate = self.repo_root / rel_path
                entry = self._analyze_file(candidate)
                if entry is None:
                    continue
                entry.score = 0.5
                entry.reasons = ["working tree change"]
                entries.append(entry)

        entries.sort(key=lambda item: (-item.score, item.relative_path))
        return entries[:max_files]

    def _iter_source_files(self, roots: Iterable[str]) -> Iterable[Path]:
        for root_name in roots:
            root = self.repo_root / root_name
            if root.is_file():
                if self._is_source_file(root):
                    yield root
                continue
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file() and self._is_source_file(path):
                    yield path

    def _is_source_file(self, path: Path) -> bool:
        if path.suffix.lower() not in _ALLOWED_SUFFIXES:
            return False
        if path.stat().st_size > self.max_file_bytes:
            return False
        if any(part in _EXCLUDED_DIRS for part in path.parts):
            return False
        return True

    def _analyze_file(self, path: Path) -> RepoMapEntry | None:
        try:
            stat = path.stat()
        except OSError:
            return None

        cache_key = (stat.st_mtime_ns, stat.st_size)
        cached = self._cache.get(path)
        if cached and cached[:2] == cache_key:
            return cached[2]

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

        relative_path = self._normalize_relative(path.relative_to(self.repo_root))
        language = self._language_for_suffix(path.suffix)
        line_count = text.count("\n") + 1 if text else 0

        if path.suffix.lower() == ".py":
            module_summary, symbols, imports = self._analyze_python_text(text)
        else:
            module_summary, symbols, imports = self._analyze_text_file(text)

        entry = RepoMapEntry(
            relative_path=relative_path,
            absolute_path=path,
            language=language,
            line_count=line_count,
            module_summary=module_summary,
            symbols=symbols,
            imports=imports,
        )
        self._cache[path] = (cache_key[0], cache_key[1], entry)
        return entry

    @staticmethod
    def _language_for_suffix(suffix: str) -> str:
        return {
            ".py": "python",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".ini": "ini",
            ".cfg": "config",
            ".txt": "text",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".js": "javascript",
            ".jsx": "jsx",
        }.get(suffix.lower(), suffix.lower().lstrip("."))

    @staticmethod
    def _normalize_relative(path: str | Path) -> str:
        return str(path).replace("\\", "/")

    @staticmethod
    def _query_tokens(query: str) -> set[str]:
        tokens: set[str] = set()
        for raw in _TOKEN_RE.findall(query.lower()):
            for part in re.split(r"[/._-]+", raw):
                if len(part) >= 3:
                    tokens.add(part)
        return tokens

    @staticmethod
    def _analyze_python_text(text: str) -> tuple[str, list[str], list[str]]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return RepoMapBuilder._analyze_text_file(text)

        module_summary = ast.get_docstring(tree) or ""
        summary_line = module_summary.strip().splitlines()[0] if module_summary.strip() else ""
        symbols: list[str] = []
        imports: list[str] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append(node.name)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")

        return summary_line[:160], symbols[:12], imports[:12]

    @staticmethod
    def _analyze_text_file(text: str) -> tuple[str, list[str], list[str]]:
        summary_line = ""
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if stripped and not stripped.startswith(("#", "//", "/*", "*")):
                summary_line = stripped[:160]
                break

        symbols = [match.group(1) for match in _SYMBOL_LINE_RE.finditer(text)][:12]
        imports: list[str] = []
        for match in _IMPORT_LINE_RE.finditer(text):
            import_group = next((group for group in match.groups() if group), "")
            if not import_group:
                continue
            cleaned = import_group.split(",")[0].strip()
            if cleaned:
                imports.append(cleaned)

        return summary_line, symbols, imports[:12]

    @staticmethod
    def _score_entry(entry: RepoMapEntry, query_tokens: set[str], changed_files: set[str]) -> tuple[float, list[str]]:
        path_text = entry.relative_path.lower()
        basename = Path(entry.relative_path).stem.lower()
        summary_text = entry.module_summary.lower()
        symbols_text = " ".join(entry.symbols).lower()
        imports_text = " ".join(entry.imports).lower()

        score = 0.0
        reasons: list[str] = []
        for token in sorted(query_tokens):
            if token == basename:
                score += 4.0
                reasons.append(f"path:{token}")
            elif token in path_text:
                score += 2.5
                reasons.append(f"path:{token}")

            if token in symbols_text:
                score += 3.0
                reasons.append(f"symbol:{token}")
            if token in summary_text:
                score += 1.5
                reasons.append(f"summary:{token}")
            if token in imports_text:
                score += 1.0
                reasons.append(f"import:{token}")

        if entry.relative_path in changed_files:
            score += 2.0 if score > 0 else 0.5
            reasons.append("working tree change")

        if ("/tests/" in path_text or basename.startswith("test_")) and (
            "test" in query_tokens or "pytest" in query_tokens
        ):
            score += 1.5
            reasons.append("test-adjacent")

        return score, list(dict.fromkeys(reasons))
