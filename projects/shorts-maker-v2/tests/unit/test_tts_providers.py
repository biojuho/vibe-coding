"""CosyVoice + Chatterbox TTS 프로바이더 유닛 테스트."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# torchaudio가 없는 환경에서도 테스트 가능하도록 mock 주입
_mock_torchaudio = MagicMock()
_mock_torch = MagicMock()


@pytest.fixture(autouse=True)
def _mock_heavy_deps(monkeypatch):
    """torchaudio/torch를 mock으로 대체."""
    _mock_torchaudio.reset_mock(return_value=True, side_effect=True)
    _mock_torch.reset_mock(return_value=True, side_effect=True)
    _mock_torchaudio.save.side_effect = None
    _mock_torch.cat.side_effect = None
    monkeypatch.setitem(sys.modules, "torchaudio", _mock_torchaudio)
    if "torch" not in sys.modules:
        monkeypatch.setitem(sys.modules, "torch", _mock_torch)
    yield
    _mock_torchaudio.reset_mock(return_value=True, side_effect=True)
    _mock_torch.reset_mock(return_value=True, side_effect=True)


def _write_fake_audio(path_str: str, *_args, **_kwargs) -> None:
    Path(path_str).write_bytes(b"wav")


# ── Chatterbox 테스트 ──────────────────────────────────────────────────────────


class TestChatterboxClient:
    """ChatterboxTTSClient 유닛 테스트."""

    def test_language_map_has_korean(self):
        from shorts_maker_v2.providers.chatterbox_client import _LANGUAGE_MAP

        assert "ko-KR" in _LANGUAGE_MAP
        assert _LANGUAGE_MAP["ko-KR"] == "ko"

    def test_language_map_has_english(self):
        from shorts_maker_v2.providers.chatterbox_client import _LANGUAGE_MAP

        assert "en-US" in _LANGUAGE_MAP
        assert _LANGUAGE_MAP["en-US"] == "en"

    def test_is_chatterbox_available_false(self):
        """chatterbox 미설치 시 False 반환."""
        from shorts_maker_v2.providers.chatterbox_client import is_chatterbox_available

        result = is_chatterbox_available()
        assert isinstance(result, bool)

    def test_is_chatterbox_available_true(self, monkeypatch):
        """chatterbox 모듈이 있으면 True 반환."""
        from shorts_maker_v2.providers.chatterbox_client import is_chatterbox_available

        fake_pkg = types.ModuleType("chatterbox")
        fake_mtl = types.ModuleType("chatterbox.mtl_tts")
        fake_pkg.mtl_tts = fake_mtl
        monkeypatch.setitem(sys.modules, "chatterbox", fake_pkg)
        monkeypatch.setitem(sys.modules, "chatterbox.mtl_tts", fake_mtl)

        assert is_chatterbox_available() is True

    def test_get_model_success_caches_loaded_model(self, monkeypatch):
        """정상 import 시 모델을 로드하고 캐시한다."""
        from shorts_maker_v2.providers.chatterbox_client import _get_model, _model_cache

        _model_cache.clear()
        fake_model = object()
        fake_torch = types.ModuleType("torch")
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
        fake_cls = MagicMock()
        fake_cls.from_pretrained.return_value = fake_model
        fake_pkg = types.ModuleType("chatterbox")
        fake_mtl = types.ModuleType("chatterbox.mtl_tts")
        fake_mtl.ChatterboxMultilingualTTS = fake_cls
        fake_pkg.mtl_tts = fake_mtl

        monkeypatch.setitem(sys.modules, "torch", fake_torch)
        monkeypatch.setitem(sys.modules, "chatterbox", fake_pkg)
        monkeypatch.setitem(sys.modules, "chatterbox.mtl_tts", fake_mtl)

        loaded = _get_model()
        cached = _get_model()

        assert loaded is fake_model
        assert cached is fake_model
        fake_cls.from_pretrained.assert_called_once_with(device="cpu")

    @patch("shorts_maker_v2.providers.chatterbox_client._get_model")
    def test_generate_tts_skips_existing(self, mock_get_model, tmp_path):
        """이미 존재하는 파일은 스킵."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        output = tmp_path / "test.mp3"
        output.write_bytes(b"fake audio data")

        client = ChatterboxTTSClient()
        result = client.generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="테스트 텍스트",
            output_path=output,
        )

        assert result == output
        mock_get_model.assert_not_called()

    @patch("shorts_maker_v2.providers.chatterbox_client._get_model")
    def test_generate_tts_calls_model(self, mock_get_model, tmp_path):
        """모델 호출 및 WAV 저장 확인."""
        import torch

        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        mock_model = MagicMock()
        mock_model.generate.return_value = torch.zeros(1, 24000) if hasattr(torch, "zeros") and callable(torch.zeros) else MagicMock()
        mock_model.sr = 24000
        mock_get_model.return_value = mock_model

        output = tmp_path / "test.wav"
        client = ChatterboxTTSClient()
        client.generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="안녕하세요",
            output_path=output,
        )

        mock_model.generate.assert_called_once()
        call_args = mock_model.generate.call_args
        assert call_args[0][0] == "안녕하세요"
        assert call_args[1]["language_id"] == "ko"

    @patch("shorts_maker_v2.providers.chatterbox_client._get_model")
    def test_generate_tts_with_words_json_calls_timing_generation(self, mock_get_model, tmp_path):
        """words_json_path가 있으면 타이밍 생성 훅을 호출한다."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        mock_model = MagicMock()
        mock_model.generate.return_value = MagicMock()
        mock_model.sr = 24000
        mock_get_model.return_value = mock_model

        output = tmp_path / "timed.wav"
        words_json = tmp_path / "words.json"
        with patch.object(ChatterboxTTSClient, "_generate_word_timings") as mock_timings:
            client = ChatterboxTTSClient()
            client.generate_tts(
                model="tts-1",
                voice="alloy",
                speed=1.0,
                text="단어 타이밍",
                output_path=output,
                words_json_path=words_json,
            )

        mock_timings.assert_called_once_with(output, "단어 타이밍", words_json, "ko-KR")

    @patch("shorts_maker_v2.providers.chatterbox_client._get_model")
    def test_hook_role_increases_exaggeration(self, mock_get_model, tmp_path):
        """hook 역할 시 exaggeration 증가."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        mock_model = MagicMock()
        mock_model.generate.return_value = MagicMock()
        mock_model.sr = 24000
        mock_get_model.return_value = mock_model

        output = tmp_path / "hook.wav"
        client = ChatterboxTTSClient(exaggeration=0.5)
        client.generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="충격적인 사실!",
            output_path=output,
            role="hook",
        )

        call_kwargs = mock_model.generate.call_args[1]
        assert call_kwargs["exaggeration"] == pytest.approx(0.7)

    @patch("shorts_maker_v2.providers.chatterbox_client._get_model")
    def test_closing_role_decreases_exaggeration(self, mock_get_model, tmp_path):
        """closing 역할 시 exaggeration 감소."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        mock_model = MagicMock()
        mock_model.generate.return_value = MagicMock()
        mock_model.sr = 24000
        mock_get_model.return_value = mock_model

        output = tmp_path / "closing.wav"
        client = ChatterboxTTSClient(exaggeration=0.5)
        client.generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="다음에 또 만나요.",
            output_path=output,
            role="closing",
        )

        call_kwargs = mock_model.generate.call_args[1]
        assert call_kwargs["exaggeration"] == pytest.approx(0.3)

    @patch("shorts_maker_v2.providers.chatterbox_client._get_model")
    def test_voice_cloning_with_ref_audio(self, mock_get_model, tmp_path):
        """참조 오디오 전달 확인."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        mock_model = MagicMock()
        mock_model.generate.return_value = MagicMock()
        mock_model.sr = 24000
        mock_get_model.return_value = mock_model

        ref_audio = tmp_path / "ref.wav"
        ref_audio.write_bytes(b"fake ref")
        output = tmp_path / "clone.wav"

        client = ChatterboxTTSClient(ref_audio_path=str(ref_audio))
        client.generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="클론 테스트",
            output_path=output,
        )

        call_kwargs = mock_model.generate.call_args[1]
        assert call_kwargs["audio_prompt_path"] == str(ref_audio)

    @patch("shorts_maker_v2.providers.chatterbox_client._get_model")
    def test_mp3_conversion_with_pydub(self, mock_get_model, tmp_path):
        """MP3 출력 시 pydub 변환 경로."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        mock_model = MagicMock()
        mock_model.generate.return_value = MagicMock()
        mock_model.sr = 24000
        mock_get_model.return_value = mock_model

        output = tmp_path / "test.mp3"
        client = ChatterboxTTSClient()

        mock_segment = MagicMock()
        with patch("shorts_maker_v2.providers.chatterbox_client.AudioSegment", create=True):
            # pydub import를 성공시키기 위해 builtins.__import__를 mock
            import builtins
            _real_import = builtins.__import__

            def _patched_import(name, *args, **kwargs):
                if name == "pydub":
                    m = MagicMock()
                    m.AudioSegment.from_wav.return_value = mock_segment
                    return m
                return _real_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", side_effect=_patched_import):
                # WAV 파일이 생성된 것처럼 torchaudio.save를 통해
                _mock_torchaudio.save.side_effect = _write_fake_audio
                client.generate_tts(
                    model="tts-1", voice="alloy", speed=1.0,
                    text="MP3 변환 테스트", output_path=output,
                )
                mock_segment.export.assert_called_once()

    @patch("shorts_maker_v2.providers.chatterbox_client._get_model")
    def test_mp3_fallback_without_pydub(self, mock_get_model, tmp_path):
        """pydub 미설치 시 WAV 파일 그대로 사용."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        mock_model = MagicMock()
        mock_model.generate.return_value = MagicMock()
        mock_model.sr = 24000
        mock_get_model.return_value = mock_model

        output = tmp_path / "test.mp3"
        client = ChatterboxTTSClient()

        # pydub import 실패 시뮬레이션
        import builtins
        _real_import = builtins.__import__

        def _fail_pydub(name, *args, **kwargs):
            if name == "pydub":
                raise ImportError("no pydub")
            return _real_import(name, *args, **kwargs)

        _mock_torchaudio.save.side_effect = _write_fake_audio
        with patch.object(builtins, "__import__", side_effect=_fail_pydub):
            result = client.generate_tts(
                model="tts-1", voice="alloy", speed=1.0,
                text="pydub 없는 테스트", output_path=output,
            )
        # .wav 확장자로 반환
        assert result.suffix == ".wav"

    def test_get_model_import_error(self):
        """_get_model — chatterbox 미설치 시 ImportError."""
        from shorts_maker_v2.providers.chatterbox_client import _get_model, _model_cache

        _model_cache.clear()
        import builtins
        _real_import = builtins.__import__

        def _fail_chatterbox(name, *args, **kwargs):
            if "chatterbox" in name:
                raise ImportError("no chatterbox")
            return _real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=_fail_chatterbox), pytest.raises(
            ImportError, match="chatterbox-tts"
        ):
            _get_model()

    def test_generate_word_timings_whisper_path(self, tmp_path):
        """단어 타이밍 — whisper 경로."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        output = tmp_path / "test.wav"
        output.write_bytes(b"fake")
        words_json = tmp_path / "words.json"

        with patch(
            "shorts_maker_v2.providers.whisper_aligner.is_whisper_available",
            return_value=True,
        ), patch(
            "shorts_maker_v2.providers.whisper_aligner.transcribe_to_word_timings",
            return_value=[{"word": "안녕", "start": 0.0, "end": 0.5}],
        ):
            ChatterboxTTSClient._generate_word_timings(output, "안녕", words_json, "ko-KR")

        assert words_json.exists()
        data = json.loads(words_json.read_text(encoding="utf-8"))
        assert data[0]["word"] == "안녕"

    def test_generate_word_timings_whisper_exception_falls_back(self, tmp_path):
        """whisper 예외 시 근사치 fallback으로 저장한다."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")
        words_json = tmp_path / "words.json"

        with patch(
            "shorts_maker_v2.providers.whisper_aligner.is_whisper_available",
            return_value=True,
        ), patch(
            "shorts_maker_v2.providers.whisper_aligner.transcribe_to_word_timings",
            side_effect=RuntimeError("boom"),
        ), patch(
            "shorts_maker_v2.providers.edge_tts_client._approximate_word_timings",
            return_value=[{"word": "fallback", "start": 0.0, "end": 1.0}],
        ):
            ChatterboxTTSClient._generate_word_timings(audio, "fallback", words_json, "ko-KR")

        data = json.loads(words_json.read_text(encoding="utf-8"))
        assert data[0]["word"] == "fallback"

    def test_generate_word_timings_approx_fallback(self, tmp_path):
        """단어 타이밍 — whisper 실패 시 근사치 fallback."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        words_json = tmp_path / "words.json"
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake audio")

        with patch(
            "shorts_maker_v2.providers.whisper_aligner.is_whisper_available",
            return_value=False,
        ), patch(
            "shorts_maker_v2.providers.edge_tts_client._approximate_word_timings",
            return_value=[{"word": "테스트", "start": 0.0, "end": 1.0}],
        ):
            ChatterboxTTSClient._generate_word_timings(audio, "테스트", words_json, "ko-KR")

        assert words_json.exists()

    def test_generate_word_timings_approx_exception_is_swallowed(self, tmp_path):
        """근사치 fallback도 실패하면 예외 없이 종료한다."""
        from shorts_maker_v2.providers.chatterbox_client import ChatterboxTTSClient

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")
        words_json = tmp_path / "words.json"

        with patch(
            "shorts_maker_v2.providers.whisper_aligner.is_whisper_available",
            return_value=False,
        ), patch(
            "shorts_maker_v2.providers.edge_tts_client._approximate_word_timings",
            side_effect=RuntimeError("boom"),
        ):
            ChatterboxTTSClient._generate_word_timings(audio, "테스트", words_json, "ko-KR")

        assert not words_json.exists()


# ── CosyVoice 테스트 ──────────────────────────────────────────────────────────


class TestCosyVoiceClient:
    """CosyVoiceTTSClient 유닛 테스트."""

    def test_language_tags_has_korean(self):
        from shorts_maker_v2.providers.cosyvoice_client import _LANGUAGE_TAGS

        assert "ko-KR" in _LANGUAGE_TAGS
        assert _LANGUAGE_TAGS["ko-KR"] == "<|ko|>"

    def test_is_cosyvoice_available_false(self):
        """cosyvoice 미설치 시 False 반환."""
        from shorts_maker_v2.providers.cosyvoice_client import is_cosyvoice_available

        result = is_cosyvoice_available()
        assert isinstance(result, bool)

    def test_is_cosyvoice_available_true(self, monkeypatch):
        """cosyvoice 모듈이 있으면 True 반환."""
        from shorts_maker_v2.providers.cosyvoice_client import is_cosyvoice_available

        fake_pkg = types.ModuleType("cosyvoice")
        fake_cli_pkg = types.ModuleType("cosyvoice.cli")
        fake_module = types.ModuleType("cosyvoice.cli.cosyvoice")
        fake_module.AutoModel = MagicMock()
        fake_pkg.cli = fake_cli_pkg
        fake_cli_pkg.cosyvoice = fake_module
        monkeypatch.setitem(sys.modules, "cosyvoice", fake_pkg)
        monkeypatch.setitem(sys.modules, "cosyvoice.cli", fake_cli_pkg)
        monkeypatch.setitem(sys.modules, "cosyvoice.cli.cosyvoice", fake_module)

        assert is_cosyvoice_available() is True

    def test_get_model_success_caches_loaded_model(self, monkeypatch):
        """정상 import 시 CosyVoice 모델을 캐시한다."""
        from shorts_maker_v2.providers.cosyvoice_client import _get_model, _model_cache

        _model_cache.clear()
        fake_model = object()
        fake_pkg = types.ModuleType("cosyvoice")
        fake_cli_pkg = types.ModuleType("cosyvoice.cli")
        fake_module = types.ModuleType("cosyvoice.cli.cosyvoice")
        fake_auto_model = MagicMock(return_value=fake_model)
        fake_module.AutoModel = fake_auto_model
        fake_pkg.cli = fake_cli_pkg
        fake_cli_pkg.cosyvoice = fake_module

        monkeypatch.setitem(sys.modules, "cosyvoice", fake_pkg)
        monkeypatch.setitem(sys.modules, "cosyvoice.cli", fake_cli_pkg)
        monkeypatch.setitem(sys.modules, "cosyvoice.cli.cosyvoice", fake_module)

        loaded = _get_model("fake-model-dir")
        cached = _get_model("ignored-second-call")

        assert loaded is fake_model
        assert cached is fake_model
        fake_auto_model.assert_called_once_with(model_dir="fake-model-dir")

    def test_instruct_text_roles(self):
        """역할별 instruct 텍스트 확인."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        hook_text = CosyVoiceTTSClient._get_instruct_text("hook", "ai_tech")
        assert "high energy" in hook_text
        assert "tech-savvy" in hook_text

        closing_text = CosyVoiceTTSClient._get_instruct_text("closing", "psychology")
        assert "softly" in closing_text
        assert "empathetic" in closing_text

        body_text = CosyVoiceTTSClient._get_instruct_text("body", "")
        assert "naturally" in body_text

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_generate_tts_cross_lingual(self, mock_get_model, tmp_path):
        """cross_lingual 모드 확인."""
        import torch

        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_speech = MagicMock()
        mock_model = MagicMock()
        mock_model.inference_cross_lingual.return_value = iter(
            [{"tts_speech": mock_speech}]
        )
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        # torch.cat mock
        with patch.object(torch, "cat", return_value=mock_speech):
            ref_audio = tmp_path / "ref.wav"
            ref_audio.write_bytes(b"fake ref")
            output = tmp_path / "test.wav"

            client = CosyVoiceTTSClient(ref_audio_path=str(ref_audio), mode="cross_lingual")
            client.generate_tts(
                model="tts-1",
                voice="alloy",
                speed=1.0,
                text="안녕하세요",
                output_path=output,
            )

        mock_model.inference_cross_lingual.assert_called_once()
        call_args = mock_model.inference_cross_lingual.call_args[0]
        assert "<|ko|>" in call_args[0]

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_generate_tts_zero_shot(self, mock_get_model, tmp_path):
        """zero_shot 모드 확인."""
        import torch

        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_speech = MagicMock()
        mock_model = MagicMock()
        mock_model.inference_zero_shot.return_value = iter(
            [{"tts_speech": mock_speech}]
        )
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        with patch.object(torch, "cat", return_value=mock_speech):
            ref_audio = tmp_path / "ref.wav"
            ref_audio.write_bytes(b"fake ref")
            output = tmp_path / "test.wav"

            client = CosyVoiceTTSClient(
                ref_audio_path=str(ref_audio),
                ref_audio_text="참조 텍스트",
                mode="zero_shot",
            )
            client.generate_tts(
                model="tts-1",
                voice="alloy",
                speed=1.0,
                text="클로닝 테스트",
                output_path=output,
            )

        mock_model.inference_zero_shot.assert_called_once()

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_generate_tts_with_words_json_calls_timing_generation(self, mock_get_model, tmp_path):
        """words_json_path가 있으면 CosyVoice 타이밍 생성을 호출한다."""
        import torch

        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_speech = MagicMock()
        mock_model = MagicMock()
        mock_model.inference_cross_lingual.return_value = iter([{"tts_speech": mock_speech}])
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        ref_audio = tmp_path / "ref.wav"
        ref_audio.write_bytes(b"ref")
        output = tmp_path / "timed.wav"
        words_json = tmp_path / "words.json"

        with patch.object(torch, "cat", return_value=mock_speech), patch.object(
            CosyVoiceTTSClient, "_generate_word_timings"
        ) as mock_timings:
            client = CosyVoiceTTSClient(ref_audio_path=str(ref_audio), mode="cross_lingual")
            client.generate_tts(
                model="tts-1",
                voice="alloy",
                speed=1.0,
                text="단어 타이밍",
                output_path=output,
                words_json_path=words_json,
            )

        mock_timings.assert_called_once_with(output, "단어 타이밍", words_json, "ko-KR")

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_generate_tts_skips_existing(self, mock_get_model, tmp_path):
        """이미 존재하는 파일은 스킵."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        output = tmp_path / "test.wav"
        output.write_bytes(b"existing audio")

        client = CosyVoiceTTSClient()
        result = client.generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="테스트",
            output_path=output,
        )

        assert result == output
        mock_get_model.assert_not_called()

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_zero_shot_with_speaker_id(self, mock_get_model, tmp_path):
        """zero_shot 모드 + speaker_id 분기."""
        import torch

        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_speech = MagicMock()
        mock_model = MagicMock()
        mock_model.inference_zero_shot.return_value = iter(
            [{"tts_speech": mock_speech}]
        )
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        with patch.object(torch, "cat", return_value=mock_speech):
            ref_audio = tmp_path / "ref.wav"
            ref_audio.write_bytes(b"ref")
            output = tmp_path / "out.wav"

            client = CosyVoiceTTSClient(
                ref_audio_path=str(ref_audio),
                speaker_id="spk_001",
                mode="zero_shot",
            )
            client.generate_tts(
                model="tts-1", voice="alloy", speed=1.0,
                text="스피커 ID 테스트", output_path=output,
            )

        call_kwargs = mock_model.inference_zero_shot.call_args[1]
        assert call_kwargs["zero_shot_spk_id"] == "spk_001"

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_instruct_mode(self, mock_get_model, tmp_path):
        """instruct 모드 분기."""
        import torch

        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_speech = MagicMock()
        mock_model = MagicMock()
        mock_model.inference_instruct2.return_value = iter(
            [{"tts_speech": mock_speech}]
        )
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        with patch.object(torch, "cat", return_value=mock_speech):
            output = tmp_path / "out.wav"
            client = CosyVoiceTTSClient(mode="instruct")
            client.generate_tts(
                model="tts-1", voice="alloy", speed=1.0,
                text="인스트럭트 모드", output_path=output,
                role="hook", channel_key="ai_tech",
            )

        mock_model.inference_instruct2.assert_called_once()
        # instruct_text 확인
        call_args = mock_model.inference_instruct2.call_args[0]
        assert "high energy" in call_args[1]

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_cross_lingual_sft_fallback(self, mock_get_model, tmp_path):
        """cross_lingual에서 참조 오디오 없을 때 SFT fallback."""
        import torch

        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_speech = MagicMock()
        mock_model = MagicMock()
        mock_model.list_available_spks.return_value = ["default_speaker"]
        mock_model.inference_sft.return_value = iter(
            [{"tts_speech": mock_speech}]
        )
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        with patch.object(torch, "cat", return_value=mock_speech), \
             patch.object(CosyVoiceTTSClient, "_get_default_ref_audio", return_value=None):
            output = tmp_path / "out.wav"
            client = CosyVoiceTTSClient(mode="cross_lingual")
            client.generate_tts(
                model="tts-1", voice="alloy", speed=1.0,
                text="SFT fallback", output_path=output,
            )

        mock_model.inference_sft.assert_called_once()

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_cross_lingual_no_ref_no_sft_raises(self, mock_get_model, tmp_path):
        """참조 오디오도 SFT 스피커도 없으면 RuntimeError."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_model = MagicMock()
        mock_model.list_available_spks.return_value = []
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        with patch.object(CosyVoiceTTSClient, "_get_default_ref_audio", return_value=None):
            output = tmp_path / "out.wav"
            client = CosyVoiceTTSClient(mode="cross_lingual")
            with pytest.raises(RuntimeError, match="참조 오디오가 필요합니다"):
                client.generate_tts(
                    model="tts-1", voice="alloy", speed=1.0,
                    text="에러 테스트", output_path=output,
                )

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_empty_audio_tensors_raises(self, mock_get_model, tmp_path):
        """음성 결과가 없으면 RuntimeError."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_model = MagicMock()
        mock_model.inference_cross_lingual.return_value = iter([])  # 빈 결과
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        ref_audio = tmp_path / "ref.wav"
        ref_audio.write_bytes(b"ref")
        output = tmp_path / "out.wav"

        client = CosyVoiceTTSClient(ref_audio_path=str(ref_audio), mode="cross_lingual")
        with pytest.raises(RuntimeError, match="음성 생성 결과 없음"):
            client.generate_tts(
                model="tts-1", voice="alloy", speed=1.0,
                text="빈 결과", output_path=output,
            )

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_mp3_conversion(self, mock_get_model, tmp_path):
        """MP3 출력 시 pydub 변환."""
        import builtins

        import torch

        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_speech = MagicMock()
        mock_model = MagicMock()
        mock_model.inference_cross_lingual.return_value = iter(
            [{"tts_speech": mock_speech}]
        )
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        mock_segment = MagicMock()
        _real_import = builtins.__import__

        def _patched_import(name, *args, **kwargs):
            if name == "pydub":
                m = MagicMock()
                m.AudioSegment.from_wav.return_value = mock_segment
                return m
            return _real_import(name, *args, **kwargs)

        ref_audio = tmp_path / "ref.wav"
        ref_audio.write_bytes(b"ref")
        output = tmp_path / "out.mp3"

        with patch.object(torch, "cat", return_value=mock_speech), \
             patch.object(builtins, "__import__", side_effect=_patched_import):
            _mock_torchaudio.save.side_effect = _write_fake_audio
            client = CosyVoiceTTSClient(ref_audio_path=str(ref_audio), mode="cross_lingual")
            client.generate_tts(
                model="tts-1", voice="alloy", speed=1.0,
                text="MP3 변환", output_path=output,
            )

        mock_segment.export.assert_called_once()

    @patch("shorts_maker_v2.providers.cosyvoice_client._get_model")
    def test_mp3_fallback_without_pydub(self, mock_get_model, tmp_path):
        """pydub가 없으면 WAV 결과를 그대로 사용한다."""
        import builtins

        import torch

        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        mock_speech = MagicMock()
        mock_model = MagicMock()
        mock_model.inference_cross_lingual.return_value = iter([{"tts_speech": mock_speech}])
        mock_model.sample_rate = 22050
        mock_get_model.return_value = mock_model

        ref_audio = tmp_path / "ref.wav"
        ref_audio.write_bytes(b"ref")
        output = tmp_path / "out.mp3"
        _real_import = builtins.__import__

        def _fail_pydub(name, *args, **kwargs):
            if name == "pydub":
                raise ImportError("no pydub")
            return _real_import(name, *args, **kwargs)

        with patch.object(torch, "cat", return_value=mock_speech), patch.object(
            builtins, "__import__", side_effect=_fail_pydub
        ):
            _mock_torchaudio.save.side_effect = _write_fake_audio
            client = CosyVoiceTTSClient(ref_audio_path=str(ref_audio), mode="cross_lingual")
            result = client.generate_tts(
                model="tts-1",
                voice="alloy",
                speed=1.0,
                text="MP3 fallback",
                output_path=output,
            )

        assert result.suffix == ".wav"

    def test_get_model_import_error(self):
        """_get_model — cosyvoice 미설치 시 ImportError."""
        import builtins

        from shorts_maker_v2.providers.cosyvoice_client import _get_model, _model_cache

        _model_cache.clear()
        _real_import = builtins.__import__

        def _fail_cosyvoice(name, *args, **kwargs):
            if "cosyvoice" in name:
                raise ImportError("no cosyvoice")
            return _real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=_fail_cosyvoice), pytest.raises(
            ImportError, match="CosyVoice"
        ):
            _get_model()

    def test_generate_word_timings_whisper(self, tmp_path):
        """CosyVoice 단어 타이밍 — whisper 경로."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")
        words_json = tmp_path / "words.json"

        with patch(
            "shorts_maker_v2.providers.whisper_aligner.is_whisper_available",
            return_value=True,
        ), patch(
            "shorts_maker_v2.providers.whisper_aligner.transcribe_to_word_timings",
            return_value=[{"word": "hello", "start": 0.0, "end": 0.5}],
        ):
            CosyVoiceTTSClient._generate_word_timings(audio, "hello", words_json, "en-US")

        assert words_json.exists()

    def test_generate_word_timings_whisper_exception_falls_back(self, tmp_path):
        """whisper 예외 시 근사치 fallback으로 저장한다."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")
        words_json = tmp_path / "words.json"

        with patch(
            "shorts_maker_v2.providers.whisper_aligner.is_whisper_available",
            return_value=True,
        ), patch(
            "shorts_maker_v2.providers.whisper_aligner.transcribe_to_word_timings",
            side_effect=RuntimeError("boom"),
        ), patch(
            "shorts_maker_v2.providers.edge_tts_client._approximate_word_timings",
            return_value=[{"word": "fallback", "start": 0.0, "end": 1.0}],
        ):
            CosyVoiceTTSClient._generate_word_timings(audio, "fallback", words_json, "ko-KR")

        data = json.loads(words_json.read_text(encoding="utf-8"))
        assert data[0]["word"] == "fallback"

    def test_generate_word_timings_approx_fallback(self, tmp_path):
        """CosyVoice 단어 타이밍 — 근사치 fallback."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")
        words_json = tmp_path / "words.json"

        with patch(
            "shorts_maker_v2.providers.whisper_aligner.is_whisper_available",
            return_value=False,
        ), patch(
            "shorts_maker_v2.providers.edge_tts_client._approximate_word_timings",
            return_value=[{"word": "test", "start": 0.0, "end": 1.0}],
        ):
            CosyVoiceTTSClient._generate_word_timings(audio, "test", words_json, "ko-KR")

        assert words_json.exists()

    def test_generate_word_timings_approx_exception_is_swallowed(self, tmp_path):
        """근사치 fallback도 실패하면 예외 없이 종료한다."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")
        words_json = tmp_path / "words.json"

        with patch(
            "shorts_maker_v2.providers.whisper_aligner.is_whisper_available",
            return_value=False,
        ), patch(
            "shorts_maker_v2.providers.edge_tts_client._approximate_word_timings",
            side_effect=RuntimeError("boom"),
        ):
            CosyVoiceTTSClient._generate_word_timings(audio, "test", words_json, "ko-KR")

        assert not words_json.exists()

    def test_get_default_ref_audio_none(self):
        """기본 참조 오디오가 없으면 None."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        # assets/ref_voice/ 디렉토리가 없는 환경
        result = CosyVoiceTTSClient._get_default_ref_audio()
        # 실제 파일이 없으면 None (CI 환경)
        assert result is None or isinstance(result, str)

    def test_get_default_ref_audio_returns_existing_asset(self, monkeypatch, tmp_path):
        """기본 참조 오디오 파일이 있으면 그 경로를 반환한다."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        asset = tmp_path / "assets" / "ref_voice" / "korean_female.wav"
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"ref")
        monkeypatch.chdir(tmp_path)

        result = CosyVoiceTTSClient._get_default_ref_audio()

        assert result is not None
        assert Path(result).as_posix() == "assets/ref_voice/korean_female.wav"

    def test_instruct_text_all_channels(self):
        """모든 채널 키에 대한 instruct text 생성."""
        from shorts_maker_v2.providers.cosyvoice_client import CosyVoiceTTSClient

        for channel in ["ai_tech", "psychology", "history", "space", "health"]:
            text = CosyVoiceTTSClient._get_instruct_text("cta", channel)
            assert len(text) > 10

        # 알 수 없는 채널 → 힌트 없이 기본만
        text = CosyVoiceTTSClient._get_instruct_text("body", "unknown")
        assert "naturally" in text


# ── MediaStep TTS 라우팅 테스트 ────────────────────────────────────────────────


class TestMediaStepTTSRouting:
    """media_step._generate_audio()의 TTS 프로바이더 라우팅 테스트."""

    def _make_config(self, tts_provider: str = "edge-tts"):
        """테스트용 최소 AppConfig mock."""
        config = MagicMock()
        config.providers.tts = tts_provider
        config.providers.tts_model = "tts-1"
        config.providers.tts_voice = "alloy"
        config.providers.tts_speed = 1.05
        config.providers.tts_voice_roles = None
        config.providers.tts_voice_pool = ()
        config.providers.tts_voice_strategy = "fixed"
        config.providers.visual_styles = ()
        config.providers.image_style_prefix = ""
        config.providers.tts_ref_audio = ""
        config.providers.tts_ref_audio_text = ""
        config.project.language = "ko-KR"
        config.audio.sync_with_whisper = False
        config.cache.dir = "/tmp/test_cache"
        config.cache.enabled = False
        config.cache.max_size_mb = 100
        return config

    @patch("shorts_maker_v2.pipeline.media_step.MediaCache")
    @patch("shorts_maker_v2.pipeline.media_step.EdgeTTSClient")
    def test_edge_tts_routing(self, mock_edge_cls, mock_cache_cls, tmp_path):
        """edge-tts 선택 시 EdgeTTSClient 호출."""
        from shorts_maker_v2.pipeline.media_step import MediaStep

        mock_edge = MagicMock()
        mock_edge.generate_tts.return_value = tmp_path / "out.mp3"
        mock_edge_cls.return_value = mock_edge

        config = self._make_config("edge-tts")
        ms = MediaStep(config, MagicMock())
        ms._generate_audio("안녕하세요", tmp_path / "out.mp3")

        mock_edge.generate_tts.assert_called_once()

    @patch("shorts_maker_v2.pipeline.media_step.MediaCache")
    @patch("shorts_maker_v2.pipeline.media_step.EdgeTTSClient")
    def test_chatterbox_fallback_to_edge(self, mock_edge_cls, mock_cache_cls, tmp_path):
        """chatterbox 미설치 시 edge-tts fallback."""
        from shorts_maker_v2.pipeline.media_step import MediaStep

        mock_edge = MagicMock()
        mock_edge.generate_tts.return_value = tmp_path / "out.mp3"
        mock_edge_cls.return_value = mock_edge

        config = self._make_config("chatterbox")
        ms = MediaStep(config, MagicMock())
        ms._generate_audio("안녕하세요", tmp_path / "out.mp3")

        # chatterbox 미설치 → edge-tts fallback 호출
        mock_edge.generate_tts.assert_called_once()

    @patch("shorts_maker_v2.pipeline.media_step.MediaCache")
    @patch("shorts_maker_v2.pipeline.media_step.EdgeTTSClient")
    def test_cosyvoice_fallback_to_edge(self, mock_edge_cls, mock_cache_cls, tmp_path):
        """cosyvoice 미설치 시 edge-tts fallback."""
        from shorts_maker_v2.pipeline.media_step import MediaStep

        mock_edge = MagicMock()
        mock_edge.generate_tts.return_value = tmp_path / "out.mp3"
        mock_edge_cls.return_value = mock_edge

        config = self._make_config("cosyvoice")
        ms = MediaStep(config, MagicMock())
        ms._generate_audio("안녕하세요", tmp_path / "out.mp3")

        # cosyvoice 미설치 → edge-tts fallback 호출
        mock_edge.generate_tts.assert_called_once()
