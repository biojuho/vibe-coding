from __future__ import annotations

import sys
import types

import execution.content_db as cdb
import execution.youtube_uploader as uploader


def _install_fake_credentials(monkeypatch, credentials_cls) -> None:
    google_mod = types.ModuleType("google")
    oauth2_mod = types.ModuleType("google.oauth2")
    creds_mod = types.ModuleType("google.oauth2.credentials")
    creds_mod.Credentials = credentials_cls
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.oauth2", oauth2_mod)
    monkeypatch.setitem(sys.modules, "google.oauth2.credentials", creds_mod)


def _install_fake_media_upload(monkeypatch, media_upload_cls) -> None:
    googleapiclient_mod = types.ModuleType("googleapiclient")
    http_mod = types.ModuleType("googleapiclient.http")
    http_mod.MediaFileUpload = media_upload_cls
    monkeypatch.setitem(sys.modules, "googleapiclient", googleapiclient_mod)
    monkeypatch.setitem(sys.modules, "googleapiclient.http", http_mod)


def test_get_auth_status_without_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", tmp_path / "credentials.json")
    monkeypatch.setattr(uploader, "TOKEN_PATH", tmp_path / "token.json")

    status = uploader.get_auth_status()

    assert status["has_credentials_file"] is False
    assert status["ready"] is False
    assert "credentials.json 없음" in status["reason"]


def test_get_auth_status_without_token(monkeypatch, tmp_path):
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", credentials_path)
    monkeypatch.setattr(uploader, "TOKEN_PATH", tmp_path / "token.json")

    status = uploader.get_auth_status()

    assert status["has_credentials_file"] is True
    assert status["has_token_file"] is False
    assert status["ready"] is True
    assert status["token_valid_or_refreshable"] is False
    assert "token.json 없음" in status["reason"]


def test_get_auth_status_with_refreshable_token(monkeypatch, tmp_path):
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "token.json"
    credentials_path.write_text("{}", encoding="utf-8")
    token_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", credentials_path)
    monkeypatch.setattr(uploader, "TOKEN_PATH", token_path)

    class FakeCredentials:
        def __init__(self, *, valid: bool, refresh_token: str | None):
            self.valid = valid
            self.refresh_token = refresh_token

        @classmethod
        def from_authorized_user_file(cls, filename, scopes):
            assert filename == str(token_path)
            assert scopes == uploader.SCOPES
            return cls(valid=False, refresh_token="refresh-token")

    _install_fake_credentials(monkeypatch, FakeCredentials)

    status = uploader.get_auth_status()

    assert status["has_credentials_file"] is True
    assert status["has_token_file"] is True
    assert status["token_valid_or_refreshable"] is True
    assert status["ready"] is True
    assert status["reason"] == "토큰 준비 완료"


def test_upload_video_uses_official_body(monkeypatch, tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video")

    class FakeMediaFileUpload:
        def __init__(self, filename, mimetype, resumable, chunksize):
            self.filename = filename
            self.mimetype = mimetype
            self.resumable = resumable
            self.chunksize = chunksize

    class FakeInsertRequest:
        def __init__(self):
            self.calls = 0

        def next_chunk(self):
            self.calls += 1
            return None, {"id": "video123"}

    class FakeVideos:
        def __init__(self):
            self.insert_kwargs = None

        def insert(self, **kwargs):
            self.insert_kwargs = kwargs
            return FakeInsertRequest()

    class FakeService:
        def __init__(self):
            self.videos_api = FakeVideos()

        def videos(self):
            return self.videos_api

    fake_service = FakeService()
    monkeypatch.setattr(uploader, "_build_youtube_service", lambda: fake_service)
    _install_fake_media_upload(monkeypatch, FakeMediaFileUpload)

    result = uploader.upload_video(
        video_path=str(video_path),
        title="테스트 제목",
        description="테스트 설명",
        tags=["space", "shorts"],
        privacy_status="private",
    )

    body = fake_service.videos_api.insert_kwargs["body"]
    assert result["video_id"] == "video123"
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["selfDeclaredMadeForKids"] is False
    assert "shorts" not in body["status"]


def test_get_video_status_returns_not_found(monkeypatch):
    class FakeVideos:
        def list(self, **kwargs):
            assert kwargs["part"] == "status,processingDetails"
            assert kwargs["id"] == "missing"
            return types.SimpleNamespace(execute=lambda: {"items": []})

    class FakeService:
        def videos(self):
            return FakeVideos()

    monkeypatch.setattr(uploader, "_build_youtube_service", lambda: FakeService())

    result = uploader.get_video_status("missing")

    assert result == {"video_id": "missing", "status": "not_found"}


def test_upload_pending_items_retries_failed_items(monkeypatch):
    calls: dict[str, object] = {}
    updates: list[tuple[int, dict[str, object]]] = []
    item = {
        "id": 7,
        "topic": "블랙홀",
        "title": "블랙홀 5가지",
        "video_path": "video.mp4",
        "channel": "우주/천문학",
        "youtube_status": "failed",
    }

    monkeypatch.setattr(cdb, "init_db", lambda: calls.setdefault("init_db", True))
    def fake_get_uploadable_items(channel=None, limit=10, include_failed=False):
        calls["query"] = {"channel": channel, "limit": limit, "include_failed": include_failed}
        return [item]

    monkeypatch.setattr(cdb, "get_uploadable_items", fake_get_uploadable_items)
    monkeypatch.setattr(cdb, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))
    monkeypatch.setattr(
        uploader,
        "upload_video",
        lambda **kwargs: {"video_id": "abc123", "youtube_url": "https://youtu.be/abc123", "status": "uploaded"},
    )

    results = uploader.upload_pending_items(limit=3, channel="우주/천문학", retry_failed=True)

    assert calls["query"] == {"channel": "우주/천문학", "limit": 3, "include_failed": True}
    assert results[0]["video_id"] == "abc123"
    assert updates[0][1]["youtube_status"] == ""
    assert updates[0][1]["youtube_error"] == ""
    assert updates[1][1]["youtube_status"] == "uploaded"
    assert updates[1][1]["youtube_error"] == ""


def test_upload_pending_items_records_youtube_error(monkeypatch):
    updates: list[tuple[int, dict[str, object]]] = []
    item = {
        "id": 9,
        "topic": "화성",
        "title": "화성 이주",
        "video_path": "video.mp4",
        "channel": "우주/천문학",
        "youtube_status": "",
    }

    monkeypatch.setattr(cdb, "init_db", lambda: None)
    monkeypatch.setattr(cdb, "get_uploadable_items", lambda channel=None, limit=10, include_failed=False: [item])
    monkeypatch.setattr(cdb, "update_job", lambda item_id, **kwargs: updates.append((item_id, kwargs)))
    monkeypatch.setattr(uploader, "upload_video", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("quota exceeded")))

    results = uploader.upload_pending_items(limit=1, retry_failed=False)

    assert results[0]["status"] == "failed"
    assert updates[-1][1]["youtube_status"] == "failed"
    assert updates[-1][1]["youtube_error"] == "quota exceeded"
    assert "notes" not in updates[-1][1]
