from scripts.source_browser_probe import (
    READY_STATUS,
    ProbeClassification,
    ProbeResult,
    build_report,
    classify_probe,
    exit_code_for_report,
    parse_targets,
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
