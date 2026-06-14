#!/usr/bin/env python3
"""Probe Blind-to-X source pages with Playwright before running the pipeline."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

DEFAULT_SOURCES: dict[str, str] = {
    "blind": "https://www.teamblind.com/kr/topics/trending",
    "fmkorea": "https://www.fmkorea.com/best",
    "jobplanet": "https://www.jobplanet.co.kr/api/v5/community/posts?limit=20&order_by=recent",
    "ppomppu": "https://www.ppomppu.co.kr/hot.php",
}
DEFAULT_FAILURE_REPORT_DIR = Path(".tmp/failures/source_preflight")
ALL_SOURCE_ALIASES = frozenset({"all", "auto", "multi"})

_JOBPLANET_BASE_URL = "https://www.jobplanet.co.kr"
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_POWERSHELL_ARG_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./:\\=-")

READY_STATUS = "ready"
PROBLEM_STATUSES = {
    "blocked",
    "browser_error",
    "browser_unavailable",
    "click_error",
    "empty",
    "http_error",
    "login_wall",
    "timeout",
}

_BLOCKED_PATTERNS = (
    "access denied",
    "automated",
    "bot detection",
    "captcha",
    "cf-error",
    "checking your browser",
    "cloudflare",
    "ddos",
    "enable cookies",
    "unusual traffic",
    "verify you are human",
    "비정상",
    "보안 문자",
    "보안문자",
    "보안 시스템",
    "자동입력",
    "접근이 차단",
    "차단되었습니다",
)

_LOGIN_WALL_PATTERNS = (
    "login required",
    "log in to continue",
    "members only",
    "please log in",
    "sign in to continue",
    "로그인 후",
    "로그인이 필요",
    "로그인해야",
    "회원만",
)

_BROWSER_UNAVAILABLE_PATTERNS = (
    "browser executable",
    "executable doesn't exist",
    "no module named 'playwright.",
    "no module named 'playwright'",
    'no module named "playwright.',
    'no module named "playwright"',
    "playwright install",
    "unable to launch browser",
)


@dataclass(frozen=True)
class ProbeTarget:
    source: str
    url: str


@dataclass(frozen=True)
class ProbeClassification:
    status: str
    reason: str
    signals: list[str]


@dataclass(frozen=True)
class ClickThroughResult:
    ok: bool
    candidate_text: str | None
    candidate_href: str | None
    final_url: str
    title: str
    body_chars: int
    screenshot_path: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class ProbeResult:
    source: str
    url: str
    final_url: str
    http_status: int | None
    title: str
    body_chars: int
    classification: ProbeClassification
    console_errors: list[str]
    page_errors: list[str]
    screenshot_path: str | None = None
    click_through: ClickThroughResult | None = None
    error: str | None = None
    exception_type: str | None = None
    html_snapshot_path: str | None = None
    trace_path: str | None = None
    failure_report_path: str | None = None
    operator_action_required: bool = False
    operator_action: str | None = None


def _compact_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _has_any(text: str, patterns: tuple[str, ...]) -> list[str]:
    lower = text.lower()
    return [pattern for pattern in patterns if pattern in lower]


def classify_probe(
    *,
    http_status: int | None,
    title: str = "",
    body_text: str = "",
    error: str | None = None,
) -> ProbeClassification:
    """Classify a source probe without requiring Playwright or network access."""
    compact_body = _compact_text(body_text)
    compact_title = _compact_text(title)
    search_text = f"{compact_title}\n{compact_body}"

    if error:
        error_text = error.lower()
        if "timeout" in error_text:
            return ProbeClassification("timeout", "navigation timed out", ["timeout"])
        browser_signals = _has_any(error_text, _BROWSER_UNAVAILABLE_PATTERNS)
        if browser_signals:
            return ProbeClassification(
                "browser_unavailable",
                "Playwright browser is not installed or cannot launch",
                browser_signals,
            )
        return ProbeClassification("browser_error", "browser probe failed", [error[:160]])

    if http_status in {401, 403, 429, 430}:
        return ProbeClassification("blocked", f"HTTP {http_status}", [f"http_{http_status}"])
    if http_status is not None and http_status >= 400:
        return ProbeClassification("http_error", f"HTTP {http_status}", [f"http_{http_status}"])

    blocked_signals = _has_any(search_text, _BLOCKED_PATTERNS)
    if blocked_signals:
        return ProbeClassification("blocked", "bot or access-control copy detected", blocked_signals)

    login_signals = _has_any(search_text, _LOGIN_WALL_PATTERNS)
    if login_signals:
        return ProbeClassification("login_wall", "login wall copy detected", login_signals)

    if len(compact_body) < 120 and len(compact_title) < 8:
        return ProbeClassification(
            "empty",
            "page has too little readable text",
            [f"body_chars={len(compact_body)}", f"title_chars={len(compact_title)}"],
        )

    return ProbeClassification(READY_STATUS, "page returned readable content", [])


def parse_targets(sources: list[str] | None, custom_urls: list[str] | None) -> list[ProbeTarget]:
    """Resolve source names and name=url overrides into deterministic targets."""
    selected = sources or list(DEFAULT_SOURCES)
    targets: list[ProbeTarget] = []

    for source in selected:
        if source in ALL_SOURCE_ALIASES:
            targets.extend(ProbeTarget(source=name, url=url) for name, url in DEFAULT_SOURCES.items())
            continue
        if source in DEFAULT_SOURCES:
            targets.append(ProbeTarget(source=source, url=DEFAULT_SOURCES[source]))
            continue
        if source.startswith(("http://", "https://")):
            targets.append(ProbeTarget(source=_source_name_from_url(source), url=source))
            continue
        raise SystemExit(f"unknown source '{source}'. Known sources: {', '.join(sorted(DEFAULT_SOURCES))}")

    for raw in custom_urls or []:
        if "=" not in raw:
            raise SystemExit("--url must use name=https://example form")
        name, url = raw.split("=", 1)
        name = name.strip()
        url = url.strip()
        if not name or not url.startswith(("http://", "https://")):
            raise SystemExit("--url must use name=https://example form")
        targets.append(ProbeTarget(source=name, url=url))

    deduped: dict[tuple[str, str], ProbeTarget] = {}
    for target in targets:
        deduped[(target.source, target.url)] = target
    return list(deduped.values())


def build_report(results: list[ProbeResult], *, viewport: str = "desktop") -> dict[str, Any]:
    summary = _build_summary(results, viewport=viewport)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "results": [_result_to_dict(result) for result in results],
    }


def _build_summary(results: list[ProbeResult], *, viewport: str = "desktop") -> dict[str, Any]:
    statuses = Counter(result.classification.status for result in results)
    ready_results = [result for result in results if result.classification.status == READY_STATUS]
    ready_sources = [result.source for result in ready_results]
    problem_sources = [
        {
            "source": result.source,
            "status": result.classification.status,
            "reason": result.classification.reason,
            "signals": result.classification.signals,
        }
        for result in results
        if result.classification.status != READY_STATUS
    ]
    ready_warnings = [warning for result in ready_results for warning in _build_ready_warnings(result)]
    recommended_source = _recommend_ready_source(ready_results)
    problem_actions = [
        _build_problem_action(result, viewport=viewport)
        for result in results
        if result.classification.status != READY_STATUS
    ]
    problem_evidence_sources = [action["source"] for action in problem_actions if action.get("evidence")]
    return {
        "source_count": len(results),
        "viewport": viewport,
        "ready_count": len(ready_sources),
        "problem_count": len(problem_sources),
        "problem_evidence_count": len(problem_evidence_sources),
        "ready_warning_count": len(ready_warnings),
        "ok": bool(results) and len(ready_sources) == len(results),
        "statuses": dict(sorted(statuses.items())),
        "ready_sources": ready_sources,
        "ready_warnings": ready_warnings,
        "problem_sources": problem_sources,
        "problem_evidence_sources": problem_evidence_sources,
        "recommended_source": recommended_source,
        "recommended_command": _build_recommended_command(recommended_source, viewport=viewport),
        "problem_actions": problem_actions,
    }


def _build_ready_warnings(result: ProbeResult) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if result.console_errors:
        warnings.append(
            {
                "source": result.source,
                "type": "console_error",
                "count": len(result.console_errors),
                "sample": result.console_errors[0],
                "action": (
                    "Source is usable, but inspect console errors before treating browser evidence as fully clean."
                ),
            }
        )
    if result.page_errors:
        warnings.append(
            {
                "source": result.source,
                "type": "page_error",
                "count": len(result.page_errors),
                "sample": result.page_errors[0],
                "action": (
                    "Source is usable, but inspect page errors before treating browser evidence as fully clean."
                ),
            }
        )
    return warnings


def _recommend_ready_source(ready_results: list[ProbeResult]) -> str | None:
    if not ready_results:
        return None
    indexed_results = enumerate(ready_results)
    _, selected = max(indexed_results, key=lambda item: (_ready_result_evidence_chars(item[1]), -item[0]))
    return selected.source


def _ready_result_evidence_chars(result: ProbeResult) -> int:
    click = result.click_through
    if click and click.ok:
        return click.body_chars
    return result.body_chars


def _build_recommended_command(source: str | None, *, viewport: str = "desktop") -> str | None:
    if source not in DEFAULT_SOURCES:
        return None
    command_parts = [
        sys.executable,
        str(_PROJECT_ROOT / "main.py"),
        "--config",
        str(_PROJECT_ROOT / "config.yaml"),
        "--source",
        source,
        "--popular",
        "--review-only",
        "--limit",
        "5",
        "--require-source-ready",
        "--source-preflight-click-through",
        "--source-preflight-output",
        str(_PROJECT_ROOT / ".tmp" / "source_browser_preflight.json"),
        "--source-preflight-screenshot-dir",
        str(_PROJECT_ROOT / "screenshots" / "source_preflight"),
        "--source-preflight-failure-dir",
        str(_PROJECT_ROOT / ".tmp" / "failures" / "source_preflight"),
    ]
    if viewport != "desktop":
        command_parts.extend(["--source-preflight-viewport", viewport])
    return _format_powershell_command(command_parts)


def _quote_powershell_arg(value: object) -> str:
    text = str(value)
    if not text:
        return "''"
    if any(char not in SAFE_POWERSHELL_ARG_CHARS for char in text):
        return "'" + text.replace("'", "''") + "'"
    return text


def _format_powershell_command(parts: list[object]) -> str:
    return "& " + " ".join(_quote_powershell_arg(part) for part in parts)


def _build_problem_action(result: ProbeResult, *, viewport: str = "desktop") -> dict[str, Any]:
    status = result.classification.status
    if status == "browser_unavailable":
        action = _build_browser_unavailable_action(result)
    elif status == "blocked":
        action = "Use a ready fallback source for this run, then recheck this source after access controls change."
    elif status == "click_error":
        action = (
            "Inspect the screenshot and click-through error, then update the source detail selector or API verifier."
        )
    elif status == "login_wall":
        action = "Use a ready fallback source unless an authenticated browser context is intentionally configured."
    elif status == "timeout":
        action = "Retry once with a higher --timeout-ms; if it repeats, use a ready fallback source."
    elif status == "empty":
        action = "Inspect the screenshot and source parser because the page returned too little readable text."
    else:
        action = "Inspect the captured evidence, then use a ready fallback source for this run."
    problem_action = {
        "source": result.source,
        "status": status,
        "action": action,
        "operator_action_required": True,
        "operator_action": action,
    }
    evidence = _build_problem_evidence(result)
    if evidence:
        problem_action["evidence"] = evidence
        problem_action.update(_build_evidence_review_guidance(result.source, evidence, viewport=viewport))
    return problem_action


def _build_evidence_review_guidance(
    source: str, evidence: dict[str, str], *, viewport: str = "desktop"
) -> dict[str, Any]:
    if not any(
        evidence.get(key)
        for key in (
            "failure_report_path",
            "screenshot_path",
            "html_snapshot_path",
            "trace_path",
            "click_screenshot_path",
        )
    ):
        return {}
    review_order = [
        key
        for key in (
            "failure_report_path",
            "screenshot_path",
            "html_snapshot_path",
            "trace_path",
            "click_screenshot_path",
            "exception_type",
            "error",
            "click_error",
        )
        if evidence.get(key)
    ]
    if not review_order:
        return {}
    return {
        "evidence_review_order": review_order,
        "evidence_review_hint": f"Open evidence in this order before changing source strategy: {', '.join(review_order)}.",
        **_build_trace_viewer_guidance(evidence),
        "repair_commands": _build_evidence_repair_commands(source, evidence, viewport=viewport),
    }


def _build_trace_viewer_guidance(evidence: dict[str, str]) -> dict[str, str]:
    trace_path = str(evidence.get("trace_path") or "").strip()
    if not trace_path:
        return {}
    return {
        "trace_viewer_command": _format_powershell_command(["playwright", "show-trace", trace_path]),
        "trace_viewer_hint": (
            "Open the Playwright trace locally and inspect Actions, Console, Network, and DOM snapshots before "
            "changing selectors or timeouts."
        ),
    }


def _build_evidence_repair_commands(source: str, evidence: dict[str, str], *, viewport: str = "desktop") -> list[str]:
    commands = [
        _format_powershell_command(
            [
                sys.executable,
                _PROJECT_ROOT / "scripts" / "source_preflight_evidence_doctor.py",
                "--input",
                _PROJECT_ROOT / ".tmp" / "source_browser_preflight.json",
                "--base-dir",
                _PROJECT_ROOT,
                "--fail-on-warning",
            ]
        )
    ]
    if source in DEFAULT_SOURCES:
        command_parts = [
            sys.executable,
            str(_PROJECT_ROOT / "main.py"),
            "--config",
            str(_PROJECT_ROOT / "config.yaml"),
            "--source",
            source,
            "--source-preflight",
            "--source-preflight-click-through",
            "--source-preflight-output",
            str(_PROJECT_ROOT / ".tmp" / "source_browser_preflight.json"),
            "--source-preflight-screenshot-dir",
            str(_PROJECT_ROOT / "screenshots" / "source_preflight"),
            "--source-preflight-failure-dir",
            str(_PROJECT_ROOT / ".tmp" / "failures" / "source_preflight"),
        ]
        if evidence.get("trace_path"):
            command_parts.extend(
                ["--source-preflight-trace-dir", str(_PROJECT_ROOT / ".tmp" / "traces" / "source_preflight")]
            )
        if viewport != "desktop":
            command_parts.extend(["--source-preflight-viewport", viewport])
        commands.append(_format_powershell_command(command_parts))
    return commands


def _build_problem_evidence(result: ProbeResult) -> dict[str, str]:
    evidence: dict[str, str] = {}
    if result.failure_report_path:
        evidence["failure_report_path"] = result.failure_report_path
    if result.screenshot_path:
        evidence["screenshot_path"] = result.screenshot_path
    if result.html_snapshot_path:
        evidence["html_snapshot_path"] = result.html_snapshot_path
    if result.trace_path:
        evidence["trace_path"] = result.trace_path
    if result.error:
        evidence["error"] = result.error
    if result.exception_type:
        evidence["exception_type"] = result.exception_type
    if result.click_through:
        if result.click_through.screenshot_path:
            evidence["click_screenshot_path"] = result.click_through.screenshot_path
        if result.click_through.error:
            evidence["click_error"] = result.click_through.error
    return evidence


def _build_browser_unavailable_action(result: ProbeResult) -> str:
    error_text = (result.error or " ".join(result.classification.signals)).lower()
    if "no module named 'playwright" in error_text or 'no module named "playwright' in error_text:
        return (
            "Run this helper with the Blind-to-X virtualenv. If Playwright is missing in the active "
            "interpreter, run `py -3 -m pip install playwright` first. Then install Chromium with "
            "`py -3 -m playwright install chromium` (or "
            "`.venv\\Scripts\\python.exe -m playwright install chromium` from the project venv), "
            "and rerun the preflight."
        )
    return (
        "Install Chromium in the same Python environment used for this preflight with "
        "`py -3 -m playwright install chromium` (or "
        "`.venv\\Scripts\\python.exe -m playwright install chromium` from the project venv), "
        "then rerun the preflight."
    )


def exit_code_for_report(report: dict[str, Any], *, fail_on_problem: bool) -> int:
    if fail_on_problem and not report.get("summary", {}).get("ok", False):
        return 1
    return 0


async def run_probe(
    targets: list[ProbeTarget],
    *,
    timeout_ms: int,
    screenshot_dir: Path | None,
    failure_dir: Path | None = DEFAULT_FAILURE_REPORT_DIR,
    trace_dir: Path | None = None,
    headed: bool = False,
    viewport: str = "desktop",
    click_through: bool = False,
) -> list[ProbeResult]:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        return [_with_failure_evidence(_browser_unavailable_result(target, exc), failure_dir) for target in targets]

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=not headed)
            try:
                context = await browser.new_context(**_context_options(viewport))
                trace_started = False
                trace_path = _trace_output_path(trace_dir, viewport=viewport)
                try:
                    trace_started = await _safe_start_trace(context, trace_path)
                    results = []
                    for target in targets:
                        results.append(
                            await _probe_target(
                                context,
                                target,
                                timeout_ms=timeout_ms,
                                screenshot_dir=screenshot_dir,
                                failure_dir=failure_dir,
                                timeout_error_cls=PlaywrightTimeoutError,
                                click_through=click_through,
                            )
                        )
                    saved_trace_path = await _safe_stop_trace(
                        context,
                        trace_path,
                        keep=_has_problem_result(results),
                    )
                    trace_started = False
                    if saved_trace_path:
                        results = _attach_trace_path_to_problem_results(results, saved_trace_path, failure_dir)
                    return results
                finally:
                    if trace_started:
                        await _safe_stop_trace(context, trace_path, keep=False)
                    await context.close()
            finally:
                await browser.close()
    except Exception as exc:
        return [_with_failure_evidence(_browser_unavailable_result(target, exc), failure_dir) for target in targets]


async def _probe_target(
    context: Any,
    target: ProbeTarget,
    *,
    timeout_ms: int,
    screenshot_dir: Path | None,
    failure_dir: Path | None,
    timeout_error_cls: type[Exception],
    click_through: bool = False,
) -> ProbeResult:
    page = await context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda msg: _collect_console_error(console_errors, msg))
    page.on("pageerror", lambda exc: page_errors.append(str(exc)[:500]))

    try:
        response = await page.goto(target.url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(500)
        title = await page.title()
        body_text = await _safe_body_text(page)
        screenshot_path = await _safe_screenshot(page, target, screenshot_dir)
        http_status = response.status if response else None
        classification = classify_probe(http_status=http_status, title=title, body_text=body_text)
        click_result = None
        if click_through and classification.status == READY_STATUS:
            click_result = await _click_first_post(page, target, timeout_ms=timeout_ms, screenshot_dir=screenshot_dir)
            if not click_result.ok:
                classification = ProbeClassification(
                    "click_error",
                    "first post click-through failed",
                    [click_result.error or "click_failed"],
                )
        html_snapshot_path = None
        if classification.status != READY_STATUS:
            html_snapshot_path = await _safe_html_snapshot(page, target, failure_dir)
        return _with_failure_evidence(
            ProbeResult(
                source=target.source,
                url=target.url,
                final_url=page.url,
                http_status=http_status,
                title=_compact_text(title)[:160],
                body_chars=len(_compact_text(body_text)),
                classification=classification,
                console_errors=console_errors[:10],
                page_errors=page_errors[:10],
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                click_through=click_result,
                html_snapshot_path=str(html_snapshot_path) if html_snapshot_path else None,
            ),
            failure_dir,
        )
    except timeout_error_cls as exc:
        screenshot_path = await _safe_screenshot(page, target, screenshot_dir)
        html_snapshot_path = await _safe_html_snapshot(page, target, failure_dir)
        return _with_failure_evidence(
            _error_result(
                target,
                page.url,
                console_errors,
                page_errors,
                str(exc),
                http_status=None,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                exception_type=type(exc).__name__,
                html_snapshot_path=str(html_snapshot_path) if html_snapshot_path else None,
            ),
            failure_dir,
        )
    except Exception as exc:
        screenshot_path = await _safe_screenshot(page, target, screenshot_dir)
        html_snapshot_path = await _safe_html_snapshot(page, target, failure_dir)
        return _with_failure_evidence(
            _error_result(
                target,
                page.url,
                console_errors,
                page_errors,
                str(exc),
                http_status=None,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                exception_type=type(exc).__name__,
                html_snapshot_path=str(html_snapshot_path) if html_snapshot_path else None,
            ),
            failure_dir,
        )
    finally:
        await page.close()


def _problem_action_text(result: ProbeResult) -> str | None:
    if result.classification.status == READY_STATUS:
        return None
    return str(_build_problem_action(result)["action"])


def _has_problem_result(results: list[ProbeResult]) -> bool:
    return any(result.classification.status != READY_STATUS for result in results)


def _trace_output_path(trace_dir: Path | None, *, viewport: str) -> Path | None:
    if not trace_dir:
        return None
    return Path(trace_dir) / f"source-preflight-{_safe_slug(viewport)}.zip"


async def _safe_start_trace(context: Any, trace_path: Path | None) -> bool:
    if not trace_path:
        return False
    try:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
    except Exception:
        return False
    return True


async def _safe_stop_trace(context: Any, trace_path: Path | None, *, keep: bool) -> str | None:
    if not trace_path:
        return None
    try:
        if keep:
            await context.tracing.stop(path=str(trace_path))
            return str(trace_path)
        await context.tracing.stop()
    except Exception:
        return None
    return None


def _attach_trace_path_to_problem_results(
    results: list[ProbeResult],
    trace_path: str,
    failure_dir: Path | None,
) -> list[ProbeResult]:
    enriched_results: list[ProbeResult] = []
    for result in results:
        if result.classification.status == READY_STATUS:
            enriched_results.append(result)
            continue
        enriched_results.append(_with_failure_evidence(replace(result, trace_path=trace_path), failure_dir))
    return enriched_results


def _with_failure_evidence(result: ProbeResult, failure_dir: Path | None) -> ProbeResult:
    action = _problem_action_text(result)
    if not action:
        return replace(result, operator_action_required=False, operator_action=None)
    if not failure_dir:
        return replace(result, operator_action_required=True, operator_action=action)

    failure_dir = Path(failure_dir)
    failure_dir.mkdir(parents=True, exist_ok=True)
    failure_report_path = (
        failure_dir / f"{_source_artifact_slug(result.source)}-{_safe_slug(result.classification.status)}.json"
    )
    enriched = replace(
        result,
        failure_report_path=str(failure_report_path),
        operator_action_required=True,
        operator_action=action,
    )
    failure_report_path.write_text(
        json.dumps(_failure_report_payload(enriched), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return enriched


def _failure_report_payload(result: ProbeResult) -> dict[str, Any]:
    evidence = _build_problem_evidence(result)
    data = _result_to_dict(result)
    data["failure_report"] = {
        "schema_version": 1,
        "tool": "source_browser_probe",
        "captured_at": datetime.now(UTC).isoformat(),
    }
    data["operator"] = {
        "action_required": bool(data.get("operator_action_required")),
        "action": data.get("operator_action"),
        "evidence": evidence,
        **_build_evidence_review_guidance(result.source, evidence),
    }
    return data


def _context_options(viewport: str) -> dict[str, Any]:
    base = {
        "locale": "ko-KR",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    if viewport == "mobile":
        base.update(
            {
                "viewport": {"width": 390, "height": 844},
                "is_mobile": True,
                "has_touch": True,
            }
        )
    else:
        base["viewport"] = {"width": 1365, "height": 768}
    return base


def _collect_console_error(console_errors: list[str], msg: Any) -> None:
    try:
        if getattr(msg, "type", "") == "error":
            console_errors.append(str(getattr(msg, "text", ""))[:500])
    except Exception:
        return


async def _safe_body_text(page: Any) -> str:
    try:
        return await page.locator("body").inner_text(timeout=1500)
    except Exception:
        try:
            return await page.content()
        except Exception:
            return ""


async def _click_first_post(
    page: Any,
    target: ProbeTarget,
    *,
    timeout_ms: int,
    screenshot_dir: Path | None,
) -> ClickThroughResult:
    if target.source == "jobplanet":
        body_text = await _safe_body_text(page)
        return await _verify_jobplanet_api_detail(
            page,
            target,
            feed_body_text=body_text,
            timeout_ms=timeout_ms,
            screenshot_dir=screenshot_dir,
        )

    candidate = None
    candidate_href: str | None = None
    try:
        anchors = await page.locator("a[href]").evaluate_all(
            """
            els => els.map((el, index) => ({
                index,
                text: (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' '),
                href: el.getAttribute('href') || '',
                visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
            })).filter(item => item.visible && item.href && item.text.length >= 4)
            """
        )
        candidate = _select_click_through_candidate(anchors)
        if candidate is None:
            raise RuntimeError("no post link candidates")

        candidate_href = _resolve_click_through_href(target.url, str(candidate.get("href", "")))
        locator = page.locator("a[href]").nth(int(candidate["index"]))
        click_error = None
        try:
            await locator.scroll_into_view_if_needed(timeout=min(5000, timeout_ms))
            await locator.click(timeout=min(8000, timeout_ms))
            await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            await _wait_for_click_detail(page, timeout_ms=timeout_ms)
        except Exception as exc:
            click_error = str(exc)[:500]
            await _retry_click_detail_url(page, candidate_href=candidate_href, timeout_ms=timeout_ms)
        title = await page.title()
        body_text = await _safe_body_text(page)
        if not _is_readable_click_detail(title, body_text):
            await _retry_click_detail_url(page, candidate_href=candidate_href, timeout_ms=timeout_ms)
            title = await page.title()
            body_text = await _safe_body_text(page)
        screenshot_path = await _safe_click_screenshot(page, target, screenshot_dir)
        body_chars = len(_compact_text(body_text))
        ok = _is_readable_click_detail(title, body_text) and page.url != target.url
        return ClickThroughResult(
            ok=ok,
            candidate_text=str(candidate.get("text", ""))[:160],
            candidate_href=candidate_href,
            final_url=page.url,
            title=_compact_text(title)[:160],
            body_chars=body_chars,
            screenshot_path=str(screenshot_path) if screenshot_path else None,
            error=(
                None
                if ok
                else f"clicked page did not look like a readable post detail; click_error={click_error}"
                if click_error
                else "clicked page did not look like a readable post detail"
            ),
        )
    except Exception as exc:
        return ClickThroughResult(
            ok=False,
            candidate_text=(str(candidate.get("text", ""))[:160] if candidate else None),
            candidate_href=(
                candidate_href if candidate_href else str(candidate.get("href", "")) if candidate else None
            ),
            final_url=getattr(page, "url", ""),
            title="",
            body_chars=0,
            error=str(exc)[:500],
        )


async def _verify_jobplanet_api_detail(
    page: Any,
    target: ProbeTarget,
    *,
    feed_body_text: str,
    timeout_ms: int,
    screenshot_dir: Path | None,
) -> ClickThroughResult:
    candidates = _select_jobplanet_api_candidates(feed_body_text)
    if not candidates:
        return ClickThroughResult(
            ok=False,
            candidate_text=None,
            candidate_href=None,
            final_url=getattr(page, "url", ""),
            title="",
            body_chars=0,
            error="no JobPlanet API post id candidates",
        )

    last_result: ClickThroughResult | None = None
    try:
        for candidate in candidates:
            response = await page.goto(str(candidate["api_href"]), wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(500)
            title = await page.title()
            body_text = await _safe_body_text(page)
            detail_title, detail_content = _extract_jobplanet_detail_payload(body_text)
            screenshot_path = await _safe_click_screenshot(page, target, screenshot_dir)
            body_chars = len(_compact_text(detail_content or body_text))
            http_status = response.status if response else None
            ok = (http_status is None or http_status < 400) and len(_compact_text(detail_content)) >= 10
            error = None
            if not ok:
                if http_status is not None and http_status >= 400:
                    error = f"JobPlanet detail API returned HTTP {http_status}"
                else:
                    error = "JobPlanet detail API did not return readable post content"

            last_result = ClickThroughResult(
                ok=ok,
                candidate_text=str(candidate["text"])[:160],
                candidate_href=str(candidate["href"]),
                final_url=getattr(page, "url", ""),
                title=_compact_text(detail_title or title)[:160],
                body_chars=body_chars,
                screenshot_path=str(screenshot_path) if screenshot_path else None,
                error=error,
            )
            if ok:
                return last_result

        if last_result is not None:
            return ClickThroughResult(
                ok=False,
                candidate_text=last_result.candidate_text,
                candidate_href=last_result.candidate_href,
                final_url=last_result.final_url,
                title=last_result.title,
                body_chars=last_result.body_chars,
                screenshot_path=last_result.screenshot_path,
                error="JobPlanet detail API did not return readable post content from feed candidates",
            )
        return ClickThroughResult(
            ok=False,
            candidate_text=None,
            candidate_href=None,
            final_url=getattr(page, "url", ""),
            title="",
            body_chars=0,
            error="no JobPlanet API post id candidates",
        )
    except Exception as exc:
        candidate = candidates[0]
        return ClickThroughResult(
            ok=False,
            candidate_text=str(candidate["text"])[:160],
            candidate_href=str(candidate["href"]),
            final_url=getattr(page, "url", ""),
            title="",
            body_chars=0,
            error=str(exc)[:500],
        )


async def _wait_for_click_detail(page: Any, *, timeout_ms: int) -> None:
    try:
        await page.wait_for_function(
            """
            () => {
                const body = document.body;
                const text = ((body && (body.innerText || body.textContent)) || '')
                    .replace(/\\s+/g, ' ')
                    .trim();
                const title = (document.title || '').trim().toLowerCase();
                return text.length >= 120 && !title.startsWith('loading ');
            }
            """,
            timeout=min(max(timeout_ms, 1000), 8000),
        )
    except Exception:
        await page.wait_for_timeout(500)


async def _retry_click_detail_url(page: Any, *, candidate_href: str, timeout_ms: int) -> None:
    if not candidate_href:
        return
    try:
        await page.goto(candidate_href, wait_until="domcontentloaded", timeout=timeout_ms)
        await _wait_for_click_detail(page, timeout_ms=timeout_ms)
    except Exception:
        return


def _is_readable_click_detail(title: str, body_text: str) -> bool:
    title_text = _compact_text(title).lower()
    return len(_compact_text(body_text)) >= 120 and not title_text.startswith("loading ")


def _resolve_click_through_href(base_url: str, href: str) -> str:
    absolute = urljoin(base_url, href)
    parts = urlsplit(absolute)
    if parts.netloc.endswith("ppomppu.co.kr") and parts.path.endswith("/zboard/zboard.php") and "no=" in parts.query:
        return urlunsplit((parts.scheme, parts.netloc, "/zboard/view.php", parts.query, ""))
    return absolute


def _select_click_through_candidate(anchors: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in anchors:
        href = str(item.get("href") or "")
        text = _compact_text(str(item.get("text") or ""))
        if not href or not text:
            continue
        href_lower = href.lower()
        text_lower = text.lower()
        if not ("no=" in href_lower or "view.php" in href_lower):
            continue
        if any(skip in href_lower for skip in ("regulation", "faq", "sponsor", "login", "auth", "https_redirect")):
            continue
        if text_lower.startswith("ad "):
            continue
        return item
    return None


def _select_jobplanet_api_candidate(body_text: str) -> dict[str, str] | None:
    candidates = _select_jobplanet_api_candidates(body_text)
    return candidates[0] if candidates else None


def _select_jobplanet_api_candidates(body_text: str, *, limit: int = 5) -> list[dict[str, str]]:
    payload = _json_payload_from_body(body_text)
    items = _nested_mapping_list(payload, "data", "items")
    candidates: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        post_id = _coerce_jobplanet_post_id(item.get("id"))
        if not post_id:
            continue
        title = _compact_text(str(item.get("title") or item.get("content") or ""))
        candidates.append(
            {
                "id": post_id,
                "text": title or f"JobPlanet post {post_id}",
                "href": f"{_JOBPLANET_BASE_URL}/community/posts/{post_id}",
                "api_href": f"{_JOBPLANET_BASE_URL}/api/v5/community/posts/{post_id}",
            }
        )
        if len(candidates) >= limit:
            break
    return candidates


def _extract_jobplanet_detail_payload(body_text: str) -> tuple[str, str]:
    payload = _json_payload_from_body(body_text)
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return "", ""
    content = _compact_text(str(data.get("content") or ""))
    title = _compact_text(str(data.get("title") or ""))
    if not title and content:
        title = content[:50]
    return title, content


def _json_payload_from_body(body_text: str) -> dict[str, Any]:
    text = (body_text or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return payload if isinstance(payload, dict) else {}


def _nested_mapping_list(payload: dict[str, Any], *keys: str) -> list[Any]:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return current if isinstance(current, list) else []


def _coerce_jobplanet_post_id(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if re.fullmatch(r"\d+", text) else None


async def _safe_click_screenshot(page: Any, target: ProbeTarget, screenshot_dir: Path | None) -> Path | None:
    if not screenshot_dir:
        return None
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / f"{_source_artifact_slug(target.source)}-click.png"
    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        return None
    return screenshot_path


async def _safe_screenshot(page: Any, target: ProbeTarget, screenshot_dir: Path | None) -> Path | None:
    if not screenshot_dir:
        return None
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / f"{_source_artifact_slug(target.source)}.png"
    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        return None
    return screenshot_path


async def _safe_html_snapshot(page: Any, target: ProbeTarget, failure_dir: Path | None) -> Path | None:
    if not failure_dir:
        return None
    failure_dir = Path(failure_dir)
    failure_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = failure_dir / f"{_source_artifact_slug(target.source)}.html"
    try:
        snapshot_path.write_text(await page.content(), encoding="utf-8")
    except Exception:
        return None
    return snapshot_path


def _browser_unavailable_result(target: ProbeTarget, exc: Exception) -> ProbeResult:
    error = str(exc)
    return ProbeResult(
        source=target.source,
        url=target.url,
        final_url="",
        http_status=None,
        title="",
        body_chars=0,
        classification=classify_probe(http_status=None, error=error),
        console_errors=[],
        page_errors=[],
        error=error[:500],
    )


def _error_result(
    target: ProbeTarget,
    final_url: str,
    console_errors: list[str],
    page_errors: list[str],
    error: str,
    *,
    http_status: int | None,
    screenshot_path: str | None = None,
    exception_type: str | None = None,
    html_snapshot_path: str | None = None,
) -> ProbeResult:
    return ProbeResult(
        source=target.source,
        url=target.url,
        final_url=final_url,
        http_status=http_status,
        title="",
        body_chars=0,
        classification=classify_probe(http_status=http_status, error=error),
        console_errors=console_errors[:10],
        page_errors=page_errors[:10],
        screenshot_path=screenshot_path,
        error=error[:500],
        exception_type=exception_type,
        html_snapshot_path=html_snapshot_path,
    )


def _source_name_from_url(url: str) -> str:
    hostname = re.sub(r"^https?://", "", url).split("/", 1)[0]
    return _safe_slug(hostname.split(":")[0])


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()
    return slug or "source"


def _source_artifact_slug(value: str) -> str:
    slug = _safe_slug(value)
    if slug != "source" or value.strip().lower() == "source":
        return slug
    digest = hashlib.sha1(value.encode("utf-8", errors="surrogatepass")).hexdigest()[:8]
    return f"{slug}-{digest}"


def _result_to_dict(result: ProbeResult) -> dict[str, Any]:
    action = _problem_action_text(result)
    if action:
        result = replace(
            result,
            operator_action_required=True,
            operator_action=result.operator_action or action,
        )
    else:
        result = replace(result, operator_action_required=False, operator_action=None)
    return asdict(result)


async def run_source_preflight(
    *,
    sources: list[str] | None,
    custom_urls: list[str] | None,
    timeout_ms: int,
    output_path: Path | None,
    screenshot_dir: Path | None,
    failure_dir: Path | None = DEFAULT_FAILURE_REPORT_DIR,
    trace_dir: Path | None = None,
    headed: bool = False,
    viewport: str = "desktop",
    click_through: bool = False,
) -> dict[str, Any]:
    targets = parse_targets(sources, custom_urls)
    results = await run_probe(
        targets,
        timeout_ms=timeout_ms,
        screenshot_dir=screenshot_dir,
        failure_dir=failure_dir,
        trace_dir=trace_dir,
        headed=headed,
        viewport=viewport,
        click_through=click_through,
    )
    report = build_report(results, viewport=viewport)
    _write_report(report, output_path)
    return report


def _write_report(report: dict[str, Any], output_path: Path | None) -> None:
    payload = json.dumps(report, ensure_ascii=True, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted([*DEFAULT_SOURCES, *ALL_SOURCE_ALIASES]),
        help=(
            "Known source to probe. Repeat to probe multiple sources. "
            "Use all/auto/multi, or omit the flag, to probe every known source."
        ),
    )
    parser.add_argument(
        "--url",
        action="append",
        help="Additional target in name=https://example form.",
    )
    parser.add_argument("--timeout-ms", type=int, default=12000, help="Navigation timeout in milliseconds.")
    parser.add_argument("--output", type=Path, default=None, help="Write the JSON report to this path.")
    parser.add_argument("--screenshot-dir", type=Path, default=None, help="Directory for full-page screenshots.")
    parser.add_argument(
        "--failure-dir",
        type=Path,
        default=DEFAULT_FAILURE_REPORT_DIR,
        help="Directory for problem-source JSON failure reports and HTML snapshots.",
    )
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=None,
        help="Optional directory for Playwright trace.zip evidence; retained only when a source has a problem.",
    )
    parser.add_argument("--headed", action="store_true", help="Run a visible browser.")
    parser.add_argument(
        "--click-through",
        action="store_true",
        help=(
            "Verify the first post detail; HTML sources click a visible post and fall back to the canonical "
            "detail URL when the click is obstructed, while API sources use a source-specific detail URL."
        ),
    )
    parser.add_argument(
        "--viewport",
        choices=("desktop", "mobile"),
        default="desktop",
        help="Browser viewport profile.",
    )
    parser.add_argument(
        "--fail-on-problem",
        action="store_true",
        help="Exit with status 1 when any source is not ready.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Accepted for CLI consistency; source preflight output is always JSON.",
    )
    return parser


async def async_main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = await run_source_preflight(
        sources=args.source,
        custom_urls=args.url,
        timeout_ms=max(1000, args.timeout_ms),
        output_path=args.output,
        screenshot_dir=args.screenshot_dir,
        failure_dir=args.failure_dir,
        trace_dir=args.trace_dir,
        headed=args.headed,
        viewport=args.viewport,
        click_through=args.click_through,
    )
    return exit_code_for_report(report, fail_on_problem=args.fail_on_problem)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
