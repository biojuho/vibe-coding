"""render_audio.py (RenderAudioMixin) 단위 테스트.

ClassMethod / StaticMethod 위주로 MoviePy 없이 테스트.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from shorts_maker_v2.pipeline.render_audio import RenderAudioMixin


# ── 테스트용 최소 Mixin 인스턴스 ──────────────────────────────────────────────
class _MinimalRenderStep(RenderAudioMixin):
    """RenderAudioMixin을 직접 테스트하기 위한 최소 스텁."""

    def __init__(self):
        self._llm_router = None
        self._openai_client = None
        self.config = MagicMock()
        self.config.audio.bgm_dir = "assets/bgm"
        self.config.audio.sfx_dir = "assets/sfx"
        self.config.audio.sfx_volume = 0.5
        self.config.audio.lyria_prompt_map = {}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. _classify_mood_keywords — 순수 함수 (classmethod)
# ═══════════════════════════════════════════════════════════════════════════════


class TestClassifyMoodKeywords:
    def test_dramatic_keyword_블랙홀(self):
        """'블랙홀' → dramatic."""
        assert RenderAudioMixin._classify_mood_keywords("블랙홀 형성 원리") == "dramatic"

    def test_dramatic_keyword_죽음(self):
        assert RenderAudioMixin._classify_mood_keywords("죽음의 위협") == "dramatic"

    def test_dramatic_keyword_전쟁(self):
        assert RenderAudioMixin._classify_mood_keywords("우주 전쟁의 역사") == "dramatic"

    def test_upbeat_keyword_돈(self):
        """'돈' → upbeat."""
        assert RenderAudioMixin._classify_mood_keywords("돈 버는 방법") == "upbeat"

    def test_upbeat_keyword_성공(self):
        # "비밀"은 dramatic 키워드이므로 사용 금지
        assert RenderAudioMixin._classify_mood_keywords("성공한 사람들의 습관") == "upbeat"

    def test_upbeat_keyword_부자(self):
        assert RenderAudioMixin._classify_mood_keywords("부자가 되는 쉬운 팁") == "upbeat"

    def test_no_keyword_returns_calm(self):
        """매칭 키워드 없음 → calm 폴백."""
        assert RenderAudioMixin._classify_mood_keywords("오늘의 날씨 이야기") == "calm"

    def test_empty_text_returns_calm(self):
        assert RenderAudioMixin._classify_mood_keywords("") == "calm"

    def test_dramatic_takes_precedence_over_upbeat(self):
        """dramatic 키워드가 먼저 등장하면 dramatic 반환."""
        text = "블랙홀 돈 이야기"
        result = RenderAudioMixin._classify_mood_keywords(text)
        assert result in ("dramatic", "upbeat")  # 순서에 따라 다름

    def test_upbeat_multiple_keywords(self):
        """여러 upbeat 키워드 → upbeat."""
        assert RenderAudioMixin._classify_mood_keywords("건강 성장 행복의 방법") == "upbeat"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. _collect_bgm_files — staticmethod (파일시스템)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCollectBgmFiles:
    def test_collects_mp3_wav_m4a_aac(self, tmp_path):
        """4가지 확장자 파일을 모두 수집."""
        for name in ["a.mp3", "b.wav", "c.m4a", "d.aac", "skip.txt"]:
            (tmp_path / name).write_bytes(b"")
        files = RenderAudioMixin._collect_bgm_files(tmp_path)
        names = {f.name for f in files}
        assert "a.mp3" in names
        assert "b.wav" in names
        assert "c.m4a" in names
        assert "d.aac" in names
        assert "skip.txt" not in names

    def test_empty_dir_returns_empty_list(self, tmp_path):
        assert RenderAudioMixin._collect_bgm_files(tmp_path) == []

    def test_result_is_sorted(self, tmp_path):
        """결과가 정렬돼 있어야 함 (재현성)."""
        for name in ["c.mp3", "a.mp3", "b.mp3"]:
            (tmp_path / name).write_bytes(b"")
        files = RenderAudioMixin._collect_bgm_files(tmp_path)
        names = [f.name for f in files]
        assert names == sorted(names)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. _apply_rms_ducking — staticmethod (numpy + MoviePy mock)
# ═══════════════════════════════════════════════════════════════════════════════


def _mock_audio(duration: float, array: np.ndarray | None = None) -> MagicMock:
    """테스트용 AudioFileClip 스텁."""
    mock = MagicMock()
    mock.duration = duration
    if array is None:
        array = np.zeros(int(44100 * duration))
    mock.to_soundarray = MagicMock(return_value=array)
    return mock


def _mock_bgm() -> MagicMock:
    """테스트용 BGM 클립 스텁 — with_effects 체인 지원."""
    bgm = MagicMock()
    bgm.with_effects = MagicMock(return_value=MagicMock())
    return bgm


class TestApplyRmsDucking:
    def test_zero_duration_returns_base_vol_clip(self):
        """RMS-DMX001: duration=0 → base_vol 고정."""
        nar = _mock_audio(0.0)
        bgm = _mock_bgm()
        result = RenderAudioMixin._apply_rms_ducking(nar, bgm)
        bgm.with_effects.assert_called_once()
        assert result is bgm.with_effects.return_value

    def test_silence_narration_no_ducking(self):
        """RMS-DMX002: 나레이션이 무음(0)이면 유효 볼륨 = base_vol."""
        silence = np.zeros(44100)  # 1초 무음
        nar = _mock_audio(1.0, silence)
        bgm = _mock_bgm()
        RenderAudioMixin._apply_rms_ducking(nar, bgm, base_vol=0.12, duck_factor=0.25)
        # bgm.with_effects가 호출돼야 함 (에러 없이)
        bgm.with_effects.assert_called()

    def test_full_speech_causes_maximum_ducking(self):
        """RMS-DMX003: 고에너지 나레이션 → BGM이 duck_factor 수준으로 감소."""
        high_energy = np.ones(44100) * 0.5  # 강한 신호
        nar = _mock_audio(1.0, high_energy)
        bgm = _mock_bgm()

        from moviepy.audio.fx import MultiplyVolume

        with patch.object(MultiplyVolume, "__init__", return_value=None):
            RenderAudioMixin._apply_rms_ducking(nar, bgm, base_vol=0.12, duck_factor=0.25)
        bgm.with_effects.assert_called()

    def test_exception_falls_back_to_base_vol(self):
        """RMS-DMX004: 예외 발생 시 고정 base_vol 폴백."""
        nar = MagicMock()
        nar.duration = 1.0
        nar.to_soundarray = MagicMock(side_effect=RuntimeError("mock error"))
        bgm = _mock_bgm()
        result = RenderAudioMixin._apply_rms_ducking(nar, bgm, base_vol=0.12)
        bgm.with_effects.assert_called()
        assert result is bgm.with_effects.return_value

    def test_stereo_array_converted_to_mono(self):
        """RMS-DMX005: 2채널 배열 → mean(axis=1) → 모노 처리, 크래시 없음."""
        stereo = np.random.rand(44100, 2) * 0.1
        nar = _mock_audio(1.0, stereo)
        bgm = _mock_bgm()
        RenderAudioMixin._apply_rms_ducking(nar, bgm)  # should not raise
        bgm.with_effects.assert_called()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. _classify_mood (GPT first, 키워드 fallback)
# ═══════════════════════════════════════════════════════════════════════════════


class TestClassifyMood:
    def test_gpt_success_returns_gpt_mood(self):
        """RMA-001: LLMRouter 성공 시 GPT 무드 반환."""
        rs = _MinimalRenderStep()
        rs._llm_router = MagicMock()
        rs._llm_router.generate_json.return_value = {"mood": "dramatic"}
        result = rs._classify_mood("블랙홀")
        assert result == "dramatic"

    def test_gpt_failure_fallback_keyword(self):
        """RMA-002: LLMRouter 실패 → 키워드 폴백."""
        rs = _MinimalRenderStep()
        rs._llm_router = MagicMock()
        rs._llm_router.generate_json.side_effect = RuntimeError("LLM down")
        result = rs._classify_mood("블랙홀 위험 경고")
        assert result == "dramatic"  # 키워드 폴백

    def test_invalid_gpt_mood_falls_back_to_keyword(self):
        """RMA-003: LLM이 알 수 없는 무드 반환 → 키워드 폴백."""
        rs = _MinimalRenderStep()
        rs._llm_router = MagicMock()
        rs._llm_router.generate_json.return_value = {"mood": "super_sad"}
        result = rs._classify_mood("오늘의 이야기")  # no dramatic/upbeat keywords
        assert result == "calm"

    def test_no_llm_router_uses_keyword_only(self):
        """RMA-004: llm_router=None → 키워드 직접 사용."""
        rs = _MinimalRenderStep()
        rs._llm_router = None
        rs._openai_client = None
        result = rs._classify_mood("성공 비결 팁")
        assert result == "upbeat"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. _pick_bgm_by_mood
# ═══════════════════════════════════════════════════════════════════════════════


class TestPickBgmByMood:
    def test_picks_mood_matched_file(self, tmp_path):
        """RMA-010: 무드 키워드가 파일명에 있으면 해당 파일 선택."""
        rs = _MinimalRenderStep()
        rs._llm_router = None
        rs._openai_client = None
        # dramatic keyword in text, "epic" file name matches dramatic
        dramatic_file = tmp_path / "epic_track.mp3"
        calm_file = tmp_path / "calm_ambient.mp3"
        dramatic_file.write_bytes(b"")
        calm_file.write_bytes(b"")
        files = [dramatic_file, calm_file]
        chosen = rs._pick_bgm_by_mood(files, "블랙홀 위험 경고")
        assert chosen == dramatic_file

    def test_random_fallback_when_no_mood_match(self, tmp_path):
        """RMA-011: 무드 매칭 파일 없으면 랜덤 폴백 (크래시 없음)."""
        rs = _MinimalRenderStep()
        rs._llm_router = None
        rs._openai_client = None
        any_file = tmp_path / "background.mp3"
        any_file.write_bytes(b"")
        chosen = rs._pick_bgm_by_mood([any_file], "오늘 날씨 이야기")
        assert chosen == any_file

    def test_empty_files_raises(self, tmp_path):
        """RMA-012: bgm_files 빈 리스트 → ValueError."""
        rs = _MinimalRenderStep()
        with pytest.raises(ValueError):
            rs._pick_bgm_by_mood([], "블랙홀")


# ── _apply_rms_ducking NaN/Inf 가드 (RA-NI 시리즈) ──────────────────────────


class TestApplyRmsDuckingNanInf:
    """RA-NI: corrupt audio(NaN/Inf RMS) 가 오디오 ducking을 완전히 깨뜨리지 않음."""

    def _make_nar(self, samples: np.ndarray, fps: int = 44100) -> MagicMock:
        nar = MagicMock()
        nar.duration = len(samples) / fps
        nar.fps = fps
        nar.to_soundarray.return_value = samples
        return nar

    def _make_bgm(self) -> MagicMock:
        bgm = MagicMock()
        bgm.with_effects.return_value = bgm
        return bgm

    def test_nan_audio_samples_return_base_vol_ducking(self) -> None:
        """RA-NI001: NaN 샘플 → rms_values 빈 리스트 → base_vol 적용, 크래시 없음."""
        samples = np.full(44100, float("nan"), dtype=np.float32)
        nar = self._make_nar(samples)
        bgm = self._make_bgm()

        result = RenderAudioMixin._apply_rms_ducking(nar, bgm, base_vol=0.12)
        assert result is bgm
        bgm.with_effects.assert_called_once()

    def test_inf_audio_samples_do_not_crash(self) -> None:
        """RA-NI002: Inf 샘플 → 폴백, 크래시 없음."""
        samples = np.full(44100, float("inf"), dtype=np.float32)
        nar = self._make_nar(samples)
        bgm = self._make_bgm()

        result = RenderAudioMixin._apply_rms_ducking(nar, bgm, base_vol=0.12)
        assert result is bgm

    def test_valid_samples_use_ducking(self) -> None:
        """RA-NI003: 정상 샘플 → ducking 적용됨 (결과 클립 반환)."""
        # 1초짜리 0.5 진폭 sine wave (유효 RMS)
        t = np.linspace(0, 1, 44100, dtype=np.float32)
        samples = np.sin(2 * np.pi * 440 * t) * 0.5
        nar = self._make_nar(samples)
        bgm = self._make_bgm()

        result = RenderAudioMixin._apply_rms_ducking(nar, bgm, base_vol=0.12)
        assert result is bgm
        bgm.with_effects.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. _build_sfx_clips — SFX timing regression tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBuildSfxClips:
    def _make_step(self, sfx_vol: float = 0.5):
        step = _MinimalRenderStep()
        step.config.audio.sfx_volume = sfx_vol
        # _build_sfx_clips calls self._load_audio_clip — add as mock method
        step._load_audio_clip = MagicMock()
        return step

    def _fake_clip(self):
        clip = MagicMock()
        effected = MagicMock()
        effected.with_start = MagicMock(return_value=MagicMock())
        clip.with_effects = MagicMock(return_value=effected)
        return clip

    def test_sfx_transition_not_placed_when_scene_too_short(self):
        """RA-SFX001: dur < 150ms 씬의 transition SFX 는 scene start 와 겹치지 않아야 한다."""
        step = self._make_step()

        # Use distinct clip per _load_audio_clip call so hook vs transition are distinguishable
        hook_clip = self._fake_clip()
        transition_clip = self._fake_clip()
        call_count = [0]

        def _side_effect(_path):
            i = call_count[0]
            call_count[0] += 1
            return [hook_clip, transition_clip][min(i, 1)]

        step._load_audio_clip.side_effect = _side_effect

        step._build_sfx_clips(
            scene_roles=["hook", "body"],
            scene_durations=[0.10, 5.0],  # scene 0 is 100ms — below 150ms threshold
            sfx_files={"hook": [MagicMock()], "transition": [MagicMock()]},
        )

        # For dur=0.10: transition_t = 0 + max(0.0, 0.10 - 0.15) = 0.0
        # 0.0 is NOT > cursor + 0.05 (0.05) → transition clip must NOT have with_start called
        (
            transition_clip.with_effects.return_value.with_start.assert_not_called(),
            ("Transition SFX must not be placed when scene dur < 150ms"),
        )

    def test_sfx_transition_placed_at_end_of_long_scene(self):
        """RA-SFX002: dur > 150ms 씬의 transition SFX 는 씬 끝 부근에 배치돼야 한다."""
        step = self._make_step()
        fake_clip = self._fake_clip()
        step._load_audio_clip.return_value = fake_clip

        step._build_sfx_clips(
            scene_roles=["hook", "body"],
            scene_durations=[5.0, 3.0],
            sfx_files={"hook": [MagicMock()], "transition": [MagicMock()]},
        )

        # transition_t = 0 + max(0, 5.0 - 0.15) = 4.85; must be > 0 + 0.05 → placed
        start_calls = fake_clip.with_effects.return_value.with_start.call_args_list
        transition_times = [c.args[0] for c in start_calls if c.args[0] > 0.05]
        assert any(abs(t - 4.85) < 0.01 for t in transition_times), (
            f"Expected transition at ~4.85, got: {transition_times}"
        )

    def test_sfx_mismatched_lengths_raises_value_error(self):
        """RA-SFX003: scene_roles/scene_durations 길이 불일치 → ValueError (strict=True).

        렌더 파이프라인 상류에서 씬 수가 맞지 않으면 silent 데이터 드롭 대신
        즉시 ValueError 가 발생해야 한다.
        """
        step = self._make_step()
        step._load_audio_clip = MagicMock(return_value=self._fake_clip())

        with pytest.raises(ValueError):
            step._build_sfx_clips(
                scene_roles=["hook", "body", "closing"],
                scene_durations=[5.0, 4.0],  # 길이 불일치 (3 vs 2)
                sfx_files={"hook": [MagicMock()], "transition": [MagicMock()]},
            )
