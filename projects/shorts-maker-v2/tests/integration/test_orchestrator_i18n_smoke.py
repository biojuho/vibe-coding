from __future__ import annotations

import json
import wave
from pathlib import Path
from unittest.mock import patch

import yaml
from PIL import Image

from shorts_maker_v2.config import load_config
from shorts_maker_v2.models import GateVerdict, QCReport, SceneAsset
from shorts_maker_v2.pipeline.orchestrator import PipelineOrchestrator
from shorts_maker_v2.pipeline.render_step import RenderStep
from shorts_maker_v2.pipeline.script_step import ScriptStep


class FakeProductionPlan:
    concept = "English locale smoke"
    target_persona = "Busy tech viewers"
    core_message = "Tiny efficiency gains change product design."
    visual_keywords = ["chip", "battery", "phone"]
    forbidden_elements = ["medical imagery"]

    def to_dict(self) -> dict[str, object]:
        return {
            "concept": self.concept,
            "target_persona": self.target_persona,
            "core_message": self.core_message,
            "visual_keywords": self.visual_keywords,
            "forbidden_elements": self.forbidden_elements,
        }


class FakeLLMRouter:
    def __init__(self, responses: list[dict[str, object]]):
        self._responses = list(responses)
        self.calls = 0

    def generate_json(
        self,
        *,
        system_prompt: str = "",
        user_prompt: str = "",
        temperature: float = 0.7,
        thinking_level: str | None = None,
    ):  # noqa: ARG002,E501
        self.calls += 1
        if not self._responses:
            raise AssertionError("No more fake LLM responses available.")
        return self._responses.pop(0)


class StubMediaStep:
    def run(self, scene_plans, run_dir: Path, cost_guard, logger=None):  # noqa: ARG002
        run_dir.mkdir(parents=True, exist_ok=True)
        assets: list[SceneAsset] = []
        palette = [(52, 152, 219), (46, 204, 113), (241, 196, 15)]

        for index, plan in enumerate(scene_plans):
            audio_path = run_dir / f"scene_{plan.scene_id}.wav"
            visual_path = run_dir / f"scene_{plan.scene_id}.png"
            _write_silent_wav(audio_path, duration_sec=plan.target_sec)
            _write_test_image(visual_path, color=palette[index % len(palette)])
            cost_guard.add_tts_cost(plan.target_sec)
            assets.append(
                SceneAsset(
                    scene_id=plan.scene_id,
                    audio_path=str(audio_path),
                    visual_type="image",
                    visual_path=str(visual_path),
                    duration_sec=plan.target_sec,
                )
            )

        return assets, []


def _write_silent_wav(path: Path, *, duration_sec: float, sample_rate: int = 16_000) -> Path:
    frame_count = max(1, int(duration_sec * sample_rate))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frame_count)
    return path


def _write_test_image(path: Path, *, color: tuple[int, int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (540, 960), color=color).save(path)
    return path


def _write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "project": {
                    "language": "en-US",
                    "default_scene_count": 3,
                    "script_review_enabled": False,
                    # No LLM API keys in test env → structure step would fall back
                    # and the new fallback-degraded signal would surface as
                    # status="degraded". This smoke test asserts a happy en-US
                    # render, so skip structure entirely.
                    "structure_validation": "off",
                },
                "video": {
                    "target_duration_sec": [8, 14],
                    "resolution": [540, 960],
                    "fps": 30,
                    "scene_video_duration_sec": 4,
                    "aspect_ratio": "9:16",
                    "transition_style": "crossfade",
                },
                "providers": {
                    "llm": "openai",
                    "tts": "edge-tts",
                    "visual_primary": "openai-image",
                    "visual_fallback": "openai-image",
                    "tts_speed": 1.05,
                },
                "limits": {"max_cost_usd": 2.0, "max_retries": 1, "request_timeout_sec": 30},
                "costs": {
                    "llm_per_job": 0.25,
                    "tts_per_second": 0.0008,
                    "veo_per_second": 0.03,
                    "image_per_scene": 0.04,
                },
                "paths": {"output_dir": "output", "logs_dir": "logs", "runs_dir": "runs"},
                "captions": {
                    "mode": "static",
                    "font_size": 40,
                    "margin_x": 36,
                    "bottom_offset": 120,
                    "hook_animation": "none",
                },
                "audio": {
                    "bgm_dir": "missing-bgm",
                    "sfx_enabled": False,
                    "bgm_provider": "local",
                },
                "canva": {"enabled": False, "design_id": "", "token_file": ""},
                "intro_outro": {},
                "thumbnail": {"mode": "none"},
                "cache": {"enabled": False},
                "research": {"enabled": False},
                "rendering": {"engine": "native"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return config_path


def test_orchestrator_en_us_smoke_reaches_render_and_srt_export(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path))
    llm = FakeLLMRouter(
        [
            {
                "title": "Tiny chips, big savings",
                "scenes": [
                    {
                        "narration": "Tiny chips win.",
                        "visual_prompt": "Close-up of a compact processor glowing in cool studio light",
                        "structure_role": "hook",
                    },
                    {
                        "narration": "That slashed power use for phones.",
                        "visual_prompt": "Clean product shot of a smartphone beside a battery meter",
                        "structure_role": "body",
                    },
                    {
                        "narration": "Check your model size tonight.",
                        "visual_prompt": "Minimal desk scene with a laptop dashboard and warm rim light",
                        "structure_role": "cta",
                    },
                ],
            }
        ]
    )
    script_step = ScriptStep(config=config, llm_router=llm, channel_key="ai_tech")
    render_step = RenderStep(config=config)
    orchestrator = PipelineOrchestrator(
        config=config,
        base_dir=tmp_path,
        script_step=script_step,
        media_step=StubMediaStep(),
        render_step=render_step,
    )

    def _fake_write(handle, output_path: Path, **kwargs):  # noqa: ANN001,ARG001
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-mp4")

    with (
        patch("shorts_maker_v2.pipeline.orchestrator.PlanningStep.run", return_value=FakeProductionPlan()),
        patch(
            "shorts_maker_v2.pipeline.orchestrator.QCStep.gate4_final",
            return_value=QCReport(checks={"smoke_pass": True}, verdict=GateVerdict.PASS.value, issues=[]),
        ),
        patch("shorts_maker_v2.pipeline.render_step.postprocess_tts_audio", return_value=None),
        patch.object(render_step, "_apply_channel_image_motion", side_effect=lambda base, **kwargs: (base, "smoke")),  # noqa: ARG005,E501
        patch.object(render_step, "_apply_transitions", side_effect=lambda clips, *args, **kwargs: clips),  # noqa: ARG005,E501
        patch.object(render_step._output_renderer, "write", side_effect=_fake_write),
        patch("shorts_maker_v2.utils.hwaccel.detect_hw_encoder", return_value=("libx264", [])),
        patch(
            "shorts_maker_v2.utils.hwaccel.detect_gpu_info",
            return_value={"gpu_name": "smoke-gpu", "encoder": "libx264", "decoder_support": "n/a"},
        ),
    ):
        manifest = orchestrator.run(topic="edge AI battery life", output_filename="en-us-smoke.mp4")

    assert manifest.status == "success"
    assert manifest.title == "Tiny chips, big savings"
    assert manifest.scene_count == 3
    assert llm.calls == 1
    assert manifest.output_path.endswith("en-us-smoke.mp4")
    assert manifest.thumbnail_path == ""
    assert manifest.production_plan["concept"] == "English locale smoke"

    output_path = Path(manifest.output_path)
    assert output_path.exists()
    assert output_path.read_bytes() == b"fake-mp4"

    srt_path = Path(manifest.srt_path)
    assert srt_path.exists()
    srt_text = srt_path.read_text(encoding="utf-8")
    assert "Tiny chips win." in srt_text
    assert "That slashed power use for phones." in srt_text
    assert "Check your model size tonight." in srt_text

    manifest_path = tmp_path / "output" / f"{manifest.job_id}_manifest.json"
    assert manifest_path.exists()
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded["status"] == "success"
    assert loaded["title"] == "Tiny chips, big savings"
    assert loaded["srt_path"].endswith(".srt")
