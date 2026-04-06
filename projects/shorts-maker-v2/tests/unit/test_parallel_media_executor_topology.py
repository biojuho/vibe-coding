from __future__ import annotations

from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


def _make_cost_guard() -> CostGuard:
    return CostGuard(
        max_cost_usd=5.0,
        price_table=CostTable(
            llm_per_job=0.01,
            tts_per_second=0.001,
            veo_per_second=0.03,
            image_per_scene=0.04,
            stock_per_scene=0.01,
        ),
    )


def test_run_parallel_disables_nested_provider_parallelism(tmp_path) -> None:
    step = MediaStep(config=_make_config(), openai_client=MagicMock())
    plans = [
        ScenePlan(scene_id=1, narration_ko="scene one", visual_prompt_en="prompt one", target_sec=5.0),
        ScenePlan(scene_id=2, narration_ko="scene two", visual_prompt_en="prompt two", target_sec=5.0),
    ]
    fake_asset = SceneAsset(
        scene_id=1,
        audio_path=str(tmp_path / "audio.mp3"),
        visual_type="image",
        visual_path=str(tmp_path / "image.png"),
        duration_sec=5.0,
    )

    def immediate_retry_submit(_executor, fn, **_kwargs):
        future = Future()
        future.set_result(fn())
        return future

    with (
        patch(
            "shorts_maker_v2.pipeline.media_step.submit_retry_with_backoff", side_effect=immediate_retry_submit
        ) as submit,
        patch.object(step, "_process_one_scene", return_value=(fake_asset, [])) as process,
    ):
        step.run_parallel(plans, run_dir=tmp_path, cost_guard=_make_cost_guard(), max_workers=2)

    assert process.call_count == 2
    assert all(call.args[-2] is False for call in process.call_args_list)
    assert all(call.args[-1] == 1 for call in process.call_args_list)
    assert submit.call_count == 2
    assert all(call.kwargs["max_attempts"] == step.config.limits.max_retries for call in submit.call_args_list)
