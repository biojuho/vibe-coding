"""Tests for pipeline.quality_gate."""

import pytest
from unittest.mock import MagicMock, patch

from pipeline.quality_gate import QualityGate, _load_rules_once
import pipeline.quality_gate as qg

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
    res1 = gate.check("클리셰1 그리고 클리셰2를 포함한 충분히 긴 문장입니다. 길이를 좀더 늘려보겠습니다.", platform="twitter")
    assert res1.passed
    assert any("cliche_detected" in w for w in res1.warnings)

    # 3+ cliches -> failures
    res3 = gate.check("클리셰1, 클리셰2, 클리셰3 모두 들어있는 아주 긴 테스트 문장입니다. 실패해야 합니다.", platform="twitter")
    assert not res3.passed
    assert any("cliche_overuse" in f for f in res3.failures)

@patch("pipeline.quality_gate._load_cliches")
@patch("pipeline.quality_gate._load_forbidden")
def test_forbidden(mock_forbidden, mock_cliches):
    mock_forbidden.return_value = ["금지어1"]
    mock_cliches.return_value = []
    gate = QualityGate()

    res = gate.check("이 문장에는 금지어1이 포함되어 있어서 통과할 수 없습니다. 길이를 채워보겠습니다.", platform="twitter")
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
    res2 = gate.check("세 번 반복합니다. 세 번 반복합니다. 세 번 반복합니다. 텍스트 길이 조건 충족용.", platform="twitter")
    assert not res2.passed
    assert any("repetition" in f for f in res2.failures)

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

        res = gate.check("충분히 긴 텍스트입니다. 20자를 넘겨서 쓰겠습니다. 원문 충실도 테스트 중입니다.", "source info", platform="twitter")
        assert res.passed  # fidelity just adds warnings in current logic
        assert any("potential_fabrication" in w for w in res.warnings)
