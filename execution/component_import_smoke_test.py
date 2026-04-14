"""
Hanwoo Dashboard Component Import Smoke Test

This tool verifies that all `@/` alias imports in the hanwoo-dashboard
project resolve to actual files on disk. It catches broken imports
that would cause build failures BEFORE running `next build`.

Usage:
    python execution/component_import_smoke_test.py
    python execution/component_import_smoke_test.py --strict  # exit 1 on failures
    python execution/component_import_smoke_test.py --verbose  # show all resolved imports

Design:
    - stdlib only (no external dependencies)
    - Parses static ES module import statements via regex
    - Resolves @/ alias to src/ directory
    - Checks .js, .mjs, .jsx, .ts, .tsx, /index.js resolution
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Project root for hanwoo-dashboard
PROJECT_ROOT = Path(__file__).resolve().parent.parent / "projects" / "hanwoo-dashboard"
SRC_DIR = PROJECT_ROOT / "src"

# Regex to capture import paths from ES module imports
# Matches: import ... from '@/...' and import ... from "@/..."
IMPORT_PATTERN = re.compile(
    r"""(?:import\s+.*?\s+from\s+|import\s*\()['"](@/[^'"]+)['"]""",
    re.MULTILINE,
)

# Also capture dynamic imports: dynamic(() => import('@/...'))
DYNAMIC_IMPORT_PATTERN = re.compile(
    r"""import\s*\(\s*['"](@/[^'"]+)['"]\s*\)""",
    re.MULTILINE,
)

# File extensions to try when resolving imports
RESOLVE_EXTENSIONS = [".js", ".jsx", ".ts", ".tsx", ".mjs"]
INDEX_FILES = [f"index{ext}" for ext in RESOLVE_EXTENSIONS]

# External packages (not file imports) - skip these
EXTERNAL_PREFIXES = [
    "react",
    "next",
    "lucide-react",
    "recharts",
    "xlsx",
    "qrcode",
]


def find_source_files(src_dir: Path) -> list[Path]:
    """Find all JS/TS source files in the src directory."""
    patterns = ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.mjs"]
    files = []
    for pattern in patterns:
        files.extend(src_dir.glob(pattern))
    # Exclude test files, node_modules, and __prefixed fixtures
    return [
        f
        for f in files
        if "node_modules" not in str(f)
        and ".next" not in str(f)
        and not f.name.endswith(".test.js")
        and not f.name.endswith(".test.mjs")
        and not f.name.endswith(".test.ts")
        and not f.name.startswith("__")
    ]


def extract_imports(file_path: Path) -> list[tuple[str, int]]:
    """Extract @/ aliased imports from a file.

    Returns list of (import_path, line_number) tuples.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    imports = []
    for line_num, line in enumerate(content.split("\n"), 1):
        # Static imports
        for match in IMPORT_PATTERN.finditer(line):
            imports.append((match.group(1), line_num))
        # Dynamic imports
        for match in DYNAMIC_IMPORT_PATTERN.finditer(line):
            imports.append((match.group(1), line_num))

    return imports


def resolve_import(import_path: str, src_dir: Path) -> Path | None:
    """Resolve an @/ import path to a file on disk.

    Resolution order:
    1. Exact path (e.g., @/lib/utils.js -> src/lib/utils.js)
    2. Path + extension (e.g., @/lib/utils -> src/lib/utils.js)
    3. Directory + index (e.g., @/lib -> src/lib/index.js)
    """
    # Strip the @/ prefix
    relative = import_path.removeprefix("@/")
    base = src_dir / relative

    # 1. Exact path
    if base.is_file():
        return base

    # 2. Try extensions
    for ext in RESOLVE_EXTENSIONS:
        candidate = base.with_suffix(ext)
        if candidate.is_file():
            return candidate

    # 3. Directory + index file
    if base.is_dir():
        for index_file in INDEX_FILES:
            candidate = base / index_file
            if candidate.is_file():
                return candidate

    return None


def run_smoke_test(
    src_dir: Path,
    verbose: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Run the import smoke test.

    Returns (resolved, unresolved) lists of import info dicts.
    """
    source_files = find_source_files(src_dir)
    resolved = []
    unresolved = []

    for file_path in sorted(source_files):
        imports = extract_imports(file_path)
        for import_path, line_num in imports:
            result = resolve_import(import_path, src_dir)
            info = {
                "source": str(file_path.relative_to(src_dir)),
                "import": import_path,
                "line": line_num,
                "resolved_to": str(result.relative_to(src_dir)) if result else None,
            }
            if result:
                resolved.append(info)
            else:
                unresolved.append(info)

    return resolved, unresolved


def format_results(
    resolved: list[dict],
    unresolved: list[dict],
    verbose: bool = False,
) -> str:
    """Format test results as a readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("  Component Import Smoke Test - hanwoo-dashboard")
    lines.append("=" * 60)

    total = len(resolved) + len(unresolved)
    lines.append(f"  Total imports scanned: {total}")
    lines.append(f"  Resolved: {len(resolved)}")
    lines.append(f"  Unresolved: {len(unresolved)}")

    if unresolved:
        lines.append("")
        lines.append("  [FAILURES]")
        for item in unresolved:
            lines.append(
                f"    X {item['source']}:{item['line']}"
                f" -> {item['import']}"
            )
        lines.append("")
        lines.append("  Fix: Check that the imported file exists in src/")
    else:
        lines.append("")
        lines.append("  [ALL PASSED] All @/ imports resolve to existing files.")

    if verbose and resolved:
        lines.append("")
        lines.append("  [RESOLVED IMPORTS]")
        for item in resolved:
            lines.append(
                f"    {item['source']}:{item['line']}"
                f" -> {item['resolved_to']}"
            )

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Verify @/ imports in hanwoo-dashboard resolve to files"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit code 1 on unresolved imports",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show all resolved imports too",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Override project root path",
    )

    args = parser.parse_args()

    src_dir = SRC_DIR
    if args.project_root:
        src_dir = Path(args.project_root) / "src"

    if not src_dir.exists():
        print(f"Error: src directory not found: {src_dir}")
        sys.exit(1)

    resolved, unresolved = run_smoke_test(src_dir, verbose=args.verbose)
    print(format_results(resolved, unresolved, verbose=args.verbose))

    if args.strict and unresolved:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
