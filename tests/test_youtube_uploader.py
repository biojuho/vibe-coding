from __future__ import annotations

import sys
import types
from pathlib import Path

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


# ── _get_credentials (lines 40-63) ────────────────────────────


def test_get_credentials_loads_from_token(monkeypatch, tmp_path):
    """_get_credentials loads and returns valid credentials from token.json."""
    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(uploader, "TOKEN_PATH", token_path)
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", tmp_path / "credentials.json")

    class FakeCredentials:
        def __init__(self, *, valid=True, expired=False, refresh_token=None):
            self.valid = valid
            self.expired = expired
            self.refresh_token = refresh_token

        @classmethod
        def from_authorized_user_file(cls, filename, scopes):
            return cls(valid=True)

        def to_json(self):
            return "{}"

    _install_fake_credentials(monkeypatch, FakeCredentials)

    # Mock the transport request and flow
    mock_request = types.ModuleType("google.auth.transport.requests")
    mock_request.Request = lambda: None
    monkeypatch.setitem(sys.modules, "google.auth.transport", types.ModuleType("google.auth.transport"))
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", mock_request)

    mock_flow_mod = types.ModuleType("google_auth_oauthlib.flow")
    mock_flow_mod.InstalledAppFlow = type("InstalledAppFlow", (), {})
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib", types.ModuleType("google_auth_oauthlib"))
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib.flow", mock_flow_mod)

    creds = uploader._get_credentials()
    assert creds.valid is True


def test_get_credentials_refreshes_expired_token(monkeypatch, tmp_path):
    """_get_credentials refreshes expired token with refresh_token."""
    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(uploader, "TOKEN_PATH", token_path)
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", tmp_path / "credentials.json")

    refresh_called = []

    class FakeCredentials:
        def __init__(self, *, valid=False, expired=True, refresh_token="rt"):
            self.valid = valid
            self.expired = expired
            self.refresh_token = refresh_token

        @classmethod
        def from_authorized_user_file(cls, filename, scopes):
            return cls(valid=False, expired=True, refresh_token="rt")

        def refresh(self, request):
            refresh_called.append(True)
            self.valid = True

        def to_json(self):
            return '{"refreshed": true}'

    _install_fake_credentials(monkeypatch, FakeCredentials)

    mock_request_cls = type("Request", (), {"__init__": lambda self: None})
    mock_request_mod = types.ModuleType("google.auth.transport.requests")
    mock_request_mod.Request = mock_request_cls
    monkeypatch.setitem(sys.modules, "google.auth.transport", types.ModuleType("google.auth.transport"))
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", mock_request_mod)

    mock_flow_mod = types.ModuleType("google_auth_oauthlib.flow")
    mock_flow_mod.InstalledAppFlow = type("InstalledAppFlow", (), {})
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib", types.ModuleType("google_auth_oauthlib"))
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib.flow", mock_flow_mod)

    uploader._get_credentials()
    assert len(refresh_called) == 1
    assert token_path.read_text(encoding="utf-8") == '{"refreshed": true}'


def test_get_credentials_browser_auth(monkeypatch, tmp_path):
    """_get_credentials runs browser auth flow when no token exists."""
    monkeypatch.setattr(uploader, "TOKEN_PATH", tmp_path / "token.json")
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", credentials_path)

    class FakeCredentials:
        def __init__(self, **kw):
            self.valid = True

        @classmethod
        def from_authorized_user_file(cls, filename, scopes):
            return None  # Token doesn't exist, will skip

        def to_json(self):
            return '{"new": true}'

    class FakeFlow:
        @classmethod
        def from_client_secrets_file(cls, path, scopes):
            return cls()

        def run_local_server(self, port=0):
            return FakeCredentials()

    _install_fake_credentials(monkeypatch, FakeCredentials)

    mock_request_mod = types.ModuleType("google.auth.transport.requests")
    mock_request_mod.Request = lambda: None
    monkeypatch.setitem(sys.modules, "google.auth.transport", types.ModuleType("google.auth.transport"))
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", mock_request_mod)

    mock_flow_mod = types.ModuleType("google_auth_oauthlib.flow")
    mock_flow_mod.InstalledAppFlow = FakeFlow
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib", types.ModuleType("google_auth_oauthlib"))
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib.flow", mock_flow_mod)

    creds = uploader._get_credentials()
    assert creds.valid is True


def test_get_credentials_no_credentials_file(monkeypatch, tmp_path):
    """_get_credentials raises FileNotFoundError when credentials.json missing."""
    monkeypatch.setattr(uploader, "TOKEN_PATH", tmp_path / "token.json")
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", tmp_path / "missing_credentials.json")

    class FakeCredentials:
        @classmethod
        def from_authorized_user_file(cls, filename, scopes):
            return None

    _install_fake_credentials(monkeypatch, FakeCredentials)

    mock_request_mod = types.ModuleType("google.auth.transport.requests")
    mock_request_mod.Request = lambda: None
    monkeypatch.setitem(sys.modules, "google.auth.transport", types.ModuleType("google.auth.transport"))
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", mock_request_mod)

    mock_flow_mod = types.ModuleType("google_auth_oauthlib.flow")
    mock_flow_mod.InstalledAppFlow = type("InstalledAppFlow", (), {})
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib", types.ModuleType("google_auth_oauthlib"))
    monkeypatch.setitem(sys.modules, "google_auth_oauthlib.flow", mock_flow_mod)

    import pytest as _pt
    with _pt.raises(FileNotFoundError, match="OAuth credentials not found"):
        uploader._get_credentials()


# ── _build_youtube_service (lines 68-71) ──────────────────────


def test_build_youtube_service(monkeypatch):
    """_build_youtube_service calls build with credentials."""
    fake_creds = object()
    monkeypatch.setattr(uploader, "_get_credentials", lambda: fake_creds)

    build_calls = []
    def fake_build(service, version, credentials):
        build_calls.append((service, version, credentials))
        return "fake_service"

    mock_discovery = types.ModuleType("googleapiclient.discovery")
    mock_discovery.build = fake_build
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", mock_discovery)

    result = uploader._build_youtube_service()
    assert result == "fake_service"
    assert build_calls[0] == ("youtube", "v3", fake_creds)


# ── get_auth_status exception (lines 104-107) ────────────────


def test_get_auth_status_exception(monkeypatch, tmp_path):
    """get_auth_status returns failure on credential load exception."""
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "token.json"
    credentials_path.write_text("{}", encoding="utf-8")
    token_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", credentials_path)
    monkeypatch.setattr(uploader, "TOKEN_PATH", token_path)

    class BadCredentials:
        @classmethod
        def from_authorized_user_file(cls, filename, scopes):
            raise ValueError("corrupt token")

    _install_fake_credentials(monkeypatch, BadCredentials)

    status = uploader.get_auth_status()
    assert status["ready"] is False
    assert "인증 상태 확인 실패" in status["reason"]


# ── is_authenticated (line 112) ───────────────────────────────


def test_is_authenticated_true(monkeypatch, tmp_path):
    """is_authenticated returns True when token is valid."""
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "token.json"
    credentials_path.write_text("{}", encoding="utf-8")
    token_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", credentials_path)
    monkeypatch.setattr(uploader, "TOKEN_PATH", token_path)

    class FakeCredentials:
        def __init__(self):
            self.valid = True
            self.refresh_token = "rt"

        @classmethod
        def from_authorized_user_file(cls, filename, scopes):
            return cls()

    _install_fake_credentials(monkeypatch, FakeCredentials)

    assert uploader.is_authenticated() is True


def test_is_authenticated_false(monkeypatch, tmp_path):
    """is_authenticated returns False when no credentials."""
    monkeypatch.setattr(uploader, "CREDENTIALS_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(uploader, "TOKEN_PATH", tmp_path / "missing_token.json")
    assert uploader.is_authenticated() is False


# ── upload_video edge cases (lines 222, 253-263) ─────────────


def test_upload_video_file_not_found(monkeypatch):
    """upload_video raises FileNotFoundError for missing video."""
    import pytest as _pt
    with _pt.raises(FileNotFoundError, match="Video file not found"):
        uploader.upload_video(
            video_path="/nonexistent/video.mp4",
            title="Test",
        )


def test_upload_video_retry_loop_exhausted(monkeypatch, tmp_path):
    """upload_video raises RuntimeError after max retries."""
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video data")

    class FakeMediaFileUpload:
        def __init__(self, filename, mimetype, resumable, chunksize):
            pass

    class FakeRequest:
        def __init__(self):
            self.call_count = 0

        def next_chunk(self):
            self.call_count += 1
            raise Exception("chunk upload failed")

    class FakeVideos:
        def insert(self, **kwargs):
            return FakeRequest()

    class FakeService:
        def videos(self):
            return FakeVideos()

    monkeypatch.setattr(uploader, "_build_youtube_service", lambda: FakeService())
    _install_fake_media_upload(monkeypatch, FakeMediaFileUpload)

    import pytest as _pt
    with _pt.raises(RuntimeError, match="Upload failed after"):
        uploader.upload_video(video_path=str(video_path), title="Test")


def test_upload_video_no_video_id(monkeypatch, tmp_path):
    """upload_video raises RuntimeError when response has no video ID."""
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video data")

    class FakeMediaFileUpload:
        def __init__(self, filename, mimetype, resumable, chunksize):
            pass

    class FakeRequest:
        def next_chunk(self):
            return None, {}  # Empty response, no "id"

    class FakeVideos:
        def insert(self, **kwargs):
            return FakeRequest()

    class FakeService:
        def videos(self):
            return FakeVideos()

    monkeypatch.setattr(uploader, "_build_youtube_service", lambda: FakeService())
    _install_fake_media_upload(monkeypatch, FakeMediaFileUpload)

    import pytest as _pt
    with _pt.raises(RuntimeError, match="no video ID"):
        uploader.upload_video(video_path=str(video_path), title="Test")


# ── get_video_status found (lines 284-287) ────────────────────


def test_get_video_status_found(monkeypatch):
    """get_video_status returns status details when video exists."""
    class FakeVideos:
        def list(self, **kwargs):
            return types.SimpleNamespace(execute=lambda: {
                "items": [{
                    "status": {"uploadStatus": "processed", "privacyStatus": "private"},
                    "processingDetails": {"processingStatus": "succeeded"},
                }]
            })

    class FakeService:
        def videos(self):
            return FakeVideos()

    monkeypatch.setattr(uploader, "_build_youtube_service", lambda: FakeService())
    result = uploader.get_video_status("vid123")
    assert result["video_id"] == "vid123"
    assert result["upload_status"] == "processed"
    assert result["privacy_status"] == "private"
    assert result["processing_status"] == "succeeded"


# ── _cli (lines 340-394) ─────────────────────────────────────


def test_cli_auth_check_valid(monkeypatch, capsys):
    """CLI auth-check prints OK for valid token."""
    monkeypatch.setattr(uploader, "get_auth_status", lambda: {
        "token_valid_or_refreshable": True,
        "ready": True,
        "reason": "ok",
    })
    monkeypatch.setattr(sys, "argv", ["youtube_uploader.py", "auth-check"])
    uploader._cli()
    out = capsys.readouterr().out
    assert "[OK]" in out


def test_cli_auth_check_warn(monkeypatch, capsys):
    """CLI auth-check prints WARN when ready but no valid token."""
    monkeypatch.setattr(uploader, "get_auth_status", lambda: {
        "token_valid_or_refreshable": False,
        "ready": True,
        "reason": "token.json 없음",
    })
    monkeypatch.setattr(sys, "argv", ["youtube_uploader.py", "auth-check"])
    uploader._cli()
    out = capsys.readouterr().out
    assert "[WARN]" in out


def test_cli_auth_check_fail(monkeypatch, capsys):
    """CLI auth-check prints FAIL when not ready."""
    monkeypatch.setattr(uploader, "get_auth_status", lambda: {
        "token_valid_or_refreshable": False,
        "ready": False,
        "reason": "credentials.json 없음",
    })
    monkeypatch.setattr(sys, "argv", ["youtube_uploader.py", "auth-check"])
    uploader._cli()
    out = capsys.readouterr().out
    assert "[FAIL]" in out


def test_cli_upload(monkeypatch, tmp_path, capsys):
    """CLI upload subcommand calls upload_video."""
    video_path = tmp_path / "test.mp4"
    video_path.write_bytes(b"vid")
    monkeypatch.setattr(uploader, "upload_video", lambda **kw: {
        "video_id": "xyz", "youtube_url": "https://youtu.be/xyz", "status": "uploaded"
    })
    monkeypatch.setattr(sys, "argv", [
        "youtube_uploader.py", "upload",
        "--video", str(video_path),
        "--title", "Test Video",
    ])
    uploader._cli()
    out = capsys.readouterr().out
    assert "xyz" in out


def test_cli_upload_pending(monkeypatch, capsys):
    """CLI upload-pending subcommand calls upload_pending_items."""
    monkeypatch.setattr(uploader, "upload_pending_items", lambda **kw: [
        {"item_id": 1, "status": "uploaded"}
    ])
    monkeypatch.setattr(sys, "argv", [
        "youtube_uploader.py", "upload-pending", "--limit", "1",
    ])
    uploader._cli()
    out = capsys.readouterr().out
    assert "업로드 완료" in out


def test_cli_status(monkeypatch, capsys):
    """CLI status subcommand calls get_video_status."""
    monkeypatch.setattr(uploader, "get_video_status", lambda vid: {
        "video_id": vid, "upload_status": "processed"
    })
    monkeypatch.setattr(sys, "argv", [
        "youtube_uploader.py", "status", "--video-id", "abc",
    ])
    uploader._cli()
    out = capsys.readouterr().out
    assert "abc" in out


def test_cli_no_subcommand(monkeypatch, capsys):
    """CLI with no subcommand prints help."""
    monkeypatch.setattr(sys, "argv", ["youtube_uploader.py"])
    uploader._cli()
    # Should not crash; help is printed to stderr or stdout


# ---------------------------------------------------------------------------
# upload_pending_items: sys.path insert (line 305)
# ---------------------------------------------------------------------------

def test_upload_pending_items_empty(monkeypatch, tmp_path):
    """upload_pending_items returns empty when no uploadable items."""
    from unittest.mock import patch as _patch
    _root_str = str(Path(uploader.__file__).resolve().parent.parent)
    # Temporarily remove _root from sys.path to trigger line 305
    original_path = sys.path.copy()
    if _root_str in sys.path:
        sys.path.remove(_root_str)
    try:
        with _patch("execution.content_db.init_db"), \
             _patch("execution.content_db.get_uploadable_items", return_value=[]):
            results = uploader.upload_pending_items(limit=1)
        assert results == []
    finally:
        sys.path[:] = original_path
