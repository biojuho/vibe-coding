"""Tests for pipeline.viral_filter — 59% → 85%+ coverage target."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch


from pipeline.viral_filter import ViralFilter, ViralScore, _WEIGHTS


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
        mock_response.text = json.dumps({
            "hook_strength": 7,
            "relatability": 6,
            "shareability": 5,
            "controversy": 4,
            "timeliness": 3,
            "reasoning": "테스트 바이럴 가능성",
        })

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
        vf = ViralFilter({
            "viral_filter.enabled": True,
            "viral_filter.timeout_seconds": 0,  # instant timeout
        })

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
