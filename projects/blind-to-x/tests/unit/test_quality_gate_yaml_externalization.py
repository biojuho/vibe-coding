"""T-1202: prove that draft_quality_gate.py honors rules/editorial.yaml
`quality_gate_patterns` instead of only the hardcoded defaults.

These tests reload the module against monkey-patched rule sections to
confirm the YAML wins when present and the hardcoded default kicks in
when the YAML key is missing.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_BTX_ROOT = Path(__file__).resolve().parents[2]
if str(_BTX_ROOT) not in sys.path:
    sys.path.insert(0, str(_BTX_ROOT))


def _reload_with_patterns(monkeypatch, patterns) -> object:
    """Force `rules_loader.get_rule_section` to return `patterns` for
    `quality_gate_patterns`, then reload draft_quality_gate so its
    module-level YAML-derived constants pick up the patched value.

    Critical: patch `pipeline.rules_loader.get_rule_section` (the
    function's *home*), not `draft_quality_gate.get_rule_section`.
    `importlib.reload(draft_quality_gate)` re-executes the
    `from pipeline.rules_loader import get_rule_section` line and
    rebinds the gate-module attribute, so patching it there is futile.
    Patching at the source makes the reload pick up the monkeypatched
    version when it re-imports.
    """
    from pipeline import rules_loader

    real_get_rule_section = rules_loader.get_rule_section

    def _routed(key, default=None, *, force_reload=False):
        if key == "quality_gate_patterns":
            return patterns
        return real_get_rule_section(key, default, force_reload=force_reload)

    monkeypatch.setattr(rules_loader, "get_rule_section", _routed)

    from pipeline import draft_quality_gate

    return importlib.reload(draft_quality_gate)


def test_yaml_generic_cta_regex_overrides_default(monkeypatch):
    """A new CTA phrase added to YAML should be detected without code change."""
    custom = {"generic_cta_regex": r"(완전\s*신규\s*문구입니다)"}
    gate = _reload_with_patterns(monkeypatch, custom)

    assert gate._has_generic_cta("이건 완전 신규 문구입니다!") is True
    # The historical "여러분 생각은?" phrase no longer matches because YAML
    # replaced (not extended) the default. Editorial team controls the full list.
    assert gate._has_generic_cta("여러분 생각은?") is False


def test_yaml_influencer_vocab_overrides_default(monkeypatch):
    """Adding a custom forbidden word in YAML should propagate."""
    custom = {"influencer_vocab": ["완전레전더리"]}
    gate = _reload_with_patterns(monkeypatch, custom)

    assert "완전레전더리" in gate._INFLUENCER_VOCAB
    # Original "끝판왕" no longer in the list because YAML replaced the tuple.
    assert "끝판왕" not in gate._INFLUENCER_VOCAB
    assert gate._find_influencer_vocab("이게 완전레전더리야") == ["완전레전더리"]


def test_yaml_closing_cta_regex_overrides_default(monkeypatch):
    """The `_ends_with_cta_or_question` path uses _CLOSING_CTA_PATTERNS."""
    custom = {"closing_cta_regex": r"(완전\s*CTA)"}
    gate = _reload_with_patterns(monkeypatch, custom)

    # Direct compiled-regex check
    assert gate._CLOSING_CTA_PATTERNS.search("이거는 완전 CTA") is not None
    # The default "댓글로" no longer matches
    assert gate._CLOSING_CTA_PATTERNS.search("댓글로 남겨주세요") is None


def test_missing_yaml_falls_back_to_hardcoded_defaults(monkeypatch):
    """If the YAML section is missing/empty, defaults are used (safety net)."""
    gate = _reload_with_patterns(monkeypatch, {})

    # Historical generic-CTA phrase still detected
    assert gate._has_generic_cta("여러분 생각은?") is True
    # Historical influencer word still rejected
    assert "끝판왕" in gate._INFLUENCER_VOCAB
    # Historical closing CTA still detected
    assert gate._CLOSING_CTA_PATTERNS.search("댓글로 남겨주세요") is not None


def test_malformed_yaml_section_does_not_crash(monkeypatch):
    """Malformed section (string instead of dict) must degrade to defaults."""

    gate = _reload_with_patterns(monkeypatch, "not a dict")

    # Defaults kick in even though YAML returned a non-dict.
    assert gate._has_generic_cta("여러분 생각은?") is True
    assert "끝판왕" in gate._INFLUENCER_VOCAB


@pytest.fixture(autouse=True)
def _restore_module():
    """Reload draft_quality_gate at teardown so other tests get the real YAML."""
    yield
    from pipeline.rules_loader import reset_rules_cache

    reset_rules_cache()
    from pipeline import draft_quality_gate

    importlib.reload(draft_quality_gate)
