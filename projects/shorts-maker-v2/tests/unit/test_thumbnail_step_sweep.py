import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from shorts_maker_v2.config import CanvaSettings, ThumbnailSettings
from shorts_maker_v2.pipeline.thumbnail_step import ThumbnailStep, _generate_pillow_thumbnail


def _make_step(
    mode: str = "pillow",
    openai_client=None,
    google_client=None,
    canva_enabled: bool = False,
    canva_design_id: str = "",
) -> ThumbnailStep:
    thumb_cfg = MagicMock(spec=ThumbnailSettings)
    thumb_cfg.mode = mode
    thumb_cfg.dalle_prompt_template = ""

    canva_cfg = MagicMock(spec=CanvaSettings)
    canva_cfg.enabled = canva_enabled
    canva_cfg.design_id = canva_design_id
    canva_cfg.token_file = ""

    return ThumbnailStep(
        thumbnail_config=thumb_cfg,
        canva_config=canva_cfg,
        openai_client=openai_client,
        google_client=google_client,
    )


def test_headers_creates_correct_auth_header() -> None:
    from shorts_maker_v2.pipeline.thumbnail_step import _headers

    res = _headers("my-token")
    assert res["Authorization"] == "Bearer my-token"
    assert res["Content-Type"] == "application/json"


def test_get_access_token(tmp_path: Path) -> None:
    import json

    from shorts_maker_v2.pipeline.thumbnail_step import _get_access_token

    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({"access_token": "token123"}), encoding="utf-8")
    assert _get_access_token(token_file) == "token123"


def test_refresh_access_token_missing_env(tmp_path: Path) -> None:
    import json

    from shorts_maker_v2.pipeline.thumbnail_step import _refresh_access_token

    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({"refresh_token": "foo"}), encoding="utf-8")
    with patch.dict("os.environ", {}, clear=True), pytest.raises(RuntimeError, match="CANVA_CLIENT_ID .*"):
        _refresh_access_token(token_file)


def test_refresh_access_token_missing_refresh_token(tmp_path: Path) -> None:
    import json

    from shorts_maker_v2.pipeline.thumbnail_step import _refresh_access_token

    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({"access_token": "foo"}), encoding="utf-8")
    with (
        patch.dict("os.environ", {"CANVA_CLIENT_ID": "cid", "CANVA_CLIENT_SECRET": "csec"}),
        pytest.raises(RuntimeError, match="refresh_token 없음"),
    ):
        _refresh_access_token(token_file)


def test_poll_timeout() -> None:
    from shorts_maker_v2.pipeline.thumbnail_step import _poll

    resp = MagicMock()
    resp.json.return_value = {"job": {"status": "in_progress"}}
    with (
        patch("shorts_maker_v2.pipeline.thumbnail_step.requests.get", return_value=resp),
        patch("time.sleep"),
        pytest.raises(TimeoutError),
    ):
        _poll("http://example.com/api", "token", timeout=0)


def test_poll_success() -> None:
    from shorts_maker_v2.pipeline.thumbnail_step import _poll

    resp = MagicMock()
    resp.json.return_value = {"job": {"status": "success", "id": "job123"}}
    with patch("shorts_maker_v2.pipeline.thumbnail_step.requests.get", return_value=resp):
        res = _poll("url", "token", timeout=10)
        assert res["id"] == "job123"


def test_poll_failed() -> None:
    from shorts_maker_v2.pipeline.thumbnail_step import _poll

    resp = MagicMock()
    resp.json.return_value = {"job": {"status": "failed", "error": "bad"}}
    with (
        patch("shorts_maker_v2.pipeline.thumbnail_step.requests.get", return_value=resp),
        pytest.raises(RuntimeError, match="Canva 작업 실패"),
    ):
        _poll("url", "token", timeout=10)


def test_export_design() -> None:
    from shorts_maker_v2.pipeline.thumbnail_step import _export_design

    post_resp = MagicMock()
    post_resp.json.return_value = {"job": {"id": "job456"}}
    with (
        patch("shorts_maker_v2.pipeline.thumbnail_step.requests.post", return_value=post_resp) as post_mock,
        patch("shorts_maker_v2.pipeline.thumbnail_step._poll", return_value={"urls": ["http://download"]}) as poll_mock,
    ):
        url = _export_design("design123", "token")
        assert url == "http://download"
        post_mock.assert_called_once()
        poll_mock.assert_called_once()


def test_http_download_success(tmp_path: Path) -> None:
    from shorts_maker_v2.pipeline.thumbnail_step import _http_download

    output = tmp_path / "down.png"
    resp = MagicMock()
    resp.content = b"image_data"
    with patch("shorts_maker_v2.pipeline.thumbnail_step.requests.get", return_value=resp):
        res = _http_download("http://fake", output)
        assert res.read_bytes() == b"image_data"


def test_load_font_for_thumb_exception() -> None:
    from shorts_maker_v2.pipeline.thumbnail_step import _load_font_for_thumb

    default_font = MagicMock(name="default_font")
    with (
        patch("shorts_maker_v2.pipeline.thumbnail_step.Path.exists", return_value=True),
        patch("PIL.ImageFont.truetype", side_effect=OSError),
        patch("PIL.ImageFont.load_default", return_value=default_font),
    ):
        font = _load_font_for_thumb(30)
        assert font is default_font


def test_wrap_text_current_append() -> None:
    from PIL import Image, ImageDraw, ImageFont

    from shorts_maker_v2.pipeline.thumbnail_step import _wrap_text

    img = Image.new("RGB", (100, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # "Short" works, but the very long word requires `current` to be flushed
    res = _wrap_text("A" + " B" * 50, font, draw, max_width=40)
    assert len(res) > 2


def test_pillow_bg_exception(tmp_path: Path) -> None:
    output = tmp_path / "thumb_ex.png"
    with patch("PIL.Image.open", side_effect=OSError):
        res = _generate_pillow_thumbnail("Fail bg", output, bg_image_path="dummy.png")
        assert res.exists()


def test_run_moviepy_exception(tmp_path: Path) -> None:
    mock_asset = MagicMock()
    video_path = tmp_path / "vid.mp4"
    video_path.touch()
    mock_asset.visual_path = str(video_path)

    class FakeVideoFileClip:
        def __init__(self, path):
            raise OSError("bad video")

        def __enter__(self):
            return self

        def __exit__(self, a, b, c):
            pass

    step = _make_step(mode="pillow")
    with patch.dict("sys.modules", {"moviepy": types.SimpleNamespace(VideoFileClip=FakeVideoFileClip)}):
        res = step.run("Video crash", tmp_path, scene_assets=[mock_asset])
    assert res is not None


def test_run_gemini_client_fallback_to_dalle(tmp_path: Path) -> None:
    mock_google = MagicMock()
    mock_google.generate_image_imagen3 = None
    mock_google.generate_image = MagicMock()

    def fake_gen(*, prompt, output_path):
        from PIL import Image

        Image.new("RGB", (100, 100), color=(0, 0, 0)).save(str(output_path), "PNG")

    mock_google.generate_image.side_effect = fake_gen

    step = _make_step(mode="gemini", google_client=mock_google)
    res = step.run("Gemini fallback", tmp_path, topic="space")
    assert res is not None
    mock_google.generate_image.assert_called_once()


def test_run_canva_other_http_error(tmp_path: Path) -> None:
    step = _make_step(mode="canva", canva_enabled=True, canva_design_id="d1")
    step.token_file = tmp_path / "token.json"
    import json

    step.token_file.write_text(json.dumps({"access_token": "tk"}), encoding="utf-8")

    http_error = requests.HTTPError("bad req")
    http_error.response = MagicMock(status_code=400)

    with patch("shorts_maker_v2.pipeline.thumbnail_step._export_design", side_effect=http_error):
        res = step.run("title", tmp_path)
        assert res is None


def test_pillow_long_title(tmp_path: Path, capfd) -> None:
    step = _make_step(mode="pillow")
    res = step.run("이 제목은 15자를 무조건 넘어가는 아주아주 긴 테스트 제목입니다", tmp_path)
    assert res is not None
    out, _ = capfd.readouterr()
    assert "15자 이하 권장" in out
