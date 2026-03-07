"""execution/selector_validator.py 테스트."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


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
