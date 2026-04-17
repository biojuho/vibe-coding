from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


from shorts_maker_v2.models import SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.render_step import RenderStep
from contextlib import ExitStack


from conftest_render import _make_render_step, _DummyClip, _DummyAudioClip, _configure_render_step_for_run


# ─── 무드 분류 테스트 ────────────────────────────────────────────────────────


def test_classify_mood_dramatic() -> None:
    """블랙홀, 우주 등 키워드 → dramatic."""
    assert RenderStep._classify_mood_keywords("블랙홀의 비밀") == "dramatic"
    assert RenderStep._classify_mood_keywords("전쟁의 역사") == "dramatic"


def test_classify_mood_upbeat() -> None:
    """돈, 성공 등 키워드 → upbeat."""
    assert RenderStep._classify_mood_keywords("돈 벌기 팁") == "upbeat"
    assert RenderStep._classify_mood_keywords("성공하는 방법") == "upbeat"


def test_classify_mood_calm_default() -> None:
    """매칭 키워드 없으면 → calm (기본값)."""
    assert RenderStep._classify_mood_keywords("오늘의 날씨") == "calm"


# ─── BGM 선택 테스트 ────────────────────────────────────────────────────────


def test_pick_bgm_by_mood_matches_filename(tmp_path: Path) -> None:
    """파일명에 무드 키워드가 있으면 우선 선택."""
    step = _make_render_step()
    step._llm_router = None  # GPT 분류 비활성화
    step._openai_client = None  # OpenAI 분류 비활성화

    bgm_dramatic = tmp_path / "bgm_dramatic_01.mp3"
    bgm_upbeat = tmp_path / "bgm_upbeat_01.mp3"
    bgm_calm = tmp_path / "bgm_calm_01.mp3"
    for f in [bgm_dramatic, bgm_upbeat, bgm_calm]:
        f.write_bytes(b"\x00" * 100)

    # "블랙홀" → dramatic → bgm_dramatic_01.mp3
    result = step._pick_bgm_by_mood([bgm_dramatic, bgm_upbeat, bgm_calm], "블랙홀의 비밀")
    assert "dramatic" in result.name


def test_pick_bgm_fallback_random(tmp_path: Path) -> None:
    """무드 매칭 실패 시 랜덤 폴백."""
    step = _make_render_step()
    step._llm_router = None
    step._openai_client = None

    bgm_files = [
        tmp_path / "bgm_01.mp3",
        tmp_path / "bgm_02.mp3",
    ]
    for f in bgm_files:
        f.write_bytes(b"\x00" * 100)

    # 매칭되는 파일명 없음 → 랜덤 선택
    result = step._pick_bgm_by_mood(bgm_files, "오늘의 날씨")
    assert result in bgm_files


# ─── BGM 수집 테스트 ──────────────────────────────────────────────────────


def test_collect_bgm_files_supports_wav(tmp_path: Path) -> None:
    """BGM 수집 시 wav 확장자도 포함한다."""
    mp3_file = tmp_path / "bgm_calm_01.mp3"
    wav_file = tmp_path / "bgm_calm_02.wav"
    txt_file = tmp_path / "notes.txt"
    mp3_file.write_bytes(b"\x00" * 10)
    wav_file.write_bytes(b"\x00" * 10)
    txt_file.write_text("ignore", encoding="utf-8")

    files = RenderStep._collect_bgm_files(tmp_path)

    assert mp3_file in files
    assert wav_file in files
    assert txt_file not in files


def test_collect_bgm_files_supports_m4a_and_aac(tmp_path: Path) -> None:
    """BGM 수집 시 m4a/aac 확장자도 포함한다."""
    m4a_file = tmp_path / "bgm_01.m4a"
    aac_file = tmp_path / "bgm_02.aac"
    m4a_file.write_bytes(b"\x00" * 10)
    aac_file.write_bytes(b"\x00" * 10)

    files = RenderStep._collect_bgm_files(tmp_path)
    assert m4a_file in files
    assert aac_file in files


def test_collect_bgm_files_empty_dir(tmp_path: Path) -> None:
    """빈 디렉토리 → 빈 리스트."""
    assert RenderStep._collect_bgm_files(tmp_path) == []


# ─── BGM 무드 GPT 분류 테스트 ─────────────────────────────────────────────────


def test_classify_mood_gpt_via_llm_router() -> None:
    """LLMRouter 성공 시 GPT 결과 반환."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.return_value = {"mood": "dramatic"}
    result = step._classify_mood_gpt("우주의 비밀")
    assert result == "dramatic"


def test_classify_mood_gpt_via_openai_fallback() -> None:
    """LLMRouter 없고 OpenAI 성공 시 결과 반환."""
    step = _make_render_step()
    step._llm_router = None
    step._openai_client = MagicMock()
    step._openai_client.generate_json.return_value = {"mood": "upbeat"}
    result = step._classify_mood_gpt("성공하는 법")
    assert result == "upbeat"


def test_classify_mood_gpt_all_fail_returns_none() -> None:
    """LLM/OpenAI 모두 실패 시 None."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.side_effect = Exception("fail")
    step._openai_client = MagicMock()
    step._openai_client.generate_json.side_effect = Exception("fail")
    result = step._classify_mood_gpt("anything")
    assert result is None


def test_classify_mood_gpt_then_keyword_fallback() -> None:
    """_classify_mood: GPT 실패 → 키워드 폴백."""
    step = _make_render_step()
    step._llm_router = None
    step._openai_client = None
    result = step._classify_mood("블랙홀에 빠져들다")
    assert result == "dramatic"


# ─── SFX 테스트 ──────────────────────────────────────────────────────────────


def test_load_sfx_files_categorizes(tmp_path: Path) -> None:
    """SFX 파일을 역할별로 분류한다."""
    step = _make_render_step()
    step.config.audio.sfx_dir = "sfx"
    sfx_dir = tmp_path / "project" / "sfx"
    sfx_dir.mkdir(parents=True)
    (sfx_dir / "whoosh_01.mp3").write_bytes(b"\x00")
    (sfx_dir / "pop_bell.wav").write_bytes(b"\x00")
    (sfx_dir / "ambient_loop.mp3").write_bytes(b"\x00")

    run_dir = tmp_path / "project" / "runs" / "run1"
    run_dir.mkdir(parents=True)

    result = step._load_sfx_files(run_dir)
    assert len(result.get("hook", [])) >= 1
    assert len(result.get("cta", [])) >= 1
    assert len(result.get("transition", [])) >= 1


def test_load_sfx_files_empty(tmp_path: Path) -> None:
    """SFX 디렉토리 없으면 빈 dict."""
    step = _make_render_step()
    step.config.audio.sfx_dir = "nonexistent_sfx"
    run_dir = tmp_path / "project" / "runs" / "run1"
    run_dir.mkdir(parents=True)
    result = step._load_sfx_files(run_dir)
    assert result == {}


# ─── RMS Ducking 테스트 ──────────────────────────────────────────────────────


def test_apply_rms_ducking_returns_ducked_clip() -> None:
    """RMS ducking이 effective_vol을 적용한다."""
    import numpy as np

    narration = MagicMock()
    narration.duration = 2.0
    narration.to_soundarray.return_value = np.random.randn(88200)

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.12)
    bgm.with_effects.assert_called_once()
    assert result is ducked


def test_apply_rms_ducking_no_duration() -> None:
    """나레이션 duration이 0이면 고정 볼륨."""
    narration = MagicMock()
    narration.duration = 0

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.15)
    assert result is ducked


def test_apply_rms_ducking_exception_fallback() -> None:
    """RMS 계산 실패 시 고정 볼륨 폴백."""
    narration = MagicMock()
    narration.duration = 2.0
    narration.to_soundarray.side_effect = Exception("numpy error")

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.12)
    assert result is ducked


# ─── _classify_mood (combined) ──────────────────────────────────────────────


def test_classify_mood_gpt_value_used() -> None:
    """_classify_mood: GPT가 값을 반환하면 그것을 사용."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.return_value = {"mood": "upbeat"}
    assert step._classify_mood("아무 텍스트") == "upbeat"


def test_classify_mood_no_gpt_keyword_calm() -> None:
    """_classify_mood: GPT 없고 키워드 매칭 없으면 calm."""
    step = _make_render_step()
    step._llm_router = None
    step._openai_client = None
    assert step._classify_mood("오늘의 날씨") == "calm"


# ─── _classify_mood_gpt 추가 분기 ──────────────────────────────────────────


def test_classify_mood_gpt_invalid_mood_falls_to_openai() -> None:
    """LLMRouter가 유효하지 않은 무드를 반환하면 OpenAI fallback."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.return_value = {"mood": "invalid_mood"}
    step._openai_client = MagicMock()
    step._openai_client.generate_json.return_value = {"mood": "calm"}
    assert step._classify_mood_gpt("테스트") == "calm"


def test_classify_mood_gpt_llm_fails_openai_fallback() -> None:
    """LLMRouter 예외 → OpenAI fallback 사용."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.side_effect = RuntimeError("LLM down")
    step._openai_client = MagicMock()
    step._openai_client.generate_json.return_value = {"mood": "upbeat"}
    assert step._classify_mood_gpt("돈 벌기 팁") == "upbeat"


# ─── _generate_lyria_bgm ───────────────────────────────────────────────────


def test_generate_lyria_bgm_no_api_key(tmp_path: Path) -> None:
    """GEMINI_API_KEY 없으면 None 반환."""
    step = _make_render_step()
    step.config.audio.lyria_prompt_map = {}
    with patch.dict("os.environ", {}, clear=True):
        result = step._generate_lyria_bgm(run_dir=tmp_path, duration_sec=30.0)
    assert result is None


def test_generate_lyria_bgm_cached_file(tmp_path: Path) -> None:
    """캐시 파일이 존재하면 그대로 반환."""
    step = _make_render_step()
    step.config.audio.lyria_prompt_map = {}
    cached = tmp_path / "bgm_lyria.mp3"
    cached.write_bytes(b"\xff\xfb\x90" + b"\x00" * 100)

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        result = step._generate_lyria_bgm(run_dir=tmp_path, duration_sec=30.0)
    assert result == cached


# ─── _build_sfx_clips ──────────────────────────────────────────────────────


def test_build_sfx_clips_with_all_roles(tmp_path: Path) -> None:
    """hook/cta/transition SFX가 올바른 위치에 배치."""
    step = _make_render_step()

    def _make_sfx_clip(*args, **kwargs):
        clip = MagicMock()
        clip.with_effects.return_value = clip
        clip.with_start.return_value = clip
        return clip

    step._load_audio_clip = MagicMock(side_effect=_make_sfx_clip)

    hook_file = tmp_path / "whoosh.mp3"
    cta_file = tmp_path / "pop.mp3"
    trans_file = tmp_path / "swoosh.mp3"
    for f in (hook_file, cta_file, trans_file):
        f.write_bytes(b"\x00" * 10)

    sfx_files = {
        "hook": [hook_file],
        "cta": [cta_file],
        "transition": [trans_file],
    }
    clips = step._build_sfx_clips(
        ["hook", "body", "cta"],
        [3.0, 5.0, 4.0],
        sfx_files,
    )
    # hook SFX + 2 transitions + cta SFX = at least 4
    assert len(clips) >= 3
    assert step._load_audio_clip.call_count >= 3


def test_build_sfx_clips_empty_files() -> None:
    """SFX 파일이 비어 있으면 빈 리스트."""
    step = _make_render_step()
    sfx_files = {"hook": [], "cta": [], "transition": []}
    clips = step._build_sfx_clips(["hook", "body"], [3.0, 5.0], sfx_files)
    assert clips == []


def test_build_sfx_clips_only_transition(tmp_path: Path) -> None:
    """transition SFX만 있을 때 씬 전환 시점에만 배치."""
    step = _make_render_step()

    def _make_sfx_clip(*args, **kwargs):
        clip = MagicMock()
        clip.with_effects.return_value = clip
        clip.with_start.return_value = clip
        return clip

    step._load_audio_clip = MagicMock(side_effect=_make_sfx_clip)

    trans_file = tmp_path / "swoosh.mp3"
    trans_file.write_bytes(b"\x00" * 10)

    sfx_files = {"hook": [], "cta": [], "transition": [trans_file]}
    clips = step._build_sfx_clips(
        ["hook", "body", "cta"],
        [3.0, 5.0, 4.0],
        sfx_files,
    )
    # 3 scenes → 2 transition points
    assert len(clips) == 2


# ─── _pick_bgm_by_mood (GPT 경유) ──────────────────────────────────────────


def test_pick_bgm_by_mood_uses_gpt_mood(tmp_path: Path) -> None:
    """GPT 무드 분류 결과가 BGM 선택에 반영."""
    step = _make_render_step()
    step._llm_router = MagicMock()
    step._llm_router.generate_json.return_value = {"mood": "upbeat"}
    step._openai_client = None

    bgm_upbeat = tmp_path / "bgm_upbeat_01.mp3"
    bgm_calm = tmp_path / "bgm_calm_01.mp3"
    for f in [bgm_upbeat, bgm_calm]:
        f.write_bytes(b"\x00" * 100)

    result = step._pick_bgm_by_mood([bgm_upbeat, bgm_calm], "아무 텍스트")
    assert "upbeat" in result.name


# ─── _collect_bgm_files 정렬 확인 ──────────────────────────────────────────


def test_collect_bgm_files_sorted_order(tmp_path: Path) -> None:
    """파일들이 정렬된 순서로 반환."""
    c = tmp_path / "bgm_c.mp3"
    a = tmp_path / "bgm_a.mp3"
    b = tmp_path / "bgm_b.mp3"
    for f in (c, a, b):
        f.write_bytes(b"\x00" * 10)
    files = RenderStep._collect_bgm_files(tmp_path)
    names = [f.name for f in files]
    assert names == sorted(names)


# ─── _apply_rms_ducking 정상 동작 (numpy 경유) ─────────────────────────────


def test_apply_rms_ducking_normal_with_speech() -> None:
    """나레이션 음성이 있는 경우 ducking 적용."""
    import numpy as np

    # Generate fake audio with some loud sections
    narration = MagicMock()
    narration.duration = 3.0
    # 3 seconds at 44100Hz = 132300 samples, loud signal
    audio_data = np.ones(132300) * 0.5
    narration.to_soundarray.return_value = audio_data

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.12)
    assert result is ducked
    bgm.with_effects.assert_called_once()


def test_apply_rms_ducking_stereo_audio() -> None:
    """스테레오 나레이션 오디오 → 모노 변환 후 처리."""
    import numpy as np

    narration = MagicMock()
    narration.duration = 2.0
    # Stereo: (88200, 2)
    narration.to_soundarray.return_value = np.random.randn(88200, 2)

    bgm = MagicMock()
    ducked = MagicMock()
    bgm.with_effects = MagicMock(return_value=ducked)

    result = RenderStep._apply_rms_ducking(narration, bgm, base_vol=0.12)
    assert result is ducked


def test_generate_lyria_bgm_creates_file_from_client(tmp_path: Path) -> None:
    """Lyria generation should return the generated file when the client succeeds."""
    step = _make_render_step()
    step.config.audio.lyria_prompt_map = {"default": "calm piano", "ai_tech": "tech pulse"}

    async def _write_music_file(*, output_path, **kwargs):  # noqa: ARG001
        output_path.write_bytes(b"bgm-data")

    client = SimpleNamespace(generate_music_file=_write_music_file)

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch(
            "shorts_maker_v2.providers.google_music_client.GoogleMusicClient.from_env",
            return_value=client,
        ),
    ):
        result = step._generate_lyria_bgm(
            run_dir=tmp_path,
            duration_sec=30.0,
            channel="ai_tech",
            topic="future chips",
        )

    assert result == tmp_path / "bgm_lyria.mp3"
    assert result.exists()


def test_generate_lyria_bgm_returns_none_on_client_failure(tmp_path: Path) -> None:
    """Lyria generation should fail closed and fall back to local assets."""
    step = _make_render_step()
    step.config.audio.lyria_prompt_map = {}

    with (
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        patch(
            "shorts_maker_v2.providers.google_music_client.GoogleMusicClient.from_env",
            side_effect=RuntimeError("music client down"),
        ),
    ):
        result = step._generate_lyria_bgm(run_dir=tmp_path, duration_sec=20.0)

    assert result is None


def test_run_handles_full_karaoke_lyria_and_sfx_flow(tmp_path: Path) -> None:
    """run() should cover the main render flow with lyric BGM and SFX mixing."""
    step = _make_render_step(channel_key="ai_tech")
    _configure_render_step_for_run(step, bgm_provider="lyria", sfx_enabled=True)
    step.config.intro_outro.intro_path = "intro.mp4"
    step.config.intro_outro.outro_path = "outro.png"

    workspace = tmp_path / "workspace"
    run_dir = workspace / "runs" / "job-001"
    output_dir = workspace / "output"
    run_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    audio_path1 = run_dir / "scene01.mp3"
    audio_path2 = run_dir / "scene02.mp3"
    ssml_path = run_dir / "scene01_words_ssml.txt"
    ssml_path.write_text("break", encoding="utf-8")
    (run_dir / "broll_01.mp4").write_bytes(b"broll")

    scene_plans = [
        ScenePlan(1, "Hook narration", "hook visual", 3.0, "hook"),
        ScenePlan(2, "Closing narration", "closing visual", 4.0, "closing"),
    ]
    scene_assets = [
        SceneAsset(1, str(audio_path1), "image", "visual-1.png", 3.0),
        SceneAsset(2, str(audio_path2), "image", "visual-2.png", 4.0),
    ]

    word_segments = [
        SimpleNamespace(word="AI", start=0.0, end=0.5),
        SimpleNamespace(word="future", start=0.5, end=1.0),
    ]
    highlight_chunks = [
        (0.0, 1.0, "AI future", word_segments),
    ]

    base_lookup = {
        1: _DummyClip("base-1", duration=3.0),
        2: _DummyClip("base-2", duration=4.0),
    }
    audio_lookup = {
        str(audio_path1): _DummyAudioClip("scene-audio-1", duration=4.0),
        str(audio_path2): _DummyAudioClip("scene-audio-2", duration=4.0),
        str(run_dir / "bgm_lyria.mp3"): _DummyAudioClip("bgm", duration=80.0),
    }

    def _image_clip_factory(*args, **kwargs):  # noqa: ARG001
        return _DummyClip("image", duration=0.1, w=400, h=120)

    def _composite_video_factory(clips, size=None):  # noqa: ARG001
        duration = max((getattr(clip, "duration", 0.0) for clip in clips), default=0.0)
        audio = next((clip.audio for clip in clips if getattr(clip, "audio", None) is not None), None)
        return _DummyClip("composite-video", duration=duration, audio=audio)

    def _composite_audio_factory(clips):
        duration = max((getattr(clip, "duration", 0.0) for clip in clips), default=0.0)
        return _DummyAudioClip("mixed-audio", duration=duration)

    final_video = _DummyClip("final-video", duration=62.0, audio=_DummyAudioClip("narration", duration=62.0))
    final_video.subclipped = lambda start, end: final_video.with_duration(max(0.0, end - start))

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                step,
                "_build_bookend_clip",
                side_effect=lambda path, duration, *_: _DummyClip(
                    path,
                    duration=duration,
                ),
            )
        )
        stack.enter_context(
            patch.object(
                step,
                "_build_base_clip",
                side_effect=lambda asset, *_: base_lookup[asset.scene_id],
            )
        )
        stack.enter_context(
            patch.object(
                step,
                "_apply_channel_image_motion",
                side_effect=lambda base, **kwargs: (
                    base,
                    f"{kwargs['role']}-motion",
                ),
            )
        )
        stack.enter_context(
            patch.object(
                step,
                "_load_audio_clip",
                side_effect=lambda path: audio_lookup[str(path)],
            )
        )
        stack.enter_context(
            patch.object(
                step,
                "_apply_transitions",
                side_effect=lambda clips, *args, **kwargs: clips,
            )
        )
        lyria_bgm = stack.enter_context(
            patch.object(step, "_generate_lyria_bgm", return_value=run_dir / "bgm_lyria.mp3")
        )
        ducking = stack.enter_context(
            patch.object(step, "_apply_rms_ducking", return_value=_DummyAudioClip("ducked", duration=62.0))
        )
        load_sfx = stack.enter_context(
            patch.object(
                step,
                "_load_sfx_files",
                return_value={
                    "hook": [Path("hook.mp3")],
                    "transition": [Path("swish.mp3")],
                    "cta": [],
                },
            )
        )
        build_sfx = stack.enter_context(
            patch.object(
                step,
                "_build_sfx_clips",
                return_value=[_DummyAudioClip("sfx-1", duration=0.2), _DummyAudioClip("sfx-2", duration=0.2)],
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.color_grade_clip",
                side_effect=lambda clip, *args, **kwargs: clip,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.postprocess_tts_audio",
                return_value=None,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.load_words_json",
                return_value=word_segments,
            )
        )
        ssml_fix = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.apply_ssml_break_correction", return_value=word_segments)
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.group_word_segments",
                return_value=highlight_chunks,
            )
        )
        render_highlight = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.render_karaoke_highlight_image", return_value=None)
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.ImageClip",
                side_effect=_image_clip_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.CompositeVideoClip",
                side_effect=_composite_video_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.CompositeAudioClip",
                side_effect=_composite_audio_factory,
            )
        )
        broll_pip = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.create_broll_pip", return_value=_DummyClip("pip", duration=1.0))
        )
        animate = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.apply_text_animation", side_effect=lambda clip, **kwargs: clip)
        )
        concat_videos = stack.enter_context(
            patch("shorts_maker_v2.pipeline.render_step.concatenate_videoclips", return_value=final_video)
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.utils.hwaccel.detect_hw_encoder",
                return_value=("libx264", ["-ignored"]),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.utils.hwaccel.detect_gpu_info",
                return_value={"gpu_name": "Fake GPU", "encoder": "libx264", "decoder_support": True},
            )
        )
        write_video = stack.enter_context(patch.object(step._output_renderer, "write", return_value=None))
        stack.enter_context(patch("builtins.print"))

        result = step.run(
            scene_plans=scene_plans,
            scene_assets=scene_assets,
            output_dir=output_dir,
            output_filename="final.mp4",
            run_dir=run_dir,
            title="AI future",
            topic="AI future",
        )

    assert result == output_dir / "final.mp4"
    assert final_video.closed is True
    assert concat_videos.called
    assert lyria_bgm.called
    assert ducking.called
    assert load_sfx.called
    assert build_sfx.called
    assert render_highlight.called
    assert ssml_fix.called
    assert broll_pip.called
    assert animate.called
    write_video.assert_called_once()


def test_run_uses_static_caption_fallback_and_local_bgm_when_karaoke_fails(tmp_path: Path) -> None:
    """run() should recover from karaoke/render warnings and fall back to local BGM."""
    step = _make_render_step(channel_key="ai_tech")
    _configure_render_step_for_run(step, bgm_provider="local", sfx_enabled=False)

    workspace = tmp_path / "workspace"
    run_dir = workspace / "runs" / "job-002"
    output_dir = workspace / "output"
    bgm_dir = workspace / "assets" / "bgm"
    run_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    bgm_dir.mkdir(parents=True)
    bgm_path = bgm_dir / "bgm_loop.mp3"
    bgm_path.write_bytes(b"loop")
    (run_dir / "broll_01.mp4").write_bytes(b"broll")

    audio_path = run_dir / "scene01.mp3"
    scene_plans = [ScenePlan(1, "Fallback narration", "visual", 5.0, "hook")]
    scene_assets = [SceneAsset(1, str(audio_path), "image", "visual-1.png", 5.0)]

    base_clip = _DummyClip("base", duration=5.0)
    final_video = _DummyClip("final", duration=10.0, audio=_DummyAudioClip("narration", duration=10.0))
    local_bgm_clip = _DummyAudioClip("local-bgm", duration=2.0)
    looped_bgm_clip = _DummyAudioClip("looped-bgm", duration=12.0)

    def _image_clip_factory(*args, **kwargs):  # noqa: ARG001
        return _DummyClip("caption", duration=0.1, w=500, h=120)

    def _composite_video_factory(clips, size=None):  # noqa: ARG001
        audio = next((clip.audio for clip in clips if getattr(clip, "audio", None) is not None), None)
        duration = max((getattr(clip, "duration", 0.0) for clip in clips), default=0.0)
        return _DummyClip("composite-video", duration=duration, audio=audio)

    def _composite_audio_factory(clips):
        duration = max((getattr(clip, "duration", 0.0) for clip in clips), default=0.0)
        return _DummyAudioClip("mixed-audio", duration=duration)

    with ExitStack() as stack:
        stack.enter_context(patch.object(step, "_build_base_clip", return_value=base_clip))
        stack.enter_context(patch.object(step, "_apply_channel_image_motion", return_value=(base_clip, "ken_burns")))
        stack.enter_context(
            patch.object(
                step,
                "_load_audio_clip",
                side_effect=lambda path: (
                    local_bgm_clip if str(path) == str(bgm_path) else _DummyAudioClip("scene", duration=5.5)
                ),
            )
        )
        static_caption = stack.enter_context(
            patch.object(step, "_render_static_caption", return_value=run_dir / "caption.png")
        )
        stack.enter_context(
            patch.object(
                step,
                "_apply_transitions",
                side_effect=lambda clips, *args, **kwargs: clips,
            )
        )
        pick_bgm = stack.enter_context(patch.object(step, "_pick_bgm_by_mood", return_value=bgm_path))
        ducking = stack.enter_context(
            patch.object(step, "_apply_rms_ducking", return_value=_DummyAudioClip("ducked", duration=10.0))
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.color_grade_clip",
                side_effect=RuntimeError("grade failed"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.postprocess_tts_audio",
                side_effect=RuntimeError("post failed"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.load_words_json",
                side_effect=RuntimeError("words missing"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.ImageClip",
                side_effect=_image_clip_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.CompositeVideoClip",
                side_effect=_composite_video_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.CompositeAudioClip",
                side_effect=_composite_audio_factory,
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.create_broll_pip",
                side_effect=RuntimeError("pip failed"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.apply_text_animation",
                side_effect=RuntimeError("anim failed"),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.pipeline.render_step.concatenate_videoclips",
                return_value=final_video,
            )
        )
        concat_audio = stack.enter_context(patch("moviepy.concatenate_audioclips", return_value=looped_bgm_clip))
        stack.enter_context(
            patch(
                "shorts_maker_v2.utils.hwaccel.detect_hw_encoder",
                return_value=("h264_nvenc", ["-preset", "p4"]),
            )
        )
        stack.enter_context(
            patch(
                "shorts_maker_v2.utils.hwaccel.detect_gpu_info",
                side_effect=RuntimeError("gpu lookup failed"),
            )
        )
        write_video = stack.enter_context(patch.object(step._output_renderer, "write", return_value=None))
        stack.enter_context(patch("builtins.print"))

        result = step.run(
            scene_plans=scene_plans,
            scene_assets=scene_assets,
            output_dir=output_dir,
            output_filename="fallback.mp4",
            run_dir=run_dir,
            title="Fallback topic",
            topic="Fallback topic",
        )

    assert result == output_dir / "fallback.mp4"
    assert static_caption.called
    assert pick_bgm.called
    assert concat_audio.called
    assert ducking.called
    write_video.assert_called_once()
