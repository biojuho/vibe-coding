from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from path_contract import REPO_ROOT, resolve_project_dir


@dataclass(frozen=True)
class BackupItem:
    name: str
    source: Path
    target_name: str
    required: bool = False


def default_items(root: Path, include_env: bool) -> list[BackupItem]:
    word_chain_dir = resolve_project_dir("word-chain", required_paths=("package.json",))
    items = [
        BackupItem(
            name="word_chain_db",
            source=word_chain_dir / "word_chain.db",
            target_name="word_chain.db",
            required=False,
        ),
    ]
    if include_env:
        items.append(
            BackupItem(
                name="workspace_env",
                source=REPO_ROOT / ".env",
                target_name="workspace.env",
                required=False,
            )
        )
    return items


def rotate_backups(backup_root: Path, keep: int) -> None:
    if keep < 1:
        return
    backup_dirs = sorted([p for p in backup_root.iterdir() if p.is_dir()], key=lambda p: p.name)
    excess = len(backup_dirs) - keep
    if excess <= 0:
        return
    for old in backup_dirs[:excess]:
        shutil.rmtree(old, ignore_errors=True)
        print(f"Removed old backup: {old}")


def run_backup(root: Path, backup_root: Path, include_env: bool, dry_run: bool) -> int:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = backup_root / timestamp
    items = default_items(root, include_env)

    copied: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    missing_required = False

    print(f"Backup root: {backup_root}")
    print(f"Backup target: {target_dir}")
    print(f"Dry run: {dry_run}")

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=False)

    for item in items:
        if not item.source.exists():
            status = {"name": item.name, "source": str(item.source), "reason": "not_found"}
            skipped.append(status)
            print(f"Skip: {item.name} (not found)")
            if item.required:
                missing_required = True
            continue

        destination = target_dir / item.target_name
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.source, destination)
        copied.append(
            {
                "name": item.name,
                "source": str(item.source),
                "target": str(destination),
            }
        )
        print(f"Copied: {item.name} -> {destination}")

    manifest = {
        "timestamp": timestamp,
        "root": str(root),
        "backup_root": str(backup_root),
        "dry_run": dry_run,
        "copied": copied,
        "skipped": skipped,
    }

    if not dry_run:
        manifest_path = target_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Manifest written: {manifest_path}")

    if missing_required:
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup critical project data files.")
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="Workspace root path (default: current workspace root).",
    )
    parser.add_argument(
        "--backup-dir",
        default="backups",
        help="Backup directory name or absolute path (default: backups).",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=20,
        help="Number of backup directories to keep after backup (default: 20).",
    )
    parser.add_argument(
        "--with-env",
        action="store_true",
        help="Include the workspace root .env in backup.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview backup actions without copying files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Error: root path does not exist: {root}", file=sys.stderr)
        return 1

    backup_dir_arg = Path(args.backup_dir)
    backup_root = backup_dir_arg.resolve() if backup_dir_arg.is_absolute() else (root / backup_dir_arg).resolve()
    backup_root.mkdir(parents=True, exist_ok=True)

    code = run_backup(
        root=root,
        backup_root=backup_root,
        include_env=args.with_env,
        dry_run=args.dry_run,
    )

    if not args.dry_run and args.keep > 0:
        rotate_backups(backup_root, args.keep)

    return code


if __name__ == "__main__":
    raise SystemExit(main())
