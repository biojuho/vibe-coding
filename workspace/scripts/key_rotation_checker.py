"""API Key Rotation Checker.

Reads .env.meta for last rotation dates and sends Telegram alerts
for keys older than the threshold (default 90 days).

Usage:
    python workspace/scripts/key_rotation_checker.py           # check all keys
    python workspace/scripts/key_rotation_checker.py --dry-run  # print only, no Telegram
    python workspace/scripts/key_rotation_checker.py --days 60  # custom threshold
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

META_PATH = ROOT / ".env.meta"
DEFAULT_THRESHOLD_DAYS = 90


def load_meta(path: Path) -> dict[str, datetime]:
    """Parse .env.meta into {KEY_NAME: last_rotation_date}."""
    entries: dict[str, datetime] = {}
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        try:
            entries[key] = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            print(f"[WARN] Invalid date for {key}: {value!r}")
    return entries


def check_rotations(
    meta: dict[str, datetime],
    threshold_days: int = DEFAULT_THRESHOLD_DAYS,
) -> list[dict]:
    """Return list of keys needing rotation."""
    now = datetime.now()
    threshold = timedelta(days=threshold_days)
    alerts = []
    for key, last_rotated in sorted(meta.items()):
        age = now - last_rotated
        if age > threshold:
            alerts.append(
                {
                    "key": key,
                    "last_rotated": last_rotated.strftime("%Y-%m-%d"),
                    "age_days": age.days,
                    "overdue_days": age.days - threshold_days,
                }
            )
    return alerts


def format_report(alerts: list[dict], threshold_days: int) -> str:
    """Format a human-readable report."""
    if not alerts:
        return f"All API keys are within the {threshold_days}-day rotation window."

    lines = [f"[KEY ROTATION] {len(alerts)} key(s) overdue (>{threshold_days} days):\n"]
    for a in alerts:
        lines.append(f"  {a['key']}: {a['age_days']}d old (rotated {a['last_rotated']}, {a['overdue_days']}d overdue)")
    lines.append("\nAction: Rotate these keys and update .env.meta")
    return "\n".join(lines)


def update_meta(path: Path, key: str) -> None:
    """Update a key's rotation date to today."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(key + "="):
            lines[i] = f"{key}={today}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={today}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Updated {key} rotation date to {today}")


def main() -> None:
    parser = argparse.ArgumentParser(description="API Key Rotation Checker")
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_THRESHOLD_DAYS,
        help=f"Rotation threshold in days (default: {DEFAULT_THRESHOLD_DAYS})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print report only, don't send Telegram")
    parser.add_argument("--update", type=str, metavar="KEY_NAME", help="Mark a key as rotated today")
    args = parser.parse_args()

    if args.update:
        update_meta(META_PATH, args.update)
        return

    meta = load_meta(META_PATH)
    if not meta:
        print(f"No entries found in {META_PATH}")
        return

    alerts = check_rotations(meta, args.days)
    report = format_report(alerts, args.days)
    print(report)

    if alerts and not args.dry_run:
        try:
            from execution.telegram_notifier import send_alert

            send_alert(report, level="WARNING")
            print("\nTelegram alert sent.")
        except Exception as e:
            print(f"\nTelegram alert failed: {e}")


if __name__ == "__main__":
    main()
