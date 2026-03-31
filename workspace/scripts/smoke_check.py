from __future__ import annotations

import importlib
import py_compile
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import resolve_workspace_legacy_root, workspace_path

ROOT = WORKSPACE_ROOT

BASE_FILES_TO_COMPILE = [
    workspace_path("execution", "joolife_hub.py"),
    workspace_path("execution", "content_db.py"),
    workspace_path("execution", "scheduler_engine.py"),
    workspace_path("execution", "shorts_daily_runner.py"),
    workspace_path("execution", "topic_auto_generator.py"),
    workspace_path("execution", "youtube_uploader.py"),
    workspace_path("execution", "bgm_downloader.py"),
    workspace_path("execution", "brand_asset_generator.py"),
    workspace_path("execution", "notion_client.py"),
    workspace_path("execution", "github_stats.py"),
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
    return resolve_workspace_legacy_root(required_paths=("rag/query.py", "utils/llm.py"))


def _files_to_compile() -> list[Path]:
    files = list(BASE_FILES_TO_COMPILE)
    pa_root = _resolve_personal_agent_root()
    if pa_root is None:
        print("[SKIP] legacy workspace-app checks skipped (checked workspace/personal-agent compatibility paths)")
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
