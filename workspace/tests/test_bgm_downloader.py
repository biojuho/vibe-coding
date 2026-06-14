from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

import execution.bgm_downloader as bgm


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        chunks: list[bytes] | None = None,
        *,
        json_error: ValueError | None = None,
        status_error: requests.RequestException | None = None,
    ) -> None:
        self.payload = payload or {}
        self.chunks = chunks or []
        self.json_error = json_error
        self.status_error = status_error

    def raise_for_status(self) -> None:
        if self.status_error is not None:
            raise self.status_error

    def json(self) -> dict[str, Any]:
        if self.json_error is not None:
            raise self.json_error
        return self.payload

    def iter_content(self, chunk_size: int) -> list[bytes]:
        assert chunk_size == 8192
        return self.chunks


def test_pixabay_search_params_limits_page_size() -> None:
    params = bgm._pixabay_search_params("secret", "calm", 30)

    assert params == {
        "key": "secret",
        "q": "calm",
        "per_page": 20,
    }


def test_download_bgm_skips_without_api_key(monkeypatch: Any, tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
    monkeypatch.setattr(bgm.requests, "get", lambda url, **kwargs: calls.append((url, kwargs)))

    assert bgm.download_bgm(output_dir=tmp_path) == []
    assert calls == []


def test_download_bgm_handles_invalid_json(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("PIXABAY_API_KEY", "secret")
    monkeypatch.setattr(
        bgm.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(json_error=ValueError("bad json")),
    )

    assert bgm.download_bgm(output_dir=tmp_path) == []


def test_download_bgm_streams_audio_to_temp_then_renames(monkeypatch: Any, tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setenv("PIXABAY_API_KEY", "secret")

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url == bgm._PIXABAY_MUSIC_API:
            return FakeResponse(
                {
                    "hits": [
                        {
                            "id": 123,
                            "audio": "https://cdn.example/audio.mp3",
                            "tags": "calm",
                        }
                    ]
                }
            )
        assert kwargs["stream"] is True
        assert kwargs["timeout"] == 120
        return FakeResponse(chunks=[b"aa", b"bb"])

    monkeypatch.setattr(bgm.requests, "get", fake_get)

    files = bgm.download_bgm(query="calm", count=30, output_dir=tmp_path)

    assert files == [tmp_path / "bgm_123.mp3"]
    assert (tmp_path / "bgm_123.mp3").read_bytes() == b"aabb"
    assert not (tmp_path / "bgm_123.tmp").exists()
    assert calls[0] == (
        bgm._PIXABAY_MUSIC_API,
        {"params": {"key": "secret", "q": "calm", "per_page": 20}, "timeout": 30},
    )


def test_download_bgm_reuses_existing_file_without_audio_fetch(monkeypatch: Any, tmp_path: Path) -> None:
    existing = tmp_path / "bgm_5.mp3"
    existing.write_bytes(b"already here")
    calls: list[str] = []
    monkeypatch.setenv("PIXABAY_API_KEY", "secret")

    def fake_get(url: str, **_kwargs: Any) -> FakeResponse:
        calls.append(url)
        return FakeResponse({"hits": [{"id": 5, "audio": "https://cdn.example/audio.mp3"}]})

    monkeypatch.setattr(bgm.requests, "get", fake_get)

    assert bgm.download_bgm(output_dir=tmp_path) == [existing]
    assert existing.read_bytes() == b"already here"
    assert calls == [bgm._PIXABAY_MUSIC_API]


def test_download_bgm_removes_temp_file_after_request_failure(monkeypatch: Any, tmp_path: Path) -> None:
    tmp_dest = tmp_path / "bgm_9.tmp"
    tmp_dest.write_bytes(b"partial")
    monkeypatch.setenv("PIXABAY_API_KEY", "secret")

    def fake_get(url: str, **_kwargs: Any) -> FakeResponse:
        if url == bgm._PIXABAY_MUSIC_API:
            return FakeResponse({"hits": [{"id": 9, "audio": "https://cdn.example/audio.mp3"}]})
        raise requests.RequestException("network down")

    monkeypatch.setattr(bgm.requests, "get", fake_get)

    assert bgm.download_bgm(output_dir=tmp_path) == []
    assert not tmp_dest.exists()
