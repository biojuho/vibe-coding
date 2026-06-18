"""Unit tests for scripts/llm_model_doctor.py (no live network)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_doctor():
    path = ROOT / "scripts" / "llm_model_doctor.py"
    spec = importlib.util.spec_from_file_location("llm_model_doctor", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["llm_model_doctor"] = module
    spec.loader.exec_module(module)
    return module


doctor = _load_doctor()


class FakeConfig:
    def __init__(self, data: dict):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


def _http(responses):
    """responses: list of (url_fragment, status, body)."""

    def http_get(url, headers=None, params=None):
        for frag, status, body in responses:
            if frag in url:
                return status, body
        return 404, None

    return http_get


# ── pure classifiers ──────────────────────────────────────────────────


def test_classify_retrieve_status_mapping():
    assert doctor.classify_retrieve(200) == doctor.OK
    assert doctor.classify_retrieve(404) == doctor.DEAD
    assert doctor.classify_retrieve(401) == doctor.AUTH_ERROR
    assert doctor.classify_retrieve(403) == doctor.AUTH_ERROR
    assert doctor.classify_retrieve(500) == doctor.UNKNOWN


def test_classify_list_membership():
    # presence confirms ok; absence is unknown (NOT dead) — lists vary by provider
    assert doctor.classify_list("grok-4", ["grok-4", "grok-3"]) == doctor.OK
    assert doctor.classify_list("grok-9", ["grok-4", "grok-3"]) == doctor.UNKNOWN
    # empty/unparseable list must not be claimed dead
    assert doctor.classify_list("grok-4", []) == doctor.UNKNOWN


def test_extract_model_ids():
    assert doctor._extract_model_ids({"data": [{"id": "a"}, {"id": "b"}, {}]}) == ["a", "b"]
    assert doctor._extract_model_ids({"object": "list"}) == []
    assert doctor._extract_model_ids("nope") == []


# ── check_provider ────────────────────────────────────────────────────

ANTHROPIC_SPEC = next(s for s in doctor.PROVIDER_SPECS if s["provider"] == "anthropic")
XAI_SPEC = next(s for s in doctor.PROVIDER_SPECS if s["provider"] == "xai")


def test_check_provider_retrieve_dead_and_ok():
    dead = doctor.check_provider(
        ANTHROPIC_SPEC,
        "claude-sonnet-4-20250514",
        "key",
        http_get=_http([("api.anthropic.com/v1/models/claude-sonnet-4-20250514", 404, None)]),
    )
    assert dead == doctor.DEAD
    ok = doctor.check_provider(
        ANTHROPIC_SPEC,
        "claude-sonnet-4-6",
        "key",
        http_get=_http([("api.anthropic.com/v1/models/claude-sonnet-4-6", 200, {"id": "claude-sonnet-4-6"})]),
    )
    assert ok == doctor.OK


def test_check_provider_openai_compatible_list():
    body = {"data": [{"id": "grok-4-1-fast-reasoning"}, {"id": "grok-3"}]}
    ok = doctor.check_provider(
        XAI_SPEC,
        "grok-4-1-fast-reasoning",
        "key",
        http_get=_http([("api.x.ai/v1/models", 200, body)]),
    )
    assert ok == doctor.OK
    # a model absent from a list is unknown, never dead (avoid false positives)
    absent = doctor.check_provider(
        XAI_SPEC,
        "grok-retired",
        "key",
        http_get=_http([("api.x.ai/v1/models", 200, body)]),
    )
    assert absent == doctor.UNKNOWN


def test_check_provider_skips_without_key_or_model():
    assert doctor.check_provider(ANTHROPIC_SPEC, "m", "", http_get=_http([])) == doctor.SKIPPED_NO_KEY
    assert doctor.check_provider(ANTHROPIC_SPEC, "", "key", http_get=_http([])) == doctor.SKIPPED_NO_MODEL


def test_check_provider_network_error_is_unreachable():
    def boom(url, headers=None, params=None):
        raise ConnectionError("down")

    assert doctor.check_provider(ANTHROPIC_SPEC, "m", "key", http_get=boom) == doctor.UNREACHABLE


# ── build_report ──────────────────────────────────────────────────────


def test_build_report_flags_dead_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    config = FakeConfig({"anthropic.enabled": True, "anthropic.model": "claude-sonnet-4-20250514"})
    http = _http([("api.anthropic.com/v1/models/", 404, None)])
    report = doctor.build_report(config, http_get=http)
    assert report["ok"] is False
    assert report["status"] == "FAIL"
    assert {"provider": "anthropic", "model": "claude-sonnet-4-20250514"} in report["dead_models"]
    anthropic_check = next(c for c in report["checks"] if c["provider"] == "anthropic")
    assert anthropic_check["severity"] == "fail"


def test_build_report_skips_disabled_provider():
    config = FakeConfig({"anthropic.enabled": False, "anthropic.model": "claude-sonnet-4-20250514"})
    report = doctor.build_report(config, http_get=_http([]))
    anthropic_check = next(c for c in report["checks"] if c["provider"] == "anthropic")
    assert anthropic_check["status"] == doctor.SKIPPED_DISABLED
    assert report["ok"] is True  # disabled provider never fails the gate
