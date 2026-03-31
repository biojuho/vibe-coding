"""Tests for shorts_maker_v2.providers.openai_client — OpenAI API wrapper.

The OpenAI SDK is fully mocked so no real API calls or costs are incurred.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.providers import openai_client

# ═══════════════════════════════════════════════════════════════════
# __init__
# ═══════════════════════════════════════════════════════════════════


class TestInit:
    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_empty_api_key_raises(self, MockOpenAI):
        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            openai_client.OpenAIClient(api_key="")

    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_creates_client(self, MockOpenAI):
        client = openai_client.OpenAIClient(api_key="sk-test", request_timeout_sec=60)
        MockOpenAI.assert_called_once_with(api_key="sk-test", timeout=60)
        assert client.request_timeout_sec == 60


# ═══════════════════════════════════════════════════════════════════
# generate_json
# ═══════════════════════════════════════════════════════════════════


class TestGenerateJson:
    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_success(self, MockOpenAI):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        expected = {"title": "Test", "acts": [1, 2, 3]}
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(expected)
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client_inst.chat.completions.create.return_value = mock_response

        client = openai_client.OpenAIClient(api_key="sk-test")
        result = client.generate_json(
            model="gpt-4o-mini",
            system_prompt="You are a helper",
            user_prompt="generate test",
        )
        assert result == expected

    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_empty_content_raises(self, MockOpenAI):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client_inst.chat.completions.create.return_value = mock_response

        client = openai_client.OpenAIClient(api_key="sk-test")
        with pytest.raises(ValueError, match="empty JSON content"):
            client.generate_json(
                model="gpt-4o-mini",
                system_prompt="s",
                user_prompt="u",
            )


# ═══════════════════════════════════════════════════════════════════
# generate_tts
# ═══════════════════════════════════════════════════════════════════


class TestGenerateTts:
    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_success(self, MockOpenAI, tmp_path: Path):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        client = openai_client.OpenAIClient(api_key="sk-test")
        out = tmp_path / "subdir" / "tts.mp3"

        result = client.generate_tts(
            model="tts-1", voice="alloy", speed=1.0, text="Hello", output_path=out
        )
        assert result == out
        mock_client_inst.audio.speech.create.assert_called_once()

    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_cached_skips_api(self, MockOpenAI, tmp_path: Path):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        out = tmp_path / "tts.mp3"
        out.write_bytes(b"existing-audio")

        client = openai_client.OpenAIClient(api_key="sk-test")
        result = client.generate_tts(
            model="tts-1", voice="alloy", speed=1.0, text="Hello", output_path=out
        )
        assert result == out
        mock_client_inst.audio.speech.create.assert_not_called()


# ═══════════════════════════════════════════════════════════════════
# transcribe_audio
# ═══════════════════════════════════════════════════════════════════


class TestTranscribeAudio:
    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_returns_word_timestamps(self, MockOpenAI, tmp_path: Path):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        word1 = MagicMock(word="hello", start=0.0, end=0.5)
        word2 = MagicMock(word="world", start=0.5, end=1.0)
        mock_resp = MagicMock()
        mock_resp.words = [word1, word2]
        mock_client_inst.audio.transcriptions.create.return_value = mock_resp

        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"fake-audio-data")

        client = openai_client.OpenAIClient(api_key="sk-test")
        result = client.transcribe_audio(audio)
        assert result == [
            {"word": "hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0},
        ]

    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_no_words_returns_empty(self, MockOpenAI, tmp_path: Path):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        mock_resp = MagicMock()
        mock_resp.words = None
        mock_client_inst.audio.transcriptions.create.return_value = mock_resp

        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"x")

        client = openai_client.OpenAIClient(api_key="sk-test")
        result = client.transcribe_audio(audio)
        assert result == []


# ═══════════════════════════════════════════════════════════════════
# generate_image
# ═══════════════════════════════════════════════════════════════════


class TestGenerateImage:
    @patch("shorts_maker_v2.providers.openai_client.requests.get")
    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_url_download(self, MockOpenAI, mock_get, tmp_path: Path):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        img_data = b"\x89PNG-fake-image"
        item = MagicMock()
        item.url = "https://example.com/image.png"
        item.b64_json = None
        mock_response = MagicMock()
        mock_response.data = [item]
        mock_client_inst.images.generate.return_value = mock_response

        dl_resp = MagicMock()
        dl_resp.content = img_data
        dl_resp.raise_for_status.return_value = None
        mock_get.return_value = dl_resp

        out = tmp_path / "img" / "out.png"
        client = openai_client.OpenAIClient(api_key="sk-test")
        result = client.generate_image(
            model="dall-e-3", prompt="cat", size="1024x1024", quality="standard", output_path=out
        )
        assert result == out
        assert out.read_bytes() == img_data

    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_b64_json_path(self, MockOpenAI, tmp_path: Path):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        raw_data = b"image-binary-content"
        item = MagicMock()
        item.url = None
        item.b64_json = base64.b64encode(raw_data).decode()
        mock_response = MagicMock()
        mock_response.data = [item]
        mock_client_inst.images.generate.return_value = mock_response

        out = tmp_path / "b64.png"
        client = openai_client.OpenAIClient(api_key="sk-test")
        result = client.generate_image(
            model="dall-e-3", prompt="dog", size="1024x1024", quality="hd", output_path=out
        )
        assert result == out
        assert out.read_bytes() == raw_data

    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_cached_skips_api(self, MockOpenAI, tmp_path: Path):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        out = tmp_path / "cached.png"
        out.write_bytes(b"already-exists")

        client = openai_client.OpenAIClient(api_key="sk-test")
        result = client.generate_image(
            model="dall-e-3", prompt="x", size="1024x1024", quality="standard", output_path=out
        )
        assert result == out
        mock_client_inst.images.generate.assert_not_called()

    @patch("shorts_maker_v2.providers.openai_client.OpenAI")
    def test_no_data_raises(self, MockOpenAI, tmp_path: Path):
        mock_client_inst = MagicMock()
        MockOpenAI.return_value = mock_client_inst

        item = MagicMock()
        item.url = None
        item.b64_json = None
        mock_response = MagicMock()
        mock_response.data = [item]
        mock_client_inst.images.generate.return_value = mock_response

        out = tmp_path / "fail.png"
        client = openai_client.OpenAIClient(api_key="sk-test")
        with pytest.raises(ValueError, match="did not contain url or b64_json"):
            client.generate_image(
                model="dall-e-3", prompt="x", size="1024x1024", quality="standard", output_path=out
            )
