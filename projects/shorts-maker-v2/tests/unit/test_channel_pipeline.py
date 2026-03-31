"""channel_pipeline 단위 테스트."""

from unittest.mock import patch

from shorts_maker_v2.templates.channel_pipeline import ChannelPipeline


class TestChannelPipeline:
    def test_init_with_profile(self):
        profile = {
            "display_name": "AI Tech",
            "highlight_keywords": ["AI", "GPT"],
            "highlight_color": "#00FF00",
            "caption_combo": ["bold", "neon", "default"],
        }
        cp = ChannelPipeline("ai_tech", profile=profile)
        assert cp.channel_key == "ai_tech"
        assert cp._keyword_map is not None
        assert len(cp._keyword_map) > 0

    def test_init_no_keywords(self):
        cp = ChannelPipeline("test", profile={})
        assert cp._keyword_map is None

    def test_keyword_map_property(self):
        cp = ChannelPipeline("test", profile={})
        assert cp.keyword_map is None

    def test_caption_combo_default(self):
        cp = ChannelPipeline("test", profile={})
        combo = cp.caption_combo
        assert len(combo) == 3
        assert combo == ("default", "default", "default")

    def test_caption_combo_from_profile(self):
        cp = ChannelPipeline("test", profile={"caption_combo": ["bold", "neon", "cta"]})
        assert cp.caption_combo == ("bold", "neon", "cta")

    def test_info(self):
        profile = {"display_name": "Space Channel"}
        with patch.object(ChannelPipeline, "list_templates", return_value=[]):
            cp = ChannelPipeline("space", profile=profile)
            info = cp.info()
            assert info["channel"] == "space"
            assert info["display_name"] == "Space Channel"
            assert "templates" in info

    def test_get_generator_wrong_channel(self):
        profile = {}
        with patch("shorts_maker_v2.templates.get", return_value={"channel": "ai_tech", "name": "x"}):
            cp = ChannelPipeline("space", profile=profile)
            try:
                cp.get_generator("x")
                raise AssertionError()
            except ValueError as e:
                assert "ai_tech" in str(e)

    def test_get_generator_not_found(self):
        profile = {}
        with (
            patch("shorts_maker_v2.templates.get", return_value=None),
            patch.object(ChannelPipeline, "list_templates", return_value=[]),
        ):
            cp = ChannelPipeline("space", profile=profile)
            try:
                cp.get_generator("nonexistent")
                raise AssertionError()
            except ValueError as e:
                assert "nonexistent" in str(e)

    def test_load_profile_fallback(self):
        result = ChannelPipeline._load_profile("nonexistent_channel_xyz")
        assert isinstance(result, dict)
