from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from openai import BadRequestError

from shorts_maker_v2.config import CostTable
from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.media_step import MediaStep
from shorts_maker_v2.utils.cost_guard import CostGuard


def _make_config() -> SimpleNamespace:
    return SimpleNamespace(
        providers=SimpleNamespace(
            tts_voice_pool=(),
            tts_voice_strategy="fixed",
            tts_voice="alloy",
            visual_styles=(),
            image_style_prefix="cinematic",
            tts_voice_roles={},
            tts="openai",
            tts_model="tts-1",
            tts_speed=1.0,
            llm_model="gpt-4o-mini",
            image_model="gpt-image-1",
            image_size="1024x1792",
            image_quality="standard",
            veo_model="veo-3",
            visual_primary="openai-image",
            visual_fallback="openai-image",
            visual_stock="pexels",
        ),
        cache=SimpleNamespace(dir=".cache", enabled=False, max_size_mb=100),
        audio=SimpleNamespace(sync_with_whisper=False),
        project=SimpleNamespace(language="ko-KR"),
        video=SimpleNamespace(
            scene_video_duration_sec=5,
            aspect_ratio="9:16",
            resolution=(1080, 1920),
            stock_mix_ratio=0.0,
        ),
        limits=SimpleNamespace(max_retries=2, request_timeout_sec=30),
    )


def _make_cost_guard(max_cost_usd: float = 5.0) -> CostGuard:
    return CostGuard(
        max_cost_usd=max_cost_usd,
        price_table=CostTable(
            llm_per_job=0.01,
            tts_per_second=0.001,
            veo_per_second=0.03,
            image_per_scene=0.04,
            stock_per_scene=0.01,
        ),
    )


def _make_step(
    *,
    config: SimpleNamespace | None = None,
    openai_client: MagicMock | None = None,
    google_client: MagicMock | None = None,
    pexels_client: MagicMock | None = None,
    llm_router: MagicMock | None = None,
    job_index: int = 0,
) -> MediaStep:
    if config is None:
        config = _make_config()
    if openai_client is None:
        openai_client = MagicMock()
    return MediaStep(
        config=config,
        openai_client=openai_client,
        google_client=google_client,
        pexels_client=pexels_client,
        llm_router=llm_router,
        job_index=job_index,
    )


def _scene(scene_id: int = 1, *, role: str = "body") -> ScenePlan:
    return ScenePlan(
        scene_id=scene_id,
        narration_ko=f"scene {scene_id}",
        visual_prompt_en=f"visual {scene_id}",
        target_sec=5.0,
        structure_role=role,
    )


def _run_retry(fn, **kwargs):  # noqa: ANN001,ARG001
    return fn()


def _bad_request_error(message: str) -> BadRequestError:
    request = httpx.Request("POST", "https://api.openai.com/v1/images")
    response = httpx.Response(400, request=request)
    return BadRequestError(message, response=response, body=None)


def test_init_rotates_voice_and_style() -> None:
    config = _make_config()
    config.providers.tts_voice_pool = ("voice-a", "voice-b")
    config.providers.tts_voice_strategy = "rotate"
    config.providers.visual_styles = ("style-a", "style-b")

    step = _make_step(config=config, job_index=3)

    assert step._tts_voice == "voice-b"
    assert step._visual_style == "style-b"


def test_init_random_voice_uses_choice() -> None:
    config = _make_config()
    config.providers.tts_voice_pool = ("voice-a", "voice-b")
    config.providers.tts_voice_strategy = "random"

    with patch("shorts_maker_v2.pipeline.media_step.random.choice", return_value="voice-b") as chooser:
        step = _make_step(config=config)

    assert step._tts_voice == "voice-b"
    chooser.assert_called_once_with(("voice-a", "voice-b"))


def test_log_and_read_audio_duration_helpers(tmp_path: Path) -> None:
    logger = MagicMock()
    MediaStep._log(logger, "info", "event-name", scene_id=1)
    logger.info.assert_called_once_with("event-name", scene_id=1)

    fake_audio = tmp_path / "voice.mp3"
    fake_audio.write_bytes(b"mp3")
    mp3_obj = MagicMock()
    mp3_obj.info.length = 4.25

    with patch("shorts_maker_v2.pipeline.media_step.MP3", return_value=mp3_obj):
        assert MediaStep._read_audio_duration(fake_audio, 2.0) == 4.25

    with patch("shorts_maker_v2.pipeline.media_step.MP3", side_effect=RuntimeError("bad mp3")):
        assert MediaStep._read_audio_duration(fake_audio, 2.0) == 2.0


def test_generate_audio_edge_tts_uses_role_voice(tmp_path: Path) -> None:
    config = _make_config()
    config.providers.tts = "edge-tts"
    config.providers.tts_voice_roles = {"hook": "hook-voice"}
    step = _make_step(config=config)
    output_path = tmp_path / "scene_01.mp3"

    with patch("shorts_maker_v2.pipeline.media_step.EdgeTTSClient") as edge_cls:
        edge_cls.return_value.generate_tts.return_value = output_path
        result = step._generate_audio("hello", output_path, role="hook")

    assert result == output_path
    edge_cls.return_value.generate_tts.assert_called_once_with(
        model="tts-1",
        voice="hook-voice",
        speed=1.0,
        text="hello",
        output_path=output_path,
        words_json_path=tmp_path / "scene_01_words.json",
        role="hook",
        language="ko-KR",
    )


def test_generate_audio_openai_with_whisper_sync_writes_words_json(tmp_path: Path) -> None:
    config = _make_config()
    config.audio.sync_with_whisper = True
    openai_client = MagicMock()
    output_path = tmp_path / "scene_02.mp3"
    output_path.write_bytes(b"audio")
    openai_client.generate_tts.return_value = output_path
    openai_client.transcribe_audio.return_value = [{"word": "hello", "start": 0.0, "end": 0.5}]
    step = _make_step(config=config, openai_client=openai_client)

    result = step._generate_audio("hello", output_path, role="body")

    assert result == output_path
    words_json_path = tmp_path / "scene_02_words.json"
    assert words_json_path.exists()
    assert "hello" in words_json_path.read_text(encoding="utf-8")


def test_generate_video_and_stock_video_require_clients(tmp_path: Path) -> None:
    step = _make_step(google_client=None, pexels_client=None)

    with pytest.raises(RuntimeError, match="Google client"):
        step._generate_video("visual", 5.0, tmp_path / "clip.mp4")

    with pytest.raises(RuntimeError, match="Pexels client"):
        step._generate_stock_video("visual", tmp_path / "stock.mp4")


def test_generate_image_pollinations_existing_and_small_response(tmp_path: Path) -> None:
    step = _make_step()
    output_path = tmp_path / "pollinations.png"
    output_path.write_bytes(b"already-here")

    assert step._generate_image_pollinations("visual", output_path) == output_path

    output_path.unlink()
    response = MagicMock()
    response.content = b"tiny"
    response.raise_for_status.return_value = None

    with (
        patch("requests.get", return_value=response),
        pytest.raises(ValueError, match="suspiciously small image"),
    ):
        step._generate_image_pollinations("visual", output_path)


def test_sanitize_visual_prompt_prefers_router_and_falls_back_to_openai() -> None:
    router = MagicMock()
    router.generate_json.return_value = {"prompt": "safe router prompt"}
    step = _make_step(llm_router=router)

    assert step._sanitize_visual_prompt("unsafe prompt") == "safe router prompt"

    router.generate_json.side_effect = RuntimeError("router down")
    step.openai_client.generate_json.return_value = {"prompt": "safe openai prompt"}

    assert step._sanitize_visual_prompt("unsafe prompt") == "safe openai prompt"


def test_build_visual_prompt_and_extract_palette(tmp_path: Path) -> None:
    step = _make_step()
    scene = _scene(role="solution")
    prompt = step._build_visual_prompt(scene, "#112233, #445566")

    assert "[SOLUTION scene" in prompt
    assert "Color palette consistency" in prompt

    image_path = tmp_path / "palette.png"
    from PIL import Image

    Image.new("RGB", (20, 20), color=(17, 34, 51)).save(image_path)
    palette = MediaStep._extract_palette(image_path)
    assert palette.startswith("#")


def test_generate_placeholder_image_creates_file(tmp_path: Path) -> None:
    output_path = tmp_path / "placeholder.png"

    result = MediaStep._generate_placeholder_image(output_path, 40, 80)

    assert result == output_path
    assert output_path.exists()


def test_generate_best_image_returns_cached_file(tmp_path: Path) -> None:
    step = _make_step()
    cached = tmp_path / "cached.png"
    cached.write_bytes(b"cached")
    step._cache = MagicMock()
    step._cache.get.return_value = cached

    path_str, visual_type, failures = step._generate_best_image(
        "visual",
        tmp_path / "target.png",
        5.0,
        _make_cost_guard(),
        tmp_path,
        _scene(),
        MagicMock(),
    )

    assert path_str == str(cached)
    assert visual_type == "image"
    assert failures == []


def test_generate_best_image_prefers_video_when_allowed(tmp_path: Path) -> None:
    config = _make_config()
    config.providers.visual_primary = "google-veo"
    google_client = MagicMock()
    step = _make_step(config=config, google_client=google_client)
    step._cache = MagicMock(get=MagicMock(return_value=None), put=MagicMock())
    video_path = tmp_path / "scene_01.mp4"
    google_client.generate_video.return_value = video_path

    with patch("shorts_maker_v2.pipeline.media_step.retry_with_backoff", side_effect=_run_retry):
        path_str, visual_type, failures = step._generate_best_image(
            "visual",
            tmp_path / "scene_01.png",
            5.0,
            _make_cost_guard(),
            tmp_path,
            _scene(),
            MagicMock(),
        )

    assert path_str == str(video_path)
    assert visual_type == "video"
    assert failures == []


def test_generate_best_image_downgrades_video_then_uses_stock_mix(tmp_path: Path) -> None:
    config = _make_config()
    config.providers.visual_primary = "google-veo"
    config.video.stock_mix_ratio = 1.0
    pexels_client = MagicMock()
    step = _make_step(config=config, google_client=MagicMock(), pexels_client=pexels_client)
    step._cache = MagicMock(get=MagicMock(return_value=None), put=MagicMock())
    stock_path = tmp_path / "scene_01_stock.mp4"
    logger = MagicMock()

    with (
        patch("shorts_maker_v2.pipeline.media_step.random.random", return_value=0.0),
        patch("shorts_maker_v2.pipeline.media_step.retry_with_backoff", side_effect=_run_retry),
        patch.object(step, "_generate_stock_video", return_value=stock_path),
    ):
        path_str, visual_type, failures = step._generate_best_image(
            "visual",
            tmp_path / "scene_01.png",
            5.0,
            _make_cost_guard(max_cost_usd=0.01),
            tmp_path,
            _scene(),
            logger,
        )

    assert path_str == str(stock_path)
    assert visual_type == "video"
    assert failures == []
    logger.warning.assert_called()


def test_generate_best_image_imagen_falls_back_to_gemini(tmp_path: Path) -> None:
    config = _make_config()
    config.providers.visual_primary = "google-imagen"
    google_client = MagicMock()
    google_client.generate_image_imagen3.side_effect = RuntimeError("imagen down")
    gemini_path = tmp_path / "gemini.png"
    google_client.generate_image.return_value = gemini_path
    step = _make_step(config=config, google_client=google_client)
    step._cache = MagicMock(get=MagicMock(return_value=None), put=MagicMock())

    with patch("shorts_maker_v2.pipeline.media_step.retry_with_backoff", side_effect=_run_retry):
        path_str, visual_type, failures = step._generate_best_image(
            "visual",
            tmp_path / "target.png",
            5.0,
            _make_cost_guard(),
            tmp_path,
            _scene(),
            MagicMock(),
        )

    assert path_str == str(gemini_path)
    assert visual_type == "image"
    assert failures[0]["step"] == "image_imagen3"
    step._cache.put.assert_called_once()


def test_generate_best_image_handles_content_policy_and_sanitized_retry(tmp_path: Path) -> None:
    step = _make_step(google_client=None)
    step._cache = MagicMock(get=MagicMock(return_value=None), put=MagicMock())
    safe_path = tmp_path / "safe.png"
    step._generate_image = MagicMock(
        side_effect=[
            _bad_request_error("content_policy_violation: blocked"),
            safe_path,
        ]
    )
    logger = MagicMock()

    with (
        patch("shorts_maker_v2.pipeline.media_step.retry_with_backoff", side_effect=_run_retry),
        patch.object(step, "_generate_image_pollinations", side_effect=RuntimeError("pollinations down")),
        patch.object(step, "_sanitize_visual_prompt", return_value="safe visual"),
    ):
        path_str, visual_type, failures = step._generate_best_image(
            "unsafe visual",
            tmp_path / "target.png",
            5.0,
            _make_cost_guard(),
            tmp_path,
            _scene(role="hook"),
            logger,
            use_paid_image=True,
        )

    assert path_str == str(safe_path)
    assert visual_type == "image"
    assert any(f["step"] == "image_policy" for f in failures)
    assert step._cache.put.called


def test_generate_best_image_body_scene_skips_paid_and_uses_placeholder_after_stock_fail(tmp_path: Path) -> None:
    pexels_client = MagicMock()
    step = _make_step(google_client=None, pexels_client=pexels_client)
    step._cache = MagicMock(get=MagicMock(return_value=None), put=MagicMock())
    placeholder = tmp_path / "placeholder.png"

    with (
        patch("shorts_maker_v2.pipeline.media_step.retry_with_backoff", side_effect=_run_retry),
        patch.object(step, "_generate_image_pollinations", side_effect=RuntimeError("pollinations down")),
        patch.object(step, "_generate_stock_video", side_effect=RuntimeError("stock down")),
        patch.object(step, "_generate_placeholder_image", return_value=placeholder) as placeholder_image,
    ):
        path_str, visual_type, failures = step._generate_best_image(
            "visual",
            tmp_path / "target.png",
            5.0,
            _make_cost_guard(),
            tmp_path,
            _scene(role="body"),
            MagicMock(),
            use_paid_image=False,
        )

    assert path_str == str(placeholder)
    assert visual_type == "image"
    assert any(f["step"] == "image_pollinations" for f in failures)
    assert any(f["step"] == "stock_policy_fallback" for f in failures)
    placeholder_image.assert_called_once()


def test_process_one_scene_recovers_checkpoint_stock_video(tmp_path: Path) -> None:
    step = _make_step()
    audio_dir = tmp_path / "audio"
    image_dir = tmp_path / "images"
    video_dir = tmp_path / "videos"
    audio_dir.mkdir()
    image_dir.mkdir()
    video_dir.mkdir()

    (audio_dir / "scene_01.mp3").write_bytes(b"audio")
    (video_dir / "scene_01_stock.mp4").write_bytes(b"stock")

    with patch.object(MediaStep, "_read_audio_duration", return_value=4.5):
        asset, failures = step._process_one_scene(
            _scene(),
            audio_dir,
            image_dir,
            video_dir,
            _make_cost_guard(),
            logger=MagicMock(),
        )

    assert asset.visual_type == "video"
    assert asset.duration_sec == 4.5
    assert failures == []


def test_process_one_scene_existing_visual_skips_regeneration(tmp_path: Path) -> None:
    step = _make_step()
    audio_dir = tmp_path / "audio"
    image_dir = tmp_path / "images"
    video_dir = tmp_path / "videos"
    audio_dir.mkdir()
    image_dir.mkdir()
    video_dir.mkdir()
    existing_image = image_dir / "scene_01.png"
    existing_image.write_bytes(b"image")
    generated_audio = audio_dir / "scene_01.mp3"
    generated_audio.write_bytes(b"audio")

    with (
        patch("shorts_maker_v2.pipeline.media_step.retry_with_backoff", side_effect=_run_retry),
        patch.object(step, "_generate_audio", return_value=generated_audio),
        patch.object(step, "_generate_best_image") as best_image,
        patch.object(MediaStep, "_read_audio_duration", return_value=5.0),
    ):
        asset, failures = step._process_one_scene(
            _scene(),
            audio_dir,
            image_dir,
            video_dir,
            _make_cost_guard(),
            logger=MagicMock(),
        )

    assert asset.visual_path == str(existing_image)
    assert asset.visual_type == "image"
    assert failures == []
    best_image.assert_not_called()


def test_process_one_scene_audio_failure_logs_and_raises(tmp_path: Path) -> None:
    step = _make_step()
    audio_dir = tmp_path / "audio"
    image_dir = tmp_path / "images"
    video_dir = tmp_path / "videos"
    audio_dir.mkdir()
    image_dir.mkdir()
    video_dir.mkdir()
    logger = MagicMock()

    with (
        patch("shorts_maker_v2.pipeline.media_step.retry_with_backoff", side_effect=_run_retry),
        patch.object(step, "_generate_audio", side_effect=RuntimeError("tts failed")),
        patch.object(step, "_generate_best_image", return_value=(str(tmp_path / "img.png"), "image", [])),
        pytest.raises(RuntimeError, match="tts failed"),
    ):
        step._process_one_scene(
            _scene(),
            audio_dir,
            image_dir,
            video_dir,
            _make_cost_guard(),
            logger=logger,
        )

    logger.error.assert_called_once()


def test_run_extracts_palette_from_hook_image(tmp_path: Path) -> None:
    step = _make_step()
    logger = MagicMock()
    hook_asset = SceneAsset(1, "a.mp3", "image", str(tmp_path / "hook.png"), 5.0)
    body_asset = SceneAsset(2, "b.mp3", "image", str(tmp_path / "body.png"), 5.0)
    captured_hints: list[str] = []

    def _process(scene, *args, **kwargs):  # noqa: ANN001
        captured_hints.append(kwargs.get("color_hint", ""))
        return (hook_asset, []) if scene.scene_id == 1 else (body_asset, [])

    with (
        patch.object(step, "_process_one_scene", side_effect=_process),
        patch.object(step, "_extract_palette", return_value="#112233, #445566"),
    ):
        assets, failures = step.run(
            [_scene(1, role="hook"), _scene(2, role="body")],
            tmp_path,
            _make_cost_guard(),
            logger,
        )

    assert [asset.scene_id for asset in assets] == [1, 2]
    assert failures == []
    assert captured_hints == ["", "#112233, #445566"]
    logger.info.assert_called_with("palette_extracted", palette="#112233, #445566")


def test_run_parallel_logs_failure_and_uses_hook_palette(tmp_path: Path) -> None:
    step = _make_step()
    logger = MagicMock()
    hook_asset = SceneAsset(1, "a.mp3", "image", str(tmp_path / "hook.png"), 5.0)
    captured_hints: list[str] = []

    def _process(scene, *args, **kwargs):  # noqa: ANN001
        color_hint = kwargs.get("color_hint", "")
        if not color_hint and len(args) >= 6:
            color_hint = args[5]
        captured_hints.append(color_hint)
        if scene.scene_id == 1:
            return hook_asset, []
        raise RuntimeError("scene failed")

    with (
        patch.object(step, "_process_one_scene", side_effect=_process),
        patch.object(step, "_extract_palette", return_value="#abcdef"),
    ):
        assets, failures = step.run_parallel(
            [_scene(1, role="hook"), _scene(2, role="body")],
            tmp_path,
            _make_cost_guard(),
            logger,
            max_workers=2,
        )

    assert [asset.scene_id for asset in assets] == [1]
    assert any(f["step"] == "scene_2" for f in failures)
    assert captured_hints == ["", "#abcdef"]
    logger.error.assert_called_once()


def test_regenerate_scene_removes_visual_files_and_stock_variant(tmp_path: Path) -> None:
    step = _make_step()
    run_dir = tmp_path / "run"
    audio_dir = run_dir / "media" / "audio"
    image_dir = run_dir / "media" / "images"
    video_dir = run_dir / "media" / "videos"
    audio_dir.mkdir(parents=True)
    image_dir.mkdir(parents=True)
    video_dir.mkdir(parents=True)

    (audio_dir / "scene_01.mp3").write_bytes(b"audio")
    (image_dir / "scene_01.png").write_bytes(b"image")
    (video_dir / "scene_01.mp4").write_bytes(b"video")
    (video_dir / "scene_01_stock.mp4").write_bytes(b"stock")

    regenerated = SceneAsset(1, "a.mp3", "image", "v.png", 5.0)
    with patch.object(step, "_process_one_scene", return_value=(regenerated, [])) as process:
        asset, failures = step.regenerate_scene(
            _scene(),
            run_dir,
            _make_cost_guard(),
            logger=MagicMock(),
            component="visual",
        )

    assert asset == regenerated
    assert failures == []
    assert (audio_dir / "scene_01.mp3").exists()
    assert not (image_dir / "scene_01.png").exists()
    assert not (video_dir / "scene_01.mp4").exists()
    assert not (video_dir / "scene_01_stock.mp4").exists()
    process.assert_called_once()
