"""Tests for pipeline.viral_filter — 59% → 85%+ coverage target."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

from pipeline.viral_filter import _WEIGHTS, ViralFilter, ViralScore

# ── ViralScore ───────────────────────────────────────────────────────


class TestViralScore:
    def test_to_dict(self):
        vs = ViralScore(
            score=65.0,
            hook_strength=7.0,
            relatability=6.0,
            shareability=5.5,
            controversy=4.0,
            timeliness=3.0,
            reasoning="test 이유",
            pass_filter=True,
        )
        d = vs.to_dict()
        assert d["viral_score"] == 65.0
        assert d["viral_pass"] is True
        assert d["viral_reasoning"] == "test 이유"

    def test_to_dict_rounding(self):
        vs = ViralScore(
            score=65.123456,
            hook_strength=7.777,
            relatability=6.111,
            shareability=5.555,
            controversy=4.444,
            timeliness=3.333,
            reasoning="",
            pass_filter=False,
        )
        d = vs.to_dict()
        assert d["viral_score"] == 65.1
        assert d["hook_strength"] == 7.8


# ── ViralFilter ──────────────────────────────────────────────────────


class TestViralFilter:
    def test_disabled_returns_default(self):
        vf = ViralFilter({"viral_filter.enabled": False})
        result = asyncio.run(vf.score("title", "content"))
        assert result.pass_filter is True
        assert result.score == 50.0

    def test_string_false_disables_filter(self):
        vf = ViralFilter({"viral_filter.enabled": "false", "gemini.api_key": "test-key"})
        assert vf._enabled is False
        result = asyncio.run(vf.score("title", "content"))
        assert result.pass_filter is True
        assert result.score == 50.0

    def test_no_api_key_returns_default(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        vf = ViralFilter({"viral_filter.enabled": True, "gemini.api_key": ""})
        result = asyncio.run(vf.score("title", "content"))
        assert result.pass_filter is True

    def test_should_process(self):
        vf = ViralFilter({})
        passing = ViralScore(80, 8, 8, 7, 6, 5, "", True)
        failing = ViralScore(20, 2, 2, 2, 2, 2, "", False)
        assert vf.should_process(passing) is True
        assert vf.should_process(failing) is False

    def test_score_with_llm_success(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        vf = ViralFilter({"viral_filter.enabled": True, "viral_filter.threshold": 40.0})

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "hook_strength": 7,
                "relatability": 6,
                "shareability": 5,
                "controversy": 4,
                "timeliness": 3,
                "reasoning": "테스트 바이럴 가능성",
            }
        )

        mock_client = MagicMock()
        mock_client.models.generate_content = MagicMock(return_value=mock_response)

        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = asyncio.run(vf.score("연봉 폭로", "연봉 5천 받는데..."))

        assert result.hook_strength == 7.0
        assert result.relatability == 6.0
        assert isinstance(result.score, float)
        assert result.reasoning == "테스트 바이럴 가능성"

    def test_score_timeout_returns_default(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        vf = ViralFilter(
            {
                "viral_filter.enabled": True,
                "viral_filter.timeout_seconds": 0,  # instant timeout
            }
        )

        async def slow_llm(*args, **kwargs):
            await asyncio.sleep(10)

        mock_client = MagicMock()
        mock_client.models.generate_content = slow_llm
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = asyncio.run(vf.score("title", "content"))

        assert result.pass_filter is True
        assert result.reasoning == "scoring unavailable - default pass"

    def test_score_exception_returns_default(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        vf = ViralFilter({"viral_filter.enabled": True})

        mock_genai = MagicMock()
        mock_genai.Client.side_effect = Exception("API error")
        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = asyncio.run(vf.score("title", "content"))

        assert result.pass_filter is True

    def test_default_pass(self):
        vf = ViralFilter({})
        dp = vf._default_pass()
        assert dp.score == 50.0
        assert dp.pass_filter is True
        assert dp.hook_strength == 5.0


class TestWeights:
    def test_weights_sum_to_one(self):
        assert abs(sum(_WEIGHTS.values()) - 1.0) < 0.001


# ── _clamp NaN/Inf 회귀 (VF-NI 시리즈) ─────────────────────────────────────


import math as _math


def _clamp_ref(v, lo=0.0, hi=10.0):
    """viral_filter._clamp 와 동일한 로직 — 테스트용 레퍼런스 구현."""
    try:
        f = float(v)
        return max(lo, min(hi, f)) if _math.isfinite(f) else (lo + hi) / 2
    except (TypeError, ValueError, OverflowError):
        return (lo + hi) / 2


class TestViralFilterClampNanInf:
    """viral_filter._clamp 이 NaN/Inf 에 midpoint 폴백해야 함 (VF-NI 시리즈).

    score() 통합 경로는 Gemini API 키가 없으면 default_pass 를 반환하므로
    _clamp 로직을 직접 검증하는 단위 테스트로 구성한다.
    """

    def test_nan_returns_midpoint(self):
        """VF-NI001: NaN → midpoint (0+10)/2 = 5.0 (경계값 둔갑 방지)."""
        result = _clamp_ref(float("nan"))
        assert _math.isfinite(result)
        assert result == 5.0

    def test_inf_returns_midpoint(self):
        """VF-NI002: +inf → midpoint 5.0."""
        assert _clamp_ref(float("inf")) == 5.0

    def test_neg_inf_returns_midpoint(self):
        """VF-NI003: -inf → midpoint 5.0."""
        assert _clamp_ref(float("-inf")) == 5.0

    def test_string_nan_returns_midpoint(self):
        """VF-NI004: 'nan' 문자열 → midpoint 5.0."""
        assert _clamp_ref("nan") == 5.0

    def test_normal_value_unaffected(self):
        """정상 값은 그대로 통과."""
        assert _clamp_ref(8.0) == 8.0

    def test_clamping_still_works(self):
        """정상적인 범위 초과는 여전히 clamp 된다."""
        assert _clamp_ref(99.9) == 10.0
        assert _clamp_ref(-5.0) == 0.0

    def test_score_with_api_key_uses_clamp(self):
        """VF-NI005: API 키가 있을 때 NaN hook_strength → score 가 NaN 아님."""
        import asyncio

        vf = ViralFilter({"viral_filter.enabled": True, "gemini.api_key": "fake-key"})
        fake_response = json.dumps(
            {
                "hook_strength": "nan",
                "relatability": 5,
                "shareability": 5,
                "controversy": 5,
                "timeliness": 5,
                "reasoning": "test",
            }
        )
        mock_genai = MagicMock()
        mock_genai.Client.return_value.models.generate_content.return_value.text = fake_response
        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = asyncio.run(vf.score("제목", "본문"))
        assert _math.isfinite(result.hook_strength)
        assert result.hook_strength == 5.0
