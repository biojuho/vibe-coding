from pathlib import Path
from types import SimpleNamespace

import pytest

from shorts_maker_v2.providers import tts_factory
from shorts_maker_v2.providers.tts_factory import TTSFactory


def _config():
    return SimpleNamespace(
        providers=SimpleNamespace(
            tts_model="tts-model",
            tts_speed=1.15,
            tts_ref_audio="ref.wav",
            tts_ref_audio_text="reference text",
            tts_openvoice_checkpoint_dir="checkpoints_v2",
        ),
        project=SimpleNamespace(language="ko-KR"),
    )


def test_premium_provider_success_uses_provider_client(monkeypatch, tmp_path):
    calls = {}

    class FakeClient:
        def __init__(self, **kwargs):
            calls["client_kwargs"] = kwargs

        def generate_tts(self, **kwargs):
            calls["generate_kwargs"] = kwargs
            Path(kwargs["output_path"]).write_bytes(b"audio")
            return kwargs["output_path"]

    monkeypatch.setattr(
        tts_factory,
        "_provider_specs",
        lambda: {
            "premium": tts_factory._ProviderSpec(
                availability_error="premium missing",
                loader=lambda: (lambda: True, FakeClient),
                client_kwargs=lambda request: {"ref_audio_path": request.config.providers.tts_ref_audio},
            )
        },
    )

    output = tmp_path / "voice.wav"
    words = tmp_path / "voice_words.json"
    result = TTSFactory.generate_tts_with_fallback(
        _config(),
        "premium",
        "hello",
        output,
        words,
        voice="voice-a",
        role="narrator",
        channel_key="channel-a",
    )

    assert result == output
    assert calls["client_kwargs"] == {"ref_audio_path": "ref.wav"}
    assert calls["generate_kwargs"] == {
        "model": "tts-model",
        "voice": "voice-a",
        "speed": 1.15,
        "text": "hello",
        "output_path": output,
        "words_json_path": words,
        "role": "narrator",
        "channel_key": "channel-a",
        "language": "ko-KR",
    }


def test_premium_provider_failure_unlinks_stale_output_and_uses_edge(monkeypatch, tmp_path):
    class UnusedClient:
        pass

    edge_calls = []

    def fake_edge(request):
        edge_calls.append(request)
        return request.output_path

    monkeypatch.setattr(
        tts_factory,
        "_provider_specs",
        lambda: {
            "premium": tts_factory._ProviderSpec(
                availability_error="premium missing",
                loader=lambda: (lambda: False, UnusedClient),
                client_kwargs=lambda request: {},
            )
        },
    )
    monkeypatch.setattr(TTSFactory, "_generate_edge_tts_request", staticmethod(fake_edge))

    output = tmp_path / "stale.wav"
    output.write_bytes(b"stale")
    words = tmp_path / "stale_words.json"

    result = TTSFactory.generate_tts_with_fallback(
        _config(),
        "premium",
        "fallback",
        output,
        words,
        voice="voice-b",
        role="host",
        channel_key="channel-b",
    )

    assert result == output
    assert len(edge_calls) == 1
    assert edge_calls[0].words_json_path == words
    assert edge_calls[0].channel_key == "channel-b"
    assert not output.exists()


def test_openai_provider_requires_client_and_uses_openai_signature(tmp_path):
    class FakeOpenAIClient:
        def __init__(self):
            self.kwargs = None

        def generate_tts(self, **kwargs):
            self.kwargs = kwargs
            return kwargs["output_path"]

    output = tmp_path / "openai.wav"
    words = tmp_path / "openai_words.json"
    client = FakeOpenAIClient()

    result = TTSFactory.generate_tts_with_fallback(
        _config(),
        "openai",
        "openai text",
        output,
        words,
        voice="alloy",
        role="narrator",
        channel_key="channel-c",
        openai_client=client,
    )

    assert result == output
    assert client.kwargs == {
        "model": "tts-model",
        "voice": "alloy",
        "speed": 1.15,
        "text": "openai text",
        "output_path": output,
    }


def test_openai_provider_without_client_raises(tmp_path):
    with pytest.raises(ValueError, match="OpenAI client is required"):
        TTSFactory.generate_tts_with_fallback(
            _config(),
            "openai",
            "missing client",
            tmp_path / "openai.wav",
            tmp_path / "openai_words.json",
            voice="alloy",
            role="narrator",
            channel_key="channel-c",
        )
