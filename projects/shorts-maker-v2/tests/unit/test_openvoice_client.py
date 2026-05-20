"""Unit tests for OpenVoice v2 TTS Client and MediaAudioMixin routing."""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.providers.openvoice_client import (
    OpenVoiceTTSClient,
    _get_base_tts,
    _get_converter,
    _model_cache,
    is_openvoice_available,
)


@pytest.fixture(autouse=True)
def clear_model_cache():
    """테스트마다 모델 캐시를 초기화합니다."""
    _model_cache.clear()


class TestOpenVoiceAvailability:
    def test_is_openvoice_available_false(self, monkeypatch):
        """openvoice 또는 melo 미설치 시 is_openvoice_available이 False를 반환하는지 테스트."""
        monkeypatch.setitem(sys.modules, "openvoice", None)
        monkeypatch.setitem(sys.modules, "openvoice.api", None)
        monkeypatch.setitem(sys.modules, "melo", None)
        monkeypatch.setitem(sys.modules, "melo.api", None)

        assert is_openvoice_available() is False

    def test_is_openvoice_available_true(self, monkeypatch):
        """openvoice 및 melo가 설치되어 있을 때 is_openvoice_available이 True를 반환하는지 테스트."""
        fake_openvoice = types.ModuleType("openvoice")
        fake_openvoice_api = types.ModuleType("openvoice.api")
        fake_openvoice_api.ToneColorConverter = MagicMock()
        fake_openvoice.api = fake_openvoice_api

        fake_melo = types.ModuleType("melo")
        fake_melo_api = types.ModuleType("melo.api")
        fake_melo_api.TTS = MagicMock()
        fake_melo.api = fake_melo_api

        monkeypatch.setitem(sys.modules, "openvoice", fake_openvoice)
        monkeypatch.setitem(sys.modules, "openvoice.api", fake_openvoice_api)
        monkeypatch.setitem(sys.modules, "melo", fake_melo)
        monkeypatch.setitem(sys.modules, "melo.api", fake_melo_api)

        assert is_openvoice_available() is True


class TestOpenVoiceLazyLoading:
    def test_get_converter_not_found_error(self, monkeypatch, tmp_path):
        """체크포인트 디렉토리가 없거나 파일이 없으면 FileNotFoundError를 유발하는지 테스트."""
        # openvoice 미설치 환경에서도 체크포인트 검증 경로에 도달하도록 가짜 모듈 주입
        fake_openvoice = types.ModuleType("openvoice")
        fake_openvoice_api = types.ModuleType("openvoice.api")
        fake_openvoice_api.ToneColorConverter = MagicMock()
        fake_openvoice.api = fake_openvoice_api
        monkeypatch.setitem(sys.modules, "openvoice", fake_openvoice)
        monkeypatch.setitem(sys.modules, "openvoice.api", fake_openvoice_api)

        checkpoint_dir = tmp_path / "checkpoints_v2"
        # 존재하지 않는 경로 (config.json / checkpoint.pth 없음)

        with pytest.raises(FileNotFoundError, match="OpenVoice v2 컨버터 체크포인트가 없습니다"):
            _get_converter(str(checkpoint_dir))

    def test_get_converter_import_error(self, monkeypatch, tmp_path):
        """openvoice 패키지 가져오기 실패 시 ImportError 유발 테스트."""
        checkpoint_dir = tmp_path / "checkpoints_v2" / "converter"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        (checkpoint_dir / "config.json").touch()
        (checkpoint_dir / "checkpoint.pth").touch()

        monkeypatch.setitem(sys.modules, "openvoice", None)
        monkeypatch.setitem(sys.modules, "openvoice.api", None)

        with pytest.raises(ImportError, match="openvoice 패키지가 설치되지 않았습니다"):
            _get_converter(str(checkpoint_dir))

    def test_get_base_tts_import_error(self, monkeypatch):
        """melo 패키지 가져오기 실패 시 ImportError 유발 테스트."""
        monkeypatch.setitem(sys.modules, "melo", None)
        monkeypatch.setitem(sys.modules, "melo.api", None)

        with pytest.raises(ImportError, match="melo 패키지.*가 설치되지 않았습니다"):
            _get_base_tts("KR")


class TestOpenVoiceTTSClient:
    @patch("shorts_maker_v2.providers.openvoice_client._get_converter")
    @patch("shorts_maker_v2.providers.openvoice_client._get_base_tts")
    def test_generate_tts_success(self, mock_get_base_tts, mock_get_converter, tmp_path, monkeypatch):
        """성공적인 OpenVoice 음성 복제 파이프라인 검증."""
        # 1. Mocking ToneColorConverter
        mock_converter = MagicMock()
        mock_get_converter.return_value = mock_converter

        # 2. Mocking MeloTTS Base TTS
        mock_base_tts = MagicMock()
        mock_base_tts.hps.data.spk2id = {"KR-Default": 0}
        mock_get_base_tts.return_value = mock_base_tts

        # 3. Mocking se_extractor (openvoice 패키지 미설치 환경에서도 import 가능하도록 부모 모듈 주입)
        fake_se_extractor = types.ModuleType("openvoice.se_extractor")
        fake_se_extractor.get_se = MagicMock(return_value=("fake_target_se", None))
        fake_openvoice = types.ModuleType("openvoice")
        fake_openvoice.se_extractor = fake_se_extractor
        monkeypatch.setitem(sys.modules, "openvoice", fake_openvoice)
        monkeypatch.setitem(sys.modules, "openvoice.se_extractor", fake_se_extractor)

        # 4. Mocking whisper_aligner & edge_tts
        fake_whisper = MagicMock(return_value=[{"word": "테스트", "start": 0.0, "end": 0.5}])
        monkeypatch.setattr(
            "shorts_maker_v2.providers.whisper_aligner.transcribe_to_word_timings",
            fake_whisper,
        )
        monkeypatch.setattr(
            "shorts_maker_v2.providers.whisper_aligner.is_whisper_available",
            lambda: True,
        )

        # 5. Client & Call
        ref_audio = tmp_path / "ref.wav"
        ref_audio.touch()

        output_wav = tmp_path / "output.wav"
        words_json = tmp_path / "output_words.json"

        client = OpenVoiceTTSClient(
            checkpoint_dir=str(tmp_path / "checkpoints_v2"),
            ref_audio_path=ref_audio,
            device="cpu",
        )

        result_path = client.generate_tts(
            model="openvoice",
            voice="default",
            speed=1.0,
            text="안녕하세요 테스트입니다.",
            output_path=output_wav,
            words_json_path=words_json,
        )

        assert result_path == output_wav
        mock_base_tts.tts_to_file.assert_called_once()
        mock_converter.convert.assert_called_once()
        assert words_json.exists()


class TestMediaAudioMixinOpenVoice:
    class DummyMediaStep:
        def __init__(self, config):
            self.config = config
            self._tts_voice = "KR-Default"
            self.openai_client = MagicMock()

    def test_routing_openvoice_available(self, monkeypatch, tmp_path):
        """AppConfig의 tts가 openvoice로 설정되었을 때 OpenVoiceTTSClient가 호출되는지 테스트."""
        # Config setup
        from shorts_maker_v2.config import AppConfig, AudioSettings, ProjectSettings, ProviderSettings

        providers = ProviderSettings(
            llm="openai",
            tts="openvoice",
            visual_primary="google-veo",
            visual_fallback="openai-image",
            llm_model="gpt-4",
            tts_model="melo",
            tts_voice="KR-Default",
            tts_speed=1.0,
            image_model="dall-e-3",
            image_size="1024x1792",
            image_quality="standard",
            veo_model="veo-2.0",
            tts_openvoice_checkpoint_dir=str(tmp_path / "checkpoints_v2"),
            tts_ref_audio=str(tmp_path / "ref.wav"),
        )
        audio_cfg = AudioSettings(sync_with_whisper=True)
        project_cfg = ProjectSettings(
            language="ko-KR",
            default_scene_count=5,
        )

        # Mock AppConfig
        mock_config = MagicMock(spec=AppConfig)
        mock_config.providers = providers
        mock_config.audio = audio_cfg
        mock_config.project = project_cfg

        # Mixin setup
        from shorts_maker_v2.pipeline.media.audio_mixin import MediaAudioMixin

        class MockStep(MediaAudioMixin, self.DummyMediaStep):
            pass

        step = MockStep(mock_config)

        # Mock OpenVoiceTTSClient
        mock_client_instance = MagicMock()
        mock_client_instance.generate_tts.return_value = tmp_path / "output.wav"

        mock_client_class = MagicMock(return_value=mock_client_instance)

        # audio_mixin은 함수 내부에서 openvoice_client를 import하므로 소스 모듈에 패치
        import shorts_maker_v2.providers.openvoice_client as ov_client

        monkeypatch.setattr(ov_client, "OpenVoiceTTSClient", mock_client_class)
        monkeypatch.setattr(ov_client, "is_openvoice_available", lambda: True)

        output_path = tmp_path / "output.wav"

        result = step._generate_audio("안녕하세요", output_path)

        assert result == output_path
        mock_client_class.assert_called_once_with(
            checkpoint_dir=str(tmp_path / "checkpoints_v2"),
            ref_audio_path=str(tmp_path / "ref.wav"),
        )
        mock_client_instance.generate_tts.assert_called_once()

    def test_routing_openvoice_fallback_to_edge_tts(self, monkeypatch, tmp_path):
        """openvoice 라이브러리가 미설치되었거나 실패 시 edge-tts로 우아하게 fallback하는지 테스트."""
        from shorts_maker_v2.config import AppConfig, AudioSettings, ProjectSettings, ProviderSettings

        providers = ProviderSettings(
            llm="openai",
            tts="openvoice",
            visual_primary="google-veo",
            visual_fallback="openai-image",
            llm_model="gpt-4",
            tts_model="melo",
            tts_voice="KR-Default",
            tts_speed=1.0,
            image_model="dall-e-3",
            image_size="1024x1792",
            image_quality="standard",
            veo_model="veo-2.0",
        )
        audio_cfg = AudioSettings(sync_with_whisper=True)
        project_cfg = ProjectSettings(
            language="ko-KR",
            default_scene_count=5,
        )

        mock_config = MagicMock(spec=AppConfig)
        mock_config.providers = providers
        mock_config.audio = audio_cfg
        mock_config.project = project_cfg

        from shorts_maker_v2.pipeline.media.audio_mixin import MediaAudioMixin

        class MockStep(MediaAudioMixin, self.DummyMediaStep):
            pass

        step = MockStep(mock_config)

        # openvoice 미설치 상황 모킹 (audio_mixin은 함수 내부 import → 소스 모듈에 패치)
        monkeypatch.setattr(
            "shorts_maker_v2.providers.openvoice_client.is_openvoice_available",
            lambda: False,
        )

        # EdgeTTSClient 모킹
        mock_edge_instance = MagicMock()
        mock_edge_instance.generate_tts.return_value = tmp_path / "fallback.wav"
        monkeypatch.setattr(
            "shorts_maker_v2.pipeline.media.audio_mixin.EdgeTTSClient",
            lambda: mock_edge_instance,
        )

        output_path = tmp_path / "output.wav"
        result = step._generate_audio("안녕하세요", output_path)

        # edge-tts로 fallback하여 생성된 파일 경로 반환 검증
        assert result == tmp_path / "fallback.wav"
        mock_edge_instance.generate_tts.assert_called_once()
