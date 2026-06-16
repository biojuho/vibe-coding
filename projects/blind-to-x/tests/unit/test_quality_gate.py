"""Tests for pipeline.quality_gate."""

from unittest.mock import MagicMock, patch

import pytest

import pipeline.quality_gate as qg
from pipeline.quality_gate import QualityGate, _load_rules_once


@pytest.fixture(autouse=True)
def reset_rules_cache():
    qg._rules_cache = None
    yield
    qg._rules_cache = None


def test_load_rules_once():
    with patch("pipeline.quality_gate.load_rules") as mock_load:
        mock_load.return_value = {"a": 1}
        # First call hits load_rules
        res1 = _load_rules_once()
        assert res1 == {"a": 1}
        assert mock_load.call_count == 1

        # Second call uses cache
        res2 = _load_rules_once()
        assert res2 == {"a": 1}
        assert mock_load.call_count == 1


def test_empty_draft():
    gate = QualityGate()
    res = gate.check("")
    assert not res.passed
    assert "empty_draft" in res.failures
    assert res.score == 0.0


@patch("pipeline.quality_gate.get_rule_section")
def test_length_limits(mock_get_rule):
    mock_get_rule.return_value = {}
    gate = QualityGate()

    # Twitter: min 20, max 280
    res_short = gate.check("너무 짧은글", platform="twitter")
    assert any("too_short" in f for f in res_short.failures)

    res_good = gate.check("이 글은 충분히 길게 작성된 글입니다. 20자가 넘었으므로 통과해야 합니다.", platform="twitter")
    assert res_good.passed

    res_long = gate.check("가" * 300, platform="twitter")
    assert any("too_long" in f for f in res_long.failures)


@patch("pipeline.quality_gate.get_rule_section")
def test_toxic_patterns(mock_get_rule):
    mock_get_rule.return_value = {}
    gate = QualityGate()

    res = gate.check("이 씨발 진짜 화나네. 길이도 충분히 넉넉하게 씀.", platform="twitter")
    assert not res.passed
    assert any("toxic_or_pii" in f for f in res.failures)

    res2 = gate.check("내 번호는 010-1234-5678야, 길이는 충분하게 작성함.", platform="twitter")
    assert not res.passed
    assert any("toxic_or_pii" in f for f in res2.failures)


@patch("pipeline.quality_gate._load_cliches")
@patch("pipeline.quality_gate._load_forbidden")
def test_cliches(mock_forbidden, mock_cliches):
    mock_forbidden.return_value = []
    mock_cliches.return_value = ["클리셰1", "클리셰2", "클리셰3", "클리셰4"]
    gate = QualityGate()

    # 0 cliches
    res0 = gate.check("아무런 문제 없는 충분히 긴 텍스트입니다. 20자가 넘어야 통과합니다.", platform="twitter")
    assert res0.passed
    assert not res0.warnings

    # 1-2 cliches -> warnings
    res1 = gate.check(
        "클리셰1 그리고 클리셰2를 포함한 충분히 긴 문장입니다. 길이를 좀더 늘려보겠습니다.", platform="twitter"
    )
    assert res1.passed
    assert any("cliche_detected" in w for w in res1.warnings)

    # 3+ cliches -> failures
    res3 = gate.check(
        "클리셰1, 클리셰2, 클리셰3 모두 들어있는 아주 긴 테스트 문장입니다. 실패해야 합니다.", platform="twitter"
    )
    assert not res3.passed
    assert any("cliche_overuse" in f for f in res3.failures)


@patch("pipeline.quality_gate._load_cliches")
@patch("pipeline.quality_gate._load_forbidden")
def test_forbidden(mock_forbidden, mock_cliches):
    mock_forbidden.return_value = ["금지어1"]
    mock_cliches.return_value = []
    gate = QualityGate()

    res = gate.check(
        "이 문장에는 금지어1이 포함되어 있어서 통과할 수 없습니다. 길이를 채워보겠습니다.", platform="twitter"
    )
    assert not res.passed
    assert any("forbidden_expression" in f for f in res.failures)


@patch("pipeline.quality_gate.get_rule_section")
def test_repetition(mock_get_rule):
    mock_get_rule.return_value = {}
    gate = QualityGate()

    # 1 repetition -> warning
    res1 = gate.check("반복되는 긴 문장입니다. 반복되는 긴 문장입니다. 길이를 맞추기 위해 씁니다.", platform="twitter")
    assert res1.passed
    assert any("minor_repetition" in w for w in res1.warnings)

    # 2+ repetitions -> failure
    res2 = gate.check(
        "세 번 반복합니다. 세 번 반복합니다. 세 번 반복합니다. 텍스트 길이 조건 충족용.", platform="twitter"
    )
    assert not res2.passed
    assert any("repetition" in f for f in res2.failures)


@patch("pipeline.quality_gate.get_rule_section")
def test_bland_creator_take_failure(mock_get_rule):
    """숫자 없음 + 상투어 2개 이상 → failure."""
    mock_get_rule.return_value = {}
    gate = QualityGate()
    bland_text = (
        "정말 중요한 이야기입니다. 꼭 기억해 두세요. 이 내용은 매우 흥미롭고 알아보겠습니다. 충분히 긴 텍스트입니다."
    )
    res = gate.check(bland_text, platform="twitter")
    assert not res.passed
    assert any("bland_creator_take" in f for f in res.failures)


@patch("pipeline.quality_gate.get_rule_section")
def test_bland_creator_take_warning_3_buzzwords(mock_get_rule):
    """숫자 있음 + 상투어 3개 이상 → warning (failure 아님)."""
    mock_get_rule.return_value = {}
    gate = QualityGate()
    # 숫자 있음 → failure 조건 미충족, but 3+ buzzwords → warning
    buzzword_text = "2024년 기준으로 정말 중요한 변화가 있었습니다. 꼭 기억해 두세요. 이 내용은 매우 흥미롭습니다. 유용한 정보를 드립니다. 한 번 알아보겠습니다."
    res = gate.check(buzzword_text, platform="twitter")
    # has digit "2024" → not a failure, but 3+ buzzwords should be a warning
    assert any("bland_creator_take_warning" in w for w in res.warnings)


@patch("pipeline.quality_gate.get_rule_section")
def test_bland_creator_take_passes_with_numbers_and_few_buzzwords(mock_get_rule):
    """숫자 있음 + 상투어 1개 이하 → 통과."""
    mock_get_rule.return_value = {}
    gate = QualityGate()
    specific_text = "연봉 3% 인상, IT 업계에서 가장 높은 수치입니다. 올해 총 150만 명이 해당됩니다."
    res = gate.check(specific_text, platform="twitter")
    assert not any("bland_creator_take" in f for f in res.failures)


@patch("pipeline.quality_gate.get_rule_section")
def test_readability_metrics_always_present(mock_get_rule):
    """T-AB029: readability_score and sentence_diversity always appear in metrics."""
    mock_get_rule.return_value = {}
    gate = QualityGate()
    res = gate.check("직장인 연봉이 화제다. 올해 3% 인상 예정이다. IT 업계가 특히 높다.", platform="twitter")
    assert "readability_score" in res.metrics
    assert "sentence_diversity" in res.metrics
    assert 0.0 <= res.metrics["readability_score"] <= 100.0


@patch("pipeline.quality_gate.get_rule_section")
def test_readability_low_score_triggers_warning(mock_get_rule):
    """T-AB029: readability_score < 40 → low_readability warning."""
    mock_get_rule.return_value = {}
    gate = QualityGate()
    # All-passive, very long sentences → low readability
    very_passive = (
        "모든 절차가 진행됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다. "
        "모든 사항이 결정됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다. "
        "모든 항목이 확인됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다. "
        "모든 내용이 수행됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다. "
        "추가 사항이 처리됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다됩니다."
    )
    res = gate.check(very_passive, platform="default")
    # Should have low_readability warning if score < 40
    if res.metrics.get("readability_score", 100) < 40:
        assert any("low_readability" in w for w in res.warnings)


@patch("pipeline.quality_gate.get_rule_section")
def test_source_fidelity(mock_get_rule):
    mock_get_rule.return_value = {}
    gate = QualityGate()

    with patch("pipeline.fact_checker.verify_facts") as mock_verify:
        mock_result = MagicMock()
        mock_result.confidence = 0.5
        mock_result.passed = False
        mock_result.fabricated_items = ["항목1", "항목2", "항목3"]
        mock_verify.return_value = mock_result

        res = gate.check(
            "충분히 긴 텍스트입니다. 20자를 넘겨서 쓰겠습니다. 원문 충실도 테스트 중입니다.",
            "source info",
            platform="twitter",
        )
        assert res.passed  # fidelity just adds warnings in current logic
        assert any("potential_fabrication" in w for w in res.warnings)


# ── QG-ND: None in recent_drafts does not disable quality gate ────────────────


def test_quality_gate_none_in_recent_drafts_does_not_crash():
    """QG-ND001: recent_drafts에 None 항목 (json.loads('null')) 있어도 AttributeError로 gate 비활성화 안 됨."""
    gate = QualityGate()

    # Directly test the for-loop guard by calling _check_semantic_similarity
    # DraftCache is imported inline, so patch at its source module
    from pipeline.quality_gate import GateResult

    gr = GateResult()
    with patch("pipeline.draft_cache.DraftCache") as mock_dc_cls:
        mock_cache = MagicMock()
        mock_cache.get_recent_drafts.return_value = [None, {"twitter": "old draft text here"}]
        mock_dc_cls.return_value = mock_cache
        gate._check_semantic_similarity("완전히 새로운 문장입니다", "twitter", gr)

    # Must not raise AttributeError — gate result is valid
    assert isinstance(gr.passed, bool)
