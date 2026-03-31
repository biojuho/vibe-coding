"""FreesoundClient 단위 테스트."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from shorts_maker_v2.providers.freesound_client import (
    BGM_ENERGY_TAGS,
    CHANNEL_BGM_ENERGY,
    FreesoundClient,
)

# ════════════════════════════════════════════════════════════
# 초기화
# ════════════════════════════════════════════════════════════


class TestFreesoundClientInit:
    def test_raises_without_api_key(self):
        with pytest.raises(ValueError, match="FREESOUND_API_KEY"):
            FreesoundClient(api_key="")

    def test_init_success(self):
        client = FreesoundClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client._auth == {"token": "test_key"}

    @patch.dict("os.environ", {"FREESOUND_API_KEY": "env_key"})
    def test_from_env(self):
        client = FreesoundClient.from_env()
        assert client.api_key == "env_key"

    @patch.dict("os.environ", {"FREESOUND_API_KEY": ""})
    def test_from_env_raises_without_key(self):
        with pytest.raises(EnvironmentError, match="FREESOUND_API_KEY"):
            FreesoundClient.from_env()


# ════════════════════════════════════════════════════════════
# 검색
# ════════════════════════════════════════════════════════════


class TestFreesoundSearch:
    @patch("shorts_maker_v2.providers.freesound_client.requests.get")
    def test_returns_results_list(self, mock_get):
        mock_get.return_value.json.return_value = {
            "results": [
                {
                    "id": 123,
                    "name": "epic_bgm.mp3",
                    "duration": 60.0,
                    "previews": {"preview-hq-mp3": "https://freesound.org/preview.mp3"},
                }
            ]
        }
        mock_get.return_value.raise_for_status = lambda: None

        client = FreesoundClient(api_key="key")
        result = client.search(query="epic orchestral")
        assert len(result) == 1
        assert result[0]["id"] == 123

    @patch("shorts_maker_v2.providers.freesound_client.requests.get")
    def test_empty_results(self, mock_get):
        mock_get.return_value.json.return_value = {"results": []}
        mock_get.return_value.raise_for_status = lambda: None

        client = FreesoundClient(api_key="key")
        result = client.search(query="xyz_nonexistent")
        assert result == []


# ════════════════════════════════════════════════════════════
# 미리듣기 다운로드
# ════════════════════════════════════════════════════════════


class TestFreesoundDownloadPreview:
    @patch("shorts_maker_v2.providers.freesound_client.requests.get")
    def test_downloads_hq_preview(self, mock_get, tmp_path):
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.iter_content = lambda chunk_size: [b"audio_data"]

        sound = {
            "id": 1,
            "duration": 60.0,
            "previews": {"preview-hq-mp3": "https://freesound.org/hq.mp3"},
        }
        client = FreesoundClient(api_key="key")
        result = client.download_preview(
            sound=sound,
            output_path=tmp_path / "bgm.mp3",
        )
        assert result.exists()

    def test_raises_without_preview_url(self, tmp_path):
        sound = {"id": 2, "previews": {}}
        client = FreesoundClient(api_key="key")
        with pytest.raises(RuntimeError, match="No preview URL"):
            client.download_preview(sound=sound, output_path=tmp_path / "x.mp3")

    @patch("shorts_maker_v2.providers.freesound_client.requests.get")
    def test_skips_download_if_file_exists(self, mock_get, tmp_path):
        existing = tmp_path / "bgm.mp3"
        existing.write_bytes(b"existing")

        sound = {"id": 3, "duration": 30.0, "previews": {"preview-hq-mp3": "url"}}
        client = FreesoundClient(api_key="key")
        result = client.download_preview(sound=sound, output_path=existing)

        mock_get.assert_not_called()
        assert result == existing


# ════════════════════════════════════════════════════════════
# 채널별 BGM 다운로드
# ════════════════════════════════════════════════════════════


class TestDownloadBgmForChannel:
    def _make_client(self) -> FreesoundClient:
        return FreesoundClient(api_key="test")

    @patch.object(FreesoundClient, "download_preview")
    @patch.object(FreesoundClient, "search")
    def test_uses_channel_energy_mapping(self, mock_search, mock_dl, tmp_path):
        mock_search.return_value = [{"id": 1, "previews": {"preview-hq-mp3": "url"}}]
        mock_dl.return_value = tmp_path / "bgm.mp3"

        client = self._make_client()
        client.download_bgm_for_channel(
            channel="space",
            output_path=tmp_path / "bgm.mp3",
        )
        # space = epic energy → "epic orchestral cinematic dramatic loop"
        call_query = mock_search.call_args[1]["query"]
        assert "epic" in call_query

    @patch.object(FreesoundClient, "search")
    def test_raises_when_no_results(self, mock_search, tmp_path):
        mock_search.return_value = []
        client = self._make_client()
        with pytest.raises(RuntimeError, match="검색 결과 없음"):
            client.download_bgm_for_channel(
                channel="ai_tech",
                output_path=tmp_path / "bgm.mp3",
            )

    def test_cache_hit_skips_search(self, tmp_path):
        existing = tmp_path / "bgm.mp3"
        existing.write_bytes(b"cached_audio")

        client = self._make_client()
        with patch.object(FreesoundClient, "search") as mock_search:
            result = client.download_bgm_for_channel(
                channel="health",
                output_path=existing,
            )
            mock_search.assert_not_called()
        assert result == existing


# ════════════════════════════════════════════════════════════
# 채널 에너지 매핑 검증
# ════════════════════════════════════════════════════════════


class TestEnergyMapping:
    def test_all_channels_have_energy(self):
        for channel in ["ai_tech", "psychology", "history", "space", "health"]:
            energy = FreesoundClient.get_energy_for_channel(channel)
            assert energy in BGM_ENERGY_TAGS, f"{channel} 에너지 {energy!r}가 BGM_ENERGY_TAGS에 없음"

    def test_unknown_channel_returns_default(self):
        energy = FreesoundClient.get_energy_for_channel("unknown_channel")
        assert energy == "medium"

    def test_all_energies_have_query(self):
        for energy in ["high", "medium", "calm", "epic"]:
            query = FreesoundClient.get_query_for_energy(energy)
            assert len(query) > 0

    def test_channel_energy_consistency(self):
        """CHANNEL_BGM_ENERGY 모든 값이 BGM_ENERGY_TAGS에 있어야 함."""
        for channel, energy in CHANNEL_BGM_ENERGY.items():
            assert energy in BGM_ENERGY_TAGS, f"채널 {channel!r}의 energy {energy!r}가 BGM_ENERGY_TAGS에 없음"
