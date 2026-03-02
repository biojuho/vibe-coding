from __future__ import annotations

import importlib
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BASE_FILES_TO_COMPILE = [
    ROOT / "joolife_hub.py",
    ROOT / "execution" / "content_db.py",
    ROOT / "execution" / "scheduler_engine.py",
    ROOT / "execution" / "shorts_daily_runner.py",
    ROOT / "execution" / "topic_auto_generator.py",
    ROOT / "execution" / "youtube_uploader.py",
    ROOT / "execution" / "bgm_downloader.py",
    ROOT / "execution" / "brand_asset_generator.py",
    ROOT / "execution" / "notion_client.py",
    ROOT / "execution" / "github_stats.py",
]

PERSONAL_AGENT_CANDIDATES = [
    ROOT / "personal-agent",
    ROOT / "_archive" / "personal-agent",
    ROOT / "projects" / "personal-agent",
]

MODULES_TO_IMPORT = [
    "execution.content_db",
    "execution.scheduler_engine",
    "execution.shorts_daily_runner",
    "execution.topic_auto_generator",
    "execution.youtube_uploader",
    "execution.bgm_downloader",
    "execution.brand_asset_generator",
    "execution.notion_client",
    "execution.github_stats",
]


def _resolve_personal_agent_root() -> Path | None:
    for candidate in PERSONAL_AGENT_CANDIDATES:
        if (candidate / "rag" / "query.py").exists() and (candidate / "utils" / "llm.py").exists():
            return candidate
    return None


def _files_to_compile() -> list[Path]:
    files = list(BASE_FILES_TO_COMPILE)
    pa_root = _resolve_personal_agent_root()
    if pa_root is None:
        print(
            "[SKIP] personal-agent checks skipped (not found in: "
            "personal-agent, _archive/personal-agent, projects/personal-agent)"
        )
        return files

    print(f"[INFO] personal-agent root: {pa_root}")
    files.append(pa_root / "rag" / "query.py")
    files.append(pa_root / "utils" / "llm.py")
    return files


def compile_files() -> list[str]:
    errors: list[str] = []
    for fp in _files_to_compile():
        try:
            py_compile.compile(str(fp), doraise=True)
            print(f"[OK] py_compile: {fp}")
        except Exception as exc:
            errors.append(f"py_compile failed: {fp} -> {exc}")
    return errors


def import_modules() -> list[str]:
    errors: list[str] = []
    for name in MODULES_TO_IMPORT:
        try:
            importlib.import_module(name)
            print(f"[OK] import: {name}")
        except Exception as exc:
            errors.append(f"import failed: {name} -> {exc}")
    return errors


def main() -> int:
    sys.path.insert(0, str(ROOT))
    errors = []
    errors.extend(compile_files())
    errors.extend(import_modules())

    if errors:
        print("\n[FAIL] Smoke check failed")
        for e in errors:
            print(f"- {e}")
        return 1
    print("\n[PASS] Smoke check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
