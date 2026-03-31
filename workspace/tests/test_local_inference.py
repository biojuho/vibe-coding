"""
단위 테스트: local_inference.py (OllamaClient)

모든 HTTP 호출을 mock하여 실제 Ollama 서버 없이 테스트합니다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.local_inference import OllamaClient


# ── 헬퍼 ─────────────────────────────────────────────────────


def _make_client_with_mock_session():
    """mock session이 주입된 OllamaClient 반환."""
    client = OllamaClient(base_url="http://test:11434")
    mock_sess = MagicMock()
    client._session = mock_sess
    return client, mock_sess


# ── is_available ─────────────────────────────────────────────


class TestIsAvailable:
    def test_available_when_200(self):
        client, mock_sess = _make_client_with_mock_session()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_sess.get.return_value = mock_resp
        assert client.is_available() is True

    def test_unavailable_when_connection_error(self):
        client, mock_sess = _make_client_with_mock_session()
        mock_sess.get.side_effect = ConnectionError("refused")
        assert client.is_available() is False

    def test_unavailable_when_500(self):
        client, mock_sess = _make_client_with_mock_session()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_sess.get.return_value = mock_resp
        assert client.is_available() is False


# ── list_models ──────────────────────────────────────────────


class TestListModels:
    def test_returns_model_names(self):
        client, mock_sess = _make_client_with_mock_session()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "qwen3-coder:30b-a3b-q4_K_M", "size": "18GB"},
                {"name": "deepseek-r1:8b", "size": "5GB"},
            ]
        }
        mock_sess.get.return_value = mock_resp
        models = client.list_models()
        assert len(models) == 2
        assert "qwen3-coder:30b-a3b-q4_K_M" in models

    def test_returns_empty_on_error(self):
        client, mock_sess = _make_client_with_mock_session()
        mock_sess.get.side_effect = Exception("timeout")
        models = client.list_models()
        assert models == []


# ── find_best_model ──────────────────────────────────────────


class TestFindBestModel:
    def test_selects_priority_model(self):
        client, _ = _make_client_with_mock_session()
        with patch.object(
            client,
            "list_models",
            return_value=[
                "codellama:7b",
                "qwen3-coder:30b-a3b-q4_K_M",
            ],
        ):
            best = client.find_best_model()
            assert "qwen3-coder" in best

    def test_returns_default_when_no_models(self):
        client, _ = _make_client_with_mock_session()
        with patch.object(client, "list_models", return_value=[]):
            best = client.find_best_model()
            assert best == client.default_model


# ── generate ─────────────────────────────────────────────────


class TestGenerate:
    def test_successful_generation(self):
        client, mock_sess = _make_client_with_mock_session()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": "def fibonacci(n):\n    pass"},
            "prompt_eval_count": 50,
            "eval_count": 120,
        }
        mock_sess.post.return_value = mock_resp
        content, in_tok, out_tok = client.generate(
            system_prompt="You are a coder.",
            user_prompt="Write fibonacci",
        )
        assert "fibonacci" in content
        assert in_tok == 50
        assert out_tok == 120

    def test_connection_error_raises(self):
        import requests

        client, mock_sess = _make_client_with_mock_session()
        mock_sess.post.side_effect = requests.ConnectionError("refused")
        with pytest.raises(ConnectionError, match="Ollama"):
            client.generate(system_prompt="t", user_prompt="t")

    def test_timeout_raises_runtime_error(self):
        import requests

        client, mock_sess = _make_client_with_mock_session()
        mock_sess.post.side_effect = requests.Timeout("timed out")
        with pytest.raises(RuntimeError, match="타임아웃"):
            client.generate(system_prompt="t", user_prompt="t")

    def test_empty_response_raises(self):
        client, mock_sess = _make_client_with_mock_session()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": ""},
            "prompt_eval_count": 10,
            "eval_count": 0,
        }
        mock_sess.post.return_value = mock_resp
        with pytest.raises(RuntimeError, match="빈 응답"):
            client.generate(system_prompt="t", user_prompt="t")

    def test_json_mode_sets_format(self):
        client, mock_sess = _make_client_with_mock_session()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": '{"key": "value"}'},
            "prompt_eval_count": 20,
            "eval_count": 30,
        }
        mock_sess.post.return_value = mock_resp
        client.generate(system_prompt="t", user_prompt="t", json_mode=True)
        call_kwargs = mock_sess.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["format"] == "json"


# ── generate_json ────────────────────────────────────────────


class TestGenerateJson:
    def test_parses_json_response(self):
        client, _ = _make_client_with_mock_session()
        with patch.object(client, "generate", return_value=('{"result": 42}', 10, 20)):
            result = client.generate_json(system_prompt="t", user_prompt="t")
            assert result == {"result": 42}

    def test_handles_markdown_wrapped_json(self):
        client, _ = _make_client_with_mock_session()
        with patch.object(client, "generate", return_value=('```json\n{"key": "val"}\n```', 10, 20)):
            result = client.generate_json(system_prompt="t", user_prompt="t")
            assert result == {"key": "val"}


# ── close ────────────────────────────────────────────────────


class TestClose:
    def test_close_clears_session(self):
        client, _ = _make_client_with_mock_session()
        client.close()
        assert client._session is None
