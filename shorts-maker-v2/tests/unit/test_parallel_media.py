from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from shorts_maker_v2.config import CostTable
from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.media_step import MediaStep
from shorts_maker_v2.utils.cost_guard import CostGuard


def _make_cost_guard() -> CostGuard:
    return CostGuard(
        max_cost_usd=5.0,
        price_table=CostTable(
            llm_per_job=0.01,
            tts_per_second=0.001,
            veo_per_second=0.03,
            image_per_scene=0.04,
        ),
    )


def _make_scene_plans(n: int = 3) -> list[ScenePlan]:
    return [
        ScenePlan(
            scene_id=i,
            narration_ko=f"테스트 나레이션 {i}",
            visual_prompt_en=f"test prompt {i}",
            target_sec=5.0,
        )
        for i in range(1, n + 1)
    ]


def _make_media_step(config: MagicMock | None = None) -> MediaStep:
    if config is None:
        config = MagicMock()
        config.limits.max_retries = 1
        config.captions.mode = "word"
        config.providers.visual_primary = "openai-image"
        config.providers.visual_stock = ""
        config.providers.image_style_prefix = ""
        config.providers.tts_model = "tts-1"
        config.providers.tts_voice = "alloy"
        config.providers.tts_speed = 1.0
        config.providers.image_model = "dall-e-3"
        config.providers.image_size = "1024x1792"
        config.providers.image_quality = "standard"
        config.providers.visual_styles = ()
        config.providers.tts_voice_pool = ()
        config.providers.tts_voice_strategy = "fixed"
        config.cache.enabled = False
        config.cache.dir = ".cache"
        config.cache.max_size_mb = 500
    openai_client = MagicMock()
    return MediaStep(config=config, openai_client=openai_client)


def test_process_one_scene_returns_asset(tmp_path) -> None:
    """_process_one_scene이 SceneAsset을 반환하는지 확인."""
    step = _make_media_step()
    scene = _make_scene_plans(1)[0]
    audio_dir = tmp_path / "audio"
    image_dir = tmp_path / "images"
    video_dir = tmp_path / "videos"
    audio_dir.mkdir()
    image_dir.mkdir()
    video_dir.mkdir()

    fake_audio = audio_dir / "scene_01.mp3"
    fake_image = image_dir / "scene_01.png"
    fake_audio.write_bytes(b"\x00" * 100)
    fake_image.write_bytes(b"\x00" * 100)

    step.openai_client.generate_tts.return_value = fake_audio
    step.openai_client.generate_image.return_value = fake_image

    cost_guard = _make_cost_guard()

    with patch.object(MediaStep, "_read_audio_duration", return_value=5.0):
        asset, failures = step._process_one_scene(
            scene, audio_dir, image_dir, video_dir, cost_guard,
        )

    assert isinstance(asset, SceneAsset)
    assert asset.scene_id == 1
    assert asset.visual_type == "image"
    assert failures == []


def test_run_sequential_matches_scene_count(tmp_path) -> None:
    """순차 run()이 모든 씬에 대해 에셋을 반환."""
    step = _make_media_step()
    plans = _make_scene_plans(3)

    fake_audio = tmp_path / "fake.mp3"
    fake_image = tmp_path / "fake.png"
    fake_audio.write_bytes(b"\x00" * 100)
    fake_image.write_bytes(b"\x00" * 100)

    cost_guard = _make_cost_guard()

    with (
        patch.object(MediaStep, "_read_audio_duration", return_value=5.0),
        patch.object(MediaStep, "_generate_audio", return_value=fake_audio),
        patch.object(MediaStep, "_generate_best_image", return_value=(str(fake_image), "image", [])),
    ):
        assets, failures = step.run(plans, run_dir=tmp_path, cost_guard=cost_guard)

    assert len(assets) == 3
    assert all(isinstance(a, SceneAsset) for a in assets)
    assert failures == []


def test_run_parallel_produces_ordered_assets(tmp_path) -> None:
    """run_parallel()이 scene_id 순으로 에셋 반환."""
    step = _make_media_step()
    plans = _make_scene_plans(4)

    fake_audio = tmp_path / "fake.mp3"
    fake_image = tmp_path / "fake.png"
    fake_audio.write_bytes(b"\x00" * 100)
    fake_image.write_bytes(b"\x00" * 100)

    cost_guard = _make_cost_guard()

    with (
        patch.object(MediaStep, "_read_audio_duration", return_value=5.0),
        patch.object(MediaStep, "_generate_audio", return_value=fake_audio),
        patch.object(MediaStep, "_generate_best_image", return_value=(str(fake_image), "image", [])),
    ):
        assets, failures = step.run_parallel(plans, run_dir=tmp_path, cost_guard=cost_guard, max_workers=2)

    assert len(assets) == 4
    assert [a.scene_id for a in assets] == [1, 2, 3, 4]
    assert failures == []


def test_run_parallel_handles_scene_failure(tmp_path) -> None:
    """병렬 실행 시 한 씬 실패해도 나머지는 성공."""
    step = _make_media_step()
    plans = _make_scene_plans(3)

    fake_audio = tmp_path / "fake.mp3"
    fake_image = tmp_path / "fake.png"
    fake_audio.write_bytes(b"\x00" * 100)
    fake_image.write_bytes(b"\x00" * 100)

    call_count = {"n": 0}

    def audio_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("TTS failed for scene 2")
        return fake_audio

    cost_guard = _make_cost_guard()

    with (
        patch.object(MediaStep, "_read_audio_duration", return_value=5.0),
        patch.object(MediaStep, "_generate_audio", side_effect=audio_side_effect),
        patch.object(MediaStep, "_generate_best_image", return_value=(str(fake_image), "image", [])),
    ):
        assets, failures = step.run_parallel(plans, run_dir=tmp_path, cost_guard=cost_guard, max_workers=3)

    # 1개 실패, 2개 성공
    assert len(assets) == 2
    assert len(failures) >= 1
    assert any("RuntimeError" in f.get("code", "") for f in failures)


def test_cost_guard_thread_safety() -> None:
    """여러 스레드에서 CostGuard에 동시 접근해도 정확한 합계 유지."""
    guard = _make_cost_guard()
    num_threads = 10
    adds_per_thread = 100
    amount = 0.01

    def add_costs():
        for _ in range(adds_per_thread):
            guard._add("test", amount)

    threads = [threading.Thread(target=add_costs) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    expected = round(num_threads * adds_per_thread * amount, 6)
    assert abs(guard.estimated_cost_usd - expected) < 0.001
    assert len(guard.events) == num_threads * adds_per_thread
