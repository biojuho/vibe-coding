#!/usr/bin/env python3
"""Probe Blind-to-X source pages with Playwright before running the pipeline."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any


DEFAULT_SOURCES: dict[str, str] = {
    "blind": "https://www.teamblind.com/kr/topics/trending",
    "fmkorea": "https://www.fmkorea.com/best",
    "jobplanet": "https://www.jobplanet.co.kr/api/v5/community/posts?limit=20&order_by=recent",
    "ppomppu": "https://www.ppomppu.co.kr/hot.php",
}

READY_STATUS = "ready"
PROBLEM_STATUSES = {
    "blocked",
    "browser_error",
    "browser_unavailable",
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
    error: str | None = None


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


def build_report(results: list[ProbeResult]) -> dict[str, Any]:
    statuses = Counter(result.classification.status for result in results)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "source_count": len(results),
            "ready_count": statuses.get(READY_STATUS, 0),
            "problem_count": sum(statuses.get(status, 0) for status in PROBLEM_STATUSES),
            "ok": statuses.get(READY_STATUS, 0) == len(results),
            "statuses": dict(sorted(statuses.items())),
        },
        "results": [_result_to_dict(result) for result in results],
    }


def exit_code_for_report(report: dict[str, Any], *, fail_on_problem: bool) -> int:
    if fail_on_problem and not report.get("summary", {}).get("ok", False):
        return 1
    return 0


async def run_probe(
    targets: list[ProbeTarget],
    *,
    timeout_ms: int,
    screenshot_dir: Path | None,
    headed: bool = False,
    viewport: str = "desktop",
) -> list[ProbeResult]:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        return [_browser_unavailable_result(target, exc) for target in targets]

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=not headed)
            try:
                context = await browser.new_context(**_context_options(viewport))
                try:
                    results = []
                    for target in targets:
                        results.append(
                            await _probe_target(
                                context,
                                target,
                                timeout_ms=timeout_ms,
                                screenshot_dir=screenshot_dir,
                                timeout_error_cls=PlaywrightTimeoutError,
                            )
                        )
                    return results
                finally:
                    await context.close()
            finally:
                await browser.close()
    except Exception as exc:
        return [_browser_unavailable_result(target, exc) for target in targets]


async def _probe_target(
    context: Any,
    target: ProbeTarget,
    *,
    timeout_ms: int,
    screenshot_dir: Path | None,
    timeout_error_cls: type[Exception],
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
        return ProbeResult(
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
        )
    except timeout_error_cls as exc:
        return _error_result(target, page.url, console_errors, page_errors, str(exc), http_status=None)
    except Exception as exc:
        return _error_result(target, page.url, console_errors, page_errors, str(exc), http_status=None)
    finally:
        await page.close()


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


async def _safe_screenshot(page: Any, target: ProbeTarget, screenshot_dir: Path | None) -> Path | None:
    if not screenshot_dir:
        return None
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / f"{_safe_slug(target.source)}.png"
    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        return None
    return screenshot_path


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
        error=error[:500],
    )


def _source_name_from_url(url: str) -> str:
    hostname = re.sub(r"^https?://", "", url).split("/", 1)[0]
    return _safe_slug(hostname.split(":")[0])


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()
    return slug or "source"


def _result_to_dict(result: ProbeResult) -> dict[str, Any]:
    data = asdict(result)
    return data


def _write_report(report: dict[str, Any], output_path: Path | None) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(DEFAULT_SOURCES),
        help="Known source to probe. Repeat to probe multiple sources. Defaults to all.",
    )
    parser.add_argument(
        "--url",
        action="append",
        help="Additional target in name=https://example form.",
    )
    parser.add_argument("--timeout-ms", type=int, default=12000, help="Navigation timeout in milliseconds.")
    parser.add_argument("--output", type=Path, default=None, help="Write the JSON report to this path.")
    parser.add_argument("--screenshot-dir", type=Path, default=None, help="Directory for full-page screenshots.")
    parser.add_argument("--headed", action="store_true", help="Run a visible browser.")
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
    return parser


async def async_main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    targets = parse_targets(args.source, args.url)
    results = await run_probe(
        targets,
        timeout_ms=max(1000, args.timeout_ms),
        screenshot_dir=args.screenshot_dir,
        headed=args.headed,
        viewport=args.viewport,
    )
    report = build_report(results)
    _write_report(report, args.output)
    return exit_code_for_report(report, fail_on_problem=args.fail_on_problem)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
