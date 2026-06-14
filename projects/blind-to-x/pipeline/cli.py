"""Command Line Interface and orchestration."""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from config import ConfigManager
from config import as_bool as _as_bool
from pipeline import NotificationManager, NotionUploader, TwitterPoster
from pipeline.bootstrap import check_budget, init_components, init_scrapers, resolve_input_sources
from pipeline.runner import execute_pipeline, handle_single_commands
from scripts.source_browser_probe import (
    DEFAULT_FAILURE_REPORT_DIR,
    DEFAULT_SOURCES,
    exit_code_for_report,
    run_source_preflight,
)

logger = logging.getLogger(__name__)

_LOCK_FILE = Path(".tmp/.running.lock")
_LOCK_MAX_AGE_SECONDS = 3600  # 1시간 초과 lock은 stale로 간주
_SOURCE_PREFLIGHT_DEFAULTS = {
    "source_preflight_timeout_ms": 12000,
    "source_preflight_output": Path(".tmp/source_browser_preflight.json"),
    "source_preflight_screenshot_dir": Path("screenshots/source_preflight"),
    "source_preflight_failure_dir": DEFAULT_FAILURE_REPORT_DIR,
    "source_preflight_trace_dir": None,
    "source_preflight_click_through": False,
    "source_preflight_use_recommended": False,
}
_SOURCE_PREFLIGHT_SAFETY_DEFAULTS = {
    "read_only": True,
    "notion_writes": False,
    "x_posts": False,
    "auto_apply_allowed": False,
    "manual_strategy_review_required": True,
}
_SOURCE_PREFLIGHT_FLAGS = {
    "source_preflight_timeout_ms": ("--source-preflight-timeout-ms",),
    "source_preflight_output": ("--source-preflight-output",),
    "source_preflight_screenshot_dir": ("--source-preflight-screenshot-dir",),
    "source_preflight_failure_dir": ("--source-preflight-failure-dir",),
    "source_preflight_trace_dir": ("--source-preflight-trace-dir",),
    "source_preflight_click_through": ("--source-preflight-click-through",),
    "source_preflight_use_recommended": ("--source-preflight-use-recommended",),
}
_SOURCE_PREFLIGHT_LOG_NAMES = {
    "source_preflight_timeout_ms": "timeout_ms",
    "source_preflight_output": "output_path",
    "source_preflight_screenshot_dir": "screenshot_dir",
    "source_preflight_failure_dir": "failure_dir",
    "source_preflight_trace_dir": "trace_dir",
    "source_preflight_click_through": "click_through",
    "source_preflight_use_recommended": "use_recommended_source",
}


def build_parser():
    parser = argparse.ArgumentParser(description="Blind to X Automation Pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--urls", nargs="+", help="Specific URLs to process")
    parser.add_argument("--trending", action="store_true", help="Fetch trending posts automatically")
    parser.add_argument("--popular", action="store_true", help="Fetch popular posts automatically")
    parser.add_argument("--limit", type=int, help="Limit number of posts (default from config)")
    parser.add_argument("--dry-run", action="store_true", help="Scrape and generate drafts without uploading")
    parser.add_argument(
        "--parallel", type=int, default=3, metavar="N", help="Process up to N posts concurrently (default: 3)"
    )
    parser.add_argument(
        "--source",
        default="auto",
        help=(
            "Source scraper to use. Use 'auto' for configured primary/input_sources, "
            "or 'multi'/'all' for all input_sources."
        ),
    )
    parser.add_argument(
        "--source-preflight",
        action="store_true",
        help="Probe configured source pages in a browser and exit before pipeline work.",
    )
    parser.add_argument(
        "--source-preflight-fail-on-problem",
        action="store_true",
        help="Exit with status 1 when any browser-probed source is not ready.",
    )
    parser.add_argument(
        "--source-preflight-print-options",
        action="store_true",
        help="Print resolved source preflight options as JSON without launching a browser.",
    )
    parser.add_argument(
        "--require-source-ready",
        action="store_true",
        help="Run source browser preflight before normal pipeline work and abort if any source is not ready.",
    )
    parser.add_argument(
        "--source-preflight-timeout-ms",
        type=int,
        default=12000,
        help="Browser source preflight navigation timeout in milliseconds.",
    )
    parser.add_argument(
        "--source-preflight-output",
        type=Path,
        default=Path(".tmp/source_browser_preflight.json"),
        help="Write the source preflight JSON report to this path.",
    )
    parser.add_argument(
        "--source-preflight-screenshot-dir",
        type=Path,
        default=Path("screenshots/source_preflight"),
        help="Directory for source preflight full-page screenshots.",
    )
    parser.add_argument(
        "--source-preflight-failure-dir",
        type=Path,
        default=DEFAULT_FAILURE_REPORT_DIR,
        help="Directory for source preflight problem JSON failure reports and HTML snapshots.",
    )
    parser.add_argument(
        "--source-preflight-trace-dir",
        type=Path,
        default=None,
        help="Optional directory for source preflight Playwright trace.zip evidence; retained only on problems.",
    )
    parser.add_argument(
        "--source-preflight-headed",
        action="store_true",
        help="Run source preflight with a visible browser window.",
    )
    parser.add_argument(
        "--source-preflight-click-through",
        action="store_true",
        help=(
            "During source preflight, click the first visible post, fall back to the canonical detail URL "
            "when the click is obstructed, and verify detail page readability."
        ),
    )
    parser.add_argument(
        "--source-preflight-use-recommended",
        action="store_true",
        help=(
            "With --require-source-ready, continue with summary.recommended_source when at least one "
            "source is ready even if other configured sources are blocked."
        ),
    )
    parser.add_argument(
        "--source-preflight-viewport",
        choices=("desktop", "mobile"),
        default="desktop",
        help="Browser viewport profile for source preflight.",
    )
    parser.add_argument("--review-only", action="store_true", help="Queue items for review without publishing")
    parser.add_argument("--reprocess-approved", action="store_true", help="Publish approved Notion items only")
    parser.add_argument(
        "--review-queue-report",
        action="store_true",
        help="Print a read-only Notion review queue report for X publish operations",
    )
    parser.add_argument(
        "--review-queue-lookback-days",
        type=int,
        default=None,
        help="Lookback window for --review-queue-report (default: config or 30)",
    )
    parser.add_argument(
        "--review-queue-stale-days",
        type=int,
        default=None,
        help="Ready-to-post age threshold for --review-queue-report (default: config or 3)",
    )
    parser.add_argument(
        "--review-queue-action-limit",
        type=int,
        default=None,
        help="Maximum operator actions to include in --review-queue-report (default: config or 10)",
    )
    parser.add_argument(
        "--review-queue-ready-attention-limit",
        type=int,
        default=None,
        help="Maximum Ready to Post attention items to include in --review-queue-report (default: config or 3)",
    )
    parser.add_argument(
        "--review-queue-report-output",
        type=Path,
        default=None,
        help="JSON artifact path for --review-queue-report (default: config or .tmp/review_queue_report_latest.json)",
    )
    parser.add_argument(
        "--review-queue-report-fail-on-warning",
        action="store_true",
        help="Exit non-zero when --review-queue-report severity is warning or critical",
    )
    parser.add_argument(
        "--newsletter-build", action="store_true", help="Build newsletter edition from approved Notion items"
    )
    parser.add_argument(
        "--newsletter-preview", action="store_true", help="Preview newsletter edition without publishing"
    )
    parser.add_argument("--digest", action="store_true", help="Generate and send daily digest")
    parser.add_argument("--digest-date", type=str, default=None, help="Digest date (YYYY-MM-DD, default: today)")
    parser.add_argument("--sentiment-report", action="store_true", help="Show current emotion trends")
    return parser


def _is_process_alive(pid: int) -> bool:
    """Windows/Unix 호환 프로세스 생존 확인."""
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True  # Windows
    except (OSError, ValueError):
        return False


def acquire_lock() -> bool:
    """Acquire the run lock. Returns True if lock acquired, False if already running."""
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _LOCK_FILE.exists():
        try:
            lock_content = _LOCK_FILE.read_text().strip()
            parts = lock_content.split(":", 1)
            pid = int(parts[0])
            lock_ts = float(parts[1]) if len(parts) > 1 else 0.0
            lock_age = time.time() - lock_ts if lock_ts else float("inf")

            if lock_age > _LOCK_MAX_AGE_SECONDS:
                logger.warning("Stale lock 감지 (%.0f초 경과, PID=%s). 덮어씁니다.", lock_age, pid)
            elif _is_process_alive(pid):
                logger.warning("이미 실행 중인 프로세스가 있습니다 (PID=%s). 종료합니다.", pid)
                return False
            else:
                logger.info("프로세스 %s 종료됨. Stale lock 제거.", pid)
        except (ValueError, IndexError):
            pass
    _LOCK_FILE.write_text(f"{os.getpid()}:{time.time()}")
    return True


def _resolve_source_preflight_sources(config_mgr, args) -> list[str]:
    resolved_sources = resolve_input_sources(config_mgr, args)
    source_names = [source for source in resolved_sources if source in DEFAULT_SOURCES]
    unsupported_sources = [source for source in resolved_sources if source not in DEFAULT_SOURCES]
    if unsupported_sources:
        logger.warning("Skipping unsupported source preflight targets: %s", ", ".join(unsupported_sources))
    return source_names


def _source_preflight_requested(args) -> bool:
    return bool(
        getattr(args, "source_preflight", False)
        or getattr(args, "require_source_ready", False)
        or getattr(args, "source_preflight_print_options", False)
    )


def _source_preflight_should_continue(args, exit_code: int) -> bool:
    return bool(getattr(args, "require_source_ready", False) and exit_code == 0)


def _mark_source_preflight_cli_overrides(args, argv: list[str] | None = None):
    tokens = sys.argv[1:] if argv is None else argv
    supplied_flags = {str(token).split("=", 1)[0] for token in tokens}
    supplied_dests = {
        dest for dest, flags in _SOURCE_PREFLIGHT_FLAGS.items() if any(flag in supplied_flags for flag in flags)
    }
    args._source_preflight_cli_overrides = supplied_dests
    return args


def _source_preflight_cli_overrode(args, dest: str) -> bool:
    supplied = getattr(args, "_source_preflight_cli_overrides", None)
    if isinstance(supplied, set):
        return dest in supplied
    default = _SOURCE_PREFLIGHT_DEFAULTS.get(dest)
    return getattr(args, dest, default) != default


def _config_value(config_mgr, key: str):
    if config_mgr is None or not hasattr(config_mgr, "get"):
        return None
    try:
        return config_mgr.get(key, None)
    except Exception:
        return None


def _source_preflight_option_origin(config_mgr, args, dest: str, config_key: str) -> str:
    if _source_preflight_cli_overrode(args, dest):
        return "cli"
    configured = _config_value(config_mgr, config_key)
    if configured in (None, ""):
        return "default"
    return "config"


def _resolve_source_preflight_path(config_mgr, args, dest: str, config_key: str) -> Path | None:
    current = getattr(args, dest, _SOURCE_PREFLIGHT_DEFAULTS[dest])
    if _source_preflight_cli_overrode(args, dest):
        return current
    configured = _config_value(config_mgr, config_key)
    if configured in (None, ""):
        return current
    return configured if isinstance(configured, Path) else Path(str(configured))


def _resolve_source_preflight_int(config_mgr, args, dest: str, config_key: str) -> int:
    current = getattr(args, dest, _SOURCE_PREFLIGHT_DEFAULTS[dest])
    if _source_preflight_cli_overrode(args, dest):
        return int(current)
    configured = _config_value(config_mgr, config_key)
    if configured in (None, ""):
        return int(current)
    try:
        return int(configured)
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid %s=%r; using %s.", config_key, configured, current)
        return int(current)


def _resolve_source_preflight_bool(config_mgr, args, dest: str, config_key: str) -> bool:
    current = bool(getattr(args, dest, _SOURCE_PREFLIGHT_DEFAULTS[dest]))
    if _source_preflight_cli_overrode(args, dest):
        return current
    configured = _config_value(config_mgr, config_key)
    if configured in (None, ""):
        return current
    if isinstance(configured, bool):
        return configured
    if isinstance(configured, str):
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    return bool(configured)


def _resolve_source_preflight_config_bool(config_mgr, config_key: str, default: bool) -> bool:
    configured = _config_value(config_mgr, config_key)
    if configured in (None, ""):
        return default
    if isinstance(configured, bool):
        return configured
    if isinstance(configured, str):
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    return bool(configured)


def _resolve_source_preflight_safety(config_mgr) -> dict[str, bool]:
    return {
        key: _resolve_source_preflight_config_bool(config_mgr, f"source_preflight.safety.{key}", default)
        for key, default in _SOURCE_PREFLIGHT_SAFETY_DEFAULTS.items()
    }


def _resolve_source_preflight_options(config_mgr, args) -> dict[str, object]:
    origins = {
        "timeout_ms": _source_preflight_option_origin(
            config_mgr,
            args,
            "source_preflight_timeout_ms",
            "source_preflight.timeout_ms",
        ),
        "output_path": _source_preflight_option_origin(
            config_mgr,
            args,
            "source_preflight_output",
            "source_preflight.output_path",
        ),
        "screenshot_dir": _source_preflight_option_origin(
            config_mgr,
            args,
            "source_preflight_screenshot_dir",
            "source_preflight.screenshot_dir",
        ),
        "failure_dir": _source_preflight_option_origin(
            config_mgr,
            args,
            "source_preflight_failure_dir",
            "source_preflight.failure_dir",
        ),
        "trace_dir": _source_preflight_option_origin(
            config_mgr,
            args,
            "source_preflight_trace_dir",
            "source_preflight.trace_dir",
        ),
        "click_through": _source_preflight_option_origin(
            config_mgr,
            args,
            "source_preflight_click_through",
            "source_preflight.click_through_default",
        ),
        "use_recommended_source": _source_preflight_option_origin(
            config_mgr,
            args,
            "source_preflight_use_recommended",
            "source_preflight.use_recommended_source_default",
        ),
    }
    return {
        "timeout_ms": max(
            1000,
            _resolve_source_preflight_int(
                config_mgr,
                args,
                "source_preflight_timeout_ms",
                "source_preflight.timeout_ms",
            ),
        ),
        "output_path": _resolve_source_preflight_path(
            config_mgr,
            args,
            "source_preflight_output",
            "source_preflight.output_path",
        ),
        "screenshot_dir": _resolve_source_preflight_path(
            config_mgr,
            args,
            "source_preflight_screenshot_dir",
            "source_preflight.screenshot_dir",
        ),
        "failure_dir": _resolve_source_preflight_path(
            config_mgr,
            args,
            "source_preflight_failure_dir",
            "source_preflight.failure_dir",
        ),
        "trace_dir": _resolve_source_preflight_path(
            config_mgr,
            args,
            "source_preflight_trace_dir",
            "source_preflight.trace_dir",
        ),
        "click_through": _resolve_source_preflight_bool(
            config_mgr,
            args,
            "source_preflight_click_through",
            "source_preflight.click_through_default",
        ),
        "use_recommended_source": _resolve_source_preflight_bool(
            config_mgr,
            args,
            "source_preflight_use_recommended",
            "source_preflight.use_recommended_source_default",
        ),
        "safety": _resolve_source_preflight_safety(config_mgr),
        "origins": origins,
    }


def _source_preflight_log_value(value) -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, Path):
        return value.as_posix()
    return str(value)


def _source_preflight_summary_value(value):
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _source_preflight_option_summary(sources: list[str], args, options: dict[str, object]) -> dict[str, object]:
    origins = options.get("origins") if isinstance(options.get("origins"), dict) else {}
    safety = options.get("safety") if isinstance(options.get("safety"), dict) else _SOURCE_PREFLIGHT_SAFETY_DEFAULTS
    supplied = getattr(args, "_source_preflight_cli_overrides", set())
    cli_overrides = (
        sorted(_SOURCE_PREFLIGHT_LOG_NAMES.get(dest, dest) for dest in supplied) if isinstance(supplied, set) else []
    )
    config_defaults = sorted(key for key, origin in origins.items() if origin == "config")
    return {
        "sources": sources,
        "timeout_ms": options.get("timeout_ms"),
        "output_path": _source_preflight_summary_value(options.get("output_path")),
        "screenshot_dir": _source_preflight_summary_value(options.get("screenshot_dir")),
        "failure_dir": _source_preflight_summary_value(options.get("failure_dir")),
        "trace_dir": _source_preflight_summary_value(options.get("trace_dir")),
        "viewport": getattr(args, "source_preflight_viewport", "desktop"),
        "headed": bool(getattr(args, "source_preflight_headed", False)),
        "click_through": bool(options.get("click_through")),
        "use_recommended_source": bool(options.get("use_recommended_source")),
        "origins": origins,
        "cli_overrides": cli_overrides,
        "config_defaults": config_defaults,
        "browser_probe_will_run": False,
        "notion_writes": bool(safety.get("notion_writes", False)),
        "x_posts": bool(safety.get("x_posts", False)),
        "read_only": bool(safety.get("read_only", True)),
        "auto_apply_allowed": bool(safety.get("auto_apply_allowed", False)),
        "manual_strategy_review_required": bool(safety.get("manual_strategy_review_required", True)),
    }


def _log_source_preflight_effective_options(sources: list[str], args, options: dict[str, object]) -> None:
    origins = options.get("origins") if isinstance(options.get("origins"), dict) else {}
    config_defaults = ",".join(sorted(key for key, origin in origins.items() if origin == "config")) or "-"
    supplied = getattr(args, "_source_preflight_cli_overrides", set())
    cli_overrides = (
        ",".join(sorted(_SOURCE_PREFLIGHT_LOG_NAMES.get(dest, dest) for dest in supplied))
        if isinstance(supplied, set) and supplied
        else "-"
    )
    logger.info(
        (
            "Source preflight effective options: sources=%s; timeout_ms=%s; output_path=%s; "
            "screenshot_dir=%s; failure_dir=%s; trace_dir=%s; viewport=%s; headed=%s; "
            "click_through=%s; use_recommended_source=%s; config_defaults=%s; cli_overrides=%s"
        ),
        ",".join(sources),
        options.get("timeout_ms"),
        _source_preflight_log_value(options.get("output_path")),
        _source_preflight_log_value(options.get("screenshot_dir")),
        _source_preflight_log_value(options.get("failure_dir")),
        _source_preflight_log_value(options.get("trace_dir")),
        getattr(args, "source_preflight_viewport", "desktop"),
        bool(getattr(args, "source_preflight_headed", False)),
        options.get("click_through"),
        options.get("use_recommended_source"),
        config_defaults,
        cli_overrides,
    )


def _apply_recommended_source_fallback(args, report: dict) -> str | None:
    if not getattr(args, "require_source_ready", False):
        return None
    if not getattr(args, "source_preflight_use_recommended", False):
        return None

    summary = report.get("summary", {})
    recommended_source = summary.get("recommended_source") if isinstance(summary, dict) else None
    if not isinstance(recommended_source, str) or not recommended_source:
        return None
    ready_sources = summary.get("ready_sources") if isinstance(summary, dict) else None
    if not isinstance(ready_sources, list) or recommended_source not in ready_sources:
        logger.warning(
            "Ignoring source preflight recommended source %s because it is not listed as ready.",
            recommended_source,
        )
        return None

    args.source = recommended_source
    logger.info("Continuing with source preflight recommended source: %s", recommended_source)
    return recommended_source


def _compact_log_value(value, max_chars: int = 160) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _log_ready_source_warnings(report: dict) -> int:
    summary = report.get("summary", {})
    ready_warnings = summary.get("ready_warnings") if isinstance(summary, dict) else None
    if not isinstance(ready_warnings, list):
        return 0

    logged_count = 0
    for warning in ready_warnings:
        if not isinstance(warning, dict):
            continue
        source = _compact_log_value(warning.get("source") or "unknown")
        warning_type = _compact_log_value(warning.get("type") or "warning")
        count = warning.get("count")
        sample = _compact_log_value(warning.get("sample"))
        action = _compact_log_value(warning.get("action"))
        parts = [f"source={source}", f"type={warning_type}"]
        if isinstance(count, int):
            parts.append(f"count={count}")
        if sample:
            parts.append(f"sample={sample}")
        if action:
            parts.append(f"action={action}")
        logger.warning("Source preflight ready warning: %s", "; ".join(parts))
        logged_count += 1
    return logged_count


def _format_source_preflight_evidence(evidence: dict) -> list[str]:
    evidence_order = (
        "failure_report_path",
        "screenshot_path",
        "html_snapshot_path",
        "trace_path",
        "click_screenshot_path",
        "exception_type",
        "error",
        "click_error",
    )
    parts: list[str] = []
    for key in evidence_order:
        value = evidence.get(key)
        if value:
            parts.append(f"{key}={_compact_log_value(value)}")
    for key, value in sorted(evidence.items()):
        if key not in evidence_order and value:
            parts.append(f"{_compact_log_value(key)}={_compact_log_value(value)}")
    return parts


def _log_source_preflight_problem_actions(report: dict) -> int:
    summary = report.get("summary", {})
    problem_actions = summary.get("problem_actions") if isinstance(summary, dict) else None
    if not isinstance(problem_actions, list):
        return 0

    logged_count = 0
    for action_item in problem_actions:
        if not isinstance(action_item, dict):
            continue
        source = _compact_log_value(action_item.get("source") or "unknown")
        status = _compact_log_value(action_item.get("status") or "problem")
        action = _compact_log_value(action_item.get("action"))
        parts = [f"source={source}", f"status={status}"]
        if "operator_action_required" in action_item:
            parts.append(
                f"operator_action_required={str(_as_bool(action_item.get('operator_action_required'))).lower()}"
            )
        if action:
            parts.append(f"action={action}")
        evidence = action_item.get("evidence")
        if isinstance(evidence, dict):
            parts.extend(_format_source_preflight_evidence(evidence))
        review_order = action_item.get("evidence_review_order")
        if isinstance(review_order, list) and review_order:
            parts.append(f"evidence_review_order={_compact_log_value(','.join(str(item) for item in review_order))}")
        repair_commands = action_item.get("repair_commands")
        if isinstance(repair_commands, list) and repair_commands:
            command_text = " | ".join(str(command) for command in repair_commands if command)
            if command_text:
                parts.append(f"repair_commands={_compact_log_value(command_text, max_chars=600)}")
        logger.warning("Source preflight problem action: %s", "; ".join(parts))
        logged_count += 1
    return logged_count


async def run_source_preflight_command(config_mgr, args) -> int | None:
    if not _source_preflight_requested(args):
        return None

    sources = _resolve_source_preflight_sources(config_mgr, args)
    if not sources:
        logger.error("No supported source preflight targets resolved for source=%s.", getattr(args, "source", "auto"))
        return 1

    options = _resolve_source_preflight_options(config_mgr, args)
    if options["use_recommended_source"]:
        args.source_preflight_use_recommended = True
    if getattr(args, "source_preflight_print_options", False):
        summary = _source_preflight_option_summary(sources, args, options)
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    _log_source_preflight_effective_options(sources, args, options)

    report = await run_source_preflight(
        sources=sources,
        custom_urls=None,
        timeout_ms=options["timeout_ms"],
        output_path=options["output_path"],
        screenshot_dir=options["screenshot_dir"],
        failure_dir=options["failure_dir"],
        trace_dir=options["trace_dir"],
        headed=getattr(args, "source_preflight_headed", False),
        viewport=getattr(args, "source_preflight_viewport", "desktop"),
        click_through=options["click_through"],
    )
    _log_ready_source_warnings(report)
    _log_source_preflight_problem_actions(report)
    if _apply_recommended_source_fallback(args, report):
        return 0

    fail_on_problem = getattr(args, "source_preflight_fail_on_problem", False) or getattr(
        args, "require_source_ready", False
    )
    return exit_code_for_report(report, fail_on_problem=fail_on_problem)


async def run_main():
    parser = build_parser()
    args = parser.parse_args()
    _mark_source_preflight_cli_overrides(args)

    if not acquire_lock():
        return

    try:
        config_mgr = ConfigManager(args.config)
    except Exception:
        logger.warning("Could not load %s. Using empty config.", args.config)
        config_mgr = ConfigManager("nonexistent")
        config_mgr.config = {}

    if _source_preflight_requested(args):
        source_preflight_exit = 1
        try:
            source_preflight_exit = await run_source_preflight_command(config_mgr, args)
        finally:
            normalized_preflight_exit = 0 if source_preflight_exit is None else source_preflight_exit
            if not _source_preflight_should_continue(args, normalized_preflight_exit):
                _LOCK_FILE.unlink(missing_ok=True)
        source_preflight_exit = 0 if source_preflight_exit is None else source_preflight_exit
        if not _source_preflight_should_continue(args, source_preflight_exit):
            sys.exit(source_preflight_exit)

    notifier = NotificationManager(config_mgr)
    notion_uploader = NotionUploader(config_mgr)
    twitter_poster = TwitterPoster(config_mgr)

    # ── Harness preflight security check ─────────────────────────────────
    try:
        from pipeline.harness_guard import is_harness_enabled, run_preflight

        if is_harness_enabled():
            preflight_result = run_preflight()
            if not preflight_result["passed"]:
                logger.error("Harness preflight failed. Aborting pipeline.")
                await notifier.send_message(
                    f"Blind-to-X harness preflight FAILED\nIssues: {len(preflight_result['issues'])}건",
                    level="CRITICAL",
                )
                sys.exit(1)
            elif not preflight_result["skipped"]:
                logger.info("Harness preflight passed.")
    except Exception as exc:
        logger.warning("Harness preflight check error (non-fatal): %s", exc)

    if await handle_single_commands(args, config_mgr, notifier, notion_uploader, twitter_poster):
        _LOCK_FILE.unlink(missing_ok=True)
        single_command_exit_code = int(getattr(args, "_single_command_exit_code", 0) or 0)
        if single_command_exit_code:
            sys.exit(single_command_exit_code)
        return

    scrapers = init_scrapers(config_mgr, args)
    if not scrapers:
        logger.error("No valid scrapers found.")
        sys.exit(1)

    cost_tracker = await check_budget(config_mgr, notifier)
    image_uploader, image_generator, draft_generator, top_examples, trend_monitor = await init_components(
        args, config_mgr, scrapers, notion_uploader, cost_tracker
    )

    try:
        await execute_pipeline(
            args,
            config_mgr,
            scrapers,
            notifier,
            notion_uploader,
            twitter_poster,
            image_uploader,
            image_generator,
            draft_generator,
            top_examples,
            trend_monitor,
        )
    except Exception as exc:
        logger.exception("Critical error in main: %s", exc)
        await notifier.send_message(f"Blind-to-X pipeline crash\nError: `{exc}`", level="CRITICAL")
        sys.exit(1)
    finally:
        _LOCK_FILE.unlink(missing_ok=True)
