from __future__ import annotations

from types import SimpleNamespace

from shorts_maker_v2.pipeline.script_step import ScriptStep


class FakeOpenAIClient:
    """LLMRouter.generate_json / OpenAIClient.generate_json 양쪽 시그니처 호환."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_json(self, *, model: str = "", system_prompt: str = "", user_prompt: str = "", temperature: float = 0.7, thinking_level: str | None = None):
        del model, system_prompt, user_prompt, temperature, thinking_level
        self.calls += 1
        if not self.responses:
            raise AssertionError("No more fake responses available.")
        return self.responses.pop(0)


def make_config(*, duration_range=(20, 30), tts_speed=1.05):
    return SimpleNamespace(
        providers=SimpleNamespace(
            llm="openai",
            llm_model="gpt-4o-mini",
            tts_speed=tts_speed,
            thinking_level="low",
            thinking_level_review="high",
            embedding_model="gemini-embedding-2-preview",
        ),
        project=SimpleNamespace(
            default_scene_count=2,
            language="ko-KR",
            script_review_enabled=False,
            script_review_min_score=6,
            structure_presets={},
        ),
        video=SimpleNamespace(
            target_duration_sec=duration_range,
        ),
    )


def test_parse_script_payload_handles_code_fence() -> None:
    raw = """
    ```json
    {
      "title": "Test",
      "scenes": [
        {
          "narration_ko": "\\uc548\\ub155\\ud558\\uc138\\uc694 \\uc774\\uac83\\uc740 \\uccab \\uc7a5\\uba74\\uc785\\ub2c8\\ub2e4. \\uc870\\uae08 \\ub354 \\uc790\\uc138\\ud788 \\uc124\\uba85\\ud569\\ub2c8\\ub2e4.",
          "visual_prompt_en": "Cinematic close-up of a speaker"
        },
        {
          "narration_ko": "\\ub450 \\ubc88\\uc9f8 \\uc7a5\\uba74\\uc785\\ub2c8\\ub2e4. \\uc18d\\ub3c4\\uac10 \\uc788\\uac8c \\uc774\\uc5b4\\uac11\\ub2c8\\ub2e4.",
          "visual_prompt_en": "Tracking shot over neon city"
        }
      ]
    }
    ```
    """
    title, scenes = ScriptStep.parse_script_payload(
        raw,
        scene_count=2,
        target_duration_sec=(20, 30),
        language="ko-KR",
        tts_speed=1.05,
    )
    assert title == "Test"
    assert len(scenes) == 2
    assert scenes[0].scene_id == 1
    assert scenes[0].target_sec > 1.0
    assert "Cinematic" in scenes[0].visual_prompt_en


def test_parse_script_payload_uses_own_estimation_not_gpt() -> None:
    """GPT estimated_seconds를 무시하고 자체 추정 함수를 사용하는지 확인."""
    payload = {
        "title": "Alias Test",
        "scenes": [
            {
                "narration": "alpha beta gamma delta epsilon",
                "visual_prompt": "A bright studio shot",
                "estimated_seconds": 4.5,
            },
        ],
    }
    title, scenes = ScriptStep.parse_script_payload(
        payload,
        scene_count=1,
        target_duration_sec=(20, 30),
        language="ko-KR",
        tts_speed=1.05,
    )
    assert title == "Alias Test"
    assert len(scenes) == 1
    # GPT의 4.5가 아닌 자체 추정값 사용 (라틴 토큰 기반, 짧은 값)
    assert scenes[0].target_sec != 4.5
    assert scenes[0].target_sec >= 1.2  # 최소값 보장


def test_estimate_total_duration_uses_scene_targets() -> None:
    payload = {
        "title": "Total Test",
        "scenes": [
            {
                "narration_ko": "\uc774\uac83\uc740 \uccab \uc7a5\uba74\uc785\ub2c8\ub2e4. \uc124\uba85\uc744 \uc870\uae08 \ub354 \ub123\uc2b5\ub2c8\ub2e4.",
                "visual_prompt_en": "Scene one",
            },
            {
                "narration_ko": "\ub450 \ubc88\uc9f8 \uc7a5\uba74\uc740 \ub354 \uae34 \ubb38\uc7a5\uc73c\ub85c \uad6c\uc131\ud574 \ubcf4\uc774\uc2a4\uc624\ubc84 \uae38\uc774\ub97c \ub298\ub9bd\ub2c8\ub2e4.",
                "visual_prompt_en": "Scene two",
            },
        ],
    }
    _, scenes = ScriptStep.parse_script_payload(
        payload,
        scene_count=2,
        target_duration_sec=(20, 30),
        language="ko-KR",
        tts_speed=1.05,
    )
    total_sec = ScriptStep.estimate_total_duration_sec(scenes)
    assert total_sec == round(scenes[0].target_sec + scenes[1].target_sec, 3)


def test_run_retries_when_first_script_is_too_short() -> None:
    short_payload = {
        "title": "Short Draft",
        "scenes": [
            {
                "narration_ko": "\uc9e7\uc740 \uc124\uba85\uc785\ub2c8\ub2e4.",
                "visual_prompt_en": "Scene one",
            },
            {
                "narration_ko": "\ub610 \uc9e7\uc2b5\ub2c8\ub2e4.",
                "visual_prompt_en": "Scene two",
            },
        ],
    }
    long_enough_payload = {
        "title": "Longer Draft",
        "scenes": [
            {
                "narration_ko": "\uccab \uc7a5\uba74\uc740 \uc774\uc57c\uae30\uc758 \ubc30\uacbd\uc744 \uc790\uc138\ud788 \uc124\uba85\ud558\uace0 \uc2dc\uccad\uc790\uac00 \ud750\ub984\uc744 \ub530\ub77c\uc624\ub3c4\ub85d \ub9cc\ub4ed\ub2c8\ub2e4.",
                "visual_prompt_en": "Scene one",
            },
            {
                "narration_ko": "\ub450 \ubc88\uc9f8 \uc7a5\uba74\uc740 \ud575\uc2ec \ud3ec\uc778\ud2b8\ub97c \ub354\ud558\uace0 \ub9c8\ubb34\ub9ac\uae4c\uc9c0 \uc790\uc5f0\uc2a4\ub7fd\uac8c \uc774\uc5b4\uc11c \ucd1d \ub7f0\ud0c0\uc784\uc744 \ub9de\ucda5\ub2c8\ub2e4.",
                "visual_prompt_en": "Scene two",
            },
        ],
    }
    client = FakeOpenAIClient([short_payload, long_enough_payload])
    step = ScriptStep(config=make_config(duration_range=(8, 10)), llm_router=client, openai_client=client)

    title, scenes, hook_pattern = step.run("science topic")

    assert title == "Longer Draft"
    assert client.calls == 2
    assert 8.0 <= ScriptStep.estimate_total_duration_sec(scenes) <= 10.0
    assert hook_pattern in [p[0] for p in ScriptStep.HOOK_PATTERNS]
