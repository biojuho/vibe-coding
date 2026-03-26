from __future__ import annotations

import config as config_module
from pipeline import analytics_tracker as analytics_module
from pipeline import image_generator as image_module
from pipeline import twitter_poster as twitter_module


class DummyConfig:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


def test_twitter_poster_uses_env_credentials(monkeypatch):
    monkeypatch.setenv("TWITTER_ENABLED", "true")
    monkeypatch.setenv("TWITTER_CONSUMER_KEY", "ck")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "cs")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "at")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ats")

    class FakeOAuth:
        def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):
            self.values = (consumer_key, consumer_secret, access_token, access_token_secret)

    class FakeAPI:
        def __init__(self, auth):
            self.auth = auth

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(twitter_module.tweepy, "OAuth1UserHandler", FakeOAuth)
    monkeypatch.setattr(twitter_module.tweepy, "API", FakeAPI)
    monkeypatch.setattr(twitter_module.tweepy, "Client", FakeClient)

    poster = twitter_module.TwitterPoster(DummyConfig({"twitter.enabled": False}))

    assert poster.enabled is True
    assert poster.consumer_key == "ck"
    assert poster.client_v2.kwargs["access_token"] == "at"


def test_analytics_tracker_uses_env_credentials(monkeypatch):
    monkeypatch.setenv("TWITTER_ENABLED", "true")
    monkeypatch.setenv("TWITTER_CONSUMER_KEY", "ck")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRET", "cs")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN", "at")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRET", "ats")

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(analytics_module.tweepy, "Client", FakeClient)

    tracker = analytics_module.AnalyticsTracker(DummyConfig({"twitter.enabled": False}))

    assert tracker.enabled is True
    assert tracker.client_v2.kwargs["consumer_secret"] == "cs"


def test_image_generator_uses_env_flag(monkeypatch):
    monkeypatch.setenv("OPENAI_IMAGE_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key

    import openai
    monkeypatch.setattr(openai, "AsyncOpenAI", FakeClient)

    generator = image_module.ImageGenerator(
        DummyConfig({"openai.enabled": False, "image.provider": "dalle"}),
    )

    assert generator.enabled is True
    assert generator.client.api_key == "openai-key"


def test_resolve_ascii_curl_ca_bundle_prefers_public_ascii_copy(monkeypatch):
    copied: dict[str, str] = {}

    monkeypatch.setenv("PUBLIC", r"C:\Public")
    monkeypatch.setenv("ProgramData", r"C:\ProgramData")
    monkeypatch.setattr(config_module.os.path, "exists", lambda _path: False)
    monkeypatch.setattr(config_module.os.path, "getsize", lambda _path: 123)
    monkeypatch.setattr(config_module.os, "makedirs", lambda path, exist_ok=True: copied.setdefault("dir", path))
    monkeypatch.setattr(
        config_module.shutil,
        "copyfile",
        lambda src, dst: copied.update({"src": src, "dst": dst}),
    )

    result = config_module._resolve_ascii_curl_ca_bundle(r"C:\Users\박주호\venv\cacert.pem")

    assert result == r"C:\Public\btx-cert\certifi-cacert.pem"
    assert copied["dir"] == r"C:\Public\btx-cert"
    assert copied["dst"] == result


def test_resolve_ascii_curl_ca_bundle_falls_back_to_short_path(monkeypatch):
    monkeypatch.setattr(config_module, "_ascii_ca_bundle_candidates", lambda: [r"C:\Public\btx-cert"])
    monkeypatch.setattr(
        config_module.os,
        "makedirs",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("blocked")),
    )
    monkeypatch.setattr(
        config_module,
        "_get_windows_short_path",
        lambda _path: r"C:\PROGRA~1\Certifi\cacert.pem",
    )

    result = config_module._resolve_ascii_curl_ca_bundle(r"C:\Users\박주호\venv\cacert.pem")

    assert result == r"C:\PROGRA~1\Certifi\cacert.pem"
