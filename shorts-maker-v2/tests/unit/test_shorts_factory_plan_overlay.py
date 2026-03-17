from __future__ import annotations

from pathlib import Path

from PIL import Image


def test_render_from_plan_keeps_visual_and_generates_text_overlay(tmp_path, monkeypatch) -> None:
    from ShortsFactory.pipeline import ShortsFactory

    visual = tmp_path / "visual.png"
    Image.new("RGB", (1080, 1920), "#101820").save(visual)
    audio = tmp_path / "voice.wav"
    audio.write_bytes(b"wav")

    captured = {}

    def fake_render_scenes(self, scenes, output, **kwargs):  # noqa: ANN001
        captured["scenes"] = scenes
        Path(output).write_bytes(b"mp4")
        return output

    monkeypatch.setattr(
        "ShortsFactory.render.SFRenderStep.render_scenes",
        fake_render_scenes,
    )

    factory = ShortsFactory(channel="ai_tech")
    output = tmp_path / "plan.mp4"
    result = factory.render_from_plan(
        scenes=[
            {
                "scene_id": 1,
                "narration_ko": "GPT API 벤치마크가 다시 공개됐습니다",
                "target_sec": 4.0,
                "structure_role": "hook",
            }
        ],
        assets={1: visual},
        audio_paths={1: audio},
        output=str(output),
    )

    assert Path(result).exists()
    scene = captured["scenes"][0]
    assert scene.image_path == visual
    assert scene.extra["audio_path"] == str(audio)
    assert scene.text_image_path is not None
    assert scene.text_image_path.exists()
    assert "GPT" in scene.keywords
    assert "API" in scene.keywords
