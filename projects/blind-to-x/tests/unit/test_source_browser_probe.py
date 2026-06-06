import json

import pytest

from scripts.source_browser_probe import (
    READY_STATUS,
    ClickThroughResult,
    ProbeClassification,
    ProbeResult,
    ProbeTarget,
    build_report,
    classify_probe,
    exit_code_for_report,
    parse_targets,
    run_source_preflight,
    _click_first_post,
    _resolve_click_through_href,
    _write_report,
    _select_click_through_candidate,
    _select_jobplanet_api_candidate,
)


def test_classify_ready_page_with_readable_content():
    body = "x" * 140

    result = classify_probe(http_status=200, title="FMKorea best", body_text=body)

    assert result.status == READY_STATUS
    assert result.reason == "page returned readable content"


def test_classify_http_forbidden_as_blocked():
    result = classify_probe(http_status=403, title="Forbidden", body_text="Access denied")

    assert result.status == "blocked"
    assert "http_403" in result.signals


def test_classify_site_security_status_as_blocked():
    result = classify_probe(http_status=430, title="Security system", body_text="security page")

    assert result.status == "blocked"
    assert "http_430" in result.signals


def test_classify_bot_copy_as_blocked_even_when_http_ok():
    result = classify_probe(
        http_status=200,
        title="Checking your browser",
        body_text="Cloudflare CAPTCHA verification required.",
    )

    assert result.status == "blocked"
    assert "captcha" in result.signals


def test_classify_login_wall_copy():
    result = classify_probe(
        http_status=200,
        title="Members only",
        body_text="Please log in to continue reading this post.",
    )

    assert result.status == "login_wall"
    assert "please log in" in result.signals


def test_classify_empty_page():
    result = classify_probe(http_status=200, title="", body_text=" ")

    assert result.status == "empty"
    assert "body_chars=0" in result.signals


def test_classify_playwright_install_error_as_browser_unavailable():
    result = classify_probe(
        http_status=None,
        error="Executable doesn't exist. Please run playwright install.",
    )

    assert result.status == "browser_unavailable"
    assert "playwright install" in result.signals


def test_parse_targets_defaults_and_custom_url():
    targets = parse_targets(None, ["example=https://example.com/feed"])

    assert [target.source for target in targets] == ["blind", "fmkorea", "jobplanet", "ppomppu", "example"]
    assert targets[-1].url == "https://example.com/feed"


def test_build_report_counts_problem_statuses_and_exit_code():
    results = [
        ProbeResult(
            source="fmkorea",
            url="https://www.fmkorea.com/best",
            final_url="https://www.fmkorea.com/best",
            http_status=200,
            title="Best",
            body_chars=200,
            classification=ProbeClassification(READY_STATUS, "ok", []),
            console_errors=[],
            page_errors=[],
        ),
        ProbeResult(
            source="blind",
            url="https://www.teamblind.com/kr/topics/trending",
            final_url="https://www.teamblind.com/kr/topics/trending",
            http_status=403,
            title="Forbidden",
            body_chars=20,
            classification=ProbeClassification("blocked", "HTTP 403", ["http_403"]),
            console_errors=[],
            page_errors=[],
        ),
    ]

    report = build_report(results)

    assert report["summary"] == {
        "source_count": 2,
        "ready_count": 1,
        "problem_count": 1,
        "ok": False,
        "statuses": {"blocked": 1, "ready": 1},
        "ready_sources": ["fmkorea"],
        "problem_sources": [
            {
                "source": "blind",
                "status": "blocked",
                "reason": "HTTP 403",
                "signals": ["http_403"],
            }
        ],
        "recommended_source": "fmkorea",
        "recommended_command": (
            "py -3 main.py --source fmkorea --popular --review-only --limit 5 "
            "--require-source-ready --source-preflight-click-through "
            "--source-preflight-output .tmp/source_browser_preflight.json "
            "--source-preflight-screenshot-dir screenshots/source_preflight"
        ),
        "problem_actions": [
            {
                "source": "blind",
                "status": "blocked",
                "action": (
                    "Use a ready fallback source for this run, then recheck this source after access controls change."
                ),
            }
        ],
    }
    assert exit_code_for_report(report, fail_on_problem=False) == 0
    assert exit_code_for_report(report, fail_on_problem=True) == 1


def test_build_report_counts_click_error_as_problem():
    results = [
        ProbeResult(
            source="ppomppu",
            url="https://www.ppomppu.co.kr/hot.php",
            final_url="https://www.ppomppu.co.kr/hot.php",
            http_status=200,
            title="Hot",
            body_chars=200,
            classification=ProbeClassification("click_error", "first post click-through failed", ["click_failed"]),
            console_errors=[],
            page_errors=[],
        )
    ]

    report = build_report(results)

    assert report["summary"]["problem_count"] == 1
    assert report["summary"]["statuses"] == {"click_error": 1}
    assert report["summary"]["ready_sources"] == []
    assert report["summary"]["problem_sources"] == [
        {
            "source": "ppomppu",
            "status": "click_error",
            "reason": "first post click-through failed",
            "signals": ["click_failed"],
        }
    ]
    assert report["summary"]["recommended_source"] is None
    assert report["summary"]["recommended_command"] is None
    assert report["summary"]["problem_actions"] == [
        {
            "source": "ppomppu",
            "status": "click_error",
            "action": (
                "Inspect the screenshot and click-through error, then update the source detail selector or API verifier."
            ),
        }
    ]
    assert exit_code_for_report(report, fail_on_problem=True) == 1


def test_build_report_recommends_ready_source_with_strongest_detail_evidence():
    results = [
        ProbeResult(
            source="jobplanet",
            url="https://www.jobplanet.co.kr/api/v5/community/posts",
            final_url="https://www.jobplanet.co.kr/api/v5/community/posts/1001",
            http_status=200,
            title="JobPlanet",
            body_chars=16000,
            classification=ProbeClassification(READY_STATUS, "ok", []),
            console_errors=[],
            page_errors=[],
            click_through=ClickThroughResult(
                ok=True,
                candidate_text="JobPlanet post",
                candidate_href="https://www.jobplanet.co.kr/community/posts/1001",
                final_url="https://www.jobplanet.co.kr/api/v5/community/posts/1001",
                title="JobPlanet post",
                body_chars=77,
            ),
        ),
        ProbeResult(
            source="ppomppu",
            url="https://www.ppomppu.co.kr/hot.php",
            final_url="https://www.ppomppu.co.kr/zboard/view.php?id=freeboard&no=1",
            http_status=200,
            title="Ppomppu",
            body_chars=1700,
            classification=ProbeClassification(READY_STATUS, "ok", []),
            console_errors=[],
            page_errors=[],
            click_through=ClickThroughResult(
                ok=True,
                candidate_text="Ppomppu post",
                candidate_href="https://www.ppomppu.co.kr/zboard/view.php?id=freeboard&no=1",
                final_url="https://www.ppomppu.co.kr/zboard/view.php?id=freeboard&no=1",
                title="Ppomppu post",
                body_chars=3300,
            ),
        ),
    ]

    report = build_report(results)

    assert report["summary"]["ready_sources"] == ["jobplanet", "ppomppu"]
    assert report["summary"]["recommended_source"] == "ppomppu"
    assert report["summary"]["recommended_command"].startswith("py -3 main.py --source ppomppu")


def test_write_report_escapes_non_ascii_evidence(tmp_path, capsys):
    korean_title = "\uc0ac\uacfc \ud1a0\ub860"
    korean_path = "C:/Users/\ubc15\uc8fc\ud638/screenshots/ppomppu.png"
    report = {
        "generated_at": "2026-06-06T00:00:00+00:00",
        "summary": {"source_count": 1, "ready_count": 1, "problem_count": 0, "ok": True},
        "results": [
            {
                "source": "ppomppu",
                "title": korean_title,
                "screenshot_path": korean_path,
            }
        ],
    }
    output_path = tmp_path / "source-preflight.json"

    _write_report(report, output_path)

    payload = output_path.read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert korean_title not in payload
    assert korean_path not in payload
    assert "\\uc0ac\\uacfc" in payload
    assert "\\ubc15\\uc8fc\\ud638" in payload
    assert all(ord(char) < 128 for char in payload)
    assert all(ord(char) < 128 for char in stdout)
    assert json.loads(payload)["results"][0]["title"] == korean_title


def test_resolve_click_through_href_normalizes_ppomppu_listing_link():
    href = "/zboard/zboard.php?id=freeboard&no=9970609"

    resolved = _resolve_click_through_href("https://www.ppomppu.co.kr/hot.php", href)

    assert resolved == "https://www.ppomppu.co.kr/zboard/view.php?id=freeboard&no=9970609"


def test_select_click_through_candidate_skips_nav_ads_and_policy():
    anchors = [
        {"index": 0, "text": "Community list", "href": "/zboard/zboard.php?id=freeboard"},
        {"index": 1, "text": "AD promo", "href": "/zboard/view.php?id=sponsor&no=1"},
        {"index": 2, "text": "Policy notice", "href": "/zboard/view.php?id=regulation&no=4"},
        {"index": 3, "text": "Real post title", "href": "/zboard/view.php?id=ppomppu&no=709586"},
    ]

    assert _select_click_through_candidate(anchors) == anchors[3]


def test_select_jobplanet_api_candidate_builds_detail_urls():
    body = json.dumps(
        {
            "data": {
                "items": [
                    {"id": None, "title": "missing id"},
                    {"id": 1001, "title": "JobPlanet post title"},
                ]
            }
        }
    )

    candidate = _select_jobplanet_api_candidate(body)

    assert candidate == {
        "id": "1001",
        "text": "JobPlanet post title",
        "href": "https://www.jobplanet.co.kr/community/posts/1001",
        "api_href": "https://www.jobplanet.co.kr/api/v5/community/posts/1001",
    }


@pytest.mark.asyncio
async def test_click_first_post_retries_canonical_detail_when_clicked_page_stays_loading():
    page = _FakeClickPage()
    target = ProbeTarget(source="ppomppu", url="https://www.ppomppu.co.kr/hot.php")

    result = await _click_first_post(page, target, timeout_ms=12000, screenshot_dir=None)

    assert result.ok is True
    assert result.candidate_href == "https://www.ppomppu.co.kr/zboard/view.php?id=freeboard&no=9970609"
    assert result.body_chars == 140
    assert page.goto_urls == ["https://www.ppomppu.co.kr/zboard/view.php?id=freeboard&no=9970609"]


@pytest.mark.asyncio
async def test_click_first_post_verifies_jobplanet_api_detail():
    page = _FakeJobplanetApiPage()
    target = ProbeTarget(
        source="jobplanet",
        url="https://www.jobplanet.co.kr/api/v5/community/posts?limit=20&order_by=recent",
    )

    result = await _click_first_post(page, target, timeout_ms=12000, screenshot_dir=None)

    assert result.ok is True
    assert result.candidate_text == "JobPlanet post title"
    assert result.candidate_href == "https://www.jobplanet.co.kr/community/posts/1001"
    assert result.final_url == "https://www.jobplanet.co.kr/api/v5/community/posts/1001"
    assert result.title == "JobPlanet detail title"
    assert result.body_chars == len("Detailed JobPlanet content")
    assert page.goto_urls == ["https://www.jobplanet.co.kr/api/v5/community/posts/1001"]


@pytest.mark.asyncio
async def test_click_first_post_reports_jobplanet_missing_api_candidate():
    page = _FakeJobplanetApiPage(feed_payload={"data": {"items": [{"title": "missing id"}]}})
    target = ProbeTarget(
        source="jobplanet",
        url="https://www.jobplanet.co.kr/api/v5/community/posts?limit=20&order_by=recent",
    )

    result = await _click_first_post(page, target, timeout_ms=12000, screenshot_dir=None)

    assert result.ok is False
    assert result.error == "no JobPlanet API post id candidates"
    assert page.goto_urls == []


@pytest.mark.asyncio
async def test_run_source_preflight_reuses_probe_and_writes_report(monkeypatch, tmp_path):
    async def fake_run_probe(targets, **kwargs):
        assert [target.source for target in targets] == ["ppomppu"]
        assert kwargs == {
            "timeout_ms": 1500,
            "screenshot_dir": tmp_path / "screens",
            "headed": True,
            "viewport": "mobile",
            "click_through": True,
        }
        return [
            ProbeResult(
                source="ppomppu",
                url="https://www.ppomppu.co.kr/hot.php",
                final_url="https://www.ppomppu.co.kr/hot.php",
                http_status=200,
                title="Hot",
                body_chars=200,
                classification=ProbeClassification(READY_STATUS, "ok", []),
                console_errors=[],
                page_errors=[],
            )
        ]

    output_path = tmp_path / "report.json"
    monkeypatch.setattr("scripts.source_browser_probe.run_probe", fake_run_probe)

    report = await run_source_preflight(
        sources=["ppomppu"],
        custom_urls=None,
        timeout_ms=1500,
        output_path=output_path,
        screenshot_dir=tmp_path / "screens",
        headed=True,
        viewport="mobile",
        click_through=True,
    )

    assert report["summary"]["ok"] is True
    assert report["summary"]["ready_sources"] == ["ppomppu"]
    assert report["summary"]["recommended_source"] == "ppomppu"
    assert '"source_count": 1' in output_path.read_text(encoding="utf-8")


class _FakeClickPage:
    def __init__(self):
        self.url = "https://www.ppomppu.co.kr/hot.php"
        self.title_value = "Loading https://www.ppomppu.co.kr/zboard/view.php?id=freeboard&no=9970609"
        self.body_text = "Load"
        self.goto_urls: list[str] = []
        self.anchors = [
            {
                "index": 0,
                "text": "Real post title",
                "href": "/zboard/zboard.php?id=freeboard&no=9970609",
                "visible": True,
            }
        ]

    def locator(self, selector):
        if selector == "a[href]":
            return _FakeAnchorCollection(self)
        if selector == "body":
            return _FakeBodyLocator(self)
        raise AssertionError(f"unexpected selector: {selector}")

    async def wait_for_load_state(self, *_args, **_kwargs):
        return None

    async def wait_for_function(self, *_args, **_kwargs):
        raise TimeoutError("not ready yet")

    async def wait_for_timeout(self, *_args, **_kwargs):
        return None

    async def title(self):
        return self.title_value

    async def goto(self, url, **_kwargs):
        self.goto_urls.append(url)
        self.url = url
        self.title_value = "Real post title - ppomppu"
        self.body_text = "x" * 140
        return None


class _FakeAnchorCollection:
    def __init__(self, page):
        self.page = page

    async def evaluate_all(self, _script):
        return self.page.anchors

    def nth(self, _index):
        return _FakeAnchor(self.page)


class _FakeAnchor:
    def __init__(self, page):
        self.page = page

    async def scroll_into_view_if_needed(self, **_kwargs):
        return None

    async def click(self, **_kwargs):
        self.page.url = "https://www.ppomppu.co.kr/zboard/view.php?id=freeboard&no=9970609"
        self.page.title_value = "Loading https://www.ppomppu.co.kr/zboard/view.php?id=freeboard&no=9970609"
        self.page.body_text = "Load"
        return None


class _FakeBodyLocator:
    def __init__(self, page):
        self.page = page

    async def inner_text(self, **_kwargs):
        return self.page.body_text


class _FakeResponse:
    def __init__(self, status):
        self.status = status


class _FakeJobplanetApiPage:
    def __init__(self, feed_payload=None, detail_payload=None):
        self.url = "https://www.jobplanet.co.kr/api/v5/community/posts?limit=20&order_by=recent"
        self.title_value = ""
        self.goto_urls: list[str] = []
        self.feed_payload = feed_payload or {"data": {"items": [{"id": 1001, "title": "JobPlanet post title"}]}}
        self.detail_payload = detail_payload or {
            "data": {
                "title": "JobPlanet detail title",
                "content": "Detailed JobPlanet content",
            }
        }
        self.body_text = json.dumps(self.feed_payload)

    def locator(self, selector):
        if selector == "body":
            return _FakeBodyLocator(self)
        raise AssertionError(f"unexpected selector: {selector}")

    async def goto(self, url, **_kwargs):
        self.goto_urls.append(url)
        self.url = url
        self.body_text = json.dumps(self.detail_payload)
        return _FakeResponse(200)

    async def wait_for_timeout(self, *_args, **_kwargs):
        return None

    async def title(self):
        return self.title_value
