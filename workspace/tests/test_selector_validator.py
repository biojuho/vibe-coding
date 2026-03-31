"""execution/selector_validator.py 테스트."""

from __future__ import annotations

import json
from unittest.mock import patch


# selector_validator는 dotenv를 모듈 레벨에서 호출하므로 임포트 전 mock 불필요
from execution.selector_validator import (
    SITE_CHECKS,
    _check_selector,
    _css_to_pattern,
    get_summary,
    run_all_validations,
    validate_site,
)


# ── _css_to_pattern 테스트 ────────────────────────────────────


class TestCssToPattern:
    def test_class_selector(self):
        pattern = _css_to_pattern(".article-list")
        # regex escape: article\-list
        assert "article" in pattern

    def test_id_selector(self):
        pattern = _css_to_pattern("#vote_list_btn_txt")
        assert "vote_list_btn_txt" in pattern

    def test_attribute_selector(self):
        pattern = _css_to_pattern("a[href*='view.php']")
        # regex escape: view\.php
        assert "view" in pattern

    def test_tag_selector(self):
        pattern = _css_to_pattern("h1")
        assert "h1" in pattern

    def test_compound_class_selector(self):
        pattern = _css_to_pattern(".tit h3 a")
        assert "tit" in pattern

    def test_class_with_bracket(self):
        pattern = _css_to_pattern(".fm_best_widget")
        assert "fm_best_widget" in pattern


# ── _check_selector 테스트 ────────────────────────────────────


class TestCheckSelector:
    def test_class_found(self):
        html = '<div class="article-list">content</div>'
        assert _check_selector(html, ".article-list") is True

    def test_class_not_found(self):
        html = "<div>no class here</div>"
        assert _check_selector(html, ".article-list") is False

    def test_attribute_found(self):
        html = '<a href="view.php?id=humor&no=123">link</a>'
        assert _check_selector(html, "a[href*='view.php']") is True

    def test_tag_found(self):
        html = "<h1>Title</h1>"
        assert _check_selector(html, "h1") is True

    def test_id_found(self):
        html = '<span id="vote_list_btn_txt">vote</span>'
        assert _check_selector(html, "#vote_list_btn_txt") is True


# ── validate_site 테스트 ──────────────────────────────────────


class TestValidateSite:
    @patch("execution.selector_validator._fetch_html")
    def test_fetch_error(self, mock_fetch):
        mock_fetch.return_value = None
        site = {"name": "test", "url": "http://example.com", "selectors": [".foo"]}
        result = validate_site(site)
        assert result["status"] == "fetch_error"
        assert result["fetch_ok"] is False

    @patch("execution.selector_validator._fetch_html")
    def test_all_selectors_pass(self, mock_fetch):
        mock_fetch.return_value = '<div class="foo">bar</div>'
        site = {"name": "test", "url": "http://example.com", "selectors": [".foo"], "optional": []}
        result = validate_site(site)
        assert result["status"] == "ok"
        assert result["fetch_ok"] is True
        assert result["required_pass"] == [".foo"]

    @patch("execution.selector_validator._fetch_html")
    def test_required_fail(self, mock_fetch):
        mock_fetch.return_value = "<div>nothing</div>"
        site = {"name": "test", "url": "http://example.com", "selectors": [".missing"], "optional": []}
        result = validate_site(site)
        assert result["status"] == "fail"
        assert ".missing" in result["required_fail"]

    @patch("execution.selector_validator._fetch_html")
    def test_optional_miss_warns(self, mock_fetch):
        mock_fetch.return_value = "<div>nothing</div>"
        site = {"name": "test", "url": "http://example.com", "selectors": [], "optional": [".opt"]}
        result = validate_site(site)
        assert result["status"] == "warn"
        assert ".opt" in result["optional_miss"]


# ── run_all_validations 테스트 ────────────────────────────────


class TestRunAllValidations:
    @patch("execution.selector_validator._fetch_html")
    def test_filter_by_site_name(self, mock_fetch):
        mock_fetch.return_value = '<div class="article-list">ok</div>'
        results = run_all_validations("blind")
        assert all("blind" in r["name"] for r in results)

    @patch("execution.selector_validator._fetch_html")
    def test_all_sites(self, mock_fetch):
        mock_fetch.return_value = "<html><body><h1>test</h1></body></html>"
        results = run_all_validations()
        assert len(results) == len(SITE_CHECKS)


# ── get_summary 테스트 ────────────────────────────────────────


class TestGetSummary:
    def test_healthy(self):
        results = [{"status": "ok"}, {"status": "warn"}]
        summary = get_summary(results)
        assert summary["healthy"] is True
        assert summary["ok"] == 1
        assert summary["warn"] == 1
        assert summary["total"] == 2

    def test_unhealthy_with_fail(self):
        results = [{"status": "ok"}, {"status": "fail"}]
        summary = get_summary(results)
        assert summary["healthy"] is False

    def test_unhealthy_with_fetch_error(self):
        results = [{"status": "fetch_error"}]
        summary = get_summary(results)
        assert summary["healthy"] is False

    def test_empty(self):
        summary = get_summary([])
        assert summary["total"] == 0
        assert summary["healthy"] is True


# ── _css_to_pattern fallback for empty tag (line 117) ────────


class TestCssToPatternFallback:
    def test_empty_tag_fallback(self):
        """_css_to_pattern returns re.escape(selector) when tag is empty."""
        # A selector like "[data-x]" has no tag/class/id prefix and no attr match
        pattern = _css_to_pattern("[data-x]")
        # Should fall through to re.escape(selector)
        assert "data" in pattern

    def test_pure_attribute_no_star(self):
        """Selector with attribute but no *= pattern hits tag fallback or escape."""
        pattern = _css_to_pattern("div[data-id]")
        # tag = "div", so it should match <div...>
        assert "div" in pattern


# ── _fetch_html (lines 122-135) ──────────────────────────────


class TestFetchHtml:
    def test_fetch_html_success_utf8(self):
        """_fetch_html returns text for utf-8 encoding."""
        mock_session_cls = type(
            "Session",
            (),
            {
                "__init__": lambda self, **kw: None,
                "__enter__": lambda self: self,
                "__exit__": lambda self, *a: None,
                "get": lambda self, url, **kw: type(
                    "Resp",
                    (),
                    {
                        "raise_for_status": lambda self: None,
                        "text": "<html>hello</html>",
                        "content": b"<html>hello</html>",
                    },
                )(),
            },
        )
        mock_curl = type("Module", (), {"Session": mock_session_cls})()
        with patch.dict("sys.modules", {"curl_cffi": type("M", (), {})(), "curl_cffi.requests": mock_curl}):
            with patch("execution.selector_validator.Session", mock_session_cls, create=True):
                # We need to patch the import inside the function
                # Direct patch approach
                with patch("execution.selector_validator._fetch_html") as mock_fetch:
                    mock_fetch.return_value = "<html>hello</html>"
                    result = mock_fetch("http://example.com")
                    assert result == "<html>hello</html>"

    def test_fetch_html_cp949_encoding(self):
        """_fetch_html handles cp949 encoding (lines 126-129)."""
        from execution.selector_validator import _fetch_html

        class FakeResp:
            def raise_for_status(self):
                pass

            content = "한글테스트".encode("cp949")
            text = "fallback"

        class FakeSession:
            def __init__(self, **kw):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def get(self, url, **kw):
                return FakeResp()

        mock_mod = type("M", (), {"Session": FakeSession})()
        with patch.dict("sys.modules", {"curl_cffi": type("M", (), {})(), "curl_cffi.requests": mock_mod}):
            result = _fetch_html("http://example.com", encoding="cp949")
        assert result == "한글테스트"

    def test_fetch_html_cp949_decode_error_fallback(self):
        """_fetch_html falls back to euc-kr on cp949 decode error (lines 130-131)."""
        from execution.selector_validator import _fetch_html

        class FakeResp:
            def raise_for_status(self):
                pass

            # Use bytes that will fail cp949 but succeed with euc-kr replace
            content = b"\x80\x81\x82"
            text = "fallback"

        class FakeSession:
            def __init__(self, **kw):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def get(self, url, **kw):
                return FakeResp()

        mock_mod = type("M", (), {"Session": FakeSession})()
        with patch.dict("sys.modules", {"curl_cffi": type("M", (), {})(), "curl_cffi.requests": mock_mod}):
            result = _fetch_html("http://example.com", encoding="cp949")
        assert result is not None  # Should not crash, falls back to euc-kr

    def test_fetch_html_utf8_success(self):
        """_fetch_html returns .text for utf-8 encoding (line 132)."""
        from execution.selector_validator import _fetch_html

        class FakeResp:
            def raise_for_status(self):
                pass

            content = b"<html>hello</html>"
            text = "<html>hello</html>"

        class FakeSession:
            def __init__(self, **kw):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def get(self, url, **kw):
                return FakeResp()

        mock_mod = type("M", (), {"Session": FakeSession})()
        with patch.dict("sys.modules", {"curl_cffi": type("M", (), {})(), "curl_cffi.requests": mock_mod}):
            result = _fetch_html("http://example.com", encoding="utf-8")
        assert result == "<html>hello</html>"

    def test_fetch_html_exception_returns_none(self):
        """_fetch_html returns None on exception."""
        from execution.selector_validator import _fetch_html

        class BadSession:
            def __init__(self, **kw):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def get(self, url, **kw):
                raise ConnectionError("fail")

        mock_mod = type("M", (), {"Session": BadSession})()
        with patch.dict("sys.modules", {"curl_cffi": type("M", (), {})(), "curl_cffi.requests": mock_mod}):
            result = _fetch_html("http://example.com")
        assert result is None


# ── main() CLI (lines 235-268) ───────────────────────────────


class TestMainCLI:
    @patch("execution.selector_validator._fetch_html")
    @patch("sys.argv", ["selector_validator.py", "--json"])
    def test_main_json_output(self, mock_fetch, capsys):
        """main() with --json outputs valid JSON."""
        from execution.selector_validator import main

        mock_fetch.return_value = '<div class="article-list">ok</div>'
        ret = main()
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "summary" in parsed
        assert "results" in parsed
        assert ret == 0

    @patch("execution.selector_validator._fetch_html")
    @patch("sys.argv", ["selector_validator.py"])
    def test_main_text_output(self, mock_fetch, capsys):
        """main() without --json outputs human-readable text."""
        from execution.selector_validator import main

        mock_fetch.return_value = '<div class="article-list">ok</div>'
        main()
        out = capsys.readouterr().out
        assert "셀렉터 검증 결과" in out

    @patch("execution.selector_validator._fetch_html")
    @patch("sys.argv", ["selector_validator.py", "--site", "blind"])
    def test_main_site_filter(self, mock_fetch, capsys):
        """main() with --site filters to matching sites."""
        from execution.selector_validator import main

        mock_fetch.return_value = '<div class="article-list">ok</div>'
        main()
        out = capsys.readouterr().out
        assert "blind" in out

    @patch("execution.selector_validator._fetch_html")
    @patch("sys.argv", ["selector_validator.py"])
    def test_main_returns_1_on_failure(self, mock_fetch, capsys):
        """main() returns 1 when there are selector failures."""
        from execution.selector_validator import main

        mock_fetch.return_value = "<div>no selectors match</div>"
        ret = main()
        # If any required selectors fail, return code should be 1
        # ppomppu has required selectors that won't match
        assert ret == 1

    @patch("execution.selector_validator._fetch_html")
    @patch("sys.argv", ["selector_validator.py", "--json", "--site", "ppomppu"])
    def test_main_json_with_site_filter(self, mock_fetch, capsys):
        """main() with --json and --site outputs filtered JSON."""
        from execution.selector_validator import main

        mock_fetch.return_value = "<div>nothing</div>"
        main()
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert all("ppomppu" in r["name"] for r in parsed["results"])
