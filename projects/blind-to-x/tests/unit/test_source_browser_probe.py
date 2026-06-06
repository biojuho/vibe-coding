import pytest

from scripts.source_browser_probe import (
    READY_STATUS,
    ProbeClassification,
    ProbeResult,
    build_report,
    classify_probe,
    exit_code_for_report,
    parse_targets,
    run_source_preflight,
    _select_click_through_candidate,
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
    assert exit_code_for_report(report, fail_on_problem=True) == 1


def test_select_click_through_candidate_skips_nav_ads_and_policy():
    anchors = [
        {"index": 0, "text": "Community list", "href": "/zboard/zboard.php?id=freeboard"},
        {"index": 1, "text": "AD promo", "href": "/zboard/view.php?id=sponsor&no=1"},
        {"index": 2, "text": "Policy notice", "href": "/zboard/view.php?id=regulation&no=4"},
        {"index": 3, "text": "Real post title", "href": "/zboard/view.php?id=ppomppu&no=709586"},
    ]

    assert _select_click_through_candidate(anchors) == anchors[3]


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
    assert '"source_count": 1' in output_path.read_text(encoding="utf-8")
