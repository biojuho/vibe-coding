"""
Error pattern analyzer for Joolife Hub.

Analyzes errors from debug_history_db, .tmp/failures/ snapshots,
and .tmp/watchdog_history.json to detect recurring patterns and
generate weekly reports.

Usage (CLI):
    python workspace/execution/error_analyzer.py analyze
    python workspace/execution/error_analyzer.py report
    python workspace/execution/error_analyzer.py report --send
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from execution.debug_history_db import list_entries, get_stats
except ImportError:
    list_entries = None  # type: ignore[assignment]
    get_stats = None  # type: ignore[assignment]

try:
    from execution.telegram_notifier import send_alert
except ImportError:
    send_alert = None  # type: ignore[assignment]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TMP_DIR = _PROJECT_ROOT / ".tmp"
_FAILURES_DIR = _TMP_DIR / "failures"
_WATCHDOG_PATH = _TMP_DIR / "watchdog_history.json"

# Error category classification rules (keyword -> category)
_CATEGORY_RULES: List[tuple[list[str], str]] = [
    (["timeout", "timed out", "TimeoutError", "asyncio.TimeoutError"], "api_timeout"),
    (["selector", "Selector", "locator", "element not found"], "selector_failure"),
    (["cost", "budget", "CostExceeded", "RPD", "rate limit", "429"], "cost_exceeded"),
    (["auth", "401", "token expired", "PermissionError", "OAuth"], "auth_expired"),
    (["network", "ConnectionError", "ConnectionRefused", "DNS", "ssl"], "network"),
]


def _classify_error(text: str) -> str:
    """Classify an error string into a category."""
    lower = text.lower()
    for keywords, category in _CATEGORY_RULES:
        if any(kw.lower() in lower for kw in keywords):
            return category
    return "other"


def _parse_iso(dt_str: str) -> Optional[datetime]:
    """Parse an ISO datetime string, returning naive-local datetime on success."""
    try:
        dt = datetime.fromisoformat(dt_str)
        # aware → naive-local 변환으로 비교 일관성 확보
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def _load_watchdog_errors(days: int) -> List[Dict[str, Any]]:
    """Load error entries from watchdog_history.json within the lookback window."""
    if not _WATCHDOG_PATH.exists():
        return []
    try:
        data = json.loads(_WATCHDOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    cutoff = datetime.now() - timedelta(days=days)
    results: List[Dict[str, Any]] = []
    items = data if isinstance(data, list) else data.get("history", [])
    for item in items:
        ts = _parse_iso(item.get("timestamp", item.get("time", "")))
        if ts and ts >= cutoff:
            results.append(item)
    return results


def _load_failure_snapshots(days: int) -> List[Dict[str, Any]]:
    """Load error snapshots from .tmp/failures/ directory."""
    if not _FAILURES_DIR.is_dir():
        return []
    cutoff = datetime.now() - timedelta(days=days)
    results: List[Dict[str, Any]] = []
    for path in _FAILURES_DIR.glob("*.json"):
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
            ts = _parse_iso(snap.get("timestamp", snap.get("time", "")))
            if ts is not None and ts >= cutoff:
                results.append(snap)
        except (json.JSONDecodeError, OSError):
            continue
    return results


def analyze_recent_errors(days: int = 7) -> Dict[str, Any]:
    """Analyze errors from the last N days grouped by category.

    Returns:
        Dict with keys: total, by_category, top_modules, period_days, entries_source.
    """
    cutoff = datetime.now() - timedelta(days=days)
    category_counts: Counter[str] = Counter()
    module_counts: Counter[str] = Counter()
    entries_found = 0

    # Source 1: debug_history_db
    if list_entries is not None:
        try:
            entries = list_entries(limit=500)
            for entry in entries:
                ts = _parse_iso(entry.get("created_at", ""))
                if ts and ts < cutoff:
                    continue
                entries_found += 1
                symptom = entry.get("symptom", "")
                category_counts[_classify_error(symptom)] += 1
                module = entry.get("module", "")
                if module:
                    module_counts[module] += 1
        except Exception:
            pass

    # Source 2: .tmp/failures/ snapshots
    for snap in _load_failure_snapshots(days):
        entries_found += 1
        error_text = snap.get("error", snap.get("message", ""))
        category_counts[_classify_error(error_text)] += 1
        module = snap.get("module", snap.get("source", ""))
        if module:
            module_counts[module] += 1

    # Source 3: watchdog_history.json
    for item in _load_watchdog_errors(days):
        entries_found += 1
        error_text = item.get("error", item.get("message", item.get("detail", "")))
        category_counts[_classify_error(error_text)] += 1
        module = item.get("module", item.get("task", ""))
        if module:
            module_counts[module] += 1

    return {
        "total": entries_found,
        "by_category": dict(category_counts.most_common()),
        "top_modules": [{"module": m, "count": c} for m, c in module_counts.most_common(3)],
        "period_days": days,
    }


def detect_recurring_patterns(min_occurrences: int = 3) -> List[Dict[str, Any]]:
    """Find errors that recur min_occurrences+ times in the last 7 days.

    Returns:
        List of dicts with: error_type, count, last_seen, affected_modules.
    """
    days = 7
    cutoff = datetime.now() - timedelta(days=days)

    # Collect (error_type, module, timestamp) tuples
    records: List[tuple[str, str, str]] = []

    if list_entries is not None:
        try:
            for entry in list_entries(limit=500):
                ts = _parse_iso(entry.get("created_at", ""))
                if ts and ts < cutoff:
                    continue
                category = _classify_error(entry.get("symptom", ""))
                records.append(
                    (
                        category,
                        entry.get("module", ""),
                        entry.get("created_at", ""),
                    )
                )
        except Exception:
            pass

    for snap in _load_failure_snapshots(days):
        error_text = snap.get("error", snap.get("message", ""))
        records.append(
            (
                _classify_error(error_text),
                snap.get("module", snap.get("source", "")),
                snap.get("timestamp", snap.get("time", "")),
            )
        )

    for item in _load_watchdog_errors(days):
        error_text = item.get("error", item.get("message", item.get("detail", "")))
        records.append(
            (
                _classify_error(error_text),
                item.get("module", item.get("task", "")),
                item.get("timestamp", item.get("time", "")),
            )
        )

    # Group by error_type
    grouped: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "last_seen": "", "modules": set()})
    for error_type, module, ts_str in records:
        g = grouped[error_type]
        g["count"] += 1
        if ts_str > g["last_seen"]:
            g["last_seen"] = ts_str
        if module:
            g["modules"].add(module)

    patterns: List[Dict[str, Any]] = []
    for error_type, info in grouped.items():
        if info["count"] >= min_occurrences:
            patterns.append(
                {
                    "error_type": error_type,
                    "count": info["count"],
                    "last_seen": info["last_seen"],
                    "affected_modules": sorted(info["modules"]),
                }
            )
    patterns.sort(key=lambda p: p["count"], reverse=True)
    return patterns


def generate_weekly_report() -> str:
    """Generate a human-readable weekly error report in Markdown."""
    now = datetime.now()
    current = analyze_recent_errors(days=7)
    previous = analyze_recent_errors(days=14)

    # Trend: compare current week vs previous week (previous 14d minus current 7d)
    prev_only_total = max(previous["total"] - current["total"], 0)
    if prev_only_total == 0:
        trend = "NEW (no prior data)"
    elif current["total"] > prev_only_total:
        pct = round((current["total"] - prev_only_total) / prev_only_total * 100)
        trend = f"UP +{pct}% ({prev_only_total} -> {current['total']})"
    elif current["total"] < prev_only_total:
        pct = round((prev_only_total - current["total"]) / prev_only_total * 100)
        trend = f"DOWN -{pct}% ({prev_only_total} -> {current['total']})"
    else:
        trend = f"FLAT ({current['total']})"

    # Severity breakdown from debug_history_db stats
    severity_lines = ""
    if get_stats is not None:
        try:
            stats = get_stats()
            by_sev = stats.get("by_severity", {})
            if by_sev:
                severity_lines = "\n".join(f"  - {sev}: {cnt}" for sev, cnt in sorted(by_sev.items()))
        except Exception:
            pass

    # Recurring patterns
    patterns = detect_recurring_patterns(min_occurrences=3)
    pattern_lines = ""
    if patterns:
        rows = []
        for p in patterns[:10]:
            mods = ", ".join(p["affected_modules"][:5]) or "(unknown)"
            rows.append(f"| {p['error_type']} | {p['count']} | {p['last_seen'][:16]} | {mods} |")
        pattern_lines = "| Category | Count | Last Seen | Modules |\n| --- | --- | --- | --- |\n" + "\n".join(rows)
    else:
        pattern_lines = "(no recurring patterns detected)"

    # Category breakdown
    cat_lines = ""
    by_cat = current.get("by_category", {})
    if by_cat:
        cat_lines = "\n".join(f"  - {cat}: {cnt}" for cat, cnt in sorted(by_cat.items(), key=lambda x: -x[1]))
    else:
        cat_lines = "  (none)"

    # Top modules
    top_mod_lines = ""
    top_mods = current.get("top_modules", [])
    if top_mods:
        top_mod_lines = "\n".join(f"  - {m['module']}: {m['count']}" for m in top_mods)
    else:
        top_mod_lines = "  (none)"

    report = f"""# Weekly Error Report

**Period**: {(now - timedelta(days=7)).strftime("%Y-%m-%d")} ~ {now.strftime("%Y-%m-%d")}
**Generated**: {now.strftime("%Y-%m-%d %H:%M")}

## Summary

- **Total errors**: {current["total"]}
- **Trend vs previous week**: {trend}

## By Severity
{severity_lines or "  (no data)"}

## By Category
{cat_lines}

## Top Error Modules
{top_mod_lines}

## Recurring Patterns (3+ occurrences)
{pattern_lines}
"""
    return report.strip()


def send_report_telegram(report: str) -> bool:
    """Send the weekly report via Telegram using the telegram_notifier module.

    Returns:
        True if sent successfully, False otherwise.
    """
    if send_alert is None:
        print("[error_analyzer] telegram_notifier not available", file=sys.stderr)
        return False
    try:
        send_alert(report, level="INFO")
        return True
    except Exception as exc:
        print(f"[error_analyzer] Telegram send failed: {exc}", file=sys.stderr)
        return False


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Joolife Error Pattern Analyzer")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("analyze", help="Show error analysis for last 7 days")

    report_p = sub.add_parser("report", help="Generate weekly error report")
    report_p.add_argument("--send", action="store_true", help="Send via Telegram")

    args = parser.parse_args()

    if args.command == "analyze":
        analysis = analyze_recent_errors(days=7)
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
        print()
        patterns = detect_recurring_patterns(min_occurrences=3)
        if patterns:
            print("Recurring patterns:")
            print(json.dumps(patterns, indent=2, ensure_ascii=False))
        else:
            print("No recurring patterns detected.")
        return 0

    if args.command == "report":
        report = generate_weekly_report()
        print(report)
        if args.send:
            ok = send_report_telegram(report)
            if ok:
                print("\n[OK] Report sent via Telegram.")
            else:
                print("\n[FAIL] Could not send report via Telegram.", file=sys.stderr)
                return 1
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
