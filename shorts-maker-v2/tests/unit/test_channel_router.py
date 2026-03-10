"""
test_channel_router.py
======================
채널 라우터 단위 테스트.

실행:
    cd "c:\\Users\\박주호\\Desktop\\Vibe coding\\shorts-maker-v2"
    python -m pytest tests/unit/test_channel_router.py -v
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import pytest

# 프로젝트 루트 기준 channel_profiles.yaml 경로
_PROFILES_YAML = Path(__file__).parents[2] / "channel_profiles.yaml"


class TestChannelRouter:
    def _get_router(self):
        """ChannelRouter를 실제 channel_profiles.yaml로 로드."""
        from shorts_maker_v2.utils.channel_router import ChannelRouter
        return ChannelRouter(profiles_path=_PROFILES_YAML)

    def test_load_profiles(self):
        """5개 채널 프로파일이 모두 로드되는지 확인."""
        router = self._get_router()
        channels = router.list_channels()
        keys = {c["key"] for c in channels}
        assert keys == {"ai_tech", "psychology", "history", "space", "health"}, (
            f"예상 채널 키와 다릅니다: {keys}"
        )

    def test_get_profile_ai_tech(self):
        """퓨처 시냅스 프로파일 주요 필드 확인."""
        router = self._get_router()
        profile = router.get_profile("ai_tech")
        assert profile["display_name"] == "퓨처 시냅스"
        assert "ko-KR" in profile["tts_voice"]
        assert isinstance(profile["visual_styles"], list)
        assert len(profile["visual_styles"]) >= 1

    def test_get_profile_unknown_raises(self):
        """존재하지 않는 채널 키는 ValueError 발생."""
        router = self._get_router()
        with pytest.raises(ValueError, match="알 수 없는 채널 키"):
            router.get_profile("unknown_channel")

    def test_get_channel_context_nonempty(self):
        """모든 채널의 persona_channel_context가 비어있지 않은지 확인."""
        router = self._get_router()
        for ch in ["ai_tech", "psychology", "history", "space", "health"]:
            ctx = router.get_channel_context(ch)
            assert len(ctx) > 50, f"[{ch}] channel_context가 너무 짧습니다: {ctx!r}"

    def test_get_channel_context_empty_key(self):
        """빈 채널 키는 빈 문자열을 반환."""
        router = self._get_router()
        assert router.get_channel_context("") == ""
        assert router.get_channel_context("nonexistent") == ""

    def test_get_notion_channel_name(self):
        """Notion DB 채널명이 올바르게 반환되는지 확인."""
        router = self._get_router()
        assert router.get_notion_channel_name("ai_tech") == "AI/기술"
        assert router.get_notion_channel_name("psychology") == "심리학"
        assert router.get_notion_channel_name("history") == "역사/고고학"
        assert router.get_notion_channel_name("space") == "우주/천문학"
        assert router.get_notion_channel_name("health") == "의학/건강"

    def test_apply_tts_voice_override(self):
        """apply()가 TTS 음성을 채널 프로파일로 교체하는지 확인."""
        from shorts_maker_v2.config import load_config
        router = self._get_router()

        config_path = Path(__file__).parents[3] / "config.yaml"
        if not config_path.exists():
            pytest.skip("config.yaml을 찾을 수 없습니다.")

        base_config = load_config(config_path)
        new_config = router.apply(base_config, "ai_tech")

        # ai_tech 프로파일의 tts_voice가 적용됐는지 확인
        profile = router.get_profile("ai_tech")
        assert new_config.providers.tts_voice == profile["tts_voice"], (
            f"TTS 음성이 적용되지 않았습니다. 현재: {new_config.providers.tts_voice}"
        )

    def test_apply_does_not_mutate_original(self):
        """apply()는 원본 config를 변경하지 않는지 확인 (deepcopy)."""
        from shorts_maker_v2.config import load_config
        router = self._get_router()

        config_path = Path(__file__).parents[3] / "config.yaml"
        if not config_path.exists():
            pytest.skip("config.yaml을 찾을 수 없습니다.")

        base_config = load_config(config_path)
        original_voice = base_config.providers.tts_voice
        _ = router.apply(base_config, "psychology")

        # 원본 음성이 변경되지 않아야 함
        assert base_config.providers.tts_voice == original_voice

    def test_apply_unknown_channel_returns_original(self):
        """존재하지 않는 채널 키는 원본 config를 그대로 반환."""
        from shorts_maker_v2.config import load_config
        router = self._get_router()

        config_path = Path(__file__).parents[3] / "config.yaml"
        if not config_path.exists():
            pytest.skip("config.yaml을 찾을 수 없습니다.")

        base_config = load_config(config_path)
        new_config = router.apply(base_config, "invalid_key")
        assert new_config.providers.tts_voice == base_config.providers.tts_voice

    def test_apply_empty_channel_returns_original(self):
        """빈 채널 키는 원본 config를 그대로 반환."""
        from shorts_maker_v2.config import load_config
        router = self._get_router()

        config_path = Path(__file__).parents[3] / "config.yaml"
        if not config_path.exists():
            pytest.skip("config.yaml을 찾을 수 없습니다.")

        base_config = load_config(config_path)
        new_config = router.apply(base_config, "")
        assert new_config is base_config
